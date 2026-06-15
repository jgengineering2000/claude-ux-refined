# Cross-Project Engineering Rules — AUR Master

These rules apply to every project that inherits from AUR. Project-level
`CLAUDE.md` files add project-specific guidance on top and must not duplicate
this content. Distribution model: `~/.claude/CLAUDE.md` is a symlink to this
file so Claude Code auto-loads it on every session regardless of cwd.

This file holds the engineering **principles** (what correct looks like); the
companion **methodology** (how we audit, verify, and build) lives in
`PROCESS.md`, imported here so it inherits identically:

@~/develop/aur/PROCESS.md

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

**6. Dependencies: avoid the gratuitous, not the purpose-built.** Minimizing
dependencies means avoiding crates that duplicate something the standard
library does cleanly, or that add build/IP surface for marginal convenience.
It does *not* mean hand-rolling a more error-prone version of something a
mature, purpose-built crate does correctly. Weigh correctness and risk first:
if a dependency is the more semantically targeted, lower-risk, better-fit tool
(e.g. a vetted concurrent-map crate vs a hand-written two-level locking
discipline with real deadlock surface), the dependency wins. Prefer the
standard library only when its path is genuinely simple *and* equivalent —
*equivalent-and-simple* favours std; *more-correct-or-much-safer* favours the
crate. Minimal-dependency/IP-surface is a tiebreaker among comparable options,
never a trump over correctness.

**7. Synchronous-deterministic-correct before async/threaded.** Establish a
correct, deterministic, single-threaded core *first*; introduce concurrency
(async, threads, pools, locks) only as an additive layer on top of a proven
sequential implementation. The reason is debuggability: a sequential bug is
reproducible (same input → same failure) and traceable under a debugger; a
concurrency bug is a *distribution* of behaviours whose pathological corner
cases may surface once in thousands of runs and never on demand. Building logic
and concurrency together means a failure could be either — and the corner cases
that hold correctness (malformed input, boundary conditions, partial state) are
precisely the ones that become intermittent and unattributable once buried in a
worker. Get them right while the path is still deterministic; then the *only*
new risk concurrency adds is the concurrency itself. Corollaries: prefer a
concurrency model that preserves sequential reasoning (e.g. per-record locking,
where you still reason about one unit at a time) over one that requires
whole-system reasoning; structure threading work so the first sub-steps are
behaviour-preserving refactors verified green before any thread is spawned; and
the same logic applies to performance — establish the correct fast sequential
ceiling, *then* parallelise, because concurrency multiplies a known-good unit
and cannot rescue a broken one.

**8. Own the resource lifecycle at the owner, self-healing across every entry
context.** A component that owns a shared, singleton system resource — a mount, a
listening socket, a lock file, a PID/port, a device — owns its full lifecycle
*itself*, not via external orchestration (systemd `ExecStartPre`/`ExecStopPost`,
wrapper scripts, test harnesses). On startup it must repair what a prior instance
left behind: a clean state → acquire; a dead orphan (crashed owner) → reap and
self-heal; a *live* peer already holding it → stop with a clear message, never
fight. On shutdown it must release cleanly on **every** signal/exit path
(SIGTERM/SIGINT/SIGHUP/normal), with the handler installed *first*, so cleanup
fires regardless of launch context or how far startup got. Startup-repair and
shutdown-release are synergistic — each guarantees the other's precondition — so
the invariant ("one owner, clean state") holds for *whoever* runs the component:
free-run, service-managed, test, or production, identically. The orchestrator
just launches the binary; it does not manage the resource. Corollary: when a test
needs the resource, it relies on the owner's self-protection (and frees the
resource the same way a redeploy would) rather than reimplementing reap/guard
logic — fix robustness in the owner, not the caller.

