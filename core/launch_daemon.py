"""Launch the background worker daemon IN-PROCESS.
This script is designed to be called by the VBS launcher which hides the console window.
It directly runs the worker's main() function - NO subprocess spawning needed.
"""
import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

os.chdir(str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR))

# Redirect stdout/stderr to log files for when running under VBS hidden window
import io
log_out = open(LOGS_DIR / "daemon_stdout.log", "a", encoding="utf-8", errors="replace", buffering=1)
log_err = open(LOGS_DIR / "daemon_stderr.log", "a", encoding="utf-8", errors="replace", buffering=1)
sys.stdout = log_out
sys.stderr = log_err

import traceback
import datetime

try:
    print(f"\n[{datetime.datetime.now()}] === launch_daemon.py starting ===", flush=True)
    from core.background_worker import main
    print(f"[{datetime.datetime.now()}] === Calling worker main() ===", flush=True)
    main()
except SystemExit as e:
    print(f"[{datetime.datetime.now()}] Worker exited with code: {e.code}", flush=True)
except BaseException as e:
    print(f"[{datetime.datetime.now()}] FATAL CRASH: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc(file=sys.stderr)
finally:
    print(f"[{datetime.datetime.now()}] === launch_daemon.py ended ===", flush=True)
    log_out.flush()
    log_err.flush()
