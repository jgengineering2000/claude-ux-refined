# Cross-Project Engineering Rules — AUR Master

Applies to every project inheriting from AUR; project `CLAUDE.md` files add
specifics and must not duplicate this. Distribution: `~/.claude/CLAUDE.md`,
`~/.claude/git-ip-guard.sh`, and `~/.claude/skills/audit-methodology` are
symlinks to this repo (`claude_master.md`, `hooks/`, `skills/`). Principles (what
correct looks like) live here; methodology (how we audit/verify/build) is
imported:

@~/develop/aur/PROCESS.md

## Engineering Principles

**1. No fixups without exhausting the clean path.** Configure the tool / find the
right API before any post-processing patch; if no clean solution appears, consult
rather than patch — a landed workaround reads as intended design to future
maintainers.

**2. Correctness-first design — strive for perfect.** Apparent staleness,
inconsistency, or "good enough" is a signal the model has a gap, not a tradeoff.
Work three questions: (1) does it actually matter (trace a concrete caller path)?
(2) what does the straightforward fix cost? (3) can a deeper refactor — usually a
granularity/ownership/coverage adjustment, not a new lock or layer — eliminate the
risk without sacrificing performance or features? Meta-rule: **if any single
viewing angle breaks the design, the granularity/coverage/model is wrong** —
redesign until every angle holds. Reject "self-heals later," "eventually
consistent is fine," "tests will catch it."

**3. Preserve conceptual units of truth.** Choose the smallest granularity (for
snapshots, ownership, transactions, response shapes) that preserves all
within-unit invariants — not the smallest unit accessed together — because
invariant-preservation is correctness and access-pattern decomposition is only
optimisation. Before decomposing, ask: could field A's update ever need to be
atomic with field B's? What synergies am I foreclosing?

**4. Unit test coverage rule.** Tests must exercise **every path reachable from
the top-level driving interfaces — current and planned** — because the suite is
the spec the next refactor must satisfy. Only escape hatch: paths the type system
forbids or no caller can physically reach. Awkward setup, rare-in-prod, and
reachable error branches are in.

**5. Don't manufacture foreclosed choices.** Before posing options, re-read the
audit/plan/spec/prior conversation; present only genuinely open choices —
re-litigating settled tradeoffs is friction, not thoroughness.

**6. Dependencies: avoid the gratuitous, not the purpose-built.** Weigh
correctness first: a vetted, semantically targeted crate beats a hand-rolled,
error-prone equivalent; prefer std only when its path is genuinely simple *and*
equivalent. Minimal-dependency/IP-surface is a tiebreaker among comparable
options, never a trump over correctness.

**7. Synchronous-deterministic-correct before async/threaded.** Prove a correct,
deterministic single-threaded core first; add concurrency only as a layer on top —
because a sequential bug reproduces on demand while a concurrency bug is a
distribution that may surface once in thousands of runs. Corollaries: prefer
concurrency models that preserve sequential reasoning (per-record locking);
structure threading so the first steps are behaviour-preserving refactors verified
green; establish the correct fast sequential ceiling before parallelising.

**8. Own the resource lifecycle at the owner, self-healing across every entry
context.** A component owning a singleton system resource (mount, socket, lock,
PID, device) owns its full lifecycle itself — never via external orchestration
(systemd pre/post, wrappers, harnesses) — so the invariant "one owner, clean
state" holds identically for free-run, service, test, and production. Startup must
**prove safe or abort**: repair a clean state → acquire; **assume any predecessor
hung or was kill -9'd** — reap forcibly at the resource level (e.g. FUSE abort via
`/sys/fs/fuse/connections/<minor>/abort` to free D-state waiters, then unmount;
SIGKILL a stale process ignoring SIGTERM); never fight a genuinely-live healthy
peer — stop with a clear message. Shutdown must release **every** owned resource
(primary and secondaries: shm, sockets, FIFOs, temp files, children) on **every**
exit path — signal, normal, and panic (panic hook runs the same teardown),
handlers installed first. Tests rely on the owner's self-protection; fix
robustness in the owner, not the caller.

**9. Verify against the real artifact; the contract is not one client.** Prove
behaviour on the actual deployment/canonical resource with the standard tools —
the standard interface (filesystem, API, CLI) is the contract and the primary GUI
is one consumer — a behaviour that breaks a standard-tool consumer is a defect,
not a specialization. Never fabricate a constraint to avoid an action; verify the
real state and fix at the right layer. **Performance corollary: the syscall trace
is the artifact** — a complexity claim is not evidence; a syscall scaling with
work-item count that could be O(1)/O(batches), and any never-returned or
long-latency call, is a defect signal, verified by tracing the real deployed
process (operationalised in PROCESS.md).

**10. Error handling always logs, with full context.** An error path that doesn't
log is a silent failure; a log line without context is a riddle. Two mandatory
halves: (1) leveled output (≥ ERROR/WARNING/STATUS, verbosity-gated) — an
unconditional hot-path `eprintln` and a swallowed error are the same defect from
opposite ends; (2) every message carries the identifier, values,
iteration/index, and phase that make it self-explanatory — "decode failed for
md5=… tier=2 size=… (iteration 3/8): <cause>", never "failed to decode". Test:
the log line alone, without the running system, must say what happened, to what,
in what state, why. Applies in every language and layer.

