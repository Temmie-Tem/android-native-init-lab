# S20+ G986N onboarding D0 H0 preparation - 2026-08-12

Status: **TERMINAL D0 PASS - ONBOARDING CONSUMED**

## Scope and Result

This H0 unit introduces a proposed target contract and bounded read-only
onboarding inventory for the operator-owned Galaxy S20+ 5G `SM-G986N`.
No ADB, USB endpoint, device shell, root, reboot, mode transition, Odin,
payload, or partition action occurred.

Operator statements and photographs establish the initial public facts:

- product/model: Galaxy S20+ 5G / `SM-G986N`;
- photographed software: One UI 5.1, Android 13, suffix
  `G986NKSS8IYC2`, kernel series `4.19.113`;
- bootloader unlock: completed; and
- USB debugging: enabled/allowed, pending direct ADB verification.

Raw serial and IMEI values visible in the private conversation are deliberately
absent from tracked files.

## Changed Closure

- `GOAL_S20PLUS.md`
- `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md`
- `workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py`
- `tests/test_s20plus_g986n_d0_inventory.py`
- `docs/reports/S20PLUS_G986N_ONBOARDING_D0_H0_2026-08-12.md`

The target contract is now `BINDING` and exactly one S20+ row is present in the
binding registry in `AGENTS.md`. This activates only the exact D0 onboarding
inventory and grants no D1, F1, root, reboot, mode-transition, transfer, or
partition authority.

## Execution Shape

After independent review and exact registry activation, the proposed D0 will:

1. run bounded host `adb version` and two `adb devices -l` inventories;
2. require exactly one `model:SM_G986N` row and require its state to be
   `device`, with unique serial and nonconflicting exact model/device/product
   metadata;
3. address only that exact serial for one bounded `get-devpath` and two
   identical fixed unprivileged property snapshots, binding their returned
   model/device/product values back to the selected ADB metadata; and
4. emit a private no-clobber result with three selected-target commands and
   zero commands to S22+, A90, and every other target.

The fixed snapshot contains only product/build/kernel/SoC identity,
boot-completion and verified-boot properties, SELinux state, shell identity,
and a boot ID that is removed and replaced with its SHA-256 digest before the
result is created. It contains no serial/IMEI query, root path, service or
setting mutation, device-file write, reboot, Download/recovery transition,
Odin, payload, block-device, or partition access.

The CLI fixes the executable target to `/usr/bin/adb`, pins its canonical
realpath and SHA-256, and verifies inode/size/hash identity before and after
collection. It exposes no alternate executable option. Before the first
connected command it writes a private intent and fixed active-intent guard.
Success, failure, and interruption leave that guard in place, preventing a
second connected invocation. Failure also writes a no-clobber private receipt
with actual command counts, a hashed failure signature, zero-effect assertions,
and a terminal no-retry verdict.

## Validation

- Python compilation: PASS.
- Focused tests after first-review remediation: 15/15 PASS.
- Device-hidden dry run: PASS; `live_authorized=false`.
- `git diff --check` for the new closure: PASS.
- Connected device commands: 0.

The fixtures cover missing, wrong-model, unauthorized, duplicate-serial,
mixed-state, conflicting-model/device, replaced, and changed targets;
metadata-property mismatch; snapshot schema/model/health/boot-ID failures;
output and time bounds; private identifier redaction; durable intent/result/
failure no-clobber mode; active-intent replay refusal; run-directory
containment; and absence of control/root/transfer CLI surfaces.

## Independent Review Required

The first independent review correctly withheld `PASS_GO`. It found that the
draft accepted duplicate serials and conflicting ADB metadata, did not bind
snapshot device/product values back to the inventory, exposed an arbitrary
`--adb` executable override, lacked durable failed-attempt/no-replay state,
would retain draft-only test assertions after activation, and omitted this
report from its own closure list.

The current remediation rejects those ambiguous identities, cross-binds the
snapshot, pins and revalidates the canonical ADB bytes, removes the override,
durably arms one non-replayable intent before contact, records actual failure
counts, expands the fault corpus, updates the closure list, and reserves the
draft-to-binding assertions for the activation patch. The same reviewer must
recheck these exact bytes before activation.

Before connected use, one independent reviewer must inspect the exact contract,
runner, tests, this report, and proposed registry activation. The review should
attempt to find:

- any route that addresses an unselected serial;
- any accepted ambiguous, offline, unauthorized, replaced, or changed target;
- raw serial, topology, boot-ID, IMEI, phone, account, or network identifier
  leakage;
- shell expansion or caller-controlled remote command material;
- device writes, root, service/settings control, reboot, mode transition,
  transfer, or partition access;
- output/time/path/no-clobber failures that could turn the one-shot D0 into an
  unbounded or replaying action; and
- any wording that could grant S20+ D1/F1 or transfer authority.

