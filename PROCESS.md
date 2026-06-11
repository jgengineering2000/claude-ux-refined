# Process & Methodology — AUR Master

These are **methodology** rules — *how* we audit, verify, and build, as distinct
from the universal engineering *principles* in `claude_master.md` (which say *what*
correct looks like). This file is inherited by every downstream project the same way
the principles are; project `PROCESS.md` (if any) adds project-specific workflow on
top and must not duplicate this content.

The line between the two files: a *principle* is a property the finished system must
have (correctness-first, preserve units of truth, own the lifecycle). A *process* is
a repeatable procedure for getting there or proving you did (how to run an audit, how
to verify a fix, when to crystallise analysis into a tool). When in doubt: if it
describes the artifact, it's a principle; if it describes our actions, it's process.

---

## 1. Crystallise once-solved analysis into a refined script — don't re-derive it

**The rule.** Complex, deterministic analytical processing that has been *worked out
once* should be captured in a script the model **calls**, not reasoning the model
**repeats** every time. The script is cached reasoning. Re-deriving "parse this trace,
group by syscall and path, find the per-item repeats, find the long and the
never-returned calls" on each audit spends expensive deep-thinking on a *solved*
problem — and, worse, solves it slightly differently each run, so results aren't
comparable across sessions.

**Why it matters.** Two failure modes it removes: (a) **cost** — the model burns its
hardest reasoning on a procedure that has one right answer already known; (b)
**inconsistency** — a hand-redone analysis drifts, so a regression looks like noise.
A refined tool is deterministic, fast, and improvable: each time it misses something,
you sharpen *the tool*, and every future audit inherits the sharpening.

**Where it applies (not just strace).** Any deterministic analytical pass over machine
output: syscall-trace mining, Valgrind/callgrind/massif parsing, log-pattern
extraction, DB query-plan analysis, allocation profiling, diff-classification. If you
find yourself reasoning step-by-step through the *same shape* of machine output a
second time, that's the signal to write the tool.

**The discipline.** First time: solve it by hand, carefully, and note the procedure.
Second time the same shape appears: stop and write the script instead of redoing it.
Thereafter: call the script, spend your reasoning on the *findings*, and refine the
script when it misses. The tool lives at the project level (it encodes project-shaped
patterns); the *practice* of building it is this process rule.

## 2. Comprehensive audits fan out per subsystem and read end-to-end

A real audit is **not** a pattern-driven sample taken to prove a point. When the task is
"audit the codebase," the method is:

- **One agent (or pass) per subsystem**, each reading **all** its assigned files *end to
  end* — not greps, not excerpts, not "until I find something." A sampling audit reports
  ~15% and gives false confidence; the fan-out reads 100%.
- **A single shared rubric** across all agents so findings are comparable: correctness,
  optimisation (buffer reuse, syscall/context consolidation — these are *standing* lenses
  the owner asks for on every audit, not one-off findings), hoisting (within and across
  modules), exception/error-handling normalisation (measured against `claude_master.md`
  principle 10 — leveled output + full-context messages, not mere consistency), code
  quality, and the mechanical lint baseline (captured *once*, up front, as ground
  truth — see rule 1).
- **Stable finding IDs and severities** (P1 correctness, P2 perf/hoist, P3 quality), each
  with file:line and a concrete fix, consolidated into **one annotatable document**.
- **The highest-impact, most-falsifiable claims are re-verified directly in source** by
  the consolidator before they're asserted as P1 — an agent's reasoning is a lead, the
  source is the proof.

Independent subsystems audit in parallel; only spawn sub-agents when the owner has asked
for the fan-out (per the spawn-restraint rule), and give each the safety constraints for
its area (e.g. an AT-SPI/session-fatal component is *read-only, never run*).

## 3. Differential syscall-tracing is a standard audit pass

Operationalises the `claude_master.md` P9 performance corollary. Across a **defined
process roster** (every component we influence, not just the GUI), trace the real
deployed process and flag:

- **per-item syscalls** — anything scaling O(files / rows / requests) that should be
  O(1) or O(batches) (a per-file `stat` of a shared config/IPC file is the canonical
  catch);
- **incomplete calls** — an enter with no matching return (a hang/leak);
- **long-latency calls** — duration outliers.

Capture with **full fork/thread following, buffer contents, and per-call latency +
timestamps** so the trace shows *what* was touched and *how long* it took, not merely
that a call happened. This is exactly the kind of analysis rule 1 says to crystallise
into a tool rather than re-reason each time. Tracing an already-running process is
read-only and safe; never *start* a session-fatal component (e.g. an AT-SPI listener)
to trace it — attach to the one already up.

## 4. Every fix lands with a test that fails first

A bug fixed without a fail-first test is a fix you can't prove and a regression waiting
to return. Before the fix: write the test, run it, watch it **fail** for the right
reason. Then fix. Then watch it pass. This is doubly required for audit findings — many
exist *precisely because the code path had no coverage*, so the missing test is part of
the defect, not an extra. (This is the procedural companion to the `claude_master.md`
unit-test-coverage *principle*: the principle says what must be covered; this says you
prove the fix by reversing red→green, not green-from-the-start.)
