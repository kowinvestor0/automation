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
import json

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
        # Every account this run touched or mentioned. The status file is
        # committed to a public repo and scrubs these; collecting only the ones
        # that received a video left the idle ones named in a warning.
        self.channel_names = []

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
            "channel_names": self.channel_names,
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
        # The topic id lives next door in script.json. Carried along so the
        # publisher can refuse a topic that already went out - once the local
        # bank recycles, the same topic renders again under a new folder name
        # and the folder check alone would wave it straight through.
        try:
            script = json.loads((folder / "script.json").read_text(encoding="utf-8"))
            meta["topic_id"] = script.get("id") or ""
        except (OSError, ValueError):
            meta["topic_id"] = ""
        out.append(meta)
    return out


def drop_repeats(videos, days, log=print):
    """Hold back anything whose topic went out recently.

    The bank is finite; at sixty videos a day it comes round in under two. A
    repeat is not a cosmetic problem - the same clip on two accounts is what
    gets a network flagged - so a recycled topic waits rather than posting.
    """
    if not days:
        return videos, []
    recent = hub_state.recent_topics(days)
    keep, held = [], []
    for video in videos:
        topic = video.get("topic_id")
        if topic and topic in recent:
            held.append(video)
        else:
            keep.append(video)
    if held:
        log(f"holding {len(held)} video(s) whose topic already went out "
            f"in the last {days} days")
    return keep, held


def caption_for(video, channel, cfg):
    """Post text. Per-network overrides come from settings; the fallback is the
    description the script generator already wrote."""
    text = (video.get("description") or video.get("title") or "").strip()
    limit = int((cfg.get("caption_limit") or 2100))
    return text[:limit]


DUET_STITCH_LIMIT = 60


def _switch(mode, seconds, limit):
    """Resolve a three-way duet/stitch switch into "must disable this".

    'auto' with an unknown duration disables, on purpose: leaving it on for a
    long video loses the whole post, while turning it off on a short one costs
    only the duet feature.
    """
    if mode == "allow":
        return False
    if mode == "disable":
        return True
    if not seconds:
        return True
    return float(seconds) > float(limit)


def options_for(video, channel, cfg):
    """Per-network extras sent with each schedule.

    The duet/stitch part is not cosmetic. TikTok only allows Duet and Stitch on
    videos of about a minute or less, and rejects a longer one outright while
    those are still on - the post simply never appears. So anything past the
    limit gets them switched off automatically.
    """
    network = (channel.get("social_network") or "").lower()
    configured = cfg.get("channel_options") or {}
    options = dict(configured.get(channel["id"]) or configured.get(network) or {})

    if "youtube" in network:
        options.setdefault("title", (video.get("title") or "")[:95])
        return options

    if "tiktok" not in network:
        return options

    post = cfg.get("post_options") or {}
    limit = post.get("auto_disable_over_seconds") or DUET_STITCH_LIMIT
    seconds = video.get("duration_seconds")

    options.setdefault("postType", 0)
    # Only sent when switching something off - an unexpected field is a good way
    # to have a network reject the whole post.
    if _switch(post.get("duet", "auto"), seconds, limit):
        options.setdefault("disableDuet", True)
    if _switch(post.get("stitch", "auto"), seconds, limit):
        options.setdefault("disableStitch", True)
    if post.get("comment") == "disable":
        options.setdefault("disableComment", True)
    if post.get("privacy_level") and post["privacy_level"] != "default":
        options.setdefault("privacyLevel", post["privacy_level"])
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


