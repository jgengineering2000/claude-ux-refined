#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jonathan George
"""
Claude Code UX Installer — GUI
Clickable installer for all Claude Code UX improvements.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from pathlib import Path

HERE = Path(__file__).parent

# ── Detection ─────────────────────────────────────────────────────────────────

SIMPLEBROWSER_CANDIDATES = [
    Path("/usr/share/antigravity/resources/app/extensions/simple-browser/dist/extension.js"),
    Path("/usr/share/code/resources/app/extensions/simple-browser/dist/extension.js"),
    Path("/snap/code/current/usr/share/code/resources/app/extensions/simple-browser/dist/extension.js"),
]

def detect_ides():
    ides = []
    if Path("~/.antigravity").expanduser().exists():
        ides.append("antigravity")
    if Path("~/.vscode").expanduser().exists():
        ides.append("vscode")
    return ides

def keybindings_path(ide):
    if ide == "antigravity":
        return Path("~/.config/Antigravity/User/keybindings.json").expanduser()
    return Path("~/.config/Code/User/keybindings.json").expanduser()

# ── Installation logic (mirrors install.py) ───────────────────────────────────

def _strip_line_comments(text):
    result, in_string, i = [], False, 0
    while i < len(text):
        if in_string:
            if text[i] == "\\" and i + 1 < len(text):
                result += [text[i], text[i + 1]]
                i += 2
                continue
            if text[i] == '"':
                in_string = False
            result.append(text[i])
        else:
            if text[i] == '"':
                in_string = True
                result.append(text[i])
            elif text[i : i + 2] == "//":
                while i < len(text) and text[i] != "\n":
                    i += 1
                continue
            else:
                result.append(text[i])
        i += 1
    return "".join(result)

def install_keybinding(ide, port, log):
    path = keybindings_path(ide)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "key": "alt+d",
        "command": "simpleBrowser.show",
        "args": f"http://localhost:{port}/manifest.html",
    }
    data = []
    if path.exists():
        try:
            data = json.loads(_strip_line_comments(path.read_text()))
        except (json.JSONDecodeError, ValueError):
            log(f"  WARNING: could not parse {path} — creating new file")
    updated = False
    for i, item in enumerate(data):
        if item.get("key") == "alt+d" and item.get("command") == "simpleBrowser.show":
            data[i] = entry
            updated = True
            break
    if not updated:
        data.append(entry)
    path.write_text(json.dumps(data, indent=2) + "\n")
    log(f"  {'Updated' if updated else 'Added'} Alt+D keybinding → {path}")

TASK_LABEL = "Start Claude doc server"

def install_task(project_dir, port, log):
    vscode_dir = project_dir / ".vscode"
    tasks_path = vscode_dir / "tasks.json"
    vscode_dir.mkdir(exist_ok=True)
    template = HERE / "server" / "tasks.json.template"
    new_task = json.loads(template.read_text())["tasks"][0]
    if port != 7432:
        new_task["command"] = f"CLAUDE_DOC_PORT={port} " + new_task["command"]
    if tasks_path.exists():
        try:
            data = json.loads(tasks_path.read_text())
        except Exception:
            log(f"  WARNING: could not parse {tasks_path} — skipping task install")
            return
        tasks = data.get("tasks", [])
        for t in tasks:
            if t.get("label") == TASK_LABEL:
                log(f"  Task '{TASK_LABEL}' already present — skipping")
                return
        tasks.append(new_task)
        data["tasks"] = tasks
        tasks_path.write_text(json.dumps(data, indent=2) + "\n")
        log(f"  Merged task into {tasks_path}")
    else:
        shutil.copy(template, tasks_path)
        log(f"  Created {tasks_path}")

def install_review_infra(project_dir, do_claude_md, log):
    claude_dir = project_dir / ".claude"
    docs_dir = project_dir / "claude-docs"
    claude_dir.mkdir(exist_ok=True)
    docs_dir.mkdir(exist_ok=True)
    files = [
        (HERE / "server" / "server.py",        claude_dir / "server.py"),
        (HERE / "server" / "manifest-link.js", docs_dir / "manifest-link.js"),
        (HERE / "templates" / "manifest.html", docs_dir / "manifest.html"),
    ]
    for src, dst in files:
        shutil.copy2(src, dst)
        log(f"  {src.name} → {dst}")
    if do_claude_md:
        dst = project_dir / "CLAUDE.md"
        if dst.exists():
            log(f"  CLAUDE.md already exists — not overwriting")
            log(f"    (template at {HERE / 'templates' / 'CLAUDE.md.template'})")
        else:
            shutil.copy2(HERE / "templates" / "CLAUDE.md.template", dst)
            log(f"  CLAUDE.md template → {dst}")
            log(f"  !! Edit {dst}: add project context at the bottom")

def run_patch(script, args, use_sudo, log):
    cmd = (["sudo"] if use_sudo else []) + [sys.executable, str(HERE / "patches" / script)] + args
    log(f"  Running {Path(script).name}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in result.stdout.strip().splitlines():
        log(f"    {line}")
    if result.returncode != 0:
        for line in result.stderr.strip().splitlines():
            log(f"    ERROR: {line}")

# ── GUI ───────────────────────────────────────────────────────────────────────

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Claude Code UX Installer")
        self.resizable(False, False)
        self.ides = detect_ides()
        sb_targets = [p for p in SIMPLEBROWSER_CANDIDATES if p.exists()]
        self.sb_available = bool(sb_targets)
        self.sb_needs_sudo = bool([p for p in sb_targets if not os.access(p, os.W_OK)])
        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────
        hdr = ttk.Frame(self, padding=(14, 10, 14, 8))
        hdr.grid(row=0, column=0, sticky="ew")
        ttk.Label(hdr, text="Claude Code UX Installer", font=("", 13, "bold")).pack(anchor="w")
        ide_text = f"Detected IDE(s): {', '.join(self.ides)}" if self.ides else "No IDE detected"
        ttk.Label(hdr, text=ide_text, foreground="gray").pack(anchor="w")
        ttk.Separator(self).grid(row=1, column=0, sticky="ew")

        body = ttk.Frame(self, padding=(14, 10))
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)

        r = 0

        # ── Part A ────────────────────────────────────────────────────────
        ttk.Label(body, text="IDE Extension Patches", font=("", 10, "bold")).grid(
            row=r, column=0, columnspan=3, sticky="w", pady=(0, 6))
        r += 1

        self.do_a1 = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text="A1  Chat panel layout  (margins, overlay scrollbar)",
                        variable=self.do_a1).grid(row=r, column=0, columnspan=3, sticky="w")
        r += 1

        self.do_a2 = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text="A2  Processing vocabulary",
                        variable=self.do_a2,
                        command=self._toggle_vocab).grid(row=r, column=0, columnspan=3, sticky="w")
        r += 1

        vf = ttk.Frame(body)
        vf.grid(row=r, column=0, columnspan=3, sticky="w", padx=(22, 0), pady=(2, 4))
        self.vocab_choice = tk.StringVar(value="Working")
        for label, val in [("Working", "Working"), ("...", "..."), ("(hidden)", ""), ("Custom:", "__custom__")]:
            ttk.Radiobutton(vf, text=label, variable=self.vocab_choice,
                            value=val, command=self._toggle_custom).pack(side="left", padx=(0, 8))
        self.custom_entry = ttk.Entry(vf, width=14)
        self.custom_entry.pack(side="left")
        self.custom_entry.config(state="disabled")
        self.vocab_frame = vf
        r += 1

        self.do_a3 = tk.BooleanVar(value=self.sb_available)
        sudo_note = "  (requires sudo)" if self.sb_needs_sudo else ""
        not_found = "  (not found — skipped)" if not self.sb_available else ""
        ttk.Checkbutton(body,
                        text=f"A3  Simple Browser tab title fix{sudo_note}{not_found}",
                        variable=self.do_a3,
                        state="normal" if self.sb_available else "disabled").grid(
                            row=r, column=0, columnspan=3, sticky="w")
        r += 1

        ttk.Separator(body, orient="horizontal").grid(
            row=r, column=0, columnspan=3, sticky="ew", pady=10)
        r += 1

        # ── Part B ────────────────────────────────────────────────────────
        self.do_b = tk.BooleanVar(value=True)
        ttk.Label(body, text="Review Document Infrastructure", font=("", 10, "bold")).grid(
            row=r, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(body, text="Enable", variable=self.do_b,
                        command=self._toggle_b).grid(row=r, column=2, sticky="e")
        r += 1

        self.b_frame = ttk.Frame(body)
        self.b_frame.grid(row=r, column=0, columnspan=3, sticky="ew", padx=(22, 0), pady=(4, 0))
        self.b_frame.columnconfigure(1, weight=1)
        r += 1

        ttk.Label(self.b_frame, text="Project directory:").grid(
            row=0, column=0, sticky="w", pady=2)
        self.proj_var = tk.StringVar(value=str(Path.cwd()))
        ttk.Entry(self.b_frame, textvariable=self.proj_var, width=38).grid(
            row=0, column=1, sticky="ew", padx=(6, 4))
        ttk.Button(self.b_frame, text="Browse…", command=self._browse).grid(row=0, column=2)

        ttk.Label(self.b_frame, text="Port:").grid(row=1, column=0, sticky="w", pady=2)
        self.port_var = tk.StringVar(value="7432")
        ttk.Entry(self.b_frame, textvariable=self.port_var, width=8).grid(
            row=1, column=1, sticky="w", padx=(6, 0))

        self.do_task = tk.BooleanVar(value=True)
        self.do_kb = tk.BooleanVar(value=bool(self.ides))
        self.do_claude_md = tk.BooleanVar(value=True)

        ttk.Checkbutton(self.b_frame, text="Add auto-start VS Code task",
                        variable=self.do_task).grid(
                            row=2, column=0, columnspan=3, sticky="w")
        kb_label = (f"Add Alt+D keybinding  ({', '.join(self.ides)})"
                    if self.ides else "Alt+D keybinding  (no IDE detected)")
        ttk.Checkbutton(self.b_frame, text=kb_label, variable=self.do_kb,
                        state="normal" if self.ides else "disabled").grid(
                            row=3, column=0, columnspan=3, sticky="w")
        ttk.Checkbutton(self.b_frame, text="Copy CLAUDE.md template to project",
                        variable=self.do_claude_md).grid(
                            row=4, column=0, columnspan=3, sticky="w")

        ttk.Separator(body, orient="horizontal").grid(
            row=r, column=0, columnspan=3, sticky="ew", pady=10)
        r += 1

        self.install_btn = ttk.Button(body, text="Install", command=self._run, width=18)
        self.install_btn.grid(row=r, column=0, columnspan=3)
        r += 1

        self.output = scrolledtext.ScrolledText(
            body, width=66, height=14, state="disabled",
            font=("Courier", 10), background="#1e1e2e", foreground="#cdd6f4",
            insertbackground="#cdd6f4")
        self.output.grid(row=r, column=0, columnspan=3, pady=(10, 0), sticky="ew")

    # ── Toggle helpers ────────────────────────────────────────────────────────

    def _toggle_vocab(self):
        state = "normal" if self.do_a2.get() else "disabled"
        for w in self.vocab_frame.winfo_children():
            try:
                w.config(state=state)
            except tk.TclError:
                pass
        if not self.do_a2.get():
            self.custom_entry.config(state="disabled")

    def _toggle_custom(self):
        if self.vocab_choice.get() == "__custom__":
            self.custom_entry.config(state="normal")
            self.custom_entry.focus()
        else:
            self.custom_entry.config(state="disabled")

    def _toggle_b(self):
        state = "normal" if self.do_b.get() else "disabled"
        for w in self.b_frame.winfo_children():
            try:
                w.config(state=state)
            except tk.TclError:
                pass

    def _browse(self):
        path = filedialog.askdirectory(initialdir=self.proj_var.get(), title="Select project directory")
        if path:
            self.proj_var.set(path)

    # ── Output ────────────────────────────────────────────────────────────────

    def _log(self, msg):
        self.output.config(state="normal")
        self.output.insert("end", msg + "\n")
        self.output.see("end")
        self.output.config(state="disabled")
        self.update_idletasks()

    # ── Installation ──────────────────────────────────────────────────────────

    def _run(self):
        self.install_btn.config(state="disabled", text="Installing…")
        threading.Thread(target=self._do_install, daemon=True).start()

    def _do_install(self):
        log = self._log
        need_restart = False

        if self.do_a1.get() or self.do_a2.get() or self.do_a3.get():
            log("── IDE Patches ───────────────────────────────────────")
            if self.do_a1.get():
                run_patch("claude-ui-layout.py", [], False, log)
                need_restart = True
            if self.do_a2.get():
                word = self.vocab_choice.get()
                if word == "__custom__":
                    word = self.custom_entry.get().strip() or "Working"
                run_patch("claude-ui-vocabulary.py", [word], False, log)
                need_restart = True
            if self.do_a3.get():
                run_patch("simplebrowser-title.py", [], self.sb_needs_sudo, log)
                need_restart = True

        if self.do_b.get():
            log("\n── Review Infrastructure ─────────────────────────────")
            project_dir = Path(self.proj_var.get()).expanduser().resolve()
            if not project_dir.exists():
                log(f"  ERROR: directory not found: {project_dir}")
                self.after(0, lambda: self.install_btn.config(state="normal", text="Install"))
                return
            port_str = self.port_var.get().strip()
            port = int(port_str) if port_str.isdigit() else 7432
            install_review_infra(project_dir, self.do_claude_md.get(), log)
            if self.do_task.get():
                install_task(project_dir, port, log)
            if self.do_kb.get():
                for ide in self.ides:
                    install_keybinding(ide, port, log)

        log("\n── Done ──────────────────────────────────────────────")
        if need_restart:
            log("Restart the extension host to activate IDE patches:")
            log("  Ctrl+Shift+P → Developer: Restart Extension Host")
        if self.do_b.get():
            log("")
            log("Start the doc server:")
            log("  python3 <project>/.claude/server.py &")
            log("Or open the project — the VS Code task starts it automatically.")
        self.after(0, lambda: self.install_btn.config(text="Done", state="disabled"))


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
