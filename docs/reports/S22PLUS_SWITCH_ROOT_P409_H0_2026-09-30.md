# S22+ P409 readonly PID1 root transition: H0 qualification

Date: 2026-09-30 KST. Target: `SM-S906N/g0q/S906NKSS7FYG8` only.
Selected bounded unit: the first readonly transition in the
[Debian handoff plan](../plans/S22PLUS_DEBIAN_HANDOFF_EXECUTION_PLAN_2026-09-30.md).
The operator requested preparation through the point immediately before a
physical experiment. No experimental grant, mode change or flash is part of
this preparation.

## Result and scope

P409 `v0.4.0-rc.9` implements replacement of the actual native PID1 by a fixed
static preparation program, followed by BusyBox switch_root and a distinct
static RAM witness. The installed P401 root stays readonly and no installed
executable runs. Debian init, writable lifetime, services and access remain
the following functional unit.

The [review-gated capability](../operations/S22PLUS_SWITCH_ROOT_WITNESS_V1.md)
preserves the working native UFS/ACM startup and authenticates before requesting
the terminal transition. The same nonblocking ACM descriptor carries bounded
authenticated progress and the witness. The initial console cannot resume or
detach after accepting the transition. One compound intent consumes this work
and its only fixed Download return; successful native proof remains separate
from Download arrival, original-A transfer and final Android32 health.

## Ownership and storage

Actual native PID1 passes a sealed state memfd and the authenticated ACM fd to
the preparation executable. It records the original run, nonce, kernel boot,
owned HUD child slots and 300-second deadline. Descriptor remapping duplicates
sources above fd4 first, so an originally occupied fd3 or low descriptor hole
cannot silently overwrite a retained input.

The helper settles all three known native workers before the existing checker
and root inspection. Exact waits, ECHILD and a bounded userspace census reject
unknown or surviving userspace. The reused checker now has explicit PID1-owned
failure kill/reap; no old console supervisor is assumed to remain available.
The unmodified default hooks produce the exact retained P408 helper bytes.

The exact GPT/entry-41 binding, partition-only BLKROSET and both RO readbacks
precede the clean-superblock admission and fixed unprivileged `e2fsck -fn`.
Readonly/noload/nodev/nosuid/noexec inspection compares 8,969 archive entries,
the installation markers and the declared additional entries. Partition RO,
superblock bytes and sealed GPT are checked after native-worker retirement.

Only the pinned witness is copied to executable RAM. The selected static
BusyBox is version 1.37.0, 1,975,064 bytes, SHA-256
`7d93682be37cf6ed46699f6fff546b80bf133cf8ec342c2d04bc23387f78bc34`.
The helper moves the root, RAM, configfs, dev, sys/debugfs and proc mounts,
closes all non-whitelisted descriptors and ordinarily unmounts both old `/run`
and the inspection work tmpfs. The final witness checks host PID1, boot,
readonly ext4 root device, partition RO, its RAM executable inode/digest,
complete moved-mount identity and the absence of other userspace or descriptors.

## Validation and findings

Real ARM64 system-QEMU uses the production parent transition include and actual
helper, selected BusyBox and witness binaries. The VM has no PID/user namespace
dependency. Its mounted old `/run` and proc/sys/dev/config/debugfs topology match
the reachable native startup. Block discovery, tty transport and terminal
poweroff are explicit virtual substitutions; this supplies no Samsung result
and demonstrates no physical automatic recovery.

The final matrix includes complete transition, fd holes, previously reaped
workers, unknown child/wait state, dirty and mismatching roots, wrong filesystem
identity, missing/non-executable witness, executable-RAM failure, mount-move
failure, late BusyBox exec failure, checker timeout, early exit zero, descendant
leak and wrong output. Every case compares the complete writable backing disk
before and after. Only the three intended positive cases emit valid post-exec
proof and complete the fixed return exchange.

The late-exec negative actually terminates PID1 and reaches a kernel panic.
BusyBox switch_root is not atomic; its late failures cannot be caught by the
previous helper. Physical Download and exact original-A recovery remain
required. Helper parking or QEMU poweroff is not evidence of that recovery.

Real native C dispatch and a separate C protocol peer exercise the old console
ACK followed by the new authenticated record domain over one PTY. RX cuts after
the exec marker produce NO_PROOF; cuts after a valid witness preserve that
scientific proof but do not authorize a return replay or close the owner.
The real Adapter regression places preparation beyond 90 seconds and verifies
that Download arrival uses the immutable return receipt's original deadline.
Missing/changed receipts reject before enumeration. Owner regressions preserve
single-transition/single-A accounting and health-only continuation after a
completed A transfer.

