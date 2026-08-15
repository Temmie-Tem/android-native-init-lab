# S20+ G986N Binding Target Contract

Status: **BINDING - ROUTINE D0/D1, P0 ABORT, ATTENDED F1, AND ATTENDED R1 ACTIVE**

This is the binding target contract for the operator-owned Samsung Galaxy S20+
5G `SM-G986N` / `y2q` / `G986NKSS8IYC2`, listed in the binding target registry
in `AGENTS.md`. Its exact one-shot D0 onboarding inventory has been consumed.
The durable onboarding active-intent guard remains present. A separately
reviewed routine D0 public-property process may be activated below without
removing, rotating, or reusing that onboarding guard. The exact routine D1 and
attended boot-only F1 and attended native-canary R1 are reviewed and active.
R1 activation creates no run or standing approval; each transaction still
requires fresh exact preparation, its emitted approval, and attendance.

Exact live D0 established model `SM-G986N`, device `y2q`, product `y2qksx`,
firmware incremental `G986NKSS8IYC2`, and fingerprint
`samsung/y2qksx/y2q:13/TP1A.220624.014/G986NKSS8IYC2:user/release-keys`.
Serial, USB topology, and boot ID remain private hashed evidence.

## Inheritance and Isolation

All common invariants and permanent safety boundaries in `AGENTS.md` apply.
This contract cannot relax target isolation, private evidence handling,
boot-only payload scope, rollback availability, no replay, or the forbidden
action list.

- S20+ profiles, evidence, approvals, transports, and recovery identities never
  apply to S22+ or A90, and neither existing target grants authority for S20+.
- Before every connected action, inventory all ADB rows, resolve exactly one
  `model:SM_G986N` row in state `device`, and send target commands only with its
  exact serial selector.
- Hash every ADB serial and USB topology before durable recording. Never put a
  raw serial, IMEI, phone number, PARTUUID, MAC address, or IP address in tracked
  files.
- If no row, more than one matching row, an unauthorized/offline matching
  endpoint, a duplicate serial row, conflicting model/device/product metadata,
  a changed selection, or conflicting property evidence appears, stop that
  invocation. Do not probe another device to resolve ambiguity.
- Every result must report the selected S20+ command count and zero commands to
  S22+, A90, and every other attached target.

## S20+ H0

H0 includes contract and profile design, source review, offline fixtures,
execution-tool tests, and dry runs with device access hidden. H0 grants no ADB,
USB endpoint, Download-mode, Odin, payload, reboot, or other device authority.

## S20+ D0 Onboarding Inventory

The first proposed connected action is the exact bounded read-only onboarding
implemented by
`workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py`.
Its sole purpose is to establish live identity and normal-Android health facts;
it does not establish root, recovery, rollback, or flash readiness.

The onboarding D0 uses only the reviewed `/usr/bin/adb` target and its pinned
canonical realpath and SHA-256. It may:

1. run bounded `adb version` and `adb devices -l` inventory commands;
2. select exactly one authorized `model:SM_G986N` row;
3. run bounded `adb -s <selected> get-devpath`;
4. run the runner's fixed unprivileged read-only property snapshot on only the
   selected serial;
5. bind the snapshot's model/device/product values back to the selected ADB
   metadata; and
6. repeat inventory and the snapshot to prove that target identity stayed
   stable during collection.

The fixed snapshot is limited to public product/build/kernel/SoC properties,
boot-completion and verified-boot state, SELinux mode, and the unprivileged
process identity. It must not request or retain `ro.serialno`, IMEI, telephony,
account, credential, network-address, package-list, user-data, or partition
contents.

D0 must not use `su`, root, `setprop`, service control, device-file creation,
settings mutation, reboot, Download/recovery entry, Odin, block-device access,
payload transfer, or partition access. It has no internal retry. Before its
first connected command it durably creates one private intent and one fixed
active-intent guard. Success, failure, or an interrupted invocation leaves the
guard in place, so connected replay is mechanically refused. Any later D0
requires an H0 audit, new operator direction, and an explicit reviewed guard
rotation; it is not inferred from this authority. A D0 result grants no D1 or
F1 authority.

USB debugging was ADB-verified when the exact selected row was in state
`device`, the fixed snapshot succeeds twice, and the selection remains stable.
The one-shot result is terminal; this paragraph grants no repeat collection.

## S20+ Routine D0 Public-Property Reads

Status: **BINDING - ROUTINE D0 PUBLIC-PROPERTY READS ACTIVE**

The reusable routine D0 is implemented by
`workspace/public/src/scripts/revalidation/s20plus_g986n_routine_d0.py`. It is
separate from the consumed onboarding transaction and does not inspect,
remove, rotate, or bypass the onboarding active-intent guard.

Once activated by the review record below, a current direct operator request
may authorize one invocation of this fixed read-only process. Each invocation:

1. pins the same reviewed `/usr/bin/adb` canonical realpath and SHA-256;
2. inventories all ADB rows and selects exactly one healthy
   `model:SM_G986N` / `device:y2q` / `product:y2qksx` target;
3. reads its USB devpath and one fixed public-property snapshot using the exact
   serial selector;
4. binds model, device, product, and `G986NKSS8IYC2` back to the selected row;
5. repeats global inventory and stops if any row or selection changed; and
6. writes one no-clobber private result or failure receipt.

The fixed snapshot is limited to public model/build identity, normal-Android
boot health, verified-boot state, and Samsung carrier/CSC/OMC properties. It
may classify Korean sales-code aliases as `KOO`, `KTC`, `SKC`, or `LUC`; no
evidence and conflicting evidence remain explicit and must not be guessed.

Routine D0 does not create an active intent because it has no device effect.
A failed read closes that invocation but does not prohibit a later separately
requested routine read. There is no automatic retry or loop. Reuse depends on
this exact runner and contract remaining unchanged and on a current direct
operator request; it is never standing background authority.

The prohibitions in the onboarding D0 apply unchanged: no `su`, root, writes,
settings or property mutation, service control, package inventory, `/efs` or
partition access, payload transfer, reboot, Download/recovery transition,
Odin, D1, or F1. A routine result cannot establish root, recovery, rollback,
firmware-package identity, or flash readiness.

