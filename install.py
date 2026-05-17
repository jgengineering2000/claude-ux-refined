#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jonathan George
"""
Claude Code UX Installer
========================
Interactive installer for all Claude Code UX improvements.

Usage:
    python3 install.py
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

# ── Terminal helpers ──────────────────────────────────────────────────────────

def hr(char="─", width=58):
    print(char * width)

def section(title):
    print()
    hr()
    print(f"  {title}")
    hr()

def ask(prompt, default=None):
    hint = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"  {prompt}{hint}: ").strip()
        if raw:
            return raw
        if default is not None:
            return default

def ask_yn(prompt, default="y"):
    hint = "[Y/n]" if default == "y" else "[y/N]"
    while True:
        raw = input(f"  {prompt} {hint}: ").strip().lower()
        if not raw:
            return default == "y"
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please enter y or n.")

def ask_choice(prompt, choices, default=None):
    labels = "/".join(c.upper() if c == default else c for c in choices)
    while True:
        raw = input(f"  {prompt} [{labels}]: ").strip().lower()
        if not raw and default:
            return default
        if raw in choices:
            return raw
        print(f"  Enter one of: {', '.join(choices)}")

# ── IDE detection ─────────────────────────────────────────────────────────────

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

# ── Keybinding file helpers ───────────────────────────────────────────────────

def _strip_line_comments(text):
    """Strip // comments for JSONC parsing. Does not handle block comments."""
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

def install_keybinding(ide, port):
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
            print(f"    WARNING: could not parse {path} — will create a new file")
            data = []

    updated = False
    for i, item in enumerate(data):
        if item.get("key") == "alt+d" and item.get("command") == "simpleBrowser.show":
            data[i] = entry
            updated = True
            break
    if not updated:
        data.append(entry)

    path.write_text(json.dumps(data, indent=2) + "\n")
    action = "Updated" if updated else "Added"
    print(f"    {action} Alt+D keybinding → {path}")

# ── tasks.json helper ─────────────────────────────────────────────────────────

TASK_LABEL = "Start Claude doc server"

def install_task(project_dir, port):
    vscode_dir = project_dir / ".vscode"
    tasks_path = vscode_dir / "tasks.json"
    vscode_dir.mkdir(exist_ok=True)

    template = HERE / "server" / "tasks.json.template"
    new_task = json.loads(template.read_text())["tasks"][0]

    # If using a non-default port, inject CLAUDE_DOC_PORT into the command
    if port != 7432:
        new_task["command"] = f"CLAUDE_DOC_PORT={port} " + new_task["command"]

    if tasks_path.exists():
        try:
            data = json.loads(tasks_path.read_text())
        except (json.JSONDecodeError, ValueError):
            print(f"    WARNING: could not parse {tasks_path} — skipping task install")
            return
        tasks = data.get("tasks", [])
        for t in tasks:
            if t.get("label") == TASK_LABEL:
                print(f"    Task '{TASK_LABEL}' already present — skipping")
                return
        tasks.append(new_task)
        data["tasks"] = tasks
        tasks_path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"    Merged task into {tasks_path}")
    else:
        shutil.copy(template, tasks_path)
        print(f"    Created {tasks_path}")

# ── Review infrastructure ─────────────────────────────────────────────────────

def install_review_infra(project_dir, do_claude_md):
    claude_dir = project_dir / ".claude"
    docs_dir = project_dir / "claude-docs"
    claude_dir.mkdir(exist_ok=True)
    docs_dir.mkdir(exist_ok=True)

    files = [
        (HERE / "server" / "server.py",         claude_dir / "server.py"),
        (HERE / "server" / "manifest-link.js",  docs_dir / "manifest-link.js"),
        (HERE / "templates" / "manifest.html",  docs_dir / "manifest.html"),
    ]
    for src, dst in files:
        shutil.copy2(src, dst)
        print(f"    {src.name} → {dst}")

    if do_claude_md:
        dst = project_dir / "CLAUDE.md"
        if dst.exists():
            print(f"    CLAUDE.md already exists — not overwriting")
            print(f"      (template is at {HERE / 'templates' / 'CLAUDE.md.template'})")
        else:
            shutil.copy2(HERE / "templates" / "CLAUDE.md.template", dst)
            print(f"    CLAUDE.md.template → {dst}")
            print(f"    !! Edit {dst} — add project context at the bottom")

# ── Patch runner ──────────────────────────────────────────────────────────────

