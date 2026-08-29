"""Planly API client: upload finished videos and put them on the calendar.

Upload is Planly's three-step dance:

    media/start-upload   -> mediaId + a presigned S3 URL
    PUT the file         -> straight to S3, not through Planly
    media/finish-upload  -> Planly ingests it and reads the resolution

then `schedules/create` takes one entry per (channel, video) pair.

The timing rules live in pure functions (`plan_slots`, `distribute`) with no
network in them. That is the part that is easy to get subtly wrong - a slot an
hour in the past, or eight channels all handed the same clip - so it is the part
worth being able to test on its own.
"""
import datetime as dt
import os

BASE = "https://app.planly.com/api/v2"
TIMEOUT = 120
UPLOAD_TIMEOUT = 900


class PlanlyError(RuntimeError):
    pass


# ---------------------------------------------------------------- transport

def _headers(key):
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _post(key, path, body):
    import requests

    r = requests.post(f"{BASE}{path}", headers=_headers(key), json=body, timeout=TIMEOUT)
    if r.status_code == 401:
        raise PlanlyError("Planly rejected the API key. Planly > Settings > Security.")
    if r.status_code == 429:
        raise PlanlyError("Planly rate limit hit. Try again in a minute.")
    if r.status_code >= 400:
        raise PlanlyError(f"{path} -> HTTP {r.status_code}: {r.text[:220]}")
    try:
        data = r.json()
    except ValueError:
        raise PlanlyError(f"{path} -> non-JSON reply: {r.text[:200]}")
    # Planly answers 200 with an `error` field rather than an HTTP error code.
    if isinstance(data, dict) and data.get("error"):
        raise PlanlyError(f"{path} -> {data['error']}")
    return data


# ---------------------------------------------------------------- discovery

def list_channels(key, team_id):
    return _post(key, "/channels/list", {"team_id": team_id}).get("data") or []


def resolve_team(key, team_id=""):
    """Planly has no endpoint that lists teams - `/teams/list` returns 404. The
    team id has to be configured, and it is the one thing that cannot be
    discovered from the key alone."""
    team_id = (team_id or "").strip()
    if not team_id:
        raise PlanlyError(
            "No Planly team id set. Planly's API cannot list teams, so it has to "
            "be filled in once - copy it from the Planly URL, or from the old "
            "upload app's planly-accounts.json.")
    return team_id


def check_key(key, team_id=""):
    """Backs the GUI's Test button. Returns (ok, message)."""
    key = (key or "").strip()
    if len(key) < 16:
        return False, "That key looks too short."
    if not (team_id or "").strip():
        return False, "Fill in the team id as well - Planly cannot look it up."
    try:
        channels = list_channels(key, team_id.strip())
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:150]}"
    networks = sorted({(c.get("social_network") or "?") for c in channels})
    return True, (f"OK - {len(channels)} channel(s): {', '.join(networks)}")


def pick_channels(all_channels, wanted):
    """Channels to post to. `wanted` is ["all"], a list of ids, or empty."""
    if not wanted or wanted == ["all"]:
        return list(all_channels)
    by_id = {c["id"]: c for c in all_channels}
    return [by_id[i] for i in wanted if i in by_id]


def missing_channel_ids(all_channels, wanted):
    """Ids asked for that this account does not have - worth saying out loud."""
    if not wanted or wanted == ["all"]:
        return []
    have = {c["id"] for c in all_channels}
    return [i for i in wanted if i not in have]


def describe(channel):
    return f"{channel.get('name') or channel.get('id')} ({channel.get('social_network') or '?'})"


# ------------------------------------------------------------------- upload

def upload_media(key, team_id, path, log=print):
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
        raise PlanlyError(f"start-upload returned no upload target: {str(start)[:200]}")

    # Send back exactly the headers Planly signed the URL with; S3 rejects the
    # PUT when Content-Type or Content-Length differ from the signature.
    put_headers = start.get("headers") or {
        "Content-Type": "video/mp4",
        "Content-Length": str(size),
    }
    with open(path, "rb") as f:
        r = requests.put(url, data=f, headers=put_headers, timeout=UPLOAD_TIMEOUT)
    if r.status_code >= 400:
        raise PlanlyError(f"S3 upload failed: HTTP {r.status_code} {r.text[:200]}")

    done = _post(key, "/media/finish-upload", {"mediaId": media_id})
    info = done.get("data") or {}
    res = info.get("resolution") or {}
    log(f"uploaded {name}  {size / (1 << 20):.1f} MB  "
        f"{res.get('width')}x{res.get('height')}  id {media_id[:8]}")
    return media_id


# ---------------------------------------------------------------- schedules

STATUS_SCHEDULED = 1


def build_groups(entries):
    """Fold flat (channel, video, time) entries into Planly schedule groups.

    Group by publish time AND media id, never by time alone. A Planly schedule
    group means "one post going out to several channels at once" - so grouping
    on time alone puts eight channels holding eight *different* videos into one
    group, and Planly then shows and posts it as one video to eight channels.
    That is exactly the bug that put the same clip on every channel before.

      different video per channel -> one group each
      same video on many channels -> one shared group, which is what a group is
    """
    order = []
    grouped = {}
    for entry in entries:
        media_id = entry["media"][0]["id"]
        gkey = (entry["publishOn"], media_id)
        if gkey not in grouped:
            grouped[gkey] = []
            order.append(gkey)
        grouped[gkey].append({
            "channelId": entry["channelId"],
            "content": entry.get("content", ""),
            "status": STATUS_SCHEDULED,
            "media": entry["media"],
            "options": entry.get("options") or {"postType": 0},
        })
    return [{"publishOn": gkey[0], "schedules": grouped[gkey]} for gkey in order]


