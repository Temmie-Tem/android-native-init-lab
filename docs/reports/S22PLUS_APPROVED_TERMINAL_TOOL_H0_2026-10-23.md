# S22+ approved ordinary-terminal tool H0

The user requested a tool through which Codex can use the ordinary terminal
for the existing approved S22+ entry. This H0 unit implements a foreground
user-started worker and a four-tool STDIO MCP transport. The worker requires
uid/euid 1000 and NoNewPrivs=0; it does not change process privileges, polkit,
system services or Codex permission settings. The agent-side transport may
remain under NoNewPrivs=1. No device command is part of installation or testing.

The [tool contract](../operations/S22PLUS_APPROVED_TERMINAL_TOOL_V1.md)
defines the fixed root-evidence/journal-recovery scope and startup command.
It exposes worker status, prepared-task status, one approved entry dispatch,
and a bounded log tail. Exact task/proposal/source/entry/review/approval and
preceding-closure bindings remain mandatory. The existing grant opener,
attended execution, current target checks and original-A recovery stay in the
original runner. The transport accepts no arbitrary shell command or approval.

## Validation and independent review

`py_compile` and 20 focused host tests pass. The fixtures exercise real Python
children, detached process sessions, actual Unix sockets and the STDIO MCP
CLI, initialization/list/call framing and unavailable-worker responses.
They cover duplicate and concurrent dispatch, process death, uncertain launch,
missing/wrong approval, changed source/entry/review, existing attempts/owner,
direct-path checks, FIFO/symlink rejection, bounded logs and actual Linux
NoNewPrivs startup refusal. No fixture invokes a physical task entry.

The independent review returned **PASS_GO**, with no unresolved findings,
against eight exact capability sources and the tool contract. The
[public review binding](../../workspace/public/src/device-action/bindings/s22plus_approved_terminal_v1_review.json)
is copied unchanged from the reviewed payload and passes the real consumer.
Findings corrected before that final review are:

- Persist the dispatch directory's parent before spawning, as well as the
  immutable intent and its containing directory.
- Treat launcher exit as an observation, not closure. A different task remains
  blocked until the exact original healthy task closure and its bound Android
  terminal exist and the original F1 owner is absent.
- Reject nonregular log paths before opening them and use nonblocking open so
  an accidental FIFO cannot leave a log-reader thread waiting indefinitely.
- Bind the running worker to its initial reviewed revision. A newly reviewed
  disk revision requires a worker restart before dispatch, so old imported
  Python code cannot inherit the replacement review.

Past-failure applicability: ROUTE/WIRE/PERSIST/SEMANTIC confirmed through the
real entry-consumer fixture, actual IPC, durable intent-before-spawn ordering
and separate process-exit/device-closure assertions. Physical artifact, ARM64
ABI, device-time bounds and USB recovery behavior are unchanged and not newly
qualified by these host tests. No kernel/image build or live experiment was
needed for this transport unit.

## Retained state and use

The actual P454 prepared bundle passes the new read-only current-source
validator. Its task identity and 88 protected predecessor/preparation records
are unchanged. P454 still has no operator approval record, grant, dispatch,
execution log or device operation. No P454 approval is inferred from the
request to build this tool. The 46 pre-existing dirty paths are unchanged;
A90 and S20+ were untouched.

The `s22_approved_terminal` Codex MCP server is registered with `/usr/bin/python3`
and this repository's `s22plus_approved_terminal_v1.py mcp`. The exact configured
process passed initialization and advertised all four tools. `bridge_status`
correctly reports the worker unavailable before user startup. The original
configuration bytes and settings are preserved with only this server appended;
the CLI's incidental removal of an empty existing argument list was restored.

Live worker availability remains unproved until the operator starts the
foreground worker in an ordinary terminal using the linked contract's command.
Once connected, `bridge_status` and `task_status` can establish host connection
and readiness without opening P454. Physical task execution remains subject to
its exact returned approval and attendance. Private review, validation and
registration evidence is retained under the terminal-bridge H0 output.
