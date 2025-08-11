#!/usr/bin/env python3
# TS4ScriptTool GUI - Tkinter-based tool for .ts4script extract/pack/watch.
# No external dependencies. Python 3.8+ recommended.
import os
import sys
import time
import threading
import zipfile
import fnmatch
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Dict

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

DEFAULT_IGNORE = [
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.log",
    ".git/",
    ".idea/",
    ".vscode/",
    "*.swp",
    ".DS_Store",
    "Thumbs.db",
]

APP_TITLE = "TS4ScriptTool GUI"
APP_VERSION = "1.0.0"
STATE_PATH = Path.home() / ".ts4script_tool_state.json"

# ----------------------- Utility functions -----------------------

def read_ignore_file(workspace: Path) -> List[str]:
    ignore_path = workspace / ".ts4ignore"
    if ignore_path.exists():
        lines = [ln.strip() for ln in ignore_path.read_text(encoding="utf-8").splitlines()]
        return [ln for ln in lines if ln and not ln.startswith("#")]
    return list(DEFAULT_IGNORE)

def write_ignore_file(workspace: Path, patterns: List[str]) -> None:
    ignore_path = workspace / ".ts4ignore"
    text = "\n".join(patterns) + "\n" if patterns else ""
    ignore_path.write_text(text, encoding="utf-8")

def should_ignore(rel_path: str, patterns: List[str]) -> bool:
    rp = rel_path.replace("\\", "/")
    for pat in patterns:
        if pat.endswith("/"):
            if rp.startswith(pat):
                return True
        if fnmatch.fnmatch(rp, pat):
            return True
    return False

def zip_dir(src_dir: Path, dst_zip: Path, ignore_patterns: List[str]) -> None:
    if dst_zip.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = dst_zip.with_suffix(f".bak_{ts}.ts4script")
        try:
            from shutil import copy2
            copy2(dst_zip, backup)
        except Exception:
            pass
    with zipfile.ZipFile(dst_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            root_p = Path(root)
            # Remove ignored dirs
            kept_dirs = []
            for d in dirs:
                rel_dir = (root_p / d).relative_to(src_dir).as_posix() + "/"
                if should_ignore(rel_dir, ignore_patterns):
                    continue
                kept_dirs.append(d)
            dirs[:] = kept_dirs

            for name in files:
                abs_path = root_p / name
                rel = abs_path.relative_to(src_dir).as_posix()
                if should_ignore(rel, ignore_patterns):
                    continue
                zf.write(abs_path, arcname=rel)

def extract_zip(src_zip: Path, dst_dir: Path) -> None:
    if dst_dir.exists() and any(dst_dir.iterdir()):
        raise RuntimeError(f"Destination '{dst_dir}' is not empty.")
    dst_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src_zip, "r") as zf:
        zf.extractall(dst_dir)

def compute_tree_signature(path: Path, ignore_patterns: List[str]) -> Tuple[int, int, str]:
    total_files = 0
    total_size = 0
    h = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        root_p = Path(root)
        kept_dirs = []
        for d in dirs:
            rel = (root_p / d).relative_to(path).as_posix() + "/"
            if should_ignore(rel, ignore_patterns):
                continue
            kept_dirs.append(d)
        dirs[:] = kept_dirs

        for name in files:
            abs_path = root_p / name
            rel = abs_path.relative_to(path).as_posix()
            if should_ignore(rel, ignore_patterns):
                continue
            try:
                st = abs_path.stat()
            except FileNotFoundError:
                continue
            total_files += 1
            total_size += st.st_size
            h.update(rel.encode("utf-8"))
            h.update(str(st.st_mtime_ns).encode("utf-8"))
            h.update(str(st.st_size).encode("utf-8"))
    return total_files, total_size, h.hexdigest()

# ----------------------- Watcher thread -----------------------

@dataclass
class WatchState:
    running: bool = False
    thread: Optional[threading.Thread] = None
    interval: float = 2.0
    last_sig: Optional[Tuple[int, int, str]] = None

