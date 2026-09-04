"""The control panel window.

The hub is built to run without anybody watching: GitHub Actions renders and
schedules on a timer. This window exists for the half-hour a month when the user
does sit at the PC - to paste a key, pick which Planly channels get posts, and
look at what the last runs did.

Three rules shape the whole file:

  * nothing slow happens on the Tk thread. Every network call and every render
    runs on a worker and comes back through `widget.after`, because a window
    that freezes while Planly is thinking looks broken.
  * nothing is saved behind the user's back except on a tab change; the Save
    button is the contract.
  * no exception from hub.* is allowed to reach the main loop. A wrong API key
    is a red line of Vietnamese text, never a traceback and a dead window.

The UI text is Vietnamese because the user is; the code and its comments are in
English like the rest of the hub.
"""
import datetime as dt
import json
import os
import queue
import re
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

# Lets `python desktop/app.py` work as well as the AutomationHub entry point.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from hub import gh, notify, planly                              # noqa: E402
from hub import paths as hub_paths                              # noqa: E402
from hub import settings as hub_settings                        # noqa: E402
from hub import state as hub_state                              # noqa: E402
from hub import status as hub_status                            # noqa: E402
from hub import workspace as hub_workspace                      # noqa: E402
from hub.paths import CODE, FACTORIES, factory_dir              # noqa: E402

APP_TITLE = "Automation Hub"
MONO = ("Consolas", 9)
TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
# Keeps a console from flashing up every time the app shells out on Windows.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
MAX_LOG_LINES = 4000

FACTORY_VI = {
    "us": "Xưởng US - tiếng Anh",
    "mx": "Xưởng Mexico - tiếng Tây Ban Nha",
}

MODE_VI = {"same_time": "Đăng cùng giờ", "spread": "Cách đều"}

# A route pins one stream of videos to one set of accounts. "default" is the
# fallback every unrouted stream uses, so it always stays first in the list.
ROUTE_VI = [
    ("default", "Chung - mọi luồng chưa chỉ định"),
    ("us", "Xưởng US (tiếng Anh)"),
    ("us:mysteries", "  US · bí ẩn"),
    ("us:truecrime", "  US · vụ án có thật"),
    ("us:facts", "  US · kiến thức"),
    ("us:history", "  US · lịch sử"),
    ("us:money", "  US · tiền bạc"),
    ("us:humor", "  US · hài"),
    ("us:commentary", "  US · bình luận viral"),
    ("mx", "Xưởng Mexico (tiếng Tây Ban Nha)"),
    ("mx:misterios", "  MX · bí ẩn"),
    ("mx:curiosidades", "  MX · chuyện lạ"),
    ("mx:historia", "  MX · lịch sử"),
    ("mx:lugares", "  MX · địa danh"),
    ("mx:humor", "  MX · hài"),
    ("mx:commentary", "  MX · bình luận viral"),
]
ROUTE_LABEL = {key: label.strip() for key, label in ROUTE_VI}
DISTRIBUTE_VI = {"unique": "Chia đều, không trùng", "mirror": "Tất cả kênh cùng video"}

STATUS_VI = {
    "ok": "Tốt", "partial": "Xong một phần", "failed": "Thất bại", "idle": "Chưa chạy",
}

# hub.settings.missing_keys() answers in English; the user reads Vietnamese.
KEY_WARNINGS = (
    ("GEMINI_API_KEY or ANTHROPIC_API_KEY",
     "Chưa có GEMINI_API_KEY hoặc ANTHROPIC_API_KEY - kịch bản sẽ lấy từ "
     "topics.json có sẵn thay vì viết mới bằng AI."),
    ("PEXELS_API_KEY",
     "Chưa có PEXELS_API_KEY - video chỉ dùng được ảnh từ Wikimedia."),
    ("PLANLY_API_KEY",
     "Đang bật đăng bài nhưng PLANLY_API_KEY còn trống - sẽ không xếp được lịch."),
)


# --------------------------------------------------------------- tiny helpers

def to_int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def to_number(value, default=0):
    """Timezone offsets can be half-hours, so this one keeps the fraction."""
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    return int(number) if number == int(number) else number


def vi_warning(text):
    for needle, viet in KEY_WARNINGS:
        if needle in text:
            return viet
    return text


def friendly(exc):
    """Anything thrown by hub.* turned into one readable Vietnamese line."""
    name = type(exc).__name__
    text = (str(exc) or name).strip()
    if isinstance(exc, planly.PlanlyError):
        return "Planly: " + text
    if isinstance(exc, gh.GitHubError):
        return "GitHub: " + text
    if name in ("URLError", "ConnectionError", "ConnectionRefusedError",
                "TimeoutError", "Timeout", "ConnectTimeout", "ReadTimeout",
                "socket.timeout", "SSLError"):
        return "Không kết nối được mạng: " + text
    if name == "ModuleNotFoundError" and "requests" in text:
        return ("Thiếu thư viện requests. Mở CMD và chạy: pip install requests")
    if name == "PermissionError":
        return "Không có quyền ghi vào thư mục: " + text
    return f"Lỗi {name}: {text}"


def run_async(widget, work, done=None, fail=None):
    """Run `work()` on a worker thread, deliver the answer on the Tk thread.

    Every network call in this file goes through here. `after` is the only
    thread-safe way back into Tk, and the widget may be gone by the time the
    worker finishes, so both hops swallow TclError.
    """
    def deliver(callback, value):
        try:
            widget.after(0, lambda: callback(value))
        except tk.TclError:
            pass                      # window closed while the worker ran

    def worker():
        try:
            value = work()
        except Exception as e:        # noqa: BLE001 - the GUI must survive anything
            if fail:
                deliver(fail, e)
            return
        if done:
            deliver(done, value)

    threading.Thread(target=worker, daemon=True).start()


