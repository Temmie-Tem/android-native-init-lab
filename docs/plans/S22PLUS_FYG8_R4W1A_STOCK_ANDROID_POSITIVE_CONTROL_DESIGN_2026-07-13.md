# S22+ FYG8 R4W1-A Stock-Android Positive-Control Design

Date: 2026-07-13 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `A0_HOST_ARTIFACT_PASS; A1_ORACLE_HIGH_RISK_UNRESOLVED; NO_LIVE_AUTHORIZATION`

This document began as a host-only design and did not itself create a boot
image, AP, live helper, policy exception, consumed state, device session, or
flash authority. The later separately authorized A0 host implementation is
recorded below; it still creates no live authority.

## Decision

R4W1-A will test the exact clean-reproduced R4W1 raw Image in the existing
live-proven R3C0 stock-Android carrier. It will not use a Magisk ramdisk and it
will not add the nine Magisk DEFEX/PROCA kernel byte changes.

The live proof is a conjunction:

1. the exact boot-only candidate reaches stable FYG8 Android;
2. the exact R4W1 marker is recovered from the first Magisk rollback boot's
   `/proc/last_kmsg` after being absent at baseline; and
3. the exact Magisk boot, root, stock DTBO, and stock recovery return.

Only this conjunction may return
`PASS_R4W1A_ANDROID_INIT_EXEC_WITNESS_RETAINED_AND_ROLLED_BACK`.

This choice tests the G/H artifact itself. A Magisk carrier would either lose
root with the unpatched R4W1 Image or require the separately audited nine-byte
Magisk kernel delta, so it would no longer be the exact clean-reproduced
artifact.

## Load-Bearing Evidence

The design depends on these already closed facts:

- R4W1 G/H raw Image SHA256:
  `9552653de86dbdc2f1abd919b4d7b0d3f365fc878a56ed5ae09c82d0d81d844c`;
- R4W1 Image size: `41490944` bytes;
- R4W1 cross-tree result SHA256:
  `71ab56b4c56010225145b82899535fbb9680c455e78aec19cebb39f39ad2cbd8`;
- R4W1 patch SHA256:
  `e66962c9e8cc503f9c5e94265816fdc2e96f4920a2d47387c6f1a4d9bbc6b787`;
- R3C0 live-proven carrier raw boot SHA256:
  `384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f`;
- R3C0 carrier manifest SHA256:
  `febffce465ea639d4d4751170bf280ae148ca3431f560aae6ecd8ea08f12ced0`;
- R3C0 live verdict:
  `PASS_R3C0_NORMALIZED_STOCK_CARRIER_AND_ROLLED_BACK`;
- R3C1 live verdict:
  `PASS_R3C1_UNPATCHED_REBUILT_KERNEL_VIABLE_AND_ROLLED_BACK`;
- Magisk rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- stock cleanup-only AP SHA256:
  `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`;
- stock DTBO SHA256:
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- stock recovery SHA256:
  `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`.

Read-only host comparison already proves that the R4W1 Image, the unpatched R2
Image, and the R3C0 carrier kernel have identical 64-byte ARM64 Image headers.
All use the same `[4096,41495040)` boot kernel interval.

## Why Rollback `last_kmsg` Is The Primary Oracle

The witness appends this fully framed marker after PID 1 accepts `/init`:

```text
[[S22R4W1|id=9ed5923b08c5eedbbdb0aaa6f6a5200c|phase=RAMDISK_EXEC_ACCEPTED|pid=1|path=/init]]
```

Exact FYG8 `sec_log_buf.ko` probe order is:

1. map and validate the reserved ring;
2. copy the ring into the immutable `last_kmsg` buffer;
3. create `/proc/last_kmsg`;
4. append early printk data and register the current logger; and
5. create `/proc/ap_klog`.

The R4W1 witness runs before this module. Candidate Android therefore creates
a module-load snapshot after the marker write. Candidate root is deliberately
not required, so reading that snapshot may be blocked by Android SELinux. The
helper may attempt an unprivileged, bounded candidate read as corroboration,
but failure or denial is not converted into a negative claim.

The intended load-bearing oracle is the first rooted Magisk rollback boot. Its
stock kernel cannot create the R4W1 marker, while its `sec_log_buf.ko` snapshots
the retained ring into `/proc/last_kmsg`. V3428R proves the transition and
persistence invariant for a marker armed immediately before Download. It does
not prove survival of a marker written before a complete Android boot.

The ring is circular and an early marker can be overwritten by later logs.
Existing exact snapshots establish a high feasibility risk:

