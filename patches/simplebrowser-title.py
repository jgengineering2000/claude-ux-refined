#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jonathan George
"""
Simple Browser / Jetski Tab Title Patch
=========================================
VS Code's Simple Browser and Antigravity's "Jetski" both set a static
panel title when first opened and never update it as the URL changes.
Every document you open shows the same generic tab label.

This patch makes the tab title reflect the filename of the loaded page,
so multiple documents are distinguishable at a glance.

Targets (auto-detected):
  Antigravity:   /usr/share/antigravity/resources/app/extensions/simple-browser/dist/extension.js
  VS Code:       /usr/share/code/resources/app/extensions/simple-browser/dist/extension.js
  VS Code (snap):/snap/code/current/usr/share/code/resources/app/extensions/simple-browser/dist/extension.js

REQUIRES SUDO — these files are system-owned.

Usage:
    sudo python3 simplebrowser-title.py
"""

import shutil
import sys
from pathlib import Path

CANDIDATES = [
    Path("/usr/share/antigravity/resources/app/extensions/simple-browser/dist/extension.js"),
    Path("/usr/share/code/resources/app/extensions/simple-browser/dist/extension.js"),
    Path("/snap/code/current/usr/share/code/resources/app/extensions/simple-browser/dist/extension.js"),
]

# The show() method pattern — identical across VS Code and forks
OLD = (
    "show(t,e){this._webviewPanel.webview.html=this.getHtml(t),"
    "this._webviewPanel.reveal(e?.viewColumn,e?.preserveFocus)}"
)

# Replaces static title with the filename portion of the URL
NEW = (
    "show(t,e){"
    'const _p=t.split("/").pop().replace(/\\.[^.]+$/,"")||"Preview";'
    "this._webviewPanel.title=_p;"
    "this._webviewPanel.webview.html=this.getHtml(t),"
    "this._webviewPanel.reveal(e?.viewColumn,e?.preserveFocus)}"
)


def patch(path):
    src = path.read_text()

    if "_webviewPanel.title=_p" in src:
        print(f"  already patched")
        return False

    if OLD not in src:
        print(f"  ERROR: pattern not found — extension may have updated")
        print(f"         Check extension.js manually")
        return False

    backup = str(path) + ".bak"
    shutil.copy2(path, backup)
    print(f"  backup: {backup}")
    path.write_text(src.replace(OLD, NEW, 1))
    print(f"  patched OK")
    return True


def main():
    targets = [p for p in CANDIDATES if p.exists()]

    if not targets:
        print("No Simple Browser extension found at known paths.")
        print("Searched:")
        for p in CANDIDATES:
            print(f"  {p}")
        sys.exit(1)

    any_changed = False
    for target in targets:
        label = target.parts[2]  # 'antigravity' or 'code'
        print(f"\n[{label}] {target}")
        any_changed |= patch(target)

    if any_changed:
        print("\nRestart the extension host (no full IDE restart needed):")
        print("  Ctrl+Shift+P → Developer: Restart Extension Host")


if __name__ == "__main__":
    main()
