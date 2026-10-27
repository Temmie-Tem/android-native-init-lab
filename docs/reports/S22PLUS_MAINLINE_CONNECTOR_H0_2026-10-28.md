# S22+ mainline connector completion — 2026-10-28

The preceding integration connected the mainline observer to the Session CLI
but left the ordinary-terminal connector on its older task profiles. Its v9
review also bound older common/target/Session sources. A direct `bridge_status`
call rejected that source drift. Asking the operator to run readiness manually
did not finish the intended connector workflow.

This change adds one explicit `check_task_readiness` tool to the existing
connector and admits the exact mainline task through its existing start,
normal-return, recovery and health tools. It does not add another service,
shell-command input, process restart API or privilege change.

## Behavior

Readiness invokes only the already adopted mainline `ready` D0 CLI. It requires
the current authorized foreground task, the reviewed prepared task, no grant
or operation and no unresolved F1 dispatch/owner. It records its own bounded
process identity and durable dispatch before returning promptly. The original
readiness owner holds the target lease and produces the raw health evidence.
Status and logs only inspect existing state; they never initiate that read.
Running/uncertain calls do not spawn another child. A settled read may be
reobserved under the existing profile, preserving old evidence; a current
raw-validated readiness is reused.

Mainline start uses one reviewed common entry with fixed `start` and exact task
arguments. It requires the saved actual finite returned approval and attendance,
binds the connector dispatch, publishes an exclusive entry intent, and calls
the existing grant opener and Session. The prepared declaration is H0 data and
cannot replace approval. No operator-approval record was created by this work.

Normal continuation validates the original mainline observation/return record
and deadline. Recovery retains the original A and journal; a settled interrupted
mainline launcher with durable effects can recover even if the host cut prevented
a `stopped` row. An uncertain A still cannot repeat. Completed A permits only
remaining health. Older profiles retain their existing stopped-row conditions.

## Validation and activation boundary

All **70 focused connector/mainline and retained persistent-transport tests
passed**. They cover
explicit readiness versus passive status, real asynchronous fixture processes,
duplicate/uncertain dispatch, source-bound backend loading, absent approval,
fixed argv, readiness/F1 exclusion and mainline normal/recovery/health routing.
The real common entry was also exercised directly with device effects mocked:
exact dispatch joins, one grant-to-operation-to-execute sequence, exclusive
entry consumption and no second grant call after a grant-opening failure.
The exact existing task, proposal, current capability and preceding healthy
Android closure also reopened through the real mainline bundle consumer in H0.
Compilation, local links and scoped whitespace checks accompany the final
independent review and source snapshot in
`workspace/private/outputs/s22plus-mainline-connector-h0-20261028-1/`.

Independent review returned **PASS_GO** for 40 execution/authority sources,
with no remaining findings. Immutable review v10 is selected; v1–v9 remain
unchanged. The current `bridge_status` call reaches the existing resident and
returns `stable transport itself changed; use the newly reviewed worker on
next startup`. Thus source verification has passed, but the loaded worker
and MCP tool listing still require the protocol refresh described below.

The existing loaded worker's seven-name allowlist cannot accept the new eighth
tool. This is a real protocol change, requiring one ordinary worker startup
and MCP reconnection after review. The current worker was not killed, replaced
or silently reloaded. Later changes confined to backend/task sources retain
the normal reviewed-selector update path without worker restart. Historical
v1–v9 bindings and consumed requests remain unchanged.

The unrelated general workspace connector rejected the named script under its
safe-command allowlist; no alternate encoding, permission setting or broad
execution mode was used. No device command, grant, transfer or other-target
action occurred in this connector completion work. Physical mainline boot/USB
and automatic recovery remain unproved.
