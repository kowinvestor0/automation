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

    from core.background_worker import is_pid_alive
    is_running = False
    lock = ROOT_DIR / "data" / "worker.lock"
    if lock.exists():
        try:
            pid = int(lock.read_text(encoding="utf-8").strip())
            if is_pid_alive(pid):
                is_running = True
                print(f"Background Worker: ĐANG CHẠY NGẦM 24/7 (PID: {pid})")
            else:
                print(f"Background Worker: ĐÃ DỪNG (Stale lock file PID {pid})")
        except Exception:
            print("Background Worker: ĐANG DỪNG")
    else:
        print("Background Worker: ĐANG DỪNG")

    mgr = AccountManager()
    accounts = mgr.load_all()
    if accounts:
        acc = accounts[0]
        channels = acc.get("channels", [])
        print(f"Account: {acc.get('name')} | Tổng số kênh TikTok: {len(channels)}")
        try:
            from core.background_worker import get_channel_scheduled_counts_by_date
            client = PlanlyClient(acc["token"], acc["team_id"])
            groups = client.list_scheduled_groups()
            print(f"Tổng số bài viết đang xếp lịch trên Planly: {len(groups)} bài")
            counts = get_channel_scheduled_counts_by_date(client)
            for c in channels:
                cid = c["id"]
                cname = c.get("name", cid)
                cdates = counts.get(cid, {})
                cdetail = ", ".join([f"{d}: {cnt} video" for d, cnt in sorted(cdates.items())]) if cdates else "Chưa có video"
                print(f"   • {cname:<24}: {cdetail}")
        except Exception as e:
            print(f"Lỗi kiểm tra Planly: {e}")

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
