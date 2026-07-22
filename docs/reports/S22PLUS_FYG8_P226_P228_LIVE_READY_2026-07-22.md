# S22+ FYG8 P2.26-P2.28 live-ready preparation

Date: 2026-07-22 KST
Tier: H0 artifact construction plus D0 connected read-only preparation
Status: `PASS_P228_CONNECTED_PREPARED_F1_INACTIVE`
F1 authority: none

## Result

P2.26 constructed one deterministic boot-only candidate from the exact P2.25
Image using the previously qualified E0 ramdisk carrier. The independent
checker then reopened every layer and proved the kernel, boot, AP, static
`/init`, child, and no-ring-writer runtime closure.

P2.27 promoted that result into the existing typed same-ring Process v2
contract. P2.28 passed common-core host validation and connected read-only
preparation against one exact healthy FYG8 Android target. The prepared private
binding contains the fresh exact approval token required for a future F1 run.

No candidate or rollback was transferred. Odin was not invoked, the device was
not rebooted, and no device write occurred. F1 remains inactive until the
operator supplies that exact token in a new explicit approval message.

## Reused Core

No candidate-specific live runner was added. P2.26 and P2.27 are thin adapters
over the existing P2.21 candidate builder, independent checker, and P2.22
offline promotion core. The only shared-core changes are:

- an optional stable `vmlinux_path` argument so a newer artifact profile can
  perform its own linked audit; and
- a promotion verdict constant so an adapter does not inherit a P2.22 label.

The Process v2 runner, live adapter, D0 adapter, Odin transition core, USBFS
identity code, transport, state machine, and permanent boundaries are
unchanged.

## P2.25 Build Reconciliation

The exact P2.25 build result records vendor compilation return code 0 but an
outer return code 7 because its first adapter required an absent GNU objdump
path. The P2.26 artifact contract accepts only that exact immutable result and
requires the supplemental exact-vmlinux audit to pass. It does not reinterpret
an arbitrary failed build.

The contract rechecks the exact Image, vmlinux, config, original build result,
source restoration, inherited build gates, output receipts, safety fields, and
the known post-build tool-path failure. It then runs the fixed linked audit and
requires `reset_retention_proven: false`.

## Candidate Artifacts

| Artifact | Size | SHA256 |
| --- | ---: | --- |
| `boot.img` | 100,663,296 | `9d0c30eda160c8369c80f0c128cba90db68566c4b6795c15da466ac5e820b940` |
| `boot.img.lz4` | 27,061,894 | `a69bafd1e4d3c69a9e075c1b405ae5015471b86ed7eec6f809005f4994264675` |
| `odin4/AP.tar.md5` | 27,064,361 | `aad4cf6bb572e228b81a1c8f441ecc50c021e3350935a349c58ed83ba4c2c44f` |
| artifact result | 5,854 | `5c2e65353c1dcc2ee4d486e2fd9264d338b230fa6c998bd70c05cd42c00817bf` |
| independent static result | 11,203 | `3dbabd3fd9e411eb425a66accb2d0f589f3ce69862d13e481f2ca0095702aa69` |

Independent closure proves:

- the candidate differs from its carrier only in the fixed kernel interval;
- the extracted kernel equals P2.25 Image SHA256
  `242909cf62c6ee1642f81da6c8d0cece3041d619a13f01e6f4ded5ee7957352a`;
- the AP has exactly one direct regular `boot.img.lz4` member;
- the compressed frame independently round-trips to the submitted boot;
- the pinned static `/init` and child remain exact; and
- the runtime still loads only the five qualified early modules and contains
  no `sec_log_buf.ko`, direct ring writer, `/dev/mem`, or block-write path.

## Process v2 Binding

| Evidence | Size | SHA256 |
| --- | ---: | --- |
| run manifest | 909 | `37a92e0798836e4c4dd261ce6e851878ceb1a888593481055292edd3dec1d58f` |
| static check | 2,374 | `2a269ec556f1b49e134a728de202d923f7302aae966f85b947dd65f0c143fa34` |
| ready manifest | 2,170 | `cacde38dabd325ea1468537503a03b19fdabf810949a290a47dd4cc2a8d9345f` |
| validated bundle | - | `61d040de0730396ab5798deb2662b96735007e028caff9ccc5339954f83b3b8b` |

The ready manifest binds the same proven Magisk boot-only rollback AP as the
earlier successful recovery path. Common core and live-adapter host validation
both pass before connected preparation.

## Connected D0

The reusable live adapter's `--prepare` mode observed exactly one Android
target matching the FYG8 profile, verified root and health evidence, confirmed
the clean same-ring baseline, reopened the candidate and rollback artifacts,
and bound the current execution closure. Its durable private result reports:

```text
device_contact=true
device_writes=false
partition_transfer=false
reboot_requested=false
odin_invoked=false
f1_authorized=false
live_authorized=false
```

The private prepared run is
`workspace/private/runs/device-action-f1-live-v2/p228-prepared-1`. It is the
only binding eligible for the next exact approval. The token itself is not
tracked and no archived token can authorize execution.

## Next Gate

P2.29 is the one attended F1 attempt. It requires the operator to send the
fresh exact token from the P2.28 prepared result. That one approval binds the
candidate, rollback, manifest, target evidence, and runner closure and also
preauthorizes mandatory rollback. Without that message, stop before execute.
