"""Create the GitHub repository and push this folder to it, once.

Run it yourself - it is deliberately not wired into anything, because pushing
code to an account is not a thing a background job should decide to do:

    set GITHUB_TOKEN=ghp_...          (PowerShell: $env:GITHUB_TOKEN="ghp_...")
    python tools/push_to_github.py --name automation --private

The token needs the `repo` and `workflow` scopes - `workflow` because this repo
contains .github/workflows and GitHub refuses a push that adds workflow files
without it. Generate one at github.com/settings/tokens, and delete it when you
are done; it is only needed for this one push.

The token is read from the environment and never written to disk. If a push
fails, the error printed is the real one from git.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"


def run(*args, **kwargs):
    """git, with output shown. Raises on failure."""
    print("$ " + " ".join(args))
    return subprocess.run(args, cwd=str(ROOT), check=True, **kwargs)


def api(path, token, body=None, method="GET"):
    request = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "AutomationHub")
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8", "replace")
        return json.loads(raw) if raw else {}


def ensure_repo(name, token, private):
    """Return the clone URL, creating the repo if it is not there yet."""
    me = api("/user", token)
    owner = me["login"]
    try:
        existing = api(f"/repos/{owner}/{name}", token)
        print(f"repo already exists: {existing['html_url']}")
        return owner, existing["clone_url"]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    created = api("/user/repos", token, {
        "name": name,
        "private": bool(private),
        "description": "Automated short-video factories that render on a "
                       "schedule and post through Planly.",
        "has_issues": True,
        "has_wiki": False,
    }, method="POST")
    print(f"created {created['html_url']}")
    return owner, created["clone_url"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--name", default="automation", help="repository name")
    parser.add_argument("--private", action="store_true", default=True)
    parser.add_argument("--public", dest="private", action="store_false")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args()

    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if not token:
        print("Set GITHUB_TOKEN first (scopes: repo, workflow).", file=sys.stderr)
        return 2

    try:
        owner, clone_url = ensure_repo(args.name, token, args.private)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        print(f"GitHub said {e.code}: {detail}", file=sys.stderr)
        return 1

    if not (ROOT / ".git").exists():
        run("git", "init", "-b", args.branch)
    run("git", "add", "-A")
    # Nothing to commit is fine - the push below still needs to happen.
    subprocess.run(["git", "commit", "-m", "Automation Hub"], cwd=str(ROOT))

    remotes = subprocess.run(["git", "remote"], cwd=str(ROOT),
                             capture_output=True, text=True).stdout.split()
    if args.remote in remotes:
        run("git", "remote", "set-url", args.remote, clone_url)
    else:
        run("git", "remote", "add", args.remote, clone_url)

    # Auth as a one-shot header via `git -c`, not in the remote URL: a URL with
    # the token in it gets written into .git/config and printed back by any
    # later `git remote -v`.
    import base64
    header = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    print(f"$ git push -u {args.remote} {args.branch}")
    pushed = subprocess.run(
        ["git", "-c", f"http.extraheader=AUTHORIZATION: basic {header}",
         "push", "-u", args.remote, args.branch], cwd=str(ROOT))
    if pushed.returncode != 0:
        print("Push failed. If it mentions 'workflow', the token is missing the "
              "'workflow' scope.", file=sys.stderr)
        return 1

    print(f"\nDone: https://github.com/{owner}/{args.name}")
    print("Next: Settings > Secrets and variables > Actions, add the keys from "
          ".env.example, then run the 'Build' workflow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
