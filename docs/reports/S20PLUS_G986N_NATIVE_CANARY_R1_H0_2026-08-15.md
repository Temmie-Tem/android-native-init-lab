# S20+ G986N Native Canary R1 H0 Report

Date: 2026-08-15

Target: operator-owned `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2` only

Status: **PASS_GO - ACTIVE CAPABILITY - NO CURRENT RUN OR DEVICE AUTHORITY**

## Outcome

The selected post-N1 unit is implemented as one exact
privileged root-data transaction and one separately owned stock-boot recovery
path. Mechanical activation changed no device. Both activation constants are
true, but activation created no run, approval, connected preparation, or
device command. Fresh preparation and attended approval remain mandatory.

The proposed normal transaction is fixed to:

- Magisk `30.7:MAGISK:R` / code `30700`;
- module ID `s20plus_native_canary`;
- one 598,551-byte data-only module ZIP at SHA-256
  `e06c88c3a1c029658160b974bc5938acc1f89ab68ea9a7d7d7169d5bd51525a2`;
- one 597,720-byte static binary at SHA-256
  `38e14e6f54374fc98604bdd61e50922ce9bff1c96feae7572221be548902066c`;
- `/data/adb/s20plus-native-init/n1`, the two fixed Magisk-managed canary
  module trees, and the single owned staging directory
  `/data/local/tmp/Codex-S20Plus-N1-e06c88c3a1c0`, direct shell:shell `0700`
  with exactly two direct shell:shell `0600` members; no normal shared-storage
  pathname is used;
- one install, three ordinary reboots, one exact disable marker, bounded
  read-only observations, exact staged-input cleanup, and no caller-supplied
  path or shell input; and
- one separately owned, one-shot stock `boot` fallback at SHA-256
  `48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b`.

This is not generic `su` authority, module maintenance, partition access, or
authority for another target. The S22+ and A90 registry rows are unchanged.

## Official Magisk closure

Only official Magisk v30.7 material was used to derive the module operation:

