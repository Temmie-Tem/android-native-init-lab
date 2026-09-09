# S22+ attended root console V1

Status: **H0 DESIGN / NOT ACTIVATED**. This document grants no device effect.
Target: SM-S906N/g0q/S906NKSS7FYG8 only.

The operator-directed console executes repeated BusyBox `sh -c` commands as
numeric UID/GID 0 in the native boot's real proc/sys/dev environment. Each command
starts a fresh child; RAM files persist in the same boot, while shell variables
and shell cwd do not. The host supplies an absolute cwd for each command. The
first version has no PTY or interactive stdin. There is no command allowlist or
per-command human approval. All permanent partition, persistent-mutation and
reboot boundaries remain binding on command use. A RAM cwd is not containment.

Before any candidate effect, the host seals one canonical optional command plan
into the prepared run. It contains at most 64 commands and binds each command's
exact bytes, absolute cwd and 1–300,000 ms timeout. Five fixed qualification
commands run first; plan commands run only if qualification passes. An empty
plan qualifies the console without adding operator work. The original ten-minute
native session deadline covers qualification, the plan and terminal CONTROL;
neither the plan nor a command can renew it.

PID1 retains one authenticated USB endpoint. Session nonce and strictly increasing
request sequences bind EXEC, STATUS, CANCEL and CONTROL. Command IDs are EXEC
sequence numbers. Responses authenticate their type, command ID, stream and output
ordinal. Output bytes never become supervisor lifecycle evidence. The trusted
operator/mistake-oriented threat model applies: HMAC is not hostile-root isolation.

One command may be active. Separate stdout/stderr pipes feed bounded output
frames without blocking PID1 on the child or host. A finite byte budget produces
an explicit truncation outcome; the two streams share a 1 MiB command budget.
At most 2,048 output frames may be emitted for one command, so short native reads
cannot exceed the declared wire budget through framing overhead. The complete
P375 observer stream has an 80 MiB raw bound, distinct from older consoles.
STATUS and CONTROL are processed independently
of command progress. ACK means acceptance, not successful exec or completion;
exec failure, exit/signal, timeout, cancellation and unresolved cleanup are distinct.
Cancellation signals the process group with TERM, then KILL, with nonblocking
reaping. It does not prove that escaped descendants or uninterruptible tasks
stopped. Unresolved cleanup closes command admission, while CONTROL remains usable.

Before each optional EXEC, the host reserves that command's full requested
timeout, ten seconds for cleanup/return, the maximum command wire bytes and the
CONTROL reply. If the remaining session or raw budget cannot cover them, the
unexecuted plan suffix is recorded and no further EXEC is sent. Complete setup,
command, timeout and cleanup-negative terminals remain exact individual outcomes;
known failure does not suppress the one terminal CONTROL. An unexecuted or
unresolved plan row keeps the run `NO_PROOF` even if fixed console qualification,
CONTROL, rollback and final health succeed.

The session has a finite native lifetime and command timeout. Expiry, malformed
authentication, transport loss or uncertain command delivery must never replay a
command, reopen the listener or renew the session. The host publishes private
command bytes and a durable intent before transmission. It retains bounded raw
wire evidence and one terminal result per command. A host crash leaves delivery
uncertain and requires journal-based recovery rather than retransmission.

Candidate qualification, authenticated CONTROL acceptance, actual Download arrival,
one boot rollback and final rooted Android health are separate results. Physical
recovery remains required; PID1/kernel stall recovery and unattended use are
unproved. Existing P349 restrictions and consumed P372-P374 paths remain intact.
Activation requires a distinct reviewed target capability and a fresh finite
attended grant bound to the new candidate, source closure and exact rollback.
