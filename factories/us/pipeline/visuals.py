"""Consigue la imagen o el video de cada escena.

Fuentes, en el orden de `visual_priority` (config.json):
  wikimedia    Fotos reales del lugar/tema. Gratis, SIN llave. Pide atribucion.
  pexels_video Video vertical de stock. Necesita PEXELS_API_KEY (gratis).
  pexels_photo Foto vertical de stock. Misma llave.
  local        Lo que pongas en assets/stock/
  gradient     Degradado animado generado por FFmpeg. Siempre funciona.
"""
import hashlib
import os
import random
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .util import ROOT, log

CACHE = ROOT / "cache" / "media"
STOCK = ROOT / "assets" / "stock"
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
PEXELS = "https://api.pexels.com"
COMMONS = "https://commons.wikimedia.org/w/api.php"
# Wikimedia pide identificarse. Pon un correo o URL tuya en WIKI_CONTACT si quieres.
UA = ("MexicoShortsBot/1.0 (+%s) python-requests"
      % os.environ.get("WIKI_CONTACT", "https://github.com/topics/faceless-video"))

# El CDN corta al primer rafagazo. Ancho estandar de miniatura + pausa creciente.
WIKI_THUMB_WIDTH = 1280
WIKI_TRIES_PER_SCENE = 3
_wiki = {"last": 0.0, "interval": 1.2}


def _wiki_throttle():
    wait = _wiki["interval"] - (time.monotonic() - _wiki["last"])
    if wait > 0:
        time.sleep(wait)
    _wiki["last"] = time.monotonic()


def _wiki_penalize():
    """Tras un 429, esperar mas entre peticiones en lo que resta de la corrida."""
    _wiki["interval"] = min(6.0, _wiki["interval"] * 1.8)


