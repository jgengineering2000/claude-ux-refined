---
name: logging-discipline
description: Read BEFORE designing or adding logging, a logger, verbosity levels, or log output anywhere in any language — and BEFORE diagnosing an error, warning, race, hang, incomplete task, unknown state, or progress ambiguity whose investigation reveals missing observability. The full field contract, type-injection requirements, and sink rules that AUR P10 anchors.
---

# Logging Discipline — the P10 recipe

AUR P10 states the principle (every error path logs, with full context; types runtime-switchable; never a null sink). This skill defines the log type structure, bitmask evaluation model, centralized configuration, timestamp format, duplicate throttling, and sink routing rules.

## Design Philosophy — Log Types, Not Severity Levels

MTI uses a **bitmask-based log type** model, not the traditional hierarchical severity model found in most logging frameworks. Each log type is an independent bit that can be enabled or disabled individually. This means:

- Setting `LOGLEVEL=5` enables Error (1) + Debug (4) **without** enabling Info (2).
- Setting `LOGLEVEL=3` enables Error (1) + Info (2) **without** enabling Debug (4).
- A message is printed if `(type_bit & LOGLEVEL) != 0`.

This is a deliberate rejection of the hierarchical pattern (where enabling "debug" implicitly enables everything above it). Each type serves a different audience and purpose, and operators should be able to mix and match exactly the output they need.

## Log Types (Bitmask)

Four log types are defined, each occupying one bit:

| Type  | Bit | Value | Audience  | Aliases          | Description |
|-------|-----|-------|-----------|------------------|-------------|
| Error | 0   | 1     | Everyone  | Warn, Warning    | Something failed or is not working as expected. Includes warnings — a separate Warning level is differentiation without real value. |
| Info  | 1   | 2     | User      | Status, Verbose  | Stateful/Status information. Infrequent but detailed: stats on startup/shutdown of a connection, Nautilus window status, directory opens. INFO and STATUS are interchangeable aliases for the same log type and bit. |
| Debug | 2   | 4     | Developer | *(none)*         | Location-sensitive information: opening a new file, reading metadata, tracking fine-grained control flow. |
| Trace | 3   | 8     | Developer | *(none)*         | High-verbosity fast-path details that would normally drown the system but are needed when debugging hot paths. |

Note: INFO/STATUS/VERBOSE are **aliases** — they share the same bit and are interchangeable. DEBUG and TRACE are **semantically distinct** developer tools occupying separate bits: Debug targets control-flow granularity, Trace targets hot-path verbosity. They are never aliases of each other.

### Audience Classification

- **User-digestible** (potentially visible to end users): Error, Info (aliases: Status, Verbose)
- **Developer tools** (diagnostic only, semantically distinct from each other): Debug, Trace

### Common Composite Values

| Value | Meaning                    | Types Enabled            |
|-------|----------------------------|--------------------------|
| 0     | Silent                     | None                     |
| 1     | Errors only (default)      | Error                    |
| 3     | Errors + Info              | Error, Info              |
| 5     | Errors + Debug (no Info)   | Error, Debug             |
| 7     | Errors + Info + Debug      | Error, Info, Debug       |
| 15    | All types enabled          | Error, Info, Debug, Trace|

### String Parsing (cumulative masks)

When parsing named log levels from config or CLI, each name maps to a **cumulative** mask that includes all lower types in its audience tier:

- `ERROR`, `WARN`, `WARNING` → `1`
- `INFO`, `STATUS`, `VERBOSE` → `3` (Error + Info)
- `DEBUG` → `7` (Error + Info + Debug)
- `TRACE`, `ALL`, `TRUE`, `ON` → `15` (all types)
- `NONE`, `FALSE`, `OFF` → `0`
- Raw numeric strings (e.g., `"5"`) are used as-is

## Bitmask Evaluation

A log message with type bit $T$ is printed if $(T \mathbin{\&} \text{LOGLEVEL}) \neq 0$.

**Do NOT use threshold/comparison checks** like `severity <= loglevel`. Always use bitwise AND.

### Performance & Cost Gating

In compiled languages like Rust, log macros must check the enabled log level bit *before* evaluating any arguments or formatting strings. For example:
```rust
macro_rules! dlog {
    ($($a:tt)*) => {
        if $crate::log::is_level_enabled("Debug") {
            $crate::log::debug(&format!($($a)*))
        }
    };
}
```
This pattern ensures that when the corresponding log type is disabled:
1. **No string formatting** occurs.
2. **No heap allocations** are performed.
3. **No function call overhead** is incurred.

