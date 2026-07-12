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
constraints: the **audit-methodology skill**. Every audit runs BOTH directions:
code→correctness ("is this site right?") AND spec→code coverage ("for each
behavior the design promises, point to the implementing code — or state 'none'");
the second traversal is the only one that finds documented designs never built.
For each central mutable structure, enumerate every writer and assert their
population/lifecycle models agree with each other and with the spec — a positive
check, not merely absence-of-violation.

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
Beyond fail-first: every fix/feature also adds or enhances coverage of adjacent
reachable paths while the file is in hand, and every plan/work item states a
concrete Before (observable defect) → After (observable outcome) — the After is
the acceptance criterion the test encodes. A reachable path with no verification
artifact is unfinished: extend a harness or build a tool to drive it, against
deterministic fixtures AND real-world data. When a result surprises, isolate the
case end-to-end before blaming the code-under-test — the verifier may itself be
wrong, and a real corpus is what stress-tests its assumptions.

## 5. Dev tests run through a committed teardown-and-guard harness, assistant-driven

Five fixed stages: guard/census every shared or session-fatal resource (refuse on
a stray — the guard detects, never cleans; a stray is a P8 defect in the
component); shut the running instance down cleanly; hand-launch the installed
binary on the SAME canonical resource under the chosen tool, driven by standard
clients (P9); a trap that ALWAYS restores; mine output with the crystallised
script. The harness is the method — ad-hoc hand sequences are how guardrails get
skipped. Full stage detail: the **audit-methodology skill**. (MTI instances:
`tests/dev_instrument.sh`, `tests/atspi_guard.sh`, `tests/syscall_audit.py`.)

## 6. Capture principles at the right altitude

When the owner states a general principle ("X should always…", a capability or
content rule), file it at the level its scope implies — universal →
`claude_master.md`; repeatable procedure → PROCESS; project fact → project
memory/spec — and do NOT demote it to a local task because it surfaced while
discussing one bug. A **task-shaped recipe** — guidance consulted only when a
specific task shape occurs (logging setup, an audit pass, a hazardous subsystem)
— files as a **skill** (AUR `skills/` symlinked global, or project skill if it
names project machinery), never as always-loaded text: the test is "would this
change behavior in a session that never touches its topic?" — if no,
always-loading it is Priority-2 waste. The skill's trigger lives in its
description; where a missed trigger is costly, an always-loaded principle keeps
a one-line "invoke the X skill before Y" anchor (P10→logging-discipline and
MTI's atspi-safety are the pattern). Reiterating a principle correctly in chat is NOT capturing
it; the in-chat echo is exactly what masks the filing error. When unsure whether
something was dropped, re-read the transcript from the request forward — recall
is the thing that fails here.

## 7. Ground plans in HEAD, not in the audit doc

Before planning from an audit/recommendation/spec document, verify each item
against HEAD (`git log --since=<doc-date> -- <files>` plus reading the live
sections) — an audit is a snapshot whose items may already be shipped, and
planning from it re-litigates settled work (P5). Cite commit SHAs for "already
done"; only the genuinely-unexecuted residue enters the plan.
