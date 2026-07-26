# S22+ FYG8 P2.72 E3 ready-manifest host pass

Date: 2026-07-26 KST

Scope: H0 host-only. No connected D0, approval, transaction, Odin session,
transfer, reboot, device contact, or device write occurred.

## Result

The P2.71-promoted E3 candidate now has one data-only Process v2 ready
manifest:

`workspace/public/src/device-action/manifests/s22plus_fyg8_p270_process_v2_ready_1.json`

The manifest binds:

- the exact reproducible boot-only candidate AP;
- the exact Magisk boot-only rollback AP from the target profile;
- the exact P2.60 candidate-static, run-manifest, and static-check contracts;
- the E2 terminal stage `0x90`;
- the versioned P2.60 decoder and source contract;
- the exact CDC-ACM observer derived from the candidate run ID;
- the FYG8 target and final-health profiles; and
- Process v2 runner `device-action-f1-v2-host-core-3`.

It contains no approval token, target continuity evidence, prepared binding,
journal, Download endpoint, or device-derived identifier.

## Validation

The unchanged reusable runner reopened the complete bundle with
`--validate`. It independently verified:

- candidate and rollback AP size and SHA256;
- exactly one regular candidate member named `boot.img.lz4`;
- candidate AP deterministic archive metadata;
- the typed E3 observation contract and terminal stage;
- the complete versioned execution-critical source closure;
- the E2 boot payload, effective rootfs, module order, and exact userspace;
- the source-derived CDC-ACM observer;
- the pinned executable Odin identity; and
- the FYG8 profile and exact rollback identity.

The durable private result is:

`workspace/private/outputs/s22plus_fyg8_p272_ready/host-preflight.json`

Its verdict is `PASS_DEVICE_ACTION_F1_V2_HOST_PREFLIGHT`. The validated bundle
hash is fixed by the tracked regression test. The result explicitly records
`device_contact=false`, `odin_invoked=false`, and `live_authorized=false`.

An independent test imports the common runner, reopens every bound artifact,
pins the exact bundle hash, checks the terminal and observer identities, and
asserts all three no-live-authority flags. It passes.

## Rejected draft

The first manifest draft inherited historical runner string
`device-action-f1-v2-host-core-1`. Current validation rejected it before any
device action with a runner-version mismatch. The manifest was corrected to
the current common runner `host-core-3`; no execution machinery changed.

## Meaning

`ready-for-f1-approval` is data readiness, not live authorization. This unit
does not establish current target health or continuity and does not authorize
Download entry, Odin, transfer, reboot, or F1.

The next bounded step is connected D0 using this immutable manifest. D0 must
reopen the same bundle and establish one exact healthy FYG8 target before any
fresh F1 approval can be considered.
