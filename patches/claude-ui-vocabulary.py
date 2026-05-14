#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jonathan George
"""
Claude Code Vocabulary Patch
==============================
Replaces the ~50-word rotating "processing" vocabulary
("Germinating", "Spelunking", "Wibbling", ...) with a single
static word. Cute the first time; annoying by the tenth session.

Targets: ~/.antigravity/extensions/anthropic.claude-code-*/webview/index.js
         (or the equivalent path for standard VS Code)

No sudo required. Safe to re-run.

Usage:
    python3 claude-ui-vocabulary.py              # defaults to "Working"
    python3 claude-ui-vocabulary.py "..."        # ellipsis
    python3 claude-ui-vocabulary.py ""           # empty string (hides label)
"""

import glob
import re
import shutil
import sys
from pathlib import Path

SEARCH_PATTERNS = [
    "~/.antigravity/extensions/anthropic.claude-code-*/webview/index.js",
    "~/.vscode/extensions/anthropic.claude-code-*/webview/index.js",
]

# First word in the array — used as an anchor to locate it
ANCHOR = '"Germinating"'


def find_js_files():
    files = []
    for pattern in SEARCH_PATTERNS:
        files.extend(glob.glob(str(Path(pattern).expanduser())))
    return files


def patch_file(path, replacement_word):
    src = Path(path).read_text()

    idx = src.find(ANCHOR)
    if idx < 0:
        # Check if already patched
        if f'["{replacement_word}"]' in src or '["Working"]' in src:
            print(f"  already patched")
            return False
        print(f"  ERROR: anchor {ANCHOR} not found — extension may have updated")
        return False

    start = src.rfind('[', 0, idx)
    end = src.find(']', idx) + 1
    old_array = src[start:end]

    if not old_array.startswith('["'):
        print(f"  ERROR: unexpected array start: {old_array[:40]}")
        return False

    word_count = old_array.count('","') + 1
    new_array = f'["{replacement_word}"]'

    backup = path + ".bak"
    shutil.copy2(path, backup)
    print(f"  backup: {backup}")

    Path(path).write_text(src[:start] + new_array + src[end:])
    print(f"  replaced {word_count}-word array with {new_array}")
    return True


def main():
    word = sys.argv[1] if len(sys.argv) > 1 else "Working"
    files = find_js_files()

    if not files:
        print("ERROR: Claude Code extension JS not found.")
        sys.exit(1)

    for f in files:
        print(f"\nPatching: {f}")
        patch_file(f, word)

    print("\nDone — restart the extension host:")
    print("  Ctrl+Shift+P → Developer: Restart Extension Host")


if __name__ == "__main__":
    main()
