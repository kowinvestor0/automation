"""Writes the run summary into the GitHub Actions Job Summary.

Called from the workflow. Run by hand it prints the same thing to the screen.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    metas = sorted(ROOT.glob("output/*/meta.json"))
    lines = ["### Videos generated", ""]

    if not metas:
        lines.append("_None. Check the log of the previous step._")
    for path in metas:
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            lines.append(f"- `{path.parent.name}`: unreadable meta ({e})")
            continue
        lines.append(f"**{d.get('title', path.parent.name)}**  ")
        lines.append(f"{d.get('duration_seconds', '?')}s · script: {d.get('source', '?')}"
                     f" · voice: {d.get('voice', '?')}  ")
        if d.get("hashtags"):
            lines.append("`" + " ".join(d["hashtags"]) + "`  ")
        if d.get("attributions"):
            lines.append(f"_{len(d['attributions'])} photos need credit "
                         f"(see credits.txt)_  ")
        lines.append("")

    text = "\n".join(lines) + "\n"
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(text)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
