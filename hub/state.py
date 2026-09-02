"""The hub's memory between runs.

A GitHub Actions runner is wiped after every job, so anything that has to
survive - which posting slots are already booked, what was published, when the
last run happened - is written here and cached back by the workflow. Locally it
just sits in the data folder.

Everything is best-effort: a corrupt or missing state file means "nothing known
yet", never a crash. Losing this file costs a duplicate slot check, not a video.
"""
import datetime as dt
import json

from hub.paths import data_dir

FILENAME = "state.json"
MAX_SLOTS_PER_CHANNEL = 600      # ~3 months at 6/day; keeps the file small
MAX_HISTORY = 400


def path():
    return data_dir() / FILENAME


def load():
    p = path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save(state):
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)
    return p


def taken_slots(channel_id, state=None):
    state = load() if state is None else state
    return set((state.get("planly_taken") or {}).get(channel_id) or [])


def all_taken_slots(state=None):
    state = load() if state is None else state
    out = set()
    for slots in (state.get("planly_taken") or {}).values():
        out.update(slots)
    return out


def remember_slots(channel_id, isos, state=None):
    """Book slots against one channel so the next run does not reuse them."""
    own_state = state is None
    state = load() if own_state else state
    booked = state.setdefault("planly_taken", {})
    used = booked.get(channel_id) or []
    used.extend(isos)
    # Keep the newest; ISO-8601 in UTC sorts chronologically as plain text.
    booked[channel_id] = sorted(set(used))[-MAX_SLOTS_PER_CHANNEL:]
    if own_state:
        save(state)
    return state


def forget_past_slots(state=None, now=None):
    """Drop slots whose time has come and gone; they can never collide again."""
    own_state = state is None
    state = load() if own_state else state
    cutoff = (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    booked = state.get("planly_taken") or {}
    for channel_id, slots in list(booked.items()):
        booked[channel_id] = [s for s in slots if s >= cutoff]
    if own_state:
        save(state)
    return state


def record_run(entry, state=None):
    own_state = state is None
    state = load() if own_state else state
    history = state.setdefault("runs", [])
    history.append(entry)
    state["runs"] = history[-MAX_HISTORY:]
    state["last_run"] = entry
    if own_state:
        save(state)
    return state


def seen_videos(state=None):
    """Video folder names already handed to Planly, so a rerun does not repost."""
    state = load() if state is None else state
    return set(state.get("published") or [])


def remember_videos(names, state=None):
    own_state = state is None
    state = load() if own_state else state
    published = state.get("published") or []
    published.extend(names)
    state["published"] = published[-MAX_HISTORY * 4:]
    if own_state:
        save(state)
    return state


def channel_start(route="default", state=None):
    """Where the last run stopped dealing videos to this route's channels.

    Kept here rather than recomputed, because fairness across accounts is a
    property of the whole history, not of any single run. One pointer per route:
    two streams posting to different sets of accounts each keep their own place,
    and neither pushes the other along.
    """
    state = load() if state is None else state
    starts = state.get("channel_starts")
    if not isinstance(starts, dict):
        return 0
    try:
        return max(0, int(starts.get(route) or 0))
    except (TypeError, ValueError):
        return 0


def remember_channel_start(route, position, state=None):
    own_state = state is None
    state = load() if own_state else state
    starts = state.get("channel_starts")
    if not isinstance(starts, dict):
        starts = {}
    starts[route] = max(0, int(position))
    state["channel_starts"] = starts
    if own_state:
        save(state)
    return state


def remember_topics(topic_ids, state=None, now=None):
    """Record when each topic went out, so a recycled one can be held back."""
    own_state = state is None
    state = load() if own_state else state
    stamp = (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%d")
    posted = state.get("topics_posted")
    if not isinstance(posted, dict):
        posted = {}
    for topic_id in topic_ids:
        if topic_id:
            posted[topic_id] = stamp
    # Keep it from growing without bound; a year is far past any repeat window.
    cutoff = ((now or dt.datetime.now(dt.timezone.utc))
              - dt.timedelta(days=365)).strftime("%Y-%m-%d")
    state["topics_posted"] = {k: v for k, v in posted.items() if v >= cutoff}
    if own_state:
        save(state)
    return state


def recent_topics(days, state=None, now=None):
    """Topic ids posted within the last `days`."""
    state = load() if state is None else state
    posted = state.get("topics_posted")
    if not isinstance(posted, dict):
        return set()
    cutoff = ((now or dt.datetime.now(dt.timezone.utc))
              - dt.timedelta(days=int(days))).strftime("%Y-%m-%d")
    return {k for k, v in posted.items() if v >= cutoff}
