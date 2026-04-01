import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import shutil
import threading
import time
import datetime
import schedule
import sys
from pathlib import Path

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup_config.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup_log.txt")

DEFAULT_CONFIG = {
    "sources": [],
    "destination": "",
    "schedule_enabled": False,
    "schedule_type": "daily",
    "schedule_time": "08:00",
    "schedule_weekday": "monday",
    "keep_versions": 3
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            c = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                c.setdefault(k, v)
            return c
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line

def do_backup(config, progress_cb=None, log_cb=None):
    dest_base = config["destination"]
    sources = config["sources"]
    if not dest_base:
        return False, "Destino não configurado."
    if not sources:
        return False, "Nenhuma pasta de origem selecionada."
    if not os.path.exists(dest_base):
        return False, f"Destino não encontrado: {dest_base}"

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(dest_base, f"Backup_{ts}")
    os.makedirs(backup_dir, exist_ok=True)

    total_files = 0
    copied_files = 0
    errors = []

    # Count total
    for src in sources:
        if os.path.isdir(src):
            for _, _, files in os.walk(src):
                total_files += len(files)
        elif os.path.isfile(src):
            total_files += 1

    if log_cb:
        log_cb(log(f"Iniciando backup → {backup_dir}"))

    for src in sources:
        src_name = os.path.basename(src.rstrip("/\\"))
        dest_path = os.path.join(backup_dir, src_name)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dest_path, dirs_exist_ok=True,
                    copy_function=lambda s, d: (shutil.copy2(s, d), [copied_files]))
                # Count after copy
                for _, _, files in os.walk(dest_path):
                    copied_files += len(files)
            elif os.path.isfile(src):
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src, dest_path)
                copied_files += 1
        except Exception as e:
            errors.append(f"{src}: {e}")
            if log_cb:
                log_cb(log(f"ERRO ao copiar {src}: {e}"))

        if progress_cb and total_files > 0:
            pct = min(int((copied_files / max(total_files, 1)) * 100), 99)
            progress_cb(pct)

    # Cleanup old versions
    try:
        keep = int(config.get("keep_versions", 3))
        all_backups = sorted([
            d for d in os.listdir(dest_base)
            if d.startswith("Backup_") and os.path.isdir(os.path.join(dest_base, d))
        ])
        while len(all_backups) > keep:
            old = os.path.join(dest_base, all_backups.pop(0))
            shutil.rmtree(old, ignore_errors=True)
            if log_cb:
                log_cb(log(f"Versão antiga removida: {old}"))
    except Exception:
        pass

    if progress_cb:
        progress_cb(100)

    msg = f"Backup concluído! {copied_files} arquivo(s) copiado(s)."
    if errors:
        msg += f" {len(errors)} erro(s)."
    if log_cb:
        log_cb(log(msg))
    return True, msg


class BackupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self.scheduler_thread = None
        self.scheduler_running = False

        self.title("Backup Ágil")
        self.geometry("720x620")
        self.resizable(False, False)
        self.configure(bg="#0f1117")

        self._setup_styles()
        self._build_ui()
        self._refresh_sources()
        self._load_schedule_ui()

        if self.config_data["schedule_enabled"]:
            self._start_scheduler()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background="#0f1117")
        style.configure("Card.TFrame", background="#1a1d27", relief="flat")
        style.configure("TLabel", background="#0f1117", foreground="#e2e8f0",
                        font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#0f1117", foreground="#ffffff",
                        font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", background="#0f1117", foreground="#94a3b8",
                        font=("Segoe UI", 9))
        style.configure("Card.TLabel", background="#1a1d27", foreground="#e2e8f0",
                        font=("Segoe UI", 10))
        style.configure("Section.TLabel", background="#1a1d27", foreground="#64b5f6",
                        font=("Segoe UI", 10, "bold"))

        style.configure("Primary.TButton",
                        background="#2563eb", foreground="#ffffff",
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0, relief="flat", padding=(12, 8))
        style.map("Primary.TButton",
                  background=[("active", "#1d4ed8"), ("pressed", "#1e40af")])

        style.configure("Ghost.TButton",
                        background="#1e2535", foreground="#94a3b8",
                        font=("Segoe UI", 9),
                        borderwidth=0, relief="flat", padding=(8, 5))
        style.map("Ghost.TButton",
                  background=[("active", "#2d3748")])

        style.configure("Danger.TButton",
                        background="#7f1d1d", foreground="#fca5a5",
                        font=("Segoe UI", 9),
                        borderwidth=0, relief="flat", padding=(8, 5))
        style.map("Danger.TButton",
                  background=[("active", "#991b1b")])

        style.configure("green.Horizontal.TProgressbar",
                        troughcolor="#1e2535", background="#22c55e",
                        borderwidth=0, thickness=8)
        style.configure("TCheckbutton", background="#1a1d27", foreground="#e2e8f0",
                        font=("Segoe UI", 10))
        style.configure("TCombobox", fieldbackground="#1e2535", background="#1e2535",
                        foreground="#e2e8f0", selectbackground="#2563eb")
        style.configure("TEntry", fieldbackground="#1e2535", foreground="#e2e8f0",
                        insertcolor="#e2e8f0")
        style.configure("TSpinbox", fieldbackground="#1e2535", foreground="#e2e8f0",
                        background="#1e2535")

    def _card(self, parent, padx=0, pady=0):
        f = ttk.Frame(parent, style="Card.TFrame", padding=16)
        f.pack(fill="x", padx=padx, pady=pady)
        return f

    def _build_ui(self):
        # Header
        hdr = ttk.Frame(self, style="TFrame", padding=(20, 16, 20, 4))
        hdr.pack(fill="x")
        ttk.Label(hdr, text="⬛ Backup Ágil", style="Title.TLabel").pack(side="left")
        ttk.Label(hdr, text="Backup rápido para formatação de desktops",
                  style="Sub.TLabel").pack(side="left", padx=(12, 0))

        sep = tk.Frame(self, bg="#1e2535", height=1)
        sep.pack(fill="x", padx=20, pady=(8, 0))

        # Main content
        body = ttk.Frame(self, style="TFrame", padding=(20, 12))
        body.pack(fill="both", expand=True)

        # Sources card
        src_card = self._card(body, pady=(0, 10))
        ttk.Label(src_card, text="📁  PASTAS DE ORIGEM", style="Section.TLabel").pack(anchor="w")
        ttk.Label(src_card, text="Pastas ou arquivos que serão copiados no backup",
                  style="Sub.TLabel", background="#1a1d27").pack(anchor="w", pady=(2, 8))

        list_frame = tk.Frame(src_card, bg="#111827", bd=0)
        list_frame.pack(fill="x")

        self.src_listbox = tk.Listbox(list_frame, bg="#111827", fg="#e2e8f0",
                                      selectbackground="#2563eb", selectforeground="#fff",
                                      borderwidth=0, highlightthickness=0,
                                      font=("Segoe UI", 9), height=5,
                                      activestyle="none")
        sb = tk.Scrollbar(list_frame, orient="vertical", command=self.src_listbox.yview)
        self.src_listbox.configure(yscrollcommand=sb.set)
        self.src_listbox.pack(side="left", fill="x", expand=True, padx=(8,0), pady=6)
        sb.pack(side="right", fill="y", pady=6)

        btn_row = ttk.Frame(src_card, style="Card.TFrame")
        btn_row.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_row, text="+ Pasta", style="Ghost.TButton",
                   command=self._add_folder).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="+ Arquivo", style="Ghost.TButton",
                   command=self._add_file).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="✕ Remover", style="Danger.TButton",
                   command=self._remove_source).pack(side="left")

        # Destination card
        dst_card = self._card(body, pady=(0, 10))
        ttk.Label(dst_card, text="💾  DESTINO DO BACKUP", style="Section.TLabel").pack(anchor="w")
        ttk.Label(dst_card, text="Onde os arquivos serão salvos (HD externo, pasta de rede...)",
                  style="Sub.TLabel", background="#1a1d27").pack(anchor="w", pady=(2, 8))

        dst_row = ttk.Frame(dst_card, style="Card.TFrame")
        dst_row.pack(fill="x")
        self.dest_var = tk.StringVar(value=self.config_data["destination"])
        self.dest_entry = tk.Entry(dst_row, textvariable=self.dest_var,
                                   bg="#111827", fg="#e2e8f0", insertbackground="#e2e8f0",
                                   borderwidth=0, highlightthickness=0,
                                   font=("Segoe UI", 9), relief="flat")
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(8, 8), ipady=6)
        ttk.Button(dst_row, text="Escolher...", style="Ghost.TButton",
                   command=self._choose_dest).pack(side="right")

        # Schedule card
        sched_card = self._card(body, pady=(0, 10))
        ttk.Label(sched_card, text="🕐  AGENDAMENTO AUTOMÁTICO", style="Section.TLabel").pack(anchor="w")

        sched_top = ttk.Frame(sched_card, style="Card.TFrame")
        sched_top.pack(fill="x", pady=(8, 0))

        self.sched_enabled = tk.BooleanVar(value=self.config_data["schedule_enabled"])
        chk = tk.Checkbutton(sched_top, text="Ativar backup automático",
                             variable=self.sched_enabled,
                             bg="#1a1d27", fg="#e2e8f0", selectcolor="#1e2535",
                             activebackground="#1a1d27", activeforeground="#e2e8f0",
                             font=("Segoe UI", 10), command=self._toggle_schedule)
        chk.pack(side="left")

        sched_row = ttk.Frame(sched_card, style="Card.TFrame")
        sched_row.pack(fill="x", pady=(10, 0))

        ttk.Label(sched_row, text="Frequência:", style="Card.TLabel").pack(side="left")
        self.sched_type = tk.StringVar(value=self.config_data["schedule_type"])
        freq_cb = ttk.Combobox(sched_row, textvariable=self.sched_type,
                               values=["daily", "weekly"], state="readonly", width=10)
        freq_cb.pack(side="left", padx=(8, 16))
        freq_cb.bind("<<ComboboxSelected>>", lambda e: self._save_schedule())

        ttk.Label(sched_row, text="Horário:", style="Card.TLabel").pack(side="left")
        self.sched_time = tk.StringVar(value=self.config_data["schedule_time"])
        tk.Entry(sched_row, textvariable=self.sched_time, width=7,
                 bg="#111827", fg="#e2e8f0", insertbackground="#e2e8f0",
                 borderwidth=0, font=("Segoe UI", 9), relief="flat").pack(side="left", padx=(8, 16), ipady=4)

        ttk.Label(sched_row, text="Versões a manter:", style="Card.TLabel").pack(side="left")
        self.keep_var = tk.StringVar(value=str(self.config_data["keep_versions"]))
        tk.Spinbox(sched_row, from_=1, to=30, textvariable=self.keep_var, width=4,
                   bg="#111827", fg="#e2e8f0", insertbackground="#e2e8f0",
                   buttonbackground="#1e2535", borderwidth=0,
                   font=("Segoe UI", 9), relief="flat").pack(side="left", padx=(8, 0))

        # Action area
        act_frame = ttk.Frame(body, style="TFrame")
        act_frame.pack(fill="x", pady=(4, 0))

        self.progress = ttk.Progressbar(act_frame, style="green.Horizontal.TProgressbar",
                                        mode="determinate", length=540)
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 12))

        ttk.Button(act_frame, text="▶  FAZER BACKUP AGORA", style="Primary.TButton",
                   command=self._run_backup_thread).pack(side="right")

        # Log area
        log_card = self._card(body, pady=(10, 0))
        ttk.Label(log_card, text="📋  LOG", style="Section.TLabel").pack(anchor="w")
        self.log_text = tk.Text(log_card, bg="#0a0d14", fg="#94a3b8",
                                font=("Consolas", 8), height=5,
                                borderwidth=0, state="disabled",
                                insertbackground="#e2e8f0", relief="flat")
        self.log_text.pack(fill="x", pady=(8, 0))

        ttk.Button(log_card, text="Ver log completo", style="Ghost.TButton",
                   command=self._open_log).pack(anchor="e", pady=(6, 0))

        # Status bar
        self.status_var = tk.StringVar(value="Pronto.")
        status_bar = tk.Label(self, textvariable=self.status_var,
                              bg="#0a0d14", fg="#64748b",
                              font=("Segoe UI", 8), anchor="w", padx=20)
        status_bar.pack(side="bottom", fill="x")

    def _refresh_sources(self):
        self.src_listbox.delete(0, "end")
        for s in self.config_data["sources"]:
            self.src_listbox.insert("end", f"  {s}")

    def _add_folder(self):
        path = filedialog.askdirectory(title="Selecione a pasta de origem")
        if path and path not in self.config_data["sources"]:
            self.config_data["sources"].append(path)
            save_config(self.config_data)
            self._refresh_sources()

    def _add_file(self):
        paths = filedialog.askopenfilenames(title="Selecione arquivos")
        changed = False
        for p in paths:
            if p not in self.config_data["sources"]:
                self.config_data["sources"].append(p)
                changed = True
        if changed:
            save_config(self.config_data)
            self._refresh_sources()

    def _remove_source(self):
        sel = self.src_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.config_data["sources"][idx]
        save_config(self.config_data)
        self._refresh_sources()

    def _choose_dest(self):
        path = filedialog.askdirectory(title="Selecione o destino do backup")
        if path:
            self.dest_var.set(path)
            self.config_data["destination"] = path
            save_config(self.config_data)

    def _save_schedule(self):
        self.config_data["schedule_type"] = self.sched_type.get()
        self.config_data["schedule_time"] = self.sched_time.get()
        self.config_data["keep_versions"] = int(self.keep_var.get() or 3)
        save_config(self.config_data)

    def _toggle_schedule(self):
        enabled = self.sched_enabled.get()
        self.config_data["schedule_enabled"] = enabled
        self._save_schedule()
        if enabled:
            self._start_scheduler()
            self._log_ui(f"Agendamento ativado: {self.sched_type.get()} às {self.sched_time.get()}")
        else:
            self._stop_scheduler()
            self._log_ui("Agendamento desativado.")

    def _load_schedule_ui(self):
        pass

    def _start_scheduler(self):
        self._stop_scheduler()
        schedule.clear()
        t = self.config_data["schedule_time"]
        stype = self.config_data["schedule_type"]
        if stype == "daily":
            schedule.every().day.at(t).do(self._scheduled_backup)
        else:
            schedule.every().week.at(t).do(self._scheduled_backup)

        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.status_var.set(f"Agendamento ativo: {stype} às {t}")

    def _stop_scheduler(self):
        self.scheduler_running = False
        schedule.clear()

    def _scheduler_loop(self):
        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(30)

    def _scheduled_backup(self):
        self._save_schedule()
        self.config_data["destination"] = self.dest_var.get()
        ok, msg = do_backup(self.config_data, log_cb=self._log_ui)
        self._log_ui(f"[Automático] {msg}")

    def _run_backup_thread(self):
        self.config_data["destination"] = self.dest_var.get()
        self._save_schedule()
        save_config(self.config_data)
        self.progress["value"] = 0
        self.status_var.set("Realizando backup...")
        t = threading.Thread(target=self._run_backup, daemon=True)
        t.start()

    def _run_backup(self):
        def prog(v):
            self.progress["value"] = v

        ok, msg = do_backup(self.config_data, progress_cb=prog, log_cb=self._log_ui)
        self.after(0, lambda: self.status_var.set(msg))
        if ok:
            self.after(0, lambda: messagebox.showinfo("Backup Ágil", msg))
        else:
            self.after(0, lambda: messagebox.showerror("Erro no Backup", msg))

    def _log_ui(self, line):
        def _do():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _do)
        return line

    def _open_log(self):
        if os.path.exists(LOG_FILE):
            os.startfile(LOG_FILE)
        else:
            messagebox.showinfo("Log", "Nenhum log encontrado ainda.")

    def _on_close(self):
        self._stop_scheduler()
        save_config(self.config_data)
        self.destroy()


if __name__ == "__main__":
    app = BackupApp()
    app.mainloop()