def _clean_url(url):
    """Quita el ?utm_source=... que agrega la API; el CDN lo trata como URL nueva."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


# Se apaga sola si Pexels contesta 401: no sirve seguir pegandole en cada escena.
_pexels_dead = [False]
PEXELS_KEY_MIN_LEN = 20


def _pexels_key():
    """Llave de Pexels, o cadena vacia si no sirve.

    Descarta los placeholders: mas de una vez alguien copia literal el
    `setx PEXELS_API_KEY "..."` del README y termina con la llave '...'.
    Una llave de Pexels real anda por los 56 caracteres.
    """
    if _pexels_dead[0]:
        return ""
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    return key if len(key) >= PEXELS_KEY_MIN_LEN else ""


def _download(url, suffix, headers=None, retries=1):
    import requests

    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / (hashlib.md5(url.encode()).hexdigest() + suffix)
    if dest.exists() and dest.stat().st_size > 1024:
        return dest

    for attempt in range(retries + 1):
        r = requests.get(url, timeout=90, stream=True, headers=headers or {})
        if r.status_code == 429 and attempt < retries:
            time.sleep(3.0 * (attempt + 1))
            continue
        r.raise_for_status()
        with open(dest, "wb") as f:
            for block in r.iter_content(1 << 16):
                f.write(block)
        return dest
    raise RuntimeError("429 after retrying")


# --------------------------------------------------------------------- Wikimedia

def _wiki_search(query, limit=12):
    """Busca fotos en Wikimedia Commons. No requiere llave."""
    import requests

    _wiki_throttle()
    r = requests.get(COMMONS, params={
        "action": "query", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrlimit": limit, "gsrnamespace": 6,
        "prop": "imageinfo", "iiprop": "url|size|extmetadata",
        "iiurlwidth": WIKI_THUMB_WIDTH, "format": "json",
    }, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()

    pages = (r.json().get("query") or {}).get("pages") or {}
    results = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        # Solo miniaturas: bajar el original dispara el limite de Wikimedia.
        url = info.get("thumburl")
        if not url or min(info.get("width", 0), info.get("height", 0)) < 500:
            continue
        url = _clean_url(url)
        meta = info.get("extmetadata") or {}

        def field(name):
            raw = (meta.get(name) or {}).get("value", "")
            return _strip_html(raw)[:120]

        results.append({
            "url": url,
            "title": page.get("title", "").replace("File:", ""),
            "license": field("LicenseShortName") or "ver Commons",
            "author": field("Artist") or "desconocido",
            "page": info.get("descriptionurl", ""),
        })
    return results


def _subject_variants(subject):
    """Commons exige que TODOS los terminos aparezcan, asi que un tema largo
    devuelve cero. Se prueba completo y luego recortado."""
    if not subject:
        return []
    stop = {"de", "del", "la", "las", "el", "los", "y", "en", "un", "una"}
    content = [w for w in subject.split() if w.lower() not in stop]
    variants = [subject]
    for size in (3, 2):
        if len(content) > size:
            variants.append(" ".join(content[:size]))
    seen, out = set(), []
    for v in variants:
        if v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def _strip_html(text):
    out, depth = [], 0
    for ch in text:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return " ".join("".join(out).split())


def _try_wikimedia(state, queries):
    for query in queries:
        if not query:
            continue
        if query not in state["wiki_cache"]:
            try:
                state["wiki_cache"][query] = _wiki_search(query)
            except Exception as e:
                log(f"Wikimedia failed on '{query}': {str(e)[:80]}")
                state["wiki_cache"][query] = []

        tries = 0
        for hit in state["wiki_cache"][query]:
            if hit["url"] in state["used"]:
                continue
            if tries >= WIKI_TRIES_PER_SCENE:
                break  # no insistir: cada intento fallido empeora el limite
            tries += 1
            state["used"].add(hit["url"])
            try:
                _wiki_throttle()
                path = _download(hit["url"], ".jpg", headers={"User-Agent": UA}, retries=2)
            except Exception as e:
                if "429" in str(e):
                    _wiki_penalize()
                log(f"could not download {hit['title'][:38]}: {str(e)[:60]}")
                continue
            return {
                "path": path, "kind": "image", "source": "wikimedia", "query": query,
                "attribution": {
                    "title": hit["title"], "author": hit["author"],
                    "license": hit["license"], "url": hit["page"],
                },
            }
    return None


# ------------------------------------------------------------------------ Pexels

def _pexels_get(path, params):
    import requests

    r = requests.get(f"{PEXELS}{path}", params=params,
                     headers={"Authorization": _pexels_key()}, timeout=30)
    if r.status_code == 401:
        _pexels_dead[0] = True
        raise RuntimeError("PEXELS_API_KEY is invalid; continuing without Pexels")
    r.raise_for_status()
    return r.json()


def _pick_video_file(files):
    """Prefiere vertical y al menos 1080 de alto, sin pasarse de peso."""
    vertical = [f for f in files if f.get("height", 0) >= f.get("width", 1)]
    pool = vertical or files
    good = [f for f in pool if f.get("height", 0) >= 1080] or pool
    good.sort(key=lambda f: f.get("height", 0))
    return good[0] if good else None


def _try_pexels_video(state, queries):
    if not _pexels_key():
        return None
    for query in queries:
        try:
            data = _pexels_get("/videos/search", {
                "query": query, "per_page": 10,
                "orientation": "portrait", "size": "medium",
            })
        except Exception as e:
            log(f"Pexels video failed on '{query}': {e}")
            continue
        for video in data.get("videos", []):
            chosen = _pick_video_file(video.get("video_files", []))
            if not chosen or chosen["link"] in state["used"]:
                continue
            state["used"].add(chosen["link"])
            return {"path": _download(chosen["link"], ".mp4"), "kind": "video",
                    "source": "pexels", "query": query, "attribution": None}
    return None


def _try_pexels_photo(state, queries):
    if not _pexels_key():
        return None
    for query in queries:
        try:
            data = _pexels_get("/v1/search", {
                "query": query, "per_page": 10, "orientation": "portrait",
            })
        except Exception as e:
            log(f"Pexels photo failed on '{query}': {e}")
            continue
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            link = src.get("large2x") or src.get("original")
            if not link or link in state["used"]:
                continue
            state["used"].add(link)
            return {"path": _download(link, ".jpg"), "kind": "image",
                    "source": "pexels", "query": query, "attribution": None}
    return None


# ------------------------------------------------------------------------- Local

def _try_local(state, _queries):
    if not STOCK.exists():
        return None
    usable = [p for p in STOCK.iterdir() if p.suffix.lower() in VIDEO_EXT | IMAGE_EXT]
    fresh = [p for p in usable if str(p) not in state["used"]] or usable
    if not fresh:
        return None
    pick = random.choice(fresh)
    state["used"].add(str(pick))
    return {"path": pick, "kind": "video" if pick.suffix.lower() in VIDEO_EXT else "image",
            "source": "local", "query": pick.name, "attribution": None}


SOURCES = {
    "wikimedia": _try_wikimedia,
    "pexels_video": _try_pexels_video,
    "pexels_photo": _try_pexels_photo,
    "local": _try_local,
}

DEFAULT_PRIORITY = ["wikimedia", "pexels_video", "pexels_photo", "local", "gradient"]


def fetch_for_timeline(timeline, cfg, subject=None):
    """Asigna un recurso visual a cada escena y devuelve la lista de assets."""
    # Humor and money need people and everyday scenes -> Pexels wins there.
    # Mysteries need the actual place -> Wikimedia wins there.
    priority = ((cfg.get("niche_visuals") or {}).get(cfg.get("niche"))
                or cfg.get("visual_priority") or DEFAULT_PRIORITY)
    # El tope existe para alternar foto real y video de stock. Sin llave de Pexels
    # no hay con que alternar, asi que se quita: mejor foto real que degradado.
    cap_con_pexels = int(cfg.get("wikimedia_max_per_video", 5))
    state = {"used": set(), "wiki_cache": {}}
    wiki_count = 0

    if "wikimedia" in priority:
        log(f"Wikimedia Commons (no key needed), subject: {subject or 'n/a'}")
    if not _pexels_key() and "pexels_video" in priority:
        log("no PEXELS_API_KEY -> skipping stock video")

    assets = []
    for sc in timeline:
        kws = sc.get("keywords", [])[:3]
        asset = None
        for name in priority:
            if name == "gradient":
                break
            if name == "wikimedia":
                # Solo el tema, nunca las keywords en ingles: buscar "empty boat"
                # en Commons trae un lago de la India, no Xochimilco.
                # Se revisa por escena, no una sola vez: si Pexels se cae a media
                # corrida, las escenas que faltan vuelven a Wikimedia.
                cap = cap_con_pexels if _pexels_key() else 10 ** 6
                if wiki_count >= cap or not subject:
                    continue
                queries = _subject_variants(subject)
            else:
                queries = kws or ([subject] if subject else [])
            asset = SOURCES[name](state, queries)
            if asset:
                if name == "wikimedia":
                    wiki_count += 1
                break

        if not asset:
            asset = {"path": None, "kind": "gradient", "source": "gradient",
                     "query": "gradient", "attribution": None}
        assets.append(asset)
        log(f"scene {sc['index'] + 1}: {asset['source']}/{asset['kind']} <- {asset['query']}")

    return assets
