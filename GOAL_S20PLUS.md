# Goal: S20+ G986N controlled onboarding

Establish an exact, isolated, evidence-bounded profile for the newly acquired
operator-owned Samsung Galaxy S20+ 5G before selecting any later experiment.

This file records current state only. It grants no device authority. The
binding target contract is
`docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md`. Independent review
returned `PASS_GO` for the exact D0 onboarding closure and the payload-free
Download-return D1 helper; `AGENTS.md` contains one exact S20+ registry row.
This file still grants no standing device authority.
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
- Routine public-property D0: PASS for the exact same target. Current Samsung
  sales/OMC properties are `boot_sales_code=KTC`, `csc_sales_code=KTC`,
  `omcnw_code=KTC`, `omc_path=/optics/configs/carriers/KTC/conf`, and
  `omc_etcpath=/prism/etc/carriers/KTC`; the distinct `carrier_id` property is
  `KOO`. The evidence therefore records current sales/OMC configuration `KTC`
  and boot carrier ID `KOO` separately rather than claiming one unqualified
  CSC value.
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
- Routine result: `PASS_S20PLUS_G986N_ROUTINE_D0_READ_ONLY`; private result
  SHA-256 `5c1825b643f1745c6ed0c84b19cf4cce0246b20c4e3eb60cdb8e6047d03ba04f`.
  Its four bounded host invocations comprised two global inventories and two
  exact S20+ reads; S22+, A90, and other-target command counts were all zero.
- Counts: six bounded host ADB invocations total, including two inventories;
  three commands addressed to S20+, and zero to S22+, A90, or another target.
- Effects: device writes, root use, reboot, mode transition, payload transfer,
  and partition access all zero/false. D1/F1 authority remains false.
- Root, recovery path, rollback artifact, partition identities, and flash
  readiness: unknown and not inferred.
- S22+ and A90 state, profiles, evidence, approvals, and commands remain wholly
  separate.
- Host-only stock-artifact acquisition: exact Samsung FUS version
  `G986NKSS8IYC2/G986NOKT8IYC2/G986NKSS8IYC2/G986NKSS8IYC2` was downloaded for
  `SM-G986N` / `KTC`. The private five-file firmware ZIP passed ZIP64 integrity
  validation and is bound by SHA-256
  `1add7bd2e8b122b0668a44b084fd5e5cd62fb7b90472412d12348599d10d64d7`.
- Stock boot candidate: the AP appended MD5 verified successfully; its sole
  extracted `boot.img.lz4` decoded to a 64 MiB Android boot image bound by
  SHA-256
  `29fde3a189b906ea20ed0e14fcd7a448e005597b82e3adceea64196284bd31ab`.
  This is an offline artifact candidate, not a demonstrated rollback or flash
  authorization.
- Samsung-published source: the operator completed the official Release Center
  download for exact row `SM-G986N` / `G986NKSS8IYC2`. The intact outer bundle
  is bound by SHA-256
  `3ae8f4606ce54e931535b72c5e339494655fd5b01a8b0abc45088033410fa1a5`;
  the extracted target-only `SM-G986N_KOR_13_Opensource.zip` is bound by
  SHA-256
  `f21189586ed4739b4810a81346cee0fdd6b82aa8fd7854b6ca337e7cac13d31e`.
  Both passed ZIP integrity checks.
- Samsung kernel source: `Kernel.tar.gz` passed gzip integrity and is bound by
  SHA-256
  `4ed0aa2f390d9d847eee313693fe8b9b726f4decefc40b3ba8fde1b64272ae6d`.
  It identifies Linux `4.19.113` and exact defconfig
  `arch/arm64/configs/vendor/y2q_kor_singlex_defconfig`. The required external
  GCC 4.9/Qualcomm Clang 10 toolchain, generated final `.config`, reproducible
  build, and stock-kernel byte identity remain unproven. Detailed H0 evidence
  is in
  `docs/reports/S20PLUS_G986N_STOCK_ARTIFACT_ACQUISITION_H0_2026-08-13.md`.
