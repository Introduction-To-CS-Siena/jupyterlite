#!/usr/bin/env python3
"""Generate the JupyterLab App Launcher tiles for the CSIS 110 labs.

Every notebook under ``files/`` becomes a card in the JupyterLite Launcher that
opens that notebook straight from the file browser (no copy is made, so student
work and the images/sounds next to the notebook keep working).

The cards are written into ``overrides.json`` under the ``appLauncherData`` key,
which is where the ``jupyter_app_launcher`` frontend extension reads them from
when it runs in JupyterLite.  Every other key in ``overrides.json`` is left
untouched.

Usage::

    python scripts/generate_launcher_tiles.py        # rewrite overrides.json
    python scripts/generate_launcher_tiles.py --check # fail if it is stale

Add a lab by dropping a folder with a notebook into ``files/`` and re-running
this script; the title and subtitle are read from the notebook's own first
markdown cell.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENTS_DIR = REPO_ROOT / "files"
OVERRIDES = REPO_ROOT / "overrides.json"

# Launcher sections, in the order they should appear.
LABS_CATEGORY = "CSIS 110 Labs"
HOMEWORK_CATEGORY = "Homework"

# Notebooks whose own first heading does not identify them well enough.
TITLE_OVERRIDES = {
    "Lab2/Chapter 1.ipynb": "Lab 2 - Chapter 1: Picture This!",
    "Lab4/Lab 4a notebook.ipynb": "Lab 4a: Getting Started",
}

# Notebooks that should not get a launcher card at all.
EXCLUDE = set()

# Card colours, per section.
COLORS = {
    LABS_CATEGORY: "#1976d2",
    HOMEWORK_CATEGORY: "#7b1fa2",
}

TAG_RE = re.compile(r"<[^>]+>")
EMPHASIS_RE = re.compile(r"[*_]{1,3}")
H1_BLOCK_RE = re.compile(r"<h1\b.*?</h1>", re.IGNORECASE | re.DOTALL)
LAB_NUM_RE = re.compile(r"^Lab\s*(\d+)([a-z]?)", re.IGNORECASE)

# Subtitles that are course logistics rather than a name for the notebook.
BORING_SUBTITLE_RE = re.compile(
    r"^(due|hint|hints|please|assigned|what you|read )", re.IGNORECASE
)


def natural_key(path: Path) -> tuple:
    """Sort Lab2 before Lab10, and keep Homeworks last."""
    parts = path.relative_to(CONTENTS_DIR).parts
    top = parts[0]
    section_rank = 1 if top.lower().startswith("homework") else 0
    chunks = [
        int(chunk) if chunk.isdigit() else chunk.lower()
        for chunk in re.split(r"(\d+)", str(path))
        if chunk
    ]
    return (section_rank, chunks)


def clean(text: str) -> str:
    """Turn a markdown/HTML heading into a single line of plain text."""
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = EMPHASIS_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" #-–—:")
    # "Picture This !" -> "Picture This!"
    text = re.sub(r"\s+([!?.,:;])", r"\1", text)
    # Banner headings are often shouted; "FUNHOUSE MIRRORS" -> "Funhouse Mirrors".
    if text.isupper():
        text = text.title()
    return text


def headings(notebook: Path) -> list[str]:
    """The plain-text headings of the notebook's first markdown cell."""
    try:
        cells = json.loads(notebook.read_text(encoding="utf-8")).get("cells", [])
    except (OSError, ValueError) as exc:  # pragma: no cover - corrupt notebook
        print(f"warning: could not read {notebook}: {exc}", file=sys.stderr)
        return []
    for cell in cells:
        if cell.get("cell_type") != "markdown":
            continue
        source = "".join(cell.get("source", []))
        # A centred <h1> banner spans several lines; fold it into one heading.
        source = H1_BLOCK_RE.sub(lambda m: "\n# " + clean(m.group(0)) + "\n", source)
        found = []
        for line in source.splitlines():
            if not line.strip().startswith("#"):
                continue
            text = clean(line)
            if text and text not in found:
                found.append(text)
            if len(found) >= 2:
                break
        return found
    return []


def describe(notebook: Path) -> tuple[str, str]:
    """Return the (title, subtitle) shown on the launcher card."""
    rel = notebook.relative_to(CONTENTS_DIR).as_posix()
    if rel in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[rel], ""
    found = headings(notebook)
    if not found:
        return notebook.stem, ""
    title, subtitle = found[0], found[1] if len(found) > 1 else ""
    if subtitle and BORING_SUBTITLE_RE.match(subtitle):
        subtitle = ""
    if subtitle and len(f"{title}: {subtitle}") <= 60:
        return f"{title}: {subtitle}", subtitle
    return title, ""


def badge(title: str, category: str) -> str:
    """A small coloured square with the lab number or the initials on it."""
    match = LAB_NUM_RE.match(title)
    if match:
        label = f"{match.group(1)}{match.group(2)}"
    else:
        words = [w for w in re.split(r"\W+", title) if w]
        label = "".join(w[0] for w in words[:2]).upper() or "?"
    size = {1: 15, 2: 12, 3: 9}.get(len(label), 9)
    color = COLORS.get(category, "#455a64")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" '
        'height="24" class="jp-al-app-icon">'
        f'<rect x="1" y="1" width="22" height="22" rx="5" fill="{color}"/>'
        f'<text x="12" y="12" fill="#ffffff" font-size="{size}" font-weight="600" '
        'font-family="var(--jp-ui-font-family, sans-serif)" text-anchor="middle" '
        f'dominant-baseline="central">{html.escape(label)}</text></svg>'
    )


def build_config() -> list[dict]:
    entries = []
    notebooks = sorted(CONTENTS_DIR.rglob("*.ipynb"), key=natural_key)
    for notebook in notebooks:
        rel = notebook.relative_to(CONTENTS_DIR).as_posix()
        if rel in EXCLUDE or ".ipynb_checkpoints" in rel:
            continue
        top = notebook.relative_to(CONTENTS_DIR).parts[0]
        category = (
            HOMEWORK_CATEGORY if top.lower().startswith("homework") else LABS_CATEGORY
        )
        title, _ = describe(notebook)
        slug = re.sub(r"[^a-z0-9]+", "-", rel.lower().removesuffix(".ipynb")).strip("-")
        entries.append(
            {
                "id": f"csis110-launcher:{slug}",
                "title": title,
                "description": f"Open {rel}",
                "type": "jupyterlab-commands",
                "catalog": category,
                "icon": badge(title, category),
                "source": [
                    {
                        "label": f"Open {title}",
                        "id": "docmanager:open",
                        "args": {"path": rel},
                    }
                ],
            }
        )
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if overrides.json is out of date instead of rewriting it",
    )
    args = parser.parse_args()

    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    config = build_config()
    updated = dict(overrides)
    updated["appLauncherData"] = {"config": config}
    rendered = json.dumps(updated, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if OVERRIDES.read_text(encoding="utf-8") != rendered:
            print(
                "overrides.json is out of date; run "
                "`python scripts/generate_launcher_tiles.py`",
                file=sys.stderr,
            )
            return 1
        print(f"overrides.json is up to date ({len(config)} launcher cards)")
        return 0

    OVERRIDES.write_text(rendered, encoding="utf-8")
    print(f"Wrote {len(config)} launcher cards to {OVERRIDES.relative_to(REPO_ROOT)}")
    for entry in config:
        print(f"  [{entry['catalog']}] {entry['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
