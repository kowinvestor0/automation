"""Read-only view of GitHub Actions, so the desktop app can show what the
background runs are doing without the user leaving the app.

Read-only on purpose, with one exception: `dispatch` starts a run, because
"generate now" is the one thing worth being able to press from the couch.
Nothing here writes to the repository.

A token is only needed for a private repo (and for dispatch). Public repos
answer these endpoints unauthenticated, which keeps the first-run experience
free of a setup step.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
TIMEOUT = 25
UA = "AutomationHub"


class GitHubError(RuntimeError):
    pass


def _request(path, token="", method="GET", body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", UA)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        if e.code == 404:
            raise GitHubError("Not found. Check the repo name, and add a token if "
                              "the repo is private.")
        if e.code in (401, 403):
            raise GitHubError(f"GitHub refused the request ({e.code}). The token may "
                              f"be missing the 'actions' scope. {detail}")
        raise GitHubError(f"HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise GitHubError(f"Could not reach GitHub: {e.reason}")


def normalise_repo(repo):
    """Accept a URL or owner/name and return owner/name."""
    repo = (repo or "").strip().rstrip("/")
    if not repo:
        return ""
    if repo.startswith("http"):
        parts = urllib.parse.urlparse(repo).path.strip("/").split("/")
        repo = "/".join(parts[:2])
    if repo.endswith(".git"):
        repo = repo[:-4]
    return repo


def recent_runs(repo, token="", limit=10, workflow=""):
    """Latest workflow runs, newest first, flattened to what the UI shows."""
    repo = normalise_repo(repo)
    if not repo:
        raise GitHubError("No repository configured.")
    if workflow:
        path = f"/repos/{repo}/actions/workflows/{workflow}/runs?per_page={limit}"
    else:
        path = f"/repos/{repo}/actions/runs?per_page={limit}"
    data = _request(path, token)
    out = []
    for run in data.get("workflow_runs") or []:
        out.append({
            "name": run.get("name") or "",
            "number": run.get("run_number"),
            "status": run.get("status"),                 # queued|in_progress|completed
            "conclusion": run.get("conclusion") or "",   # success|failure|cancelled|...
            "event": run.get("event"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "url": run.get("html_url"),
        })
    return out


def latest_release(repo, token=""):
    """Used by the app's update check and by the 'where is my installer' link."""
    repo = normalise_repo(repo)
    data = _request(f"/repos/{repo}/releases/latest", token)
    assets = [{"name": a.get("name"), "size": a.get("size"),
               "url": a.get("browser_download_url")}
              for a in data.get("assets") or []]
    return {"tag": data.get("tag_name"), "url": data.get("html_url"),
            "published_at": data.get("published_at"), "assets": assets}


def status_file(repo, token="", branch="main"):
    """Fetch status.json straight from the repo - the same file the runs commit."""
    repo = normalise_repo(repo)
    path = f"/repos/{repo}/contents/status.json?ref={urllib.parse.quote(branch)}"
    data = _request(path, token)
    import base64
    content = data.get("content") or ""
    try:
        return json.loads(base64.b64decode(content).decode("utf-8", "replace"))
    except Exception:
        raise GitHubError("status.json in the repo is not readable JSON yet.")


def dispatch(repo, workflow, token, ref="main", inputs=None):
    """Start a run. Needs a token with the `workflow` scope."""
    repo = normalise_repo(repo)
    if not token:
        raise GitHubError("Starting a run needs a GitHub token with the "
                          "'workflow' scope.")
    _request(f"/repos/{repo}/actions/workflows/{workflow}/dispatches",
             token, method="POST", body={"ref": ref, "inputs": inputs or {}})
    return True


def check_token(repo, token):
    """Backs the GUI's Test button. Returns (ok, message)."""
    repo = normalise_repo(repo)
    if not repo:
        return False, "Fill in the repository first (owner/name)."
    try:
        runs = recent_runs(repo, token, limit=1)
    except GitHubError as e:
        return False, str(e)
    if not runs:
        return True, f"OK - {repo} is reachable, but has no workflow runs yet."
    run = runs[0]
    return True, (f"OK - last run #{run['number']} "
                  f"{run['conclusion'] or run['status']}")


LABEL = {
    ("completed", "success"): "\U0001F7E2 success",
    ("completed", "failure"): "\U0001F534 failed",
    ("completed", "cancelled"): "⚪ cancelled",
    ("completed", "skipped"): "⚪ skipped",
    ("in_progress", ""): "\U0001F7E1 running",
    ("queued", ""): "\U0001F7E1 queued",
}


def label(run):
    return LABEL.get((run.get("status"), run.get("conclusion") or ""),
                     f"{run.get('status')} {run.get('conclusion')}".strip())


def get_public_key(repo, token):
    """Fetch repo public key for encrypting Actions secrets."""
    repo = normalise_repo(repo)
    if not token:
        raise GitHubError("Setting secrets requires a GitHub token with 'repo' scope.")
    return _request(f"/repos/{repo}/actions/secrets/public-key", token)


def set_secret(repo, token, name, value, pub_key=None):
    """Encrypt and set a secret in GitHub Actions."""
    repo = normalise_repo(repo)
    if not token:
        raise GitHubError("Setting secrets requires a GitHub token with 'repo' scope.")
    if not pub_key:
        pub_key = get_public_key(repo, token)

    key_id = pub_key.get("key_id")
    pk_b64 = pub_key.get("key")
    if not key_id or not pk_b64:
        raise GitHubError("Could not retrieve repository public key.")

    try:
        import base64
        from nacl import encoding, public
        pk = public.PublicKey(pk_b64.encode("utf-8"), encoding.Base64Encoder())
        box = public.SealedBox(pk)
        encrypted = box.encrypt(value.encode("utf-8"))
        encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")
    except Exception as e:
        raise GitHubError(f"Failed to encrypt secret '{name}': {e}")

    _request(f"/repos/{repo}/actions/secrets/{name}", token, method="PUT",
             body={"encrypted_value": encrypted_b64, "key_id": key_id})
    return True


def sync_secrets(repo, token, secrets_dict):
    """Sync a dictionary of secrets to GitHub Actions."""
    repo = normalise_repo(repo)
    if not repo:
        raise GitHubError("No repository configured.")
    if not token:
        raise GitHubError("Syncing secrets requires a GitHub token with 'repo' scope.")
    pub_key = get_public_key(repo, token)
    synced = []
    errors = []
    for name, value in secrets_dict.items():
        v = (value or "").strip()
        if not v:
            continue
        try:
            set_secret(repo, token, name, v, pub_key=pub_key)
            synced.append(name)
        except Exception as e:
            errors.append(f"{name}: {e}")
    if errors:
        raise GitHubError(f"Synced {len(synced)} secret(s), but errors occurred:\n" + "\n".join(errors))
    return synced


def update_file(repo, token, file_path, content_str, commit_message, branch="main"):
    """Update or create a file in the repository using the Contents API."""
    import base64
    repo = normalise_repo(repo)
    if not token:
        raise GitHubError("Updating files requires a GitHub token with 'repo' scope.")
    encoded = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    body = {"message": commit_message, "content": encoded, "branch": branch}

    # Check if file exists to include its sha for update
    try:
        data = _request(f"/repos/{repo}/contents/{file_path}?ref={urllib.parse.quote(branch)}", token)
        if data.get("sha"):
            body["sha"] = data["sha"]
    except GitHubError:
        pass  # file does not exist yet

    return _request(f"/repos/{repo}/contents/{file_path}", token, method="PUT", body=body)
