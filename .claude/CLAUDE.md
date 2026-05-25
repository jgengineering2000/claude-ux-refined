# AUR — Claude Instructions

## Inheritance

Universal engineering principles, collaboration rules, spec-doc rule,
communication style, and patent-IP whitelist live in `claude_master.md` at
this repo root, and are auto-loaded into every session via the
`~/.claude/CLAUDE.md` symlink. This file contains only AUR-specific guidance.

AUR is the authoritative source: edits to cross-project rules go into
`claude_master.md`, not here.

## Generated Documents

Write structured output (audits, plans, reviews) as HTML to `claude-docs/`, post a one-paragraph summary + link in chat, tell the user **Alt+D**. Never paste document content into chat.

- `.claude/` — server binary, config, port file (infrastructure)
- `claude-docs/` — all generated HTML documents and annotations (output/product)

1. Write `claude-docs/<name>-<date>-<HHMMSS>.html` (seconds precision avoids multi-session collisions)
2. `PORT=$(cat .claude/server.port 2>/dev/null || echo 7432)` — set `Alt+D` keybinding in `~/.config/Antigravity/User/keybindings.json` to `http://localhost:${PORT}/<name>-<date>-<HHMMSS>.html`
3. Server auto-starts via `Start Claude doc server` VSCode task; manual fallback: `python3 .claude/server.py &`

Every HTML doc must include `<script src="/manifest-link.js"></script>` just before `</body>` (injects the Manifest chip into the top bar; skip only for manifest.html itself).

Every HTML doc must include the annotation system from `templates/review-template.html` (CSS + JS verbatim).

## Prompt Library

`PROMPTS.md` is the canonical specification for all quick-prompt triggers. When the user
enters a trigger phrase, execute the full spec from PROMPTS.md for that trigger.

The prompt bar in `claude-docs/manifest.html` copies these trigger phrases to the clipboard.
The `PROMPTS` array in manifest.html must stay in sync with the triggers defined in PROMPTS.md.

## Release Process

When the user triggers `push release`, follow RELEASE.md exactly. Key steps:

1. **Build binary** — `pyinstaller --onefile --windowed --name claude-ux-installer install-gui.py`
   Output at `dist/claude-ux-installer`. Do not commit it.
2. **Source zip** — zip `patches/ server/ templates/ keybindings/ install.py install-gui.py
   README.md LICENSE PROJECT.md PROMPTS.md PATCHES.md WORKFLOW.md RELEASE.md`
   excluding `*.bak __pycache__/ *.pyc`. Save to `/tmp/claude-ux-refined-vX.Y.Z-source.zip`.
3. **Tag** — `git tag vX.Y.Z && git push origin vX.Y.Z`
4. **Release** — `gh release create vX.Y.Z --title "..." --notes "..."`
5. **Upload** — `gh release upload vX.Y.Z dist/claude-ux-installer /tmp/claude-ux-refined-vX.Y.Z-source.zip`
6. **Verify** — `gh release view vX.Y.Z --json assets --jq '.assets[].name'`

Gate: confirm version, changelog, and pre-flight checks before any tag/push/upload.
See RELEASE.md for the full procedure including release notes template.

## Project Context

- **Language:** Python 3 (patches, server, installer)
- **Config dir:** `~/.config/Antigravity/User/` (not `~/.config/Code/`)
- **Doc server:** port in `.claude/server.port` (default 7432)
- **Keybinding:** `Alt+D` → Antigravity Simple Browser / VS Code Simple Browser
