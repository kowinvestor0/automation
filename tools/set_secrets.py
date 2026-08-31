"""Copy the keys from the local settings into the repository's Actions secrets.

Run once, after the repo exists. Everything a background run needs comes from
these; the local settings.json never leaves this machine.

    python tools/set_secrets.py --repo kowinvestor0/automation

Each value is sealed with the repository's own public key before it is sent, so
the plaintext never travels and nothing is printed. Only keys that are actually
set locally get uploaded - an empty one is skipped rather than written as blank,
because a blank secret shadows nothing and just looks configured.

GitHub refuses any secret whose name starts with GITHUB_, so that one is never
offered; a workflow already has its own token.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hub import settings                                        # noqa: E402

API = "https://api.github.com"
SKIP = {"GITHUB_TOKEN"}          # GitHub rejects the GITHUB_ prefix


def token_from_git():
    """Reuse whatever Git Credential Manager already holds for github.com."""
    try:
        filled = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    for line in filled.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    return ""


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


def seal(public_key_b64, value):
    from nacl import encoding, public

    key = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder())
    return base64.b64encode(public.SealedBox(key).encrypt(value.encode())).decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", required=True, help="OWNER/NAME")
    parser.add_argument("--dry-run", action="store_true",
                        help="list what would be uploaded, send nothing")
    args = parser.parse_args()

    token = (os.environ.get("GITHUB_TOKEN") or "").strip() or token_from_git()
    if not token:
        print("No GitHub credential. Set GITHUB_TOKEN, or sign in once with git.",
              file=sys.stderr)
        return 2

    cfg = settings.load()
    wanted = {}
    for name in settings.SECRET_NAMES:
        if name in SKIP:
            continue
        value = settings.secret(name, cfg)
        if value:
            wanted[name] = value

    if not wanted:
        print("Nothing to upload - no keys are set locally.", file=sys.stderr)
        return 1

    print(f"repo    {args.repo}")
    for name in sorted(wanted):
        print(f"  {name:<20} {len(wanted[name])} chars")
    missing = [n for n in settings.SECRET_NAMES
               if n not in SKIP and n not in wanted]
    if missing:
        print("not set locally, skipped: " + ", ".join(missing))

    if args.dry_run:
        print("\ndry run - nothing sent")
        return 0

    try:
        key = api(f"/repos/{args.repo}/actions/secrets/public-key", token)
        for name, value in sorted(wanted.items()):
            api(f"/repos/{args.repo}/actions/secrets/{name}", token,
                {"encrypted_value": seal(key["key"], value),
                 "key_id": key["key_id"]}, method="PUT")
            print(f"  set {name}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:250]
        print(f"\nGitHub said {e.code}: {detail}", file=sys.stderr)
        return 1

    print(f"\nDone. {len(wanted)} secret(s) on {args.repo}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
