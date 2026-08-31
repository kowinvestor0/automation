"""One command that does a whole background pass: render, then schedule.

This is what GitHub Actions calls, what the desktop app's Run button calls, and
what you can run by hand:

    python tools/run_factory.py --factory us --count 3
    python tools/run_factory.py --all
    python tools/run_factory.py --factory mx --publish-only

Each factory runs as a subprocess. That is not incidental: both factories ship a
package called `pipeline`, so importing them into one process would give the
second one whichever copy Python imported first. Separate processes also mean a
factory that crashes takes down its own run and nothing else.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hub import library, notify, publish, settings, state as hub_state, status  # noqa: E402
from hub import workspace as hub_workspace                             # noqa: E402
from hub.paths import CODE, FACTORIES, FACTORY_LABEL, factory_dir       # noqa: E402


def _utf8_console():
    """Windows consoles default to cp1252 and raise on Vietnamese video titles
    or on the status badges. Losing a finished run to a print is not acceptable."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()


def log(message):
    print(message, flush=True)


def _stream(command, cwd, env):
    """Run the factory and echo its output live, so a 20-minute render shows
    progress in the Actions log instead of a wall of text at the end."""
    process = subprocess.Popen(
        command, cwd=str(cwd), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1)
    tail = []
    for line in process.stdout:
        line = line.rstrip()
        print(line, flush=True)
        tail.append(line)
        del tail[:-40]
    return process.wait(), tail


def render(name, count, niche, extra_args, cfg, bank=False):
    """Run one factory. Returns (exit_code, tail_of_output)."""
    directory = factory_dir(name)
    main = directory / "main.py"
    if not main.exists():
        return 127, [f"factory '{name}' has no main.py at {main}"]

    env = os.environ.copy()
    settings.export_env(cfg)
    for key in settings.SECRET_NAMES:
        if os.environ.get(key):
            env[key] = os.environ[key]
    env["FACTORY_ROOT"] = str(directory)
    env["PYTHONIOENCODING"] = "utf-8"
    # The hub owns publishing now. Older factory configs carry their own
    # `planly` block; neutralise it so a video cannot be scheduled twice.
    env["FACTORY_SKIP_PLANLY"] = "1"

    # Frozen, `sys.executable` is AutomationHub.exe, not python - so the exe
    # re-launches itself in its `factory` mode instead of naming a script.
    if getattr(sys, "frozen", False):
        command = [sys.executable, "factory", name, "--count", str(count)]
    else:
        command = [sys.executable, "main.py", "--count", str(count)]
    if niche:
        command += ["--niche", niche]
    if bank:
        command.append("--bank")
    command += list(extra_args or [])

    log(f"\n{'=' * 62}\n{FACTORY_LABEL.get(name, name)}  ->  {' '.join(command[1:])}\n{'=' * 62}")
    return _stream(command, directory, env)


def one_factory(name, cfg, args):
    started = time.time()
    run_cfg = (cfg.get("run") or {}).get(name) or {}
    count = args.count if args.count is not None else int(run_cfg.get("count", 1))
    niche = args.niche or run_cfg.get("niche") or ""

    record = {
        "factory": name,
        "label": FACTORY_LABEL.get(name, name),
        "videos": 0,
        "scheduled": 0,
        "titles": [],
        "calendar": [],
        "warnings": [],
        "errors": [],
        "dry_run": bool((cfg.get("publish") or {}).get("dry_run", True)),
        "status": "ok",
    }

    directory = factory_dir(name)
    before = {p.name for p in (directory / "output").glob("*") if p.is_dir()}

    if not args.publish_only:
        code, tail = render(name, count, niche, args.factory_args, cfg,
                            bank=args.bank)
        if code != 0:
            record["status"] = "failed"
            record["errors"].append(f"render exited {code}: " + " / ".join(tail[-3:]))

    after = [p for p in sorted((directory / "output").glob("*")) if p.is_dir()]
    fresh = [p for p in after if p.name not in before]
    record["videos"] = len(fresh)
    for folder in fresh:
        try:
            meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
            record["titles"].append(meta.get("title") or folder.name)
        except (OSError, ValueError):
            record["titles"].append(folder.name)

    if record["videos"] == 0 and record["status"] != "failed" and not args.publish_only:
        record["status"] = "failed"
        record["errors"].append("the render produced no video")

    if not args.no_publish:
        result = publish.run_for_factory(directory, cfg.get("publish") or {},
                                         log=log, factory=name, niche=niche)
        record["scheduled"] = result.scheduled
        record["dry_run"] = result.dry_run
        record["warnings"] += result.warnings
        record["errors"] += result.errors
        record["route"] = result.route
        record["calendar"] = [(e["local_time"], f"{e['video']} -> {e['channel']}")
                              for e in result.entries]
        # Kept so the committed status can scrub them; the Telegram copy keeps
        # the real names.
        record["channel_names"] = sorted({e["channel"].split(" (")[0]
                                          for e in result.entries})
        if result.errors and record["status"] == "ok":
            record["status"] = "partial"

    record["seconds"] = time.time() - started
    return record


