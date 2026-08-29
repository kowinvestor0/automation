"""Escribe el resumen de la corrida en el Job Summary de GitHub Actions.

Se usa desde el workflow. Corriendolo a mano imprime lo mismo en pantalla.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    metas = sorted(ROOT.glob("output/*/meta.json"))
    lines = ["### Videos generados", ""]

    if not metas:
        lines.append("_Ninguno. Revisa el log del paso anterior._")
    for path in metas:
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            lines.append(f"- `{path.parent.name}`: meta ilegible ({e})")
            continue
        lines.append(f"**{d.get('title', path.parent.name)}**  ")
        lines.append(f"{d.get('duration_seconds', '?')}s · guion: {d.get('source', '?')}"
                     f" · voz: {d.get('voice', '?')}  ")
        if d.get("hashtags"):
            lines.append("`" + " ".join(d["hashtags"]) + "`  ")
        if d.get("attributions"):
            lines.append(f"_{len(d['attributions'])} fotos con atribucion "
                         f"(ver creditos.txt)_  ")
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