- Magisk boot-only H0: official Magisk v30.7 and its tag source were pinned;
  the APK is bound by SHA-256
  `e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5`.
  Its official `magiskboot` accepted the exact stock boot as Android boot v2
  with a gzip ramdisk, raw ARM64 kernel, DTB, Samsung marker, and AVB 2 footer.
  The ramdisk and DTB read-only tests both classify as stock/clean.
- Direct kernel evidence: Samsung's `extract-ikconfig` recovered the embedded
  final stock configuration, including `CONFIG_IKCONFIG=y`,
  `CONFIG_MODULES=y`, `CONFIG_MODULE_SIG=y`, and
  `CONFIG_MODULE_SIG_FORCE=y`; its text is bound by SHA-256
  `5e4e4a986f7aae396dc3ebb03818a4c0b9bea5f6948c5e17eb6abaf8d988f760`.
- AVB blocker: the stock boot's valid AVB 2 footer and the AP's separate
  top-level `vbmeta.img` both bind the exact stock boot digest. Magisk's
  Samsung AP flow modifies the separate VBMeta flags and the official first
  install flashes patched AP together with BL, CP, and CSC. That is not a
  boot-only transaction and is outside the permanent boundary.
- Current rooting verdict:
  `FORMAT_COMPATIBLE_AVB_AND_TRANSPORT_UNQUALIFIED_NO_GO`. No patched image was
  created. Detailed H0 evidence is in
  `docs/reports/S20PLUS_G986N_MAGISK_BOOT_ONLY_FEASIBILITY_H0_2026-08-13.md`.
- Routine connected-action simplification is independently reviewed and
  active for S20+ only. It covers exact routine reads, one-shot attended
  normal/Download/recovery reboot
  dispatch, the pinned Magisk v30.7 APK install, and no-clobber device-hash-
  verified staging of the exact stock AP. It grants no launch, patch, Odin,
  partition, root, or F1 action. The reviewed runner SHA-256 is
  `709a89fb35f643170a72e613105af68816a0a17ee622865f2d7ebdac6442c444`.
  The H0
  design is
  `docs/reports/S20PLUS_G986N_ROUTINE_CONNECTED_ACTIONS_H0_2026-08-13.md`.
- Patched-AP retrieval is independently reviewed and active for the current
  exact operator request. It accepts exactly one
  `magisk_patched-30700_[A-Za-z0-9_-]{1,64}.tar` in Download, verifies its
  device and host SHA-256, and publishes no-clobber into the private firmware
  tree. It grants no device write, root, patch, flash, partition, or F1 action.
  The active runner SHA-256 is
  `7b1d8989db5ffbf012cbf356e4e1411d5e487e965361b4ea61307a508b17bc72`.
- Patched-AP retrieval completed with
  `PASS_S20PLUS_G986N_PATCHED_AP_RETRIEVED_VERIFIED`. The exact
  `magisk_patched-30700_kFiLC.tar` is `7,362,972,672` bytes and bound by
  SHA-256
  `a025e13cf5665701df2229e07ecdab404a906d816aa7dd93aa3393bf8797b5f6`.
  It is a read-only private artifact under the target's private firmware tree;
  no partial remains. The private result SHA-256 is
  `c6183f5679510d713d2cefc7c58f7fbeebb811fbeb86e503f6567ca8f4b3e292`.
  The run issued zero device-effect, S22+, A90, other-target, reboot, root,
  partition, flash, or F1 commands.
- The exact `enter-download` D1 control was dispatched once and the operator's
  subsequent “다운로드 모드 진입” confirmation closed it as
  `download-observed`; it was not replayed. The private dispatch result SHA-256
  is `0f62006aa71e5d1a76e87f994d2c465fa47a8d550f2fe0e3fe99c5ab18418e84`.
- The attended, payload-free Download-mode return helper is active as an exact
  D1 action. It requires an empty USB baseline while the phone is physically
  held in Download mode, then one exact endpoint and the operator confirmation
  token before a single `odin4 --reboot -d` dispatch. It performs no AP or
  partition transfer and releases its guard only after exact normal-Android
  health. Runner SHA-256:
  `c00558393235b82e50b8df833fd97064801c3f297f1ce067cefcee27332a2bb6`.