## S20+ Routine Connected Actions

Status: **BINDING - ROUTINE D1 SETUP/CONTROL ACTIVE**

The routine D1 process is implemented only by
`workspace/public/src/scripts/revalidation/s20plus_g986n_routine_actions.py`
under `docs/operations/ROUTINE_CONNECTED_ACTIONS.md`. A current direct operator
request naming one exact action authorizes one invocation under this section.

A fresh direct operator request may name exactly one of these closed actions:

| Action | Exact effect | Terminal meaning |
|---|---|---|
| `install-magisk` | Package Manager installs/replaces the pinned official Magisk v30.7 APK without permission grants | package path verified; no launch or root claim |
| `stage-ap` | atomically claim one fixed `/sdcard/Download` directory and copy the pinned exact stock AP inside it | final device SHA-256 verified |
| `reboot-system` | one exact `adb reboot` | dispatch only; normal health remains pending |
| `enter-download` | one exact `adb reboot download` | dispatch only; Download state remains pending observation |
| `enter-recovery` | one exact `adb reboot recovery` | dispatch only; recovery state remains pending observation |
| `exit-download` | one exact payload-free `odin4 --reboot -d <Download endpoint>` after the attended handoff below | normal Android health required before closure |

### Download-mode normal return

Status: **BINDING - ATTENDED PAYLOAD-FREE DOWNLOAD RETURN ACTIVE**

The exact return helper is
`workspace/public/src/scripts/revalidation/s20plus_g986n_download_exit_d1.py`.
It is a D1 control action and is separate from the boot-only F1 runner. The
operator first disconnects the USB cable while the phone remains in Download
mode and runs `--arm`; the helper requires an empty `odin4 -l` baseline and
records it before any endpoint is accepted. After the operator reconnects the
same attended phone, `--confirm` requires the exact confirmation token
`S20PLUS-G986N-DOWNLOAD-EXIT-CONFIRM`, exactly one Samsung `04e8:685d`
`SM8250` endpoint, one of the two allowlisted paired-controller topology
hashes, and a stable character-device identity. The helper then sends exactly
`/usr/bin/odin4 --reboot -d <endpoint>` once. No `-a`, `-b`, `-c`, `-s`, `-u`,
PIT, archive, or partition payload is accepted.

The Odin executable is pinned to `/usr/bin/odin4`, size `3746744`, SHA-256
`6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`.
Dispatch intent is durable before the command, output is bounded and stored
privately, and any nonzero, timeout, endpoint drift, or post-dispatch
uncertainty retains the shared action guard and forbids replay. The helper
performs bounded exact-target ADB inventory, topology, public-health, and
SELinux checks after return. Only a durable healthy result releases the guard;
`--finalize` performs that read-only health closure and never sends Odin.
This activation grants one fresh attended `exit-download` D1 request at a
time. It grants no root, boot-image, recovery, partition, or F1 authority.

### Patched-AP retrieval

Status: **BINDING - ROUTINE D0 PATCHED-AP RETRIEVAL ACTIVE**

The independently reviewed `retrieve-patched-ap` implementation is present in
the runner's closed live `--action` choices. The current operator request to
bring back the completed file authorizes one invocation of this exact D0
retrieval after its normal exact-target preflight.

The D0 retrieval is limited to exactly one regular file directly under
`/sdcard/Download` matching the closed grammar
`magisk_patched-30700_[A-Za-z0-9_-]{1,64}.tar`. The runner uses a fixed `find`
expression followed by a device-side fixed `LC_ALL=C` extended-regex filter,
so invalid glob matches are never emitted to the host. It rejects zero or
multiple valid matches, requires a size from 1 GiB through 12 GiB, computes the device-side
SHA-256, and performs one `adb pull -a`. It writes only to
`workspace/private/inputs/s20plus_g986n/G986NKSS8IYC2_KTC/patched/`, checks
host free space, compares the pulled size and SHA-256, and publishes with an
atomic no-clobber hard link. Partial files are unique and removed on a handled
failure only when they are exact regular non-symlink files. An unexpected node
or cleanup failure retains the guard and fails closed. It neither deletes nor
modifies the device file.

The fixed routine guard excludes concurrent retrieval/setup/control. A
retrieval has zero device effects; a durable success releases the guard, and a
failure may release it only because no device mutation or control dispatch was
attempted. It reads no other Download name, package data, credential, app-
private path, partition, or block device and creates no root, patch, flash, or
F1 authority.

Routine public reads continue through the separately active D0 runner. A later
normal-health read may close a reboot return, but an absent or late observation
never authorizes resending the reboot or mode-entry command. No setup or
additional control action may start while normal health or the requested mode
remains unresolved.

Every proposed D1 invocation:

1. pins `/usr/bin/adb` to canonical realpath
   `/usr/lib/android-sdk/platform-tools/adb` and SHA-256
   `05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226`;
2. validates every fixed host artifact before device contact;
3. atomically creates the fixed private `active-action.json` guard and writes
   one no-clobber private intent before the first connected command;
4. inventories all ADB rows and selects one healthy exact
   `model:SM_G986N` / `device:y2q` / `product:y2qksx` /
   `G986NKSS8IYC2` target;
5. records only SHA-256 representations of serial, topology, and boot ID;
6. sends the named effect once with no automatic retry; and
7. writes one no-clobber private result or failure receipt.

The two fixed setup inputs are:

- official Magisk v30.7 APK: `11,613,864` bytes, SHA-256
  `e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5`,
  installed only as package `com.topjohnwu.magisk` using exact
  `adb install --no-streaming -r`; and
- exact stock AP
  `AP_G986NKSS8IYC2_G986NKSS8IYC2_MQB93855401_REV00_user_low_ship_MULTI_CERT_meta_OS13.tar.md5`,
  `8,799,989,882` bytes, SHA-256
  `460a414ca8ba0d9fb64aa53de0fc1c1cc87ae75f0d79a1a1496e478bafa08753`.

AP staging requires at least 20 GiB free in shared storage. The runner first
claims the fixed artifact-specific directory
`Codex-S20Plus-IYC2-460a414ca8ba` with one atomic failing-if-present `mkdir`.
It pushes the AP only inside that newly owned directory and verifies its
device-side SHA-256. There is no rename/publish or overwrite operation. A
failure after directory creation starts may leave the directory or file and
retains the active guard; do not replay or delete it without a separately
represented action.

