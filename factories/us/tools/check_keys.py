"""Verifica las llaves contra las APIs de verdad y dice exactamente que falla.

    python tools/check_keys.py

No imprime las llaves: solo su longitud y de donde salieron.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.util import load_dotenv  # noqa: E402

PLACEHOLDERS = {"...", "your-key-here", "xxx", "sk-ant-...", ""}


def _origin(name, from_file):
    return ".env" if name in from_file else "entorno (setx / export)"


def check_anthropic(from_file):
    name = "ANTHROPIC_API_KEY"
    key = os.environ.get(name, "").strip()
    if key in PLACEHOLDERS:
        print(f"  {name:20} NO CONFIGURADA -> se usara topics.json")
        return
    print(f"  {name:20} {len(key)} caracteres, desde {_origin(name, from_file)}")
    try:
        import anthropic
    except ImportError:
        print("     (instala `anthropic` para probarla)")
        return
    try:
        client = anthropic.Anthropic()
        client.messages.create(model="claude-opus-5", max_tokens=8,
                               messages=[{"role": "user", "content": "ok"}])
        print("     OK: la API responde")
    except Exception as e:
        print(f"     FALLA: {type(e).__name__}: {str(e)[:110]}")


def check_pexels(from_file):
    name = "PEXELS_API_KEY"
    key = os.environ.get(name, "").strip()
    if key in PLACEHOLDERS:
        print(f"  {name:20} NO CONFIGURADA -> solo Wikimedia y degradados")
        return
    print(f"  {name:20} {len(key)} caracteres, desde {_origin(name, from_file)}")
    if len(key) < 20:
        print("     FALLA: demasiado corta. Una llave real trae ~56 caracteres.")
        print("     Casi seguro copiaste el texto de ejemplo en vez de la llave.")
        return
    import requests
    try:
        r = requests.get("https://api.pexels.com/videos/search",
                         params={"query": "city", "per_page": 1},
                         headers={"Authorization": key}, timeout=20)
        if r.status_code == 200:
            print(f"     OK: la API responde ({r.json().get('total_results', 0)} resultados)")
        elif r.status_code == 401:
            print("     FALLA: 401, la llave no es valida. Sacala de pexels.com/api/")
        else:
            print(f"     FALLA: HTTP {r.status_code}")
    except Exception as e:
        print(f"     FALLA: {type(e).__name__}: {str(e)[:110]}")


def main():
    from_file = load_dotenv()
    env_path = ROOT / ".env"
    print(f"\narchivo .env: {'encontrado' if env_path.exists() else 'no existe'} ({env_path})")
    if from_file:
        print(f"cargadas desde .env: {', '.join(from_file)}")
    print("\nLlaves:")
    check_anthropic(from_file)
    check_pexels(from_file)
    print("\nPara arreglarlo, crea un archivo .env en la raiz del proyecto con:")
    print("  ANTHROPIC_API_KEY=sk-ant-...")
    print("  PEXELS_API_KEY=...")
    print("Sin comillas y sin espacios alrededor del signo igual.\n")


if __name__ == "__main__":
    main()