**9. Verify against the real artifact, and the contract is not one client.** Test
and prove behaviour against the *actual* deployment / canonical resource, not a
convenient fiction (a throwaway temp mount no real consumer reads, a mock that
diverges from production, a happy-path stand-in). If a system exposes a standard
interface (a filesystem, an HTTP API, a CLI), that interface — exercised by the
standard tools — *is* the contract; the primary GUI/SDK client is one consumer
among many, and a behaviour that works for it but breaks a standard-tool consumer
(or vice-versa) is a defect, not an acceptable specialization. And never
*fabricate* a constraint to avoid an action ("I can't touch this, it's a runtime
gate") — verify the real state, identify the right layer, and fix it there.

  **Performance corollary — the syscall trace is the artifact, not the code or
  the comment.** A complexity claim ("O(1) per call", "one extra getxattr per
  file", "never re-opens") is *not* evidence; the trace is. Code review and
  doc-comments routinely miss a per-item syscall that a `strace -f` surfaces
  instantly — a function can *look* O(1) while doing an extra `stat` of a shared
  IPC/config file on every item. So treat differential syscall-tracing as a
  *correctness* check, not merely a perf tool: **a syscall that scales with the
  work-item count (files, rows, requests) when it could be O(1) or O(batches),
  and any incomplete (never-returned) or long-latency call, is a defect signal**
  — verified against the trace of the real, deployed process, not asserted from
  the source. (How to operationalise this — capture flags, per-process roster,
  the once-solved-analysis-into-a-script rule — is methodology, in `PROCESS.md`.)

**10. Error handling always logs, and every message carries the context that
makes the failure self-explanatory.** Error handling and logging are not separate
concerns: an error path that does not log is a silent failure, and a log line that
omits its context is a riddle. Two requirements, both mandatory:

  1. **Capability — leveled output.** Logging must distinguish at least
     `ERROR` / `WARNING` / `STATUS`, gated by a verbosity control. Severity is not
     decoration: it is how an operator filters signal from noise. An unconditional
     debug `eprintln` on a hot path and a swallowed error are the *same* defect from
     opposite ends — one logs without a level, the other has a level (error) and
     doesn't log. Neither is acceptable.
  2. **Content — full context, every message.** Every log/error message must include
     *all* the relevant data that makes it instantly obvious *what* failed and *in
     which state*: the identifier (inode, key, path, request id), the data or
     parameter values, the iteration/index, and the status/phase. The reader should
     never have to reproduce the failure to learn what it was about — the message
     *is* the diagnosis. "Failed to decode" is a non-message; "decode failed for
     md5=… tier=2 size=… (iteration 3/8): <cause>" is a message.

  The test: read the log line alone, with no access to the running system. If it does
  not tell you what happened, to what, in what state, and why, the message is
  incomplete — fix the message, not just the bug. This applies in every language and
  every layer (daemon, CLI, UI, shell, service unit), not only where a logger already
  exists.

**11. Every non-trivial task carries a proof-of-progress; silence is not success.**
The moment you start anything that runs longer than a glance — a build, a long
command, a hook, a migration, a generation loop, a remote job — you must *also* have
a concrete mechanism that tells you it is **advancing**, not stalled, looping, or
silently failing. "It's probably still working" is not an observation; it is the
absence of one, and absence-of-output looks identical to a hang. The discipline:

  1. **Decide the liveness signal before (or as) you launch**, not after it worries
     you. Cheapest first: check the result/exit code, tail the log, add a `-v`/verbose
     or progress flag, print a per-iteration counter. If the tool gives you nothing,
     that lack is itself the defect to fix (a long job with no progress output is
     under-instrumented) — but in the meantime you still owe yourself a probe.
  2. **Escalate to the trace when output is missing or ambiguous.** If a thing makes
     no observable progress within ~10 seconds, treat it as *suspected hung* and look —
     `ps`/`wchan` to see if it's blocked vs. burning CPU, then `strace -f` (or read
     its open fds) to see the actual syscall it is stuck in or repeating. Do **not**
     wait it out, and do **not** poll it with another blocking loop (which can itself
     stall the same way). A blocked process at 0% CPU and a busy one repeating the same
     call are different diagnoses with different fixes — the trace distinguishes them in
     seconds. (This is the same artifact-not-assertion stance as P9: the trace tells you
     what is happening; "it should be progressing" does not.)
  3. **The reflex is general; the scheduled syscall-audit is one instance of it.**
     PROCESS.md's differential syscall-tracing pass is a deliberate, after-the-fact
     audit over a defined roster — it catches per-item O(files) calls, never-returned
     calls, and latency outliers *when you point it at them*. This principle is the
     live, always-on counterpart: the habit that makes you point a trace at the stuck
     thing *right now*, mid-task, before it has wasted minutes. Build the proof in;
     don't discover its absence by staring at a frozen terminal.

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

**Test execution is the assistant's to own — don't offload it.** Until a
project declares "production," there is no live system to protect from the
assistant, so the assistant runs development tests *itself*, locally, having
first taken full precautions through the project's **committed harness** (not
an ad-hoc shell sequence): engage every guardrail in *every* context — most
critically for any **session-fatal / destructive-on-unclean-teardown shared
subsystem** (an accessibility or IPC layer that can crash the whole desktop
session, a singleton mount/device/socket whose double-acquire corrupts state):
census it, refuse to proceed on a stray — then shut the running instance down
cleanly so it releases its resources via its own lifecycle (P8), run, and ALWAYS
restore on exit via a trap. The guardrails
**detect** incorrect cleanup; they do not implement it — a stray the guard
flags is a P8 defect to fix in the daemon/tool's own startup-repair and
signal-handled shutdown, never by adding cleanup to the harness. This clean-teardown
stance is *also* what makes unprivileged tracing possible: strace / ltrace /
valgrind / gdb on a **hand-launched** instance need no privilege escalation (no
`ptrace_scope` fight, no setuid-mount-under-ptrace dead end), whereas attaching
to a service-managed instance does. Pushing repeatable test-running or guardrail
discipline back onto the owner is a redirection of responsibility, not a safety
measure — the assistant is in the better position to keep those steps
*consistent* run-to-run, and that consistency **is** the safety. The owner drives
only what genuinely needs their live interactive session; everything the harness
can do shut-down-and-guarded, the assistant does, every time, without being asked.

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

