"""Planly Multi-Account Manager with safe local storage and auto-import."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.paths import ACCOUNTS_FILE


def _scan_legacy_accounts() -> List[Dict[str, Any]]:
    """Automatically find and import existing Planly accounts from previous apps."""
    found: List[Dict[str, Any]] = []
    seen_tokens = set()

    # 1. Check Electron UploadApp accounts file
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        upload_app_file = Path(appdata) / "upload-app" / "planly-accounts.json"
        if upload_app_file.exists():
            try:
                data = json.loads(upload_app_file.read_text(encoding="utf-8"))
                for acc in data.get("accounts", []):
                    token = acc.get("token", "").strip()
                    if token and token not in seen_tokens:
                        seen_tokens.add(token)
                        found.append({
                            "id": acc.get("id") or f"acc_{len(found)+1}",
                            "name": acc.get("name") or f"Planly Account {len(found)+1}",
                            "token": token,
                            "team_id": acc.get("teamId", "").strip(),
                            "channels": [],
                            "status": "imported",
                        })
            except Exception:
                pass

    # 2. Check D:\automation\settings.json
    legacy_settings = Path(r"D:\automation\settings.json")
    if legacy_settings.exists():
        try:
            cfg = json.loads(legacy_settings.read_text(encoding="utf-8"))
            # Check publish.accounts
            for acc in cfg.get("publish", {}).get("accounts", []):
                tok = acc.get("key", "").strip()
                if tok and tok not in seen_tokens:
                    seen_tokens.add(tok)
                    found.append({
                        "id": f"acc_{len(found)+1}",
                        "name": acc.get("name") or f"Account {len(found)+1}",
                        "token": tok,
                        "team_id": acc.get("team_id", "").strip(),
                        "channels": [],
                        "status": "imported",
                    })
            # Check root keys
            root_key = cfg.get("keys", {}).get("PLANLY_API_KEY", "").strip()
            root_team = cfg.get("keys", {}).get("PLANLY_TEAM_ID", "").strip()
            if root_key and root_key not in seen_tokens:
                seen_tokens.add(root_key)
                found.append({
                    "id": f"acc_{len(found)+1}",
                    "name": "Main Planly",
                    "token": root_key,
                    "team_id": root_team,
                    "channels": [],
                    "status": "imported",
                })
        except Exception:
            pass

    return found


class AccountManager:
    def __init__(self, storage_path: Optional[Path] = None):
        self.path = storage_path or ACCOUNTS_FILE
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        if not self.path.exists():
            accounts = _scan_legacy_accounts()
            self.save_all(accounts)

    def load_all(self) -> List[Dict[str, Any]]:
        try:
            if not self.path.exists():
                return []
            data = json.loads(self.path.read_text(encoding="utf-8"))
            accounts = data.get("accounts", [])
            for acc in accounts:
                for ch in acc.get("channels", []):
                    if not ch.get("tier"):
                        ch["tier"] = "monetized"
            return accounts
        except Exception:
            return []

    def save_all(self, accounts: List[Dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"accounts": accounts}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        for acc in self.load_all():
            if acc.get("id") == account_id:
                return acc
        return None

    def add_or_update(self, name: str, token: str, team_id: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        accounts = self.load_all()
        token = token.strip()
        team_id = team_id.strip()
        name = name.strip() or "Unnamed Account"

        if account_id:
            for i, acc in enumerate(accounts):
                if acc.get("id") == account_id:
                    accounts[i]["name"] = name
                    accounts[i]["token"] = token
                    accounts[i]["team_id"] = team_id
                    self.save_all(accounts)
                    return accounts[i]

        new_id = f"acc_{len(accounts) + 1}_{os.urandom(4).hex()}"
        new_acc = {
            "id": new_id,
            "name": name,
            "token": token,
            "team_id": team_id,
            "channels": [],
            "status": "active",
        }
        accounts.append(new_acc)
        self.save_all(accounts)
        return new_acc

    def delete_account(self, account_id: str) -> bool:
        accounts = self.load_all()
        filtered = [a for a in accounts if a.get("id") != account_id]
        if len(filtered) != len(accounts):
            self.save_all(filtered)
            return True
        return False

    def update_channels(self, account_id: str, channels: List[Dict[str, Any]]) -> bool:
        accounts = self.load_all()
        for i, acc in enumerate(accounts):
            if acc.get("id") == account_id:
                # Preserve existing tiers if already set
                existing_tiers = {c["id"]: c.get("tier") for c in acc.get("channels", []) if "id" in c}
                for ch in channels:
                    if ch.get("id") in existing_tiers and existing_tiers[ch["id"]]:
                        ch["tier"] = existing_tiers[ch["id"]]
                    elif "tier" not in ch:
                        ch["tier"] = "monetized"  # Default to monetized (>60s)
                accounts[i]["channels"] = channels
                accounts[i]["status"] = "connected"
                self.save_all(accounts)
                return True
        return False

    def toggle_channel_tier(self, channel_id: str, new_tier: Optional[str] = None) -> str:
        """Toggles between 'monetized' (>60s) and 'growth' (<45s) for a channel."""
        accounts = self.load_all()
        updated_tier = "monetized"
        for acc in accounts:
            for ch in acc.get("channels", []):
                if ch.get("id") == channel_id:
                    current = ch.get("tier", "monetized")
                    target = new_tier or ("growth" if current == "monetized" else "monetized")
                    ch["tier"] = target
                    updated_tier = target
        self.save_all(accounts)
        return updated_tier