| Evidence | Snapshot bytes | Oldest timestamp | Latest timestamp |
| --- | ---: | ---: | ---: |
| O11 first rollback | `2097136` | `3.541924` | `35.415962` |
| V3437 candidate | `2097136` | `3.453647` | `33.253545` |
| V3439 first stock boot | `2097136` | `3.342527` | `27.748355` |

The source snapshots are pinned respectively at SHA256
`8db1b9211818f654b5c8f50151004dd3373a4c925b8c57aa19c210a8fa157787`,
`d6a7bc92b12a472f78ffb2567dae1cdea99dc703ffa0ca26849b154cb5a8c8ae`,
and `4e706127ec6065c98b1ade492fa3bd6f62b8294209b8b9b737546386c78589a3`.

Each normal-boot snapshot is already a full ring and has lost the earliest
three-plus seconds. The exact R4W1 marker time is not measured, so this is not
proof of overwrite, but it is strong evidence that waiting for three stable
Android samples may erase the physical-ring copy before rollback.

The future helper must request Download immediately after its selected
candidate milestone. Absence after rollback remains `NO_PROOF`; it is never
evidence that `/init` was rejected. A1 implementation and live design remain
blocked until A0 closes an observation path that does not depend on an
unmeasured early marker surviving a full Android boot.

## A0 Artifact Contract

The future builder is a new R4W1-A-specific program. Retired R3C0/R3C1 sources
and state are not reactivated.

It must:

1. read the R3C0 carrier and R4W1 Image once each, then validate the exact
   in-memory bytes used for construction;
2. replace only `[4096,41495040)` in the R3C0 raw boot;
3. require the inserted interval to equal the exact R4W1 Image byte-for-byte;
4. require zero changed bytes outside that interval;
5. preserve the R3C0 header, stock ramdisk, signer-normalized region, vbmeta,
   AVB footer, padding, and total `100663296`-byte size;
6. explicitly retain the already-audited stale AVB descriptor semantics;
7. generate one strict LZ4 frame and one deterministic USTAR `AP.tar.md5`
   containing only `boot.img.lz4`;
8. run Odin parsing only against fixed nonexistent path
   `/dev/bus/usb/999/999`, requiring failure before device open;
9. refuse existing output paths and atomically promote only a complete result;
   and
10. set every device-contact, transfer, flash, and live-authorization field to
    false.

An independent static checker must reconstruct the candidate from pinned
inputs and verify:

- exact R4W1 build/repro evidence and marker identity;
- exact kernel interval and zero outside-kernel delta;
- exact R3C0 carrier geometry and all preserved regions;
- AP tar, MD5 trailer, LZ4 round trip, and single-member shape;
- full FYG8 stock-firmware evidence;
- exact Magisk and stock rollback chains; and
- boot-only scope.

It must also prove from the exact patch and carrier that the witness gate is
the stock ramdisk PID-1 `/init` path: one successful
`kernel_execve("/init", ...)`, PID exactly 1, and exactly one call to the
R4W1 record function after the success predicate.

### A0 Overwrite-Budget Deliverable

A0 must produce a machine-readable, SHA-bound overwrite-budget result from all
available normal-boot `ap_klog`/`last_kmsg` captures. It records ring size,
snapshot size, oldest/latest parsed kernel timestamps, source SHA256, and the
limits of inference. At minimum it includes the O11, V3437, and V3439 evidence
above.

A0 does not claim an exact byte count from witness write to `boot_completed`
when the prefix is already lost. It must classify the current rollback-only
oracle as `HIGH_RISK_UNRESOLVED` unless one of these is independently closed:

1. exact FYG8 SELinux and file-mode proof that non-root candidate ADB can read
   the immutable candidate `/proc/last_kmsg` snapshot;
2. exact FYG8 dumpstate proof that a bounded host capture returns the complete
   candidate `LAST KMSG` section, with any temporary userdata write and cleanup
   explicitly authorized in a future policy;
3. a separately reviewed witness channel that cannot be overwritten; or
4. a separately labeled Magisk-equivalent positive control whose nine-byte
   kernel delta and root semantics are not confused with the exact G/H Image.

AOSP generic policy and tooling are supporting evidence only. AOSP shell policy
allows a bounded set of proc reads, but Samsung's effective FYG8 policy is not
pinned. AOSP dumpstate can fall back to `/proc/last_kmsg` when no pstore console
file exists, but the exact Samsung binary, output shape, and temporary-file
behavior are not yet verified. Android BootReceiver stores only a truncated
tail and is not an acceptable early-marker oracle.

Primary references:

- AOSP shell policy:
  <https://android.googlesource.com/platform/system/sepolicy/+/refs/heads/android11-tests-dev/public/shell.te>
- AOSP dumpstate `LAST KMSG` fallback:
  <https://android.googlesource.com/platform/frameworks/native/+/d0198af634f557f57d3c541eb00ca8d9a6460408/cmds/dumpstate/dumpstate.cpp>