**Model settings advisory — always last in the turn.** There are THREE
independent knobs the owner sets and the assistant cannot self-change:
**model**, **effort** (1–6), and **thinking** (on/off + depth). At the end of
every turn, evaluate all three against what the *next* step needs and put the
verdict as the **final** element of the response (after the end-of-turn
summary) so it is never missed.

**Visibility caveat.** The assistant can only see **model** directly (it's
surfaced in system context). **Effort** and **thinking** have no readout —
the assistant carries the owner's last-stated values forward as an
assumption. Printing those values back every turn lets the owner spot a
stale assumption immediately and correct it before the assistant acts on it.

Use these EXACT formats — the word "settings" is semantically inclusive of
all three knobs, whereas "model is" would suggest only the model, so never
phrase it that way. Always print ALL THREE values on the second line so the
owner sees the assistant's working assumption every turn:

- If all three already fit the next step:
  ```
  Model settings are appropriate @
  Model=Opus Effort=4 Thinking=off
  ```

- If one or more should change:
  ```
  Model settings change to:
  Model=Opus Effort=4 Thinking=off
  ```
  Then a one-line why for each knob that actually changed (skip the unchanged
  ones).

**Effort scale** (post-2026-05-29 Claude Code update): `1 low`, `2 medium`,
`3 high`, `4 extra high`, `5 max`, `6 ultracode xhigh + workflows`. Level 6
is the new ceiling, reserved for the most demanding multi-step coding and
workflow-driven tasks.

State what's next, then the verdict block (two lines). Default mapping:
level 5–6 + heaviest model + thinking on for design, architecture,
concurrency-correctness, audits, and demanding multi-step coding; level 2–3
+ mid model + thinking off for locked-plan mechanical work (renames, dedup,
commits, running tests); level 1 + lightest model for trivial lookups. The
owner switches via `/model`, `/fast`, the effort control, and the thinking
toggle; this advisory is the only signal they get, since the assistant
cannot change its own model/effort/thinking.

**Session-freshness advisory — a fourth, occasional knob.** Session lifecycle
(start a new session / clear context) is a fourth thing only the owner controls
and the assistant cannot self-change. Every turn re-sends the accumulated
transcript, so token cost scales with context length: once the live context has
grown large *and* the next step needs little of it — typically right after a big
task finishes and the next is unrelated, or when long investigation / build /
trace output has bloated the window — continuing spends tokens on dead weight
that a fresh session avoids. Unlike the three always-printed knobs (which are a
working-assumption readout), this is actionable advice, so surface it ONLY when
it actually applies: add a third line to the verdict block recommending a new
session with a one-line why (what is now dead weight). When the current context
is still load-bearing for the next step, say nothing about it — do not print a
"session is fine" line every turn.

- When a fresh session would save tokens (append the third line):
  ```
  Model settings are appropriate @
  Model=Opus Effort=4 Thinking=off
  New session recommended — <what is now dead weight, e.g. "audit shipped; next task is unrelated">
  ```

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

**External-data sourcing — never check in, never distribute, never promote.**
For ANY project (whitelisted or not), data sourced from outside that project's
own tree — the user's personal files, test fixtures pulled from `~/`, snippets
copied from other repos, output of system tools that reveals local-system
state — must NEVER be checked in, committed, added to a tarball/archive, or
included in any artifact that could leave the project tree. This covers the
data itself AND its derivatives (manifests, indexes, file lists, paths,
basenames — anything that reflects local-system content or layout). If a test
or tool needs such data, the data lives only on the local filesystem, the
tool that materialises it from the local source is committed, and the
materialised data is gitignored. A "small / it's just metadata / nobody will
notice" exception is not a thing — the rule is absolute. If the user later
clarifies a specific carve-out, that carve-out is documented explicitly, not
inferred.

## Backup

Patent-IP repos have no automated mirror or remote. Backup is manual via
`~/.claude/git-backup.sh` (wraps `git archive` over the list in
`~/.claude/git-backup-projects.txt`, writes `<repo>-<ts>.tar.gz` + `.sha`
sidecar to `~/git-backups/`, skip-if-up-to-date). Prompt the user at every
session-memory checkpoint: "Run `~/.claude/git-backup.sh` now?" Do not
propose post-commit hooks, systemd timers, or any auto-mirror without
explicit re-authorization.
