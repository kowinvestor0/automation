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


def publish(videos, cfg, key, log=print, now=None):
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
    missing = planly.missing_channel_ids(channels, cfg.get("channels") or [])
    if missing:
        result.warnings.append("Channel id(s) not on this account: " + ", ".join(missing))
    chosen = planly.pick_channels(channels, cfg.get("channels") or [])
    if not chosen:
        result.errors.append("No Planly channels to post to. Connect one in Planly, "
                             "or fix the channel list in settings.")
        return result

    log(f"{len(videos)} video(s) -> {len(chosen)} channel(s) on team {team_id}")

    for video in videos:
        warning = planly.duration_warning(video, cfg.get("max_seconds"))
        if warning:
            result.warnings.append(warning)

    dealt = planly.distribute(videos, chosen, cfg.get("distribute") or "unique")
    by_id = {c["id"]: c for c in chosen}

    empty = [planly.describe(by_id[cid]) for cid, items in dealt.items() if not items]
    if empty:
        result.warnings.append(
            f"{len(videos)} video(s) for {len(chosen)} channel(s) - nothing left for: "
            + ", ".join(empty))

    # Plan every channel from the same booked-slot set. In same_time mode that
    # is what makes the Nth post land on the same minute across all channels,
    # which is how the user schedules by hand.
    booked = hub_state.all_taken_slots()
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


def run_for_factory(factory_dir, cfg, log=print, only_new=True):
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
        return publish(videos, cfg, key, log=log)
    except planly.PlanlyError as e:
        result.errors.append(str(e))
    except Exception as e:
        result.errors.append(f"{type(e).__name__}: {str(e)[:200]}")
    return result
