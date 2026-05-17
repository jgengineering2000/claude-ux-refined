# AUR — Review Document Workflow

This document specifies how the review-document infrastructure works end to end:
from Claude generating a document to the user reading, annotating, and referencing it
in a future session.

---

## Components and their roles

```
CLAUDE.md instructions
    │  tells Claude where to write and how to format
    ▼
claude-docs/<name>-<date>-<HHMMSS>.html
    │  static HTML document written by Claude
    ▼
.claude/server.py  (running in background)
    │  serves claude-docs/ on localhost
    │  stores/retrieves annotations as JSON
    ▼
Alt+D keybinding  →  simpleBrowser.show(http://localhost:PORT/manifest.html)
    │  single keystroke opens the manifest in the IDE's built-in browser
    ▼
manifest.html
    │  lists all documents with date, title, annotation count
    │  quick-prompt bar for one-click clipboard copy
    ▼
Per-document annotation system
    │  ✎ buttons on cards, headings, list items, table rows
    │  auto-saves to claude-docs/annotations/<docname>.json
    ▼
Future Claude session
    │  can read annotation JSON files directly
    │  reads spec docs via /spec/<filename> endpoint
```

---

## Document naming convention

```
claude-docs/<type>-<YYYY>-<MM>-<DD>-<HHMMSS>.html
```

- **type** — short slug describing the document kind: `audit`, `bench-plan`,
  `bench-results`, `session-close`, `code-quality`, `debug-plan`, `debug-results`,
  `release`.
- **seconds precision** — prevents collisions when multiple sessions run in parallel.
- The manifest strips the date suffix for display; the full filename is the stable
  permanent link.

---

## Server port selection

1. Check `CLAUDE_DOC_PORT` environment variable.
2. If unset, try port 7432.
3. If 7432 is taken, scan upward until a free port is found (limit: 100 ports).
4. Write the bound port to `.claude/server.port`.

CLAUDE.md and the installer read `.claude/server.port` to construct the correct
`http://localhost:PORT/…` URL. The Alt+D keybinding points to the manifest, not a
specific document; the manifest listing is dynamic.

---

## Annotation storage

Annotations are stored as plain JSON alongside the documents they annotate:

```
claude-docs/annotations/<docname>.json
```

Where `<docname>` is the HTML filename without extension.

The JSON structure is a flat object keyed by annotation ID:

```json
{
  "card-0": "This finding is already fixed in the current branch.",
  "head-2": "Defer until Phase 4.",
  "item-3-7": "Confirmed with integration test TC-14."
}
```

Annotation IDs are assigned at page-load time by the annotation JS and are stable
as long as the document structure does not change.

Because annotation files are plain text, they can be:
- Committed to git alongside the HTML documents
- Read directly by Claude in future sessions (`read /path/to/annotations/doc.json`)
- Diffed to track how review notes evolve over time

---

## CLAUDE.md instructions summary

Projects using AUR infrastructure add the following to their CLAUDE.md:

1. Write structured output as HTML to `claude-docs/`, never paste it into chat.
2. Filename format: `<type>-<YYYY>-<MM>-<DD>-<HHMMSS>.html`.
3. Post a one-paragraph summary + Alt+D reminder in chat after writing.
4. Update the Alt+D keybinding to point at the new document.
5. Every HTML document must include the annotation system CSS + JS verbatim.
6. Every HTML document must include `<script src="/manifest-link.js"></script>`
   before `</body>` (except `manifest.html` itself).

See `templates/CLAUDE.md.template` for the full boilerplate to copy into a project.

---

## Quick-prompt bar

The manifest includes a row of chip buttons populated from the `PROMPTS` array in
`manifest.html`. Clicking a chip copies the prompt text to the clipboard.

To customise prompts for a project, edit the `PROMPTS` array in the project's
`claude-docs/manifest.html`. The `PROMPTS.md` spec document defines the full
optimised instruction set for each trigger phrase.

---

## Server auto-start (VS Code task)

The installer adds a VS Code task to `.vscode/tasks.json`:

```json
{
  "label": "Start Claude doc server",
  "type": "shell",
  "command": "python3 '${workspaceFolder}/.claude/server.py'",
  "runOptions": { "runOn": "folderOpen" }
}
```

This starts the server automatically when the project folder is opened. The task
uses `presentation.reveal: "silent"` so it does not interrupt the editor layout.

---

## Manifest spec endpoint

The server exposes `/spec/<filename>` which renders any Markdown file from the project
root as styled HTML viewable in the IDE browser. This allows all-caps spec docs
(DESIGN.md, REQUIREMENTS.md, PROMPTS.md, etc.) to be read in the same environment
as generated review documents, without leaving the IDE.

Access via the "Project Specifications" table on the manifest page.