- Odin host preparation found the full Magisk AP unsafe for direct use because
  it also contains recovery, DTBO, super, persist, VBMeta, and other members.
  A host-only builder extracted only its `boot.img` and prepared candidate and
  stock rollback AP files whose sole TAR member is `boot.img.lz4`. Candidate AP
  SHA-256 is
  `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`;
  stock rollback AP SHA-256 is
  `48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b`.
  Official Magisk v30.7 `magiskboot` accepted the candidate as boot header v2
  and its ramdisk test returned the Magisk-patched classification. These are
  private host artifacts only: Odin was not invoked, no flash occurred, and no
  S20+ F1 process or live flash authority exists.
- A target-specific one-shot bootstrap F1 was reviewed, but connected prepare
  exposed a pre-transfer Download profile mismatch: this device reports product
  `SM8250` and may negotiate the same physical port through two exact paired-
  controller topology identities retained publicly only as SHA-256. A
  correction was briefly activated, then suspended after its first approved
  execute exposed an endpoint-session defect before transfer. That historical
  activation grants no current authority.
- The first exact approved execution failed closed before candidate intent or
  Odin transfer because prepare-time Download device-node inode/devnum was
  incorrectly treated as stable across re-enumeration. Host validation and
  journal inspection proved candidate/rollback intents and raw transfer logs
  absent. A proposal to accept any fresh matching
  Download endpoint was rejected because it could transfer approval to another
  device on the same port. The dormant runner restores prepare-time endpoint
  identity equality. Only the exact host-only zero-effect abandon for this
  prepared run passed review and cleared its guard; F1 remains suspended and
  the approval must not be reused.
- The activated F1 correction now makes prepare start from exact healthy,
  root-absent Android. In one guarded execution it records a no-replay intent,
  records an empty endpoint baseline, dispatches exactly one Download reboot,
  observes an endpoint arrival after that baseline, and only then emits an
  approval token. Execute requires stable path, endpoint hash, `st_dev`, inode,
  `st_rdev`, topology, and USB profile continuity while treating mutable
  `ctime_ns` as observational; the freshly read complete identity is still
  pinned at Odin dispatch. If a stable field changes, the runner records
  the changed endpoint and stops before Odin; an attended
  `--confirm-candidate-endpoint` with token
  `S20PLUS-G986N-CANDIDATE-ENDPOINT-REENUM-CONFIRM` is required to bind that
  one observed endpoint for the sole candidate transfer. Recovery uses an
  explicit two-step physical handoff and never auto-selects a generic endpoint.
  The active runner SHA-256 is
  `fe86f61166a7f719678ca74431abb0de4f1638ead514289f973601f5b47c4cda` with
  normalized SHA-256
  `6ceec9037dad1e486450a7fc1085aeb5e527b1e3d1ec7420ac6aa23f03bb823e`.
  This correction passed independent `PASS_GO`; `F1_ACTIVE` is true, no run was
  created by activation itself, and activation grants only the attended
  boot-only F1 capability described by the target contract.
- Closed pre-candidate run state: one F1 run completed only its exact initial
  Android-to-Download transition and then stopped on endpoint re-enumeration
  before candidate intent. Host journal inspection records no candidate
  intent/result/raw output and no rollback evidence; partition transfer count
  is zero. The operator has returned the exact device to normal Android. A
  generic owner-aware `--abort-pre-candidate` health-only closure passed
  independent review and completed without Odin. Its terminal receipt records
  zero partition transfers, no candidate/rollback evidence, and both replay
  permissions false; the owning shared guard is released. Receipt SHA-256 is
  `c50a7e619015bd5061585adcbdedf6d8f3000e23b10c3e6a67f945e006ac470d`.
  Active runner SHA-256 is
  `11ca8aaef183e76c6eeec1a43e75b00bbc14e4b51650e3122c8f4bbdfdc8799f`;
  normalized SHA-256 is
  `457c6c9c06a70b431a0c352d7707c1d421bbe89f190667eb2eab608cab49c57e`.
  The closure refresh binds shared `device_action_f1_v2.py` SHA-256
  `4e61a7511cc2ed103d1cac4d1afdd2c91d6edc41e30d9bc2832229286d9ee290`;
  its intervening P3.18 changes are confined to S22+ overlay selection and do
  not change the S20+ Odin-output classifier used by this runner.
