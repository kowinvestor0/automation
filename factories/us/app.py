"""Desktop app for the short-video factory.

Tkinter on purpose: it ships with Python, so the packaged exe stays small and
there is no GUI toolkit to install on a fresh machine.

    python app.py           run it
    python build_exe.py     package it into dist/VideoFactory.exe
"""
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

from pipeline.util import ROOT, bootstrap, load_dotenv, save_json

bootstrap()
load_dotenv()

CONFIG_PATH = ROOT / "config.json"
ENV_PATH = ROOT / ".env"
OUT_DIR = ROOT / "output"

NICHES = ["mysteries", "truecrime", "facts", "history", "money", "humor"]
PROVIDERS = ["auto", "gemini", "claude", "bank"]
VOICES = [
    "en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural",
    "en-US-AvaMultilingualNeural", "en-US-EmmaMultilingualNeural",
    "en-US-AndrewNeural", "en-US-BrianNeural", "en-US-AvaNeural",
    "en-US-EmmaNeural", "en-US-GuyNeural", "en-US-JennyNeural",
    "en-US-EricNeural", "en-US-RogerNeural", "en-US-SteffanNeural",
    "en-US-AriaNeural", "en-US-MichelleNeural", "en-US-ChristopherNeural",
]
KEYS = [
    ("GEMINI_API_KEY", "Gemini (scripts)", "https://aistudio.google.com/apikey"),
    ("ANTHROPIC_API_KEY", "Claude (scripts)", "https://console.anthropic.com/settings/keys"),
    ("PEXELS_API_KEY", "Pexels (stock video)", "https://www.pexels.com/api/"),
    ("PLANLY_API_KEY", "Planly (scheduling)", "https://app.planly.com/settings/security"),
]

BG = "#14161c"
PANEL = "#1c1f27"
FG = "#e6e8ee"
MUTED = "#9aa1b1"
ACCENT = "#4f8cff"


