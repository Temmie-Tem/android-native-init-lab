# S20+ G986N recovery ADB canary T0 design

Date: 2026-08-31
Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2` only
State: **H0 BUILT; POLICY AND INDEPENDENT REVIEW PENDING; NOT ACTIVE**

## Objective

Prove or refute one narrow proposition before installing a full TWRP:

> The exact unlocked S20+ boot chain accepts one IYC2-stock-derived recovery
> whose only semantic delta is recovery ADB plus a fixed marker, and the device
> can then be returned through one exact stock recovery rollback with exact
> healthy rooted Android and stock recovery bytes re-proved.

T0 is not an Android restoration project and does not preserve `/data` for its
own sake. Its purpose is to establish the recovery foundation needed to pursue
an A90-like native-init workflow safely. It performs no format, VBMeta change,
vendor change, Magisk change, or Android-data write.

## Why unofficial status is not the gate

The repository's A90 TWRP is also unofficial. Its value comes from exact and
repeatable operational evidence: a bound TWRP version/banner, a unique recovery
ADB transition, exact helper bytes, physical recovery availability, image
readback, no-replay handling, and observed return/rollback health.

The S20+ public AstroForge candidate contains the same 89-byte
`rebootsystem.sh` as A90, including SHA-256
`3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07`.
This makes the A90 treatment technically relevant, but transfers no authority.
S20+ still needs its own exact-target evidence and review.

## Current contract blocker

The common contract classifies recovery-partition payloads as forbidden and
defines F1 as boot-only. The current S20+ target contract grants no recovery
write. T0 cannot become live merely through a manifest, a passing builder, an
operator's broad willingness to discard Android, or an existing A90 exception.

Before live T0, independently review and mechanically activate either:

1. a new recovery-only risk tier; or
2. a narrow S20+-only recovery-canary exception whose semantics are at least as
   strict as ordinary F1.

The review must cover `AGENTS.md`, the shared risk-tier document, the S20+
target contract, the new recovery-only process/runner, the artifact builder,
the root-read-only recovery digest profile, the journal/recovery finalizer, and
hostile tests. Until all named bytes and gates are current, status remains H0.

## Exact artifacts

### Candidate

- `recovery.img`: 82,694,144 bytes,
  SHA-256 `e1297613df576d25cc9391df97dac7cf316fee545f56111e6bc5340cb8ce659b`;
- `recovery.img.lz4`: 36,547,618 bytes,
  SHA-256 `7f0e6b53a1036904fd02c5e8c2c014d3112ffb58fc33f9aa9a26c0962af45928`;
- recovery-only `AP.tar.md5`: 36,556,841 bytes,
  SHA-256 `30227458889f1fa99eca192c9b7f8747f168d9e33cc1f407b52ae2b4d298559a`.

### Rollback

- exact stock `recovery.img`: 82,694,144 bytes,
  SHA-256 `dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e`;
- exact stock `recovery.img.lz4`: 36,600,544 bytes,
  SHA-256 `6b962af2fc4fcc424d16ecdcee1793bdd6d4c8dba2e80d35cb21961fcb865923`;
- recovery-only `AP.tar.md5`: 36,608,041 bytes,
  SHA-256 `ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157`.

Each AP contains exactly one regular `recovery.img.lz4` member. Neither contains
boot, VBMeta, DTBO, vendor, super, userdata, modem, CSC, BL, EFS, persist, misc,
or another member.

## Candidate semantic closure

The candidate preserves the exact stock header, kernel, DTB, recovery DTBO,
partition size, and all but three ramdisk entries. It removes no entry:

- `prop.default`: exact substitutions `ro.secure=1 -> 0`, both exact
  `ro.adb.secure=1 -> 0` rows, and `ro.debuggable=0 -> 1`;
- `init.recovery.samsung.rc`: append one fixed boot trigger that sets
  `service.adb.root=1` and `sys.usb.config=adb`;
- `/init.s20plus_g986n_recovery_adb_canary`: add one mode-`0444`, 159-byte
  fixed marker with SHA-256
  `5aafd7ca6918bf82aef0b7de62346d8de1b17bb0c9ececafa15978cfae2c87b0`.

The recovery hash descriptor intentionally no longer matches. Its embedded
stock VBMeta signature still parses and verifies, but that does not authorize
or predict boot-chain acceptance. Runtime acceptance is the T0 proposition.

## Proposed attended live flow

### 1. Prepare, without a device effect

- Require the exact reviewed builder, candidate, rollback, runner, schemas,
  observer, root digest profile, and independent-review bytes.
- Require direct regular, single-link, non-writable artifact inputs at stable
  absolute paths; reopen and rehash them at every effect boundary.
- Prove each tar has one exact recovery member and that both LZ4 frames decode
  to their bound images.
- Create a new empty durable run journal and candidate-SHA permanent guard.
- Bind one fresh approval to this exact target, current boot, candidate,
  rollback, two recovery writes at most, manual transitions, observations, and
  final health. It cannot approve TWRP T1 or another image.

### 2. Prove the starting device and recovery bytes

- Use a fresh bounded public inventory to require one healthy
  `SM-G986N/y2q/y2qksx/G986NKSS8IYC2` and no ambiguous ADB selection.
- Bind hashed serial, physical USB topology, current boot ID, build, verified
  boot state, and the known resident Magisk/root-health profile.
- Through a separately reviewed fixed no-input root-read-only command, resolve
  the direct recovery by-name node and stream only its SHA-256. Require exact
  stock digest
  `dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e`.
- Record the complete pre-effect USB baseline and require the operator to be
  physically able to enter Download and Recovery.

If the current recovery digest is not exact stock, T0 stops before any write.

### 3. Enter Download and transfer candidate once

- Publish a durable physical Download-entry intent before the operator action.
- Require one newly arrived exact Samsung Download endpoint and bind its USBFS
  path/topology to this run.
- Publish candidate intent before invoking exactly once:

  `/usr/bin/odin4 -a <bound-candidate-AP.tar.md5> -d <bound-USBFS>`

- Do not use `--reboot`. This keeps the handset in Download after transfer so
  Android cannot run its stock-recovery restoration path before first canary
  observation.
- Missing, partial, timed-out, or malformed Odin output consumes the candidate
  attempt. Never replay it.

### 4. Boot directly into the candidate and observe

- Publish one physical Recovery-entry intent, then have the attended operator
  leave Download directly into Recovery with the model-specific key chord.
- Require a unique new `04e8:6860` recovery ADB endpoint on the bound topology;
  zero, multiple, unauthorized, or foreign endpoints prove nothing.
- Issue only a fixed bounded read sequence:
  target/build properties, boot ID, kernel banner, UID/SELinux state, and
  `cat /init.s20plus_g986n_recovery_adb_canary`.
- PASS_T0_CANDIDATE requires the exact marker bytes, exact IYC2 identity,
  recovery role, root UID, and stable same-boot observations. A visible recovery
  screen without the marker is supportive observation only.

Recovery ADB is deliberately unauthenticated in this canary. Therefore the run
must remain attended, use one physically controlled USB link, expire on any
disconnect/topology drift, and proceed immediately to rollback. This temporary
exposure grants no generic ADB shell authority to the runner.

### 5. Roll back recovery once

Candidate success, candidate refutation, or candidate uncertainty all converge
on the prebound rollback; none permits a candidate retry.

- Publish a physical Download-return intent before the operator returns to
  Download.
- Require one exact bound Download endpoint.
- Publish rollback intent before invoking exactly once:

  `/usr/bin/odin4 --reboot -a <bound-stock-recovery-AP.tar.md5> -d <bound-USBFS>`

- Missing or ambiguous rollback output never permits another Odin transfer.
  It leaves observation and external recovery pending.

### 6. Final proof

- Require a new Android boot ID and exact healthy rooted IYC2 state.
- Through the same fixed root-read-only profile, require the complete recovery
  block SHA-256 to equal the exact stock image again.
- Require candidate attempts exactly one, rollback attempts exactly one,
  candidate replay zero, other partition transfers zero, VBMeta changes zero,
  format/data/vendor/Magisk effects zero, and all owned temporary state closed.

Only both exact Android health and exact stock recovery digest close the run.
`PASS_T0_CANDIDATE`, `REFUTED_T0_CANDIDATE`, and `NO_PROOF_T0_CANDIDATE` remain
separate from rollback/final-health status.

## Cut and failure rules

- Intent always precedes physical transition or transfer.
- A cut after candidate intent consumes the candidate and reaches rollback only.
- A cut after rollback intent permits observation/finalization only; it never
  repeats stock recovery transfer.
- Observer or reporting failure never changes a proven transfer into permission
  to replay it.
- Loss of exact Download access, artifact drift, endpoint ambiguity, foreign
  device presence, current-boot drift before candidate intent, or inability to
  re-prove stock recovery is an immediate stop/recovery park.
- Other targets receive zero commands and no approval or identity transfers.

## T1 after T0

If T0 later proves custom-recovery acceptance and exact rollback, T1 may qualify
an exact unofficial TWRP. Official status is not required. Two evidence routes
remain possible:

1. a reproducible pinned-source build; or
2. a byte-pinned public image whose provenance uncertainty is retained, whose
   ramdisk is sanitized, and whose exact static/runtime behavior is separately
   qualified without claiming source reproducibility.

At minimum T1 must neutralize the automatic vendor deletion hook, prevent the
automatic read-write EFS/persist mounts or bind a reviewed alternative, decide
whether to remove or adopt the exact A90-identical `misc` hook through a narrow
S20+-only exception, and treat every manual TWRP flash/wipe/terminal surface as
outside runner authority. `/data` usability is then a separate observed claim,
not a prerequisite for proving TWRP boot and recovery ADB.

## Current verdict

The T0 artifacts and 9/9 focused host corpus are ready for independent review.
No live runner, common-boundary amendment, target-contract activation, approval,
recovery write, or device effect is created by this design.