def publish(videos, cfg, key, log=print, now=None, factory=None, niche=None, account_name="default"):
    """Upload each video once, then schedule it on the channels it was dealt to."""
    result = PublishResult()
    result.dry_run = bool(cfg.get("dry_run", True))

    videos, held = drop_repeats(videos, cfg.get("repeat_days", 14), log=log)
    for video in held:
        result.warnings.append(
            f"held back: '{video.get('title') or video['folder']}' repeats a topic "
            f"posted in the last {cfg.get('repeat_days', 14)} days")
    if not videos:
        result.warnings.append("Nothing to publish - every video repeated a "
                               "recent topic, or output/ was empty.")
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
    result.channel_names = sorted({c.get("name") for c in chosen if c.get("name")})

    log(f"{len(videos)} video(s) -> {len(chosen)} channel(s) "
        f"on team {team_id} [route: {route}]")

    for video in videos:
        warning = planly.duration_warning(video, cfg.get("max_seconds"))
        if warning:
            result.warnings.append(warning)

    # A video that names its own channel was put in that account's folder by
    # hand, and the folder is the instruction - there is nothing to deal.
    pinned = [v for v in videos if v.get("channel_id")]
    by_id = {c["id"]: c for c in chosen}
    start_key = f"{account_name}:{route}" if account_name != "default" else route
    start = hub_state.channel_start(start_key)
    if pinned and len(pinned) == len(videos):
        rotating = False
        dealt = {c["id"]: [] for c in chosen}
        for video in videos:
            if video["channel_id"] in dealt:
                dealt[video["channel_id"]].append(video)
            else:
                result.warnings.append(
                    f"{video['folder']}: that account is not in this route")
    else:
        rotating = True
        dealt = planly.distribute(videos, chosen,
                                  cfg.get("distribute") or "unique", start=start)

    empty = ([planly.describe(by_id[cid]) for cid, items in dealt.items() if not items]
             if rotating else [])
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
    # "now" is Planly's own rule: a schedule with no publishOn goes out
    # immediately. There is nothing to plan and no slot to book.
    post_now = (cfg.get("when") or "slots") == "now"
    per_channel = max((len(v) for v in dealt.values()), default=0)
    if post_now:
        slots = [None] * per_channel
    else:
        st_now = hub_state.load()
        booked = set()
        for channel_id, items in dealt.items():
            if items:
                booked |= hub_state.taken_slots(channel_id, st_now)
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
            entry = {
                "channelId": channel_id,
                "content": caption_for(video, channel, cfg),
                "media": [{"id": media_id, "options": {}}],
                "options": options_for(video, channel, cfg),
            }
            if when:
                entry["publishOn"] = when
            entries.append(entry)
            result.entries.append({
                "channel": planly.describe(channel),
                "channel_id": channel_id,
                "video": video.get("title") or video["folder"],
                "folder": video["folder"],
                "publish_on": when,
                "local_time": _local(when, cfg) if when else "ngay bay gio",
            })

    if not entries:
        result.errors.append("Nothing could be scheduled - every upload failed.")
        return result

    if result.dry_run:
        log(f"DRY RUN - would {'post' if post_now else 'schedule'} "
            f"{len(entries)} video(s) right now" if post_now else
            f"DRY RUN - would create {len(entries)} schedule entr"
            f"{'y' if len(entries) == 1 else 'ies'}")
        return result

    planly.create_schedules(key, team_id, entries)

    st = hub_state.load()
    if not post_now:
        for channel_id, items in dealt.items():
            if items:
                hub_state.remember_slots(channel_id, slots[:len(items)], state=st)
    hub_state.remember_videos([v["folder"] for v in videos
                               if v["folder"] in media_ids], state=st)
    hub_state.remember_topics([v["topic_id"] for v in videos
                               if v.get("topic_id") and v["folder"] in media_ids],
                              state=st)
    if rotating and (cfg.get("distribute") or "unique") != "mirror":
        hub_state.remember_channel_start(
            start_key, planly.next_start(start, len(videos), len(chosen)), state=st)
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
    """Entry point used by the CLI and the GUI. Returns a PublishResult.

    Supports both single-account and multi-account configurations (via cfg['accounts']).
    """
    result = PublishResult()
    result.dry_run = bool(cfg.get("dry_run", True))

    if not cfg.get("enabled"):
        result.warnings.append("Publishing is off (publish.enabled = false).")
        return result

    # Check for multi-account configuration
    accounts = cfg.get("accounts")
    if not accounts:
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

    # Multi-account publishing
    videos = collect_videos(factory_dir, only_new=only_new, log=log)
    if not videos:
        result.warnings.append("Nothing to publish - output/ was empty.")
        return result

    combined = PublishResult()
    combined.dry_run = result.dry_run

    is_split = (cfg.get("account_distribution") == "split") and len(accounts) > 1
    if is_split:
        import math
        chunk_size = max(1, math.ceil(len(videos) / len(accounts)))
        chunks = [videos[i * chunk_size:(i + 1) * chunk_size] for i in range(len(accounts))]
    else:
        chunks = [videos] * len(accounts)

    for idx, acc in enumerate(accounts):
        acc_name = acc.get("name") or f"account_{idx + 1}"
        acc_key = acc.get("key") or secret(acc.get("api_key_secret") or (f"PLANLY_API_KEY_{idx + 1}" if idx > 0 else "PLANLY_API_KEY"))
        if not acc_key and idx == 0:
            acc_key = secret("PLANLY_API_KEY")

        if not acc_key:
            combined.errors.append(f"Account '{acc_name}': API key is missing.")
            continue

        acc_team = acc.get("team_id") or secret(acc.get("team_id_secret") or (f"PLANLY_TEAM_ID_{idx + 1}" if idx > 0 else "PLANLY_TEAM_ID"))
        if not acc_team and idx == 0:
            acc_team = cfg.get("team_id") or secret("PLANLY_TEAM_ID")

        acc_cfg = dict(cfg)
        if acc_team:
            acc_cfg["team_id"] = acc_team
        if "routes" in acc:
            acc_cfg["routes"] = acc["routes"]
        if "channels" in acc:
            acc_cfg["channels"] = acc["channels"]

        curr_videos = chunks[idx] if idx < len(chunks) else []
        if not curr_videos:
            combined.warnings.append(f"Account '{acc_name}': No videos assigned this run.")
            continue

        log(f"\n[Planly Account: {acc_name}] scheduling {len(curr_videos)} video(s)...")
        try:
            acc_res = publish(curr_videos, acc_cfg, acc_key, log=log,
                              factory=factory, niche=niche, account_name=acc_name)
            combined.entries.extend(acc_res.entries)
            combined.warnings.extend([f"[{acc_name}] {w}" for w in acc_res.warnings])
            combined.errors.extend([f"[{acc_name}] {e}" for e in acc_res.errors])
            combined.uploaded += acc_res.uploaded
            combined.skipped.extend(acc_res.skipped)
            for cname in acc_res.channel_names:
                if cname not in combined.channel_names:
                    combined.channel_names.append(cname)
            combined.channel_names.sort()
        except Exception as e:
            combined.errors.append(f"Account '{acc_name}' error ({type(e).__name__}: {str(e)[:200]})")

    return combined