- the v30.7
  [`magisk --install-module ZIP` interface](https://github.com/topjohnwu/Magisk/blob/v30.7/docs/tools.md);
- the v30.7
  [`install_module` implementation](https://github.com/topjohnwu/Magisk/blob/v30.7/scripts/util_functions.sh),
  reviewed at tag commit
  `e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac`;
- the native [`install_module` entrypoint](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/core/scripting.cpp)
  and native [`umask(0)` applet entrypoint](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/core/applets.cpp),
  and module promotion/Safe Mode implementation in
  [`module.rs`](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/core/module.rs),
  including the boot-stage order in
  [`bootstages.rs`](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/core/bootstages.rs); and
- the official [module developer guide](https://topjohnwu.github.io/Magisk/guides.html)
  and [Safe Mode FAQ](https://topjohnwu.github.io/Magisk/faq.html).

The source shows that boot-mode installation extracts to `modules_update`,
applies default file modes, creates the active update stub, and removes the
update root after promotion. Because the native applet sets `umask(0)`, the
exact post-install phase has a root-owned mode-`0777` `modules_update` parent
and active-stub module directory, mode-`0755` update module root/`bin`, and
separately bound regular files. Promotion replaces the stub with the `0755`
update module and removes `modules_update`. The native CLI entrypoint also redirects stderr
to `/dev/null` before the installer shell, which is why the exact reviewed
success transcript has empty stderr even though the shell routes unzip output
there. Therefore the
runner calls the fixed absolute Magisk binary, validates the exact official
success transcript, applies `0750` only to the one pinned canary binary, and
then audits the full expected update and active-stub trees before reboot.
Prepare-time and execute-time regular-file receipts bind the local Magisk,
BusyBox, and `util_functions.sh` mode/owner/link/size/SHA-256. They prove stable
local bytes and version, not independent upstream provenance.

The payload never enters normal shared user storage. Host preflight binds the
ZIP as direct regular/link-count-one mode `0600` and the generated binding as
direct regular/link-count-one mode `0400` before any stage command. The shell transport first
claims the fixed `/data/local/tmp` child as an empty direct shell:shell `0700`
directory, then pushes exactly two direct shell:shell `0600`, link-count-one
files and verifies their sizes and hashes. Immediately before Magisk, the root
command independently revalidates the directory and exact two-member set,
ownership, modes, links, sizes, and hashes. Normal apps and shared-storage
writers cannot enter or replace this private stage; a bounded interrupted
stage is removed by exact no-replay shell cleanup, including after a
stock/root-absent return. A concurrent independently authorized writer with the
same shell UID is outside the lane and is an immediate stop. The partial-file
mode grammar follows AOSP
[`file_sync_service.cpp`](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/aml_mpr_331311080/daemon/file_sync_service.cpp)
and its matching
[`file_sync_client.cpp`](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/aml_mpr_331311080/client/file_sync_client.cpp):
ADB sync copies owner permission bits to group/other and applies that mode
before data writes, so the bound host `0600` ZIP may be `0666` and the bound
`0400` binding may be `0444` until the post-push fixed `0600` normalization.
No other host or interrupted-push mode is accepted.

## State and recovery design

Preparation binds exact healthy rooted Android, boot identity, Magisk version,
a deliberately empty pre-existing module inventory, absent `modules_update`, clean canary
namespaces, artifact receipts, runner/helper receipts, and the stock fallback.
This zero-module precondition makes the complete unrelated state finite and
rejects any third-party module rather than incompletely hashing only its name.
Staging and privileged installation have separate intents. An exact
prepared-only run may be declined with zero device writes. A cut after staging
but before the install intent permits only fresh exact-current same-target
health/root, unchanged zero-module/Magisk validation, and exact staged cleanup
or read-only absence, and closes with zero install attempts. The terminal
records whether that target is still on the prepared boot or a later changed
boot; post-stage identity/helper drift never falls through to install. Every
staging/install/reboot/disable/cleanup or transfer effect has durable
one-shot evidence before dispatch. An intent or uncertain result consumes that
effect; replay is false.

Preparation emits the allocated run ID and exact approval token in one closed
schema. A lost stdout after durable guard publication is recovered by
validating the sole prepared-only guarded journal and re-emitting those same
values with zero device work.

Strict typed JSON rejects duplicate authority keys and bool/integer or
number/string substitution. A bounded raw/result publication cut is recorded
as `uncertain-consumed` recovery-only evidence. A canary intent read without
its result is likewise not success, but may read and atomically publish only
that missing result; a result without its preceding intent is malformed. A
partial final read-only audit is re-observed only as a read and captured in one
atomic zero-effect resume receipt. The canary result must also be byte-for-byte the ordered canonical
JSON emitted and re-consumed by the C implementation; whitespace/escape
equivalents and values beyond the C INT32/INT64/UINT64 bounds are rejected.
R1 journal JSON and raw receipts are file-fsynced in unnamed same-directory
inodes and atomically linked no-replace to final names, so write/fsync/close
cuts cannot expose a partial final value.
Contiguous reboot evidence binds each prior boot to the previous durable
observation. A fresh exact target/root/helper/phase-state read precedes every
reboot intent, and the prepared plus all normal, Android-recovery, or stock
terminal returned boot IDs must be pairwise distinct rather than merely
adjacent-different.

Canonical completed bytes that were not bound to a durably observed source
boot close only as `completed-source-unobserved`, never as N1 PASS. Exact
recovery evidence records the canary-source boot separately from the current
disable-source boot, so recovery from the replay boot retains first-boot result
attribution without conflating the two identities. Exact
monotonic state advancement during disable is accepted; regression is rejected.
Guard-release-only finalization does not reopen unused ADB/candidate/stock-owner
inputs for a rooted terminal, while the stock terminal still pins its owner and
must carry the same identity as its durable final-health receipt.

Normal PASS requires:

1. exact first-boot native intent/result;
2. a second boot proving byte-identical one-shot evidence;
3. the exact module `disable` marker;
4. a third healthy rooted boot with unchanged evidence and unrelated module
   inventory; and
5. removal of only the two owned private-stage files; after a consumed partial
   stage write the same cleanup accepts only bounded direct shell-owned regular
   bytes at those fixed names and rejects every extra/indirect node.

Recovery is part of the same future approval:

- exact rooted Android after promotion may create only the fixed disable
  marker and reboot; a prepared-boot/pre-promotion install uncertainty is
  limited to stock recovery;
- physical Magisk Safe Mode is excluded. Official v30.7 not only creates module
  disable markers; `bootstages.rs` also changes persistent Magisk
  database/configuration state, including disabling Zygisk, outside this
  finite state/module surface. There is no Safe Mode arm, key-sequence,
  finalizer, or database-mutation authority; and
- the root-data owner can issue only a durable stock handoff after the operator
  submits
  `S20PLUS-G986N-NATIVE-CANARY-R1-ROOTED-RECOVERY-UNAVAILABLE-STOCK-HANDOFF`;
  that exact token is the attended assertion that rooted Android recovery is
  unavailable, not a generic confirmation. It cannot replace a completed
  normal/Android rooted recovery proof. The separate
  recovery owner records an exact arm intent after the empty Download baseline
  and before physical entry, gives the initial attended wait one fixed
  300-second arrival window,
  records the exact endpoint session separately, then requires direct attended
  confirmation. An arm-only cut performs only one current endpoint observation
  without refreshing the arm, baseline, or physical entry; legacy baseline-only
  and different-session states fail closed. The owner has no
  candidate path and can send the fixed stock boot artifact once. Ambiguity
  retains the shared guard and forbids replay.

Rooted-Android recovery revalidates only the frozen runner/helper closure it
needs, not candidate ZIP/build inputs that may legitimately be
gone after installation. Candidate-builder import is lazy and prepare-only;
all rooted and stock recovery CLI entrypoints still import, parse, and reach
their scoped recovery validator when that source is absent. Immediately before rooted recovery use they re-read
the prepared Magisk version plus exact Magisk, BusyBox, and
`util_functions.sh` receipts. The stock owner additionally revalidates its exact
reviewed full/normalized identity and the fixed stock artifact before
dispatch. Completed stock transfer can resume health-only finalization without
replay or reopening the AP. If rollback intent exists but its result is missing
or partial, the owner records `odin_effect_outcome_unproved_after_intent` and
permits only observation/final-health continuation, never another Odin call;
strict duplicate-free typed rollback evidence and final stock
Android, prepared serial/topology, changed boot, and root absence are persisted
before guard release. A missing/partial transfer receipt may close only with a
truthful root-absent-after-consumed-attempt terminal; it never claims stock boot
provenance unless the transfer completion evidence is exact.

Both rooted and stock terminals use a durable branch-specific terminal input
before cleanup. The stock input binds its transfer classification, exact health
receipt, and pre-cleanup root-absence receipt. The rooted named
finalizer derives missing input only from a complete branch journal, never
replays a consumed cleanup, requires the shell-private staging parent to be
accessible before calling the fixed stage path absent, and can publish a
missing terminal, release a guard left after an already durable terminal, or
re-emit the byte-identical terminal after the guard was already released and
only CLI output was lost. A present foreign guard rejects. Except for those
terminal-only cuts, it repeats current exact Android/root and branch-state reads. The stock owner
similarly treats prior health as resumable evidence rather than a lease; it
rechecks current Android and an exact rc-127/empty-stdout/finite whole-raw-`not found`
root-absence transcript. Rooted guard-only release does not reopen unused
ADB/candidate/stock-owner inputs; stock guard-only release still pins the stock
owner and requires terminal identity to equal durable final-health identity.
`permission denied` is rejected.

Factory reset and complete data loss are accepted possible operator recovery
costs; neither runner contains a reset or format command.

## Public closure

Execution-critical public files:

- `AGENTS.md`;
- `docs/operations/DEVICE_ACTION_RISK_TIERS.md`;
- `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md`;
- `workspace/public/src/scripts/revalidation/s20plus_g986n_native_canary_r1.py`;
- `workspace/public/src/scripts/revalidation/s20plus_g986n_native_canary_stock_recovery_r1.py`;
- `tests/test_s20plus_g986n_native_canary_r1.py`; and
- this report, the phased design, draft disposition, and `GOAL_S20PLUS.md`.

The active reviewed identities are:

- root-data runner: 212,818 bytes, SHA-256
  `536cb88c67ddd378c511b3e6c659433009b68a5f2d9b767f7e41afdcf6a567a3`,
  normalized
  `83ea1116e17ba1551633d9e4b73008f512b83764957f6bcc9bfd84f79e2479aa`;
- stock-recovery runner: 61,312 bytes, SHA-256
  `b029afc3d4a899e4d83304773f8405519bacdb02de742de015a52c97689cc2a6`,
  normalized
  `0bb7eab8a87d11758dac20103ede5ac16c5acbdf3cbc3b511cb30842c4f29f2d`;
  and
- focused active/hostile tests: 114/114 PASS; exact eight-module S20+
  aggregate: 276/276 PASS.

The 2026-08-15 changed-closure audit corrected five material boundaries before
the initial activation: recovery entrypoints no longer import candidate-only
builder code; stock Download attribution uses a finite arm/arrival session;
the root sink consumes a verified shell-private stage rather than normal
shared storage; a post-Odin reporting cut is observation-only and never
replays transfer; and stock cleanup follows its durable branch-specific
terminal input. Independent re-review returned `PASS_GO` for root runner
SHA-256 `c683a5cb5e230996cce439e6f2e0c5ebd02bda152e44fa9944eb74fcc41145c8`
(normalized `61b32d82ebf3a14db5a236d7286f2d6fb5764d04372152549100a48f2f224fe7`),
the unchanged stock owner above, and the then-current 112/112 focused and
274/274 aggregate closure.

The 2026-08-16 prepare incident exposed a separate observability defect in the
fixed Magisk closure command. Its reviewed hotfix changes that command's
internal error handling to the finite classifier described in the incident
report; it adds no CLI action, caller input, path, root authority, or persistent
effect. Independent H0 review qualified the self-blocked candidate at full
SHA-256 `51a210748b538ecb53f1a468e68f6a0e700c2b9bc86b040a73d97f9e1a45e3c5`.
The subsequent mechanical identity-only rotation produced the current active
root identity above, and post-activation review accepted the 114/114 focused
and 276/276 aggregate closure.

No private artifact or device evidence is included in this tracked report.

## Activation record and boundary

On 2026-08-15, independent `PASS_GO` qualified the exact dormant closure and
its mechanical initial activation changed only capability constants, reviewed
identities, registry/status wording, and assertions. On 2026-08-16, the
separately reviewed finite-classifier hotfix changed fixed command logic but
not its surface or authority; its later activation changed only the normalized
identity constant and matching records. Neither activation touched a device or
created a run or standing approval. Post-hotfix activation review returned
`PASS_GO` for the exact current identities above, target isolation, and the
114/114 focused plus 276/276 aggregate test closure. Only a fresh connected
prepare may emit an approval for one attended run.