The fixed guard prevents concurrent or later routine setup/control. An
effect-free preflight failure removes it only after a durable failure receipt;
a setup success removes it only after a durable result. Any effect-attempted
failure and every control dispatch retain it. The runner's separate host-only
control finalizer requires durable one-dispatch evidence and a current explicit
operator confirmation matching one of: normal reboot returned, Download
observed/returned, or recovery observed/returned. Only that finalizer clears a
control guard. A missing, malformed, or mismatched guard fails closed.

This routine process never launches Magisk, patches AP, reads package data,
grants permissions, invokes root, changes settings/properties/services, sends
Odin or partition bytes, accesses `/efs` or block devices, or claims Download,
recovery, root, rollback, or flash readiness. F1 and all partition actions
remain undefined.

## Evidence

- Durable raw execution evidence belongs only under
  `workspace/private/runs/s20plus-g986n-d0-inventory/`.
- The result may retain the public model, device codename, build fingerprint,
  firmware/build versions, Android and security-patch versions, kernel/SoC
  identity, verified-boot fields, SELinux mode, and boot-completion state.
- The ADB serial, USB topology, boot ID, complete inventory, and other attached
  serials are recorded only as SHA-256 digests. Raw values remain in memory and
  are never printed or durably written by the runner.
- A public summary may contain only non-private identity and health fields plus
  command counts. S22+, A90, and other-target command counts must be zero.
- Success writes one no-clobber `result.json`. Failure writes one no-clobber
  `failure.json` containing only a hashed failure signature, actual command
  counts, zero-effect assertions, and a stop verdict. Neither path clears the
  durable active-intent guard or retries the command sequence.
- Routine D0 raw evidence belongs only under
  `workspace/private/runs/s20plus-g986n-routine-d0/`. Public summaries may
  retain only the target's public properties, CSC resolution, command counts,
  zero-effect assertions, verdict, and private result SHA-256.

## Arbitrary F1 and non-routine D1 are not defined

The binding section above defines six exact D1 setup/control actions and one
exact D0 patched-AP retrieval. It does not activate or imply arbitrary D0 or
D1. Except for the exact bootstrap F1 below, this contract defines no S20+ F1,
resident root, arbitrary flash, non-boot partition recovery, or rollback
capability. Any such work requires a
later exact contract amendment, recovery design, appropriate artifacts,
proportional validation, independent safety review, and fresh authority.
Bootloader-unlocked state and a passing D0/D1 do not grant those capabilities.

## Magisk bootstrap F1

Status: **BINDING - ATTENDED BOOT-ONLY F1 ACTIVE**

The target-specific bootstrap process is implemented by
`workspace/public/src/scripts/revalidation/s20plus_g986n_magisk_bootstrap_f1.py`.
The Download product/topology correction passed review, but the first approved
execute then failed before candidate intent because it required ephemeral USB
inode/devnum equality across prepare and execution. A proposal to accept any
fresh generic matching Download endpoint was rejected because it could transfer
the approval to another device on the same port.

The current active correction starts prepare only from an exact healthy,
root-absent Android target. It first records an empty Download-endpoint
baseline, then records the exact hashed serial, Android topology, and boot ID in
a durable no-replay intent before one `adb reboot download`. It requires the
exact Download profile and paired-controller topology to appear after that
baseline in the same guarded invocation. Only after that observation does it
bind the observed Download character-device identity and emit an approval.
Execute treats path, endpoint hash, `st_dev`, inode, `st_rdev`, topology, and
USB profile as the stable session identity; mutable `ctime_ns` is observational
only. It refreshes the complete identity immediately before Odin and requires
that exact fresh value at dispatch. A change to any stable field is recorded as
durable
candidate re-enumeration evidence and sends no Odin transfer. It may continue
only through the attended `--confirm-candidate-endpoint` handoff with exact
token `S20PLUS-G986N-CANDIDATE-ENDPOINT-REENUM-CONFIRM`; that handoff observes
the recorded endpoint once, binds it, and permits the sole candidate transfer.
Any further replacement, missing observation, or identity ambiguity fails
closed. Physical recovery remains a separate two-step attended rollback
handoff. This correction passed an independent `PASS_GO` review with no
unresolved finding. `F1_ACTIVE` is true, but activation creates no run
approval; each run still requires a fresh connected prepare, exact approval,
and attendance.

The 2026-08-14 P1 correction additionally permits one exact pre-candidate run
prepared by runner SHA-256
`5200a4bff71f0f8996530497354ddee07c5efbd9c70be5ac7c7f92c77fc4c4d5`
to continue only after a durable runner-rotation receipt is written before
candidate intent. It does not permit a second candidate attempt or a different
path/inode/device/topology/profile.

### Generic pre-candidate abort

Status: **BINDING - ACTIVE**

The `--abort-pre-candidate` path is owned by the existing guarded F1
run; it never creates or bypasses a second shared guard. It is eligible only
after the exact Android-to-Download transition completed and while candidate
intent, candidate result/raw output/observation, endpoint confirmation,
rollback intent/result/raw output, and every partition-transfer receipt remain
absent. It validates the exact prepared target, artifacts, helpers, transition,
and either the current reviewed runner closure or the one reviewed compatible
closure named by the implementation.

If the exact S20+ is already in healthy normal Android, the path performs only
bounded exact-target health reads, requires serial/topology continuity and a
changed boot ID, writes a durable terminal receipt, and releases the owning
guard. If the phone remains in Download mode, a current attended direct request
permits one payload-free `/usr/bin/odin4 --reboot -d <endpoint>` under that same
guard. The endpoint must retain the prepared profile/topology and is pinned
immediately before dispatch. No `-a`, AP, BL, CP, CSC, PIT, archive, or other
payload option is accepted. The payload-free command is no-replay; a later
invocation may only observe exact Android health and finalize it.

The partition-transfer count is always zero. Any candidate/rollback evidence,
foreign or ambiguous endpoint, malformed journal, unhealthy Android return, or
uncertain payload-free dispatch retains the guard and grants no retry or flash
authority. Independent review returned `PASS_GO` with no unresolved finding. A
current direct operator request authorizes one invocation for the exact owning
guarded run; it grants no candidate, rollback, or partition-transfer authority.

