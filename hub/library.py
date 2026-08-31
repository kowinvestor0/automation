"""Videos the user made themselves, dropped into a folder per account.

The factories never need this. They render, upload and publish in one pass, and
the file on disk is a by-product nobody has to file anywhere. This exists for the
other direction: a folder the user drops their own clips into, named after the
account they belong to.

    D:/video/outdoorboysl/clip1.mp4   ->  posts to outdoorboysl
    D:/video/outdoorboysm/clip2.mp4   ->  posts to outdoorboysm

The folder name is the routing. That is the whole model, and it is deliberately
the one thing a person can get right from a file manager on a phone.
"""
import time

from hub import state as hub_state

VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
DONE_DIR = "_da_dang"          # where a posted file is moved to
# A file still being copied in has a size that keeps changing. Anything touched
# in the last half minute is left for the next run rather than uploaded torn.
SETTLE_SECONDS = 30


def folder_name(channel):
    """Accounts are named by the user, so the folder is named the same way."""
    return (channel.get("name") or channel.get("id") or "").strip()


def ensure_folders(root, channels, log=lambda *_: None):
    """One folder per connected account, plus a place for posted files."""
    made = []
    root.mkdir(parents=True, exist_ok=True)
    for channel in channels:
        name = folder_name(channel)
        if not name:
            continue
        target = root / name
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            made.append(name)
        (target / DONE_DIR).mkdir(parents=True, exist_ok=True)
    if made:
        log(f"created {len(made)} folder(s) under {root}: " + ", ".join(made[:8])
            + ("..." if len(made) > 8 else ""))
    return made


def _settled(path, now=None):
    try:
        age = (now or time.time()) - path.stat().st_mtime
    except OSError:
        return False
    return age >= SETTLE_SECONDS


def scan(root, channels, log=print, now=None):
    """Everything waiting to be posted, as {channel_id: [file, ...]}.

    A folder that matches no account is reported rather than ignored - a typo in
    a folder name would otherwise mean videos silently never post.
    """
    if not root.exists():
        return {}, []

    by_folder = {folder_name(c).lower(): c for c in channels if folder_name(c)}
    waiting = {}
    unknown = []

    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name == DONE_DIR:
            continue
        channel = by_folder.get(entry.name.lower())
        if channel is None:
            # Only worth mentioning if something is actually sitting in there.
            # A root shared with other folders would otherwise report dozens of
            # names that were never meant to be accounts.
            if any(p.suffix.lower() in VIDEO_SUFFIXES
                   for p in entry.iterdir() if p.is_file()):
                unknown.append(entry.name)
            continue
        files = []
        for item in sorted(entry.iterdir()):
            if not item.is_file() or item.suffix.lower() not in VIDEO_SUFFIXES:
                continue
            if not _settled(item, now):
                log(f"{item.name} is still being written, leaving it for next time")
                continue
            files.append(item)
        if files:
            waiting[channel["id"]] = files
    return waiting, unknown


def as_videos(waiting, channels):
    """Turn the scan into the shape publish() already understands.

    Each file is pinned to its own channel, so this deliberately bypasses the
    round-robin: the folder already said where it goes.
    """
    names = {c["id"]: c for c in channels}
    out = []
    for channel_id, files in waiting.items():
        for path in files:
            out.append({
                "title": path.stem.replace("_", " ").replace("-", " ").strip(),
                "description": "",
                "folder": f"library/{names[channel_id].get('name')}/{path.name}",
                "path": path,
                "channel_id": channel_id,
                "duration_seconds": None,
            })
    return out


def mark_done(video, move=True, log=print):
    """Move a posted file into the done folder so it cannot go out twice."""
    hub_state.remember_videos([video["folder"]])
    if not move:
        return None
    path = video["path"]
    target = path.parent / DONE_DIR
    try:
        target.mkdir(parents=True, exist_ok=True)
        destination = target / path.name
        if destination.exists():
            destination = target / f"{path.stem}-{int(path.stat().st_mtime)}{path.suffix}"
        path.replace(destination)
        return destination
    except OSError as e:
        # Not fatal: the state file already knows it was posted, so the worst
        # case is a file sitting in the folder looking unposted.
        log(f"could not move {path.name} into {DONE_DIR}: {e}")
        return None


def unposted(videos):
    seen = hub_state.seen_videos()
    return [v for v in videos if v["folder"] not in seen]
