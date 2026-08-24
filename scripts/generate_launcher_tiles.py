#!/usr/bin/env python3
"""Generate the JupyterLab App Launcher tiles for the CSIS 110 labs.

Every notebook under ``files/`` becomes a card in the JupyterLite Launcher.
Clicking a card navigates the file browser into that lab's folder and opens the
notebook from there (no copy is made, so student work and the images/sounds next
to the notebook keep working).

This runs *after* ``jupyter lite build`` and patches the built site in place:

* the cards go into the ``appLauncherData`` key of ``settingsOverrides`` in
  ``jupyter-lite.json``, where the ``jupyter_app_launcher`` frontend extension
  reads them from when it runs in JupyterLite;
* a small stylesheet goes into each built page, to lift the course sections
  above the built-in Notebook/Console/Other ones.

``appLauncherData`` deliberately does not live in the repository's
``overrides.json``: ``jupyter lite check`` splits every key there on ``":"`` to
find its schema and raises ``ValueError`` on a key without one.

Usage::

    python scripts/generate_launcher_tiles.py dist  # patch a built site
    python scripts/generate_launcher_tiles.py       # list the cards, change nothing

Add a lab by dropping a folder with a notebook into ``files/``; the title and
subtitle are read from the notebook's own first markdown cell, and the deploy
workflow re-runs this script on every build.
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
LITE_JSON = "jupyter-lite.json"

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

# Marks the stylesheet this script injects into the built pages.
MARKER = "csis110-launcher-order"

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


def build_css() -> str:
    """CSS that lifts the course sections to the top of the Launcher.

    JupyterLab ranks the built-in Launcher sections (Notebook 0, Console 20,
    Other 100) ahead of any section it does not know, and only an item's
    ``categoryRank`` can beat that -- which ``jupyter_app_launcher`` does not
    pass through.  Re-ordering the rendered sections with flexbox is the part
    we can control from here.
    """
    rules = [
        f"/* {MARKER} */",
        ".jp-Launcher-content { display: flex; flex-direction: column; }",
        ".jp-Launcher-section { order: 10; }",
    ]
    for order, category in enumerate((LABS_CATEGORY, HOMEWORK_CATEGORY), start=1):
        rules.append(
            f'.jp-Launcher-section:has(.jp-LauncherCard[data-category="{category}"])'
            f" {{ order: {order}; }}"
        )
    return "\n".join(rules)


def patch_pages(output_dir: Path) -> int:
    """Inject :func:`build_css` into every built page of a JupyterLite site."""
    style = f"<style>\n{build_css()}\n</style>\n</head>"
    seen = patched = 0
    for page in sorted(output_dir.rglob("index.html")):
        text = page.read_text(encoding="utf-8")
        if "</head>" not in text:
            continue
        seen += 1
        if MARKER in text:
            continue
        page.write_text(text.replace("</head>", style, 1), encoding="utf-8")
        patched += 1
    if not seen:
        print(f"error: no page under {output_dir} has a <head> to patch", file=sys.stderr)
        return 1
    print(f"Ordered the Launcher sections on {seen} page(s) ({patched} newly patched)")
    return 0


def patch_settings(output_dir: Path, config: list[dict]) -> int:
    """Add the cards to the built site's settings overrides."""
    lite_json = output_dir / LITE_JSON
    if not lite_json.exists():
        print(
            f"error: {lite_json} not found; run `jupyter lite build` first",
            file=sys.stderr,
        )
        return 1
    data = json.loads(lite_json.read_text(encoding="utf-8"))
    overrides = data.setdefault("jupyter-config-data", {}).setdefault(
        "settingsOverrides", {}
    )
    overrides["appLauncherData"] = {"config": config}
    lite_json.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(config)} launcher cards to {lite_json}")
    return 0


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
                        # open-path navigates the file browser into the folder,
                        # selects the notebook there, and then opens it.
                        "id": "filebrowser:open-path",
                        "args": {"path": rel},
                    }
                ],
            }
        )
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_dir",
        nargs="?",
        type=Path,
        help="a JupyterLite site built by `jupyter lite build`; "
        "omit to only list the cards",
    )
    args = parser.parse_args()

    config = build_config()
    for entry in config:
        print(f"  [{entry['catalog']}] {entry['title']}")
    if args.output_dir is None:
        print(f"{len(config)} launcher cards (pass an output dir to apply them)")
        return 0

    return patch_settings(args.output_dir, config) or patch_pages(args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