The reviewed dormant implementation SHA-256 was
`81ac97471d4155a35cbb2fe98a4c81d98b63da0cd81b1019dd2a91e5806db93b`;
its normalized SHA-256 was
`c8c95150be76e7cde100db23a47a9fc30bc8fb836e1e92a44bcd94771f78c43e`.
Mechanical activation changed only the capability constant and reviewed hash.
The active implementation SHA-256 is
`11ca8aaef183e76c6eeec1a43e75b00bbc14e4b51650e3122c8f4bbdfdc8799f`;
its normalized SHA-256 is
`457c6c9c06a70b431a0c352d7707c1d421bbe89f190667eb2eab608cab49c57e`.
The closure refresh binds shared `device_action_f1_v2.py` SHA-256
`4e61a7511cc2ed103d1cac4d1afdd2c91d6edc41e30d9bc2832229286d9ee290`;
the added P3.18 branches are S22+-specific and leave the S20+ classifier call
surface unchanged.

The current recovery correction is limited to a candidate already transferred
exactly once by the reviewed predecessor runner. Its Odin raw output reports a
completed transfer and the pre/post USB character identity differs only in
`ctime_ns`, while the predecessor conservatively persisted an uncertain
classification and timed out before Android observation. Recovery accepts that
historical state only with the exact predecessor runner receipt, the complete
candidate intent/result/raw/observation journal, and a durable no-replay
recovery-continuation receipt. It then permits one fresh exact Android health
and bounded root observation, records `candidate-late-observation.json`, and
continues directly to the already-mandatory stock boot rollback. It never
replays the candidate. Any stable endpoint field drift, malformed evidence,
target/boot identity mismatch, or rollback uncertainty retains the guard.

The reviewed handoff surface is `--confirm-rollback-mode`. The arm token is
`S20PLUS-G986N-PHYSICAL-ROLLBACK-ARM`; it records the empty baseline and does
not dispatch Odin. The confirm token is
`S20PLUS-G986N-PHYSICAL-ROLLBACK-CONFIRM`; it accepts one exact endpoint once,
binds the physical-handoff evidence, and permits only the stock rollback
transfer. There is no automatic wait or generic endpoint fallback.

The named prior run that completed only the initial Download transition may be
closed once, and only, with `--close-pre-candidate`. It is pinned to binding
`dfb6aab5ebfcc88aa516e0463b79cb5458abf26c54177a7a1f6a6fd9d3e734f4`, requires
the exact six-node transition journal with no candidate/rollback/raw transfer
evidence, and performs a fresh exact Android health/root-absence read. It
requires the exact serial/topology and a changed boot ID after the recorded
Download transition before writing its durable close receipt and releasing the guard. This is a host
repair for that named run, not a retry or standing recovery authority.

The current endpoint-uncertain run has a separate one-shot
`--close-endpoint-uncertain` host repair bound to approval
`9bc9b25e4299126b239541b7808135ea5a55367543b44dc2fa5ba787a60b80d9`. It
requires the exact seven-node journal plus `events/`, the endpoint-uncertain
result, no candidate/rollback/raw evidence, exact serial/topology continuity,
a changed boot ID, and fresh root absence. It writes the durable close receipt
before releasing the guard and never retries endpoint discovery or invokes
Odin.

Status: **PASS_GO - EXACT HOST-ONLY PRE-EFFECT ABANDON ACTIVE**

The exact host-only pre-effect abandon finalizer may close only the named old
prepared run bound to runner SHA-256
`d2447b21b1ab22b4def7ae309220d508e66b9de6064cc5fde702870758322976`
when its directory contains only `prepared.json` and the ordinal-zero prepared
event, with no candidate/rollback intent, raw transfer log, result, or other
evidence. It writes a durable zero-effect abandonment receipt before clearing
the shared guard. Any extra node fails closed.

This is one attended experiment with two fixed private AP files.
Each AP is a deterministic TAR+MD5 archive containing only one canonical
regular member named `boot.img.lz4`. The candidate is `25,835,561` bytes with
SHA-256 `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`;
the stock rollback is `25,671,721` bytes with SHA-256
`48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b`.
No BL, CP, CSC, recovery, vendor_boot, DTBO, VBMeta, super, persist, userdata,
or other partition payload is accepted.

The fixed state machine pins the exact Download endpoint, artifacts, tools,
transition evidence, and reviewed helper closure; accepts one fresh exact
approval for one candidate boot transfer; observes root only on the exact
normal-Android target; and then requires one stock-boot rollback in the same
approval whether root was proved or not. Terminal health requires completed
rollback transfer, exact Android identity and health, and root absence. The
experiment deliberately leaves Magisk non-persistent.

Candidate and rollback intents are durable before their respective Odin
sessions and each transfer has exactly one attempt. Missing or uncertain
outcomes never permit candidate replay; after rollback intent, rollback replay
is also forbidden. The fixed guard remains through any unresolved state and is
removed only after healthy stock return. A Download-mode timeout parks for the
attended physical recovery path. Raw logs and identifiers remain private and
public results report zero commands to S22+, A90, and other targets.

This capability grants no native-init, TWRP, recovery write, arbitrary Odin,
arbitrary artifact, or resident-root authority.

## Magisk resident boot F1

Status: **BINDING - ACTIVE**

The proposed resident process is implemented separately by
`workspace/public/src/scripts/revalidation/s20plus_g986n_magisk_resident_f1.py`.
It reuses the already-qualified exact target, Download transition, Odin
transport, fixed Magisk-patched boot candidate, and fixed stock-boot rollback.
It changes only the terminal policy: a healthy exact-target Android boot with
bounded `uid=0(root)` proof keeps the candidate boot installed instead of
performing the bootstrap runner's mandatory stock rollback.

The fixed target is `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`. Candidate SHA-256 is
`1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`;
failure recovery is limited to the fixed stock boot SHA-256
`48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b`.
Each has one attempt, candidate replay is forbidden, and no non-boot payload is
permitted. Successful resident completion records one candidate transfer,
zero rollback transfers, exact serial/topology continuity, a changed boot ID,
and Magisk root proof before releasing the shared S20+ guard.

