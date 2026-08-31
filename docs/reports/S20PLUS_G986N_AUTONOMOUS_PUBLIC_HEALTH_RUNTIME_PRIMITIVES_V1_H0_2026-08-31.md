# S20+ autonomous public-health runtime primitives v1 H0 qualification

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **PASS_GO_NOT_ACTIVE — exact inactive runtime-primitives source only**

## Objective and scope

Qualify the host-side primitives needed by a future no-input campaign executor:
an exact held ADB client, ADB-server continuity owner, bounded host-clock owner,
USB-generation owner, bounded direct-child capture, and a process-local
opening-to-read state object.

This is not the executor. The supported public entry checks all operational
gates before observation and then reaches only an unimplemented stub; its CLI
only renders a plan. No raw journal writer, attended-opening verifier,
terminal-continuity receipt, closed executor call graph, recovery integration,
cross-runner integration, mechanical activation, or live authority exists.

The exact source and test are:

- `workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_runtime_v1_h0.py`;
- `tests/test_s20plus_g986n_autonomous_public_health_runtime_v1_h0.py`.

## Exact reviewed identities

After the reviewed status and test-literal rotation:

- source: 85,645 bytes, SHA-256
  `f6644edc1f8eee80e6f9fc5e7623c96b8e58de23312e71607e51a4658d67652f`;
- source activation-normalized SHA-256
  `12b993c199a104c2c0f1bdb9706c179005292971428ef26317442e600eb89ac2`;
- test: 79,428 bytes, SHA-256
  `69b90ff55e3a4e7b48f346b9a452c1227dca345e6d334b4e443e6faeef53a403`.

The status is
`H0_AUTONOMOUS_PUBLIC_HEALTH_RUNTIME_PRIMITIVES_V1_PASS_GO_NOT_ACTIVE`.
Reverse substitution of only that status reproduced the reviewed 85,602-byte
candidate at SHA-256
`f931e068023835f341d31d661d2efb1ebdd592f8970f7633013b0c39ad14a662`.
The final test differs from the reviewed 79,442-byte test at SHA-256
`4d8c4ce7c8850c1c3ba77186f200d420594c17d84068bd4ea16fda9052ca56ad`
only by comparing the rendered status with the module status rather than the
temporary review-pending literal.

## Exact-file ADB client and child capture

The candidate pins the final Phase-A model and the host ADB binary by exact
path, size, and SHA-256. A held regular-file descriptor is hashed and fstat'd,
reopened through its canonical path before and after use, and proposed for
`execveat(AT_EMPTY_PATH)` rather than pathname or `/proc/self/fd` execution.
Caller-selected path, argv, environment, timeout, serial source, shell,
callback, or backend is not a public CLI input.

The direct-child capture model fixes the six-command timeouts at
10/10/10/20/20/10 seconds and the combined stdout/stderr ceiling at 64 KiB.
Child write ends remain blocking while only parent read ends become
nonblocking. The child duplicates the exact executable safely to fd 3 and
uses Linux `close_range(4, UINT_MAX)` so a lowered soft `RLIMIT_NOFILE` cannot
leak a higher inheritable descriptor. Parent-death signal setup, pidfd
signaling, one exact direct-child reap, TERM-to-KILL cleanup, allocation and
selector failure cuts, and complete descriptor closure are modeled and tested.

After direct-child completion, pipe draining is bounded to 250 ms. A first
child completion observed at or after the command deadline is a timeout even
if its status is zero. A pipe EOF observed at or after the drain deadline is a
mandatory non-success. Both checks use BOOTTIME sampled after the relevant
`waitpid` or select/read boundary; retained raw-capture integration remains a
future executor responsibility.

## ADB-server boundary

The server owner requires one preexisting IPv4 loopback listener at the fixed
ADB socket and binds its socket inode, exact current-UID PID and start ticks,
pidfd liveness, and held executable inode/bytes to the held client generation.
It rechecks those axes around future use. `/proc/net/tcp`, PID, fd-link, and
aggregate probe counts are bounded.

This detects a server death or replacement but does not prevent the ADB client
from trying to autostart a server in the race after the check. Autostart policy
is false, `autostart_prevention_implemented` is false, and the missing reviewed
no-autostart transport is an explicit activation blocker.

## Clock, USB, and process-local state

The clock owner binds a process-local host boot identity plus REALTIME,
BOOTTIME, and MONOTONIC observations. It models a 300-second opening window,
30-second handoff, 600-second owner lifetime, five-second realtime projection
skew, and one-millisecond non-atomic cross-axis sampling tolerance. Reboot,
reversal, expiry, and excess skew stop.

The USB owner opens a loss-detecting kernel uevent monitor before selection,
then binds the deepest exact USB topology to held sysfs and usbfs descriptors.
It verifies bus/device numbers, Linux usbfs major/minor mapping, node types and
identities, canonical reopens, monitor liveness, and relevant-event absence.
Sysfs, netlink packet/event/byte/field, and monitor overflow bounds fail closed;
setup and partial-bind exceptions close their owned resources.

The opening-to-read object requires exact live owners from one environment and
one ADB generation, the same process and actual thread object, and a paired
pipe identity with exact read/write access modes. It is one-shot,
nonserializable, noncopyable, and not reconstructible from durable bytes.
Python visibility is explicitly not an authority boundary: its factory and
concrete host-observer helpers are import-reachable H0 fixtures, not permission
to invoke them. Only a future reviewed closed no-input executor may own their
construction and command transition.

## Validation and review

Focused stdlib validation passed 64/64. The eleven-suite autonomous H0
aggregate including this source passed 405 tests. `py_compile`, render-only
CLI, self-normalization and logic-mutation checks, real safe-child FD/pipe
tests, fake failure-cut matrices, and scoped whitespace checks passed.

Hostile review proceeded through four `NO_GO` revisions. It found and retired:
unbounded descendant-held pipes, incomplete child cleanup, nonblocking child
writes, unbounded observer enumerations, USB resource leaks and topology/rdev
gaps, weak process/FD/owner generation, soft-RLIMIT FD leakage, mixed ADB
generations, and pre-wait/pre-select deadline timestamp races. Final exact-byte
and status-rotation reviews returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.

## Dormant boundary and next unit

All 14 review, exact-binding, execution, handoff, target/cross-code,
contract, mechanical, and live gates remain false. The plan reports no device
commands, writes, root commands, Odin invocations, or partition transfers.
The concrete observers are internal/importable source primitives, but no
supported public entry reaches them and this qualification grants no D0 or
connected authority.

This unit ran no ADB, USB device, `su`, root, device-network, reboot, Download,
Odin, payload, partition, private-state, or live-evidence action.

Before activation, a separate executor must prevent ADB autostart, close the
construction call graph, retain raw command evidence before interpretation,
publish recoverable receipt-06 clock/server/USB continuity, integrate the
qualified start interlock and recovery grammar, bind exact private bundle and
activation identities, and pass combined independent review. A fresh
post-activation exact-target/current-boot attended opening remains required.
