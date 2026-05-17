# Claude Code UX Improvements

Quality-of-life patches and workflow tooling for
[Claude Code](https://claude.ai/code), Anthropic's AI coding assistant.

Two independent layers — use either or both:

- **A. IDE Extension Patches** — improve the chat panel UI
  (VS Code and any VS Code-based fork)
- **B. Review Document Infrastructure** — generate, view, and
  annotate structured HTML documents from within the IDE
  (works with any Claude Code environment)

---

## A. IDE Extension Patches

These patch the Claude Code VS Code extension's webview assets.
They target the user-owned extension directory under `~/.vscode/` or
`~/.antigravity/` — **no sudo required** for the chat panel patches.

### A1. Chat Panel Layout

The default panel wastes horizontal space in a narrow side panel:

| Before | After |
|---|---|
| 30px left indent on assistant messages | 14px |
| 20px left/right container padding | 8px |
| Scrollbar reserves space even when hidden | Overlay mode |
| Timeline dot and vertical line misaligned | Aligned |

```bash
python3 patches/claude-ui-layout.py
```

### A2. Processing Vocabulary

Claude Code cycles through ~50 synonyms while thinking
("Spelunking", "Wibbling", "Shimmying"…).
This replaces the list with a single configurable word.

```bash
python3 patches/claude-ui-vocabulary.py            # "Working"
python3 patches/claude-ui-vocabulary.py "..."      # ellipsis
python3 patches/claude-ui-vocabulary.py ""         # hide it
```

### A3. Simple Browser Tab Title

VS Code's Simple Browser and Antigravity's "Jetski" both display a
static label ("Simple Browser" / "Jetski Preview") in the tab,
regardless of the page loaded. When you open multiple documents the
tabs are indistinguishable.

This patch makes the tab title reflect the filename of the page.

```bash
python3 patches/simplebrowser-title.py
```

Targets auto-detected from:
- VS Code: `/usr/share/code/…`
- VS Code (snap): `/snap/code/…`
- Antigravity: `/usr/share/antigravity/…`

The script checks whether the target file is writable before proceeding.
**System-installed** VS Code / Antigravity (apt/dpkg) store the extension
under `/usr/share/` (root-owned), so `sudo` is required.
**User-local installs** (AppImage, `~/.local/`) are writable without
elevation — run without `sudo`.

```bash
# system install (apt/dpkg) — target is root-owned
sudo python3 patches/simplebrowser-title.py

# user-local install (AppImage, ~/.local/) — no sudo needed
python3 patches/simplebrowser-title.py
```

If elevation is needed and not provided, the script exits with a clear
message rather than failing silently.

### Apply All

```bash
# Layout + vocabulary only (never needs sudo)
python3 patches/apply-all.py

# Include Simple Browser title fix:
#   system install (apt/dpkg)
sudo python3 patches/apply-all.py --browser
#   user-local install
python3 patches/apply-all.py --browser
```

After any patch: `Ctrl+Shift+P` → **Developer: Restart Extension Host**

> **Note:** Extension updates overwrite patches. Re-run after updating
> Claude Code. Each script detects already-patched files and is safe to
> re-run.

---

## B. Review Document Infrastructure

When Claude Code generates audits, reviews, or implementation plans,
the default is to paste the full content into the chat window. This
infrastructure redirects that output to styled HTML documents that
open inside the IDE.

Works with **any Claude Code environment** — VS Code, Antigravity,
or the CLI with any browser.

### What You Get

- Dark-themed HTML documents with colour-coded finding cards
- Per-finding annotation system, auto-saved to local JSON
- Sticky URL bar for opening documents in the IDE's Simple Browser
- Single-keypress document access (`Alt+D`)
- Annotations stored as plain JSON alongside the document —
  version-controllable, readable by Claude in future sessions

### Setup

**1. Copy the server into your project:**

```bash
mkdir -p yourproject/.claude
cp server/server.py yourproject/.claude/
```

**2. Start it** (add to your shell profile or a startup script):

```bash
cd yourproject/.claude && python3 server.py &
# Serves on http://localhost:7432/
```

**3. Add the keybinding** (VS Code / Antigravity):

Add to your IDE's user `keybindings.json`:

```json
{
  "key": "alt+d",
  "command": "simpleBrowser.show",
  "args": "http://localhost:7432/your-doc.html"
}
```

Update `args` to point at the latest document Claude generates.
Claude can do this automatically — see step 4.

**4. Add `CLAUDE.md` to your project:**

Copy `templates/CLAUDE.md.template` to your project root as `CLAUDE.md`
and fill in the project-specific section at the bottom.

This instructs Claude to:
- Write structured output as HTML to `.claude/`
- Update the `Alt+D` keybinding to point at the new file
- Post only a one-paragraph summary in chat
- Keep responses concise and formatted for a narrow panel

**5. Use the HTML template** for your own documents:

`templates/review-template.html` is a self-contained starting point
with the full CSS, card components, annotation system, and sticky
URL bar. Copy and fill in `{{TITLE}}`, `{{DATE}}`, `{{SCOPE}}`.

### Annotation Storage

Annotations are saved to `.claude/annotations/<docname>.json` via
`POST /annotations/<docname>` on the local server. They load
automatically when the page is opened. The JSON files are plain text
and can be committed to git or read by Claude directly.

---

## Compatibility

| Feature | VS Code | Antigravity | CLI + browser |
|---|---|---|---|
| Layout patch (A1) | ✔ | ✔ | — |
| Vocabulary patch (A2) | ✔ | ✔ | — |
| Simple Browser title (A3) | ✔ (sudo if system-installed) | ✔ (sudo if system-installed) | — |
| Doc server (B) | ✔ | ✔ | ✔ |
| CLAUDE.md workflow (B) | ✔ | ✔ | ✔ |
| Alt+D keybinding (B) | ✔ | ✔ | — |

The layout and vocabulary patches target the Claude Code extension's
webview CSS/JS using content patterns rather than hashed class names,
so they are reasonably robust across minor updates. If an update breaks
a patch the script reports which pattern it couldn't find.

---

## File Layout

```
claude-code-ux/
├── patches/
│   ├── apply-all.py               run this to apply everything
│   ├── claude-ui-layout.py        chat panel margins, dot, scrollbar
│   ├── claude-ui-vocabulary.py    replace cycling word list
│   └── simplebrowser-title.py     tab title fix (VS Code + forks, sudo)
├── server/
│   └── server.py                  annotation-capable doc server
├── templates/
│   ├── CLAUDE.md.template         project instructions for Claude
│   └── review-template.html       styled HTML review doc template
└── keybindings/
    └── antigravity.json           Alt+D binding example
```

---

---

MIT License — Copyright (c) 2026 Jonathan George

*Contributions welcome. Patches tested on Linux; the layout and
vocabulary scripts should work on macOS and Windows with the
appropriate extension paths.*
