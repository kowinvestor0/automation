"""GitHub Cloud Sync Manager: Syncs secrets and triggers cloud workflow runs."""
from __future__ import annotations

import base64
import json
import logging
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("GitHubSync")
DEFAULT_REPO = "kowinvestor0/automation"

def get_git_token() -> Optional[str]:
    try:
        p = subprocess.Popen(["git", "credential", "fill"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, _ = p.communicate("protocol=https\nhost=github.com\n\n")
        for line in out.strip().splitlines():
            if line.startswith("password="):
                return line[9:].strip()
    except Exception as e:
        logger.warning(f"Error getting git token: {e}")
    return None

def _github_api_request(url: str, token: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Any:
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AutoMakeMoney-Sync"
    }
    body = json.dumps(data).encode("utf-8") if data else None
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 204:
                return {}
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        logger.warning(f"GitHub API error {e.code}")
        return None
    except Exception as e:
        logger.warning(f"GitHub API error {e}")
        return None

def _encrypt_secret(public_key_b64: str, secret_value: str) -> Optional[str]:
    try:
        from nacl import encoding, public as nacl_public
        pk = nacl_public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
        sealed = nacl_public.SealedBox(pk).encrypt(secret_value.encode("utf-8"))
        return base64.b64encode(sealed).decode("utf-8")
    except Exception as e:
        logger.warning(f"Encryption error {e}")
        return None

def sync_secrets_to_github(secrets: Dict[str, str], repo: str = DEFAULT_REPO) -> Dict[str, Any]:
    token = get_git_token()
    if not token:
        return {"ok": False, "message": "Khong tim thay GitHub token tren Git Credential Manager."}
    key_url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    key_data = _github_api_request(key_url, token)
    if not key_data or "key" not in key_data:
        return {"ok": False, "message": "Khong the lay public key tu GitHub repo."}
    key_id = key_data["key_id"]
    public_key = key_data["key"]
    results = {}
    success_count = 0
    for name, val in secrets.items():
        if not val:
            continue
        encrypted = _encrypt_secret(public_key, str(val))
        if not encrypted:
            results[name] = "encrypt_failed"
            continue
        put_url = f"https://api.github.com/repos/{repo}/actions/secrets/{name}"
        res = _github_api_request(put_url, token, method="PUT", data={"encrypted_value": encrypted, "key_id": key_id})
        if res is not None:
            results[name] = "ok"
            success_count += 1
        else:
            results[name] = "failed"
    return {
        "ok": success_count > 0,
        "success_count": success_count,
        "total": len(secrets),
        "details": results,
        "message": f"Da dong bo {success_count}/{len(secrets)} secrets len GitHub Cloud!"
    }

def get_cloud_workflow_status(repo: str = DEFAULT_REPO, limit: int = 5) -> Dict[str, Any]:
    token = get_git_token()
    if not token:
        return {"ok": False, "message": "Khong tim thay GitHub token.", "runs": []}
    url = f"https://api.github.com/repos/{repo}/actions/runs?per_page={limit}"
    data = _github_api_request(url, token)
    if not data or "workflow_runs" not in data:
        return {"ok": False, "message": "Khong the lay danh sach workflow runs.", "runs": []}
    runs = []
    for r in data.get("workflow_runs", []):
        runs.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "run_number": r.get("run_number"),
            "status": r.get("status"),
            "conclusion": r.get("conclusion"),
            "created_at": r.get("created_at"),
            "html_url": r.get("html_url")
        })
    return {"ok": True, "total_count": data.get("total_count", 0), "runs": runs}

def trigger_cloud_workflow(quota: int = 6, lookahead: int = 7, repo: str = DEFAULT_REPO) -> Dict[str, Any]:
    token = get_git_token()
    if not token:
        return {"ok": False, "message": "Khong tim thay GitHub token."}
    url = f"https://api.github.com/repos/{repo}/actions/workflows/auto_story_producer.yml/dispatches"
    res = _github_api_request(url, token, method="POST", data={
        "ref": "main",
        "inputs": {"quota": str(quota), "lookahead": str(lookahead)}
    })
    if res is not None:
        return {"ok": True, "message": f"Da kich hoat GitHub Cloud tu dong san xuat ({quota} video/kenh/ngay)!"}
    return {"ok": False, "message": "Khong the kich hoat workflow. Vui long kiem tra quyen repo."}