def create_schedules(key, team_id, entries):
    """Create every schedule in one call, as groups."""
    groups = build_groups(entries)
    return _post(key, "/schedule-groups/create",
                 {"teamId": team_id, "scheduleGroups": groups})


# 0 draft, 1 scheduled, 3 published, 4 failed. Failed and draft have to be
# listed too, or a post that quietly died just looks like it vanished.
ALL_STATUSES = [0, 1, 3, 4]


def list_schedules(key, team_id, channel_ids=None, statuses=None, max_items=500):
    """Scheduled posts, newest first. Paginated by cursor."""
    rows = []
    cursor = None
    page_size = 50
    while len(rows) < max_items:
        body = {
            "teamId": team_id,
            "pagination": {
                "cursor": cursor,
                "orderBy": ["CreatedAt", "desc"],
                "pageSize": min(page_size, max_items - len(rows)),
            },
        }
        filters = {}
        if channel_ids:
            filters["channels"] = list(channel_ids)
        filters["status"] = list(statuses or ALL_STATUSES)
        body["filter"] = filters

        data = _post(key, "/schedule-groups/list", body).get("data") or {}
        page = data.get("rows") or []
        if not page:
            break
        rows.extend(page)
        cursor = data.get("next")
        if not cursor:
            break
    return rows


def delete_schedules(key, group_ids, batch=50):
    """Delete by group. Planly documents this as the only supported way, and
    deleting a group deletes every schedule inside it."""
    ids = [i for i in (group_ids or []) if i]
    for start in range(0, len(ids), batch):
        _post(key, "/schedule-groups/delete", {"ids": ids[start:start + batch]})
    return len(ids)


# -------------------------------------------------------- slot planning (pure)

def _tz(offset_hours):
    return dt.timezone(dt.timedelta(hours=float(offset_hours or 0)))


def _to_utc_iso(when):
    return when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def plan_slots(count, cfg, now=None, taken=()):
    """`count` posting times for one channel, as UTC ISO strings.

    The times in the config are the user's own wall clock - "09:00" means 9am
    where they live - and are only converted to UTC on the way out, so the
    Planly calendar reads the way they think about it.

    mode "same_time" walks the configured list of times and rolls to the next
    day when the list runs out; every channel is planned from the same list, so
    they land on the same minute together. mode "spread" ignores the rest of the
    list and steps forward from the first time by `gap_minutes`.
    """
    tz = _tz(cfg.get("timezone_offset", 0))
    now = now or dt.datetime.now(tz)
    lead = dt.timedelta(minutes=int(cfg.get("lead_minutes", 30) or 0))
    earliest = now + lead
    taken = set(taken)
    if count <= 0:
        return []

    times = sorted(t for t in (cfg.get("times") or ["09:00"]) if t)
    if not times:
        times = ["09:00"]
    slots = []

    if (cfg.get("mode") or "same_time") == "spread":
        gap = dt.timedelta(minutes=max(1, int(cfg.get("gap_minutes", 120) or 120)))
        hour, _, minute = times[0].partition(":")
        cursor = dt.datetime(now.year, now.month, now.day,
                             int(hour), int(minute or 0), tzinfo=tz)
        # Bounded so a pathological config cannot spin forever.
        for _ in range(20000):
            if len(slots) == count:
                return slots
            if cursor >= earliest:
                iso = _to_utc_iso(cursor)
                if iso not in taken:
                    slots.append(iso)
            cursor += gap
        raise PlanlyError("Could not lay out enough posting slots. "
                          "Lower the count or shorten gap_minutes.")

    for day in range(0, 120):
        date = (now + dt.timedelta(days=day)).date()
        for hhmm in times:
            hour, _, minute = hhmm.partition(":")
            when = dt.datetime(date.year, date.month, date.day,
                               int(hour), int(minute or 0), tzinfo=tz)
            if when < earliest:
                continue
            iso = _to_utc_iso(when)
            if iso in taken:
                continue
            slots.append(iso)
            if len(slots) == count:
                return slots
    raise PlanlyError("No free slot within 120 days. Add more entries to `times`.")


def distribute(videos, channels, mode="unique"):
    """Which channel gets which video, and in what order.

    Returns {channel_id: [video, ...]}; position in the list is the slot index.

    "unique" deals the batch out like cards, so no clip lands on two channels -
    that is what stops eight channels posting the same video at the same minute.
    "mirror" is the opposite: every channel gets every video.
    """
    ids = [c["id"] for c in channels]
    if not ids:
        return {}
    if mode == "mirror":
        return {cid: list(videos) for cid in ids}

    out = {cid: [] for cid in ids}
    for index, video in enumerate(videos):
        out[ids[index % len(ids)]].append(video)
    return out


def duration_warning(video, max_seconds):
    """Planly hides posts longer than a minute from the calendar view.

    Returns a warning string, or None. Never blocks - the limit is a setting and
    the user may have raised it on purpose.
    """
    seconds = video.get("duration_seconds") or 0
    if max_seconds and seconds and float(seconds) > float(max_seconds):
        name = video.get("title") or video.get("file") or "video"
        return (f"{name}: {float(seconds):.0f}s is longer than {max_seconds}s - "
                f"Planly will not show it on the calendar.")
    return None