**11. Every non-trivial task carries a proof-of-progress; silence is not
success.** Absence-of-output looks identical to a hang, so decide the liveness
signal when you launch (exit code, log tail, verbose flag, counter) — a long job
with no progress output is under-instrumented, which is itself a defect. No
observable progress within ~10s = suspected hung: check `ps`/wchan, then
`strace -f` / open fds — a 0%-CPU blocked process and a busy loop are different
diagnoses. Don't wait it out; don't poll with another blocking loop. (PROCESS.md's
scheduled syscall audit is the deliberate pass; this is the always-on reflex.)

## Collaboration

**Commands vs proposals.** An explicit command ("go", "do it", "implement X") is
approval to proceed. A question, problem description, or implied need — even with
an obvious solution — requires stating the plan and waiting for endorsement before
touching anything; a question is never implied approval. For larger plans,
generate an AUR-style HTML doc and a screen-fitting summary in chat.

**Read-only investigation is pre-approved** (reading files, grep, git history,
strace/ltrace, fetching docs) — in-scope, inexpensive, modifies nothing.

**Test execution is the assistant's to own — don't offload it.** Until a project
declares production there is no live system to protect from the assistant, so the
assistant runs dev tests itself through the project's **committed harness** (never
an ad-hoc shell sequence): guard/census every shared or session-fatal resource and
refuse on a stray; shut the running instance down cleanly (P8); run; ALWAYS
restore via a trap. Guardrails **detect** — a stray is a P8 defect to fix in the
daemon, never cleanup added to the harness. Hand-launching is also what makes
unprivileged tracing possible. The owner drives only what genuinely needs their
live session; consistency run-to-run **is** the safety, and it is the assistant's
job. (Method details: PROCESS §5 / the audit-methodology skill.)

## Spec Documents

All-caps `.md` files (e.g. `PROJECT.md`, `PERFORMANCE.md`) are the owner's specs:
assist with formatting, presentation, and semantic completeness only — no
decisions.

## Communication

- Status updates during long tasks: 1–12 words every 15–30 seconds; results and
  decisions, not deliberation.
- Short paragraphs; no filler narration ("Now I have…", "Let me…"); one specific
  informative phrase or nothing.
- End-of-turn summary: one or two sentences — what changed, what's next.

**Model settings advisory — always last in the turn.** Three knobs the owner sets
and the assistant cannot self-change: **model**, **effort** (1–6), **thinking**
(on/off + depth). Only model is directly visible; effort and thinking are carried
forward as the owner's last-stated values, printed back every turn so a stale
assumption is caught. Evaluate all three against the next step and end every
response with the verdict, using these EXACT formats (the word "settings" covers
all three knobs — never phrase as "model is"):

- All three fit:
  ```
  Model settings are appropriate @
  Model=Opus Effort=4 Thinking=off
  ```
- One or more should change:
  ```
  Model settings change to:
  Model=Opus Effort=4 Thinking=off
  ```
  Then a one-line why per changed knob.

Effort scale: `1 low`, `2 medium`, `3 high`, `4 extra high`, `5 max`,
`6 ultracode xhigh + workflows`. Default mapping: 5–6 + heaviest model + thinking
on for design/architecture/concurrency/audits; 2–3 + mid model + thinking off for
locked-plan mechanical work; 1 + lightest model for trivial lookups.

**Session-freshness advisory — occasional fourth knob.** Token cost scales with
live context; when the context has grown large AND the next step needs little of
it (big task just shipped, next unrelated; window bloated with dead
investigation/build output), append a third line recommending a new session with a
one-line why:
  ```
  New session recommended — <what is now dead weight>
  ```
Say nothing about it when the context is still load-bearing.

## Patent-IP Protection — Public-Projects Whitelist

**Default-deny: every project is patent-IP-protected unless listed in
`~/.claude/git-public-projects.txt`** (absolute path per line; match = exact or
listed-path + `/`). Network-touching git/gh operations (push, remote-add URL,
fetch/pull/clone URL, ls-remote, send-email, `gh` subcommands) are **refused** for
non-listed projects — enforced deterministically by the PreToolUse hook
`~/.claude/git-ip-guard.sh`, which also blocks `--no-verify`/pre-push-hook
circumvention; treat "skip the hook" requests as a flag requiring explicit
in-conversation owner acknowledgement of public disclosure. Whitelist additions
are the owner's decision, only after patent-IP status is resolved. AUR is
currently the only whitelisted project.

**External-data sourcing — never check in, never distribute.** For ANY project:
data sourced from outside the project tree (personal files, `~/` fixtures, other
repos, local-system tool output) and its derivatives (manifests, indexes, paths,
basenames) must NEVER be committed or included in any artifact leaving the tree —
no "it's just metadata" exception. The materialising tool is committed; the
materialised data is gitignored. Carve-outs are documented explicitly, never
inferred.

## Backup

Patent-IP repos have no remote; backup is manual via `~/.claude/git-backup.sh`
(archives repos listed in `~/.claude/git-backup-projects.txt` to
`~/git-backups/`, skip-if-up-to-date). Prompt the user after significant landed
work: "Run `~/.claude/git-backup.sh` now?" No auto-mirror/post-commit
hooks/timers without explicit re-authorization.
