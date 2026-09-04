# S22+ FYG8 P3.38 first-OPEN branch Process-v2 H0

Date: 2026-09-05
Target: `SM-S906N / g0q / S906NKSS7FYG8`
Tier: H0 only
Independent review: `PASS_GO_P338_H0`

## Result

P3.38 is a fresh boot-only diagnostic successor to the consumed P3.37
candidate. It preserves the P3.37 successful authenticated resident path,
three fixed commands, 300-second observation, exact Magisk rollback and final
health choreography. It changes only the first framed OPEN failure report.

The existing stage-3/type-`0x86` diagnostic code now identifies one of four
branches:

- `0`: header read returned an errno;
- `1`: header or complete OPEN validation failed;
- `2`: body read returned an errno;
- `3`: frame CRC validation failed.

The original read or validation return is preserved. The diagnostic write is
best effort. P3.38 adds no retry, second OPEN, extra wait, command, reconnect,
lease action, caller-selected shell, persistent state or global gate. A branch
receipt is diagnostic evidence only and cannot make the candidate successful.

## Exact host closure

- Run ID: `c338f1e0a90b5e6d7c8a9b0c1d2e3f2b`
- Builder result: `61618B/c23dd514f33946a030ea72cd35230dd804e21c6435d7808e3ebc8be661cbd2a4`
- Candidate AP A/B: `28631081B/2f6dc740d06e6b7aef65423ba167fa7ac641d6374583322206dd4a5259a6d2e8`
- Candidate-static: `38958B/f1c63d2376d90f32ee7c69ed174b802c2c09fb19964ad6cafde39667879beb91`
- Current ready manifest (`ready_3`): `10246B/44f192f27bc600a8cf3826075071228b6e15caeafc449b4c7bc7514e189e24d1`
- Exact rollback AP: `23367721B/d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`

Candidate A and B are byte-identical and contain only `boot.img.lz4`. P3.37
and earlier run identities and candidate APs are rejected. The private
promotion contains the exact candidate-static, run manifest and static check;
the tracked ready manifest remains preparation data, not F1 authority.

## Proportional baseline path

P3.38 does not add another D0/D1 wrapper pair. A fresh connected Process-v2 D0
may accept the retained P3.37 rollback baseline only when `/proc/last_kmsg` is
exactly `2097136B/64ac7a5b6666c4a21ce23effce2ec13015cdbdb985555300202ad46d8fe26a11`
and the P3.37 decoder reproduces the fixed predecessor record at offset
`1657825`, with no foreign record and no candidate success. This proves only
that the fresh P3.38 run is absent. If the fresh read differs, preparation
stops and a separately authorized attended D1 rotation is required; the
baseline rule is not widened.

## Validation

- P3.38 artifact/open-read/Process-v2 focused tests: 18/18 passed.
- P3.37 plus P3.32-P3.36 selected common regressions: 46/46 passed.
- Builder and candidate-static audit-only checks passed.
- Prepare audit-only and tracked ready-manifest verification passed.
- P335-P338 raw-first current-tree contracts and three focused mutation/
  receipt tests passed after the final common-source repin.
- Python compilation and `git diff --check` passed.
- Host-only work made no ADB, Odin, reboot, Download transition, transfer or
  partition action.

## Authority boundary

This H0 result does not authorize connected D0/D1, F1, recovery or replay.
P3.37 remains consumed. A live P3.38 campaign still needs fresh exact-target
D0 preparation, a new durable run, physical attendance and the exact one-use
F1 approval emitted for that prepared run. Success still requires the complete
intended authenticated proof, mandatory rollback and healthy exact-target
return.

## First D0 stop and host-only correction

The first connected preparation read the exact expected P3.37 rollback bytes,
`2097136B/64ac7a5b...`, and verified healthy rooted FYG8 Android, but stopped
0/0 at baseline classification. The target contract and constants named the
P3.38 exception, while `classify_clean_baseline()` had not registered its
dispatch branch. This was a host integration omission, not baseline drift and
not a reason to reboot the device.

Commit `21f338f418` adds only the missing P3.38 overlay branch. It requires the
exact raw identity and independently reopens the sole P3.37 record, run ID,
offset, valid slots, zero foreign count, no candidate success and
`NO_PROOF_OBSERVER`; a one-byte mutation is rejected. Independent narrow
review returned `PASS_GO_P338_D0_BASELINE_REPAIR_H0`. Commit `24553e0c80`
repins the raw-first inventory to this final source. `ready_2` supersedes
`ready_1` for new preparation. No D1, reboot, Download transition, Odin or
partition transfer occurred during the stop or correction.

The next fresh preparation proved the exact baseline repair: D0 returned
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY` with the same raw identity and
healthy rooted FYG8 state. Preparation then stopped before publishing
`prepared.json` because `_candidate_arrival_proof_role()`,
`_p324_lane_bundle()` and `_acm_primary_bundle()` ended their exact membership
sets at P3.37. Commit `09ba2854fd` adds only the P3.38 overlay/run to those
three sets and a direct ready-bundle dispatch test; independent review returned
`PASS_GO_P338_LIVE_MAPPING_REPAIR_H0`. Commit `713ce80058` repins the final
live source in the raw-first audit. `ready_3` supersedes `ready_2`. This second
stop also performed no D1, device write, reboot, Download transition, Odin or
partition transfer.

A third fresh preparation against `ready_3` completed. Exact-target D0 returned
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`, reopening the healthy rooted
FYG8 target, absent Download endpoint and reviewed P3.37 predecessor raw
baseline `2097136B/64ac7a5b`. It published mode-0400/link-1 preflight
`3261B/76ab20a3` and `prepared.json` `25187B/eb10244c` under
`p338-ready3-prepared-20260905-3`, with one-use approval digest `31fab860`.
No D1, write, reboot, Download request, Odin invocation, partition transfer or
F1 action occurred. This preparation authorizes nothing without the exact
fresh attended approval it emitted.

The first invocation of that approval closed before candidate intent. Fresh
execute preflight remained healthy, but observer guard arm returned 127 with
captured stdout `pkexec must be setuid root`. `/usr/bin/pkexec` itself was
root-owned mode 4755 on the normal root mount; the distinction was the Codex
executor's inherited `NoNewPrivs:1`, which prevents setuid elevation. The
four-record journal therefore closed `ABORTED` with
`candidate_observer_arm_failed_before_candidate`, candidate `not-attempted`,
rollback not attempted and `recovery_required=false`. Result is mode-0400/
link-1 `1351B/3fefd240`. No Download request, Odin invocation, transfer,
partition action or device write occurred, and the run/approval is not reused.

A new ordinary preparation run `p338-ready3-prepared-20260905-4` then passed
the unchanged exact D0 baseline and published preflight `3261B/3325358b` plus
mode-0400/link-1 `prepared.json` `25187B/36218e4d`. Its one-use approval digest
is `18c992d8`. D1 remained unnecessary. Live execution must use the operator's
normal terminal, where the host process does not inherit the Codex executor's
`NoNewPrivs` restriction.