def library_root(cfg):
    configured = (cfg.get("publish") or {}).get("library_root") or ""
    return Path(configured) if configured else CODE / "video"


def library_pass(cfg, make_only=False):
    """Create the per-account folders, and post whatever is waiting in them."""
    pub = cfg.get("publish") or {}
    key = settings.secret("PLANLY_API_KEY", cfg)
    if not key:
        log("no PLANLY_API_KEY, cannot look up the accounts")
        return 1
    from hub import planly

    team = planly.resolve_team(key, pub.get("team_id")
                               or settings.secret("PLANLY_TEAM_ID", cfg))
    channels = planly.list_channels(key, team)
    root = library_root(cfg)
    library.ensure_folders(root, channels, log)
    log(f"library: {root}")

    if make_only:
        for channel in channels:
            log(f"  {library.folder_name(channel)}")
        return 0

    waiting, unknown = library.scan(root, channels, log=log)
    for name in unknown:
        log(f"folder '{name}' matches no account - nothing from it will post")
    videos = library.unposted(library.as_videos(waiting, channels))
    if not videos:
        log("library: nothing waiting")
        return 0

    log(f"library: {len(videos)} video(s) waiting")
    result = publish.publish(videos, pub, key, log=log)
    for warning in result.warnings:
        log(f"  warning: {warning}")
    for error in result.errors:
        log(f"  ERROR: {error}")
    if not result.dry_run and result.scheduled:
        posted = {e["folder"] for e in result.entries}
        for video in videos:
            if video["folder"] in posted:
                library.mark_done(video, log=log)
    return 0 if not result.errors else 1


def main():
    parser = argparse.ArgumentParser(
        description="Render videos with one or both factories, then schedule them.")
    parser.add_argument("--factory", choices=FACTORIES, action="append",
                        help="which factory to run; repeatable")
    parser.add_argument("--all", action="store_true", help="run every enabled factory")
    parser.add_argument("--count", type=int, help="videos per factory (overrides settings)")
    parser.add_argument("--niche", help="force a niche for this run")
    parser.add_argument("--no-publish", action="store_true",
                        help="render only, leave the calendar alone")
    parser.add_argument("--publish-only", action="store_true",
                        help="skip rendering, schedule what is already in output/")
    parser.add_argument("--dry-run", action="store_true",
                        help="walk the whole publish flow but create no schedule")
    parser.add_argument("--live", action="store_true",
                        help="turn the dry run off for this run - posts for real")
    parser.add_argument("--library", action="store_true",
                        help="post videos waiting in the per-account folders")
    parser.add_argument("--make-folders", action="store_true",
                        help="create one folder per connected account, then stop")
    parser.add_argument("--bank", action="store_true",
                        help="write scripts from topics.json instead of an LLM")
    # Anything after a bare `--` goes to the factory untouched, for the flags
    # that only one of them has.
    parser.add_argument("factory_args", nargs="*",
                        help="extra factory flags, after a literal --")
    args = parser.parse_args()

    cfg = settings.load()
    settings.export_env(cfg)

    if args.dry_run:
        cfg.setdefault("publish", {})["dry_run"] = True
    if args.live:
        cfg.setdefault("publish", {})["dry_run"] = False
        cfg["publish"]["enabled"] = True

    names = args.factory or []
    if args.all or not names:
        names = [n for n in FACTORIES
                 if ((cfg.get("run") or {}).get(n) or {}).get("enabled", True)]
    if not names:
        log("Every factory is disabled in settings. Nothing to do.")
        return 0

    for problem in settings.missing_keys(cfg):
        log(f"note: {problem}")

    hub_workspace.ensure(log)
    hub_state.forget_past_slots()

    if args.make_folders or args.library:
        code = library_pass(cfg, make_only=args.make_folders)
        if args.make_folders or not (args.factory or args.all):
            return code

    runs = [one_factory(name, cfg, args) for name in names]
    payload = status.build(runs)
    names = set()
    for run in runs:
        names.update(run.get("channel_names") or [])
    text = status.write(payload, CODE, names=names)
    hub_state.record_run({"finished_at": payload["finished_at"],
                          "status": payload["status"],
                          "videos": payload["videos"],
                          "scheduled": payload["scheduled"]})

    log("\n" + text)
    notify.announce(payload, cfg, log=log)

    return 0 if payload["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
