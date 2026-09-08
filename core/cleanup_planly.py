import concurrent.futures
import json
import sys
import time
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.account_manager import AccountManager
from core.paths import DATA_DIR

def purge_all_planly_schedules():
    mgr = AccountManager()
    accounts = mgr.load_all()
    if not accounts:
        print("[Purge] No accounts found.")
        return

    acc = accounts[0]
    client = PlanlyClient(acc["token"], acc["team_id"])
    print(f"[Purge] Connecting to Planly for team: {acc['team_id']}...")
    total_deleted = client.clear_all_scheduled_posts()

    history_file = DATA_DIR / "published_history.json"
    if history_file.exists():
        history_file.write_text("{}", encoding="utf-8")
        print("[Purge] Reset local published_history.json")

    print(f"[Purge] SUCCESS: Deleted total {total_deleted} scheduled posts. Planly calendar is pristine!")

if __name__ == "__main__":
    purge_all_planly_schedules()
