---
name: logging-discipline
description: Read BEFORE designing or adding logging, a logger, verbosity levels, or log output anywhere in any language — and BEFORE diagnosing an error, warning, race, hang, incomplete task, unknown state, or progress ambiguity whose investigation reveals missing observability. The full field contract, level-injection requirements, and sink rules that AUR P10 anchors.
---

# Logging Discipline — the P10 recipe

AUR P10 states the principle (every error path logs, with full context; levels
runtime-switchable; never a null sink). This skill is the task-time contract.

## When logging is mandatory

Any context requiring research or information to understand after the fact:
errors, warnings, race conditions, failure to complete, unknown state/status,
debugging paths, and progress ambiguity (P11 liveness). If an investigator would
ask "what was happening?", the code must answer in the log.

## Field contract — each line self-explanatory

Provide as much context as possible, subject to the dedup rule below:

- **Location:** thread (id/name), pid, function, and runtime/component — enough
  to place the line in a concurrent, multi-process trace without a debugger.
- **Time:** millisecond-resolution timestamps.
- **State:** every global, thread-level, or function-level variable value
  relevant to the context or state — identifiers, sizes, indexes,
  iteration/phase counters, the P10 pattern ("decode failed for md5=… tier=2
  size=… (iteration 3/8): <cause>").
- **Dedup rule:** omit only what is *deterministically* provided by adjacent
  logging (same line-cluster, guaranteed-printed neighbor) — never omit because
  another line *usually* prints it; gated or reordered neighbors break that.

Test (from P10): the line alone, without the running system, says what
happened, to what, in what state, why.

## Level control — two mandatory mechanisms

1. **Startup:** environment variable(s) select the initial level.
2. **Runtime:** the component's **most robust existing input event interface**
   (its IPC socket, control FIFO, D-Bus surface, signal handler — whichever
   already exists and survives load) accepts log-level changes while running.
   Do not build a new channel if a sound one exists; do not pick a fragile one
   because it's convenient.

## Sink rules

- **Never /dev/null.** What isn't important can be turned *off* at the level
  gate; what is on must be **readable from a file** afterward. A discarded
  stream is indistinguishable from silence (P11) and destroys the post-mortem.
- Gate at the emit site (level check), not by redirecting the sink; an
  unconditional hot-path emit and a swallowed error are the same defect (P10).

## Applies

In every language and layer — Rust, Python, shell, systemd units, C shims —
matching each component's existing logging idiom rather than inventing a
parallel one.
