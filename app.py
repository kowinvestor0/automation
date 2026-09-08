"""Main entry point for Auto Make Money application."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui.server import run_server


def cleanup_zombie_instances() -> None:
    """Terminates any previous dangling instances of AutoMakeMoney or processes holding port 8888."""
    curr_pid = os.getpid()
    try:
        out = subprocess.check_output('netstat -ano | findstr :8888', shell=True, text=True, stderr=subprocess.DEVNULL)
        for line in out.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and "LISTENING" in line.upper():
                pid = int(parts[-1])
                if pid != curr_pid and pid > 0:
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(0.5)
    except Exception:
        pass


def find_free_port(start_port: int = 8888, max_tries: int = 50) -> int:
    """Finds the first free port starting from start_port to prevent [Errno 10048] address binding crashes."""
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start_port


def open_desktop_window(url: str, delay: float = 1.0):
    """Launches the UI as a standalone native Desktop Application Window (no browser address bar/tabs)."""
    time.sleep(delay)
    
    edge_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    
    # 1. Try Microsoft Edge in standalone App Mode (Standard on Windows 10/11)
    for p in edge_candidates:
        if os.path.exists(p):
            try:
                subprocess.Popen([p, f"--app={url}", "--window-size=1280,860"])
                return
            except Exception:
                pass

    # 2. Try Google Chrome App Mode
    for p in chrome_candidates:
        if os.path.exists(p):
            try:
                subprocess.Popen([p, f"--app={url}", "--window-size=1280,860"])
                return
            except Exception:
                pass

    # 3. Fallback to standard browser if no app mode browser is available
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    # Configure UTF-8 console output for Windows
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    # Clean up any lingering zombie instances
    cleanup_zombie_instances()

    # Dynamically bind to 8888 or the first available free port
    port = find_free_port(8888)
    url = f"http://localhost:{port}"

    # Auto open standalone desktop app window
    threading.Thread(target=open_desktop_window, args=(url,), daemon=True).start()

    # Start local dashboard server
    run_server(host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
