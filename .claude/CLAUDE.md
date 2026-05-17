# AUR — Claude Instructions

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

## Collaboration

When the user asks a question ("is there a way to…", "could we…", "what about…"),
respond to it and ask before implementing. The question signals they want to consider
alternatives, not receive an immediate implementation.

## Spec Documents

All-caps `.md` files (PROJECT.md, PROMPTS.md, PATCHES.md, WORKFLOW.md) are owner's specs.
Assist with formatting, presentation, and semantic completeness only — no decisions.

## Project Context

- **Language:** Python 3 (patches, server, installer)
- **Config dir:** `~/.config/Antigravity/User/` (not `~/.config/Code/`)
- **Doc server:** port in `.claude/server.port` (default 7432)
- **Keybinding:** `Alt+D` → Antigravity Simple Browser / VS Code Simple Browser
- **Updates:** 1–12 words every 15–30 s during long tasks
- **Format:** Short paragraphs, no wall-to-wall prose