The operator-observed first-boot behavior makes a factory reset a likely part
of this exact campaign. A fresh run approval therefore contains the literal
`DATA-RESET-ACCEPTED` hazard acknowledgement and binds it into the prepared
manifest. If Android does not return rooted after the candidate transfer, the
runner parks without rollback or replay. After an operator-performed recovery
factory reset and Android setup/USB authorization, `--finalize-resident`
performs only bounded exact-target health and root reads; it releases the guard
only if the same target returns with a changed boot ID and Magisk root.
The receipt names this only as `late_boot_finalization`; it does not claim that
a factory reset was machine-observed.

If resident root cannot be proved, recovery is an explicit attended two-step
physical Download handoff. The arm step requires an empty Download baseline;
the confirmation step permits exactly one fixed stock-boot transfer. A stock
first-boot reset may likewise be followed only by the read-only
`--finalize-stock` health/root-absence closure. Candidate or rollback outcome
uncertainty never permits replay. `--abort-pre-candidate` is available only
before candidate intent and closes only after exact healthy stock Android and
root absence are observed.

The reviewed dormant runner was 41,140 bytes with SHA-256
`3141fe6eea3fae7844715df3a6b3304e176cd608de446f382d570da643cb19e7`
and normalized SHA-256
`73388d9ba786ae9d73fe577ed5e5e202a1879de99ee5a947b051a0f76a0ebe88`.
Mechanical activation changed only the capability constant and its reviewed
identity. The active 41,139-byte runner SHA-256 is
`226842be1c5a32dd72e4af3f5d4e9936a2d389489ce09f1d904b56e955b99a22`;
its normalized SHA-256 is
`d9a47bbc6627fbfc2f57ee18952c5d9524527c23978873ea541e04c7617c8fdc`.
`RESIDENT_F1_ACTIVE` is true. Activation grants the capability only; it creates
no run, approval, transfer, reset, or recovery action.

If prepare records an initial Download intent but fails before `prepared.json`,
the shared guard deliberately remains unresolved and this capability has no
automatic finalizer for that partial state. It is a conservative stranded
state: do not delete the guard or retry. Return the phone manually and qualify
a separate exact host-only repair before any later run.

Independent review returned `PASS_GO` for the exact dormant closure with no
unresolved finding. Mechanical activation changed only the capability
constant, reviewed identities, registry/status wording, and their exact test
assertions; the post-activation S20+ aggregate passes 155/155. A fresh prepare,
its emitted `DATA-RESET-ACCEPTED` approval, and attendance remain mandatory.

## N1 exact privileged root-data transaction

Status: **PASS_GO - BINDING - ACTIVE CAPABILITY - NO CURRENT RUN OR DEVICE AUTHORITY**

The reviewed active capability is implemented by two exact runners:

- `workspace/public/src/scripts/revalidation/s20plus_g986n_native_canary_r1.py`;
  and
- `workspace/public/src/scripts/revalidation/s20plus_g986n_native_canary_stock_recovery_r1.py`.

Both activation constants are true. This section specializes and activates the
common R1 invariants only for the exact operator-owned `SM-G986N` / `y2q` /
`y2qksx` / `G986NKSS8IYC2` target. Existing resident Magisk root is a
precondition only. It does not itself authorize `su`, `/data/adb` mutation,
module installation, cleanup, reboot, or stock transfer. Activation creates no
run or approval; each use still requires fresh connected preparation, its
emitted exact approval, and operator attendance.

The active root-data runner is 213,525 bytes at SHA-256
`71cb0617d6989ad1bbfce98779796e7cf923c65fb497b67cd4ea93fe9f4253b1`
and normalized SHA-256
`5e29e8659fb493f0b1885cdc8954e11ec8be6fb60e6953e80923da4ed225300c`.
The active stock-recovery runner is 61,312 bytes at SHA-256
`b029afc3d4a899e4d83304773f8405519bacdb02de742de015a52c97689cc2a6`
and normalized SHA-256
`0bb7eab8a87d11758dac20103ede5ac16c5acbdf3cbc3b511cb30842c4f29f2d`.
These values identify the active capability. They do not identify a prepared
run, approval, target session, or device action.

The only proposed payload is the canonical data-only Magisk module ID
`s20plus_native_canary`: ZIP size `598551`, SHA-256
`e06c88c3a1c029658160b974bc5938acc1f89ab68ea9a7d7d7169d5bd51525a2`;
static binary size `597720`, SHA-256
`38e14e6f54374fc98604bdd61e50922ce9bff1c96feae7572221be548902066c`.
The finite persistent root-data surface is exactly the runner-owned state tree
`/data/adb/s20plus-native-init/n1` plus the Magisk-managed module trees
`/data/adb/modules_update/s20plus_native_canary` and
`/data/adb/modules/s20plus_native_canary`. The only staging namespace is the
fixed non-shared shell-private directory
`/data/local/tmp/Codex-S20Plus-N1-e06c88c3a1c0`, claimed direct shell:shell
`0700`; its ZIP and binding are direct shell:shell `0600` regular files with
link count one. No normal shared-storage pathname is part of R1. Paths, module
ID, bytes, and root command strings are constants. Magisk's own source-pinned temporary
installer paths are not caller-selectable and are not terminal owned state.
The CLI allocates its run directory and later accepts only its closed-grammar
`run-id`; no CLI parameter can provide a path,
module/package ID, executable, property, service, mount, credential, or shell
fragment.

Fresh preparation requires exact healthy rooted Android, stable target
identity, Magisk `30.7:MAGISK:R` / `30700`, no canary module or state/stage
namespace, zero pre-existing modules, and an absent `modules_update` tree.
`/data/adb/modules` must be a direct root-owned `0755` directory with exact
top-level count zero. This deliberately narrow zero-module baseline makes the
complete pre-existing module inventory finite; any unrelated module or pending
update rejects preparation instead of requiring a recursive third-party tree
manifest. One approval binds that state, the exact artifacts, three ordinary
reboots, one install, one exact disable marker, staged-input cleanup, and one
stock fallback. Every effect has a durable intent and one attempt; ambiguity
retains the shared S20+ guard and forbids replay.
Preparation prints one closed-schema result containing the allocated run ID and
its exact approval token. If output is lost after the guard is claimed, a
second `--prepare` invocation validates the sole guarded prepared-only journal
and re-emits the same values with zero device commands; it never allocates a
replacement run or approval.

