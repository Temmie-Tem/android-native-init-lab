# S20+ G986N Native Canary R1 H0 Report

Date: 2026-08-15

Target: operator-owned `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2` only

Status: **ACTIVE R1 CAPABILITY; LAST N1 RUN RECOVERED INTENT-ONLY/DISABLED ROOTED HEALTHY**

## Outcome

The selected post-N1 unit is implemented as one exact
privileged root-data transaction and one separately owned stock-boot recovery
path. Mechanical activation changed no device. Both activation constants are
true. Activation itself created no run, approval, connected preparation, or
device command. A later attended run consumed its sole install attempt, then
closed through the reviewed no-install continuation and preauthorized
Android-root disable recovery. Its exact terminal is rooted healthy with the
canary `intent-only`, module disabled, staged inputs absent, stock attempts
zero, and the shared guard released. Fresh preparation and attended approval
remain mandatory for every new transaction.

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

## Install transcript incident and bounded continuation outcome

The run initially had one exact install intent and one complete command result
with rc zero and empty stderr. At that stop no post-install audit or reboot
intent had been published. Its private stdout SHA-256 is
`a8127967c1e9ffbc12d32f6630ed0bdbc4c12237c009a4bf727e7348d0e7e5eb`.
The old grammar omitted the source-defined first line
`- Device is system-as-root`; official Magisk v30.7 emits it in
`mount_partitions()` before the module title and extraction output. The
installation is therefore consumed and successful as a command result, but N1
PASS remains unproved until the module tree and reboot sequence are observed.
Installation replay is forbidden.

The independently reviewed candidate added only
`--resume-after-install --run-id <closed-id>`. It binds exact predecessor
binding SHA-256
`89098a4190d3ab2a85ddf0efd8b12ffdd800f79cf4146b8302f8e23832cf1845`
and the predecessor root-runner receipt. Before connected reads it atomically
publishes an exact typed continuation receipt binding predecessor/current
runner identities and install result/stdout hashes, with zero device effects
and `install_replay_permitted=false`. It accepts no approval, artifact path, or
command input; it never stages or installs. It requires the same prepared
serial/topology/boot before privileged reads, rechecks exact Magisk/helper
bytes, and resumes only at the existing read-only post-install audit. All later
cuts must revalidate that continuation receipt and use the ordinary no-replay
recovery state machine.

The candidate is 223,363 bytes at SHA-256
`e2725e77dc552384eedc669902e35790af940d15fc786240171b50cc608ea420`,
normalized SHA-256
`39cdf9eda1eb4fa8240bab49c1a45fdf54b63431908fd6721cdde2453e77544c`.
Focused validation has 118 logic passes plus the expected stale-identity
failure before activation. Independent review returned `PASS_GO`; the separate
identity-only rotation produced the active 223,363-byte runner at SHA-256
`63e58f99b06275ed0d1eeacc5d87dbb7fdc1a9f471fcd7645f447345b23a3b52`
with the same normalized SHA-256. Post-rotation focused validation is 119/119
and the canonical eight-module S20+ aggregate is 281/281. Full details are in
`docs/reports/S20PLUS_G986N_NATIVE_CANARY_R1_INSTALL_TRANSCRIPT_INCIDENT_2026-08-16.md`.

The active continuation then passed the separate post-install audit and issued
the first reboot exactly once. The canary produced its canonical intent but no
result, so the runner stopped without replay. Android-root recovery created the
single disable marker and performed one recovery reboot; final evidence proves
the same exact target rooted healthy, state `intent-only`, module disabled,
staged input absent, and stock/Odin attempts zero. Both install and reboot
replay remain false, and the shared guard is released. Terminal verdict is
`RECOVERED_S20PLUS_G986N_NATIVE_CANARY_N1_DISABLED_ROOTED_HEALTHY`; private
terminal result SHA-256 is
`146230b0744b956bfa03c5088b7022ffe89be4d2596f0ebd3bb600eb495c7d66`.

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

