# S22+ completed-restoration USB arrival H0 repair

Status: **implementation, H0 validation and independent PASS_GO complete.**
Target: SM-S906N / g0q / S906NKSS7FYG8. This is the separate host-arrival unit
from the [phase-1 plan](../plans/S22PLUS_FYG8_REFACTOR_PHASE1_PREPARATION_2026-09-10.md).
No device effect, new candidate, AP, READY manifest, activation or replay occurs.

## Failure and bounded repair

The [consumed P383 record](S22PLUS_FYG8_NATIVE_BASELINE_ROUNDTRIP_H0_2026-09-10.md#attended-attempt-and-final-android-health)
retains completed exceptional native restoration followed by an empty child
snapshot history and a sequence0 membership-change diagnostic. The removed
usbfs path matches the restoration's exact Download receipt. This shape is
compatible with normal post-transfer departure during the first inventory, but
the historical record remains NO_PROOF for second kernel/PID1/console progress.

The old absence observer derived an expected departure only from an earlier
snapshot in the same directory. The restored arrival intentionally owns a new
directory and lease, so no such snapshot existed. The repair derives the first
comparison's path and immutable identity from the existing completed-restoration
context. It reopens and validates the parent claim/owner/original host-boot/time
window, first health/return, exact restoration intent, delivery marker, completed
transfer raw evidence, and exact Download topology/ticket receipts.

The backend supplies that pair only for the declared restoration child. The
core accepts the initial context only for a measured observer with empty
history and sequence0 under its own valid lease. It compares a still-present
baseline node with the bound immutable identity before enumeration. An already
absent node follows ordinary complete-absence observation; no timed departure
event is invented. No parent snapshot, generation, ticket or lease is copied.

When Odin's list is empty and the before/after inventory removes exactly the
bound path, the existing measured path can publish the child's first complete
absence snapshot. Additional arrival/removal, wrong identity/path, incomplete
inventory and I/O failures retain rejection and raw diagnostics. This is one
enumeration, without a catch-all retry or transfer replay.

The related exact-departure helper previously compared the remaining after
inventory with itself. It now compares baseline-minus-removed-node against the
actual after inventory, so another node's inode/immutable-identity replacement
cannot be hidden by the expected removal. Existing timestamp-aware identity
rules, post-publication revalidation and raw-capture bounds remain in place.

## Validation and review

The changed producer/consumer suites passed **120 tests in 38.982 seconds**:
usbfs identity, Odin transition core and P383 lifecycle. The updated lifecycle
fixture keeps the exact endpoint present until Odin enumeration starts, then
removes it between measured inventories. The actual restored-child path emits
one sequence0 absence receipt, reaches second authenticated health and closes
through the existing three-role owner. This is H0 fixture evidence, not another
P383 device run. The already-absent case also passes.

Negative cases reject missing/wrong initial context, path reuse with changed
identity, reused sequence, unrelated addition/removal and replacement of a
remaining node. Parent/binding/intent/delivery/completed-result/raw-topology
corruptions are rejected by the actual owner readers. Existing lease, incomplete
inventory, raw failure, publication-cut and recovery/no-replay cases remain in
the passing suites. Fixture edits replace only disposable temporary test files.

The unchanged generic live-owner suite passed **77 tests in 28.490 seconds**;
total parent validation is **197 tests**. Touched Python compilation, whitespace
and repository boundary checks pass. No native C or artifact build changed.

Independent reviewer `p352_usb_review` returned **PASS_GO** for all six changed
files after source inspection and an independent 46-test usbfs/P383 lifecycle
run (41.950 seconds). It verified child ownership, exact context derivation,
measured first-inventory timing, remaining-node rejection and no role replay.

| Changed source | SHA-256 |
| --- | --- |
| `device_action_f1_live_v2.py` | `386b0f14d9933fd3c81ed608939124dadb9b39220f9ab4fc79a2d4c58adb74de` |
| `s22plus_native_roundtrip_owner_v1.py` | `92508b84d71263aa7eb6f51ac336c686e612566392b28feabc2cab50818f7b6f` |
| `s22plus_odin_transition_core.py` | `26a5a5a446987a21165622d1e79b98505c720fea2f1460d3e05af175a62c0bf7` |
| `s22plus_odin_usbfs_identity.py` | `9266f0a4a0f10dcd4f8a7b55fa2d2079afd2a1480e310ab6667f6bf2cf491451` |
| `test_s22plus_fyg8_p383_lifecycle.py` | `ac28bc59bb4efbfb8b352110825c5673670e75f25216a42d5505ef15e0eb97b3` |
| `test_s22plus_odin_usbfs_identity.py` | `5491e5008d7e435d73f4dfe2c593910f190f0fd44da9c6243037fa3527937ace` |

Current execution-critical sources intentionally differ from consumed P383
bindings. Historical prepared closures, approvals, claims, journals, results and
their source pins remain unchanged. Future use requires a fresh applicable
binding; this review grants no new effect and cannot reopen the consumed first
roundtrip exception. The transient ADB-offline cause and historical second-boot
progress remain unknown. Local-display observation is a separately reviewed H0
unit; A90 and S20+ device work is outside this change.