# ----------------------- GUI application -----------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("820x560")
        self.minsize(760, 520)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("vista")
        except Exception:
            pass

        self._build_ui()
        self.watch_state = WatchState()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_state()

    def _build_ui(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_extract = ttk.Frame(self.nb)
        self.tab_pack = ttk.Frame(self.nb)
        self.tab_watch = ttk.Frame(self.nb)
        self.tab_ignore = ttk.Frame(self.nb)

        self.nb.add(self.tab_extract, text="Extract")
        self.nb.add(self.tab_pack, text="Pack")
        self.nb.add(self.tab_watch, text="Watch")
        self.nb.add(self.tab_ignore, text="Ignore List")

        self._build_extract_tab()
        self._build_pack_tab()
        self._build_watch_tab()
        self._build_ignore_tab()

        self.status = tk.StringVar(value="Ready.")
        status_bar = ttk.Label(self, textvariable=self.status, anchor="w")
        status_bar.pack(fill="x", padx=8, pady=(0,8))

    def _save_state(self):
        data = {
            "extract_src": self.extract_src.get(),
            "extract_dst": self.extract_dst.get(),
            "pack_src": self.pack_src.get(),
            "pack_dst": self.pack_dst.get(),
            "watch_src": self.watch_src.get(),
            "watch_dst": self.watch_dst.get(),
            "watch_interval": self.watch_interval.get(),
            "ignore_ws": self.ignore_ws.get(),
            "selected_tab": self.nb.index(self.nb.select()),
        }
        try:
            STATE_PATH.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def _load_state(self):
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        self.extract_src.set(data.get("extract_src", ""))
        self.extract_dst.set(data.get("extract_dst", ""))
        self.pack_src.set(data.get("pack_src", ""))
        self.pack_dst.set(data.get("pack_dst", ""))
        self.watch_src.set(data.get("watch_src", ""))
        self.watch_dst.set(data.get("watch_dst", ""))
        try:
            self.watch_interval.set(float(data.get("watch_interval", 2.0)))
        except Exception:
            pass
        self.ignore_ws.set(data.get("ignore_ws", ""))
        idx = data.get("selected_tab")
        if isinstance(idx, int):
            try:
                self.nb.select(idx)
            except Exception:
                pass

    def _on_close(self):
        self._save_state()
        self.destroy()

    # ---------------- Extract tab ----------------
    def _build_extract_tab(self):
        f = self.tab_extract
        pad = {"padx": 8, "pady": 6}

        ttk.Label(f, text=".ts4script file:").grid(row=0, column=0, sticky="w", **pad)
        self.extract_src = tk.StringVar()
        ttk.Entry(f, textvariable=self.extract_src, width=70).grid(row=0, column=1, **pad)
        ttk.Button(f, text="Browse", command=self._pick_extract_src).grid(row=0, column=2, **pad)

        ttk.Label(f, text="Workspace folder:").grid(row=1, column=0, sticky="w", **pad)
        self.extract_dst = tk.StringVar()
        ttk.Entry(f, textvariable=self.extract_dst, width=70).grid(row=1, column=1, **pad)
        ttk.Button(f, text="Choose", command=self._pick_extract_dst).grid(row=1, column=2, **pad)

        ttk.Button(f, text="Extract", command=self._do_extract).grid(row=2, column=1, sticky="e", **pad)

        for i in range(3):
            f.grid_columnconfigure(i, weight=1)

    def _pick_extract_src(self):
        path = filedialog.askopenfilename(title="Select .ts4script", filetypes=[("TS4 Script", "*.ts4script"), ("Zip", "*.zip"), ("All", "*.*")])
        if path:
            self.extract_src.set(path)

    def _pick_extract_dst(self):
        path = filedialog.askdirectory(title="Select workspace folder (must be empty or new)")
        if path:
            self.extract_dst.set(path)

    def _do_extract(self):
        try:
            src = Path(self.extract_src.get()).expanduser()
            dst = Path(self.extract_dst.get()).expanduser()
            if not src.exists():
                raise RuntimeError("Source file not found.")
            if dst.exists() and any(Path(dst).iterdir()):
                raise RuntimeError("Destination must be empty or non-existent.")
            extract_zip(src, dst)
            self.status.set(f"Extracted to {dst}")
            messagebox.showinfo("Done", f"Extracted to:\n{dst}")
        except Exception as e:
            messagebox.showerror("Extract error", str(e))
            self.status.set(f"Extract error: {e}")

    # ---------------- Pack tab ----------------
    def _build_pack_tab(self):
        f = self.tab_pack
        pad = {"padx": 8, "pady": 6}

        ttk.Label(f, text="Workspace folder:").grid(row=0, column=0, sticky="w", **pad)
        self.pack_src = tk.StringVar()
        ttk.Entry(f, textvariable=self.pack_src, width=70).grid(row=0, column=1, **pad)
        ttk.Button(f, text="Choose", command=self._pick_pack_src).grid(row=0, column=2, **pad)

        ttk.Label(f, text="Output .ts4script:").grid(row=1, column=0, sticky="w", **pad)
        self.pack_dst = tk.StringVar()
        ttk.Entry(f, textvariable=self.pack_dst, width=70).grid(row=1, column=1, **pad)
        ttk.Button(f, text="Browse", command=self._pick_pack_dst).grid(row=1, column=2, **pad)

        ttk.Button(f, text="Pack", command=self._do_pack).grid(row=2, column=1, sticky="e", **pad)

        for i in range(3):
            f.grid_columnconfigure(i, weight=1)

    def _pick_pack_src(self):
        path = filedialog.askdirectory(title="Select workspace folder (package root)")
        if path:
            self.pack_src.set(path)

    def _pick_pack_dst(self):
        path = filedialog.asksaveasfilename(title="Output .ts4script", defaultextension=".ts4script", filetypes=[("TS4 Script", "*.ts4script")])
        if path:
            self.pack_dst.set(path)

    def _do_pack(self):
        try:
            src = Path(self.pack_src.get()).expanduser()
            dst = Path(self.pack_dst.get()).expanduser()
            if not src.exists():
                raise RuntimeError("Workspace not found.")
            patterns = read_ignore_file(src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            zip_dir(src, dst, patterns)
            self.status.set(f"Packed: {dst}")
            messagebox.showinfo("Done", f"Packed:\n{dst}")
        except Exception as e:
            messagebox.showerror("Pack error", str(e))
            self.status.set(f"Pack error: {e}")

    # ---------------- Watch tab ----------------
    def _build_watch_tab(self):
        f = self.tab_watch
        pad = {"padx": 8, "pady": 6}

        ttk.Label(f, text="Workspace folder:").grid(row=0, column=0, sticky="w", **pad)
        self.watch_src = tk.StringVar()
        ttk.Entry(f, textvariable=self.watch_src, width=70).grid(row=0, column=1, **pad)
        ttk.Button(f, text="Choose", command=self._pick_watch_src).grid(row=0, column=2, **pad)

        ttk.Label(f, text="Output .ts4script:").grid(row=1, column=0, sticky="w", **pad)
        self.watch_dst = tk.StringVar()
        ttk.Entry(f, textvariable=self.watch_dst, width=70).grid(row=1, column=1, **pad)
        ttk.Button(f, text="Browse", command=self._pick_watch_dst).grid(row=1, column=2, **pad)

        ttk.Label(f, text="Interval (sec):").grid(row=2, column=0, sticky="w", **pad)
        self.watch_interval = tk.DoubleVar(value=2.0)
        ttk.Entry(f, textvariable=self.watch_interval, width=10).grid(row=2, column=1, sticky="w", **pad)

        self.btn_watch = ttk.Button(f, text="Start Watching", command=self._toggle_watch)
        self.btn_watch.grid(row=3, column=1, sticky="e", **pad)

        for i in range(3):
            f.grid_columnconfigure(i, weight=1)

    def _pick_watch_src(self):
        path = filedialog.askdirectory(title="Select workspace folder")
        if path:
            self.watch_src.set(path)

    def _pick_watch_dst(self):
        path = filedialog.asksaveasfilename(title="Output .ts4script", defaultextension=".ts4script", filetypes=[("TS4 Script", "*.ts4script")])
        if path:
            self.watch_dst.set(path)

    def _toggle_watch(self):
        if self.watch_state.running:
            self.watch_state.running = False
            self.btn_watch.configure(text="Start Watching")
            self.status.set("Watcher stopped.")
            return

        src = Path(self.watch_src.get()).expanduser()
        dst = Path(self.watch_dst.get()).expanduser()
        if not src.exists():
            messagebox.showerror("Watch error", "Workspace not found.")
            return
        patterns = read_ignore_file(src)
        interval = float(self.watch_interval.get())

        self.watch_state.running = True
        self.btn_watch.configure(text="Stop Watching")
        self.status.set(f"Watching '{src}' -> '{dst}' every {interval}s.")

        def loop():
            last_sig = None
            while self.watch_state.running:
                try:
                    sig = compute_tree_signature(src, patterns)
                    if sig != last_sig:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        zip_dir(src, dst, patterns)
                        self._set_status_threadsafe(f"[{time.strftime('%H:%M:%S')}] Change detected -> packed {dst}")
                        last_sig = sig
                except Exception as e:
                    self._set_status_threadsafe(f"Watch error: {e}")
                time.sleep(interval)

        t = threading.Thread(target=loop, daemon=True)
        self.watch_state.thread = t
        t.start()

    def _set_status_threadsafe(self, text: str):
        self.after(0, lambda: self.status.set(text))

    # ---------------- Ignore tab ----------------
    def _build_ignore_tab(self):
        f = self.tab_ignore
        pad = {"padx": 8, "pady": 6}

        ttk.Label(f, text="Workspace folder:").grid(row=0, column=0, sticky="w", **pad)
        self.ignore_ws = tk.StringVar()
        ttk.Entry(f, textvariable=self.ignore_ws, width=70).grid(row=0, column=1, **pad)
        ttk.Button(f, text="Choose", command=self._pick_ignore_ws).grid(row=0, column=2, **pad)

        self.ignore_text = tk.Text(f, height=20)
        self.ignore_text.grid(row=1, column=0, columnspan=3, sticky="nsew", **pad)

        btns = ttk.Frame(f)
        btns.grid(row=2, column=0, columnspan=3, sticky="e", **pad)
        ttk.Button(btns, text="Load", command=self._ignore_load).pack(side="left", padx=4)
        ttk.Button(btns, text="Save", command=self._ignore_save).pack(side="left", padx=4)
        ttk.Button(btns, text="Reset to Defaults", command=self._ignore_reset).pack(side="left", padx=4)

        for i in range(3):
            f.grid_columnconfigure(i, weight=1)
        f.grid_rowconfigure(1, weight=1)

    def _pick_ignore_ws(self):
        path = filedialog.askdirectory(title="Select workspace folder")
        if path:
            self.ignore_ws.set(path)

    def _ignore_load(self):
        try:
            ws = Path(self.ignore_ws.get()).expanduser()
            patterns = read_ignore_file(ws)
            self.ignore_text.delete("1.0", "end")
            self.ignore_text.insert("1.0", "\n".join(patterns))
            self.status.set("Loaded ignore patterns.")
        except Exception as e:
            messagebox.showerror("Load error", str(e))

    def _ignore_save(self):
        try:
            ws = Path(self.ignore_ws.get()).expanduser()
            raw = self.ignore_text.get("1.0", "end").splitlines()
            patterns = [ln.strip() for ln in raw if ln.strip()]
            write_ignore_file(ws, patterns)
            self.status.set("Saved ignore patterns.")
            messagebox.showinfo("Saved", ".ts4ignore updated.")
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def _ignore_reset(self):
        self.ignore_text.delete("1.0", "end")
        self.ignore_text.insert("1.0", "\n".join(DEFAULT_IGNORE))
        self.status.set("Reset ignore patterns to defaults.")

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