- root-data runner: 223,363 bytes, SHA-256
  `63e58f99b06275ed0d1eeacc5d87dbb7fdc1a9f471fcd7645f447345b23a3b52`,
  normalized
  `39cdf9eda1eb4fa8240bab49c1a45fdf54b63431908fd6721cdde2453e77544c`;
- stock-recovery runner: 61,312 bytes, SHA-256
  `b029afc3d4a899e4d83304773f8405519bacdb02de742de015a52c97689cc2a6`,
  normalized
  `0bb7eab8a87d11758dac20103ede5ac16c5acbdf3cbc3b511cb30842c4f29f2d`;
  and
- focused active/hostile tests: 119/119 PASS; exact eight-module S20+
  aggregate: 281/281 PASS.

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
The subsequent mechanical identity-only rotation produced root identity
`536cb88c67ddd378c511b3e6c659433009b68a5f2d9b767f7e41afdcf6a567a3`
(normalized `83ea1116e17ba1551633d9e4b73008f512b83764957f6bcc9bfd84f79e2479aa`),
and post-activation review accepted the 114/114 focused and 276/276 aggregate
closure.

The first classified live retry then exposed a separate command-framing defect:
ADB joins the arguments after `shell` without escaping, while the runner passed
the multiline fixed script as a raw argument. The resulting `absent` records
did not prove that Magisk files were missing. The reviewed correction quotes
the entire fixed script before ADB's join and requires UID 0 in the same
closure command. Independent review returned `PASS_GO` for self-blocked runner
SHA-256 `66fcf659b2025a477bc19336c746bb745774258f8395b860038b0f906b37d274`
(normalized `5e29e8659fb493f0b1885cdc8954e11ec8be6fb60e6953e80923da4ed225300c`).
Its mechanical identity-only rotation produced the then-active 213,525-byte
identity `71cb0617d6989ad1bbfce98779796e7cf923c65fb497b67cd4ea93fe9f4253b1`
with the same `5e29e8659fb493f0b1885cdc8954e11ec8be6fb60e6953e80923da4ed225300c`
normalized hash; focused and aggregate closure reached 115/115 and 277/277.

The next exact preparation reached the now-valid quoted root probe and reported
only `util_functions=unsafe-metadata`. Official Magisk v30.7 commit
`e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac` applies recursive `0755` to
the persistent `MAGISKBIN` tree in both flash and app direct-install paths;
the runner had incorrectly admitted only non-executable modes for
`util_functions.sh`. Independent review returned `PASS_GO` for self-blocked
candidate SHA-256
`6905a92a7dd2eb7a3d64b3dc5055cf7cd297c43077a682eeea0f0fadbb1639c4`
(normalized
`6c64c8763fd0ab68fe2b88721f6d6d1f0f9c28f96b4595f028c0af7c143194ad`).
The mechanical identity-only rotation produced the then-active 213,403-byte
identity `35dfc7557c5c9e9b3e62d4865e81122572c57d0464997f4e2a35904a0b15432f`
with the same normalized hash; the CLI, fixed root script, effect budget, and
recovery surface were unchanged.

The install-transcript continuation candidate above then received independent
`PASS_GO` at full SHA-256
`e2725e77dc552384eedc669902e35790af940d15fc786240171b50cc608ea420`.
Its identity-only rotation produced the current active root-data identity
listed in Public closure. The active CLI adds only the closed run-ID
continuation and cannot stage or reinstall.

No private artifact or device evidence is included in this tracked report.

## Activation record and boundary

On 2026-08-15, independent `PASS_GO` qualified the exact dormant closure and
its mechanical initial activation changed only capability constants, reviewed
identities, registry/status wording, and assertions. On 2026-08-16, separately
reviewed finite-classifier and remote-shell-framing hotfixes changed fixed
command logic but not its surface or authority. The later metadata correction
changed only the source-derived `util_functions.sh` mode expectation and shared
validator table; each later activation changed only the normalized identity
constant and matching records. No activation
touched a device or created a run or standing approval. Post-hotfix activation
review returned `PASS_GO` for the exact current identities above, target
isolation, and the 119/119 focused plus 281/281 aggregate test closure. Only a
fresh connected prepare may emit an approval for one attended run.
