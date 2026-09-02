"""Genera el guion del video.

Proveedores, en el orden de `llm_priority` (config.json):
  gemini   Google AI Studio. Tiene capa gratuita real -> la opcion de cero costo.
  claude   Anthropic. Sin capa gratuita, pero sale en centavos por video.
  bank     `topics.json`. Sin llaves, sin internet para el guion.

Cae al siguiente si el anterior no tiene llave o falla. El texto de los prompts
vive en `prompts.py`, que es el archivo que se edita para cambiar el tono.
"""
import json
import os
import random

from .prompts import NICHES, NICHE_EXTRA, SYSTEM
from .util import ROOT, load_json, log, save_json, slugify

STATE_PATH = ROOT / "state.json"

SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "title": {"type": "string"},
        "subject": {"type": "string"},
        "description": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "keywords"],
                "additionalProperties": False,
            },
        },
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["topic", "title", "subject", "description", "scenes", "hashtags"],
    "additionalProperties": False,
}


def _load_state():
    return load_json(STATE_PATH, {"used_topics": []}) or {"used_topics": []}


def _mark_used(topic_id):
    state = _load_state()
    used = state.get("used_topics", [])
    if topic_id not in used:
        used.append(topic_id)
    state["used_topics"] = used[-500:]
    save_json(STATE_PATH, state)


def _brief(cfg, topic=None, avoid=None):
    """El encargo para el modelo. El mismo para todos los proveedores."""
    niche = cfg.get("niche", "misterios")
    n = int(cfg.get("scene_count", 7))
    secs = int(cfg.get("target_seconds", 45))

    if topic:
        brief = f"Escribe el guion sobre este tema exacto: {topic}"
    else:
        brief = (f"Elige tu un tema de: {NICHES.get(niche, niche)}. "
                 f"Que sea especifico, no generico.")
    if avoid:
        brief += "\n\nNO repitas ninguno de estos temas ya usados:\n- " + "\n- ".join(avoid[-40:])

    return (
        f"{brief}\n\n"
        f"Formato: {n} escenas, duracion total hablada de unos {secs} segundos "
        f"(aprox. {int(secs * 2.6)} palabras en total)."
        + NICHE_EXTRA.get(niche, "")
    )


# --------------------------------------------------------------------- Claude

def _extract_json(response):
    if getattr(response, "stop_reason", None) == "refusal":
        detail = getattr(response, "stop_details", None)
        raise RuntimeError(f"Claude rechazo la peticion (stop_reason=refusal): {detail}")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise RuntimeError("Claude no devolvio texto")
    return json.loads(text)


