# JupyterLite for Siena University MLS

This is a JupyterLite deployment for the Siena University **CSIS 110 - Introduction to Computer Science** course.

Deployed at [https://lab.csis110.com](https://lab.csis110.com)

## Commands

```bash
python -m pip install -r requirements.txt
jupyter lite build
jupyter lite serve
```
## Notes
`jupyter lite build --contents files --output-dir dist`

## Launcher cards for the labs

Every notebook under `files/` gets a card in the JupyterLite Launcher, grouped
into **CSIS 110 Labs** and **Homework**. Those sections, and the
**Notebook Pairing** section above them, are lifted above the built-in
Notebook/Console/Other ones — `SECTION_ORDER` in the script sets the order.
Clicking a lab card navigates the file browser
into that lab's folder, selects the notebook and opens it — it does not copy
the notebook, so a student's saved work and the images/sounds stored beside it
keep working.

The cards are rendered by the [`jupyter-app-launcher`](https://github.com/trungleduc/jupyter_app_launcher)
extension. `scripts/generate_launcher_tiles.py` generates them from the `files/`
tree and patches them into an already-built site:

```bash
jupyter lite build --contents files --output-dir dist
python scripts/generate_launcher_tiles.py dist  # add the cards
jupyter lite serve --output-dir dist

python scripts/generate_launcher_tiles.py       # list the cards, change nothing
```

The deploy workflow runs the same two commands, so to add a lab you only have
to drop a folder with a notebook into `files/`. A card's title comes from the
notebook's own first markdown heading, so `# Lab 11` plus `## Recursion!`
becomes a card labelled *Lab 11: Recursion!*. If a notebook's heading does not
identify it well, add an entry to `TITLE_OVERRIDES` at the top of the script;
`EXCLUDE` hides a notebook from the Launcher entirely.

Two notes on why the script patches `dist/` instead of this repo's
`overrides.json`:

- `jupyter lite check` splits every key in `overrides.json` on `":"` to find
  the matching schema, so the extension's `appLauncherData` key crashes it.
  The cards go straight into `settingsOverrides` in the built
  `jupyter-lite.json` instead, after the check has run.
- JupyterLab ranks its own Launcher sections ahead of any it does not know,
  and only an item's `categoryRank` can beat that — which `jupyter-app-launcher`
  does not pass through, and which we cannot set on the pairing extension's
  card at all. The script injects a small stylesheet into the built pages that
  re-orders the sections with flexbox instead.
