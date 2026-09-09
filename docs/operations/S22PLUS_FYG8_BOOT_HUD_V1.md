# S22+ FYG8 boot HUD with root console V1

P376 is a fresh, attended boot-only successor to consumed P375. This document
records a capability design; it creates no live grant. Ordinary Process-v2
review, exact candidate/rollback qualification, fresh connected preparation,
physical attendance and one finite approval remain required.

## Scope and ownership

After authenticated native console preparation, PID1 launches one separate
`/s22-display` HUD child. It displays NATIVE INIT, a parent PID1 snapshot,
monotonic uptime and the parent's current console READY/BUSY/BLOCKED snapshot.
The first version uses the existing exact 1080x2340 30HS DRM path, white bitmap
text on black, with no touch, menu, GPU submission, arbitrary renderer input,
standing console, child restart or reconnect. It is not an unauthenticated
standalone boot UI. A stale visible frame proves no current liveness.

PID1 remains the sole authenticated CDC owner. The HUD has its own PID/process
group and cannot inherit the console, auth-key or other parent descriptors.
A nonblocking AF_UNIX SOCK_SEQPACKET channel carries fixed 40-byte snapshots
with exact run, increasing sequence, monotonic uptime and console state.
MSG_NOSIGNAL avoids changing command-child signal semantics. A full channel
drops a snapshot; no backlog is retransmitted. The renderer drains bounded
queued snapshots before drawing the newest one. EOF, malformed/oversized input,
wrong run, stale sequence or a stale parent parks that child.

PID1 independently drains at most 512 diagnostic bytes per tick to an exclusively
created RAM log, bounded at 128 KiB, and reaps only the exact HUD PID with
WNOHANG. HUD start/exit, update publication, completed flip and console command
outcomes are different evidence. HUD faults never consume command-child status
or block STATUS, EXEC, CANCEL or CONTROL. CONTROL stops updates and signals the
still-owned HUD at most once; it does not await exit, DRM close or teardown
before the existing single Download request. A kernel/PID1 stall can still need
physical recovery. The original ten-minute console deadline is not renewed.

## Immutable frame lifecycle

The target synchronous commit returns without propagating every commit-wait
failure. Its return alone is not buffer-retirement proof. Each HUD commit also
requests one matched FLIP_COMPLETE event, with exact size/type/CRTC and unique
user_data, on the same open DRM descriptor. Exactly one commit is in flight;
preclose-generated events are never accepted. The selected display must exclude
other active encoder/CWB transitions that could complete that event first.
This exclusion combines fresh successful DRM module insertion (an already-loaded
module fails), sole HUD DRM ownership, no virtual/clone-output request, and the
other-active-encoder check; the encoder query alone is not that proof.

Each frame gets a fresh cached, non-imported GEM. It is fully painted before
its first scanout preparation/DMA mapping and never modified again. Both the
successful ioctl and the matching event are required before RMFB, munmap and
GEM_CLOSE retire the prior buffer. Successful retirement precedes the next
allocation, so at most two buffers are held. Commit, event or retirement
uncertainty parks with remaining resources; no retry, repaint, further
allocation or cleanup sequence occurs. Parent CONTROL remains independent.

## Acceptance and evidence

Host qualification must exercise actual AArch64 IPC/descriptor/process-group
semantics and the exact target UAPI, generated parent/console/renderer joins,
font bounds and long uptime, and deterministic DRM lifecycle faults. It must
show full/broken IPC, a parked child, diagnostic overflow, cancellation while
HUD runs, and one CONTROL without waiting for the HUD. Event mismatch, timeout
and cleanup failure must prevent subsequent allocation/reuse.

Live acceptance separately requires the inherited five root-console
qualifications, fresh HUD update evidence while commands execute, exact
Download, one rollback and final rooted Android/original-hash health. Physical
text and time changes remain operator observation; completed submissions alone
are not pixel proof. Supplemental stock evidence keeps its independent status.
All raw logs and private identifiers remain under `workspace/private/`.

Consumed predecessors, permanent partition/evidence boundaries and target
isolation remain unchanged. This new closure requires one independent review;
review is triggered again by changes to DRM completion/ownership, IPC framing,
rendering lifecycle, supervision, source binding or recovery behavior.
