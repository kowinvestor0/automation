import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

def _roots():
    """Where the editable files live, and where the bundled defaults live.

    Frozen in an exe, PyInstaller unpacks read-only copies into a temp folder
    that is deleted on exit. Anything the user edits or that we write out has to
    sit next to the exe instead, or their settings vanish when they close it.
    """
    # The hub runs a factory out of a workspace folder the user chose at install
    # time and passes it in. Honour that first: an installed copy that wrote next
    # to its own exe would be trying to write into Program Files.
    override = os.environ.get("FACTORY_ROOT", "").strip()
    if getattr(sys, "frozen", False):
        bundle = Path(sys._MEIPASS)
        return Path(override or Path(sys.executable).resolve().parent), bundle
    here = Path(__file__).resolve().parent.parent
    return Path(override) if override else here, here


ROOT, BUNDLE = _roots()

# Files the user is meant to open and edit. Restored next to the exe if missing.
SEEDED = ("config.json", "topics.json")


def bootstrap():
    """First run of the exe: lay the editable files out next to it."""
    if ROOT == BUNDLE:
        return
    for name in SEEDED:
        target = ROOT / name
        source = BUNDLE / name
        if not target.exists() and source.exists():
            target.write_bytes(source.read_bytes())
    for folder in ("assets/fonts", "assets/music", "assets/stock", "output", "cache"):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    fonts_src, fonts_dst = BUNDLE / "assets" / "fonts", ROOT / "assets" / "fonts"
    if fonts_src.exists():
        for font in fonts_src.iterdir():
            if not (fonts_dst / font.name).exists():
                (fonts_dst / font.name).write_bytes(font.read_bytes())
    use_bundled_ffmpeg()


def use_bundled_ffmpeg():
    """If ffmpeg.exe shipped inside the build, make plain `ffmpeg` calls find it.

    Putting the folder on PATH means none of the pipeline has to know whether
    FFmpeg came from the system or from the bundle.
    """
    for folder in (BUNDLE / "ffmpeg", ROOT / "ffmpeg"):
        if (folder / "ffmpeg.exe").exists() or (folder / "ffmpeg").exists():
            os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")
            return folder
    return None


def find_ffmpeg():
    """Absolute path to a usable ffmpeg, or None. For the GUI's startup check."""
    import shutil

    use_bundled_ffmpeg()
    return shutil.which("ffmpeg")

# La consola de Windows usa cp1252 por defecto y rompe los acentos del espanol.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def load_dotenv(path=None):
    """Lee las llaves de un archivo .env junto al proyecto.

    `setx` en Windows se equivoca facil (comillas, terminal sin reiniciar, valores
    de relleno tipo "..."), asi que el archivo manda: es lo que uno puede abrir y
    verificar a simple vista. Lo ya definido en el entorno real se respeta, salvo
    que sea un valor de relleno.
    """
    env_file = Path(path) if path else ROOT / ".env"
    if not env_file.exists():
        return {}

    loaded = {}
    for raw in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or not value or value in {"...", "your-key-here", "xxx"}:
            continue
        current = os.environ.get(key, "").strip()
        # Un valor real ya puesto en el entorno gana; uno de relleno, no.
        if current and current not in {"...", "your-key-here", "xxx"}:
            continue
        os.environ[key] = value
        loaded[key] = value
    return loaded


load_dotenv()


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def slugify(text, maxlen=60):
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:maxlen] or "video"


def log(msg):
    print(f"  {msg}", flush=True)


def step(msg):
    print(f"\n>> {msg}", flush=True)


def run(cmd, cwd=None, quiet=True):
    """Ejecuta un comando; levanta RuntimeError con el stderr real si falla."""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout or "").splitlines()[-25:])
        raise RuntimeError(f"Comando fallo ({proc.returncode}):\n{' '.join(cmd)}\n{tail}")
    if not quiet and proc.stdout:
        print(proc.stdout)
    return proc.stdout or ""


def ffprobe_duration(path):
    out = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def require_binaries():
    missing = []
    for exe in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run([exe, "-version"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=True)
        except Exception:
            missing.append(exe)
    if missing:
        print(f"ERROR: falta {', '.join(missing)} en el PATH. Instala FFmpeg.", file=sys.stderr)
        sys.exit(1)
