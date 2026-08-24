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