"""Push this folder to GitHub, once. Run it yourself - pushing code to somebody's
account is not a decision a background job should make.

Two ways, and the first one needs no token at all:

  1. Make an empty repository at github.com/new (a phone browser will do), then

         python tools/push_to_github.py --repo YOURNAME/automation

     Git Credential Manager opens a browser the first time and you sign in to
     GitHub there. Nothing to generate, nothing to paste, and the sign-in is
     remembered for every push after this one.

  2. Or hand it a token and it will create the repository too:

         $env:GITHUB_TOKEN="ghp_..."       # PowerShell
         python tools/push_to_github.py --name automation --private

     The token needs the `repo` and `workflow` scopes - `workflow` because this
     repo contains .github/workflows, and GitHub rejects a push that adds
     workflow files without it.

Either way the token is read from the environment and never written to disk; the
auth header is passed per-command so it cannot end up in .git/config. If a push
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
    parser.add_argument("--repo", help="an existing repository as OWNER/NAME; "
                                       "with this, no token is needed")
    parser.add_argument("--name", default="automation", help="repository name")
    parser.add_argument("--private", action="store_true", default=True)
    parser.add_argument("--public", dest="private", action="store_false")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args()

    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()

    if args.repo:
        # The repository already exists, so nothing here needs the API. Git
        # Credential Manager will open a browser sign-in on the first push.
        owner, _, name = args.repo.strip().strip("/").rpartition("/")
        if not owner or not name:
            print("--repo wants OWNER/NAME, e.g. --repo kow/automation",
                  file=sys.stderr)
            return 2
        clone_url = f"https://github.com/{owner}/{name}.git"
        print(f"pushing to existing repo {owner}/{name}")
    elif token:
        try:
            owner, clone_url = ensure_repo(args.name, token, args.private)
            name = args.name
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            print(f"GitHub said {e.code}: {detail}", file=sys.stderr)
            return 1
    else:
        print("Nothing to push to yet. Either:\n"
              "  - make an empty repo at https://github.com/new, then rerun with\n"
              "      --repo YOURNAME/automation\n"
              "  - or set GITHUB_TOKEN (scopes: repo, workflow) and this will "
              "create the repo for you.", file=sys.stderr)
        return 2

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

    command = ["git"]
    if token:
        # Auth as a one-shot header via `git -c`, not in the remote URL: a URL
        # with the token in it gets written into .git/config and handed back by
        # any later `git remote -v`.
        import base64
        header = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        command += ["-c", f"http.extraheader=AUTHORIZATION: basic {header}"]
    else:
        print("\nNo token set, so git will ask Credential Manager to sign you in.")
        print("A browser window opens - approve it there, once.")

    command += ["push", "-u", args.remote, args.branch]
    print(f"$ git push -u {args.remote} {args.branch}")
    if subprocess.run(command, cwd=str(ROOT)).returncode != 0:
        print("\nPush failed. Two usual reasons:\n"
              "  - 'workflow' in the message: the token lacks the workflow scope\n"
              "  - 'not found': the repo name is wrong, or it is not yours",
              file=sys.stderr)
        return 1

    print(f"\nDone: https://github.com/{owner}/{name}")
    print("Next: Settings > Secrets and variables > Actions, add the keys from "
          ".env.example, then run the 'Build' workflow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
