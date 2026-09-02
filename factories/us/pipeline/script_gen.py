"""Builds the video script.

Primary path: Claude API (claude-opus-5) -> a fresh script every run.
Fallback path: local `topics.json` bank -> works with no API key at all.
The wording of the prompts lives in `prompts.py`.
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


def build_prompt(cfg, topic=None, avoid=None):
    """The user-side brief. Shared by every provider so they get the same job."""
    niche = cfg.get("niche", "mysteries")
    n = int(cfg.get("scene_count", 7))
    secs = int(cfg.get("target_seconds", 45))

    if topic:
        brief = f"Write the script about exactly this topic: {topic}"
    else:
        brief = (f"Pick your own topic from: {NICHES.get(niche, niche)}. "
                 f"Make it specific, not generic.")
    if avoid:
        brief += "\n\nDo NOT repeat any of these already-used topics:\n- " + \
                 "\n- ".join(avoid[-40:])

    return (
        f"{brief}\n\n"
        f"Format: {n} scenes, about {secs} seconds of spoken audio in total "
        f"(roughly {int(secs * 2.6)} words all together)."
        + NICHE_EXTRA.get(niche, "")
    )


def generate_with_claude(cfg, topic=None, avoid=None):
    import anthropic

    client = anthropic.Anthropic()
    prompt = build_prompt(cfg, topic, avoid)
    model = cfg.get("model", "claude-opus-5")
    log(f"asking {model} for a script...")
    data = _extract_json(_call_claude(client, model, prompt))
    data["source"] = "claude"
    data["id"] = slugify(data.get("topic") or data.get("title", "video"))
    return data


def generate_with_gemini(cfg, topic=None, avoid=None):
    from . import gemini

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    prompt = build_prompt(cfg, topic, avoid)
    model = cfg.get("gemini_model") or gemini.DEFAULT_MODEL
    log(f"asking Gemini ({model}) for a script...")
    data = gemini.generate_json(key.strip(), SYSTEM, prompt, SCHEMA, model=model)
    data["source"] = "gemini"
    data["id"] = slugify(data.get("topic") or data.get("title", "video"))
    return data


def _forget_used(topic_ids):
    """Drop these from the used list so the next cycle can pick them again."""
    state = _load_state()
    drop = set(topic_ids)
    state["used_topics"] = [t for t in state.get("used_topics", []) if t not in drop]
    save_json(STATE_PATH, state)

def generate_from_bank(topic_id=None, niche=None):
    bank = load_json(ROOT / "topics.json", []) or []
    if not bank:
        raise RuntimeError("topics.json esta vacio y no hay ANTHROPIC_API_KEY")

    if topic_id:
        item = next((t for t in bank if t["id"] == topic_id), None)
        if not item:
            raise RuntimeError(f"Tema '{topic_id}' no existe en topics.json")
    else:
        if niche:
            bank = [t for t in bank if t.get("niche", "mysteries") == niche] or bank
        used = set(_load_state().get("used_topics", []))
        pool = [t for t in bank if t["id"] not in used]
        if not pool:
            # The niche is used up. Start a clean cycle instead of drawing at
            # random from everything - random reuse can repeat inside a single
            # run, which puts the same clip on two accounts at once.
            log(f"bank exhausted for '{niche or 'all'}', starting a new cycle")
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


def _has_gemini():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    return len(key.strip()) >= 20


def _has_claude():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def available_providers():
    """What this machine can actually use right now, best first."""
    out = []
    if _has_gemini():
        out.append("gemini")
    if _has_claude():
        out.append("claude")
    out.append("bank")
    return out


def build_script(cfg, topic=None, force_bank=False):
    """Writes the script with whatever provider is configured and reachable.

    `provider` in config.json: "auto" | "gemini" | "claude" | "bank".
    Auto prefers Gemini because its free tier covers this workload; any provider
    that errors falls through to the next one rather than killing the run.
    """
    provider = "bank" if force_bank else (cfg.get("provider") or "auto")

    if provider == "auto":
        order = available_providers()
    elif provider == "bank":
        order = ["bank"]
    else:
        order = [provider, "bank"]

    for name in order:
        if name == "bank":
            break
        if name == "gemini" and not _has_gemini():
            log("no GEMINI_API_KEY -> skipping Gemini")
            continue
        if name == "claude" and not _has_claude():
            log("no ANTHROPIC_API_KEY -> skipping Claude")
            continue
        try:
            fn = generate_with_gemini if name == "gemini" else generate_with_claude
            data = fn(cfg, topic=topic, avoid=_load_state().get("used_topics", []))
            _mark_used(data["id"])
            return data
        except Exception as e:
            log(f"{name} failed ({type(e).__name__}: {str(e)[:140]})")

    log("using the local topics.json bank")
    data = generate_from_bank(topic_id=topic, niche=cfg.get("niche"))
    _mark_used(data["id"])
    return data
