import os
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
worker_script = str(ROOT_DIR / "core" / "background_worker.py")

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

# Clear any stale stop signal
stop_signal = ROOT_DIR / "data" / "worker.stop"
if stop_signal.exists():
    try:
        stop_signal.unlink()
    except Exception:
        pass

p = subprocess.Popen(
    [pythonw_path, worker_script],
    cwd=str(ROOT_DIR),
    creationflags=flags,
    close_fds=True
)
print(f"Background worker daemon launched with PID: {p.pid}")