- Policy proportionality and future blockers are audited in
  `docs/reports/S20PLUS_G986N_POLICY_FRICTION_AUDIT_2026-08-14.md`.

## Current Bounded Unit

The S20+-only D0 onboarding inventory completed and proved that it:

1. selects one exact authorized `model:SM_G986N` ADB row;
2. reads only bounded unprivileged identity and normal-health facts;
3. stores raw execution evidence only under `workspace/private/` with serial,
   topology, and boot ID represented by SHA-256 digests;
4. proves that no command was addressed to S22+, A90, or another device; and
5. creates no D1, F1, root, reboot, mode-transition, transfer, or partition
   authority.

The durable onboarding active-intent guard remains present. That D0 is consumed
and must not be replayed. The separately reviewed routine public-property D0
process is active for current direct operator-requested reads under the binding
contract. Its first successful read recorded the exact device's public Samsung
CSC/OMC properties and preserved their KTC/KOO role distinction. The
operator-provided photograph records Download Mode state without creating a
host-connected process.

## Next Bounded Unit

On 2026-08-14 the operator explicitly accepted the possible irreversible Knox
warranty/security-state change from the first custom boot. That decision is
recorded for this exact S20+ bootstrap campaign and unchanged hazard class.
The permanent scope remains boot-only; TWRP, VBMeta, BL, CP, CSC, and all other
partition writes remain excluded.

The next unit is the smallest P1 correction needed before a fresh bootstrap:
absorb the expected Android-to-Download USB re-enumeration inside the same
guarded, freshly approved F1 invocation using causal empty-baseline/arrival and
dispatch-time endpoint pinning. It must not require a second magic confirmation
for an otherwise unchanged target/artifact/session. After host validation and
independent review, perform a fresh connected prepare, obtain its fresh exact
approval, execute the one boot-only Magisk candidate, observe bounded root or
no-proof, and perform the already-authorized mandatory stock-boot rollback.
Candidate replay remains forbidden.

The fresh approved candidate was transferred exactly once and booted the exact
S20+ into healthy rooted Android; the durable late observation proved root in
the Magisk SELinux domain. The predecessor's ctime-only endpoint ambiguity was
closed by the independently reviewed recovery continuation. The fixed stock
boot rollback then transferred exactly once. Final exact-target Android health
proved a changed boot ID and root absence, both replay permissions are false,
S22+/A90 command counts are zero, and the shared guard is released. The
terminal verdict is
`PASS_S20PLUS_G986N_MAGISK_ROOT_PROVEN_STOCK_ROLLBACK_HEALTHY`; private recovery
result SHA-256 is
`f4cad9dcf5c0b147395e48db6b009d6abb3ac8e09c064a0b6e2885e76d53a8db`.
No candidate replay or resident-root promotion occurred.

The operator observed the same first-boot failure and recovery fallback after
both patched and stock boot transfers; factory reset restored normal boot in
both directions. That symmetry leaves the cause unclassified and makes a data-
encryption/metadata/mount transition at least as plausible as a boot-image
mismatch. The reset erased the most useful failure-state evidence. Before any
resident-root attempt, capture bounded recovery logs before resetting and plan
for complete data loss as a likely recovery cost.

