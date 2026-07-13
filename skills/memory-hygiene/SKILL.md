---
name: memory-hygiene
description: Read BEFORE setting up a project's persistent memory system, or when a project's memory recall root has grown large / feels bloated / over-fires on unrelated tasks — the three proven cuts (checkpoints out of recall, SETTLED archived not deleted, one-trigger descriptions) and the always-loaded-baseline vs. recall-corpus distinction.
---

# Memory-Recall Hygiene (proven in MTI, 2026-06-25 → 2026-07-13)

## The problem this targets

A session can hit a large token count fast even when the fixed always-loaded
baseline (masters + project `CLAUDE.md` + `MEMORY.md`) is small. The usual
driver is the **file-based memory recall corpus**: as a project's `project_*`/
`feedback_*` memory files accumulate, broad multi-topic descriptions match
almost any query, so a growing fraction gets injected up front every turn.
Diagnose which cost is which before optimizing — the baseline chain is fixed
and cheap; the recall corpus is what grows unbounded and needs active upkeep.

## Three cuts, in the order that actually worked (not the order originally planned)

1. **Move crash-survival/checkpoint scratch out of the recall root.**
   Session-checkpoint files are crash-survival scratch, not durable knowledge —
   relocate them to something like `.claude/checkpoints/` and stop indexing
   them in the always-loaded index. Redirect any cron/hook that writes them so
   it doesn't refill the recall root.
2. **Archive SETTLED memories — never delete.** A `project_*` file describing
   shipped/closed/superseded work still carries "why we did X" value but
   shouldn't front-load during active work. Demote its pointer into a
   secondary index (e.g. `MEMORY-archive.md`) while keeping the file itself
   recallable and retrievable by hand. This can happen organically, per file,
   as memories are written and closed out — it does not require a big
   one-time ACTIVE/SETTLED classification batch to start paying off.
3. **One file, one trigger.** Rewrite each memory's `description:` to a
   single ≤~15-word condition ("recall when X"), not a summary of its
   contents — the body already holds the detail. Multi-topic, 40-70-word
   descriptions match almost any task and defeat the point of scoped recall.
   Where a file legitimately covers two unrelated triggers, that's a sign it
   should be split into two memories.

## Before rewriting descriptions, know what you're optimizing for

Confirm — from the project's own `MEMORY.md` header, or by asking — whether
recall keys on `description:` frontmatter alone (not body). If so, cut 3 above
is a pure precision play regardless of whether matching is top-K-ranked or
match-all; a narrower trigger can only reduce false-fires either way. Don't
block the whole pass on reverse-engineering ranking internals that aren't
introspectable from outside the harness — the safety net below covers the risk
regardless of the answer.

## Risk & safety net

Over-narrowing a description risks a genuinely relevant memory going
unrecalled on a given turn. Mitigation: keep the always-loaded index
(`MEMORY.md`) as the backstop — it lists every memory by a one-line hook
regardless of whether recall fires, so a missed recall is recoverable by
reading the index, not lost. Never delete a memory as part of this hygiene;
archive means relocate out of the recall path, always retrievable.

## Applies

Any AUR-inheriting project accumulating memory — apply proactively once the
recall root starts feeling bloated (session token counts jump at start,
descriptions run long, files keep piling up), rather than waiting for it to
become an ongoing per-session cost. MTI instances: `.claude/checkpoints/`,
`.claude/inherited-aur-anchors/`, `MEMORY-archive.md`.
