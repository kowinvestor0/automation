@echo off
title Auto Make Money - Status
chcp 65001 >nul
cd /d "%~dp0"

python -c "
import sys
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding='utf-8', errors='replace')
    except: pass

from core.planly_client import PlanlyClient
from core.account_manager import AccountManager
from pathlib import Path

print('====================================================================')
print('KIEM TRA TRANG THAI HE THONG AUTO MAKE MONEY')
print('====================================================================')

lock = Path('data/worker.lock')
if lock.exists():
    print(f'Background Worker: DANG CHAY NGAM (PID: {lock.read_text().strip()})')
else:
    print('Background Worker: DANG DUNG')

mgr = AccountManager()
accounts = mgr.load_all()
if accounts:
    acc = accounts[0]
    client = PlanlyClient(acc['token'], acc['team_id'])
    groups = client.list_scheduled_groups()
    print(f'Tong so bai viet dang xep lich tren Planly: {len(groups)} bai')
    dates = {}
    for g in groups:
        p = g.get('publishOn', '')[:10]
        dates[p] = dates.get(p, 0) + 1
    for d, c in sorted(dates.items()):
        print(f'   -> Ngay {d}: {c} video')

log_p = Path('logs/background_worker.log')
if log_p.exists():
    print('\nNhat ky moi nhat (logs/background_worker.log):')
    lines = log_p.read_text(encoding='utf-8', errors='ignore').splitlines()
    for l in lines[-8:]:
        print('   ', l)
print('====================================================================')
"

echo.
pause
