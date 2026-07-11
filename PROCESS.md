# Process & Methodology — AUR Master

Methodology rules — *how* we audit, verify, and build (the principles — *what*
correct looks like — live in `claude_master.md`). Inherited by every project; a
project `PROCESS.md` adds workflow on top without duplicating this. When in
doubt: describes the artifact → principle; describes our actions → process.

## 1. Crystallise once-solved analysis into a refined script — don't re-derive it

Complex, deterministic analytical processing worked out once (trace mining,
Valgrind/log/query-plan/diff parsing) becomes a script the model **calls**, not
reasoning it repeats — re-deriving burns expensive reasoning on a solved problem
and drifts between runs, so regressions look like noise. First time: solve by
hand, note the procedure. Second time the same shape appears: write the tool.
Thereafter: call it, reason only over its findings, and sharpen the tool when it
misses. **Never hand-mine machine output with the reasoning model** — repetition
(multi-line included), anomalies, incomplete-call pairing, context/buffer capture,
and counts belong in an analyzer with stable indexed references; eyeballing a log
in chat is the signal to write it.

## 2. Comprehensive audits fan out per subsystem and read end-to-end

One agent/pass per subsystem reading 100% of its files (sampling gives false
confidence); a single shared rubric (correctness, optimisation, hoisting, P10
error-handling, quality, lint baseline captured once); stable finding IDs with
severities (P1/P2/P3) and file:line fixes in one annotatable doc; the
consolidator re-verifies the most falsifiable P1 claims in source. Full method +
constraints: the **audit-methodology skill**.

## 3. Differential syscall-tracing is a standard audit pass

Operationalises the P9 corollary: across the defined process roster, trace the
real deployed process; flag per-item syscalls, incomplete calls, and latency
outliers; capture with fork-following, buffers, and per-call latency/timestamps.
Never start a session-fatal component to trace it. Full capture flags + roster
discipline: the **audit-methodology skill**.

## 4. Every fix lands with a test that fails first

Write the test, watch it fail for the right reason, fix, watch it pass — a fix
without a red→green reversal is unproven and a regression waiting to return.
Doubly required for audit findings: the missing coverage is part of the defect.

## 5. Dev tests run through a committed teardown-and-guard harness, assistant-driven

Five fixed stages: guard/census every shared or session-fatal resource (refuse on
a stray — the guard detects, never cleans; a stray is a P8 defect in the
component); shut the running instance down cleanly; hand-launch the installed
binary on the SAME canonical resource under the chosen tool, driven by standard
clients (P9); a trap that ALWAYS restores; mine output with the crystallised
script. The harness is the method — ad-hoc hand sequences are how guardrails get
skipped. Full stage detail: the **audit-methodology skill**. (MTI instances:
`tests/dev_instrument.sh`, `tests/atspi_guard.sh`, `tests/syscall_audit.py`.)