def _call_claude(client, model, prompt):
    kwargs = dict(
        model=model,
        max_tokens=8000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    # Fallback del lado del servidor: si un clasificador rechaza, otro modelo responde.
    try:
        return client.beta.messages.create(
            betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
        )
    except Exception as e:
        log(f"beta/fallbacks no disponible ({type(e).__name__}), uso la ruta estandar")
        return client.messages.create(**kwargs)


def claude_key():
    key = (os.environ.get("ANTHROPIC_API_KEY")
           or os.environ.get("ANTHROPIC_AUTH_TOKEN") or "").strip()
    return key if len(key) >= 20 else ""


def generate_with_claude(cfg, topic=None, avoid=None):
    import anthropic

    client = anthropic.Anthropic()
    model = cfg.get("model", "claude-opus-5")
    log(f"pidiendo guion a {model}...")
    data = _extract_json(_call_claude(client, model, _brief(cfg, topic, avoid)))
    data["source"] = "claude"
    data["id"] = slugify(data.get("topic") or data.get("title", "video"))
    return data


# --------------------------------------------------------------------- Gemini

def gemini_key():
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        key = os.environ.get(name, "").strip()
        # Las llaves de AI Studio empiezan con AIza y rondan los 39 caracteres.
        if len(key) >= 20:
            return key
    return ""


def gemini_models(key=None):
    """Lista los modelos que esa llave puede usar. Sirve para diagnosticar."""
    from . import gemini

    key = key or gemini_key()
    if not key:
        raise RuntimeError("no hay GEMINI_API_KEY")
    return gemini.list_models(key)


def generate_with_gemini(cfg, topic=None, avoid=None):
    from . import gemini

    key = gemini_key()
    if not key:
        raise RuntimeError("no hay GEMINI_API_KEY")
    model = cfg.get("gemini_model") or gemini.DEFAULT_MODEL
    log(f"pidiendo guion a Gemini ({model})...")
    data = gemini.generate_json(key, SYSTEM, _brief(cfg, topic, avoid), SCHEMA, model=model)
    data["source"] = "gemini"
    data["id"] = slugify(data.get("topic") or data.get("title", "video"))
    return data


# ----------------------------------------------------------------- banco local

def _forget_used(topic_ids):
    """Los saca de la lista de usados para que el proximo ciclo los tome otra vez."""
    state = _load_state()
    drop = set(topic_ids)
    state["used_topics"] = [t for t in state.get("used_topics", []) if t not in drop]
    save_json(STATE_PATH, state)

def generate_from_bank(topic_id=None, niche=None):
    bank = load_json(ROOT / "topics.json", []) or []
    if not bank:
        raise RuntimeError("topics.json esta vacio y no hay ninguna llave configurada")

    if topic_id:
        item = next((t for t in bank if t["id"] == topic_id), None)
        if not item:
            raise RuntimeError(f"Tema '{topic_id}' no existe en topics.json")
    else:
        if niche:
            bank = [t for t in bank if t.get("niche", "misterios") == niche] or bank
        used = set(_load_state().get("used_topics", []))
        pool = [t for t in bank if t["id"] not in used]
        if not pool:
            # El nicho se agoto. Empezar un ciclo limpio en vez de sortear entre
            # todo: repetir al azar puede dar el mismo tema dos veces en una
            # sola corrida, y eso pone el mismo clip en dos cuentas a la vez.
            log(f"banco agotado para '{niche or 'todos'}', empiezo otro ciclo")
            _forget_used([t["id"] for t in bank])
            pool = list(bank)
        item = random.choice(pool)

    return {
        "id": item["id"],
        "topic": item["title"],
        "title": item["title"],
        "subject": item.get("subject", item["title"]),
        "description": item.get("description", item["title"]),
        "scenes": item["scenes"],
        "hashtags": item.get("hashtags", []),
        "source": "bank",
    }


PROVIDERS = {
    "gemini": (gemini_key, generate_with_gemini, "GEMINI_API_KEY"),
    "claude": (claude_key, generate_with_claude, "ANTHROPIC_API_KEY"),
}


def available_providers():
    """Lo que esta maquina puede usar ahorita, en el orden de `llm_priority`."""
    out = [n for n in ("gemini", "claude") if PROVIDERS[n][0]()]
    return out + ["bank"]


def build_script(cfg, topic=None, force_bank=False):
    """Prueba los proveedores de `llm_priority` en orden y cae al banco local."""
    orden = [] if force_bank else (cfg.get("llm_priority") or ["gemini", "claude"])

    for nombre in orden:
        if nombre == "bank":
            break
        if nombre not in PROVIDERS:
            log(f"proveedor '{nombre}' desconocido, lo salto")
            continue
        hay_llave, generar, var = PROVIDERS[nombre]
        if not hay_llave():
            log(f"sin {var} -> me salto {nombre}")
            continue
        try:
            data = generar(cfg, topic=topic,
                           avoid=_load_state().get("used_topics", []))
            _mark_used(data["id"])
            return data
        except Exception as e:
            log(f"{nombre} fallo ({type(e).__name__}: {str(e)[:140]})")

    if not force_bank:
        log("ningun proveedor disponible -> uso el banco local topics.json")
    data = generate_from_bank(topic_id=topic, niche=cfg.get("niche"))
    _mark_used(data["id"])
    return data
