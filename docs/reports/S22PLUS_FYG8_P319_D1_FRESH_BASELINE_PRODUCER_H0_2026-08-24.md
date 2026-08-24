# S22+ FYG8 P3.19 D1 fresh-baseline producer H0

Date: 2026-08-24 KST

Status: `PASS_GO_P319_D1_FRESH_BASELINE_H0_CAPABILITY_V1`

This host-only unit implements the D1 half of the future fresh-baseline
producer. It does not create an approval, arm, run, D0 result, normalized
fresh-baseline result, ready/run manifest or device authority. The execution
binding records the completed independent review, but that capability review
is not a current operator approval; no test invokes ADB, USB, Odin or a device.

## D1 execution closure

The 48,354-byte D1 source has SHA-256
`e0fa9d40e58e2ab372fa3f89005b51a33e17aeb47c21c2b42cdb0bbe35edad55`.
Its 4,128-byte canonical execution binding has SHA-256
`d92e7e463e26f1fae4f9a5515e00feb0c09fb2d83930839e89c391b58931fb4e`.
The binding pins the exact target/profile, current intent and qualification,
437-source/73-module/EUD38/latch-only closure, reviewed P2.96 primitive,
reviewed P3.18 wrapper, current D0 runtime, reference target/health D0 and
exact host ADB bytes. It contains no active candidate AP digest or live run
pair.

The exact future approval form is the fixed prefix
`DEVICE-ACTION-D1-P319-FRESH-BASELINE-V1-APPROVE:` followed by that full
binding SHA-256. Recording the format and capability `PASS_GO` does not issue,
collect or satisfy a current operator approval.

The reviewed P2.96 state machine remains the one-reboot owner. The adapter
publishes the fixed arm before constructing a device transport, snapshots the
exact ADB executable, pins the verified profile object, requires stable serial
and topology while allowing transport-id drift, and permits zero commands to
other targets. Arm/start/result and caught post-arm cuts use fixed no-clobber
names. A partial arm remains consumed and is represented by a typed stop; an
absent pre-intent arm produces no stop. Stop validation reopens the exact
namespace and rejects forged presence booleans, indirect nodes, hardlinks,
special files and mismatched complete arm/start/result schemas.

The P3.18 wrapper is not imported by reopening its path. The exact 30,648-byte
payload read and bound by input validation is retained, compiled and executed
directly with fixed `__file__`/package metadata. The original path is stable
reopened immediately after import and again after the one-reboot primitive
returns. Replacing the path after the initial read neither executes replacement
bytes nor survives the post-import/post-run identity checks.

The reducer is 48,596 bytes with SHA-256
`310f9670f130da47ad48191f12504f79dab8830efeb04700c6e7f1af02badde1`.
Its source identity is checked before import. The initially pinned module
object is reused for success validation, while post-run reducer/profile/ADB
drift is rejected without importing changed bytes.

## Permanent raw-first registration

The D1 source is not claimed as a migrated D0/F1 observer. It is registered as
one `D1` `byte-frozen-global-acquisition-detector-member` under the permanent
raw-first audit, with independent review required. Active raw-capture and
detector semantics are unchanged.

The current auditor is 63,258 bytes with SHA-256
`06ccabe3d39d4cd9b5d78c69483440f4effb1dd657b6eec4d836b29afc4051ae`
and normalized self-hash
`a965d866fc7cc2333a295b0e8c8949c0cf884445e0f47d9b5c319cbec3c34a03`.
The S22 pre-boundary inventory is now 128 entries at
`fcb3bb805ccbadb7277ecf4922ebd0d9c603f44204a9a0889162fceafb68bf95`;
target-external membership remains 52. A one-byte D1 mutation, renamed copy or
new acquiring source remains fail-closed.

The no-clobber successor receipt is
`raw-first-observer-audit-20260824-02-p319-d1-import-pin.json`, 11,285
bytes, SHA-256
`ff1cab6460e644aa2fcd2dcd38202d2ab66ab347e5c97e50194027a1a2cb9eba`,
mode `0400`, link count one. The 11,285-byte `20260824-01` receipt at
`b56ef0463fec122b72b522824ce2eda89e653e9ca39ee69810ab87398c9921aa`,
the 11,012-byte `20260823-04` receipt and every earlier receipt
remain byte-preserved.

The prerequisite auditor is 45,260 bytes at SHA-256
`39d3567b9ace6e91c6b541e3f78ae5c3c65fa7f0ebb908f6e97e30c9f2ae92cb`.
Its new no-clobber successor receipt
`process-v2-prerequisite-audit-20260824-02.json` is 12,530 bytes at SHA-256
`26c8eb9d0b17c00bf57841ce56c748704eaa2dadbeabb871576c3258946f40d2`,
mode `0400`, link count one. It consumes the exact new auditor and raw receipt;
the 12,534-byte `20260824-01` receipt at
`e7ff447886082aca3dc59e7da93d38ea511ad00a30e35eb065b500aeca4b9a1c`
and the `20260823-03` predecessor remain unchanged.

## Boundary and review

The D0 producer is still an immediate-failure stub. The normalized reducer
continues to set `producer_execution_closure_reviewed=false` and
`producer_execution_closure_authoritative=false`; integration remains
`BLOCKED_P319_PROCESS_V2_INTEGRATION_H0` on `FRESH_BASELINE_MISSING`. No
candidate byte, common Process-v2 contract, target contract, recovery path or
A90/S20+ state changed.

Validation on the final tree is: D1/fresh reducer `39/39`, integration
qualification `14/14`, raw-first auditor `21/21`, raw-first docs `18/18`,
prerequisite `9/9`, integration docs `8/8`, taxonomy `39/39`, and common
Process-v2 `142/142`. The broad P3.19 selection is exactly 626 tests: 625
passed, zero failed, and one error because
`/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko` is unavailable.
That unavailable external input is not reported as a pass.

Independent changed-closure review has completed and resolves only topic 40.
This capability `PASS_GO` and its raw registration grant no current approval,
D0, D1, F1, recovery, replay, causal result, candidate success, device or live
authority.
