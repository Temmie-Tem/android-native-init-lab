# S22+ persistent approved terminal transport V1

Status: **H0 capability; startup requires its matching independent PASS_GO;
no device authority**. This is a host transport for the selected
S22+ contract and its existing exact approved tasks; A90 and S20+ are excluded.

## Stable connection and fresh task code

The ordinary-terminal worker remains unprivileged uid/euid 1000, NoNewPrivs=0,
with the same mode-0700 runtime directory, mode-0600 same-UID Unix socket and
exclusive worker lock. No service, setuid helper, polkit/sandbox change, TCP
listener, live module reload or restart API is added. The six fixed MCP tool
names and argument shapes remain stable. The worker has no device descriptor.

The stable transport imports only Python's standard library. Each request
starts one fixed repository backend with a fixed Python executable, a fresh
process session, closed inherited descriptors and one bounded JSON stdin frame.
It never accepts an executable, shell command, arbitrary operation or approval
text from the caller. It reads one bounded response frame, not process EOF.
Timeout, disconnect or a missing reply means uncertainty and never cancels,
kills or retries an entry. A background waiter only reaps the backend process;
process exit is not device health or closure.

Before starting the backend, the worker verifies every source in the selected
independent review, including imported helpers. A fixed declarative selector
names only an immutable versioned review receipt under the repository binding
directory. It cannot change the backend executable or repository root. The
review must be PASS_GO, have no findings, include the fixed backend, transport
and this policy, and bind their current bytes. Its stable worker-source subset
is exactly the transport and this invariant policy. Each request requires that
subset to equal the worker's originally loaded subset. Backend and task-source
changes with a new independent review therefore need no worker restart.
Transport or API changes themselves may require a later normal startup; this
is not a promise that arbitrary changes to running code require no restart.

The fresh child rechecks the exact selected immutable review and current
selector before task admission. A selection/source update race fails closed.
It then uses the existing approved-task bundle and original execution owner.
Every dispatch intent pins that immutable backend review. Historical review
files and consumed intents are never overwritten when the selector advances.
Review capability is not operator approval or a new research budget.

Each launch uses a newly created empty private Python cache prefix and disables
bytecode writes before repository imports. Disabling writes alone would still
read an older timestamp-cached module. Fixed interpreter options establish the
fresh namespace for the backend, and inherited Python environment settings
carry it into the original entry's Python descendants. Shared caches are never
deleted. The reaper removes only its own empty directory after the backend
finishes; disconnect may leave an empty private directory, never replay rights.

## Admission and result ownership

Fresh backend processes share one fixed private admission flock, also guarded
against concurrent threads. It covers current checks, durable dispatch intent
and process spawn, and is released before waiting for completion. This retains
the original cross-task exclusion formerly provided by the resident's thread
lock. The original target-session lease and F1 owner remain independent and
continue to govern device effects. Lock contention rejects before admission;
it neither renews a budget nor makes a failed request retryable after intent.

The backend keeps the existing one-shot dispatch, normal automatic-boot return
and raw-proved post-A health semantics. Start requires the saved actual human
approval and unchanged reviewed task/entry. Normal continuation requires the
existing automatic-boot ready record and original live window. Health
continuation requires a unique raw-proved completed original-A transfer and
uses only the original existing-A recovery branch. No general recovery, new
grant, native control replay or uncertain transfer replay is exposed.

After dispatch the backend flushes exactly one bounded response and closes its
RPC stdout. A non-daemon result waiter remains until the original entry exits
and publishes its bound result. The child entry and backend result owner
survive client/resident disconnect; neither holds the admission or worker lock
while waiting. A broken response pipe does not abandon the result waiter.
A missing result or uncertain dispatch retains the existing no-replay stop;
only the original task's proved healthy closure resolves it.

These lifetime and admission rules address duplicate dispatch, stale imported
code and lost result ownership. They apply to this transport until the original
owner closes each task, and require independent review when transport, admission,
review selection, transfer or recovery semantics change. They add no device
permission ceremony. Attendance and required physical Download actions remain
those of the original task contract.

## Deployment

The existing `s22plus_approved_terminal_v1.py` worker and its review remain
byte-identical and usable during H0 development. Do not request another restart
merely to qualify this successor. At a later normal startup, select:

```sh
python3 /home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/host_tools/s22plus_approved_terminal_persistent_v1.py serve
```

Its MCP registration uses the same script with `mcp`. A fresh MCP connection
loads the stable six-tool schema. Future candidate changes and reviewed backend
updates use that connection without another worker restart. Verify the exact
selected backend review and `fresh_backend_per_request` through status before
future authorized use. Existing P456 is closed and must never be dispatched or
continued again.
