# S22+ persistent terminal transport — H0, 2026-10-24

## Problem and design

The operator intended to start the terminal connector once and keep using it.
Initial launch and return support were added in separate revisions, each of
which required replacing the already imported worker. Its loaded review also
included changing task/owner sources, unnecessarily coupling backend updates
to the lifetime of the connection.

The successor separates a standard-library-only resident transport from a
fresh reviewed backend for each request. The six tool names stay fixed. A new
independent backend review can be selected without restarting that resident
when the transport and its invariant policy have not changed. Actual changes
to the resident/API may still require a later normal startup.

The existing running worker, policy and d545 review are untouched and remain
connected. This change is qualified separately and requires no immediate
worker or app restart. The persistent worker is selected at the next normal
startup. Its compatible MCP transport is selected as the registered `mcp` script for
the next connection. Only that script argument changed; every other parsed
configuration field is preserved. The currently running listener was not
terminated or restarted.

## Boundaries retained

The resident hash-checks the complete selected source closure before starting
the fixed backend process. A declarative selector names an immutable versioned
review, never an executable. The child checks the same receipt and current
selector again before admission. Historical reviews remain readable after an
update, and each dispatch records its exact immutable review.

The extracted controller keeps current approval/task/entry/source checks,
exclusive durable dispatch records and the original start/return/health paths.
A shared private admission flock replaces the process-local-only lock so fresh
backends cannot both admit different tasks. It is released before waiting for
task completion; the original target lease and F1 owner remain separate.

The child flushes one bounded response and closes RPC stdout while a non-daemon
thread retains result-publication ownership. Both the original entry and its
backend survive loss of the resident or client. A missing reply, timeout or
process exit never authorizes cancellation, replay or a new image. No shell,
new device lane, grant, daemon service, privilege change or live module reload
is introduced. The original worker's launch environment remains required.

## Validation

Private evidence is under
`workspace/private/outputs/s22plus-approved-terminal-persistent-h0-20261024-1/`.

- Twenty-nine tests pass: 15 existing continuation cases against the extracted
  backend and 14 persistent-transport/admission cases. Real subprocess fixtures
  prove an updated reviewed backend is used through the same resident, immutable
  old review receipts survive, one response arrives before task completion,
  broken pipes/resident exit preserve the result owner, and concurrent fresh
  backends cannot admit two tasks. Changed helpers, changed resident policy,
  invalid selector and parent/child review races reject before dispatch.
- The harmless copied backend fixtures retain the caller's NNP value without
  changing privileges. A separate test explicitly sets NNP=1 in a child and
  confirms the production backend rejects that restricted identity before review.
- Original continuation behavior includes raw-proved A-only health, owner and
  target-lease exclusion, existing grant/ready limits, changed approvals/sources,
  and duplicate/uncertain dispatch rejection. No physical entry is tested.
- Current-worker source/policy/review and P456 evidence are preserved. Actual
  live `bridge_status` still reports the reviewed d545 worker as connected; no
  request to restart it was made for this successor.

Independent review reproduced stale timestamp bytecode after a same-size,
same-second source update. The resident now creates a fresh empty private
Python cache prefix, disables bytecode writes before imports, and passes the
same settings to the original entry descendants. A regression demonstrates
that the new reviewed helper is executed while its old shared cache remains
untouched. Only the request's own empty directory is removed on normal backend
exit; no shared cache is deleted.

Independent final review is **PASS_GO**, with no open findings; the stale
bytecode finding is closed. It binds the 14-source backend closure and its
two-source stable resident subset. The original selector and backend consumers
pass the published immutable review, and both continuation paths reject the
actual closed P456 task without process creation. The public
selector contains only that immutable receipt. The current task, P456, remains
`ANDROID_CLOSED_HEALTHY`; no new device effect, approval or grant is created.

## Use and remaining deployment

On the next ordinary startup, use the persistent script's `serve` command in
[its contract](../operations/S22PLUS_APPROVED_TERMINAL_PERSISTENT_V1.md).
The existing listener remains usable until then. New task candidates and
reviewed backend updates are handled through fresh processes after that
one-time transition. A90 and S20+ remain untouched.
