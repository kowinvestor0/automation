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


def write(payload, repo_root):
    """Write all three surfaces. Returns the markdown that was produced."""
    text = "\n".join(_lines(payload)) + "\n"

    (repo_root / "STATUS.md").write_text(text, encoding="utf-8")
    (repo_root / "status.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

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
