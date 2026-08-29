"""Script generation through the Gemini API (Google AI Studio).

Plain REST on purpose: no extra SDK to install, nothing that breaks when Google
renames a package. The model name is *resolved* at call time rather than
hardcoded, because Google retires and renames model ids often and a stale id in
a config file is the most common way this stops working.
"""
import json

from .util import log

BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-2.5-pro"
_resolved = {}


def _headers(key):
    return {"x-goog-api-key": key, "Content-Type": "application/json"}


def list_models(key):
    """Model ids that can actually do generateContent, best-looking first."""
    import requests

    r = requests.get(f"{BASE}/models", headers=_headers(key), timeout=30)
    r.raise_for_status()
    names = []
    for m in r.json().get("models", []):
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        names.append(m["name"].split("/")[-1])

    def rank(name):
        # Prefer pro over flash, newer version numbers, and non-preview builds.
        version = 0.0
        for token in name.replace("-", " ").split():
            try:
                version = max(version, float(token))
            except ValueError:
                pass
        return (
            0 if "pro" in name else 1,
            0 if not any(t in name for t in ("preview", "exp", "latest")) else 1,
            -version,
            name,
        )

    return sorted(names, key=rank)


def resolve_model(key, preferred=None):
    """Use the configured model if the API really has it; otherwise pick the best.

    Cached per key+preference so a batch of ten videos costs one lookup.
    """
    cache_key = (key[-8:], preferred)
    if cache_key in _resolved:
        return _resolved[cache_key]

    want = preferred or DEFAULT_MODEL
    try:
        available = list_models(key)
    except Exception as e:
        log(f"could not list Gemini models ({type(e).__name__}); trying {want}")
        return want

    if want in available:
        chosen = want
    else:
        chosen = next((m for m in available if "pro" in m), None) or (
            available[0] if available else want)
        log(f"model '{want}' not available -> using '{chosen}'")

    _resolved[cache_key] = chosen
    return chosen


def to_gemini_schema(schema):
    """JSON Schema -> the OpenAPI subset Gemini accepts.

    Two real differences: types are uppercase, and `additionalProperties` is
    rejected outright rather than ignored.
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
    """One structured-output call. Returns the parsed object."""
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
    if r.status_code == 400 and "API key" in r.text:
        raise RuntimeError("GEMINI_API_KEY rejected. Get one at aistudio.google.com/apikey")
    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:200]}")

    data = r.json()
    candidates = data.get("candidates") or []
    if not candidates:
        blocked = (data.get("promptFeedback") or {}).get("blockReason")
        raise RuntimeError(f"Gemini returned nothing (blockReason={blocked})")

    cand = candidates[0]
    reason = cand.get("finishReason")
    if reason in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
        raise RuntimeError(f"Gemini refused this topic (finishReason={reason})")

    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError(f"Gemini returned empty text (finishReason={reason})")
    if reason == "MAX_TOKENS":
        raise RuntimeError("Gemini hit the token cap; the JSON is cut off. "
                           "Lower scene_count or raise max_tokens.")
    return json.loads(text)


def check_key(key):
    """Used by the GUI's Test button. Returns (ok, message)."""
    if not key or len(key) < 20:
        return False, "Key looks too short. An AI Studio key is around 39 characters."
    try:
        models = list_models(key)
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:120]}"
    if not models:
        return False, "The key works but no model supports generateContent."
    return True, f"OK - {len(models)} models available, best match: {models[0]}"
