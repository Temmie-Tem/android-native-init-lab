# S22+ approved ordinary-terminal tool V1

Status: **H0 capability; startup requires the matching independent PASS_GO
binding; no device authority**.

The operator requested a tool connecting the ordinary terminal to this chat.
Its bounded purpose is to start an already reviewed and explicitly approved
S22+ root-evidence, journal-recovery or Debian automatic-boot task, then expose
status and bounded logs. Automatic boot also has fixed original-return and
post-return health continuations. The fixed profiles select one attended operation:
root-evidence and journal-recovery have 1800 seconds; `debian-autoboot-v1`
selects only `debian-autoboot` with 3600 seconds. The task still has no E.
The benefit is removing repeated manual launch commands while preserving the
existing finite grant, attendance, target, recovery and no-replay checks.
P454's task, sources, entry and approval hash remain unchanged.
P456's task, sources, entry and returned approval likewise remain unchanged.
Its independently reviewed core receipt uses an exact candidate/profile/version
schema and `verdict=PASS_GO`; require the public capability's pointer to that
same receipt. Earlier core receipts retain their original `status` format.

## Execution boundary

The operator starts the foreground worker as the original uid/euid 1000 in an
ordinary terminal with NoNewPrivs=0. It remains unprivileged. No setuid binary,
polkit rule, system service, sandbox setting or process privilege flag is
changed. A Codex STDIO MCP process forwards six fixed tool operations over a
same-UID, mode-0600 Unix socket inside a mode-0700 runtime directory. There is
no TCP listener, tunnel, shell command field, stdin injection or arbitrary
executable/path selection. The worker never opens ADB, USB or serial endpoints.

The tools report worker status, report a prepared task's status, dispatch its
approved entry once, continue an automatic-boot return, resume post-A health,
and return bounded tails of the four fixed logs.
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
general recovery or force-retry operation. After a worker restart, PID/start
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

## Existing automatic-boot continuation

`continue_approved_task` selects only `debian-autoboot-v1` and the existing
single `operation-0001`. It requires the original dispatch to have a bound
process-exit record, the same host epoch, an unexpired original grant, the same
active F1 owner, consumed operation, four complete pre-return steps revalidated
by the original raw consumers, and the exact `debian-return-ready.json` bound
to that operation and shutdown. Its original deadline, capped at ten minutes,
must remain current. A stopped journal, Android-return start/intent/result,
terminal, unused operation, closed task or competing live owner rejects the
request before process creation. Physical Download remains the operator's
action; the original runner checks its exact endpoint. Existing attendance and
approval apply without a second grant or approval request.

`resume_approved_health` is a separate automatic-boot path for the observed
post-A read-failure case. It requires exactly one `install-android` transfer
intent and the original adapter's raw-derived completed transfer. Missing or
uncertain transfer evidence rejects it; it never selects a general recovery
path. The fixed command is the original `recover --attended` CLI for the same
operation, whose existing-A branch reconstructs that transfer and performs only
remaining health/closure. It cannot fall through to another A transfer. An
expired grant may retain its original recovery semantics, but the host epoch,
owner, artifacts and current source closure must still match. No deadline is
renewed. Healthy terminals and closed tasks require no device continuation.

Each continuation has its own exclusive durable intent before spawn, bound to
the original start, task, approval, grant, operation, journal tail, applicable
ready/raw-A proof and current bridge review. It has a separate process/result
and bounded log (`continuation` or `health`). Duplicate or uncertain requests
return their existing state; a spawn error never permits a retry. A subsequent
health continuation requires any earlier normal continuation to have a bound
process exit. The existing target lease excludes a running manual owner during
admission; the original CLI takes that lease and rechecks the durable journal
before any action. A manual invocation racing the launch cannot replay an
already-intended transfer. A process exit is never healthy closure.

These are the existing owner/no-replay requirements applied to two missing
transport operations. They address duplicate return and uncertain-transfer
hazards, apply only to the named automatic-boot continuation, and resolve when
the original owner proves healthy closure. Changes to continuation, transfer
or recovery semantics trigger independent review. They add no research budget,
new image, new experiment, native control replay or new recovery mechanism.

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
`bridge_status` reports the loaded review identity; connection alone does not
prove that a running worker has loaded the newly reviewed implementation.
Each transport extension has its own review binding; retained reviews and
consumed dispatch records are not repinned. It adds no live reload or restart
command. The operator stops the old idle listener with Ctrl-C and starts the
same `serve` command below after qualification.

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
`mcp`. Reload that MCP server or reopen Codex after registration if the six
tools are not yet visible. `bridge_status` confirms the connection without
opening a task, and `task_status` can inspect the retained P454 preparation.
Keep the worker terminal open during use and the operator physically present
for an approved device task. Worker availability is separate from device health.
