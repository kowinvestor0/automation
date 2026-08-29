"""Panel de control de la fabrica de videos.

Doble clic y listo: llaves, ajustes y el boton de generar, sin tocar JSON.
Escribe en los MISMOS archivos que usa el pipeline (config.json y .env), asi que
lo que cambies aqui vale igual corriendo a mano o en GitHub Actions.

Empaquetado con PyInstaller, este mismo ejecutable corre el pipeline cuando se le
pasa `--run`; asi la interfaz puede lanzarlo como proceso aparte y matarlo.
"""
import sys

# Modo CLI dentro del mismo binario. Va antes de importar tkinter: en el proceso
# hijo no hay ventana que crear.
if "--run" in sys.argv:
    sys.argv.remove("--run")
    from main import main as _cli
    sys.exit(_cli())

import json
import os
import queue
import subprocess
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent

CONFIG = ROOT / "config.json"
ENV = ROOT / ".env"
TOPICS = ROOT / "topics.json"
OUTPUT = ROOT / "output"

RELLENOS = {"...", "your-key-here", "xxx", ""}

LLAVES = [
    ("GEMINI_API_KEY", "Gemini (Google AI Studio)",
     "Miễn phí. Lấy ở aistudio.google.com/apikey", "https://aistudio.google.com/apikey"),
    ("ANTHROPIC_API_KEY", "Claude (Anthropic)",
     "Trả phí, ~$0,015/video", "https://console.anthropic.com/settings/keys"),
    ("PEXELS_API_KEY", "Pexels (video stock)",
     "Miễn phí, tuỳ chọn. Key thật dài ~56 ký tự", "https://www.pexels.com/api/"),
]

# (clave, etiqueta, tipo, opciones) — tipo: choice | int | float | bool | text
CAMPOS = [
    ("niche", "Chủ đề kênh", "choice",
     ["misterios", "humor", "curiosidades", "historia", "lugares"]),
    ("voice", "Giọng đọc", "choice", ["es-MX-JorgeNeural", "es-MX-DaliaNeural"]),
    ("voice_rate", "Tốc độ đọc", "choice", ["+0%", "+8%", "+14%", "+20%", "+26%"]),
    ("target_seconds", "Độ dài mong muốn (giây)", "int", None),
    ("scene_count", "Số cảnh", "int", None),
    ("font_size", "Cỡ chữ phụ đề", "int", None),
    ("words_per_caption", "Số từ mỗi dòng phụ đề", "int", None),
    ("music_volume", "Âm lượng nhạc nền", "float", None),
    ("sfx_volume", "Âm lượng hiệu ứng", "float", None),
    ("music_duck", "Nhạc nhỏ lại khi có giọng", "bool", None),
    ("sfx", "Bật hiệu ứng âm thanh", "bool", None),
    ("transitions", "Bật hiệu ứng chuyển cảnh", "bool", None),
    ("resolution", "Độ phân giải", "choice", ["1080p", "1440p", "4k"]),
    ("quality", "Chất lượng nén", "choice", ["fast", "high", "max"]),
    ("gemini_model", "Model Gemini", "text", None),
]


# --------------------------------------------------------------------- datos

def leer_env():
    valores = {}
    if ENV.exists():
        for linea in ENV.read_text(encoding="utf-8-sig").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, _, v = linea.partition("=")
            valores[k.strip()] = v.strip().strip('"').strip("'")
    return valores


def escribir_env(valores):
    lineas = ["# Llaves de la fabrica de videos. NO subas este archivo a GitHub.",
              "# Para GitHub Actions, copia cada valor en Settings > Secrets.", ""]
    for nombre, _, _, _ in LLAVES:
        v = (valores.get(nombre) or "").strip()
        if v and v not in RELLENOS:
            lineas.append(f"{nombre}={v}")
    ENV.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def cargar_config():
    return json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}


def guardar_config(cfg):
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")


