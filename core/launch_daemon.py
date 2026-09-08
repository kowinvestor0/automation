import os
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
worker_script = str(ROOT_DIR / "core" / "background_worker.py")

sys.path.insert(0, str(ROOT_DIR))
from core.background_worker import is_pid_alive

# Clear any stale stop signal or dead lock file
stop_signal = ROOT_DIR / "data" / "worker.stop"
if stop_signal.exists():
    try:
        stop_signal.unlink()
    except Exception:
        pass

lock_file = ROOT_DIR / "data" / "worker.lock"
if lock_file.exists():
    try:
        pid = int(lock_file.read_text().strip())
        if is_pid_alive(pid):
            print(f"Background worker is already running with PID: {pid}")
            sys.exit(0)
        else:
            lock_file.unlink()
    except Exception:
        pass

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

p = subprocess.Popen(
    [pythonw_path, worker_script],
    cwd=str(ROOT_DIR),
    creationflags=flags,
    close_fds=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    stdin=subprocess.DEVNULL
)
print(f"Background worker daemon launched with PID: {p.pid}")