- AOSP BootReceiver tail capture:
  <https://android.googlesource.com/platform/frameworks/base/+/6193aa3/core/java/com/android/server/BootReceiver.java>

Three clean outputs from final checked source match on raw boot, LZ4, AP, and
manifest:

- raw boot: `a2bba0ef907af14e57508ca55d247d571c3f89936dd7020293e51ebfa8f8d133`;
- LZ4: `0bf83af2bb7167aae4a57be1686599aa99fe9e75ccd7aa89128da799a4c14a99`;
- boot-only AP: `cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895`;
- manifest: `3b9b5c0f0d3bac818a010cb7682e1146eaa50d5feec8a16324a039bbd5d2f85b`.

The independent checker returned `PASS_R4W1A_THREE_REPRO_STATIC_CONTRACT`.
Artifact reproduction PASS does not override the overwrite-budget result:
`HIGH_RISK_UNRESOLVED`, `a1_ready=false`.

## A1 Pre-Live Gates

The future live helper may be implemented only after the overwrite-budget gate
selects a viable primary marker oracle. It must have separate R4W1-A constants, verdicts,
acknowledgements, run directory, and consumed-state path. It may import only
reviewed transport and read-only collection primitives.

Before an exception can become ACTIVE, require:

1. A0 builder, tests, three reproductions, and independent static checker PASS;
2. exact SHA pins for candidate raw boot, LZ4, AP, manifest, helper, Odin, both
   rollback APs, R4W1 Image, build/repro results, DTBO, and recovery;
3. focused negative tests for wrong target, wrong artifact, duplicate path,
   malformed marker, foreign marker, partial reads, transfer failure, missing
   Android milestone, missing rollback endpoint, stock fallback, and consumed
   state;
4. offline check with zero device contact;
5. independent read-only review of source, tests, artifacts, and policy draft;
6. one connected read-only dry-run while policy remains inactive; and
7. fresh attended approval supplied only after all preceding gates.

The connected dry-run must prove one exact Magisk Android baseline:

- model/device/build `SM-S906N/g0q/S906NKSS7FYG8`;
- completed boot, stopped boot animation, and orange verified-boot state;
- Magisk `uid=0(root)`;
- boot SHA256
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- stock DTBO and recovery hashes;
- `sec_log_buf` module `Live`, exact platform bind, and both proc nodes;
- complete bounded reads of baseline `/proc/ap_klog` and `/proc/last_kmsg`;
- zero exact, partial, malformed, or foreign R4W1 marker occurrences;
- SHA256 for both complete baseline snapshots, durably bound to the run;
- no Odin endpoint; and
- absent R4W1-A consumed state.

Baseline marker contamination is a hard preflash stop. The helper must not
delete, clear, rotate, or initialize the ring.

## One-Shot Live Sequence

1. Re-run the complete offline and connected preflight.
2. Request Download from the exact baseline Android target.
3. Require exactly one Odin endpoint.
4. Durably create the R4W1-A consumed-state record immediately before
   `candidate_flash_start`.
5. Transfer the exact candidate AP once to boot only.
6. Require the original Odin endpoint to disconnect.
7. Observe candidate Android for at most 300 seconds.
8. Require three stable samples of exact model/device/build, completed boot,
   stopped boot animation, orange verified-boot state, exact FYG8 release, and
   exact R4W1 `/proc/version`. Candidate root is not required.
9. Capture the A0-selected candidate marker oracle. A direct non-root read,
   dumpstate capture, or other path is not allowed merely as a best-effort
   option; its exact bytes, permissions, bounds, and cleanup contract must have
   been selected before policy activation.
10. Immediately request Download. If candidate ADB is absent, require attended
    physical Download entry.
11. Flash the exact Magisk rollback AP once.
12. On the first returned Magisk boot, verify exact baseline health and
    `sec_log_buf` readiness before any further reboot.
13. Read `/proc/last_kmsg` twice to EOF through root, fsync both raw snapshots
    and their classifications, and require byte-identical reads.
14. Finish only after exact marker classification and final no-Odin check.

Every event and result update is written atomically and fsynced before the next
destructive transition. No candidate or rollback transfer is retried.

## Marker Classifier

The classifier works on raw bytes, not decoded or line-truncated shell output.
It must require:

- snapshot size greater than zero and no larger than the exact ring payload;
- two post-rollback reads with clean EOF, identical size, bytes, and SHA256;
- at least one complete newline-framed exact marker;
- every `[[S22R4W1|` occurrence to be that exact expected frame;
- no partial frame at either boundary;
- no foreign ID, phase, PID, or path; and
- baseline count zero in both proc snapshots.