class Tee:
    """Mirrors the pipeline's prints into the log pane without losing the console."""

    def __init__(self, sink, original):
        self.sink = sink
        self.original = original

    def write(self, text):
        if text:
            self.sink.put(text)
        if self.original:
            try:
                self.original.write(text)
            except Exception:
                pass

    def flush(self):
        if self.original:
            try:
                self.original.flush()
            except Exception:
                pass


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = self._load_config()
        self.log_queue = queue.Queue()
        self.worker = None
        self.cancel = threading.Event()

        root.title("Video Factory - US")
        root.geometry("1120x760")
        root.minsize(960, 640)
        root.configure(bg=BG)
        self._init_style()

        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=12)
        body.columnconfigure(0, weight=0, minsize=430)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_settings(body)
        self._build_log(body)
        self._build_footer(root)

        self._check_ffmpeg()
        self._pump_log()

    # ------------------------------------------------------------------ setup

    def _init_style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", background=PANEL, foreground=FG, fieldbackground=PANEL,
                     bordercolor="#2c3140", lightcolor=PANEL, darkcolor=PANEL)
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", background=BG, foreground=MUTED,
                     padding=(14, 7), borderwidth=0)
        st.map("TNotebook.Tab",
               background=[("selected", PANEL)], foreground=[("selected", FG)],
               lightcolor=[("selected", PANEL)], darkcolor=[("selected", PANEL)],
               bordercolor=[("selected", PANEL)])

        # A readonly Combobox keeps the platform's selection colors, which on a
        # dark theme comes out white text on white. Every state has to be pinned.
        st.configure("TCombobox", arrowcolor=FG, borderwidth=0)
        st.map("TCombobox",
               fieldbackground=[("readonly", "#22262f"), ("disabled", "#22262f")],
               background=[("readonly", "#2c3140")],
               foreground=[("readonly", FG), ("disabled", MUTED)],
               selectbackground=[("readonly", "#22262f")],
               selectforeground=[("readonly", FG)],
               lightcolor=[("readonly", "#22262f")],
               darkcolor=[("readonly", "#22262f")],
               bordercolor=[("readonly", "#2c3140")])
        # The dropdown list is a plain Tk Listbox, styled through the option DB.
        self.root.option_add("*TCombobox*Listbox.background", "#22262f")
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")
        self.root.option_add("*TCombobox*Listbox.font", "TkDefaultFont")
        st.configure("TCheckbutton", background=PANEL, foreground=FG)
        st.map("TCheckbutton", background=[("active", PANEL)])
        st.configure("Horizontal.TProgressbar", background=ACCENT,
                     troughcolor="#22262f", borderwidth=0)

    def _load_config(self):
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            messagebox.showerror("config.json", f"Could not read config.json:\n{e}")
            return {}

    # --------------------------------------------------------------- settings

    def _build_settings(self, parent):
        tabs = ttk.Notebook(parent)
        tabs.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        content = self._tab(tabs, "Content")
        look = self._tab(tabs, "Look & sound")
        publish = self._tab(tabs, "Publishing")
        keys = self._tab(tabs, "API keys")

        self.v = {}

        # --- Content
        self._combo(content, "Niche", "niche", NICHES, self.cfg.get("niche", "mysteries"))
        self._spin(content, "Videos per run", "count", 1, 50, 1)
        self._spin(content, "Target length (s)", "target_seconds", 15, 180,
                   self.cfg.get("target_seconds", 45))
        self._spin(content, "Scenes per video", "scene_count", 3, 14,
                   self.cfg.get("scene_count", 7))
        self._entry(content, "Force topic (optional)", "topic", "")
        self._sep(content)
        self._combo(content, "Script writer", "provider", PROVIDERS,
                    self.cfg.get("provider", "auto"))
        self._entry(content, "Gemini model", "gemini_model",
                    self.cfg.get("gemini_model", "gemini-2.5-pro"))
        self._note(content, "auto = use whichever key you have. Gemini first,\n"
                            "then Claude, then the offline topics.json bank.")

        # --- Look & sound
        self._combo(look, "Voice", "voice", VOICES,
                    self.cfg.get("voice", VOICES[0]))
        self._entry(look, "Voice speed", "voice_rate", self.cfg.get("voice_rate", "+10%"))
        self._note(look, "Per-niche voices in config.json override this\n"
                         "unless you change the voice here.")
        self._sep(look)
        self._check(look, "Scene transitions", "transitions", self.cfg.get("transitions", True))
        self._check(look, "Camera shake on the hook", "camera_shake",
                    self.cfg.get("camera_shake", True))
        self._check(look, "Sound effects", "sfx", self.cfg.get("sfx", True))
        self._scale(look, "Music volume", "music_volume", self.cfg.get("music_volume", 0.2))
        self._scale(look, "SFX volume", "sfx_volume", self.cfg.get("sfx_volume", 0.35))
        self._sep(look)
        self._combo(look, "Quality", "quality", ["fast", "high", "max"],
                    self.cfg.get("quality", "high"))
        self._combo(look, "Resolution", "resolution", ["1080p", "1440p", "4k"],
                    self.cfg.get("resolution", "1080p"))
        self._note(look, "1080p is what TikTok, Reels and Shorts actually serve.\n"
                         "Bigger just gets re-encoded down on upload.")

        # --- Publishing
        pl = self.cfg.get("planly") or {}
        self._check(publish, "Send finished videos to Planly", "planly_enabled",
                    pl.get("enabled", False))
        self._check(publish, "Dry run (upload but do not schedule)", "planly_dry_run",
                    pl.get("dry_run", True))
        self._entry(publish, "Post times (local)", "planly_slots",
                    ", ".join(pl.get("slots") or ["09:00", "13:00", "18:00"]))
        self._spin(publish, "Timezone offset (hours)", "planly_timezone_offset",
                   -12, 14, pl.get("timezone_offset", 7))
        self._spin(publish, "Earliest slot (minutes ahead)", "planly_lead_minutes",
                   0, 1440, pl.get("lead_minutes", 30))
        self._entry(publish, "Team id (blank = first)", "planly_team_id",
                    pl.get("team_id", ""))
        self._entry(publish, "Channel ids", "planly_channels",
                    ", ".join(pl.get("channels") or ["all"]))
        tk.Button(publish, text="Load channels from Planly", command=self._load_channels,
                  bg="#2c3140", fg=FG, relief="flat", padx=12, pady=6,
                  activebackground="#3a4152", cursor="hand2").pack(anchor="w",
                                                                   padx=14, pady=6)
        self._note(publish, "Leave 'all' to post to every connected channel.\n"
                            "Turn dry run off only once you have seen a test run\n"
                            "land on the Planly calendar the way you expect.")

        # --- API keys
        self.key_vars, self.key_status = {}, {}
        for env_name, label, url in KEYS:
            self._key_row(keys, env_name, label, url)
        self._note(keys, "Keys are saved to a .env file next to the app.\n"
                         "Nothing here is sent anywhere except that provider.")
        tk.Button(keys, text="Save keys to .env", command=self._save_keys,
                  bg=ACCENT, fg="white", relief="flat", padx=12, pady=6,
                  activebackground="#3f78e0", activeforeground="white",
                  cursor="hand2").pack(anchor="w", padx=14, pady=(4, 12))

    def _tab(self, tabs, title):
        frame = tk.Frame(tabs, bg=PANEL)
        tabs.add(frame, text=title)
        return frame

    def _row(self, parent, label):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=14, pady=5)
        tk.Label(row, text=label, bg=PANEL, fg=MUTED, width=22, anchor="w").pack(side="left")
        return row

    def _combo(self, parent, label, key, values, initial):
        row = self._row(parent, label)
        var = tk.StringVar(value=initial)
        combo = ttk.Combobox(row, textvariable=var, values=values, state="readonly",
                             width=26)
        combo.pack(side="left", fill="x", expand=True)
        combo.bind("<<ComboboxSelected>>", lambda e: e.widget.selection_clear())
        self.v[key] = var

    def _entry(self, parent, label, key, initial):
        row = self._row(parent, label)
        var = tk.StringVar(value=str(initial))
        tk.Entry(row, textvariable=var, bg="#22262f", fg=FG, relief="flat",
                 insertbackground=FG).pack(side="left", fill="x", expand=True, ipady=3)
        self.v[key] = var

    def _spin(self, parent, label, key, lo, hi, initial):
        row = self._row(parent, label)
        var = tk.StringVar(value=str(initial))
        tk.Spinbox(row, from_=lo, to=hi, textvariable=var, width=8, bg="#22262f",
                   fg=FG, relief="flat", buttonbackground="#2c3140",
                   insertbackground=FG).pack(side="left")
        self.v[key] = var

    def _check(self, parent, label, key, initial):
        var = tk.BooleanVar(value=bool(initial))
        ttk.Checkbutton(parent, text=label, variable=var).pack(anchor="w", padx=16, pady=3)
        self.v[key] = var

    def _scale(self, parent, label, key, initial):
        row = self._row(parent, label)
        var = tk.DoubleVar(value=float(initial))
        readout = tk.Label(row, text=f"{float(initial):.2f}", bg=PANEL, fg=FG, width=5)
        tk.Scale(row, from_=0.0, to=1.0, resolution=0.01, orient="horizontal",
                 variable=var, showvalue=False, bg=PANEL, fg=FG, relief="flat",
                 troughcolor="#22262f", highlightthickness=0,
                 command=lambda _v, lbl=readout, v=var: lbl.config(text=f"{v.get():.2f}")
                 ).pack(side="left", fill="x", expand=True)
        readout.pack(side="left")
        self.v[key] = var

    def _sep(self, parent):
        tk.Frame(parent, bg="#2c3140", height=1).pack(fill="x", padx=14, pady=8)

    def _note(self, parent, text):
        tk.Label(parent, text=text, bg=PANEL, fg=MUTED, justify="left",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=16, pady=(2, 8))

    def _key_row(self, parent, env_name, label, url):
        block = tk.Frame(parent, bg=PANEL)
        block.pack(fill="x", padx=14, pady=(10, 2))

        head = tk.Frame(block, bg=PANEL)
        head.pack(fill="x")
        tk.Label(head, text=label, bg=PANEL, fg=FG, anchor="w").pack(side="left")
        link = tk.Label(head, text="get a key", bg=PANEL, fg=ACCENT, cursor="hand2",
                        font=("Segoe UI", 8, "underline"))
        link.pack(side="right")
        link.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))

        entry_row = tk.Frame(block, bg=PANEL)
        entry_row.pack(fill="x", pady=3)
        var = tk.StringVar(value=os.environ.get(env_name, ""))
        tk.Entry(entry_row, textvariable=var, show="*", bg="#22262f", fg=FG,
                 relief="flat", insertbackground=FG).pack(side="left", fill="x",
                                                          expand=True, ipady=3)
        tk.Button(entry_row, text="Test", relief="flat", bg="#2c3140", fg=FG,
                  padx=10, cursor="hand2", activebackground="#3a4152",
                  command=lambda n=env_name: self._test_key(n)).pack(side="left", padx=(6, 0))

        status = tk.Label(block, text="", bg=PANEL, fg=MUTED, anchor="w",
                          font=("Segoe UI", 8), wraplength=380, justify="left")
        status.pack(fill="x")

        self.key_vars[env_name] = var
        self.key_status[env_name] = status

    # -------------------------------------------------------------------- log

    def _build_log(self, parent):
        panel = tk.Frame(parent, bg=PANEL)
        panel.grid(row=0, column=1, sticky="nsew")

        head = tk.Frame(panel, bg=PANEL)
        head.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(head, text="Output", bg=PANEL, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(head, text="Open folder", relief="flat", bg="#2c3140", fg=FG,
                  padx=10, cursor="hand2", activebackground="#3a4152",
                  command=self._open_output).pack(side="right")

        wrap = tk.Frame(panel, bg=PANEL)
        wrap.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        bar = tk.Scrollbar(wrap)
        bar.pack(side="right", fill="y")
        self.log = tk.Text(wrap, bg="#0f1116", fg="#c8cede", relief="flat",
                           insertbackground=FG, wrap="word", font=("Consolas", 9),
                           yscrollcommand=bar.set)
        self.log.pack(side="left", fill="both", expand=True)
        bar.config(command=self.log.yview)
        self.log.tag_config("step", foreground="#7aa2ff")
        self.log.tag_config("done", foreground="#4ade80")
        self.log.tag_config("fail", foreground="#f87171")
        self._write("Ready. Pick a niche and hit Generate.\n"
                    "No API key needed - it falls back to the built-in topic bank.\n\n")

    def _check_ffmpeg(self):
        """FFmpeg is the one thing the app cannot do without. Say so up front."""
        from pipeline.util import find_ffmpeg

        if find_ffmpeg():
            return
        self._write(
            "FFmpeg was not found.\n"
            "  Nothing will render until it is installed and on PATH.\n"
            "  Windows:  winget install Gyan.FFmpeg   (then reopen this app)\n"
            "  Or rebuild with:  python build_exe.py --with-ffmpeg\n\n", "fail")
        self.run_btn.config(state="disabled")
        self.status.config(text="FFmpeg missing")

    def _write(self, text, tag=None):
        self.log.insert("end", text, tag)
        self.log.see("end")

    def _pump_log(self):
        """Drains whatever the worker thread printed. Runs on the Tk thread."""
        try:
            while True:
                chunk = self.log_queue.get_nowait()
                tag = None
                if chunk.lstrip().startswith(">>"):
                    tag = "step"
                elif "DONE in" in chunk:
                    tag = "done"
                elif "FAILED" in chunk or "ERROR" in chunk:
                    tag = "fail"
                self._write(chunk, tag)
        except queue.Empty:
            pass
        self.root.after(120, self._pump_log)

    # ----------------------------------------------------------------- footer

    def _build_footer(self, root):
        bar = tk.Frame(root, bg=BG)
        bar.pack(fill="x", padx=14, pady=(0, 12))

        self.progress = ttk.Progressbar(bar, mode="determinate",
                                        style="Horizontal.TProgressbar")
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.status = tk.Label(bar, text="Idle", bg=BG, fg=MUTED, width=22, anchor="w")
        self.status.pack(side="left")

        self.stop_btn = tk.Button(bar, text="Stop", relief="flat", bg="#2c3140",
                                  fg=FG, padx=14, pady=7, state="disabled",
                                  cursor="hand2", command=self._stop)
        self.stop_btn.pack(side="right", padx=(8, 0))

        self.run_btn = tk.Button(bar, text="Generate", relief="flat", bg=ACCENT,
                                 fg="white", padx=24, pady=7, cursor="hand2",
                                 activebackground="#3f78e0", activeforeground="white",
                                 font=("Segoe UI", 10, "bold"), command=self._start)
        self.run_btn.pack(side="right")

    # ---------------------------------------------------------------- actions

    def _collect_config(self):
        """GUI widgets -> the config dict the pipeline expects."""
        cfg = dict(self.cfg)
        ints = {"target_seconds", "scene_count", "crf"}
        floats = {"music_volume", "sfx_volume"}
        planly = dict(cfg.get("planly") or {})
        planly_ints = {"timezone_offset", "lead_minutes"}
        planly_lists = {"slots", "channels"}

        for key, var in self.v.items():
            if key in ("count", "topic"):
                continue
            value = var.get()
            if key.startswith("planly_"):
                field = key[len("planly_"):]
                if field in planly_ints:
                    value = int(float(value))
                elif field in planly_lists:
                    value = [p.strip() for p in str(value).split(",") if p.strip()]
                planly[field] = value
                continue
            if key in ints:
                value = int(float(value))
            elif key in floats:
                value = round(float(value), 3)
            cfg[key] = value
        cfg["planly"] = planly

        # A voice picked by hand has to beat the per-niche preset, so drop the
        # preset for the selected niche instead of silently losing the choice.
        presets = dict(cfg.get("niche_voice") or {})
        preset = dict(presets.get(cfg["niche"], {}))
        preset.pop("voice", None)
        preset.pop("voice_rate", None)
        presets[cfg["niche"]] = preset
        cfg["niche_voice"] = presets
        return cfg

    def _save_keys(self):
        lines = ["# Keys for the video factory. Do not commit this file.\n"]
        saved = []
        for env_name, _label, _url in KEYS:
            value = self.key_vars[env_name].get().strip()
            if value:
                lines.append(f"{env_name}={value}\n")
                os.environ[env_name] = value
                saved.append(env_name)
        ENV_PATH.write_text("".join(lines), encoding="utf-8")
        self._write(f"Saved {len(saved)} key(s) to {ENV_PATH}\n", "done")
        messagebox.showinfo("Saved", f"{len(saved)} key(s) written to .env")

    def _test_key(self, env_name):
        value = self.key_vars[env_name].get().strip()
        label = self.key_status[env_name]
        label.config(text="checking...", fg=MUTED)

        def work():
            ok, msg = self._probe(env_name, value)
            self.root.after(0, lambda: label.config(
                text=msg, fg="#4ade80" if ok else "#f87171"))

        threading.Thread(target=work, daemon=True).start()

    def _probe(self, env_name, value):
        if not value:
            return False, "Empty."
        try:
            if env_name == "GEMINI_API_KEY":
                from pipeline.gemini import check_key
                return check_key(value)
            if env_name == "PEXELS_API_KEY":
                import requests
                if len(value) < 20:
                    return False, "Too short - a real Pexels key is about 56 characters."
                r = requests.get("https://api.pexels.com/videos/search",
                                 params={"query": "city", "per_page": 1},
                                 headers={"Authorization": value}, timeout=20)
                if r.status_code == 200:
                    return True, "OK - Pexels responded."
                return False, f"HTTP {r.status_code}" + (
                    " - key rejected." if r.status_code == 401 else "")
            if env_name == "PLANLY_API_KEY":
                from pipeline.planly import check_key as planly_check
                return planly_check(value)
            if env_name == "ANTHROPIC_API_KEY":
                import anthropic
                anthropic.Anthropic(api_key=value).messages.create(
                    model="claude-opus-5", max_tokens=8,
                    messages=[{"role": "user", "content": "ok"}])
                return True, "OK - Claude responded."
        except Exception as e:
            return False, f"{type(e).__name__}: {str(e)[:110]}"
        return False, "Unknown key."

    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            count = max(1, int(float(self.v["count"].get())))
        except ValueError:
            count = 1

        cfg = self._collect_config()
        save_json(CONFIG_PATH, {k: v for k, v in cfg.items()})
        topic = self.v["topic"].get().strip() or None

        self.cancel.clear()
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress.config(maximum=count, value=0)
        self.status.config(text=f"0 / {count}")
        self._write(f"\n{'=' * 58}\nStarting {count} video(s) - niche {cfg['niche']}\n"
                    f"{'=' * 58}\n", "step")

        self.worker = threading.Thread(target=self._run, args=(cfg, count, topic),
                                       daemon=True)
        self.worker.start()

    def _run(self, cfg, count, topic):
        from main import make_one

        original = sys.stdout
        sys.stdout = Tee(self.log_queue, original)
        made = 0
        try:
            for i in range(count):
                if self.cancel.is_set():
                    self.log_queue.put("\nStopped after the current video.\n")
                    break
                try:
                    make_one(cfg, topic=topic, force_bank=(cfg.get("provider") == "bank"))
                    made += 1
                except Exception as e:
                    self.log_queue.put(f"\nFAILED video {i + 1}: "
                                       f"{type(e).__name__}: {e}\n")
                self.root.after(0, self._tick, made, count)
        finally:
            sys.stdout = original
            self.root.after(0, self._finish, made, count)

    def _tick(self, made, count):
        self.progress.config(value=made)
        self.status.config(text=f"{made} / {count}")

    def _finish(self, made, count):
        self.run_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status.config(text=f"Done - {made} / {count}")
        self._write(f"\nFinished: {made} of {count} video(s) in {OUT_DIR}\n",
                    "done" if made else "fail")

    def _stop(self):
        self.cancel.set()
        self.status.config(text="Stopping...")
        self._write("\nStop requested - finishing the current video first.\n")

    def _load_channels(self):
        """Prints the account's channels with their ids, to paste into the field."""
        key = self.key_vars["PLANLY_API_KEY"].get().strip() or os.environ.get(
            "PLANLY_API_KEY", "").strip()
        if not key:
            self._write("No Planly key. Put one in the API keys tab first.\n", "fail")
            return
        self._write("\nLoading Planly channels...\n", "step")

        def work():
            try:
                from pipeline.planly import list_channels, list_teams
                teams = list_teams(key)
                if not teams:
                    self.log_queue.put("This account has no teams.\n")
                    return
                team_id = self.v["planly_team_id"].get().strip() or teams[0]["id"]
                lines = [f"team: {teams[0].get('name', team_id)}  ({team_id})\n"]
                for c in list_channels(key, team_id):
                    lines.append(f"  {c['id']}  {c.get('social_network', '?'):18} "
                                 f"{c.get('name', '')}\n")
                lines.append("Paste the ids you want into 'Channel ids'.\n")
                self.log_queue.put("".join(lines))
            except Exception as e:
                self.log_queue.put(f"Planly failed: {type(e).__name__}: {e}\n")

        threading.Thread(target=work, daemon=True).start()

    def _open_output(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(OUT_DIR)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", str(OUT_DIR)])


def run_cli():
    """Headless mode: `VideoFactory.exe --count 3 --niche facts`.

    A windowed exe has no console, so the run is mirrored to run.log next to the
    exe. That is what Task Scheduler and CI actually need to debug a failed run.
    """
    from main import main as cli_main

    log_path = ROOT / "run.log"
    handle = open(log_path, "a", encoding="utf-8", buffering=1)
    original_out, original_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = handle
    try:
        return cli_main()
    finally:
        sys.stdout, sys.stderr = original_out, original_err
        handle.close()


def main():
    # Any argument means headless. No arguments opens the window.
    if len(sys.argv) > 1:
        return run_cli()
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
