# Goal: S20+ G986N controlled onboarding

Establish an exact, isolated, evidence-bounded profile for the newly acquired
operator-owned Samsung Galaxy S20+ 5G before selecting any later experiment.

This file records current state only. It grants no device authority. The
binding target contract is
`docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md`. Independent review
returned `PASS_GO` for its exact D0-only onboarding closure, and `AGENTS.md`
contains one exact S20+ registry row. This does not define D1 or F1.
The current preparation evidence is
`docs/reports/S20PLUS_G986N_ONBOARDING_D0_H0_2026-08-12.md`.

## Current State

- Operator and photographic identification: Galaxy S20+ 5G, model `SM-G986N`.
- Photographed software: One UI 5.1, Android 13, build/baseband suffix
  `G986NKSS8IYC2`, kernel series `4.19.113`.
- Bootloader unlock: completed, based on operator statement and the photographed
  developer-options state.
- USB debugging: enabled/allowed based on the operator statement.
- Direct ADB verification: terminal one-shot D0 PASS. USB debugging and host
  authorization were verified with one exact row in state `device`.
- Live public identity: `SM-G986N` / `y2q` / `y2qksx` /
  `G986NKSS8IYC2`; fingerprint
  `samsung/y2qksx/y2q:13/TP1A.220624.014/G986NKSS8IYC2:user/release-keys`.
- Platform: Qualcomm `kona`, QTI `SM8250`, `aarch64`, ABI list
  `arm64-v8a,armeabi-v7a,armeabi`.
- Software health: Android 13 / SDK 33, first API 29, security patch
  `2025-03-01`, user/release-keys, kernel `4.19.113-27166950`, SELinux
  `Enforcing`, boot complete, boot animation stopped.
- Boot security observations: `flash_locked=0`,
  `vbmeta_device_state=unlocked`, verified boot `orange`. These corroborate the
  unlocked state but grant no root or flash authority.
- Operator-provided Download Mode photograph records the following
  screen-visible state: `CURRENT BINARY: Samsung Official`, `FRP LOCK: OFF`,
  `OEM LOCK: OFF (U)`, `KG STATUS: CHECKING`, `WARRANTY VOID: 0x0`,
  `QUALCOMM SECUREBOOT: ENABLE`, `SECURE DOWNLOAD: ENABLE`, RPMB fuse set and
  provisioned, `RP SWREV: B8(1,1,1,0,1,1) K0 S0`, `SPU:5`, and
  `HDMI STATUS: NONE`. This is photographic observation, not a host/ADB/Odin
  probe. It corroborates the unlocked state but does not prove flash readiness,
  rollback availability, recovery, root, or partition safety.
- The Download Mode screen's DID is a private device identifier and is omitted
  from tracked text. A clearer follow-up photograph makes the previously
  untranscribed RP SWREV and red status rows readable and is bound by SHA-256
  `e3ce871f7381b1f64abdccab4fcdbf7eeed565475704b3d122bd225e3920e7be`.
  The initial full-screen photograph remains bound by SHA-256
  `2ea3eac21446264aac030bf00c25727c3bdf478712984d9d1b8154ee524bfe4c`.
- Download Mode entry was performed by the operator outside this agent's
  command path. This recording sent zero device commands and grants no exit,
  reboot, Odin, transfer, D1, or F1 authority.
- Durable result: `PASS_S20PLUS_G986N_D0_ONBOARDING_READ_ONLY`; private result
  SHA-256 `bda29a458c11eab7634bf1d0ea9186ba314f55604e06fe0fca331ab8e6a60cef`.
- Counts: six bounded host ADB invocations total, including two inventories;
  three commands addressed to S20+, and zero to S22+, A90, or another target.
- Effects: device writes, root use, reboot, mode transition, payload transfer,
  and partition access all zero/false. D1/F1 authority remains false.
- Root, recovery path, rollback artifact, partition identities, and flash
  readiness: unknown and not inferred.
- S22+ and A90 state, profiles, evidence, approvals, and commands remain wholly
  separate.

## Current Bounded Unit

The S20+-only D0 onboarding inventory completed and proved that it:

1. selects one exact authorized `model:SM_G986N` ADB row;
2. reads only bounded unprivileged identity and normal-health facts;
3. stores raw execution evidence only under `workspace/private/` with serial,
   topology, and boot ID represented by SHA-256 digests;
4. proves that no command was addressed to S22+, A90, or another device; and
5. creates no D1, F1, root, reboot, mode-transition, transfer, or partition
   authority.

The durable active-intent guard remains present. The D0 is consumed and must
not be replayed. The operator-provided photograph now records Download Mode
state without creating a host-connected process. The next unit remains
host-only interpretation and selection of a future objective.

## Open Decisions

No post-onboarding objective is selected. Rooting, recovery work, native-init,
or boot-only experiments each require a separately designed and reviewed target
contract amendment; none is implied by the unlocked bootloader.
