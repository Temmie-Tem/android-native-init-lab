# A90 H13 rootfs transfer socket-timeout incident

Date: 2026-08-10
Target: Samsung Galaxy A90 5G only
Classification: F1 staging incident before candidate intent

## Incident

The attended run08 F1 transaction entered absent-only rootfs staging and
durably recorded `payload-transfer-start`. The host connected to the A90
receiver and transferred part of the 2 GiB rootfs, then `sock.sendall()` raised
`TimeoutError`. Cleanup commands were sent through the serial bridge while the
foreground receiver was still active, so they queued behind it and the control
channel stopped producing framed replies.

The transaction closed `ABORTED_F1_V2_BEFORE_CANDIDATE`. Candidate intent was
never recorded; candidate and rollback boot transfer counts were both zero.
There was no boot flash or reboot by the runner, and run08 is terminal and not
eligible for retry or reuse.

## Cause

`tcpctl_host.py` created the payload socket with the 10-second connection
timeout and left that timeout installed for the complete data send. The
1200-second transfer timeout governed only the later receiver-thread join.
Normal SD write backpressure lasting more than 10 seconds therefore aborted a
valid long transfer.

The exception path then attempted remote unlink before it had cancelled and
obtained terminal acknowledgement from the foreground `netcat`/`dd` receiver.
The staging parent repeated a remote cleanup attempt after the child failed,
which extended the channel blockage instead of proving cleanup.

## Recovery evidence

The operator physically rebooted the A90. Fresh exact-target read-only checks
then proved the installed H11 `0.11.179` resident, self-test `11/1/0`, native
SD mount read-write, and responsive serial/TCP control. A CPU snapshot was
96.9 percent idle; the failed `netcat`/`dd` receiver was absent.

The run08 final rootfs and shared work path were absent. The exact run08 stage
directory remained with one 486,818,512-byte partial temporary regular file;
the published payload was absent. That residue remains preserved until a
separately represented exact cleanup action is selected. S22+ received no
command.

## Containment and correction

- File sending now replaces the connection timeout with the remaining time
  from one positive overall transfer deadline before every chunk.
- Both bridge and TCP-control install paths use the same deadline-bound sender.
- A bridge receiver keeps its owning socket and accepts one exact native `q`
  cancellation request after a send failure.
- Remote cleanup is allowed only after `[done] run`, `[err] run`, or `[busy]`
  terminal acknowledgement. Without acknowledgement, the child emits
  `A90_TRANSFER_RECEIVER_UNCONFIRMED` and skips cleanup.
- The staging parent recognizes that marker, and also treats a host subprocess
  timeout as receiver-unknown, so it does not queue a second cleanup command.
- Focused tests cover deadline replacement, successful chunk progress,
  cancel-before-cleanup ordering, unacknowledged cleanup suppression, and the
  staging marker gate.

## Safety judgment

The device is back at exact H11 resident health, and no boot candidate effect
occurred. The incident changes transfer and failure-recovery machinery, so the
prior H13 capability qualification is no longer reusable. A fresh independent
review of the named transfer closure is required before any successor staging
or F1 attempt. Any successor that retains the SD-staging lane must use a fresh
candidate identity, rootfs destination, run directory, D0 evidence, and live
binding. Reusing the already formatted UFS appliance root is a separate
host-design and target-contract unit; it does not authorize a run08 retry.