def comando_cli(args):
    """El pipeline como proceso aparte, funcione o no empaquetado."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--run", *args]
    return [sys.executable, str(Path(__file__).resolve()), "--run", *args]


# ----------------------------------------------------------------- interfaz

class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.pack(fill="both", expand=True)
        self.cfg = cargar_config()
        self.env = leer_env()
        self.proc = None
        self.cola = queue.Queue()
        self.vars_llaves = {}
        self.vars_campos = {}

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        nb.add(self._tab_llaves(nb), text="  Khoá API  ")
        nb.add(self._tab_ajustes(nb), text="  Cấu hình  ")
        nb.add(self._tab_correr(nb), text="  Tạo video  ")

        self.estado = ttk.Label(self, text="Sẵn sàng", anchor="w")
        self.estado.pack(fill="x", pady=(8, 0))
        self.after(120, self._vaciar_cola)

    # -- pestana 1: llaves
    def _tab_llaves(self, padre):
        f = ttk.Frame(padre, padding=14)
        ttk.Label(f, text="Không có khoá nào cũng chạy được — kịch bản sẽ lấy từ "
                          "topics.json.", foreground="#555").pack(anchor="w", pady=(0, 10))

        for nombre, titulo, ayuda, url in LLAVES:
            caja = ttk.LabelFrame(f, text=titulo, padding=8)
            caja.pack(fill="x", pady=5)
            var = tk.StringVar(value=self.env.get(nombre, ""))
            self.vars_llaves[nombre] = var
            fila = ttk.Frame(caja)
            fila.pack(fill="x")
            ttk.Entry(fila, textvariable=var, show="*", width=52).pack(side="left",
                                                                      fill="x", expand=True)
            ttk.Button(fila, text="Lấy khoá", width=10,
                       command=lambda u=url: webbrowser.open(u)).pack(side="left", padx=4)
            ttk.Label(caja, text=ayuda, foreground="#777").pack(anchor="w", pady=(4, 0))

        acciones = ttk.Frame(f)
        acciones.pack(fill="x", pady=12)
        ttk.Button(acciones, text="Lưu khoá", command=self._guardar_llaves).pack(side="left")
        ttk.Button(acciones, text="Kiểm tra khoá",
                   command=self._probar_llaves).pack(side="left", padx=6)

        ttk.Label(f, wraplength=560, foreground="#a05000",
                  text="Khoá lưu vào .env và CHỈ dùng khi chạy trên máy này. Muốn "
                       "GitHub Actions dùng thì vào Settings → Secrets and variables "
                       "→ Actions và thêm từng khoá vào đó. Đừng commit file .env.",
                  ).pack(anchor="w", pady=(10, 0))
        return f

    def _guardar_llaves(self):
        valores = {k: v.get() for k, v in self.vars_llaves.items()}
        malas = [k for k, v in valores.items()
                 if v.strip() and len(v.strip()) < 20]
        if malas:
            messagebox.showwarning(
                "Khoá quá ngắn",
                "Mấy khoá này ngắn dưới 20 ký tự nên chắc là chữ mẫu, "
                "tool sẽ bỏ qua:\n\n" + "\n".join(malas))
        escribir_env(valores)
        self.env = leer_env()
        self.estado.config(text=f"Đã lưu khoá vào {ENV.name}")

    def _probar_llaves(self):
        self._guardar_llaves()
        threading.Thread(target=self._probar_llaves_worker, daemon=True).start()

    def _probar_llaves_worker(self):
        for nombre, valor in self.env.items():
            os.environ[nombre] = valor
        lineas = []

        gem = (self.env.get("GEMINI_API_KEY") or "").strip()
        if len(gem) >= 20:
            try:
                from pipeline.script_gen import gemini_models
                modelos = gemini_models(gem)
                lineas.append(f"Gemini OK — {len(modelos)} model dùng được.\n"
                              f"Vài cái đầu: {', '.join(modelos[:6])}")
            except Exception as e:
                lineas.append(f"Gemini LỖI — {type(e).__name__}: {e}")
        else:
            lineas.append("Gemini — chưa có khoá")

        pex = (self.env.get("PEXELS_API_KEY") or "").strip()
        if len(pex) >= 20:
            try:
                import requests
                r = requests.get("https://api.pexels.com/v1/search",
                                 params={"query": "mexico", "per_page": 1},
                                 headers={"Authorization": pex}, timeout=30)
                lineas.append("Pexels OK" if r.status_code == 200
                              else f"Pexels LỖI — HTTP {r.status_code}")
            except Exception as e:
                lineas.append(f"Pexels LỖI — {e}")
        else:
            lineas.append("Pexels — chưa có khoá (chỉ dùng ảnh Wikimedia)")

        ant = (self.env.get("ANTHROPIC_API_KEY") or "").strip()
        lineas.append("Claude — có khoá" if len(ant) >= 20 else "Claude — chưa có khoá")
        self.cola.put(("popup", "Kết quả kiểm tra", "\n\n".join(lineas)))

    # -- pestana 2: ajustes
    def _tab_ajustes(self, padre):
        f = ttk.Frame(padre, padding=14)
        rejilla = ttk.Frame(f)
        rejilla.pack(fill="both", expand=True)

        for i, (clave, etiqueta, tipo, opciones) in enumerate(CAMPOS):
            ttk.Label(rejilla, text=etiqueta).grid(row=i, column=0, sticky="w",
                                                   pady=3, padx=(0, 12))
            actual = self.cfg.get(clave)
            if tipo == "bool":
                var = tk.BooleanVar(value=bool(actual))
                ttk.Checkbutton(rejilla, variable=var).grid(row=i, column=1, sticky="w")
            elif tipo == "choice":
                var = tk.StringVar(value=str(actual))
                ttk.Combobox(rejilla, textvariable=var, values=opciones,
                             width=24, state="readonly").grid(row=i, column=1, sticky="w")
            else:
                var = tk.StringVar(value="" if actual is None else str(actual))
                ttk.Entry(rejilla, textvariable=var, width=26).grid(row=i, column=1,
                                                                    sticky="w")
            self.vars_campos[clave] = (var, tipo)

        ttk.Button(f, text="Lưu cấu hình", command=self._guardar_ajustes).pack(
            anchor="w", pady=(14, 0))
        ttk.Label(f, foreground="#777", wraplength=560,
                  text="Ghi vào config.json. File này ĐƯỢC commit lên GitHub nên "
                       "Actions dùng chung cấu hình với máy bạn.").pack(anchor="w",
                                                                        pady=(8, 0))
        return f

    def _guardar_ajustes(self):
        errores = []
        for clave, (var, tipo) in self.vars_campos.items():
            crudo = var.get()
            try:
                if tipo == "bool":
                    self.cfg[clave] = bool(crudo)
                elif tipo == "int":
                    self.cfg[clave] = int(str(crudo).strip())
                elif tipo == "float":
                    self.cfg[clave] = float(str(crudo).strip())
                else:
                    self.cfg[clave] = str(crudo).strip()
            except ValueError:
                errores.append(f"{clave}: '{crudo}' không phải số hợp lệ")
        if errores:
            messagebox.showerror("Giá trị sai", "\n".join(errores))
            return
        guardar_config(self.cfg)
        self.estado.config(text="Đã lưu config.json")

    # -- pestana 3: correr
    def _tab_correr(self, padre):
        f = ttk.Frame(padre, padding=14)
        barra = ttk.Frame(f)
        barra.pack(fill="x")

        ttk.Label(barra, text="Số video:").pack(side="left")
        self.var_count = tk.StringVar(value="1")
        ttk.Spinbox(barra, from_=1, to=20, width=5,
                    textvariable=self.var_count).pack(side="left", padx=(4, 14))

        ttk.Label(barra, text="Chủ đề:").pack(side="left")
        self.var_topic = tk.StringVar(value="(tự chọn)")
        ttk.Combobox(barra, textvariable=self.var_topic, width=30, state="readonly",
                     values=self._lista_temas()).pack(side="left", padx=4)

        self.var_bank = tk.BooleanVar(value=False)
        ttk.Checkbutton(barra, text="Chỉ dùng topics.json",
                        variable=self.var_bank).pack(side="left", padx=10)

        botones = ttk.Frame(f)
        botones.pack(fill="x", pady=10)
        self.btn_ir = ttk.Button(botones, text="Tạo video", command=self._arrancar)
        self.btn_ir.pack(side="left")
        self.btn_parar = ttk.Button(botones, text="Dừng", command=self._parar,
                                    state="disabled")
        self.btn_parar.pack(side="left", padx=6)
        ttk.Button(botones, text="Mở thư mục output",
                   command=self._abrir_output).pack(side="left", padx=6)

        self.log = tk.Text(f, height=20, wrap="word", bg="#111", fg="#ddd",
                           insertbackground="#ddd", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        return f

    def _lista_temas(self):
        temas = ["(tự chọn)"]
        if TOPICS.exists():
            try:
                temas += [t["id"] for t in json.loads(TOPICS.read_text(encoding="utf-8"))]
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        return temas

    def _abrir_output(self):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        os.startfile(OUTPUT)  # noqa: S606 - solo Windows, ruta propia

    def _arrancar(self):
        if self.proc and self.proc.poll() is None:
            return
        self._guardar_ajustes()
        self._guardar_llaves()

        args = ["--count", self.var_count.get()]
        if self.var_topic.get() != "(tự chọn)":
            args += ["--topic", self.var_topic.get()]
        if self.var_bank.get():
            args.append("--bank")

        entorno = dict(os.environ)
        entorno.update({k: v for k, v in self.env.items() if v})
        entorno["PYTHONIOENCODING"] = "utf-8"

        self.log.delete("1.0", "end")
        self.log.insert("end", f"> main.py {' '.join(args)}\n\n")
        self.btn_ir.config(state="disabled")
        self.btn_parar.config(state="normal")
        self.estado.config(text="Đang chạy...")

        self.proc = subprocess.Popen(
            comando_cli(args), cwd=str(ROOT), env=entorno,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        threading.Thread(target=self._leer_salida, daemon=True).start()

    def _leer_salida(self):
        for linea in self.proc.stdout:
            self.cola.put(("log", linea))
        codigo = self.proc.wait()
        self.cola.put(("fin", codigo))

    def _parar(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.estado.config(text="Đã dừng")

    def _vaciar_cola(self):
        try:
            while True:
                tipo, *resto = self.cola.get_nowait()
                if tipo == "log":
                    self.log.insert("end", resto[0])
                    self.log.see("end")
                elif tipo == "popup":
                    messagebox.showinfo(resto[0], resto[1])
                elif tipo == "fin":
                    self.btn_ir.config(state="normal")
                    self.btn_parar.config(state="disabled")
                    self.estado.config(
                        text="Xong. Bấm 'Mở thư mục output' để xem."
                        if resto[0] == 0 else f"Kết thúc với lỗi (mã {resto[0]})")
        except queue.Empty:
            pass
        self.after(120, self._vaciar_cola)


def main():
    root = tk.Tk()
    root.title("Fábrica de Videos MX — bảng điều khiển")
    root.geometry("660x620")
    root.minsize(620, 560)
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
