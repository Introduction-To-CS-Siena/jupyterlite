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
into **CSIS 110 Labs** and **Homework**, so students can open a lab
without digging through the file browser. Clicking a card runs
`docmanager:open` on the real file in the file browser — it does not copy the
notebook, so a student's saved work and the images/sounds stored beside the
notebook keep working.

The cards are rendered by the [`jupyter-app-launcher`](https://github.com/trungleduc/jupyter_app_launcher)
extension, which reads them from the `appLauncherData` key of `overrides.json`.
That key is generated, not hand-written:

```bash
python scripts/generate_launcher_tiles.py          # rewrite the cards
python scripts/generate_launcher_tiles.py --check  # fail if they are stale
```

To add a lab, drop a folder with a notebook into `files/` and re-run the
script (CI runs it before every build too). The card's title comes from the
notebook's own first markdown heading, so `# Lab 11` plus `## Recursion!`
becomes a card labelled *Lab 11: Recursion!*. If a notebook's heading does not
identify it well, add an entry to `TITLE_OVERRIDES` at the top of the script;
`EXCLUDE` hides a notebook from the Launcher entirely.