The re-review returned `PASS_GO` with no unresolved finding for runner SHA-256
`3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81`,
test SHA-256
`8ba9d91cff80069eb742ce82dc7b13b1f06b9947b35e245000f1f1412507671b`,
and pre-activation contract SHA-256
`f4bca9e6c9fbeee597cc10ef25f71158b995a9294550e1e28bec2bca23b80908`.
The exact mechanical activation changed only contract status/record, the one
registry row, goal state, report state, and draft-only assertions. It did not
change the reviewed runner or broaden device authority.

## Terminal Live D0 Result

The approved one-shot connected D0 returned
`PASS_S20PLUS_G986N_D0_ONBOARDING_READ_ONLY`. It established:

- exact public identity `SM-G986N` / `y2q` / `y2qksx` /
  `G986NKSS8IYC2`;
- Android 13 / SDK 33, first API 29, security patch `2025-03-01`;
- Qualcomm `kona`, QTI `SM8250`, `aarch64`, kernel
  `4.19.113-27166950`;
- boot complete, boot animation stopped, SELinux Enforcing;
- ADB state `device`, so USB debugging and host authorization are directly
  verified; and
- `flash_locked=0`, `vbmeta_device_state=unlocked`, and verified boot `orange`,
  corroborating the unlocked bootloader state without establishing root or
  flash readiness.

The durable private intent and active guard are identical, mode `0400`, and
SHA-256 `9bb8430b167e979cdbcfa0d5bca12feeb0d292bf7dfd92819f470de98938fbce`.
The mode-`0400` private result SHA-256 is
`bda29a458c11eab7634bf1d0ea9186ba314f55604e06fe0fca331ab8e6a60cef`.
Serial, topology, and boot ID are present only as SHA-256 digests; the known
raw serial and IMEI and raw USB topology are absent from the result.

Counts are six bounded host ADB invocations: two global inventories and three
commands addressed to the exact S20+. S22+, A90, and every other target each
received zero commands. Device writes, root use, reboot, mode transition,
payload transfer, and partition access are false; D1/F1 authority is false.

The active-intent guard remains present. This D0 is consumed and is never
replayed. The post-result host privacy checker initially used an invalid JSON
array traversal and exited without changing the result; a corrected exact-key
and digest-shape check passed. No device command was repeated for that host
inspection defect.

## Operator-Provided Download Mode Photograph

The operator subsequently supplied a 1001-by-1280 JPEG photograph of this
S20+ already displaying Download Mode. The attachment SHA-256 is
`2ea3eac21446264aac030bf00c25727c3bdf478712984d9d1b8154ee524bfe4c`.
No ADB, USB enumeration, Odin, reboot, mode-transition, or other device command
was used to obtain or inspect this photograph.

The following screen text is sufficiently clear for exact status recording:

- `RPMB Fuse Set`;
- `RPMB PROVISIONED`;
- `CURRENT BINARY: Samsung Official`;
- `FRP LOCK: OFF`;
- `OEM LOCK: OFF (U)`;
- `KG STATUS: CHECKING`;
- `WARRANTY VOID: 0x0`;
- `QUALCOMM SECUREBOOT: ENABLE`;
- `SECURE DOWNLOAD: ENABLE`; and
- `HDMI STATUS: NONE`.

The photograph also visibly contains a DID. It is treated as a private device
identifier and is intentionally omitted from tracked text. In this first
photograph, the RP SWREV row and one red status/code row were not transcribed
because blur and color overlap did not support exact character-level evidence.

This photograph corroborates `OEM LOCK: OFF (U)` together with the earlier
Android observations `flash_locked=0`, `vbmeta_device_state=unlocked`, and
verified boot `orange`. It does not establish that flashing is safe or ready.
In particular, `KG STATUS: CHECKING` is retained as an unresolved observed
state, not normalized to pass; rollback artifact, recovery path, exact
partition identities, root, and any Odin transfer capability remain unknown or
undefined. The observation grants no Download-mode exit, reboot, D1, F1,
payload, or partition authority.

### Clearer follow-up photograph

The operator supplied a closer 1221-by-1280 JPEG of the same Download Mode
status block, SHA-256
`e3ce871f7381b1f64abdccab4fcdbf7eeed565475704b3d122bd225e3920e7be`.
It preserves all previously recorded fields and makes the two formerly
untranscribed rows sufficiently clear to record as:

- `RP SWREV: B8(1,1,1,0,1,1) K0 S0`; and
- `SPU:5`.

`B8` is consistent with the revision digit in the observed firmware
`G986NKSS8IYC2`, but this is only a consistency observation. It is not a
firmware compatibility, anti-rollback, Odin, or flash-readiness decision. The
DID remains intentionally omitted. Processing the follow-up photograph used
zero device commands and created no connected or live authority.
