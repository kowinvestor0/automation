"""Push a finished video into Planly and put it on the calendar.

Flow per video:
    media/start-upload  -> mediaId + a presigned S3 URL
    PUT the file        -> straight to S3, not through Planly
    media/finish-upload -> Planly ingests it, returns contentUri
    schedules/create    -> one entry per channel, at the next free slot

This is the part that reaches the outside world, so it stays off until
`planly.enabled` is true in config.json, and `planly.dry_run` walks the whole
flow (upload included) without ever creating the schedule.
"""
import datetime as dt
import os

from .util import ROOT, load_json, log, save_json

BASE = "https://app.planly.com/api/v2"
STATE_PATH = ROOT / "state.json"
TIMEOUT = 120


class PlanlyError(RuntimeError):
    pass


def _headers(key):
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _post(key, path, body):
    import requests

    r = requests.post(f"{BASE}{path}", headers=_headers(key), json=body, timeout=TIMEOUT)
    if r.status_code == 401:
        raise PlanlyError("PLANLY_API_KEY rejected. Settings > Security in Planly.")
    if r.status_code >= 400:
        raise PlanlyError(f"{path} -> HTTP {r.status_code}: {r.text[:220]}")
    data = r.json()
    # Planly answers 200 with an `error` field rather than an HTTP error code.
    if isinstance(data, dict) and data.get("error"):
        raise PlanlyError(f"{path} -> {data['error']}")
    return data


# ----------------------------------------------------------------- discovery

def list_teams(key):
    data = _post(key, "/teams/list", {})
    return data.get("data") or []


def list_channels(key, team_id):
    data = _post(key, "/channels/list", {"team_id": team_id})
    return data.get("data") or []


def check_key(key):
    """Used by the GUI's Test button. Returns (ok, message)."""
    if not key or len(key.strip()) < 16:
        return False, "Key looks too short."
    try:
        teams = list_teams(key.strip())
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:130]}"
    if not teams:
        return False, "Key works but the account has no teams."
    name = teams[0].get("name") or teams[0].get("id")
    return True, f"OK - {len(teams)} team(s), first: {name}"


# -------------------------------------------------------------------- upload

def upload_media(key, team_id, path):
    """Three-step upload. Returns the mediaId to attach to a schedule."""
    import requests

    path = str(path)
    size = os.path.getsize(path)
    name = os.path.basename(path)

    start = _post(key, "/media/start-upload", {
        "teamId": team_id,
        "contentLength": size,
        "contentType": "video/mp4",
        "fileName": name,
    })
    media_id = start.get("mediaId")
    url = start.get("uploadUrl")
    if not media_id or not url:
        raise PlanlyError(f"start-upload gave no upload target: {str(start)[:200]}")

    # Send back exactly the headers Planly signed the URL with; S3 rejects the
    # PUT if Content-Type or Content-Length differ from the signature.
    put_headers = start.get("headers") or {
        "Content-Type": "video/mp4", "Content-Length": str(size),
    }
    with open(path, "rb") as f:
        r = requests.put(url, data=f, headers=put_headers, timeout=600)
    if r.status_code >= 400:
        raise PlanlyError(f"S3 upload failed: HTTP {r.status_code} {r.text[:200]}")

    done = _post(key, "/media/finish-upload", {"mediaId": media_id})
    info = done.get("data") or {}
    res = info.get("resolution") or {}
    log(f"uploaded to Planly: {size / (1 << 20):.1f} MB, "
        f"{res.get('width')}x{res.get('height')}, id {media_id[:8]}")
    return media_id


# ------------------------------------------------------------------ schedule

def _tz(cfg):
    """Offset in hours from the config, e.g. 7 for Vietnam."""
    return dt.timezone(dt.timedelta(hours=float(cfg.get("timezone_offset", 0))))


def _taken():
    state = load_json(STATE_PATH, {}) or {}
    return set(state.get("planly_scheduled", []))


def _remember(iso):
    state = load_json(STATE_PATH, {}) or {}
    used = state.get("planly_scheduled", [])
    used.append(iso)
    state["planly_scheduled"] = used[-400:]
    save_json(STATE_PATH, state)


def next_slot(cfg, now=None):
    """First posting slot that is far enough away and not already booked.

    Slots are local wall-clock times ("09:00"), so the calendar reads the way
    the user thinks about it; the value sent to Planly is UTC.
    """
    tz = _tz(cfg)
    now = now or dt.datetime.now(tz)
    lead = dt.timedelta(minutes=int(cfg.get("lead_minutes", 30)))
    slots = cfg.get("slots") or ["09:00", "13:00", "18:00"]
    taken = _taken()

    for day in range(0, 60):
        date = (now + dt.timedelta(days=day)).date()
        for hhmm in sorted(slots):
            hour, _, minute = hhmm.partition(":")
            when = dt.datetime(date.year, date.month, date.day,
                               int(hour), int(minute or 0), tzinfo=tz)
            if when < now + lead:
                continue
            iso = when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            if iso in taken:
                continue
            return iso
    raise PlanlyError("No free slot in the next 60 days. Add more `slots`.")


def _options_for(channel, meta, cfg):
    """Per-network extras. Defaults stay empty; YouTube needs a real title."""
    network = (channel.get("social_network") or "").lower()
    configured = (cfg.get("channel_options") or {})
    options = dict(configured.get(channel["id"]) or configured.get(network) or {})
    if "youtube" in network:
        options.setdefault("title", (meta.get("title") or "")[:95])
    return options


def publish(video_path, meta, cfg, key):
    """Upload the video and schedule it on every configured channel.

    Returns a dict describing what happened, for meta.json.
    """
    team_id = cfg.get("team_id")
    if not team_id:
        teams = list_teams(key)
        if not teams:
            raise PlanlyError("No teams on this Planly account.")
        team_id = teams[0]["id"]
        log(f"no team_id set, using '{teams[0].get('name', team_id)}'")

    channels = list_channels(key, team_id)
    wanted = cfg.get("channels") or []
    if wanted and wanted != ["all"]:
        chosen = [c for c in channels if c["id"] in wanted]
        missing = set(wanted) - {c["id"] for c in chosen}
        if missing:
            log(f"channel id(s) not on this account: {', '.join(sorted(missing))}")
    else:
        chosen = channels
    if not chosen:
        raise PlanlyError("No Planly channels to post to. Connect one, or fix "
                          "`planly.channels` in config.json.")

    media_id = upload_media(key, team_id, video_path)
    publish_on = next_slot(cfg)

    caption = (meta.get("description") or meta.get("title") or "").strip()
    schedules = [{
        "channelId": c["id"],
        "publishOn": publish_on,
        "content": caption,
        "media": [{"id": media_id, "options": {}}],
        "options": _options_for(c, meta, cfg),
    } for c in chosen]

    names = ", ".join(f"{c.get('name')} ({c.get('social_network')})" for c in chosen)
    if cfg.get("dry_run", True):
        log(f"DRY RUN - would schedule for {publish_on} on: {names}")
        return {"dry_run": True, "media_id": media_id,
                "publish_on": publish_on, "channels": names}

    result = _post(key, "/schedules/create", {"schedules": schedules})
    _remember(publish_on)
    log(f"scheduled for {publish_on} on: {names}")
    return {
        "dry_run": False,
        "media_id": media_id,
        "publish_on": publish_on,
        "channels": names,
        "group_ids": [g.get("id") for g in (result.get("data") or {}).get("upsert", [])],
    }