The runtime cost drops to a single fast CPU atomic bitwise check (typically 1–2 ns). This makes it safe to instrument code liberally (even in embedded environments) without introducing latency or memory pressure. Instrumentation should only be avoided or restricted in performance-dependent hot paths (e.g. raw encoder/decoder inner loops) where even nanosecond-level checks can accumulate.

## Centralized Configuration (`~/.config/mti/mti.conf`)

Log levels are configured via a centralized INI-style config file at `~/.config/mti/mti.conf`. This avoids the need for environment variables in `.bashrc` (which don't propagate to graphical desktop applications or systemd user services).

### Format

```ini
[global]
LOGLEVEL=7

[mtid]
LOGLEVEL=7

[mti-fuse]
LOGLEVEL=3

[trackmetad]
LOGLEVEL=3

[mti-sidecar]
LOGLEVEL=7

[mti-columns]
LOGLEVEL=3
```

### Resolution Order (highest priority first)

1. **Environment variable** `MTI_LOGLEVEL` — overrides everything (useful for one-off debugging)
2. **Process-specific section** in `mti.conf` (e.g., `[mtid]`) — matched against the binary name from `current_exe()` (Rust) or a hardcoded component name (Python)
3. **`[global]` section** in `mti.conf` — fallback default
4. **Hardcoded default** — `1` (Error only)

### Section Naming

Section names must match the **executable binary name**, not the host process:
- `[mtid]`, `[mti-fuse]`, `[trackmetad]`, `[mti-sidecar]` — Rust binaries
- `[mti-columns]` — the Nautilus Python extension (NOT `[nautilus]`, since it is not Nautilus)

## Field and Timestamp Contract

Every log line must be self-explanatory and contain full context:
- **Timestamp Format**: Exactly `YYYY-MM-DD_HH:MM:SS.ms` (e.g. `2026-07-14_01:28:08.123`).
- **Context fields**: `[Level]`, `[PID:nnn]`, `[Thread:name/ThreadId(n)]`, `[component]`
- **State**: Variable values, identifiers, sizes, and loop/iteration counters.

### Log Line Format

```
[2026-07-14_01:28:08.123] [Error] [PID:254656] [Thread:main/ThreadId(1)] [mtid] Something failed
```

## Duplicate Throttling (Deduplication)

To prevent log-spam and write bottlenecks:
- Consecutive identical log messages (same level and message text) are suppressed within a 5-second window.
- When the message text or level changes, or the 5-second window expires, a summary line `Last message repeated N times` is printed immediately prior to the next message.

## Target Sink Routing

### Per-Process Log Files

Each daemon/process writes to its own log file under `~/.local/share/mti/`:
- `mtid.log`, `mti-fuse.log`, `trackmetad.log`, `mti-sidecar.log`, `mti-columns.log`

The log filename is derived from the binary/component name, **not** the host process. The Nautilus extension log is `mti-columns.log`, not `nautilus.log`.

### Routing

- **File (Mandatory)**: Appended to the process-specific log file. Parent directories are auto-created.
- **Console (Optional/stderr)**: Written to locked standard error (enabled by default, can be disabled by setting `MTI_LOG_CONSOLE=0` or `MTI_LOG_CONSOLE=false`).

## Level Control

- **Startup**: Initialized by calling `init_from_env()` (Rust) or `load_config()` (Python) which reads `~/.config/mti/mti.conf` then checks `MTI_LOGLEVEL`.
- **Runtime**: Level changes can be made dynamically:
  - **Daemons**: Via the command FIFO socket (`loglevel:<val>`), AI Chat command (`/loglevel <val>`), or by sending `SIGUSR2` (toggles between Error=1 and Trace=8 verbosity).
  - **Non-Daemons**: Standard command utilities keep the `-v` / `--verbose` CLI options, which map to level `7` (Error + Info + Debug).
- **Storage**: A single atomic variable: `LOGLEVEL` (Rust `AtomicU8`) or `loglevel` (Python module global).

## Startup Logging

Every daemon must emit a structured startup block on launch that includes:
- All command-line arguments
- All parsed configuration settings
- All `MTI_*` environment variables
- The resolved log level value

This ensures that crash investigations always have the initial state context.

## Instrumentation Placement Rules

The mechanism sections above define HOW to log. This section defines WHERE — which code points must emit log statements and at which type. A logger without instrumentation is useless; these rules ensure that every user action, failure path, and state transition is observable.

### Info — User-Initiated Action Summary

Every user-initiated action must emit **at least one Info-level log line** summarizing what happened. This is the action's receipt — if an operator runs with `LOGLEVEL=3` (Error+Info), they should see a chronological record of every action the system performed and its outcome.

**Placement**: After the action completes (or fails), on the main/initiating code path.

**Content**: Action name, target (e.g. file path), and outcome (success, failure reason, or key result metric like elapsed time or output path).

```
[Info] [sidecar] Enhance completed for /photos/a.jpg → /photos/a_enhance.jpg (12.3s)
[Info] [sidecar] Enhance failed for /photos/a.jpg: fast_pass.sh exited with status 1
[Info] [sidecar] Regen (file) completed for /photos/a.jpg
```

### Debug — Pre-Action Context Snapshot

Before the first I/O, IPC, or subprocess action begins, emit **at least one Debug-level log line** capturing the full invocation context. This is the action's "black box recorder" — if a crash or hang occurs during execution, the Debug log is the last evidence of what was attempted.

**Placement**: After argument resolution but before the first side-effecting call (spawn, file write, DB update, FIFO write, D-Bus call).

**Content**: All resolved variables that influence the action's behavior:
- **Target**: file path, directory, hash
- **Configuration**: mode flags, quality tier, autoclean state, resolved input path (if different from the user-selected path, e.g. recovery composite)
- **Initiator**: button click, remote `ACTION:` dispatch, FIFO command, CLI
- **Computed values**: output path, resolved script path, subprocess arguments

```
[Debug] [sidecar] run_manual_cleanup: path="/photos/a.jpg" input="/photos/.mti/recovery/a_g5composite.jpg" output="/photos/a_g5composite_enhance.jpg" script="fast_pass.sh"
```

### Error — Happy-Path Deviation

Any point where the expected (happy) path cannot proceed must emit **at least one Error-level log line** with enough information to understand WHY it failed. This includes:
- Subprocess spawn failures (with the OS error)
- Non-zero exit codes from child processes (with the status code and, when available, stderr)
- File/DB/IPC operations that return errors
- Unexpected state (missing parent directory, no file stem, null path)

**Placement**: At the point of failure, before any early return or fallback.

**Content**: The operation that failed, the error value, and enough context to identify the specific call site (function name, target path).

```
[Error] [sidecar] run_manual_cleanup: failed to spawn fast_pass.sh: No such file or directory (os error 2)
[Error] [sidecar] run_manual_cleanup: fast_pass.sh exited with status 127 for /photos/a.jpg
[Error] [sidecar] run_recover: db.clear_fuse_thumbnail failed for md5=abc123: database is locked
```

### Trace — Hot-Path Instrumentation (On Demand Only)

Trace-level log lines are reserved for **hot paths** — code that runs per-item in a tight loop, per-frame, or per-event at high frequency (e.g. per-thumbnail serve, per-FUSE read, per-pixel decode). Trace lines are NEVER added speculatively; they are added only when a specific debugging need has been demonstrated (a proven bug, performance regression, or unexplained behavior on that path).

**Placement**: Only inside loops, callbacks, or handlers that fire at high frequency where Debug logging would cause backpressure or log flooding.

**Anti-pattern**: Do NOT use Trace for one-shot user actions, button clicks, or subprocess lifecycle events. Those are Debug or Info.

### Summary: Decision Table

| Situation | Type | Example |
|-----------|------|---------|
| User clicked a button / action dispatched | Info (outcome) + Debug (context) | "Enhance completed", "run_manual_cleanup: path=... input=... output=..." |
| Subprocess failed to spawn | Error | "failed to spawn fast_pass.sh: ..." |
| Subprocess exited non-zero | Error | "fast_pass.sh exited with status 127" |
| File/DB/IPC operation failed | Error | "FIFO write failed: broken pipe" |
| Unexpected null/missing state causing early return | Error | "path has no parent directory, aborting" |
| Per-item loop iteration (thumbnails, directory walk) | Trace (only if proven need) | "serve thumbnail for hash=abc123" |
| Daemon startup | Info (mandatory block) | CLI args, config, env vars |
| Configuration change at runtime | Info | "Log level changed to 7" |

## Timing Fields — logs as a live perf sensor (P7 corollary)

INFO-level logs of discrete operations (a scan, a decode batch, a serve, a
flush, a startup phase) carry the operation's **elapsed duration** as a
standard field — `... done files=142 elapsed=1.84s` — so any run with Info
enabled doubles as a perf-regression sensor: a regression shows up in the
ordinary log stream immediately, in flight, not in a later dedicated benchmark.
Where a stable expectation exists (recorded baseline), a breach beyond the
±30% band is logged at Error level with both actual and expected values.
Timing fields follow the same context contract as every other field: the
identifier, counts, and phase that make the number attributable on its own.
