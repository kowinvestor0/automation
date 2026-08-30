"""Take the videos a factory just rendered and put them on the Planly calendar.

This is the only part of the hub that reaches the outside world and touches the
user's real accounts, so it is off by default (`publish.enabled`) and has a
`dry_run` that walks the entire flow - upload included - and stops one call
short of creating the schedule.

The shape of a run:

    collect  - read output/*/meta.json, skip anything published before
    upload   - one media upload per video, reused across every channel
    plan     - slots per channel, from settings, in the user's own timezone
    schedule - one entry per (channel, video), sent in a single batch
"""
import datetime as dt

from hub import planly, state as hub_state
from hub.settings import secret


class PublishResult:
    """Plain record of what a publish pass did, for the log, the summary and
    the Telegram message. Nothing here talks to the network."""

    def __init__(self):
        self.entries = []          # [{channel, channel_id, video, publish_on}]
        self.warnings = []
        self.errors = []
        self.uploaded = 0
        self.dry_run = True
        self.skipped = []
        self.route = "default"

    @property
    def scheduled(self):
        return len(self.entries)

    def as_dict(self):
        return {
            "scheduled": self.scheduled,
            "uploaded": self.uploaded,
            "dry_run": self.dry_run,
            "entries": self.entries,
            "warnings": self.warnings,
            "errors": self.errors,
            "skipped": self.skipped,
            "route": self.route,
        }


def collect_videos(factory_dir, only_new=True, log=print):
    """Every rendered video under output/, newest last, with its metadata."""
    import json

    out = []
    already = hub_state.seen_videos() if only_new else set()
    for meta_path in sorted((factory_dir / "output").glob("*/meta.json")):
        folder = meta_path.parent
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            log(f"skipping {folder.name}: unreadable meta.json ({e})")
            continue
        video = folder / (meta.get("file") or "video.mp4")
        if not video.exists():
            # Fall back to whatever mp4 is in there; the filename in meta.json
            # has changed shape between factory versions.
            candidates = sorted(folder.glob("*.mp4"))
            if not candidates:
                log(f"skipping {folder.name}: no .mp4 in the folder")
                continue
            video = candidates[0]
        key = folder.name
        if key in already:
            continue
        meta = dict(meta)
        meta["path"] = video
        meta["folder"] = key
        out.append(meta)
    return out


def caption_for(video, channel, cfg):
    """Post text. Per-network overrides come from settings; the fallback is the
    description the script generator already wrote."""
    text = (video.get("description") or video.get("title") or "").strip()
    limit = int((cfg.get("caption_limit") or 2100))
    return text[:limit]


def options_for(video, channel, cfg):
    """Per-network extras. YouTube refuses a post with no title."""
    network = (channel.get("social_network") or "").lower()
    configured = cfg.get("channel_options") or {}
    options = dict(configured.get(channel["id"]) or configured.get(network) or {})
    if "youtube" in network:
        options.setdefault("title", (video.get("title") or "")[:95])
    return options


def route_for(cfg, factory=None, niche=None):
    """Which channel list a given source of videos posts to, and under what name.

    Looked up most specific first: a niche inside a factory, then the factory,
    then the account-wide list. Returns (channel_ids, key) - the key names the
    route, and the rotation pointer is kept per key so a Spanish stream taking
    its turn does not move an English stream's place in its own list.
    """
    routes = cfg.get("routes") or {}
    for candidate in (f"{factory}:{niche}" if factory and niche else None,
                      factory or None):
        if candidate and routes.get(candidate):
            return list(routes[candidate]), candidate
    return list(cfg.get("channels") or ["all"]), "default"