Multiple exact frames are allowed because an attended boot retry may execute
the same exact kernel more than once. Their count is recorded. Any malformed
or foreign frame blocks PASS.

## Verdict Matrix

| Candidate Android | Exact rollback marker | Magisk rollback | Verdict |
| --- | --- | --- | --- |
| yes | yes | exact | `PASS_R4W1A_ANDROID_INIT_EXEC_WITNESS_RETAINED_AND_ROLLED_BACK` |
| yes | no | exact | `NO_PROOF_R4W1A_ANDROID_VIABLE_WITNESS_NOT_RECOVERED` |
| no | yes | exact | `PROOF_R4W1A_INIT_EXEC_ACCEPTED_NO_ANDROID_MILESTONE` |
| no | no | exact | `NO_PROOF_NO_R4W1A_ANDROID_OR_RETAINED_WITNESS` |
| any | any | stock cleanup | `STOCK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED` |
| any | any | unverified | `FAIL_R4W1A_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED` |

All verdicts other than the first are nonzero and do not promote R4W1-B.
Candidate transfer failure is separately
`NO_PROOF_R4W1A_CANDIDATE_TRANSFER_FAILED_MAGISK_ROLLED_BACK` when exact
Magisk rollback succeeds.

`PROOF_R4W1A_INIT_EXEC_ACCEPTED_NO_ANDROID_MILESTONE` is a completed partial
result, not an automatic retry trigger. The one-shot state remains consumed.

## Timeline Contract

`timeline.json` has exactly one top-level key and one schema:

```json
{"events":[{"name":"live_session_start","timestamp_utc":"..."}]}
```

The standard phases appear exactly once and in order:

1. `live_session_start`
2. `candidate_flash_start`
3. `candidate_flash_done`
4. `candidate_boot_ready`
5. `rollback_flash_start`
6. `rollback_flash_done`
7. `rollback_boot_ready`
8. `live_session_end`

The result JSON carries explicit phase semantics when a named milestone was
not achieved; the timeline shape never gains ad-hoc `steps`, elapsed fields,
or nested phase objects.

## Recovery And Safety Envelope

- Only boot may be transferred.
- Primary rollback is the pinned Magisk boot-only AP.
- Only a failed Magisk transfer with one unambiguous retained Odin endpoint may
  use the pinned stock boot cleanup AP; cleanup is never PASS.
- If candidate Android or automatic Download is absent, the operator physically
  enters Download mode for rollback.
- Candidate flash start consumes the one-shot exception regardless of result.
- Emergency rollback remains available only for the already-started run.
- No raw host `dd`, fastboot, recovery/vendor_boot/DTBO/vbmeta/BL/CP/CSC/super/
  userdata/persist/EFS/sec_efs/RPMB/keymaster/modem/bootloader write, Magisk
  module, format, panic, SysRq, RDX command, dump, EUD/UART write, PMIC/GPIO/
  regulator action, or A90 action is authorized.

The future policy must be a new exact SHA-pinned one-shot `AGENTS.md`
exception. Retired R3C0 and R3C1 exceptions cannot be reused.

## Promotion Rule

Only full R4W1-A PASS allows design of R4W1-B. R4W1-B must use a new marker ID,
a separately reproduced Image, a new candidate package, a new helper and
consumed state, a new exception, and fresh approval. R4W1-A does not prove any
checkpoint after `/init` acceptance, USB, native PID1 service readiness,
Debian, hardware completeness, long-duration stability, or cross-host build
reproducibility.

## A0 Implementation Result

The operator separately authorized A0 implementation after this design was
committed. The bounded host-only unit added a dedicated builder, an independent
checker, an overwrite-budget analyzer, and negative tests. It contacted no
device and created no A1 helper or policy.

The builder reads the carrier and Image once, executes only staged byte-exact
copies of the pinned LZ4 and Odin tools, and uses Odin only with fixed nonexistent
path `/dev/bus/usb/999/999`. The checker does not import the builder. It
reconstructs the expected boot bytes itself, validates all three outputs,
rechecks complete FYG8 firmware and rollback evidence, and verifies the exact
witness source predicate. Seventy-two related R3/R4 tests pass.

Result details and source/artifact pins are recorded in
`docs/reports/S22PLUS_FYG8_R4W1A_A0_HOST_ARTIFACT_RESULT_2026-07-13.md`.

## Next Unit

Independent review returned `GO` for committing the completed A0 host-only
implementation with no blocker. Early-marker overwrite remains the load-bearing
A1 feasibility risk. The next bounded unit is host-only oracle selection and
proof. This document does not authorize an A1 helper, connected dry-run, policy
activation, device contact, or live execution.
