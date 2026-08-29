"""Push a line to the user's phone when a run finishes.

GitHub can already email on failure, but it says nothing on success and nothing
about what was actually made. A Telegram bot is the cheapest way to get "6
videos, scheduled for tomorrow 09:00" onto a lock screen, and it needs no app
install beyond Telegram itself.

Entirely optional: with no bot token configured every function here is a no-op
that returns False. A notification failing must never fail a run.
"""
import json
import urllib.parse
import urllib.request

from hub.settings import secret

API = "https://api.telegram.org/bot{token}/sendMessage"
TIMEOUT = 20
LIMIT = 3900          # Telegram caps a message at 4096 characters


def configured(cfg=None):
    return bool(secret("TELEGRAM_BOT_TOKEN", cfg) and secret("TELEGRAM_CHAT_ID", cfg))


def send(text, cfg=None, log=print):
    """Returns True if Telegram accepted the message."""
    token = secret("TELEGRAM_BOT_TOKEN", cfg)
    chat = secret("TELEGRAM_CHAT_ID", cfg)
    if not token or not chat:
        return False

    body = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text[:LIMIT],
        "disable_web_page_preview": "true",
    }).encode()

    request = urllib.request.Request(API.format(token=token), data=body)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except Exception as e:
        log(f"telegram: {type(e).__name__}: {str(e)[:140]}")
        return False

    if not payload.get("ok"):
        log(f"telegram refused the message: {str(payload)[:160]}")
        return False
    return True


def announce(payload, settings, log=print):
    """Send the end-of-run summary, honouring the on_success / on_failure switches."""
    rules = settings.get("notify") or {}
    if not rules.get("telegram", True):
        return False
    failed = payload.get("status") in ("failed", "partial")
    if failed and not rules.get("on_failure", True):
        return False
    if not failed and not rules.get("on_success", True):
        return False

    from hub import status
    return send(status.short(payload), cfg=settings, log=log)


def test(cfg=None):
    """Backs the GUI's Test button. Returns (ok, message)."""
    if not configured(cfg):
        return False, "Bot token or chat id is empty."
    ok = send("Automation Hub: test message. If you can read this, "
              "run notifications will arrive here.", cfg=cfg, log=lambda *_: None)
    return (True, "Sent - check Telegram.") if ok else (
        False, "Telegram refused it. Check the token and the chat id.")
