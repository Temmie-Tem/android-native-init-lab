# S22+ approved ordinary-terminal tool V1

Status: **H0 capability; startup requires the matching independent PASS_GO
binding; no device authority**.

The operator requested a tool connecting the ordinary terminal to this chat.
Its bounded purpose is to start an already reviewed and explicitly approved
S22+ root-evidence or journal-recovery task, then expose status and bounded logs.
The benefit is removing repeated manual launch commands while preserving the
existing finite grant, attendance, target, recovery and no-replay checks.
P454's task, sources, entry and approval hash remain unchanged.

## Execution boundary

The operator starts the foreground worker as the original uid/euid 1000 in an
ordinary terminal with NoNewPrivs=0. It remains unprivileged. No setuid binary,
polkit rule, system service, sandbox setting or process privilege flag is
changed. A Codex STDIO MCP process forwards four fixed tool operations over a
same-UID, mode-0600 Unix socket inside a mode-0700 runtime directory. There is
no TCP listener, tunnel, shell command field, stdin injection or arbitrary
executable/path selection. The worker never opens ADB, USB or serial endpoints.

The tools report worker status, report a prepared task's status, dispatch its
approved entry once, and return a bounded tail of its launcher/execution log.
Preparation directories must be direct S22+ H0 outputs in this repository.
The original task/proposal, current capability source hashes, frozen snapshot
manifest, independent prepared-entry review, exact entry and predecessor pins
must agree. Dispatch additionally requires the existing actual operator
approval record and absence of a prior grant, operation, host-preflight attempt
or execution log. The tool accepts no approval text and creates no approval.
Artifacts and review records never replace direct human authorization.

Only the exact reviewed Python entry is started, with no entry arguments and
no shell. That entry still invokes the unchanged grant opener and original
attended CLI. Fresh connected checks and any physical Download action remain
owned by that runner and the attending operator. This tool adds no new device
effect, recovery mode or repeat authority. A90 and S20+ remain outside scope.

## Dispatch and shutdown

A durable host dispatch intent precedes process creation. Repeated requests
return the existing dispatch state and never launch a second process. A launch
error or uncertain worker loss preserves the record for H0 investigation;
original device journals determine any authorized recovery. This is the
existing no-replay rule applied to a new dispatch transport, not a new device
approval or renewable budget.

The entry owns a separate process session with logs on disk. Closing the MCP
connection or worker does not terminate it. The tool has no cancel, kill,
continue, recover or force-retry operation. After a worker restart, PID/start
identity, launch records and original task records are observations only;
missing process/output never proves that the operation did not execute.
Ctrl-C stops the worker accepting new requests. It is not a device recovery.

The worker serializes dispatch across the complete original task lifetime.
Process exit, including exit zero, does not resolve a dispatch. A different task
requires the exact original healthy task closure and its bound Android terminal,
plus absence of an F1 owner; missing or uncertain closure permits observation
only. This stop covers possible surviving descendants or incomplete recovery,
applies to this dispatch until original healthy closure is proved, and is
reviewed again if the execution or recovery machinery changes. No new recovery
route or general pre-effect-failure override is created.

The worker uses no target transport and holds no
device descriptor, so it cannot compete with the existing console or recovery.
Local same-UID repository tampering remains outside the repository's ordinary
threat model; other UIDs, path confusion, accidental replay and partial output
are checked within this tool's scope.

## Qualification and use

Independent review must bind the reachable bridge source, record helper and
this document before production worker startup. The worker retains that review
identity and requires a restart when a new reviewed revision replaces it, so
old loaded code cannot inherit the new on-disk review. H0 tests cover the actual
MCP/stdin and Unix-socket framing with harmless fixtures, duplicate/concurrent
dispatch, changed or missing approvals/sources, invalid paths/UIDs, bounded logs,
restart/uncertain process state and the actual NoNewPrivs startup refusal.
No fixture launches a physical entry. The live connection is verified with
status only after the operator starts the reviewed worker.

Codex configuration adds only this named MCP server and retains existing
permissions and servers. The STDIO transport follows the
[MCP transport specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
and uses the supported
[Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp).
Registration/start commands and final validation are recorded in the completion
report. Tool connection alone does not open the pending P454 grant.

Start the foreground worker once in an ordinary user terminal, without sudo:

```sh
python3 /home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/host_tools/s22plus_approved_terminal_v1.py serve
```

The `s22_approved_terminal` Codex MCP registration runs the same script with
`mcp`. Reload that MCP server or reopen Codex after registration if the four
tools are not yet visible. `bridge_status` confirms the connection without
opening a task, and `task_status` can inspect the retained P454 preparation.
Keep the worker terminal open during use and the operator physically present
for an approved device task. Worker availability is separate from device health.