A fixed install-closure probe may report only the ordered labels `magisk`,
`busybox`, and `util_functions`. Expected path/type or individual metadata/hash
read failures use a finite reviewed token vocabulary with raw command stderr
suppressed; all other output is malformed. Because ADB joins remote-shell
arguments without escaping, every fixed root script is shell-quoted as one
`su -c` argument before that join. The closure probe additionally verifies UID
0 inside that same quoted command before reading any path. A classified
incompatibility stops before Magisk version, inventory, guard publication,
staging, or any persistent effect and never grants a preparation retry. The
ADB behavior is pinned by the AOSP
[`client/commandline.cpp`](https://android.googlesource.com/platform/packages/modules/adb/+/7c2fd99d6ec7e0d2d977ba03cecc82375af1baad/client/commandline.cpp)
implementation. The 2026-08-16 preflight incident and its H0 corrections are recorded in
`docs/reports/S20PLUS_G986N_NATIVE_CANARY_R1_PREPARE_INCIDENT_2026-08-16.md`.
Those corrections changed only fixed command framing and failure
classification, not the CLI or authority surface; independent review qualified
each self-blocked candidate before a separate identity-only activation.

Staging and privileged install use distinct intents. Before the install intent
exists, an exact prepared-only run may be declined with zero device writes;
otherwise the only permitted finalizer proves the exact current same target,
healthy root, unchanged zero-module/Magisk baseline, and whether its boot ID is
the prepared or a later changed boot, removes only the exact staged ZIP/binding
or bounded partial regular bytes at those two fixed names if staging began,
records zero install attempts and an absent module, and releases the guard. Once
the install intent exists, the install attempt is consumed and only the disabled-rooted or
stock-recovery branches may close the run.

The ordinary shell transport first binds the host ZIP as a direct regular
link-count-one mode-`0600` input and the runner-created binding as a direct
regular link-count-one mode-`0400` input. It then claims the fixed non-shared stage as an
empty direct shell:shell `0700` directory, pushes only those ZIP and binding bytes,
makes both direct shell:shell `0600`/link-count-one files, and verifies their
exact size and SHA-256. After both pushes and immediately before the install
intent, the runner freshly rebinds the same Android serial/topology/boot,
Magisk version, and exact Magisk/BusyBox/`util_functions.sh` bytes; drift closes
only through the zero-install cleanup path. Immediately before the sink, the
fixed root command revalidates the same directory, exact two-member set,
ownership, modes, link counts, sizes, and hashes, then invokes exactly
`/data/adb/magisk/magisk --install-module` on that private-stage ZIP. Normal
apps and shared-storage writers cannot enter or replace this stage. A bounded
partial stage is removed by the consumed shell cleanup path; installation is
never repeated. A concurrent independently authorized writer with the same
shell UID is outside this lane and is an immediate stop. Because cleanup and
absence checks use the non-root shell owner, the same bounded cleanup remains
available after a stock/root-absent return. The only accepted interrupted-push
modes are the AOSP sync derivations from those bound host inputs: ZIP `0666`
and binding `0444`, plus each normalized completed mode `0600`. Magisk
v30.7's official installer extracts boot-mode modules into
`modules_update`, resets default file modes, and later promotes that directory
at boot, after which the official promotion code removes `modules_update`.
The proposed runner therefore requires that tree absent before install and
after promotion, and performs and verifies one additional
fixed `chmod 0750` only on
`modules_update/s20plus_native_canary/bin/s20plus_native_canary`; this is part
of the same preauthorized root-data effect, not a generic chmod surface. The
source authority is the official v30.7 tag commit
`e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac`, particularly
[`native/src/core/applets.cpp`](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/core/applets.cpp),
[`scripts/util_functions.sh`](https://github.com/topjohnwu/Magisk/blob/v30.7/scripts/util_functions.sh)
and [`native/src/core/scripting.cpp`](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/core/scripting.cpp),
[`native/src/core/module.rs`](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/core/module.rs),
[`native/src/core/bootstages.rs`](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/core/bootstages.rs), and the documented
[`magisk --install-module` interface](https://github.com/topjohnwu/Magisk/blob/v30.7/docs/tools.md).
The native entrypoint redirects installer stderr to `/dev/null` before the
BusyBox shell, so the reviewed exact success grammar correctly requires empty
stderr even though `util_functions.sh` redirects unzip diagnostics to its
stderr. The same native entrypoint sets `umask(0)`: immediately after install,
the newly created `modules_update` parent and active-stub module directory are
therefore exact root-owned mode `0777`, while the update module root and `bin`
are `0755` and its regular payload files are separately mode/hash bound. After
promotion, the exact active module root and `bin` are `0755` and
`modules_update` is absent. Preparation also binds direct regular-file mode/owner/link/size/SHA-256
receipts for the on-device Magisk binary, BusyBox, and `util_functions.sh`, and
execution requires byte-identical receipts. Those receipts prove stable local
installer bytes and version, not upstream provenance by themselves.

Normal PASS requires exact direct directory modes/ownership and exact child
sets for the update, active, state-parent, and state trees; every regular file
has its exact mode, owner, link count, size/hash; then one exact canary result, a second boot with byte-identical
intent/result, the exact module `disable` marker, a third healthy rooted boot
with no canary journal change, unchanged unrelated module inventory, and
no-clobber namespace cleanup of only the two private staged files. The disabled module
and immutable on-device evidence remain; arbitrary module removal is not part
of this capability. Immediately before each reboot intent the runner freshly
rebinds the exact source boot, working root, prepared Magisk/helper bytes, and
the phase-specific module tree. The prepared, first, replay, disabled,
Android-recovery, and stock-terminal return boot IDs form a non-repeating
ordered history; a reused earlier ID is malformed evidence and sends no new
reboot or terminal release.

All host journals use bounded no-follow reads, exact key sets, strict JSON
types, duplicate-key rejection, no-clobber publication, and file/directory
fsync. The R1 owners build each record in an unnamed same-directory inode,
file-fsync it, and publish it with an atomic no-replace link before directory
fsync, so a final name is absent or contains the complete value and never a
partial JSON prefix. A result-write cut after an intent is `uncertain-consumed`: it cannot
authorize replay, but exact partial command evidence and an exact canary
intent-only read remain valid inputs to recovery. A cut after the canary intent
read may fetch and atomically publish only the missing fixed result read; a
result without its preceding intent remains malformed. A partial final
read-only audit may be repeated only as a read and published as one atomic
zero-effect resume receipt whose source-prefix set is exact. A durable branch-specific
`terminal-input.json` precedes cleanup, including the stock branch's exact
transfer classification, health receipt, and pre-cleanup root-absence receipt.
The named terminal finalizer can derive
that input from a complete branch journal, accept a consumed partial cleanup
only after an accessible shell-private staging parent and staged-input-absence proof,
publish a missing terminal, or validate an existing terminal and release its
leftover guard without a device command. Every other terminal publication
repeats current exact target/root and branch-state reads.
The terminal-only path revalidates only the runners/parsers and immutable
journal needed for that terminal: it may release a leftover matching guard or,
after the guard was already released and only CLI output was lost, re-emit the
byte-identical terminal with zero device command. A present foreign guard
rejects. Unrelated missing candidate inputs, ADB, or the unused stock owner
cannot strand a rooted terminal, while the stock owner remains mandatory for a
stock terminal. Stock terminal identity must equal the
durable final-health identity, not merely a self-consistent terminal record.

Canary intent/result evidence is not accepted by semantic JSON equivalence.
The host reconstructs and compares the exact ordered canonical bytes emitted
and re-consumed by the reviewed C canary, including the C parser's INT32,
INT64, and UINT64 limits. Whitespace variants, escaped fixed keys/values, and
out-of-range numeric tokens are malformed even when a generic JSON decoder
would produce the same object.

Recovery is preauthorized by the same approval and does not depend on the
candidate ZIP, builder source, or canary source remaining present after an
install intent. Candidate-only builder loading is confined to fresh prepare;
all recovery CLI entrypoints import, parse, and reach their scoped validator
when that builder is absent. Recovery revalidates the exact root-data runner and shared helper
closure. Before any rooted recovery audit or persistent disable effect it also
re-reads Magisk `30.7:MAGISK:R` / `30700` and the exact prepared on-device
Magisk, BusyBox, and `util_functions.sh` receipts. The stock dispatch branch
additionally revalidates the reviewed stock owner and fixed stock artifact;
after exact transfer completion, its health-only finalizer revalidates the
owner and completed strict journal but does not require the AP bytes to remain
present. When exact rooted Android is available after the
update tree has been promoted on a changed boot, the runner may create only
the canary module's fixed `disable` flag and perform one recovery reboot.
Install uncertainty while the device is still on the prepared pre-promotion
boot is deliberately not normalized by a root command; it proceeds only
through the stock branch. On-device
recovery audits accept only the exact filesystem state classes `binding-only`,
`intent-only`, or `completed`. When `completed` bytes are canonical and
hash-bound but the source boot was not durably observed before a recovery
transition, the terminal uses the distinct `completed-source-unobserved` class
and never claims N1 PASS or observed-source attribution. A completed result may
use the ordinary `completed` terminal class only when it matches the observed
first source boot. The recovery intent binds that canary-source boot separately
from the current disable-source identity, so an exact replay boot can disable
the module without misattributing the immutable first-boot result. Exact
monotonic advance from binding-only or intent-only to
completed during disable is accepted; regression is malformed. Physical
Magisk Safe Mode is not an R1 recovery action. Official v30.7 runs
`disable_modules()` but also changes persistent Magisk database/configuration
state, including disabling Zygisk, while its bootloop bookkeeping is outside
the finite module/state surface bound here. No Safe Mode arm, key sequence,
finalizer, marker mode, or database mutation is authorized. A future lane must
bind and independently review every such persistent side effect before it can
add that recovery path. Submitting the exact
token
`S20PLUS-G986N-NATIVE-CANARY-R1-ROOTED-RECOVERY-UNAVAILABLE-STOCK-HANDOFF`
is the attended operator's explicit assertion that the supported
rooted-Android recovery path is unavailable; it is not a
generic confirmation. Only then may the root-data runner write one exact durable handoff.
That handoff cannot supersede a durable completed rooted recovery proof,
terminal input/result, or cleanup closure;
only the separate stock-recovery runner may consume it. Preparation pins that
owner's exact reviewed size, full SHA-256, and normalized SHA-256; the owner
revalidates the same receipt before use. That runner has no candidate path. It
publishes a durable attended physical-action intent after an empty Download
baseline and before physical entry, with a fixed 300-second arrival deadline,
then publishes a separate exact endpoint-session arrival. An intent-only
reporting cut may observe the current sole endpoint once without refreshing
the baseline, arm, or physical action; the deadline bounds only the initial
attended wait and does not strand that read-only resumption. A legacy
baseline-only record or a different endpoint session fails closed. Direct operator
confirmation binds that arrival, and the owner can transfer exactly once only
the fixed stock boot AP,
size `25671721`, SHA-256
`48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b`.
Terminal stock health requires exact Android, root absence, staged-input
absence/cleanup, and a durable result. Root absence requires rc `127`, empty
stdout, one finite whole-stderr `not found`/`inaccessible or not found`/`no
such file` grammar, raw transcript bytes and hashes, and unchanged exact target
identity; `permission denied` is not absence. Only a completed transfer may
claim stock-boot provenance. Exact healthy/root-absent Android after an
unproved/failed/local-parse stock attempt uses a distinct non-PASS terminal
verdict, `stock-attempt-unproved` recovery class, and
`inactive-under-root-absent-boot` module state. An exact root-absent observation
whose boot ID did not change is recorded as a distinct recovery-pending state,
not as success and not as a malformed factory-reset receipt. A durable health receipt is
resumable evidence, not a standing lease, so terminal publication repeats the
read-only Android/root check. A complete arm/arrival or confirmation reporting
cut may resume without repeating its effect; an arm-only cut is limited to one
current read-only arrival observation without repeating or refreshing the
finite initial wait window. Once rollback intent exists, missing
or partial result evidence is classified
`odin_effect_outcome_unproved_after_intent` and only observation/final-health
continuation is allowed—Odin is never resent. Rollback intent/result JSON is re-read by the stock owner
with duplicate-key rejection and exact typed schemas. A required factory reset is an accepted
recovery cost, not permission for the runner to issue a format command.

Independent review of the common R1 boundary, this section, both dormant
runners, schemas, fixed command literals, artifact and Magisk source closure,
hostile tests, cleanup, stock handoff, and higher-precedence interactions
returned `PASS_GO`. Mechanical activation set only the two capability
constants true, rotated their full/normalized hashes and exact assertions, and
updated the single S20+ registry row without changing either command surface
or another target. Fresh connected preparation, its emitted exact approval,
and operator attendance remain mandatory. No approval or run exists now.
Independent H0 re-review of the exact active identities, activation-only diff,
registry/status wording, and full test closure returned `PASS_GO` with no
unresolved finding.

## Activation and Review Record

The following gates were completed before activation:

1. focused offline tests must cover wrong, missing, unauthorized, duplicated,
   and replaced target rows; snapshot schema failures; raw-identifier leakage;
   output/time bounds; and absence of control, root, transfer, and write paths;
2. one independent safety review inspected this contract, the exact runner,
   its tests, and the `AGENTS.md` registry diff and returned `PASS_GO` with no
   unresolved finding;
3. this status is `BINDING` and exactly one S20+ registry row is present in
   `AGENTS.md`; and
4. the current operator direction must still authorize this exact read-only
   onboarding collection.

This activation authorized only the now-consumed D0 onboarding inventory above.
It does not activate D1 or F1. Independent review of the routine contract,
exact runner, tests, registry transition, and activation wording returned
`PASS_GO` with no unresolved finding on 2026-08-12. The reviewed routine runner
SHA-256 is
`2377e463e1ec4869fd9ba7a5155aeb6c792bdb5b5b969c902a2b0e5a00fda77c`.
The exact S20+ registry process cell is active. The existing onboarding
active-intent guard remains consumed and must not be removed or rotated.

Independent review of the common routine policy, risk-tier and permanent-
boundary wording, this exact target contract, runner, tests, registry
transition, report, and activation wording returned `PASS_GO` with no
unresolved finding on 2026-08-13. The reviewed routine-action runner SHA-256 is
`709a89fb35f643170a72e613105af68816a0a17ee622865f2d7ebdac6442c444`.
The existing onboarding active-intent guard remains consumed and was not
removed or rotated. This activation creates no F1, root, flash, or partition
authority and does not activate any S22+ or A90 action.

Independent review of the patched-AP retrieval closure returned `PASS_GO` with
no unresolved finding on 2026-08-13. The reviewed pre-activation runner SHA-256
was `5361f986811f9283b340c7ee37f2ff6945f3081979d395409201e9b823f51bad`.
The permitted mechanical activation changed only its activation constant and
the named status/hash assertions. The active runner SHA-256 is
`7b1d8989db5ffbf012cbf356e4e1411d5e487e965361b4ea61307a508b17bc72`.
This activation adds only the exact D0 retrieval above and creates no device
write, root, patch, flash, partition, arbitrary user-data, or F1 authority.

Independent review of the exact Magisk bootstrap F1 runner, helpers, target
contract, registry transition, report, goal, tests, no-replay journal,
Download-endpoint pinning, root observation, and mandatory rollback state
machine returned `PASS_GO` with no unresolved finding on 2026-08-13. The
reviewed dormant runner SHA-256 was
`cb0d288a1f699b1958927c3c1307639ac63751d1c6bd5c532d974ee17d6b289b`;
the mechanically activated runner SHA-256 is
`211e001c492930c4490405ace09a6203980bf4092d276dcd018171624a16e887` and
its normalized reviewed identity is
`73e8800248796a542c4d9d63acbfb641302dc12fe79b14d30b23771b6bbfb23b`.
This activation grants only the attended one-shot boot-only candidate plus
mandatory stock rollback described above. It creates no resident-root,
arbitrary artifact/Odin, non-boot partition, S22+, or A90 authority.

Independent review of the Download profile correction returned `PASS_GO` with
no unresolved finding. The reviewed dormant runner SHA-256 was
`e3c0e3236d13227fd5321d348f8eb21c3f9b67d6ab7572a405735e2043c94edd`;
the corrected active runner SHA-256 is
`d2447b21b1ab22b4def7ae309220d508e66b9de6064cc5fde702870758322976`,
with normalized reviewed identity
`f85505049b899be56df0e79b95092c13afd8deaa885befce03c8e0736d1b4407`.
Only product `SM8250` and the two exact paired-controller topology hashes were
added to the Download profile; raw topology remains private. All prior target,
artifact, journal, endpoint-identity, no-replay, and mandatory rollback rules
remain unchanged.

Those two bootstrap activation records are historical and were suspended after
the first approved execute exposed the pre-effect endpoint-session defect. The
old prepared run was closed only by the independently reviewed zero-effect
abandon finalizer. The current single-session correction is active at runner
SHA-256 `fe86f61166a7f719678ca74431abb0de4f1638ead514289f973601f5b47c4cda`
and normalized SHA-256
`6ceec9037dad1e486450a7fc1085aeb5e527b1e3d1ec7420ac6aa23f03bb823e`.
It has independent `PASS_GO`; `F1_ACTIVE` is true and the registry grants only
this attended boot-only F1 authority. One later run reached pre-candidate state
with zero partition transfers and was closed through the active P0 Android
health-only branch; its owning shared guard was released after the durable
terminal receipt, as recorded in the current goal.

Independent review of the payload-free Download return helper returned
`PASS_GO` with no unresolved finding on 2026-08-14. The reviewed runner
SHA-256 is
`c00558393235b82e50b8df833fd97064801c3f297f1ce067cefcee27332a2bb6`.
The activation adds only the exact attended `exit-download` D1 action above;
it creates no current run, approval, root, boot-image, recovery, partition, or
F1 authority.
