"""Guiones por la API de Gemini (Google AI Studio).

REST pelon a proposito: ni un SDK extra que instalar, ni algo que se rompa
cuando Google le cambie el nombre al paquete. El id del modelo se *resuelve* al
momento de llamar en vez de venir escrito a mano, porque Google retira y renombra
modelos seguido y un id viejo en el config es la forma mas comun de que esto
deje de jalar.
"""
import json

from .util import log

BASE = "https://generativelanguage.googleapis.com/v1beta"

# Flash y no pro: la capa gratuita de AI Studio cubre flash, y esta fabrica
# existe para salir en cero pesos. Quien quiera pro lo pone en config.json.
DEFAULT_MODEL = "gemini-2.5-flash"

_resolved = {}


def _headers(key):
    return {"x-goog-api-key": key, "Content-Type": "application/json"}


def _family(name):
    """'flash-lite', 'flash' o 'pro'. Aqui la familia es el costo, nada mas."""
    for tier in ("flash-lite", "flash", "pro"):
        if tier in name:
            return tier
    return ""


def _rank(name):
    # Version mas nueva primero, y los builds estables antes que preview/exp,
    # que desaparecen sin aviso a media semana.
    version = 0.0
    for token in name.replace("-", " ").split():
        try:
            version = max(version, float(token))
        except ValueError:
            pass
    return (
        0 if not any(t in name for t in ("preview", "exp", "latest")) else 1,
        -version,
        name,
    )


def list_models(key):
    """Modelos que esa llave puede usar con generateContent, el mejor primero."""
    import requests

    r = requests.get(f"{BASE}/models", headers=_headers(key), timeout=30)
    if r.status_code in (400, 403):
        raise RuntimeError(f"llave rechazada por Google ({r.status_code})")
    r.raise_for_status()

    nombres = []
    for m in r.json().get("models", []):
        if "generateContent" not in (m.get("supportedGenerationMethods") or []):
            continue
        nombres.append(m["name"].split("/")[-1])
    return sorted(nombres, key=_rank)


def resolve_model(key, preferred=None):
    """Usa el modelo del config si la API de verdad lo tiene; si no, elige otro.

    Se cachea por llave+preferencia, asi una tanda de diez videos cuesta una sola
    consulta.
    """
    cache_key = (key[-8:], preferred)
    if cache_key in _resolved:
        return _resolved[cache_key]

    quiero = preferred or DEFAULT_MODEL
    try:
        disponibles = list_models(key)
    except Exception as e:
        log(f"no pude listar los modelos de Gemini ({type(e).__name__}); pruebo con {quiero}")
        return quiero

    if quiero in disponibles:
        elegido = quiero
    else:
        # El reemplazo se busca primero en la misma familia: brincar de flash a
        # pro sin avisar saca la corrida de la capa gratuita y empieza a cobrar.
        familia = _family(quiero)
        elegido = (next((m for m in disponibles if _family(m) == familia), None)
                   or (disponibles[0] if disponibles else quiero))
        log(f"el modelo '{quiero}' no esta disponible -> uso '{elegido}'")

    _resolved[cache_key] = elegido
    return elegido


def to_gemini_schema(schema):
    """JSON Schema -> el subconjunto de OpenAPI que acepta Gemini.

    Dos diferencias de verdad: los tipos van en mayusculas, y
    `additionalProperties` no lo ignora, lo rechaza con un 400.
    """
    if not isinstance(schema, dict):
        return schema

    out = {}
    for key, value in schema.items():
        if key == "additionalProperties":
            continue
        if key == "type" and isinstance(value, str):
            out["type"] = value.upper()
        elif key == "properties":
            out["properties"] = {k: to_gemini_schema(v) for k, v in value.items()}
        elif key == "items":
            out["items"] = to_gemini_schema(value)
        else:
            out[key] = value
    return out


def generate_json(key, system, prompt, schema, model=None, max_tokens=8192):
    """Una llamada con salida estructurada. Devuelve el objeto ya parseado."""
    import requests

    model_id = resolve_model(key, model)
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": to_gemini_schema(schema),
            "temperature": 1.0,
            "maxOutputTokens": max_tokens,
        },
    }

    r = requests.post(f"{BASE}/models/{model_id}:generateContent",
                      headers=_headers(key), json=body, timeout=180)
    if r.status_code == 429:
        raise RuntimeError("cuota de la capa gratuita agotada (429); intenta mas tarde")
    if r.status_code == 400 and "API key" in r.text:
        raise RuntimeError("GEMINI_API_KEY rechazada. Saca una en aistudio.google.com/apikey")
    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:200]}")

    data = r.json()
    candidatos = data.get("candidates") or []
    if not candidatos:
        motivo = (data.get("promptFeedback") or {}).get("blockReason")
        raise RuntimeError(f"Gemini no devolvio nada (blockReason={motivo})")

    cand = candidatos[0]
    fin = cand.get("finishReason")
    if fin in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
        raise RuntimeError(f"Gemini bloqueo este tema (finishReason={fin})")

    partes = (cand.get("content") or {}).get("parts") or []
    texto = "".join(p.get("text", "") for p in partes).strip()
    if not texto:
        raise RuntimeError(f"Gemini devolvio texto vacio (finishReason={fin})")
    if fin == "MAX_TOKENS":
        raise RuntimeError("Gemini topo el limite de tokens y el JSON quedo cortado. "
                           "Baja scene_count o sube max_tokens.")
    return json.loads(texto)


def check_key(key):
    """Para el boton de probar del panel. Devuelve (ok, mensaje)."""
    if not key or len(key) < 20:
        return False, "La llave se ve muy corta. Una de AI Studio trae unos 39 caracteres."
    try:
        modelos = list_models(key)
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:120]}"
    if not modelos:
        return False, "La llave sirve pero ningun modelo soporta generateContent."
    return True, f"OK - {len(modelos)} modelos disponibles, el mejor: {modelos[0]}"
