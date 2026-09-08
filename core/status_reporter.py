import sys
from pathlib import Path

# Ensure UTF-8 output
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr is not None:
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.planly_client import PlanlyClient
from core.account_manager import AccountManager

def main():
    print("====================================================================")
    print("KIEM TRA TRANG THAI HE THONG AUTO MAKE MONEY")
    print("====================================================================")

    lock = ROOT_DIR / "data" / "worker.lock"
    if lock.exists():
        try:
            pid = lock.read_text(encoding="utf-8").strip()
            print(f"Background Worker: DANG CHAY NGAM (PID: {pid})")
        except Exception:
            print("Background Worker: DANG CHAY NGAM")
    else:
        print("Background Worker: DANG DUNG")

    mgr = AccountManager()
    accounts = mgr.load_all()
    if accounts:
        acc = accounts[0]
        channels = acc.get("channels", [])
        print(f"Account: {acc.get('name')} | So kenh TikTok: {len(channels)}")
        try:
            client = PlanlyClient(acc["token"], acc["team_id"])
            groups = client.list_scheduled_groups()
            print(f"Tong so bai viet dang xep lich tren Planly: {len(groups)} bai")
            dates = {}
            for g in groups:
                p = (g.get("publishOn") or "")[:10]
                if p:
                    dates[p] = dates.get(p, 0) + 1
            if dates:
                for d, c in sorted(dates.items()):
                    print(f"   -> Ngay {d}: {c} video")
            else:
                print("   -> Chua co video nao dang xep lich.")
        except Exception as e:
            print(f"Loi kiem tra Planly: {e}")

    log_p = ROOT_DIR / "logs" / "background_worker.log"
    if log_p.exists():
        print("\nNhat ky moi nhat (logs/background_worker.log):")
        try:
            lines = log_p.read_text(encoding="utf-8", errors="ignore").splitlines()
            for l in lines[-8:]:
                print("   ", l)
        except Exception as e:
            print(f"   Loi doc log: {e}")
    print("====================================================================")

if __name__ == "__main__":
    main()
