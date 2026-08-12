# S20+ G986N Binding Target Contract

Status: **BINDING - D0 ONBOARDING CONSUMED**

This is the binding target contract for the operator-owned Samsung Galaxy S20+
5G `SM-G986N` / `y2q` / `G986NKSS8IYC2`, listed in the binding target registry
in `AGENTS.md`. Its exact one-shot D0 onboarding inventory has been consumed.
The durable onboarding active-intent guard remains present. A separately
reviewed routine D0 public-property process may be activated below without
removing, rotating, or reusing that onboarding guard. The exact routine D1 is
reviewed and active. Bootstrap F1 is suspended for endpoint-session correction
review and grants no current live F1.

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

The binding section above defines five exact D1 setup/control actions and one
exact D0 patched-AP retrieval. It does not activate or imply arbitrary D0 or
D1. Except for the exact bootstrap F1 below, this contract defines no S20+ F1,
resident root, arbitrary flash, non-boot partition recovery, or rollback
capability. Any such work requires a
later exact contract amendment, recovery design, appropriate artifacts,
proportional validation, independent safety review, and fresh authority.
Bootloader-unlocked state and a passing D0/D1 do not grant those capabilities.

## Magisk bootstrap F1

Status: **H0 REVIEW PENDING - ENDPOINT SESSION CORRECTION - NO LIVE F1**

The target-specific bootstrap process is implemented by
`workspace/public/src/scripts/revalidation/s20plus_g986n_magisk_bootstrap_f1.py`.
The Download product/topology correction passed review, but the first approved
execute then failed before candidate intent because it required ephemeral USB
inode/devnum equality across prepare and execution. A proposal to accept any
fresh generic matching Download endpoint was rejected because it could transfer
the approval to another device on the same port. The dormant runner therefore
restores exact prepare-time endpoint-identity equality and no flash correction
is qualified. A future design must prove target continuity in one live session.

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
