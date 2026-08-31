"""What the user sees from their phone.

Three surfaces, all written by the same run:

  GITHUB_STEP_SUMMARY - the panel on the run page in the GitHub app
  STATUS.md           - committed back to the repo, so the front page of the
                        repo always shows the last run without opening Actions
  status.json         - the same facts, for the desktop app to read

STATUS.md is the important one. Opening a repo on a phone lands on the README
and the file list; a status file sitting there means the answer is one tap away
rather than four.
"""
import datetime as dt
import json
import os

BADGE = {
    "ok": "\U0001F7E2",        # green circle
    "partial": "\U0001F7E1",   # yellow
    "failed": "\U0001F534",    # red
    "idle": "⚪",          # white
}


def _now_iso():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def build(runs, extra=None):
    """`runs` is a list of per-factory dicts from tools/run_factory.py."""
    made = sum(r.get("videos", 0) for r in runs)
    scheduled = sum(r.get("scheduled", 0) for r in runs)
    failed = [r for r in runs if r.get("status") == "failed"]

    if not runs:
        overall = "idle"
    elif failed and len(failed) == len(runs):
        overall = "failed"
    elif failed:
        overall = "partial"
    else:
        overall = "ok"

    payload = {
        "status": overall,
        "finished_at": _now_iso(),
        "videos": made,
        "scheduled": scheduled,
        "runs": runs,
        "run_url": run_url(),
        "run_number": os.environ.get("GITHUB_RUN_NUMBER", ""),
    }
    payload.update(extra or {})
    return payload


def run_url():
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return ""


def _lines(payload):
    mark = BADGE.get(payload["status"], BADGE["idle"])
    out = [
        "# Status",
        "",
        f"{mark} **{payload['status'].upper()}** - {payload['finished_at']}",
        "",
        f"- Videos rendered: **{payload['videos']}**",
        f"- Posts scheduled on Planly: **{payload['scheduled']}**",
    ]
    if payload.get("run_url"):
        out.append(f"- [Open this run on GitHub]({payload['run_url']})")
    out.append("")

    for run in payload.get("runs", []):
        mark = BADGE.get(run.get("status"), BADGE["idle"])
        out.append(f"## {mark} {run.get('label') or run.get('factory')}")
        out.append("")
        out.append(f"- rendered: {run.get('videos', 0)}"
                   f"  ·  scheduled: {run.get('scheduled', 0)}"
                   f"  ·  took: {run.get('seconds', 0):.0f}s")
        if run.get("dry_run"):
            out.append("- _dry run - nothing was actually put on the calendar_")
        for title in run.get("titles", [])[:12]:
            out.append(f"  - {title}")
        for when, what in run.get("calendar", [])[:12]:
            out.append(f"  - `{when}`  {what}")
        for warning in run.get("warnings", [])[:8]:
            out.append(f"  - warning: {warning}")
        for error in run.get("errors", [])[:8]:
            out.append(f"  - **error:** {error}")
        out.append("")

    out.append("---")
    out.append("")
    out.append("_Written automatically at the end of every run. "
               "Nothing here is edited by hand._")
    return out


def alias(name):
    """A stable stand-in for an account name. Same name, same alias, for ever."""
    import hashlib

    return "acc-" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:4]


def _scrub(value, names):
    if isinstance(value, str):
        for name in names:
            if name in value:
                value = value.replace(name, alias(name))
        return value
    if isinstance(value, list):
        return [_scrub(v, names) for v in value]
    # Tuples matter here rather than being pedantry: the calendar is a list of
    # (time, text) tuples, and skipping them let every account name through.
    if isinstance(value, tuple):
        return tuple(_scrub(v, names) for v in value)
    if isinstance(value, dict):
        return {k: _scrub(v, names) for k, v in value.items()}
    return value


def mask(payload, names):
    """Replace account names throughout, for the copies that get committed.

    STATUS.md and status.json land in the repository, and the repository has to
    be public to get unlimited Actions minutes. Account names in there would
    publish the whole network and its posting rhythm to anyone who looks. The
    Telegram message is private and keeps the real names.

    Longest first, so one account name that contains another - outdoorboyso
    inside outdoorboysoo - cannot be half-replaced.
    """
    names = sorted({n for n in names if n}, key=len, reverse=True)
    return _scrub(payload, names) if names else payload


def channel_names(payload):
    """Every account name a run recorded, for scrubbing."""
    found = set()
    for run in payload.get("runs") or []:
        found.update(run.get("channel_names") or [])
    return found


def write(payload, repo_root, names=()):
    """Write all three surfaces. Returns the markdown that was produced."""
    committed = mask(payload, set(names) | channel_names(payload))
    text = "\n".join(_lines(committed)) + "\n"

    (repo_root / "STATUS.md").write_text(text, encoding="utf-8")
    (repo_root / "status.json").write_text(
        json.dumps(committed, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with open(summary, "a", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            pass
    return text


def short(payload):
    """One-screen version, for a phone notification."""
    mark = BADGE.get(payload["status"], BADGE["idle"])
    bits = [f"{mark} Automation Hub - {payload['status']}",
            f"{payload['videos']} video(s), {payload['scheduled']} scheduled"]
    for run in payload.get("runs", []):
        line = f"- {run.get('label') or run.get('factory')}: {run.get('videos', 0)} made"
        if run.get("errors"):
            line += f" - {run['errors'][0][:90]}"
        bits.append(line)
    if payload.get("run_url"):
        bits.append(payload["run_url"])
    return "\n".join(bits)