def publish(videos, cfg, key, log=print, now=None, factory=None, niche=None):
    """Upload each video once, then schedule it on the channels it was dealt to."""
    result = PublishResult()
    result.dry_run = bool(cfg.get("dry_run", True))

    if not videos:
        result.warnings.append("Nothing to publish - no new videos in output/.")
        return result

    # A repo secret is how CI gets this; the app stores it locally. Either
    # way it never lands in the committed settings file.
    team_id = planly.resolve_team(
        key, cfg.get("team_id") or secret("PLANLY_TEAM_ID"))
    channels = planly.list_channels(key, team_id)

    wanted, route = route_for(cfg, factory, niche)
    missing = planly.missing_channel_ids(channels, wanted)
    if missing:
        result.warnings.append(f"Route '{route}' names channel id(s) not on this "
                               f"account: " + ", ".join(missing))
    chosen = planly.pick_channels(channels, wanted)
    if not chosen:
        result.errors.append(
            f"Route '{route}' has no channel to post to. Connect one in Planly, "
            f"or fix the channel list for this route in settings.")
        return result
    result.route = route

    log(f"{len(videos)} video(s) -> {len(chosen)} channel(s) "
        f"on team {team_id} [route: {route}]")

    for video in videos:
        warning = planly.duration_warning(video, cfg.get("max_seconds"))
        if warning:
            result.warnings.append(warning)

    # Carry the deal forward from where the last run stopped, so accounts take
    # turns instead of the first few taking everything for ever.
    start = hub_state.channel_start(route)
    dealt = planly.distribute(videos, chosen, cfg.get("distribute") or "unique",
                              start=start)
    by_id = {c["id"]: c for c in chosen}

    empty = [planly.describe(by_id[cid]) for cid, items in dealt.items() if not items]
    if empty:
        result.warnings.append(
            f"{len(videos)} video(s) for {len(chosen)} channel(s) - none this round "
            f"for {len(empty)}: " + ", ".join(empty[:6])
            + ("..." if len(empty) > 6 else "") + ". They lead the next run.")

    # Plan every channel from one shared booked-slot set, which is what makes
    # the Nth post land on the same minute across all of them - the way these
    # get scheduled by hand.
    #
    # The set covers only the channels actually receiving videos this round. Two
    # channels posting different videos at 09:00 is the normal case, not a
    # clash; counting a slot as spent the moment any channel anywhere used it
    # would push each run further into the day than the last and, after six
    # runs, spill everything into tomorrow.
    st_now = hub_state.load()
    booked = set()
    for channel_id, items in dealt.items():
        if items:
            booked |= hub_state.taken_slots(channel_id, st_now)
    per_channel = max((len(v) for v in dealt.values()), default=0)
    slots = planly.plan_slots(per_channel, cfg, now=now, taken=booked)

    # One upload per video, reused by every channel that was dealt it.
    media_ids = {}
    for video in videos:
        try:
            media_ids[video["folder"]] = planly.upload_media(
                key, team_id, video["path"], log=log)
            result.uploaded += 1
        except Exception as e:
            result.errors.append(f"upload failed for {video['folder']}: "
                                 f"{type(e).__name__}: {str(e)[:180]}")

    entries = []
    for channel_id, items in dealt.items():
        channel = by_id[channel_id]
        for index, video in enumerate(items):
            media_id = media_ids.get(video["folder"])
            if not media_id:
                result.skipped.append(f"{video['folder']} -> {planly.describe(channel)}")
                continue
            when = slots[index]
            entries.append({
                "channelId": channel_id,
                "publishOn": when,
                "content": caption_for(video, channel, cfg),
                "media": [{"id": media_id, "options": {}}],
                "options": options_for(video, channel, cfg),
            })
            result.entries.append({
                "channel": planly.describe(channel),
                "channel_id": channel_id,
                "video": video.get("title") or video["folder"],
                "folder": video["folder"],
                "publish_on": when,
                "local_time": _local(when, cfg),
            })

    if not entries:
        result.errors.append("Nothing could be scheduled - every upload failed.")
        return result

    if result.dry_run:
        log(f"DRY RUN - would create {len(entries)} schedule entr"
            f"{'y' if len(entries) == 1 else 'ies'}")
        return result

    planly.create_schedules(key, team_id, entries)

    st = hub_state.load()
    for channel_id, items in dealt.items():
        if items:
            hub_state.remember_slots(channel_id, slots[:len(items)], state=st)
    hub_state.remember_videos([v["folder"] for v in videos
                               if v["folder"] in media_ids], state=st)
    if (cfg.get("distribute") or "unique") != "mirror":
        hub_state.remember_channel_start(
            route, planly.next_start(start, len(videos), len(chosen)), state=st)
    hub_state.save(st)

    log(f"scheduled {len(entries)} post(s)")
    return result


def _local(iso, cfg):
    """The UTC string turned back into the clock the user actually reads."""
    try:
        when = dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.000Z").replace(
            tzinfo=dt.timezone.utc)
    except ValueError:
        return iso
    offset = dt.timezone(dt.timedelta(hours=float(cfg.get("timezone_offset", 0) or 0)))
    return when.astimezone(offset).strftime("%Y-%m-%d %H:%M")


def run_for_factory(factory_dir, cfg, log=print, only_new=True,
                    factory=None, niche=None):
    """Entry point used by the CLI and the GUI. Returns a PublishResult."""
    result = PublishResult()
    result.dry_run = bool(cfg.get("dry_run", True))

    if not cfg.get("enabled"):
        result.warnings.append("Publishing is off (publish.enabled = false).")
        return result

    key = secret("PLANLY_API_KEY")
    if not key:
        result.errors.append("Publishing is on but PLANLY_API_KEY is not set.")
        return result

    videos = collect_videos(factory_dir, only_new=only_new, log=log)
    try:
        return publish(videos, cfg, key, log=log, factory=factory, niche=niche)
    except planly.PlanlyError as e:
        result.errors.append(str(e))
    except Exception as e:
        result.errors.append(f"{type(e).__name__}: {str(e)[:200]}")
    return result
