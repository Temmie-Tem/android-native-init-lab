# S22+ FYG8 P3.19 D1 fresh-baseline raw-first V2 H0 successor

Date: 2026-08-24 KST

Status: `PASS_GO_P319_D1_FRESH_BASELINE_RAW_FIRST_V2_H0_CAPABILITY_V1`

This is a host-only successor to the consumed `d1-fresh-baseline-1` action.
It creates no approval, arm, run, device command or live authority. The V1
arm, stop, binding and source remain byte-preserved and the V1 ordinal remains
consumed without replay.

## Source-localized cause evidence

A zero-device fixture executes the exact reviewed P2.96/P3.18/V1/current-D0
closure. The inherited P2.96 inventory method reaches `d0.bounded_command`
once and produces no immutable raw handle. With a successful fixture inventory
substituted, P3.18 `select_exact()` next calls the current D0 client's
`topology()`, which fails exactly with `D0Error: ADB raw-first capture is not
bound`; the fixture executes zero device commands on that topology path.

This mechanically reproduces the source path that strongly localizes the V1
failure. It does not rewrite the incident receipt. The consumed stop retained
only `D0Error`, so its append-only classification remains
`HEALTH_PENDING / NO_PROOF_OBSERVER`; the original evidence still cannot by
itself distinguish every possible inventory, topology, health or client-read
cause.

## Versioned successor

The corrected V2 source is 66,357 bytes at SHA-256
`9443c81cd51e23a24f48a0f43573e1449cfa188b3cd1c69e6f6f11644d15d478`.
It uses the new fixed ordinal `d1-fresh-baseline-2` under
`workspace/private/runs/device-action-d1-p319-fresh-baseline-v2/`; neither the
V1 run nor its approval form is accepted. The committed 5,300-byte
review-pending execution binding at SHA-256
`917daa0257fda4b6bd784bf303ef9226b744ba0ce458e1bbfc4b7a48721cef8f`
is the preserved predecessor. Independent review promotes only its review
tuple; the final 5,351-byte canonical binding is SHA-256
`65e2953ecdcb55a0b5b21614e181c7ed8fe4daafaadda5e7319ae142ad9fbae9`
with verdict
`PASS_GO_P319_D1_FRESH_BASELINE_RAW_FIRST_V2_H0_CAPABILITY_V1`.

The future authority form is the fixed prefix
`DEVICE-ACTION-D1-P319-FRESH-BASELINE-V2-APPROVE:` followed by the complete
final binding digest. This records a format only: no token was issued or
supplied. Capability review is not current operator approval.

After a future exact operator approval, the fixed durable arm would precede
the ADB snapshot, raw namespace and transport construction. The
transport binds `raw-adb/` before inventory, rejects a pre-populated namespace,
and routes inventory, topology, properties, root health, reboot command and
poll output through the byte-pinned common raw writer. Each parser receives
only a reopened immutable handle. A controlled full fixture proves one reboot,
zero other-target commands and a closed 14-handle/42-child raw namespace; it
has no device effect.

The target serial is bound to the exact retained S22 reference, topology is
measured on the first selection and held across the action, and transport-id
drift alone is excluded from the stable inventory digest. No payload, Odin,
Download transition, F1 or command to another target exists.

## Failure preservation

The fixed stop schema uses allowlisted `failure_site`/`failure_code` pairs for
raw-capture binding, inventory read/format/cardinality/state, serial, topology,
properties, root health, USB, health validation, start publication, reboot,
poll inventory, returned health, namespace publication and an unclassified internal
bucket. Raw exception text and private identifiers are never copied into
tracked artifacts.

The reviewed P2.96 return-poll behavior is preserved. A finalized raw handle
whose early post-reboot property read fails is retained as
connected-but-not-ready and the bounded poll continues. A later healthy read
completes the same one-reboot attempt; persistent failures terminate once as
`RETURN_HEALTH` and never dispatch a second reboot.

Every direct raw child is mode `0400`, single-link, stably reopened and claimed
by exactly one canonical capture receipt. The stop binds the ordered handles,
all children and an aggregate digest; symlinks, hardlinks, special nodes,
unexpected children, replacement and drift fail closed. Partial regular arm or
start publication created by this invocation is represented separately from
complete bytes. A pre-existing exact arm, prior successful start/result/raw
namespace, or concurrent O_EXCL duplicate is not owned by the new invocation
and is rejected without adding a stop or changing any byte. Reboot
dispatch is only possible after a complete durable start, and every caught
post-arm stop is non-reusable with replay false.

## Permanent raw-first registration

V1 remains one byte-frozen pre-boundary D1 detector member. V2 is separately
registered as the 17th active raw-first source because its actual transport
binds the common raw namespace and reopens immutable handles; it is not an
exception or a relaxation. The current auditor is 66,941 bytes at SHA-256
`86a0fc328538c5a39470dca2272957a4ac7453a48a7f629feebfb7edbddfd3d2`
with normalized self-hash
`139838505b937c8634c21db652d1d50adaf45bfaf65d2b8359743f2aaedcbe28`.
The all-file/subprocess census is `1740/412`; pre-boundary S22 membership stays
`128/fcb3bb80`, and target-external membership stays 52.

The no-clobber raw successor
`raw-first-observer-audit-20260824-05-p319-d1-v2-no-replay.json` is 12,394
bytes at SHA-256
`2d5fc0428f6683ce9a7ac056c6da6b92c4decad45b7fd7430febf2edbd1325e9`,
mode `0400`, link count one. The `-04` receipt remains 12,268 bytes at
`38ba4f9b`, the `-03` receipt remains 11,792 bytes at `9c5d892c`, and all older
receipts are byte-preserved.

The minimally repinned prerequisite auditor is 45,262 bytes at SHA-256
`08654b354da110c21fb0ec4e672505e3f57db253b74c0e9da4535d9109633481`.
Its no-clobber `process-v2-prerequisite-audit-20260824-05.json` receipt is
12,532 bytes at SHA-256
`5ea7fd30aabc99041ce64e1b1e9c50f6cea181dc7f73d251d5cbdc396624fb4a`,
mode `0400`, link count one. The `-04`, `-03` and all earlier prerequisite receipts
remain unchanged.

## Validation and boundaries

The combined V1/V2/reducer/integration selection passes `81/81`; its V2
cause/producer/hostile subset is `28/28`. Permanent raw-first tests pass
`24/24`, raw-first docs `19/19`, prerequisite `9/9`, integration docs `8/8`,
taxonomy `39/39`, consumed-stop evidence `4/4`, and common Process-v2
`142/142`. The broad P3.19 selection is exactly 688: 687 passed, zero failed,
and one known unavailable-input error because
`/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko` is absent; it
is not reported as a pass. The V2 source and tests compile, and
`git diff --check` is clean.

Independent changed-closure review passed for implementation commit
`694ad3ad53` and the exact source closure; the separate review report records
its scope. No current operator approval exists, and the consumed V1 run cannot
be retried. The reviewed D0 producer/reducer remains pinned to the V1 result
and binding and still requires a separate exact V2 consumer repin before any
D0 request. No D1 result or D0 baseline exists, so
integration remains blocked on `FRESH_BASELINE_MISSING`. This unit creates no ready/run/public
candidate manifest, D0, D1, F1, recovery, replay, causal-result,
candidate-success, device, ADB, USB, Odin or live authority.