The current bounded unit is a separate resident-root F1 design, not a replay
or relaxation of the completed bootstrap run. Its active runner is
`workspace/public/src/scripts/revalidation/s20plus_g986n_magisk_resident_f1.py`
at SHA-256
`226842be1c5a32dd72e4af3f5d4e9936a2d389489ce09f1d904b56e955b99a22`
and normalized SHA-256
`d9a47bbc6627fbfc2f57ee18952c5d9524527c23978873ea541e04c7617c8fdc`.
It binds the same fixed patched boot and stock rollback, permits one candidate
and at most one failure-recovery rollback, and treats healthy exact-target
Magisk root as terminal success with zero rollback. Its fresh approval must
explicitly accept another factory reset and complete data loss. First-boot
failure parks for operator reset; later finalization is read-only and requires
exact identity, changed boot ID, and root proof. Independent review returned
`PASS_GO` and the capability is now `BINDING - ACTIVE`; activation itself
created no resident run or approval.

The first fresh resident run then transferred the fixed patched boot exactly
once. Initial Android observation timed out and parked without replay or
rollback. After operator recovery/factory-reset handling, the read-only
finalizer proved the exact S20+ returned with a changed boot ID and working
Magisk `uid=0(root)`. Terminal verdict is
`PASS_S20PLUS_G986N_MAGISK_RESIDENT_ROOT_HEALTHY`: candidate transfers `1`,
rollback transfers `0`, both replay permissions false, other-target/S22+/A90
command counts zero, and the shared guard released. Private terminal result
SHA-256 is
`14dfeb9bae3567dc20da9719104bceb06bf64d1a14e7880775eeb8826602fdd2`.

An ordinary reviewed Android reboot subsequently returned the exact target to
healthy Android. The routine control resolver closed the pending reboot, and a
fresh bounded read proved Magisk `uid=0(root)` on the first attempt. Magisk
`30.7:MAGISK:R` (`30700`) and `magiskd` remained active, SELinux remained
`Enforcing`, PID 1 remained stock `/system/bin/init` in `u:r:init:s0`, and the
identity remained stable throughout the read. The terminal read-only verdict
is `PASS_S20PLUS_G986N_ROOT_BASELINE_COMPLETED`; no command was addressed to
the concurrently connected S22+.

The host-only native-init architecture review is now recorded in
`docs/plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md`. It selects
a data-only Magisk `late_start` native canary as N1, followed by private
mount/UTS supervisor mechanics, a boot-ramdisk overlay canary, a retained
pre-userspace witness, and only then a global native PID 1. The current kernel
has no PID or user namespace, no veth, and no devtmpfs, so the A90 isolated-
Debian topology and a blind direct-PID1 candidate are not portable.

The next commit-sized unit is H0 implementation of the deterministic N1 module,
static AArch64 canary, no-clobber one-shot evidence format, hostile host tests,
and a draft exact recovery-aware root-data transaction. The current common and
target contracts do not authorize arbitrary `su`, `/data/adb` writes, or a
Magisk module install; no such capability, runner, artifact, approval, staging,
reboot, or device command was created by the design. Persistent Magisk root is
the prerequisite now proved, not itself proof of native init.

That H0 implementation is now complete and recorded in
`docs/reports/S20PLUS_G986N_NATIVE_CANARY_N1_H0_2026-08-15.md`. The tracked C
source SHA-256 is
`e611310eadf992bb1050fd5e35f236d3523e5c04693fd9e2beede1173766791b` and the
deterministic builder SHA-256 is
`2046fc81a3cd71b2f9390cf29387e75b7ede9c0195eb2b30739b87a16c80175f`.
The canonical private output contains a 597,720-byte static AArch64 canary at
SHA-256 `f5ebd70951827f831b2b11bb6eb012e150ef5a198444cc335e15016627e9536c`
and an exact four-member 598,551-byte module ZIP at SHA-256
`207c91293714a22460441c10b9b126530328ce0f2e2f384e8584a85663218e79`.
Two native builds and two ZIP builds were byte-identical, and the QEMU/native
hostile suite passed 13/13. The root-data transaction remains a non-binding,
inactive H0 draft: no install runner, policy activation, approval, staging,
`su`, reboot, or device command was created. The next bounded unit is an
independent H0 review, not a live module install.

A later reproducible-kernel-build unit would still need exact toolchain
acquisition and a demonstrated matching build; the newly recovered embedded
final `.config` removes the configuration-evidence gap but does not itself
prove stock-kernel byte identity.
