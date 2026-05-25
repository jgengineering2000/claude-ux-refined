# Cross-Project Engineering Rules — AUR Master

These rules apply to every project that inherits from AUR. Project-level
`CLAUDE.md` files add project-specific guidance on top and must not duplicate
this content. Distribution model: `~/.claude/CLAUDE.md` is a symlink to this
file so Claude Code auto-loads it on every session regardless of cwd.

## Engineering Principles

**1. No fixups without exhausting the clean path.** Workarounds signal that
something upstream needs to be done correctly. Before implementing any
post-processing patch, exhaust the clean approach first (configure the tool,
find the right API, use the right option). If no clean solution is apparent,
consult rather than patch. A workaround that lands in the codebase will be
read by future maintainers as the intended design.

**2. Correctness-first design — strive for perfect.** Treat apparent
staleness, inconsistency, or "good enough" compromises as a *signal* that
the model has a gap, not as an inherent tradeoff. For any such case, work
the three-question framework:

  1. **Does it actually matter?** Trace the concrete caller path. If a real
     caller can observe the issue in a way that affects correctness,
     latency, or UX, the queueing/ownership model has a gap. Find it.
  2. **What's the performance impact** of closing the gap with the
     straightforward fix?
  3. **Can a deeper refactor eliminate the risk entirely** without
     sacrificing performance, latency, throughput, reliability, or features?
     Usually this is a granularity, ownership, or coverage adjustment — not
     a new lock or new layer.

  Meta-rule: **if any single viewing angle breaks the design, the
  granularity, coverage, or model is wrong.** Don't paper over the broken
  view; redesign until every angle holds. Anti-patterns to reject:
  "self-heals later," "eventually consistent is fine," "tests will catch
  it" — all framings that legitimise a broken view rather than fix the
  model.

**3. Preserve conceptual units of truth.** When choosing granularity for
snapshots, publication, ownership, transactions, or API response shapes,
preserve the conceptual unit (record, entity, document) as a whole even if
a finer-grained decomposition would be locally faster. The right granularity
is the smallest unit that preserves all within-unit invariants, not the
smallest unit that's accessed together.

  Counter-questions before decomposing:
  - *"Is there any future change where field A's update needs to be atomic
    with field B's update?"* If yes (or plausibly yes), keep them in the
    same unit.
  - *"What synergies between fields am I foreclosing?"*

  Access-pattern decomposition is *optimisation*; invariant-preservation is
  *correctness*.

**4. Unit test coverage rule.** Tests for a feature or component must
exercise **every path reachable from the top-level driving interfaces —
both the interfaces that exist now and the ones planned.** "Sanely manifest"
is the only escape hatch: paths the type system forbids or no caller can
physically reach are out; awkward setup, rare-in-prod, or error branches a
real caller can hit are *in*.

  The test suite is the *spec* a refactor must satisfy. Narrowing it to
  today's call sites leaves the next refactor (usually the reason the tests
  were written) without a safety net.

**5. Don't manufacture foreclosed choices.** Before posing a multiple-choice
question, re-read the audit / plan / spec / prior conversation for that
domain. Only present options that are *genuinely open*. If the prior work —
including documents generated in this session — already picked X with
reasons, honour that decision; don't re-pose "X vs not-X" as if the
question is open. Re-litigating settled tradeoffs is friction, not
thoroughness.

## Collaboration

**Commands vs proposals.** An explicit command ("go", "do it", "implement
X") is approval to proceed. A question, a problem description, or an
implied need — even when the solution is obvious — requires stating the
plan first and waiting for endorsement before touching anything. A question
is not a command and is not implied approval. For larger plans, generate
an AUR-style HTML doc and present a screen-fitting summary in chat.

**Read-only investigation.** Reading files, grepping code, checking git
history, running strace/ltrace, fetching docs — these are pre-approved and
require no plan or endorsement. They are in-scope, inexpensive, and modify
nothing.

## Spec Documents

All-caps `.md` files (e.g. `PROJECT.md`, `PROMPTS.md`, `PATCHES.md`,
`WORKFLOW.md`, `PERFORMANCE.md`) are the owner's specs. Assist with
formatting, presentation, and semantic completeness only — no decisions.

## Communication

- Status updates during long tasks: 1–12 words every 15–30 seconds. State
  results and decisions, not deliberation.
- Output format: short paragraphs, no wall-to-wall prose.
- No filler narration. Avoid "Now I have…", "Let me…", "I'll now…",
  "I'll go ahead and…" phrasings. One specific informative phrase, or
  nothing.
- End-of-turn summary: one or two sentences max — what changed and what's
  next.

## Patent-IP Protection — Public-Projects Whitelist

**Default-deny model.** Every project on this system is treated as
patent-IP-protected by default. The whitelist of projects cleared for
network-touching git/gh operations is at `~/.claude/git-public-projects.txt`
— one absolute path per line, comments allowed.

**Before any of these operations**, in any project, consult the whitelist.
A repo is permitted only if its absolute path is either an exact match or
starts with a listed path followed by `/`. If the project is not on the
whitelist, **refuse** the operation:

- `git push`, `git push --mirror`, `git push --force`
- `git remote add <name> <URL>` where the URL is not file:// or a local path
- `git fetch <URL>`, `git pull <URL>`, `git ls-remote <URL>`
- `git clone <URL>` if the target directory will land in a not-listed parent
- `git send-email`, `git request-pull`, `git format-patch` piped to a
  network sink
- `gh repo create`, `gh repo clone` (across orgs), `gh pr ...`,
  `gh release ...`, any other `gh` subcommand that touches GitHub

**Do not bypass the pre-push hook.** Refusing `--no-verify`, deletion of
`.git/hooks/pre-push`, or any other hook-circumvention without an explicit,
in-conversation acknowledgement from the user that they are disclosing the
project publicly. Treat "skip the hook" requests as a flag, not a directive.

**Adding to the whitelist** is the user's decision. If asked to add a
project, confirm patent-IP status is resolved (published, abandoned, or
otherwise cleared) before editing the file.

**AUR is currently the only whitelisted project.** MTI, WWI, FAIP, and any
other project under `~/develop/` not explicitly listed are
patent-IP-protected.

## Backup

Patent-IP repos have no automated mirror or remote. Backup is manual via
`~/.claude/git-backup.sh` (wraps `git archive` over the list in
`~/.claude/git-backup-projects.txt`, writes `<repo>-<ts>.tar.gz` + `.sha`
sidecar to `~/git-backups/`, skip-if-up-to-date). Prompt the user at every
session-memory checkpoint: "Run `~/.claude/git-backup.sh` now?" Do not
propose post-commit hooks, systemd timers, or any auto-mirror without
explicit re-authorization.
