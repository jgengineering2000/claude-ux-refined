#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jonathan George
"""
Apply all Claude Code UX patches.

Usage:
    python3 apply-all.py                   # layout + vocabulary (no sudo)
    sudo python3 apply-all.py --browser    # + Simple Browser title fix
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def run(script, *args):
    cmd = [sys.executable, str(HERE / script)] + list(args)
    print(f"\n{'='*50}")
    print(f"Running: {script}")
    print('='*50)
    subprocess.run(cmd)


def main():
    run("claude-ui-layout.py")
    run("claude-ui-vocabulary.py")

    if "--browser" in sys.argv:
        run("simplebrowser-title.py")

    print("\n" + "="*50)
    print("Done. Restart the extension host:")
    print("  Ctrl+Shift+P → Developer: Restart Extension Host")


if __name__ == "__main__":
    main()
