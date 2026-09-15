"""Standard OpenAI Chat Completions API fallback for structured story generation."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import requests

from core.config_manager import get_api_key, load_config

logger = logging.getLogger(__name__)
CHAT_URL = "https://api.openai.com/v1/chat/completions"


def generate_json(prompt: str, *, purpose: str) -> Optional[Dict[str, Any]]:
    """Ask GPT for JSON only. Returns None when no OpenAI key is configured."""
    api_key = get_api_key("openai_api_key")
    if not api_key:
        return None

    model = os.environ.get("OPENAI_MODEL") or load_config().get("generation", {}).get("openai_model", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return valid JSON only. Do not invent sources or include markdown. "
                    "The content must be factual, safe for all audiences, and suitable for a short documentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    try:
        response = requests.post(
            CHAT_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=45,
        )
        if response.status_code >= 400:
            logger.warning("OpenAI fallback for %s returned HTTP %s: %s", purpose, response.status_code, response.text[:120])
            return None
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return None
        content = choices[0].get("message", {}).get("content", "")
        return json.loads(content) if content else None
    except Exception as exc:
        logger.warning("OpenAI fallback for %s failed: %s", purpose, exc)
        return None