def open_folder(path):
    """Show a folder in Explorer, creating it if the run has not made it yet."""
    path = Path(path)
    try:
        path.mkdir(parents=True, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(str(path))   # noqa: S606 - Windows shell open
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True, ""
    except Exception as e:            # noqa: BLE001
        return False, friendly(e)


def local_clock(iso, offset_hours):
    """A UTC ISO stamp shown on the clock the user actually reads."""
    for shape in ("%Y-%m-%dT%H:%M:%S.000Z", "%Y-%m-%dT%H:%M:%SZ",
                  "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            when = dt.datetime.strptime(iso, shape).replace(tzinfo=dt.timezone.utc)
        except (TypeError, ValueError):
            continue
        zone = dt.timezone(dt.timedelta(hours=float(offset_hours or 0)))
        return when.astimezone(zone).strftime("%d/%m %H:%M")
    return str(iso or "")


def machine_clock(iso):
    """GitHub timestamps, on this machine's own clock."""
    try:
        when = dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return str(iso or "")
    return when.astimezone().strftime("%d/%m %H:%M")


def scrollable(parent, height=190):
    """A frame that scrolls. Returns (outer, inner); pack widgets into inner."""
    outer = ttk.Frame(parent)
    background = ttk.Style().lookup("TFrame", "background") or None
    canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0, height=height)
    if background:
        canvas.configure(background=background)
    bar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)
    window = canvas.create_window((0, 0), window=inner, anchor="nw")

    def resized(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(window, width=canvas.winfo_width())

    def wheel(event):
        canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    inner.bind("<Configure>", resized)
    canvas.bind("<Configure>", resized)
    # bind_all only while the pointer is over this canvas, otherwise the wheel
    # would scroll every scrollable area on the tab at once.
    canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", wheel))
    canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
    canvas.configure(yscrollcommand=bar.set)
    canvas.pack(side="left", fill="both", expand=True)
    bar.pack(side="right", fill="y")
    return outer, inner


def text_pane(parent, height=12, mono=True):
    text = tk.Text(parent, height=height, wrap="none", undo=False)
    if mono:
        text.configure(font=MONO)
    bar = ttk.Scrollbar(parent, orient="vertical", command=text.yview)
    hbar = ttk.Scrollbar(parent, orient="horizontal", command=text.xview)
    text.configure(yscrollcommand=bar.set, xscrollcommand=hbar.set,
                   state="disabled")
    return text, bar, hbar


def set_text(widget, content):
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    widget.configure(state="disabled")


# ------------------------------------------------------------------ the panel

class ControlPanel:

    def __init__(self, root):
        self.root = root
        self.cfg = self._load_settings()
        self.process = None
        self.lines = queue.Queue()
        self.channels = []            # channels loaded from Planly, if any
        self.channel_vars = {}
        self.wanted_channels = list((self.cfg["publish"].get("channels") or ["all"]))
        # route key -> list of channel ids. "default" mirrors wanted_channels.
        self.routes = {k: list(v) for k, v in
                       (self.cfg["publish"].get("routes") or {}).items() if v}
        self.route_key = "default"
        pub0 = self.cfg["publish"]
        post0 = pub0.get("post_options") or {}
        self.v_when = tk.StringVar(value=pub0.get("when") or "now")
        self.v_duet = tk.StringVar(value=post0.get("duet") or "auto")
        self.v_stitch = tk.StringVar(value=post0.get("stitch") or "auto")
        self.v_duet_limit = tk.StringVar(
            value=str(post0.get("auto_disable_over_seconds") or 60))
        self.v_no_comment = tk.BooleanVar(value=post0.get("comment") == "disable")
        self.gh_runs = []
        self.ready = False
        self.preview_job = None
        self.drain_job = None

        self._skin()
        self._make_vars()
        self._build()
        self.ready = True
        self._drain()
        self._startup()

    # ---------------------------------------------------------------- setup

    def _load_settings(self):
        try:
            return hub_settings.load()
        except Exception:             # noqa: BLE001 - a broken file must not block launch
            import copy
            cfg = copy.deepcopy(hub_settings.DEFAULTS)
            cfg["workspace"] = str(hub_paths.default_workspace())
            return cfg

    def _skin(self):
        self.root.title(APP_TITLE)
        self.root.geometry("1120x780")
        self.root.minsize(960, 640)
        try:
            icon = CODE / "assets" / "app.ico"
            if icon.exists():
                self.root.iconbitmap(str(icon))
        except tk.TclError:
            pass
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(family="Segoe UI", size=10)
            except tk.TclError:
                pass
        self.big_font = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.small_font = tkfont.Font(family="Segoe UI", size=9)
        style.configure("Hint.TLabel", font=self.small_font, foreground="#5a5a5a")
        style.configure("Big.TLabel", font=self.big_font)

    def _make_vars(self):
        cfg = self.cfg
        pub, run, note, hub = (cfg["publish"], cfg["run"], cfg["notify"],
                               cfg["github"])

        self.v_workspace = tk.StringVar(value=cfg.get("workspace") or "")
        self.v_keys = {name: tk.StringVar(value=(cfg["keys"].get(name) or ""))
                       for name in hub_settings.SECRET_NAMES}
        self.v_repo = tk.StringVar(value=hub.get("repo") or "")
        self.v_run_wf = tk.StringVar(value=hub.get("run_workflow") or "videos.yml")
        self.v_build_wf = tk.StringVar(value=hub.get("build_workflow") or "build.yml")

        self.v_pub_enabled = tk.BooleanVar(value=bool(pub.get("enabled")))
        self.v_dry_run = tk.BooleanVar(value=bool(pub.get("dry_run", True)))
        self.v_team = tk.StringVar(value=pub.get("team_id") or "")
        self.v_all_channels = tk.BooleanVar(
            value=(not pub.get("channels")) or pub.get("channels") == ["all"])
        self.v_mode = tk.StringVar(value=pub.get("mode") or "same_time")
        self.v_gap = tk.StringVar(value=str(pub.get("gap_minutes", 120)))
        self.v_tz = tk.StringVar(value=str(pub.get("timezone_offset", 7)))
        self.v_lead = tk.StringVar(value=str(pub.get("lead_minutes", 30)))
        self.v_max_seconds = tk.StringVar(value=str(pub.get("max_seconds", 60)))
        self.v_distribute = tk.StringVar(value=pub.get("distribute") or "unique")
        self.times = list(pub.get("times") or [])

        self.v_run = {}
        for name in FACTORIES:
            block = run.get(name) or {}
            self.v_run[name] = {
                "enabled": tk.BooleanVar(value=bool(block.get("enabled", True))),
                "count": tk.StringVar(value=str(block.get("count", 3))),
                "niche": tk.StringVar(value=block.get("niche") or ""),
            }

        self.v_telegram = tk.BooleanVar(value=bool(note.get("telegram", True)))
        self.v_on_success = tk.BooleanVar(value=bool(note.get("on_success", True)))
        self.v_on_failure = tk.BooleanVar(value=bool(note.get("on_failure", True)))

        self.v_dispatch_count = tk.StringVar(value=str(
            (run.get("us") or {}).get("count", 3)))
        self.v_preview_count = tk.StringVar(value=str(self._planned_total()))
        self.v_render_only = tk.BooleanVar(value=False)
        self.v_show_keys = tk.BooleanVar(value=False)
        self.v_saved = tk.StringVar(value="")

        for var in (self.v_mode, self.v_gap, self.v_tz, self.v_lead,
                    self.v_distribute, self.v_preview_count, self.v_max_seconds):
            var.trace_add("write", lambda *_: self.schedule_preview())

    def _planned_total(self):
        total = 0
        for name in FACTORIES:
            block = (self.cfg["run"].get(name) or {})
            if block.get("enabled", True):
                total += to_int(block.get("count", 0), 0)
        return max(total, 1)

    def _build(self):
        outer = ttk.Frame(self.root, padding=(10, 8))
        outer.pack(fill="both", expand=True)

        self.tabs = ttk.Notebook(outer)
        self.tabs.pack(fill="both", expand=True)
        self.tab_dashboard = ttk.Frame(self.tabs, padding=10)
        self.tab_factories = ttk.Frame(self.tabs, padding=10)
        self.tab_publish = ttk.Frame(self.tabs, padding=10)
        self.tab_keys = ttk.Frame(self.tabs, padding=10)
        self.tab_settings = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.tab_dashboard, text="  Bảng điều khiển  ")
        self.tabs.add(self.tab_factories, text="  Xưởng video  ")
        self.tabs.add(self.tab_publish, text="  Đăng bài  ")
        self.tabs.add(self.tab_keys, text="  Khóa API  ")
        self.tabs.add(self.tab_settings, text="  Cài đặt  ")
        self.tabs.bind("<<NotebookTabChanged>>", self._tab_changed)

        self._build_dashboard()
        self._build_factories()
        self._build_publish()
        self._build_keys()
        self._build_settings()

        bar = ttk.Frame(outer)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Lưu cài đặt", command=self.save).pack(side="left")
        ttk.Label(bar, textvariable=self.v_saved, style="Hint.TLabel").pack(
            side="left", padx=10)
        ttk.Label(bar, text=f"Automation Hub {self._version()}",
                  style="Hint.TLabel").pack(side="right")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    @staticmethod
    def _version():
        try:
            from hub import __version__
            return __version__
        except Exception:             # noqa: BLE001
            return ""

    def _startup(self):
        """First-launch chores, none of which may block the window."""
        self.log("Automation Hub sẵn sàng.")
        self.log(f"Cài đặt: {hub_settings.path()}")

        def prepare():
            hub_paths.ensure_dirs()
            collected = []
            hub_workspace.ensure(collected.append)
            return collected

        run_async(self.root, prepare,
                  done=lambda lines: [self.log(line) for line in lines],
                  fail=lambda e: self.log("Không dựng được thư mục làm việc: "
                                          + friendly(e)))
        self.refresh_local_status()
        if (self.v_repo.get() or "").strip():
            self.refresh_runs(quiet=True)
        self.schedule_preview()
        self.refresh_key_warnings()

    # ------------------------------------------------------- tab 1: dashboard

    def _build_dashboard(self):
        tab = self.tab_dashboard
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(3, weight=1)

        head = ttk.Frame(tab)
        head.grid(row=0, column=0, sticky="ew")
        self.lbl_local = ttk.Label(head, text="Chưa có lần chạy nào trên máy này.",
                                   style="Big.TLabel")
        self.lbl_local.pack(anchor="w")
        self.lbl_github = ttk.Label(head, text="GitHub: chưa kiểm tra.",
                                    style="Hint.TLabel")
        self.lbl_github.pack(anchor="w", pady=(2, 0))

        actions = ttk.Frame(tab)
        actions.grid(row=1, column=0, sticky="ew", pady=(10, 6))
        ttk.Button(actions, text="Làm mới",
                   command=lambda: self.refresh_runs()).pack(side="left")
        ttk.Label(actions, text="   Số video:").pack(side="left")
        ttk.Spinbox(actions, from_=1, to=50, width=4,
                    textvariable=self.v_dispatch_count).pack(side="left", padx=(4, 8))
        ttk.Button(actions, text="Chạy ngay trên GitHub",
                   command=self.dispatch_run).pack(side="left")
        ttk.Button(actions, text="Mở trang Actions",
                   command=self.open_actions).pack(side="left", padx=6)
        ttk.Button(actions, text="Mở thư mục cài đặt",
                   command=lambda: self._open(hub_paths.data_dir())).pack(side="left")

        runs = ttk.LabelFrame(tab, text=" Các lần chạy gần đây trên GitHub ",
                              padding=6)
        runs.grid(row=2, column=0, sticky="ew")
        runs.columnconfigure(0, weight=1)
        columns = ("state", "number", "event", "when", "name")
        self.tree_runs = ttk.Treeview(runs, columns=columns, show="headings",
                                      height=9, selectmode="browse")
        for key, title, width in (("state", "Kết quả", 120),
                                  ("number", "Số", 60),
                                  ("event", "Khởi động bởi", 130),
                                  ("when", "Lúc", 110),
                                  ("name", "Quy trình", 320)):
            self.tree_runs.heading(key, text=title)
            self.tree_runs.column(key, width=width,
                                  anchor="w" if key != "number" else "center")
        scroll = ttk.Scrollbar(runs, orient="vertical",
                               command=self.tree_runs.yview)
        self.tree_runs.configure(yscrollcommand=scroll.set)
        self.tree_runs.grid(row=0, column=0, sticky="ew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree_runs.bind("<Double-1>", self._open_selected_run)
        ttk.Label(runs, text="Bấm đúp vào một dòng để mở nó trên GitHub.",
                  style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))

        report = ttk.LabelFrame(tab, text=" Báo cáo lần chạy gần nhất ", padding=6)
        report.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        report.columnconfigure(0, weight=1)
        report.rowconfigure(0, weight=1)
        self.txt_status, bar, hbar = text_pane(report, height=10)
        self.txt_status.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")

    def refresh_local_status(self):
        """status.json is written by every run; state.json remembers the rest."""
        payload = None
        for candidate in (CODE / "status.json",
                          hub_paths.data_dir() / "status.json",
                          Path(self.v_workspace.get() or ".") / "status.json"):
            try:
                if candidate.exists():
                    payload = json.loads(candidate.read_text(encoding="utf-8-sig"))
                    break
            except (OSError, ValueError):
                continue

        if payload:
            mark = hub_status.BADGE.get(payload.get("status"), hub_status.BADGE["idle"])
            state = STATUS_VI.get(payload.get("status"), payload.get("status", "?"))
            self.lbl_local.configure(
                text=f"{mark} Lần chạy gần nhất: {state} - "
                     f"{payload.get('videos', 0)} video, "
                     f"{payload.get('scheduled', 0)} bài đã xếp lịch "
                     f"({payload.get('finished_at', '')})")
            try:
                body = hub_status.short(payload)
            except Exception:         # noqa: BLE001
                body = json.dumps(payload, indent=2, ensure_ascii=False)
            set_text(self.txt_status, body)
            return

        try:
            last = (hub_state.load() or {}).get("last_run") or {}
        except Exception:             # noqa: BLE001
            last = {}
        if last:
            self.lbl_local.configure(
                text=f"Lần chạy gần nhất: {STATUS_VI.get(last.get('status'), '?')} - "
                     f"{last.get('videos', 0)} video ({last.get('finished_at', '')})")
        else:
            self.lbl_local.configure(
                text="Chưa có lần chạy nào trên máy này.")
            set_text(self.txt_status,
                     "Chưa có báo cáo. Sang tab \"Xưởng video\" và bấm "
                     "\"Chạy trên máy này\", hoặc chạy trên GitHub.")

    def refresh_runs(self, quiet=False):
        repo = gh.normalise_repo(self.v_repo.get())
        if not repo:
            self.lbl_github.configure(
                text="GitHub: chưa khai báo kho mã. Điền ở tab \"Cài đặt\".")
            if not quiet:
                self.info("Chưa có kho mã",
                          "Vào tab \"Cài đặt\" và điền kho mã dạng ten-ban/ten-kho.")
            return

        token = self.secret("GITHUB_TOKEN")
        workflow = (self.v_run_wf.get() or "").strip()
        self.lbl_github.configure(text="GitHub: đang tải...")

        def work():
            try:
                return gh.recent_runs(repo, token, limit=10, workflow=workflow)
            except gh.GitHubError:
                # A workflow file that does not exist yet is the normal state
                # before the first push; fall back to every run in the repo.
                return gh.recent_runs(repo, token, limit=10)

        run_async(self.root, work, done=self._show_runs,
                  fail=lambda e: self._runs_failed(e, quiet))

    def _runs_failed(self, exc, quiet):
        self.lbl_github.configure(text="GitHub: " + friendly(exc))
        if not quiet:
            self.warn("Không đọc được GitHub", friendly(exc))

    def _show_runs(self, runs):
        self.gh_runs = runs or []
        self.tree_runs.delete(*self.tree_runs.get_children())
        for run in self.gh_runs:
            self.tree_runs.insert("", "end", values=(
                gh.label(run), run.get("number") or "", run.get("event") or "",
                machine_clock(run.get("created_at")), run.get("name") or ""))
        if not self.gh_runs:
            self.lbl_github.configure(text="GitHub: kho mã chưa có lần chạy nào.")
            return
        newest = self.gh_runs[0]
        self.lbl_github.configure(
            text=f"GitHub: {gh.label(newest)} - lần chạy #{newest.get('number')} "
                 f"lúc {machine_clock(newest.get('created_at'))}")

    def _open_selected_run(self, _event=None):
        selected = self.tree_runs.selection()
        if not selected:
            return
        index = self.tree_runs.index(selected[0])
        if index < len(self.gh_runs):
            url = self.gh_runs[index].get("url")
            if url:
                webbrowser.open(url)

    def dispatch_run(self):
        repo = gh.normalise_repo(self.v_repo.get())
        workflow = (self.v_run_wf.get() or "").strip()
        token = self.secret("GITHUB_TOKEN")
        if not repo or not workflow:
            self.info("Thiếu thông tin",
                      "Cần khai báo kho mã và tên quy trình ở tab \"Cài đặt\".")
            return
        if not token:
            self.info("Chưa có GITHUB_TOKEN",
                      "Muốn bấm chạy từ đây thì cần GITHUB_TOKEN có quyền "
                      "\"workflow\". Điền ở tab \"Khóa API\".")
            return
        count = max(1, to_int(self.v_dispatch_count.get(), 3))
        if not messagebox.askyesno(
                "Chạy trên GitHub",
                f"Khởi động {workflow} trên {repo} với {count} video mỗi xưởng?",
                parent=self.root):
            return

        def work():
            # The workflow's inputs are defined in the repo, not here, so an
            # older or simpler videos.yml is retried without any inputs rather
            # than failing with a 422 the user cannot act on.
            try:
                return gh.dispatch(repo, workflow, token, "main",
                                   {"count": str(count)})
            except gh.GitHubError as first:
                text = str(first)
                if "Unexpected inputs" in text or "422" in text:
                    return gh.dispatch(repo, workflow, token, "main", {})
                if "No ref found" in text or "Not found" in text:
                    return gh.dispatch(repo, workflow, token, "master",
                                       {"count": str(count)})
                raise

        def started(_value):
            self.info("Đã gửi lệnh",
                      "GitHub đã nhận lệnh chạy. Bấm \"Làm mới\" sau khoảng "
                      "30 giây để thấy nó trong danh sách.")
            self.root.after(8000, lambda: self.refresh_runs(quiet=True))

        run_async(self.root, work, done=started,
                  fail=lambda e: self.warn("Không khởi động được", friendly(e)))

    def open_actions(self):
        repo = gh.normalise_repo(self.v_repo.get())
        if not repo:
            self.info("Chưa có kho mã", "Điền kho mã ở tab \"Cài đặt\" trước.")
            return
        webbrowser.open(f"https://github.com/{repo}/actions")

    # ------------------------------------------------------- tab 2: factories

    def _build_factories(self):
        tab = self.tab_factories
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        boxes = ttk.Frame(tab)
        boxes.grid(row=0, column=0, sticky="ew")
        boxes.columnconfigure(0, weight=1)
        boxes.columnconfigure(1, weight=1)

        for column, name in enumerate(FACTORIES):
            box = ttk.LabelFrame(boxes, text=f" {FACTORY_VI.get(name, name)} ",
                                 padding=8)
            box.grid(row=0, column=column, sticky="nsew", padx=(0, 8))
            box.columnconfigure(1, weight=1)
            variables = self.v_run[name]
            ttk.Checkbutton(box, text="Bật xưởng này",
                            variable=variables["enabled"],
                            command=self.schedule_preview).grid(
                row=0, column=0, columnspan=2, sticky="w")
            ttk.Label(box, text="Số video mỗi lần:").grid(row=1, column=0, sticky="w",
                                                          pady=4)
            ttk.Spinbox(box, from_=1, to=50, width=5, textvariable=variables["count"],
                        command=self.schedule_preview).grid(row=1, column=1,
                                                            sticky="w")
            ttk.Label(box, text="Chủ đề ép buộc:").grid(row=2, column=0, sticky="w")
            ttk.Entry(box, textvariable=variables["niche"]).grid(row=2, column=1,
                                                                 sticky="ew")
            ttk.Label(box, text="Để trống thì xưởng tự chọn chủ đề.",
                      style="Hint.TLabel").grid(row=3, column=0, columnspan=2,
                                                sticky="w", pady=(2, 6))
            buttons = ttk.Frame(box)
            buttons.grid(row=4, column=0, columnspan=2, sticky="w")
            ttk.Button(buttons, text="Chạy trên máy này",
                       command=lambda n=name: self.start_run([n])).pack(side="left")
            ttk.Button(buttons, text="Mở thư mục video",
                       command=lambda n=name: self._open(
                           factory_dir(n) / "output")).pack(side="left", padx=6)

        controls = ttk.Frame(tab)
        controls.grid(row=1, column=0, sticky="ew", pady=(10, 6))
        ttk.Button(controls, text="Chạy tất cả xưởng đang bật",
                   command=lambda: self.start_run(None)).pack(side="left")
        self.btn_stop = ttk.Button(controls, text="Dừng", command=self.stop_run,
                                   state="disabled")
        self.btn_stop.pack(side="left", padx=6)
        ttk.Checkbutton(controls, text="Chỉ dựng video, không đăng bài",
                        variable=self.v_render_only).pack(side="left", padx=10)
        ttk.Button(controls, text="Xóa nhật ký",
                   command=lambda: set_text(self.txt_log, "")).pack(side="right")
        self.lbl_run = ttk.Label(controls, text="", style="Hint.TLabel")
        self.lbl_run.pack(side="right", padx=8)

        log_box = ttk.LabelFrame(tab, text=" Nhật ký ", padding=6)
        log_box.grid(row=2, column=0, sticky="nsew")
        log_box.columnconfigure(0, weight=1)
        log_box.rowconfigure(0, weight=1)
        self.txt_log, bar, hbar = text_pane(log_box, height=18)
        self.txt_log.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")

    def log(self, message):
        """Thread-safe: the queue is drained by a timer on the Tk thread."""
        self.lines.put(str(message))

    def _drain(self):
        pending = []
        try:
            while True:
                pending.append(self.lines.get_nowait())
        except queue.Empty:
            pass
        if pending:
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", "\n".join(pending) + "\n")
            # A long render prints thousands of lines; keep the widget bounded.
            excess = int(self.txt_log.index("end-1c").split(".")[0]) - MAX_LOG_LINES
            if excess > 0:
                self.txt_log.delete("1.0", f"{excess}.0")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        self.drain_job = self.root.after(150, self._drain)

    def _run_command(self, names):
        count_flags = []
        if names and len(names) == 1:
            count_flags = ["--count", str(max(1, to_int(
                self.v_run[names[0]]["count"].get(), 3)))]
        base = [sys.executable]
        if not getattr(sys, "frozen", False):
            base.append(str(CODE / "AutomationHub.py"))
        command = base + ["run"]
        for name in names or []:
            command += ["--factory", name]
        if not names:
            command.append("--all")
        command += count_flags
        if self.v_render_only.get():
            command.append("--no-publish")
        return command

    def start_run(self, names):
        if self.process is not None:
            self.info("Đang chạy", "Một lần chạy đang diễn ra. Bấm \"Dừng\" trước.")
            return
        if names is None:
            names = [n for n in FACTORIES if self.v_run[n]["enabled"].get()]
            if not names:
                self.info("Không có xưởng nào bật",
                          "Bật ít nhất một xưởng rồi thử lại.")
                return
            names = []                # let run_factory read `enabled` itself
        # The subprocess reads settings.json, so what is on screen must be on
        # disk before it starts.
        self.save(quiet=True)
        command = self._run_command(names)
        self.log("")
        self.log("> " + " ".join(command))

        def spawn():
            return subprocess.Popen(
                command, cwd=str(CODE),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                env=os.environ.copy(), creationflags=NO_WINDOW)

        try:
            self.process = spawn()
        except Exception as e:        # noqa: BLE001
            self.process = None
            self.warn("Không chạy được", friendly(e))
            return

        self.btn_stop.configure(state="normal")
        self.lbl_run.configure(text="Đang chạy...")
        threading.Thread(target=self._pump, args=(self.process,),
                         daemon=True).start()

    def _pump(self, process):
        """Read the child's output on a worker; the Tk side only sees the queue."""
        try:
            for line in process.stdout:
                self.lines.put(line.rstrip())
        except Exception as e:        # noqa: BLE001
            self.lines.put(friendly(e))
        code = process.wait()
        self.lines.put(f"--- kết thúc, mã thoát {code} ---")
        try:
            self.root.after(0, lambda: self._run_finished(code))
        except tk.TclError:
            pass

    def _run_finished(self, code):
        self.process = None
        self.btn_stop.configure(state="disabled")
        self.lbl_run.configure(
            text="Xong." if code == 0 else f"Kết thúc với lỗi (mã {code}).")
        self.refresh_local_status()

    def stop_run(self):
        process = self.process
        if process is None:
            return
        if not messagebox.askyesno("Dừng", "Dừng lần chạy đang diễn ra?",
                                   parent=self.root):
            return
        self.log("Đang dừng...")
        try:
            if os.name == "nt":
                # run_factory spawns the factory itself; terminate() would only
                # kill the middleman and leave ffmpeg running.
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                               capture_output=True, creationflags=NO_WINDOW)
            else:
                process.terminate()
        except Exception as e:        # noqa: BLE001
            self.log("Không dừng được: " + friendly(e))

    # -------------------------------------------------------- tab 3: publish

    def _build_publish(self):
        tab = self.tab_publish
        tab.columnconfigure(0, weight=0)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)

        left = ttk.Frame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = ttk.Frame(tab)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        switches = ttk.LabelFrame(left, text=" Bật / tắt ", padding=8)
        switches.pack(fill="x")
        ttk.Checkbutton(switches, text="Bật đăng bài lên Planly",
                        variable=self.v_pub_enabled).pack(anchor="w")
        ttk.Checkbutton(switches, text="Chạy thử (dry run)",
                        variable=self.v_dry_run).pack(anchor="w")
        ttk.Label(switches, wraplength=330, style="Hint.TLabel",
                  text="Chạy thử: làm đủ mọi bước - kể cả tải video lên Planly - "
                       "nhưng dừng ngay trước khi tạo lịch. Không có bài nào lên "
                       "lịch. Tắt ô này thì bài sẽ được xếp thật.").pack(
            anchor="w", pady=(4, 0))

        channels = ttk.LabelFrame(left, text=" Kênh Planly ", padding=8)
        channels.pack(fill="x", pady=(8, 0))
        row = ttk.Frame(channels)
        row.pack(fill="x")
        ttk.Button(row, text="Tải danh sách kênh",
                   command=self.load_channels).pack(side="left")
        ttk.Checkbutton(row, text="Tất cả", variable=self.v_all_channels,
                        command=self._channels_toggled).pack(side="left", padx=8)
        ttk.Label(channels, text="Mã nhóm (team id, bắt buộc):",
                  style="Hint.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Entry(channels, textvariable=self.v_team).pack(fill="x")
        route_row = ttk.Frame(channels)
        route_row.pack(fill="x", pady=(8, 2))
        ttk.Label(route_row, text="Luồng video:").pack(side="left")
        self.v_route = tk.StringVar(value=ROUTE_LABEL["default"])
        self.cmb_route = ttk.Combobox(
            route_row, textvariable=self.v_route, state="readonly", width=30,
            values=[label for _key, label in ROUTE_VI])
        self.cmb_route.pack(side="left", padx=6)
        self.cmb_route.bind("<<ComboboxSelected>>", self._route_changed)
        ttk.Label(channels, style="Hint.TLabel", wraplength=330,
                  text="Chọn một luồng rồi tích những kênh mà luồng đó đăng lên. "
                       "Luồng nào không tích riêng thì dùng danh sách Chung.").pack(
            anchor="w")

        outer, self.channel_box = scrollable(channels, height=150)
        outer.pack(fill="x", pady=(6, 0))
        self.lbl_channels = ttk.Label(channels, text="", style="Hint.TLabel",
                                      wraplength=330)
        self.lbl_channels.pack(anchor="w", pady=(4, 0))
        self._render_channels()

        timing = ttk.LabelFrame(left, text=" Giờ đăng ", padding=8)
        timing.pack(fill="x", pady=(8, 0))
        ttk.Radiobutton(timing, text="Đăng ngay khi có video xong",
                        value="now", variable=self.v_when,
                        command=self._sync_when).pack(anchor="w")
        ttk.Radiobutton(timing, text="Xếp vào khung giờ bên dưới",
                        value="slots", variable=self.v_when,
                        command=self._sync_when).pack(anchor="w")
        ttk.Label(timing, wraplength=330, style="Hint.TLabel",
                  text="Đăng ngay: Planly nhận là đăng luôn, không chờ khung giờ. "
                       "Các ô giờ bên dưới lúc đó không dùng đến.").pack(
            anchor="w", pady=(2, 8))

        self.slot_widgets = []
        ttk.Radiobutton(timing, text="Đăng cùng giờ (mọi kênh cùng một phút)",
                        value="same_time", variable=self.v_mode,
                        command=self._sync_mode).pack(anchor="w")
        ttk.Radiobutton(timing, text="Cách đều (mỗi bài cách nhau một khoảng)",
                        value="spread", variable=self.v_mode,
                        command=self._sync_mode).pack(anchor="w")
        gap_row = ttk.Frame(timing)
        gap_row.pack(fill="x", pady=(4, 6))
        ttk.Label(gap_row, text="Cách nhau (phút):").pack(side="left")
        self.spin_gap = ttk.Spinbox(gap_row, from_=1, to=1440, width=6,
                                    textvariable=self.v_gap)
        self.spin_gap.pack(side="left", padx=6)

        ttk.Label(timing, text="Các khung giờ (giờ địa phương):").pack(anchor="w")
        times_row = ttk.Frame(timing)
        times_row.pack(fill="x")
        self.list_times = tk.Listbox(times_row, height=6, exportselection=False)
        self.list_times.pack(side="left", fill="x", expand=True)
        times_buttons = ttk.Frame(times_row)
        times_buttons.pack(side="left", padx=6)
        self.v_new_time = tk.StringVar(value="")
        ttk.Entry(times_buttons, textvariable=self.v_new_time, width=8).pack()
        ttk.Button(times_buttons, text="Thêm", command=self.add_time).pack(
            fill="x", pady=2)
        ttk.Button(times_buttons, text="Xóa", command=self.remove_time).pack(fill="x")
        ttk.Label(timing, text="Nhập dạng 09:00 rồi bấm Thêm.",
                  style="Hint.TLabel").pack(anchor="w", pady=(2, 0))
        self._render_times()

        post = ttk.LabelFrame(left, text=" Tuỳ chọn bài đăng (TikTok) ", padding=8)
        post.pack(fill="x", pady=(8, 0))
        ttk.Label(post, wraplength=330, style="Hint.TLabel",
                  text="TikTok từ chối video dài hơn khoảng 1 phút nếu còn bật "
                       "Duet/Stitch - bài sẽ không lên. Để \"Tự động\" là an "
                       "toàn nhất.").pack(anchor="w", pady=(0, 6))
        for label, var in (("Duet:", self.v_duet), ("Stitch:", self.v_stitch)):
            row = ttk.Frame(post)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=label, width=8).pack(side="left")
            for value, text in (("auto", "Tự động"), ("allow", "Luôn bật"),
                                ("disable", "Luôn tắt")):
                ttk.Radiobutton(row, text=text, value=value, variable=var,
                                command=self.schedule_preview).pack(side="left")
        cutoff = ttk.Frame(post)
        cutoff.pack(fill="x", pady=(6, 0))
        ttk.Label(cutoff, text="Tự tắt khi video dài hơn (giây):").pack(side="left")
        ttk.Spinbox(cutoff, from_=1, to=600, width=6,
                    textvariable=self.v_duet_limit).pack(side="left", padx=6)
        ttk.Checkbutton(post, text="Tắt bình luận",
                        variable=self.v_no_comment).pack(anchor="w", pady=(6, 0))

        deal = ttk.LabelFrame(left, text=" Chia video cho kênh ", padding=8)
        deal.pack(fill="x", pady=(8, 0))
        ttk.Radiobutton(deal, text="Chia đều, không trùng", value="unique",
                        variable=self.v_distribute).pack(anchor="w")
        ttk.Radiobutton(deal, text="Tất cả kênh cùng video", value="mirror",
                        variable=self.v_distribute).pack(anchor="w")

        numbers = ttk.LabelFrame(left, text=" Thông số ", padding=8)
        numbers.pack(fill="x", pady=(8, 0))
        numbers.columnconfigure(1, weight=1)
        for index, (text, var, low, high) in enumerate((
                ("Múi giờ (UTC+):", self.v_tz, -12, 14),
                ("Đặt lịch sớm nhất sau (phút):", self.v_lead, 0, 1440),
                ("Độ dài tối đa (giây):", self.v_max_seconds, 0, 600))):
            ttk.Label(numbers, text=text).grid(row=index, column=0, sticky="w", pady=2)
            ttk.Spinbox(numbers, from_=low, to=high, width=6,
                        textvariable=var).grid(row=index, column=1, sticky="w")
        ttk.Label(numbers, wraplength=330, style="Hint.TLabel",
                  text="Planly giấu bài dài hơn 60 giây khỏi lịch, nên để 60.").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        preview_head = ttk.Frame(right)
        preview_head.grid(row=0, column=0, sticky="ew")
        ttk.Label(preview_head, text="Xem trước lịch đăng",
                  style="Big.TLabel").pack(side="left")
        ttk.Label(preview_head, text="  Số video giả lập:").pack(side="left")
        ttk.Spinbox(preview_head, from_=1, to=100, width=4,
                    textvariable=self.v_preview_count).pack(side="left", padx=4)
        ttk.Button(preview_head, text="Xem lịch đã xếp",
                   command=self.open_schedule_window).pack(side="right")

        pane = ttk.Frame(right)
        pane.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        pane.columnconfigure(0, weight=1)
        pane.rowconfigure(0, weight=1)
        self.txt_preview, bar, hbar = text_pane(pane, height=24)
        self.txt_preview.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")

        self._sync_mode()

    def _sync_mode(self):
        self.spin_gap.configure(
            state="normal" if self.v_mode.get() == "spread" else "disabled")
        self.schedule_preview()

    def _render_times(self):
        self.list_times.delete(0, "end")
        for value in sorted(self.times):
            self.list_times.insert("end", value)

    def add_time(self):
        raw = (self.v_new_time.get() or "").strip()
        match = TIME_RE.match(raw)
        if not match:
            self.info("Giờ không hợp lệ",
                      "Nhập theo dạng 24 giờ, ví dụ 09:00 hoặc 21:30.")
            return
        value = f"{int(match.group(1)):02d}:{match.group(2)}"
        if value in self.times:
            self.info("Đã có", f"Khung giờ {value} đã có trong danh sách.")
            return
        self.times.append(value)
        self.v_new_time.set("")
        self._render_times()
        self.schedule_preview()

    def remove_time(self):
        selected = list(self.list_times.curselection())
        if not selected:
            self.info("Chưa chọn", "Chọn một khung giờ trong danh sách rồi bấm Xóa.")
            return
        for index in reversed(selected):
            value = self.list_times.get(index)
            if value in self.times:
                self.times.remove(value)
        if not self.times:
            # plan_slots falls back to 09:00 on an empty list; say so out loud.
            self.times = ["09:00"]
            self.info("Danh sách trống",
                      "Phải có ít nhất một khung giờ, đã đặt lại 09:00.")
        self._render_times()
        self.schedule_preview()

    def _channels_toggled(self):
        state = "disabled" if self.v_all_channels.get() else "normal"
        for child in self.channel_box.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass
        self.schedule_preview()

    def _render_channels(self, current=None):
        if current is None:
            current = (self.wanted_channels if self.route_key == "default"
                       else self.routes.get(self.route_key) or ["all"])
        for child in self.channel_box.winfo_children():
            child.destroy()
        self.channel_vars = {}
        if not self.channels:
            saved = [c for c in current if c != "all"]
            note = (f"Đang dùng {len(saved)} kênh đã lưu."
                    if saved else "Chưa tải danh sách kênh.")
            ttk.Label(self.channel_box, style="Hint.TLabel", wraplength=320,
                      text=note + " Bấm \"Tải danh sách kênh\" để lấy tên kênh "
                                  "thật từ Planly.").pack(anchor="w")
            self.lbl_channels.configure(text="")
            return
        wanted = set(current)
        for channel in self.channels:
            cid = channel.get("id")
            var = tk.BooleanVar(value=(self.v_all_channels.get() or cid in wanted))
            self.channel_vars[cid] = var
            label = f"{planly.describe(channel)}  ·  {cid}"
            ttk.Checkbutton(self.channel_box, text=label, variable=var,
                            command=self._channel_picked).pack(anchor="w")
        self._channels_toggled()
        self.lbl_channels.configure(
            text=f"Tài khoản này có {len(self.channels)} kênh. "
                 + self._route_summary())

    def _channel_picked(self):
        self.v_all_channels.set(False)
        self._channels_toggled()

    def _sync_when(self):
        """Grey out the slot controls when nothing is being scheduled."""
        state = "normal" if self.v_when.get() == "slots" else "disabled"
        for widget in getattr(self, "slot_widgets", []):
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass
        if self.v_when.get() == "slots":
            self._sync_mode()
        self.schedule_preview()

    def _route_changed(self, _event=None):
        """Remember the route being left before showing the next one."""
        self._store_route()
        # Match on the combobox index first. The labels are indented to show
        # which factory a niche belongs to, and matching on the text alone
        # silently picks the wrong route the moment anything trims it.
        index = self.cmb_route.current()
        if 0 <= index < len(ROUTE_VI):
            self.route_key = ROUTE_VI[index][0]
        else:
            wanted = (self.v_route.get() or "").strip()
            for key, text in ROUTE_VI:
                if text.strip() == wanted:
                    self.route_key = key
                    break
        self._load_route()

    def _store_route(self):
        picked = self._picked_channels()
        if self.route_key == "default":
            self.wanted_channels = picked
        elif picked == ["all"]:
            # "all" on a specific route means "no opinion" - drop it so the
            # stream falls back to the shared list instead of pinning itself
            # to every account by accident.
            self.routes.pop(self.route_key, None)
        else:
            self.routes[self.route_key] = picked

    def _load_route(self):
        current = (self.wanted_channels if self.route_key == "default"
                   else self.routes.get(self.route_key) or ["all"])
        self.v_all_channels.set(current == ["all"])
        self._render_channels(current)
        self.schedule_preview()

    def _route_summary(self):
        if not self.routes:
            return "Chưa chỉ định luồng nào - tất cả dùng danh sách Chung."
        parts = [f"{ROUTE_LABEL.get(k, k)}: {len(v)} kênh"
                 for k, v in sorted(self.routes.items())]
        return "Đã chỉ định - " + "; ".join(parts)

    def load_channels(self):
        key = self.secret("PLANLY_API_KEY")
        if not key:
            self.info("Chưa có khóa Planly",
                      "Điền PLANLY_API_KEY ở tab \"Khóa API\" rồi lưu lại.")
            return
        self.lbl_channels.configure(text="Đang tải danh sách kênh...")
        team_id = (self.v_team.get() or "").strip()

        def work():
            team = planly.resolve_team(key, team_id)
            return team, planly.list_channels(key, team)

        def done(result):
            team, channels = result
            self.v_team.set(team)
            self.channels = channels or []
            self._render_channels()
            if not self.channels:
                self.lbl_channels.configure(
                    text="Nhóm này chưa nối kênh mạng xã hội nào.")
            self.schedule_preview()

        run_async(self.root, work, done=done, fail=self._channels_failed)

    def _channels_failed(self, exc):
        self.lbl_channels.configure(text=friendly(exc))
        self.warn("Không tải được kênh", friendly(exc))

    def _preview_channels(self):
        """Real channels when they have been loaded, believable stand-ins if not."""
        wanted = self._picked_channels()
        if self.channels:
            chosen = planly.pick_channels(self.channels, wanted)
            if chosen:
                return chosen, ""
        if wanted and wanted != ["all"]:
            fake = [{"id": cid, "name": f"Kênh {index + 1}",
                     "social_network": "?"} for index, cid in enumerate(wanted)]
        else:
            fake = [{"id": f"demo-{i}", "name": f"Kênh {i}", "social_network": "?"}
                    for i in range(1, 4)]
        return fake, ("Chưa tải danh sách kênh - đây là kênh giả lập, "
                      "chỉ để xem cách chia giờ.")

    def schedule_preview(self):
        """Debounced: a spinbox fires per keystroke and plan_slots is not free."""
        if not self.ready:
            return
        if self.preview_job:
            try:
                self.root.after_cancel(self.preview_job)
            except tk.TclError:
                pass
        self.preview_job = self.root.after(250, self.refresh_preview)

    def refresh_preview(self):
        self.preview_job = None
        try:
            set_text(self.txt_preview, "\n".join(self._preview_lines()))
        except Exception as e:        # noqa: BLE001
            set_text(self.txt_preview, friendly(e))

    def _preview_lines(self):
        cfg = self._publish_cfg()
        channels, note = self._preview_channels()
        count = max(1, to_int(self.v_preview_count.get(), 6))
        videos = [{"folder": f"v{i + 1}", "title": f"Video {i + 1}",
                   "duration_seconds": 45} for i in range(count)]

        lines = [
            f"{MODE_VI.get(cfg['mode'], cfg['mode'])}  ·  "
            f"{DISTRIBUTE_VI.get(cfg['distribute'], cfg['distribute'])}  ·  "
            f"múi giờ UTC{cfg['timezone_offset']:+g}",
            f"{count} video  ->  {len(channels)} kênh"
            + (f"  ·  cách nhau {cfg['gap_minutes']} phút"
               if cfg["mode"] == "spread" else "  ·  mọi kênh đăng cùng một phút"),
        ]
        if note:
            lines.append(note)
        if cfg["dry_run"]:
            lines.append("Đang bật CHẠY THỬ: sẽ không có bài nào lên lịch thật.")
        if not cfg["enabled"]:
            lines.append("Đăng bài đang TẮT: lần chạy sẽ chỉ dựng video.")
        lines.append("")

        dealt = planly.distribute(videos, channels, cfg["distribute"])
        per_channel = max((len(items) for items in dealt.values()), default=0)
        if per_channel == 0:
            lines.append("Không có kênh nào để chia.")
            return lines
        slots = planly.plan_slots(per_channel, cfg)

        empty = [planly.describe(c) for c in channels if not dealt.get(c["id"])]
        if empty:
            lines.append("Không đủ video cho: " + ", ".join(empty))
            lines.append("")

        offset = cfg["timezone_offset"]
        for index in range(per_channel):
            lines.append(f"[{index + 1}]  {local_clock(slots[index], offset)}")
            for channel in channels:
                items = dealt.get(channel["id"]) or []
                if index < len(items):
                    lines.append(f"        {planly.describe(channel):<34} "
                                 f"<-  {items[index]['title']}")
            lines.append("")
        lines.append(f"Tổng cộng {sum(len(v) for v in dealt.values())} bài "
                     f"trên {len(channels)} kênh.")
        return lines

    # ------------------------------------------------- schedules already made

    def open_schedule_window(self):
        key = self.secret("PLANLY_API_KEY")
        if not key:
            self.info("Chưa có khóa Planly",
                      "Điền PLANLY_API_KEY ở tab \"Khóa API\" rồi lưu lại.")
            return

        window = tk.Toplevel(self.root)
        window.title("Lịch đã xếp trên Planly - 7 ngày tới")
        window.geometry("900x460")
        window.transient(self.root)
        frame = ttk.Frame(window, padding=8)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        head = ttk.Frame(frame)
        head.grid(row=0, column=0, sticky="ew")
        status = ttk.Label(head, text="Đang tải...", style="Hint.TLabel")
        status.pack(side="left")

        columns = ("when", "channel", "content", "id")
        tree = ttk.Treeview(frame, columns=columns, show="headings",
                            selectmode="browse")
        for name, title, width in (("when", "Giờ đăng", 140),
                                   ("channel", "Kênh", 200),
                                   ("content", "Nội dung", 380),
                                   ("id", "Mã lịch", 140)):
            tree.heading(name, text=title)
            tree.column(name, width=width, anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.grid(row=1, column=0, sticky="nsew", pady=6)
        scroll.grid(row=1, column=1, sticky="ns")

        rows = {}

        def load():
            status.configure(text="Đang tải...")

            def work():
                team = planly.resolve_team(key, (self.v_team.get() or "").strip())
                return planly.list_schedules(key, team, max_items=300)

            def done(groups):
                tree.delete(*tree.get_children())
                rows.clear()
                offset = to_number(self.v_tz.get(), 7)
                # One group can hold several channels. Each gets its own row so
                # the table reads like a calendar, but the id kept for deletion
                # is the GROUP's - Planly only deletes whole groups.
                for group in groups or []:
                    if not isinstance(group, dict):
                        continue
                    gid = str(group.get("id") or "")
                    when = local_clock(group.get("publishOn") or "", offset)
                    for item in group.get("schedules") or []:
                        channel = ((item.get("channel") or {}).get("name")
                                   or (item.get("channel") or {}).get("id") or "")
                        content = str(item.get("content") or "").replace("\n", " ")[:120]
                        node = tree.insert("", "end", values=(
                            when, channel, content, gid[:8]))
                        rows[node] = gid
                status.configure(
                    text=f"{len(rows)} bài trong {len(groups or [])} nhóm lịch.")

            run_async(window, work, done=done,
                      fail=lambda e: status.configure(text=friendly(e)))

        def delete_selected():
            selected = tree.selection()
            if not selected:
                self.info("Chưa chọn", "Chọn một dòng trong bảng trước.", window)
                return
            node = selected[0]
            sid = rows.get(node)
            values = tree.item(node, "values")
            if not sid:
                self.info("Thiếu mã nhóm lịch",
                          "Planly không trả về mã nhóm cho dòng này nên không xóa được.",
                          window)
                return
            # Planly only deletes whole groups, so say how many posts go with it.
            siblings = sum(1 for value in rows.values() if value == sid)
            extra = ("" if siblings <= 1 else
                     f"\nNhóm này có {siblings} bài - xóa là mất cả {siblings}.")
            if not messagebox.askyesno(
                    "Xóa lịch",
                    f"Xóa hẳn bài lúc {values[0]} trên {values[1]}?{extra}\n"
                    "Thao tác này không hoàn tác được.", parent=window):
                return
            status.configure(text="Đang xóa...")
            run_async(window, lambda: planly.delete_schedules(key, [sid]),
                      done=lambda _v: load(),
                      fail=lambda e: status.configure(text=friendly(e)))

        ttk.Button(head, text="Làm mới", command=load).pack(side="right")
        ttk.Button(head, text="Xóa bài đã chọn",
                   command=delete_selected).pack(side="right", padx=6)
        load()

    # ----------------------------------------------------------- tab 4: keys

    def _build_keys(self):
        tab = self.tab_keys
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        head = ttk.Frame(tab)
        head.grid(row=0, column=0, sticky="ew")
        ttk.Label(head, text="Khóa API", style="Big.TLabel").pack(side="left")
        ttk.Label(head, style="Hint.TLabel", wraplength=700,
                  text="  Khi chạy trên GitHub, khóa lấy từ Secrets của kho mã. "
                       "Ở đây là bản dùng cho máy này.").pack(side="left")

        box = ttk.LabelFrame(tab, text=" Khóa ", padding=8)
        box.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        box.columnconfigure(1, weight=1)
        self.key_entries = {}
        for index, name in enumerate(hub_settings.SECRET_NAMES):
            ttk.Label(box, text=name).grid(row=index, column=0, sticky="w", pady=3)
            entry = ttk.Entry(box, textvariable=self.v_keys[name], show="*")
            entry.grid(row=index, column=1, sticky="ew", padx=6)
            self.key_entries[name] = entry
            ttk.Button(box, text="Hiện", width=6,
                       command=lambda n=name: self._toggle_key(n)).grid(
                row=index, column=2)
            if os.environ.get(name):
                ttk.Label(box, text="(máy này đã có biến môi trường)",
                          style="Hint.TLabel").grid(row=index, column=3, sticky="w")

        tests = ttk.Frame(tab)
        tests.grid(row=2, column=0, sticky="ew", pady=(10, 4))
        ttk.Button(tests, text="Thử Planly",
                   command=self.test_planly).pack(side="left")
        ttk.Button(tests, text="Thử Telegram",
                   command=self.test_telegram).pack(side="left", padx=6)
        ttk.Button(tests, text="Thử GitHub",
                   command=self.test_github).pack(side="left")
        self.lbl_test = ttk.Label(tests, text="", style="Hint.TLabel")
        self.lbl_test.pack(side="left", padx=10)

        warn = ttk.LabelFrame(tab, text=" Cảnh báo ", padding=8)
        warn.grid(row=3, column=0, sticky="ew")
        warn.columnconfigure(0, weight=1)
        self.lbl_key_warnings = ttk.Label(warn, text="", justify="left",
                                          wraplength=900)
        self.lbl_key_warnings.grid(row=0, column=0, sticky="w")
        ttk.Button(warn, text="Kiểm tra lại",
                   command=self.refresh_key_warnings).grid(row=0, column=1,
                                                           sticky="e")

    def _toggle_key(self, name):
        entry = self.key_entries[name]
        entry.configure(show="" if entry.cget("show") else "*")

    def refresh_key_warnings(self):
        try:
            problems = hub_settings.missing_keys(self.collect())
        except Exception as e:        # noqa: BLE001
            problems = [friendly(e)]
        if not problems:
            self.lbl_key_warnings.configure(text="Không thiếu khóa nào quan trọng.")
            return
        self.lbl_key_warnings.configure(
            text="\n".join("- " + vi_warning(p) for p in problems))

    def _test(self, work):
        self.lbl_test.configure(text="Đang kiểm tra...")

        def done(result):
            ok, message = result
            self.lbl_test.configure(text=("OK - " if ok else "Hỏng - ") + message)
            (self.info if ok else self.warn)(
                "Kết quả kiểm tra" if ok else "Không dùng được", message)

        run_async(self.root, work, done=done,
                  fail=lambda e: (self.lbl_test.configure(text=friendly(e)),
                                  self.warn("Không kiểm tra được", friendly(e))))

    def test_planly(self):
        key = self.secret("PLANLY_API_KEY")
        if not key:
            self.info("Trống", "Chưa điền PLANLY_API_KEY.")
            return
        team = (self.v_team.get() or "").strip()
        self._test(lambda: planly.check_key(key, team))

    def test_telegram(self):
        cfg = self.collect()
        self._test(lambda: notify.test(cfg))

    def test_github(self):
        repo = gh.normalise_repo(self.v_repo.get())
        token = self.secret("GITHUB_TOKEN")
        self._test(lambda: gh.check_token(repo, token))

    # ------------------------------------------------------- tab 5: settings

    def _build_settings(self):
        tab = self.tab_settings
        tab.columnconfigure(0, weight=1)

        work = ttk.LabelFrame(tab, text=" Thư mục làm việc ", padding=8)
        work.grid(row=0, column=0, sticky="ew")
        work.columnconfigure(0, weight=1)
        ttk.Entry(work, textvariable=self.v_workspace).grid(row=0, column=0,
                                                            sticky="ew")
        ttk.Button(work, text="Chọn...", command=self.pick_workspace).grid(
            row=0, column=1, padx=6)
        ttk.Button(work, text="Mở thư mục",
                   command=lambda: self._open(self.v_workspace.get())).grid(
            row=0, column=2)
        ttk.Label(work, style="Hint.TLabel", wraplength=880,
                  text="Nơi đặt bản chạy của hai xưởng, video xuất ra và bộ nhớ "
                       "đệm. Đổi xong nhớ bấm Lưu rồi mở lại ứng dụng.").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

        reset = ttk.LabelFrame(tab, text=" Khôi phục mặc định ", padding=8)
        reset.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        for name in FACTORIES:
            ttk.Button(reset, text=f"Khôi phục {FACTORY_VI.get(name, name)}",
                       command=lambda n=name: self.reset_factory(n)).pack(side="left",
                                                                          padx=(0, 8))
        ttk.Label(reset, style="Hint.TLabel", wraplength=560,
                  text="Đặt lại config.json và topics.json về bản gốc. "
                       "Video đã dựng và bộ nhớ đệm giữ nguyên.").pack(side="left")

        hub_box = ttk.LabelFrame(tab, text=" GitHub ", padding=8)
        hub_box.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        hub_box.columnconfigure(1, weight=1)
        for index, (text, var, hint) in enumerate((
                ("Kho mã (owner/name):", self.v_repo, "ví dụ: hoang/automation-hub"),
                ("Quy trình chạy video:", self.v_run_wf, "videos.yml"),
                ("Quy trình dựng bản cài:", self.v_build_wf, "build.yml"))):
            ttk.Label(hub_box, text=text).grid(row=index, column=0, sticky="w", pady=3)
            ttk.Entry(hub_box, textvariable=var).grid(row=index, column=1,
                                                      sticky="ew", padx=6)
            ttk.Label(hub_box, text=hint, style="Hint.TLabel").grid(row=index,
                                                                    column=2,
                                                                    sticky="w")

        note = ttk.LabelFrame(tab, text=" Báo về Telegram ", padding=8)
        note.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Checkbutton(note, text="Bật báo qua Telegram",
                        variable=self.v_telegram).pack(anchor="w")
        ttk.Checkbutton(note, text="Báo cả khi chạy thành công",
                        variable=self.v_on_success).pack(anchor="w")
        ttk.Checkbutton(note, text="Báo khi chạy hỏng",
                        variable=self.v_on_failure).pack(anchor="w")

        where = ttk.LabelFrame(tab, text=" Tệp và thư mục ", padding=8)
        where.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        where.columnconfigure(0, weight=1)
        ttk.Label(where, justify="left", wraplength=880, text=(
            f"Cài đặt: {hub_settings.path()}\n"
            f"Bộ nhớ giữa các lần chạy: {hub_state.path()}\n"
            f"Mã chương trình: {CODE}")).grid(row=0, column=0, sticky="w")
        ttk.Button(where, text="Mở thư mục cài đặt",
                   command=lambda: self._open(hub_paths.data_dir())).grid(row=0,
                                                                          column=1)

    def pick_workspace(self):
        chosen = filedialog.askdirectory(
            parent=self.root, title="Chọn thư mục làm việc",
            initialdir=self.v_workspace.get() or str(hub_paths.default_workspace()))
        if chosen:
            self.v_workspace.set(chosen)

    def reset_factory(self, name):
        if not messagebox.askyesno(
                "Khôi phục mặc định",
                f"Đặt lại config.json và topics.json của "
                f"{FACTORY_VI.get(name, name)} về bản gốc?", parent=self.root):
            return
        run_async(self.root,
                  lambda: hub_workspace.reset_factory(name, self.log),
                  done=lambda target: self.info(
                      "Đã khôi phục", f"Đã đặt lại {FACTORY_VI.get(name, name)}."),
                  fail=lambda e: self.warn("Không khôi phục được", friendly(e)))

    # ------------------------------------------------------ settings plumbing

    def _picked_channels(self):
        """Whatever is ticked right now, for the route on screen."""
        if self.v_all_channels.get():
            return ["all"]
        if self.channel_vars:
            picked = [cid for cid, var in self.channel_vars.items() if var.get()]
            return picked or ["all"]
        return list(self.wanted_channels if self.route_key == "default"
                    else self.routes.get(self.route_key) or ["all"])

    def _current_channels(self):
        """The shared list - what an unrouted stream posts to."""
        if self.route_key == "default":
            return self._picked_channels()
        return list(self.wanted_channels)

    def _current_routes(self):
        self._store_route()
        return {k: list(v) for k, v in self.routes.items() if v}

    def _publish_cfg(self):
        return {
            "enabled": bool(self.v_pub_enabled.get()),
            "dry_run": bool(self.v_dry_run.get()),
            "team_id": (self.v_team.get() or "").strip(),
            "channels": self._current_channels(),
            "routes": self._current_routes(),
            "mode": self.v_mode.get() or "same_time",
            "times": sorted(self.times) or ["09:00"],
            "gap_minutes": max(1, to_int(self.v_gap.get(), 120)),
            "timezone_offset": to_number(self.v_tz.get(), 7),
            "lead_minutes": max(0, to_int(self.v_lead.get(), 30)),
            "distribute": self.v_distribute.get() or "unique",
            "when": self.v_when.get() or "now",
            "post_options": {
                "duet": self.v_duet.get() or "auto",
                "stitch": self.v_stitch.get() or "auto",
                "comment": "disable" if self.v_no_comment.get() else "keep",
                "privacy_level": "default",
                "auto_disable_over_seconds": max(
                    1, to_int(self.v_duet_limit.get(), 60)),
            },
            "max_seconds": max(0, to_int(self.v_max_seconds.get(), 60)),
            "channel_options": (self.cfg["publish"].get("channel_options") or {}),
        }

    def collect(self):
        """Everything on screen, as the settings.json shape. Does not write."""
        cfg = self.cfg
        cfg["workspace"] = (self.v_workspace.get() or "").strip()
        cfg["keys"] = {name: (var.get() or "").strip()
                       for name, var in self.v_keys.items()}
        cfg["github"] = {
            "repo": gh.normalise_repo(self.v_repo.get()),
            "run_workflow": (self.v_run_wf.get() or "").strip(),
            "build_workflow": (self.v_build_wf.get() or "").strip(),
        }
        cfg["publish"] = self._publish_cfg()
        cfg["run"] = {name: {
            "count": max(1, to_int(self.v_run[name]["count"].get(), 3)),
            "niche": (self.v_run[name]["niche"].get() or "").strip(),
            "enabled": bool(self.v_run[name]["enabled"].get()),
        } for name in FACTORIES}
        cfg["notify"] = {
            "telegram": bool(self.v_telegram.get()),
            "on_success": bool(self.v_on_success.get()),
            "on_failure": bool(self.v_on_failure.get()),
        }
        return cfg

    def secret(self, name):
        """A key as the rest of the hub would see it - environment first."""
        try:
            return hub_settings.secret(name, self.collect())
        except Exception:             # noqa: BLE001
            return (self.v_keys[name].get() or "").strip()

    def save(self, quiet=False):
        cfg = self.collect()
        self.wanted_channels = list(cfg["publish"]["channels"])
        self.routes = {k: list(v) for k, v in
                       (cfg["publish"].get("routes") or {}).items() if v}
        try:
            where = hub_settings.save(cfg)
        except Exception as e:        # noqa: BLE001
            self.warn("Không lưu được", friendly(e))
            return False
        # The keyless half also goes into the repo, because that copy is the one
        # the GitHub runs read. Without it the posting times set here would only
        # ever apply on this PC, and the background runs would keep using the
        # defaults. Returns None on an installed copy, which has no repo.
        public = None
        try:
            public = hub_settings.save_public(cfg)
        except Exception:             # noqa: BLE001
            public = None

        stamp = dt.datetime.now().strftime("%H:%M:%S")
        self.v_saved.set(f"Đã lưu lúc {stamp}")
        self.refresh_key_warnings()
        if not quiet:
            extra = (f"\n\nLịch đăng cũng đã ghi vào:\n{public}\n"
                     "Commit và push file này thì các lần chạy trên GitHub mới "
                     "dùng đúng cài đặt vừa chọn." if public else "")
            self.info("Đã lưu", f"Cài đặt đã ghi vào:\n{where}{extra}")
        return True

    def _tab_changed(self, _event=None):
        if not self.ready:
            return
        self.save(quiet=True)
        self.schedule_preview()

    # -------------------------------------------------------------- dialogs

    def info(self, title, message, parent=None):
        messagebox.showinfo(title, message, parent=parent or self.root)

    def warn(self, title, message, parent=None):
        messagebox.showerror(title, message, parent=parent or self.root)

    def _open(self, path):
        ok, problem = open_folder(path or ".")
        if not ok:
            self.warn("Không mở được thư mục", problem)

    def on_close(self):
        if self.process is not None:
            if not messagebox.askyesno(
                    "Thoát", "Một lần chạy đang diễn ra. Dừng và thoát?",
                    parent=self.root):
                return
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID",
                                    str(self.process.pid)],
                                   capture_output=True, creationflags=NO_WINDOW)
                else:
                    self.process.terminate()
            except Exception:         # noqa: BLE001
                pass
        for job in (self.drain_job, self.preview_job):
            if job:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
        self.root.destroy()


def main(argv=None):
    """Open the control panel. Returns a process exit code."""
    try:
        hub_paths.ensure_dirs()
    except Exception:                 # noqa: BLE001 - a read-only data dir is
        pass                          # the app's problem to report, not to die on
    try:
        root = tk.Tk()
    except tk.TclError as e:
        print(f"Khong mo duoc cua so: {e}", file=sys.stderr)
        return 1
    ControlPanel(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