Independent review caught a low-FD remapping collision, corrected before final
VM qualification, and missing generated-header/source joins in the new helper
audit. The latter are required to bind the actual compiled partition/GPT,
comparison and executable identities. An early VM run also found an incorrect
BusyBox argv0; the fixed applet invocation was rerun successfully. All failed H0
attempts remain private evidence; no device transition resulted from them.

## Retained evidence and pre-experiment state

Private evidence base:
`workspace/private/outputs/s22plus-switch-root-h0-20260930-1/`.
Artifacts, generated filesystem bindings, authentication inputs and raw captures
remain under `workspace/private/`. P401–P408 consumed journals and artifacts
retain their original provenance. A90 and S20+ were not contacted.

The final package is `s22plus-switch-root-v1/p409/build-2/`. Its A/B actual
boot-only AP is 34,529,321 bytes and byte-identical to the pre-audit-correction
build. The 176 runtime inputs and 82 host inputs are preserved with validation
sources and the declarative candidate catalogue in a 247-file snapshot.

| Evidence | SHA-256 |
| --- | --- |
| Actual selected AP | `cd61bc7ebdd9406ac6b2b7e213ec2001f3c317ba98358d6a5237c1822d499320` |
| Final `build-2/result.json` | `b6f0aa9f3e63fee5d998626641a7636eccc784eb8bb0dd4f32766cd5c09cfbcf` |
| `qualified-1/image.json` | `362c022395c037017b0b5d176e568cb929a438c4df5bddcd40b617d307d5ac9c` |
| Actual artifact qualification audit | `03b001ba27829bfd796e4fb83c7900149848b6a571f233731b1d02931a26843a` |
| `source-closure-1.json` | `ce57371c1c5af80699fa38c17b945110ad00f7be5290e750defcc0b6ad9aa4da` |
| `validation-1.json` | `b33c91772429efc67f44d16415b65dbd5b04cf2989c1d8e996772ac7828aa8a4` |
| Eight generated-input rejection cases | `0d2ba9e7691a3d77cafe52091b473f33e32e02159925806d1c66dbf914dd7fd5` |
| Independent review receipt | `738de9640d812921337e27091aa697510f3014f6e309f91e77d3f9674d94b27e` |
| Canonical capability review | `589f3cd0ccc2c33f16c9582561582e20bb8203401e4b3b1add654df552956abd` |

All 17 VM results passed their intended classifications and unchanged-disk
checks. The rebuilt virtual helpers and all seven fault builds match the
previously exercised binaries byte for byte. Physical builds reject virtual
fault injection. Seventy-five focused regression tests, the additional
health-only continuation case and the final 13 switch-root tests pass.
Eighteen selected Python files compile successfully. Exact boot-only
qualification and the live owner's strict image admission both pass against
the actual AP. Selected local links, whitespace and repository privacy checks
pass.

The [independent capability review](../../workspace/public/src/device-action/bindings/s22plus_switch_root_v1_review.json)
is **PASS_GO**, with no remaining findings. The reviewer independently checked
the frozen working-tree source bytes, actual A/B artifacts, all 17 VM results,
unchanged backing digests and the resolved descriptor/header-audit findings.
The canonical review admits only this scoped capability; it opens no device
grant and does not prove Samsung execution.

## Completed fixed D0 preparation

The first attempt stopped at its initial `adb devices -l` read because ADB
started its host daemon and printed startup notices to stderr. The bounded raw
capture shows successful daemon startup and enumeration of the selected S22+.
No target-specific command or mode change followed in that attempt. Its stop
and raw evidence remain under `prepared-1/`; stderr acceptance was not relaxed.

The already adopted fixed D0 reobservation ran in fresh `prepared-2/`.
Before/after health brackets proved the exact rooted original-A Android,
matching boot/supporting partition digests and same-boot continuity. Shell-v2,
full GPT metadata and Android32 statfs passed, with 34,357,624,832 filesystem
bytes. H0 rederivation reproduced the published preparation and validated the
concrete task, retained original-A recovery and current capability. All 22 raw
captures across the two preparation attempts were retained.

| Prepared evidence | SHA-256 |
| --- | --- |
| `prepared-2/ready.json` | `efd20ad4427ee0950fb12df19b66de5b279f19d98ab85f18c418b07f5edeafff` |
| Concrete task | `ad08d06a0f49aad51a8cc027e0b3c7d5950c7e9a3f09c6fd4dec289734fa96df` |
| `preparation-audit.json` | `4d579d9b94d4bbc724090f2da19bc55dc98ca2a529b22628eb60f5fa13f1e5a7` |

The task is READY only for `switch-root`, one attended operation and 1800
seconds. The candidate is unconsumed, the F1 owner is absent and no grant is
open. Preparation performed zero mode changes, transfers or native experiments.
The next physical operation requires its returned finite attended start. Its
future machine checks still bind the exact target, image, original-A recovery
and health. These Android reads make no current native_data content or Samsung
PID1-transition claim.