def run_patch(script, *args, use_sudo=False):
    cmd = (["sudo"] if use_sudo else []) + [sys.executable, str(HERE / "patches" / script)] + list(args)
    label = " ".join(str(c) for c in cmd[1:])  # omit sudo/python prefix for display
    print(f"\n  Running: {Path(script).name} {' '.join(args)}")
    subprocess.run(cmd)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("  Claude Code UX Installer")
    print("  " + "=" * 24)

    ides = detect_ides()
    if ides:
        print(f"\n  Detected IDE(s): {', '.join(ides)}")
    else:
        print("\n  No VS Code / Antigravity extension directory detected.")
        print("  IDE patches (A1–A3) will still be attempted if selected.")

    # ── Top-level feature selection ───────────────────────────────────────────
    section("Feature Selection")
    print()
    print("  [A]  IDE Extension Patches   — chat panel, vocabulary, tab titles")
    print("  [B]  Review Document Infra   — HTML docs, server, Alt+D keybinding")
    print("  [AB] Both")
    print()
    sel = ask_choice("Install which features?", ["a", "b", "ab"], default="ab")
    do_a = sel in ("a", "ab")
    do_b = sel in ("b", "ab")

    # ── Part A: configure ─────────────────────────────────────────────────────
    do_a1 = do_a2 = do_a3 = False
    vocab_word = "Working"
    sb_needs_sudo = False

    if do_a:
        section("Part A — IDE Extension Patches")
        print()

        do_a1 = ask_yn("A1  Chat panel layout  (reduced margins, overlay scrollbar)", default="y")
        do_a2 = ask_yn("A2  Processing vocabulary  (replace cycling word list)", default="y")
        do_a3 = ask_yn("A3  Simple Browser tab title fix", default="y")

        if do_a2:
            print()
            print("  Replacement word options:")
            print("    1  Working   (default)")
            print("    2  ...       (ellipsis)")
            print("    3  (empty)   (hides the label entirely)")
            print("    4  Custom")
            c = ask_choice("  Choice", ["1", "2", "3", "4"], default="1")
            vocab_word = {"1": "Working", "2": "...", "3": ""}.get(c)
            if vocab_word is None:
                vocab_word = ask("    Enter word", default="Working")

        if do_a3:
            sb_targets = [p for p in SIMPLEBROWSER_CANDIDATES if p.exists()]
            if not sb_targets:
                print("\n  A3: no Simple Browser extension found at known paths — will skip.")
                do_a3 = False
            else:
                unwritable = [p for p in sb_targets if not os.access(p, os.W_OK)]
                if unwritable:
                    print("\n  A3 targets require elevated access:")
                    for p in unwritable:
                        print(f"    {p}")
                    sb_needs_sudo = ask_yn("  Apply A3 with sudo?", default="y")
                    if not sb_needs_sudo:
                        do_a3 = False

    # ── Part B: configure ─────────────────────────────────────────────────────
    project_dir = None
    port = 7432
    do_task = do_keybinding = do_claude_md = False

    if do_b:
        section("Part B — Review Document Infrastructure")
        print()

        proj_input = ask("Target project directory", default=str(Path.cwd()))
        project_dir = Path(proj_input).expanduser().resolve()
        if not project_dir.exists():
            print(f"\n  Directory not found: {project_dir}")
            sys.exit(1)

        port = int(ask("Doc server port", default="7432"))
        print()
        do_task      = ask_yn("Add auto-start task to .vscode/tasks.json?", default="y")
        do_keybinding = ask_yn(f"Add Alt+D keybinding to IDE keybindings.json?", default="y") if ides else False
        do_claude_md = ask_yn("Copy CLAUDE.md template into project?", default="y")

        if do_claude_md and (project_dir / "CLAUDE.md").exists():
            print("    !! CLAUDE.md already exists — will skip, not overwrite.")

    # ── Confirmation summary ──────────────────────────────────────────────────
    section("Summary")
    print()
    if do_a:
        print("  Part A — IDE patches:")
        if do_a1: print("    A1  Chat panel layout")
        if do_a2: print(f"    A2  Vocabulary → \"{vocab_word}\"")
        if do_a3: print(f"    A3  Simple Browser title {'(sudo)' if sb_needs_sudo else ''}")
        if not any([do_a1, do_a2, do_a3]):
            print("    (nothing selected)")
    if do_b:
        print("  Part B — Review infra:")
        print(f"    Project:    {project_dir}")
        print(f"    Port:       {port}")
        print(f"    tasks.json: {'yes' if do_task else 'no'}")
        if ides:
            print(f"    Keybinding: {'yes (' + ', '.join(ides) + ')' if do_keybinding else 'no'}")
        print(f"    CLAUDE.md:  {'yes' if do_claude_md else 'no'}")
    print()
    if not ask_yn("Proceed?", default="y"):
        print("\n  Cancelled.")
        sys.exit(0)

    # ── Execute ───────────────────────────────────────────────────────────────
    if do_a:
        section("Applying IDE Patches")
        if do_a1:
            run_patch("claude-ui-layout.py")
        if do_a2:
            run_patch("claude-ui-vocabulary.py", vocab_word)
        if do_a3:
            run_patch("simplebrowser-title.py", use_sudo=sb_needs_sudo)

    if do_b:
        section("Installing Review Infrastructure")
        print()
        install_review_infra(project_dir, do_claude_md)
        if do_task:
            install_task(project_dir, port)
        if do_keybinding:
            for ide in ides:
                install_keybinding(ide, port)

    # ── Done ──────────────────────────────────────────────────────────────────
    section("Done")
    print()
    if do_a and any([do_a1, do_a2, do_a3]):
        print("  Restart extension host to activate IDE patches:")
        print("    Ctrl+Shift+P → Developer: Restart Extension Host")
        print()
    if do_b:
        server_path = project_dir / ".claude" / "server.py"
        print(f"  Start the doc server:")
        print(f"    python3 {server_path} &")
        print(f"  (or open the project in VS Code — task starts it automatically)")
        if do_claude_md and not (project_dir / "CLAUDE.md").exists():
            print(f"\n  Edit {project_dir / 'CLAUDE.md'}")
            print(f"    Add your project context below the marker line at the bottom.")
        print(f"\n  Press Alt+D to open the document manifest.")
    print()


if __name__ == "__main__":
    main()
