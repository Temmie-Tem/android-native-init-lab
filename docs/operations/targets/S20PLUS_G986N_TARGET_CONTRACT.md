# S20+ G986N Binding Target Contract

Status: **BINDING - ROUTINE D0/D1, ATTENDED ROOT-HEALTH AND TWRP BOOT-IDENTITY D0, P0 ABORT, ATTENDED F1/F2, AND ATTENDED R1 ACTIVE**

This is the binding target contract for the operator-owned Samsung Galaxy S20+
5G `SM-G986N` / `y2q` / `G986NKSS8IYC2`, listed in the binding target registry
in `AGENTS.md`. Its exact one-shot D0 onboarding inventory has been consumed.
The durable onboarding active-intent guard remains present. A separately
reviewed routine D0 public-property process may be activated below without
removing, rotating, or reusing that onboarding guard. The exact routine D1 and
attended boot-only F1 and attended native-canary R1 are reviewed and active.
The exact attended root-health and TWRP boot-identity D0 lanes are active.
Recovery-canary T0 and TWRP
T1 owners retain only their consumed-candidate journals and terminal paths;
TWRP T2 recovery is retained and its candidate is consumed; its owner remains
active only for journal validation and terminal re-emission.
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

This onboarding D0 must not use `su`, root, `setprop`, service control, device-file creation,
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

## S20+ Attended Root-Health D0

Status: **BINDING - ATTENDED ROOT-HEALTH D0 ACTIVE**

This is a separate target-specific capability for one attended, fixed,
read-only root-health snapshot. It is not part of routine public-property D0,
the autonomous-research session, or the active N1 R1 capability. Existing
resident Magisk root is a precondition only and grants no generic `su`
authority. Only the fixed read below is active; an R1 preparation, approval,
result, or recovery journal cannot
authorize this D0. The common invariants and permanent boundaries in
`AGENTS.md` and the target-isolation rules above retain higher precedence; any
conflict stops the invocation.

The active implementation path is
`workspace/public/src/scripts/revalidation/s20plus_g986n_attended_root_health_d0.py`.
Its activation constant is `ATTENDED_ROOT_HEALTH_D0_ACTIVE = True`. Its only
CLI modes are host-only `--render-plan` and one `--connected` entrypoint. The
constant is repeated at the CLI, execution-owner, and backend boundaries.

Under this reviewed activation,
one fresh direct operator request may authorize exactly one invocation with
these six bounded host commands in order:

1. one global ADB inventory;
2. one selected-target `get-devpath`;
3. one fixed unprivileged pre-snapshot whose exact keys are `model`, `device`,
   `product_name`, `incremental`, `boot_completed`, `bootanim`, `selinux`, and
   `boot_id`;
4. one selected-target `shell su -c` invocation of the fixed root-health
   literal defined below;
5. the byte-identical fixed unprivileged post-snapshot; and
6. one final global ADB inventory.

The complete non-root command closure is fixed as follows. Both inventory
commands use exactly `[adb, devices, -l]`; `get-devpath` uses exactly
`[adb, -s, <internally-selected-serial>, get-devpath]`. Those commands have a
10-second timeout, a 32-KiB combined-output bound, rc zero, and empty stderr.
Each public snapshot uses exactly
`[adb, -s, <internally-selected-serial>, exec-out, sh, -c,
<public-snapshot-script>]`, where the final host argv element is the raw fixed
script and ADB 34.0.5 applies its own `escape_arg()` exactly once. It has a
20-second timeout, an 8-KiB combined-output bound, rc zero, empty stderr, and
the following complete script bytes including the final newline:

```sh
set -eu
emit_prop() {
    printf '%s=' "$1"
    /system/bin/getprop "$2"
}
emit_prop model ro.product.model
emit_prop device ro.product.device
emit_prop product_name ro.product.name
emit_prop incremental ro.build.version.incremental
emit_prop boot_completed sys.boot_completed
emit_prop bootanim init.svc.bootanim
printf 'selinux='; /system/bin/getenforce
printf 'boot_id='; /system/bin/cat /proc/sys/kernel/random/boot_id
```

Its stdout is exactly eight ordered, LF-terminated `key=value` lines matching
the keys named above; duplicates, extra bytes, CR, NUL, non-UTF-8, or a
malformed boot ID are rejected.

Both inventories must select the same sole healthy
`model:SM_G986N` / `device:y2q` / `product:y2qksx` row. The selected row must
contain exactly one `usb:` metadata token, and it must equal
`usb:<get-devpath>`. The same exact token must remain in the final selected
row while the complete sanitized global inventory remains unchanged. The public snapshots
must bind `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`, completed healthy
Android, enforcing SELinux, and one unchanged current boot. Selection,
devpath, public identity, health, and boot must remain stable across the
root read and final inventory. Any missing, duplicate, unauthorized, changed,
or conflicting row or field stops the invocation without selecting another
device.

The root command is one runner-owned, shell-quoted literal and accepts no
caller text. Its host argv is exactly
`[adb, -s, <internally-selected-serial>, shell, su, -c,
shlex.quote(<root-read-script>)]`. It has a 30-second timeout, a 4-KiB
combined-output bound, rc zero, empty stderr, and the following complete
script bytes including the final newline:

```sh
set -eu
uid=$(/system/bin/id -u)
gid=$(/system/bin/id -g)
context=$(/system/bin/cat /proc/self/attr/current)
magisk_version=$(/data/adb/magisk/magisk -v)
magisk_version_code=$(/data/adb/magisk/magisk -V)
selinux=$(/system/bin/getenforce)
pid1_exe=$(/system/bin/readlink /proc/1/exe)
pid1_context=$(/system/bin/cat /proc/1/attr/current)
printf '%s\n' \
    "uid=$uid" \
    "gid=$gid" \
    "context=$context" \
    "magisk_version=$magisk_version" \
    "magisk_version_code=$magisk_version_code" \
    "selinux=$selinux" \
    "pid1_exe=$pid1_exe" \
    "pid1_context=$pid1_context"
```

Its accepted stdout is exactly these eight ordered lines:

```text
uid=0
gid=0
context=u:r:magisk:s0
magisk_version=30.7:MAGISK:R
magisk_version_code=30700
selinux=Enforcing
pid1_exe=/system/bin/init
pid1_context=u:r:init:s0
```

This proves only that the fixed read observed the expected current root,
Magisk, SELinux, and stock PID-1 health fields. It does not prove native init,
module health, arbitrary root access, recovery, rollback, F1 readiness, or
future root availability. The CLI must never accept a serial, path, shell
fragment, command, executable, property, service, package, module, mount,
credential, callback, or output destination. Generic or interactive `su`, a
caller-selected `su -c`, file-byte extraction, directory enumeration, writes,
deletion, permission or ownership change, settings/property/service mutation,
package action, module action, reboot, mode transition, transfer, Odin, block
access, and partition access are outside this capability.

Private evidence belongs only under
`workspace/private/runs/s20plus-g986n-attended-root-health-d0/` and must use a
runner-allocated no-clobber run directory, bounded no-follow reads, strict
typed parsing, atomic no-replace publication, and file/directory fsync. Raw
serial, devpath, boot ID, and complete inventories must never be persisted;
only their SHA-256 representations may be retained. A success records exactly
two inventory commands, four selected-target commands, and one root command.
A failure records the actual executed prefix bounded by at most two, four, and
one respectively. Both paths record zero device effects, writes, reboots,
transfers, partition operations, and commands to S22+, A90, or every other
target. Failure is terminal for that invocation and never triggers an internal
retry.

The reviewed dormant runner is 39,830 bytes with SHA-256
`89c93b815dda6a5ad80d4e926958cfc0ce9758b563c307d286057647ebe3622b` and
activation-only normalized SHA-256
`86f7d49fc533750e9d641ae1d481fd2603f4b90e20e9051ef5e6a5080464848c`.
The 35,704-byte focused test has SHA-256
`3ebb9d538e73bd69985fa9aa4f2904cad5a3a524aaaba2722b095ce67a07111e`.
The 423-byte public script, its 449-byte quoted shell argument, the 584-byte
root script, and its 594-byte quoted shell argument have SHA-256
`f17aac6c9c946968b18ac91a05c6d8f006fef1857533518495a97d5e71d9813b`,
`0fa4c7d3b01941f467f5ad2da51059f5b7ae5d054267a39fdca2cac878f8e4f9`,
`128ba6294378442b9e2a580086c2a8f6fc2f06afe30e642066f9bca4af314da1`, and
`e5db5a7bb0fb78553e033649bc16496c008b9e5882b88f0c84234c1dede657aa`
respectively. The exact inventory helper remains 21,474 bytes at SHA-256
`3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81`.

Focused validation passed 28/28 and the pinned inventory-helper suite passed
15/15; `py_compile` and scoped `git diff --check` passed. Independent hostile
review of the dormant runner, tests, command framing, target/USB/boot binding,
privacy/evidence owner, policy interaction, and prior review corrections
returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`. This qualifies only the
dormant bytes and creates no live request or authority.

The initial mechanical activation changed the runner boolean from false to true, made its
module help text status-neutral, and rotated the corresponding test
expectations, this section and top-level status, the single
S20+ registry process cell, and the goal/report activation record. The active
runner at that activation was 39,820 bytes with SHA-256
`7967f85dc1418473c66b418cedfc2c15063a141fed2550d040eb122fec04584a`; its
normalized SHA-256 is
`0c4c15a014d181b43f85a00a55d335e6256663969664c95c1adf953049038b91`.
The corresponding 35,922-byte focused test SHA-256 is
`70f43252ba163f854eb21c325a5087c470a7d9305bb114c593266a5457bc3cb7`.
Four existing document-assertion tests changed only the target header and/or
exact S20+ registry-row strings required by this activation:

| Test | Predecessor size / SHA-256 | Active size / SHA-256 |
|---|---|---|
| onboarding D0 | 13,218 / `40875785faf27edc2315f3735b8f200e657c0c1e4ca9fc4743d6d5c73d7ffa9c` | 13,281 / `214ae02ed69023b2096010add91e0b29502976ccece80233925281c152c343d9` |
| routine D0 | 12,332 / `19c2483934327be3e9b6815c853e69768fcca0c07a29f44547e88368c4fa5f9e` | 12,370 / `a713846021822a0f28c1514e4813c3735a10e89397dafb6daaed394d4cd07101` |
| routine actions | 37,204 / `e90eccc5bc7d5980682cdaced7bef3f4cd437b3001a5b2122cfb4f5eca7a7960` | 37,242 / `533255e6a97d18c932f236e2d68e8f25e7223ffee798ee18c4f7216ee574fedc` |
| bootstrap F1 | 96,409 / `e6325fe50fa030f455959d66004d28669df12d3484ad7aa3dfa431c2650af0ac` | 96,447 / `4ec89126082b1da183246397794b5ad5af9cad10dbd4bf2bdba2b764424e1112` |
Post-rotation independent review returned `PASS_GO` with HIGH/MEDIUM/LOW
`0/0/0`; no connected use occurred during qualification.

One 2026-08-31 attended invocation then stopped before root because the public
pre-snapshot had the wrong field count. Host-only analysis proved that the
active runner prequoted the public script before ADB's exec-out path escaped it
again. The failure receipt recorded three host commands, one public snapshot,
zero root commands, and zero device effects; the consumed request was not
replayed. The exact inactive repair qualification passed 21/21 tests and
independent HIGH/MEDIUM/LOW `0/0/0` review. Its two-fragment candidate removes
only the public prequote and rotates the render-plan description; the public
and root scripts remain byte-identical, and the root `adb shell su -c` argument
retains its required `shlex.quote()`.

The corrected active runner is 39,819 bytes at SHA-256
`24f69cc5aa43c70558e3594534ee684db0a038e972d1b0db2f1b8d8446af2d44`;
its activation-normalized SHA-256 is
`afdae9953f6ea93d2d299857f38d93229152e834395783fb12ae3c3df5693668`.
The corrected 35,854-byte focused test SHA-256 is
`7b0029aaf7bf00bd6655cada41fcc2430192bb9bdfbf41dc6a525cce73985615`.
The 423-byte raw public argv produces the exact 456-byte ADB exec service at
SHA-256
`8ff45512fd92c37671396cf1d0abeb5b591dd1cdf37a5ee7bbc489d9f3acdbbf`.
This host-only rotation creates no invocation and no standing approval; a new
direct attended request is still required before the corrected runner may
contact the device.

The activation gates required the exact runner and hostile test identities to be frozen,
focused tests to pass for dormancy, wrong/duplicate/replaced targets,
pre/post/final drift, parser/order/type/output/time bounds, identifier leakage,
no-clobber evidence and zero-effect accounting, and one independent review of
the runner, tests, this section, higher-precedence interactions, and the
mechanical activation-only transition to return `PASS_GO` with no unresolved
finding. The completed mechanical activation changed all and only these
authority atoms together: this section's status,
the runner's activation constant and exact full/normalized identity assertions,
the top-level target-contract status sentence, the single S20+ `AGENTS.md`
registry process cell, the exact test assertions, and the activation/review
record. A partial rotation, stale identity, or an omitted authority atom would
leave the capability inactive. Despite activation, the design request is not
standing live authority: one
new direct operator request and attendance are required for each invocation.
No activation or invocation in this section transfers authority to S22+, A90,
the autonomous lane, R1, or F1.

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
The incident-reviewed recovery-only finalizer may also consume the exact
one-shot result `returncode=0`, `post_state=changed`, and
`RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_EXIT_UNKNOWN`. It revalidates the
original no-payload intent and raw output hashes, sends no Odin command, and
releases the guard only after fresh exact-target normal Android health whose
ADB devpath hash exactly equals the already durable, allowlisted Download
endpoint topology hash. Its
terminal receipt preserves the source verdict and records
`exit_dispatch_proven=false`; it never relabels the uncertain dispatch itself
as proved. Nonzero, absent raw evidence, malformed types, other endpoint states,
or failed health retain the guard.
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
D1. Except for the exact bootstrap F1, resident F1, boot recovery-canary B0 F1,
and the single recovery-canary T0 F2 section immediately below, this contract
defines no S20+ F1/F2, arbitrary flash, non-boot partition recovery, or
rollback capability. Any such work requires a
later exact contract amendment, recovery design, appropriate artifacts,
proportional validation, independent safety review, and fresh authority.
Bootloader-unlocked state and a passing D0/D1 do not grant those capabilities.

## Recovery-canary T0 F2

Status: **BINDING - ATTENDED RECOVERY-CANARY T0 F2 ACTIVE**

This section activates the one S20+-only F2
exception delegated by `AGENTS.md` and
`docs/operations/DEVICE_ACTION_RISK_TIERS.md`. It applies only to the exact
operator-owned `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`. Every other
recovery image, target, partition, path, and command remains forbidden.

The active concrete owner is
`workspace/public/src/scripts/revalidation/s20plus_g986n_recovery_canary_t0_f2.py`,
153,798 bytes at SHA-256
`a91d45e14f4cb82f10a83a8c2bdc38126deb20b9b841918888ec45842ad51e75`
and activation-normalized SHA-256
`82a357b96f5b7cc03868d5c174d70f5b3d66a4aa2525482e14bd862e40d5425b`.
`T0_F2_ACTIVE=true`. Its 54,687-byte focused test is SHA-256
`5ffb49c0836ebff473ef2a09268ee7c60073d418c10477036f7d4a8ceaea6c94`
and passes 44/44; the owner plus earlier T0 model and recovery-digest profile
pass 79/79. Activation creates no run or standing approval; live use still
requires exact fresh preparation, its emitted approval, attendance, and all
current health/recovery gates.

The owner pins the earlier H0 artifact model, fixed recovery-digest profile,
exact S20+ inventory and raw-capture helpers, and the current reviewed B0
target/USB/process-cage primitives. It calls no B0 candidate or rollback
transfer function. Any dependency byte or imported API drift stops. The CLI
accepts only an internally allocated closed-grammar run ID and exact emitted
approval/physical-confirmation tokens; it accepts no serial, endpoint, path,
artifact, partition, shell fragment, command, property, executable, or output
destination.

Its strict journal accepts only the fixed regular-file namespace and exact
typed predecessor graph. Preparation, execution pre-transfer, and either final
health or pre-candidate abort each have a separate one-shot recovery-read
intent. `--resume` first quiesces any candidate/rollback cgroup, rederives a
complete missing result from raw capture where possible, otherwise publishes
unknown without replay, and can consume only an already-bound physical
confirmation/arrival. Fake semantic JSON, an unknown node, a duplicate raw
ordinal, a result without its intent, or a classification not reproduced from
raw bytes stops.

The only candidate is the recovery-only AP at 36,556,841 bytes and SHA-256
`30227458889f1fa99eca192c9b7f8747f168d9e33cc1f407b52ae2b4d298559a`.
Its sole member is `recovery.img.lz4`, 36,547,618 bytes at SHA-256
`7f0e6b53a1036904fd02c5e8c2c014d3112ffb58fc33f9aa9a26c0962af45928`;
the decoded fixed-size recovery image SHA-256 is
`e1297613df576d25cc9391df97dac7cf316fee545f56111e6bc5340cb8ce659b`.
The only rollback is the exact-stock recovery-only AP at 36,608,041 bytes and
SHA-256
`ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157`.
Its sole member is `recovery.img.lz4`, 36,600,544 bytes at SHA-256
`6b962af2fc4fcc424d16ecdcee1793bdd6d4c8dba2e80d35cb21961fcb865923`;
the decoded exact-stock recovery SHA-256 is
`dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e`.
No archive may contain boot, VBMeta, DTBO, BL, CP, CSC, super, userdata,
persist, EFS, misc, or a second member.

Preparation is read-only. Under a future activation, one direct attended
request may acquire the shared S20+ action guard, validate the complete host
closure, select exactly one exact healthy S20+ while permitting but never
addressing foreign ADB rows, and run the fixed root-health plus recovery-digest
profile. `/dev/block/by-name/recovery` must resolve to the H0-derived direct
block node `/dev/block/sda24`, report exactly 82,694,144 bytes, and hash to the
exact stock recovery above. The target serial, topology, current boot, build,
healthy rooted Android, Magisk 30.7/30700, enforcing SELinux, and stock PID 1
are hash-bound around that read. Preparation records an empty Download
baseline and emits one approval beginning
`S20PLUS-G986N-RECOVERY-CANARY-T0-F2-APPROVE:` with a 15-minute expiry. It
sends no reboot, Odin, transfer, or other device effect.

Only the byte-identical approval may start execution. Execution repeats the
exact Android/root/recovery-digest read and requires the same prepared boot,
then durably records the Download intent before one exact selected-target
`adb reboot download`. A missing arrival permits no candidate claim or
transfer; after an attended payload-free/manual Android return, the health-only
`abort-pre-candidate` path may record zero partition attempts and release the
guard. It never sends a return command.

After one newly bound exact Download endpoint arrives, a global no-replace
candidate claim is published before candidate intent. That claim permanently
prevents another run from sending this candidate even if execution cuts before
the local intent. The candidate command is exactly
`/usr/bin/odin4 -a <exact-candidate-AP> -d <bound-USBFS>` with no auto-reboot.
The AP, Odin, and process-cage shell remain open and identity-stable across the
command and are revalidated afterward. Intent precedes the caged bounded raw
capture; descendant quiescence precedes observation or rollback. Missing,
partial, timed-out, locally rejected, or ambiguous output consumes the attempt
and never permits replay.

Only a completed candidate classification publishes the already-reviewed
one-shot attended direct-Recovery action intent. The operator must leave
Download directly for Recovery without booting Android. The bounded observer
requires the same serial/topology, ADB state `recovery`, a fresh boot ID, exact
IYC2 identity, running root adbd properties, and the exact fixed marker SHA-256
`5aafd7ca6918bf82aef0b7de62346d8de1b17bb0c9ececafa15978cfae2c87b0`.
Absence, malformed output, Android arrival, or timeout is `NO_PROOF`; it never
authorizes a candidate retry.

From proved recovery ADB, rollback entry is one separately journaled exact
`adb reboot download`. If recovery ADB or automatic arrival is unavailable,
the owner may instead publish one 15-minute attended physical-rollback arm;
only its exact returned confirmation may bind the current sole exact Download
endpoint. The confirmation permits one deadline-bounded initial observation;
an owner cut permits at most one separately intended resume observation before
the original deadline. Expiry, absence, ambiguity, listing/identity mismatch,
or either observation miss is durable and no later endpoint may be rebound.
Both branches converge only on
`/usr/bin/odin4 --reboot -a <exact-stock-recovery-AP> -d <bound-USBFS>`.
Rollback intent consumes its sole attempt. Uncertainty permits observation and
health finalization only, never a second Odin transfer.

Terminal closure repeats exact healthy rooted Android on a later boot and the
fixed recovery digest read. It separately records candidate/rollback attempts,
proved transfer counts, canary claim, rollback classification, and exact stock
bytes. Only exact stock recovery plus healthy Android releases the shared
guard. A raw rollback result that remains unproved cannot be relabeled as a
completed transfer merely because stock bytes are later observed.
The final Android wait retries only genuine exact-target absence; malformed or
ambiguous inventory, prepared-serial metadata mismatch, a wrong state, or a
foreign exact-target selection stops immediately.

This capability expires on target/build, recovery node, Magisk, artifact,
source, ADB/Odin, endpoint/topology, key-choreography, journal, or physical
Download-path drift; any new incident also stops activation. The first global
candidate claim permanently retires fresh T0 candidate use. A T0 terminal,
including `PROVED`, grants no T1 authority. T1 requires a separate exact
contract amendment, review, preparation, and approval.

Independent hostile review of the common revision-3
boundary, F2 tier, this section, owner, tests, exact artifacts, recovery-digest
read, key choreography, cut/recovery behavior, and higher-precedence
interactions returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0` on dormant commit
`1084e67f3b`. The mechanical activation changes only the owner boolean,
status-derived plan assertions, reviewed identities/status assertions, this
status, the single S20+ registry cell, goal/report wording, and exact tests.
Its separate activation-diff review and commit are required before these
sentences grant live authority.

## TWRP T1 F2 retained recovery

Status: **BINDING OWNER ACTIVE - T1 CANDIDATE CONSUMED**

This section activates the separate F2-T1 exception only for
the exact operator-owned `SM-G986N/y2q/y2qksx/G986NKSS8IYC2`. It receives no
live authority from T0. The completed T0 terminal proved one recovery-only
candidate transfer, one exact-stock rollback transfer, later healthy rooted
Android, and the exact stock recovery SHA-256. Its candidate observation was
`NO_PROOF`; therefore it proves neither TWRP nor recovery ADB.
The owner must revalidate the complete fixed T0 journal and exact 2,188-byte
terminal SHA-256
`94a7edbf5607f60cb19eeb3c7f09795682ccecb26a4dc807bed2485263b9e67a`,
pin the T0 owner and 30,909-byte H0 base source, and compare the terminal's final
serial hash to the current healthy T1 preflight. It returns only a sanitized
qualification summary and never publishes the serial value.

The only T1 candidate is the 52,111,401-byte recovery-only AP at SHA-256
`3ed8498243ff09399ffd93fa3b0e90044a3cfe1709b7204dac53fe190647260f`.
Its only member is `recovery.img.lz4`, 52,100,173 bytes at SHA-256
`f4ccd3fbcd683b5597cf20b028b1230cfb0dd8f4f3c93d3db27c5314834ace7a`;
the decoded recovery is 82,694,144 bytes at SHA-256
`48406883b1f631c4dfa1b157708f2e320e70b744967024bad6cb50b08cd06cb2`.
It uses the exact IYC2 stock header, kernel, DTB, and recovery DTBO with the
pinned AstroForge V2 TWRP ramdisk and the reviewed five-entry safety delta.

The prebound rollback is the 36,608,041-byte exact-stock recovery-only AP at
SHA-256
`ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157`.
No VBMeta, DTBO, boot, userdata, misc, EFS, persist, super, or other partition
member is present in either archive.

The exact profile is
`workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_t1_profile_h0.py`,
12,843 bytes at SHA-256
`c495deaac141fbbbee8fa9d13501f0e593306fa40127618640615f6a498de5e1`.
The connected owner is
`workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_t1_f2.py`,
161,745 bytes at SHA-256
`756289617ee4837457a5d1c0357d6a8b78d10d86f4b6822d30a86ed24a174fd0`
and activation-normalized SHA-256
`6ed9fe2ff0cf23f7ff28a2f3cc036cebc97ff48c37228fbac67d3c87cb72ee7a`.
`T1_F2_ACTIVE=true`. After the revision-5 consumed-state assertion rotation,
its focused hostile test is 60,061 bytes at SHA-256
`3f3e80a849e71244b94679207dc0f2407f852fcfa67850a7c51b01d0310487da`;
the T1 execution model and owner identity are unchanged.

Preparation requires fresh healthy exact rooted Android, a fresh stock recovery
digest, an empty Download baseline, exact host closure, no foreign guard, and a
new short-lived approval. Candidate and rollback each have at most one intent
and one caged Odin process. The candidate is globally no-replay. A completed
candidate may enter recovery only through the fixed attended key choreography.

Retention requires the same prepared serial and topology to appear once in ADB
state `recovery`, then return exact root UID, TWRP version
`3.7.1_12-AstroForge_v2`, donor incremental, ADB-only state, fresh boot ID, and
the fixed T1 marker SHA-256. The retained terminal performs no rollback, mount,
format, install, backup, restore, terminal command, or other partition action.
Visual UI is supportive observation and cannot substitute for the fixed ADB
marker proof.

The sole T1 candidate is now consumed. Its exact observer proved root UID,
TWRP version/incremental, security fields, running adbd, and the T1 marker, but
returned `sys.usb.config=mtp,adb` instead of the predeclared `adb`. The immutable
result is `NO_PROOF_T1_RETURNED_STOCK_RECOVERY_HEALTHY`: one candidate transfer,
one exact-stock rollback transfer, final healthy rooted Android, and the exact
stock recovery digest are proved. The T1 owner remains active only to validate
and re-emit that closed journal; the global claim prevents a new T1 prepare.

If that proof is absent or malformed, the candidate is not retained by proof
and may not be replayed. Before any retained terminal, the attended physical
Download path may send only the exact-stock rollback once, followed by exact
Android and stock-recovery health. A clean retained terminal closes that run
and its approval; any later stock restoration requires separately reviewed
fresh exact-stock authority. Drift or ambiguity stops. Activation required a
separate independent `PASS_GO` over the common/risk/target boundary, profile,
owner, tests, retained terminal, rollback graph, and exact identities, followed
by an independently reviewed mechanical activation-only commit. It creates no
run or standing approval; live use still requires fresh attended preparation
and its exact returned approval.

## TWRP T2 F2 corrected retained recovery

Status: **PROVED - T2 RECOVERY RETAINED, CANDIDATE CONSUMED**

This section activates F2-T2 only for the operator-owned
`SM-G986N/y2q/y2qksx/G986NKSS8IYC2`. T1 remains `NO_PROOF`; its observation is
predecessor evidence, not inherited authority or a relabeled T1 result.

The sole T2 candidate is the 52,101,161-byte recovery-only AP at SHA-256
`6d10b3154f2e899ee64305f3f3279d7d5243eb917f1fedb413b8f88d22ec88cb`.
Its only member is `recovery.img.lz4`, 52,096,466 bytes at SHA-256
`6fed66d26ff7cc75899c4471ab60eefb49bccff052de37043bced65719b65936`;
the decoded recovery is 82,694,144 bytes at SHA-256
`d46a1f72743a28acc4c820184d7318df9801ee43d425c22d092778e4b63d1f89`.
It preserves the T1 stock substrate and safety delta but carries the distinct
398-byte T2 marker SHA-256
`19a1a617fd2e97feda6362a2435e3d2bcce600fb37f983dd131e21c5ecf9c246`.
The 25,475-byte deterministic builder is SHA-256
`505f4fabc5e9684464b3c266453734db9e5f089507576df5dac00785683e635d`.
Its 11,687-byte focused test is SHA-256
`ce29e8d8f74051dcb4502835c3ebe92dec26cbfeac74cd68788ed4722d1f987c`.

The sole rollback is the already demonstrated 36,608,041-byte exact-stock
recovery-only AP SHA-256
`ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157`.
Both APs contain exactly one regular `recovery.img.lz4`; neither contains
VBMeta, DTBO, boot, userdata, misc, EFS, persist, super, or another partition.

The exact profile is
`workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_t2_profile_h0.py`,
12,847 bytes at SHA-256
`c02b78f2a1215a1fc2104a4634264609d2060d610bc628a068b318cb1cf55fb7`.
The connected owner is
`workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_t2_f2.py`,
167,684 bytes at SHA-256
`7f5519ef76091f491165a0be5ce81733f0343318057d02f7577954db1d1a0d11`
and activation-normalized SHA-256
`67f5f1708037afb6ba8c3f2879e70195453bc36df112bb37e0a37378bebd66a7`.
`T2_F2_ACTIVE=true`. After the retained-state assertion rotation, its focused
hostile test is 64,769 bytes at SHA-256
`8657920b486039ef37ff0dcf2ec14b2bdebd64980c7ee11c8c71d1eea39f3c5c`;
the execution model and owner identity are unchanged.

Host validation must first re-run the exact active T1 source closure and the
complete fixed T1 journal. It pins the 2,144-byte T1 terminal SHA-256
`9475e2cd6f283c7390b0d4b86b5e5208f0e943b2b452439febbe1dc3ca82cd7f`,
336-byte observation SHA-256
`c2c1d123d1f26a2416252fc5da8c576efbb0bf2bd9527c2b2fcebd3529204e74`,
546-byte raw-capture receipt SHA-256
`bbd780281ffccf7991ad4a5b10c4ba063be9bc690422699b75a9b033159d024b`,
and 271-byte observer stdout SHA-256
`c2c8b4e7393153ff40e1ca3487b76d8c345e1c2816636a6f30913e9d27baf0cc`.
It strictly reparses that stdout as the T1 marker/version/security tuple with
exactly `mtp,adb`, proves its recovery boot differs from prepared and final
Android boots, and requires current serial continuity without publishing the
identifier.

Preparation still requires fresh healthy exact rooted
Android, a fresh exact-stock recovery digest, empty Download baseline, exact
host closure, no foreign guard, and a new short-lived returned approval.
Candidate and rollback each have one intent and one caged Odin process. The T2
candidate is globally no-replay. Recovery retention requires the same prepared
serial/topology in ADB state `recovery`, a fresh boot ID, root UID, exact TWRP
version/incremental, `ro.secure=0`, `ro.debuggable=1`, exactly `mtp,adb`, running
adbd, and the T2 marker SHA-256.

The first T2 approval expired before approval consumption, candidate claim,
Download intent, or transfer. Its initial `--abort-pre-candidate` invocation
proved the same prepared boot remained healthy and recovery remained exact
stock, then stopped because the original owner required a later boot after
already publishing that fixed read. The reviewed incident repair permits this
prepared-only same-boot terminal only when candidate and rollback intents are
absent, preserves zero transfer attempts and the unclaimed candidate, validates
the exact existing root/recovery receipts, and releases only that run's guard.
It neither reuses the expired approval nor performs a reboot or partition write.
Before any cleanup read or terminal publication, the repair accepts only the
exact pre-repair active closure SHA-256
`bdf8bd67962729c38152235b725ca8badca093fe1d08b229c84dd5fd2a669a57`
or the freshly rederived current reviewed closure. Any other stale/forged
closure stops while retaining the guard.
Independent incident-repair review returned `PASS_GO` with HIGH/MEDIUM/LOW
`0/0/0`; its committed exact source is required before cleanup resumes.

A retained terminal records one candidate and zero rollback transfers, releases
the shared guard, and intentionally leaves TWRP installed. It grants no UI,
mount, format, install, backup, restore, terminal, or other partition action.
Absent/malformed proof, Android arrival, transfer uncertainty, or endpoint
drift never replays or retains the candidate and may converge only on the
attended exact-stock physical rollback. A clean retained terminal closes the
run and its rollback approval; any later stock restore requires separate fresh
reviewed authority.

Activation required independent review of the common/risk/target boundary,
builder, profile, owner, tests, T1 predecessor closure, retained terminal,
rollback graph, and exact identities, followed by a mechanical activation-only
commit. Activation created no run or standing approval; the now-completed live
use still required fresh attended preparation and its exact returned approval.

The first prepared run expired and closed with zero transfer attempts under the
reviewed same-boot cleanup. The second fresh prepared run consumed the sole T2
candidate. Its caged Odin result proves one recovery-only transfer, and the
same prepared serial/topology appeared in ADB state `recovery` with a fresh boot
ID, root UID, exact TWRP version/incremental, `ro.secure=0`,
`ro.debuggable=1`, exact `mtp,adb`, running adbd, and the T2 marker. The exact
1,911-byte retained terminal SHA-256 is
`da24acd3b33c78f4ed41565858e5314bb2c3a1acaf020ac06fb83fd99ab84d05`.
It records `PROVED_T2_RECOVERY_RETAINED`, one proved candidate transfer, zero
rollback attempts, zero other partition transfers, and zero S22+/A90/other-
target commands. The guard is absent and TWRP remains installed/running.

The candidate cannot replay and the owner cannot prepare another T2 run. The
retained terminal closed its stock rollback approval; any later stock recovery
restore requires a separately reviewed fresh exact-stock authority. Retention
does not grant TWRP UI, mount, format, install, backup, restore, terminal, or
arbitrary ADB authority.

## TWRP boot-identity metadata D0

Status: **BINDING - ATTENDED TWRP BOOT-IDENTITY D0 ACTIVE**

This section activates one attended read-only D0 for the exact retained
T2 recovery on the operator-owned
`SM-G986N/y2q/y2qksx/G986NKSS8IYC2`. It does not extend the consumed T2 F2
owner or inherit any T2 command, transfer, UI, terminal, mount, format,
install, backup, restore, or block-write authority.

The active implementation is
`workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_boot_identity_d0.py`,
29,863 bytes at SHA-256
`a71db531a25778b2dbd38c0b05b897dac33a7cc2f7eef51ba59edd899f9ecec6`.
Its activation-normalized SHA-256 is
`abd40c644e5bbbac8da743bee8e94e427730dca252bfadcbf39f6beb71b7bdfb`,
and `ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE=true`. Its 21,208-byte focused
test is SHA-256
`5f895be987466257a88c59cec980a329aa1027e90b1ba018325b98fe2b6aad1d`.
The only CLI modes are host-only `--render-plan` and one attended
`--connected` entrypoint. A fresh direct operator request authorizes exactly
one invocation; it is not standing or background authority.

Before each first connected command, the runner must revalidate the exact
active T2 owner and its complete retained run: all 43 journal nodes, the
1,911-byte terminal SHA-256
`da24acd3b33c78f4ed41565858e5314bb2c3a1acaf020ac06fb83fd99ab84d05`,
`PROVED_T2_RECOVERY_RETAINED`, the consumed no-replay T2 candidate, current T2
host closure, and an absent shared S20+ action guard. The terminal's hashed
serial/topology select only the same live ADB row in state `recovery`; another
`model:SM_G986N` row is ambiguity. Foreign attached rows receive zero
commands. Raw serial, devpath, boot ID, and complete inventory bytes are never
persisted.

One invocation has exactly two global inventories and five
selected-target commands: initial inventory; selected `get-devpath`; the exact
T2 identity script; one fixed boot-metadata script; the same T2 identity
script; selected `get-devpath`; and final inventory. Both inventories,
devpaths, selected serial, topology, and current recovery identity must remain
stable. The T2 script must prove root UID 0, exact TWRP version/incremental,
`ro.secure=0`, `ro.debuggable=1`, `mtp,adb`, running adbd, the T2 marker, and
one current boot. No `su` is invoked.

The fixed 1,916-byte metadata script SHA-256 is
`1335eeee973bf4a77802c54b0eaff38a15122efe58ff7be0bded6f0557abe09d`.
It accepts no caller input and resolves only
`/dev/block/bootdevice/by-name/boot`. It requires a symlink resolving below
`/dev/block/` to a block inode, takes major/minor from that inode, then reads
only `uevent`, `dev`, `partition`, and `size` below the derived exact
`/sys/dev/block/<major>:<minor>` node. It emits only `MAJOR`, `MINOR`,
`DEVNAME`, `DEVTYPE`, `PARTNAME`, `PARTN`, direct path, partition number,
sector count, calculated size, and three fixed zero/open-type facts; it never
emits `PARTUUID`. Cross-checks require identical inode/sysfs rdev, direct
basename equal to `DEVNAME`, `DEVTYPE=partition`, `PARTNAME=boot`, equal
partition numbers, exactly 131,072 512-byte sectors, and exactly 67,108,864
bytes.

The remote script may test the fixed inode type and read its metadata, but it
must not open the block device, read a partition byte, enumerate another
partition, invoke `blockdev`, hash block bytes, stage a file, write, mount,
reboot, enter another mode, invoke Odin, or transfer a payload. Therefore
block-device opens, partition-content bytes, writes, reboots, mode transitions, Odin invocations, and transfers are all zero.
The result is one no-clobber private JSON under
`workspace/private/runs/s20plus-g986n-twrp-boot-identity-d0/`, containing only
hashed private identity plus the bounded non-secret boot metadata and exact
command/effect counters. Failure is terminal for that invocation and has no
internal retry.

One attended invocation completed on 2026-09-01 with private 2,812-byte result
SHA-256
`46ffd0388fdcf23b46608f1557d9523e9b338316537bc19c45015877eba5f6b7` and
verdict `PROVED_S20PLUS_G986N_TWRP_BOOT_IDENTITY_METADATA`. It proved the
fixed boot link resolved to direct node `/dev/block/sda23`, with block-inode
and sysfs rdev `259:7`, `DEVNAME=sda23`, `DEVTYPE=partition`,
`PARTNAME=boot`, partition number 23, 131,072 sectors, and 67,108,864 bytes.
The receipt records seven host commands, zero commands to every other target,
zero block opens or partition-content bytes, and zero writes, staging,
reboots, mode transitions, Odin invocations, or transfers. It explicitly
records F1 and direct block write as unauthorized. Completion expired that
request and creates no standing identity lease.
Independent host-only review of the exact receipt and documentation returned
`PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.

Independent review of this section, runner, scripts, parsers, current T2
predecessor, hostile tests, private schema, and higher-precedence boundaries
returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`. The exact T2 ramdisk command
and boot-flag delta re-review also returned `0/0/0`. Mechanical activation
changed only the reviewed boolean, activation-state test assertions, and this
status/full-hash wording; the normalized identity and command surface are
unchanged. Independent review of that exact activation delta returned
`PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`. This retires only the
activation gate that blocked the hazard of treating retained T2 root ADB as
generic partition authority within this fixed metadata-only D0. Any
runner/script/parser/schema/T2/target/build/recovery/block-map or policy drift
triggers re-review. Each invocation still requires a fresh direct operator
request and attendance; disconnect, reboot, identity drift, guard conflict,
or invocation completion expires that request.

A successful result proves only that one observed current direct node maps to
`PARTNAME=boot` with the recorded rdev, partition number, and size. It is not a
write pin or standing lease. It expires for future use on any target, build,
recovery boot, TWRP, topology, block map, runner, script, parser, or policy
drift and must return to H0 design/review before an identical-resident write
qualification. It grants no F1/F2, direct block write, candidate, rollback,
reboot, Odin, partition transfer, or replay authority.

## Boot recovery-canary B0 F1

Status: **BINDING - ATTENDED BOOT-ONLY F1 ACTIVE AFTER REVIEWED COMMIT**

This section activates only the exact attended B0 owner at
`workspace/public/src/scripts/revalidation/s20plus_g986n_boot_recovery_canary_b0_f1.py`
for the operator-owned `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2` target. It does not activate the separate F2 owner above or the
donor-ramdisk T1 image. Within B0, recovery-partition reads, writes, and
transfers remain forbidden and fixed at zero; the independently bound F2
exception does not transfer authority into B0.

The candidate is the `36,198,441`-byte AP with SHA-256
`a8ed52d314e3b0cf5820e99ecd55e97cacdbc8a943d2181886d52d42a1c177fa`.
Its only TAR member is canonical `boot.img.lz4`; its decoded 64-MiB boot image
has SHA-256
`b42ba829a4a45728951f688b7b4ef07140686ce07f111a751bba948d1d934b4c`.
It carries the fixed recovery-canary ramdisk in `boot`, disables automatic
`/system/bin/recovery` service start, and retains only the reviewed PID1,
ueventd, root-ADB transport, and marker observation surface.

The mandatory rollback is the known resident Magisk boot AP, `25,835,561`
bytes with SHA-256
`1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`.
Its only member is canonical `boot.img.lz4`; its decoded 64-MiB resident boot
has SHA-256
`d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc`.
No stock AP, builder, manifest, candidate, or prose report is a runtime
dependency after candidate intent except where the branch has not yet
consumed that input. Health-only finalization requires only the exact owner,
inventory/parser, raw-capture helper, and ADB. Rollback requires only those
execution sources, fixed tools, and the exact resident rollback AP.

One current direct attended operator request authorizes one `--prepare` under
this section. Preparation inventories every global ADB row and starts only when
exactly one row matches the healthy resident `SM_G986N` / `y2q` / `y2qksx`
target. Foreign ADB rows are permitted, receive zero selected-target commands,
and do not make the exact S20+ ambiguous. A second matching model row, missing
or conflicting target metadata, unauthorized/offline target state, or selected
serial drift stops. Every non-inventory ADB command uses the selected serial's
exact `-s` selector. The root-health capture binds the boot ID inside the same
fixed `su -c` raw output and repeats the complete sanitized inventory before
acceptance. Preparation records an empty Download baseline, durably records one
no-replay `adb reboot download` intent, binds the exact resulting Download
profile/topology/character endpoint, and then emits an approval token beginning
`S20PLUS-G986N-BOOT-RECOVERY-CANARY-B0-F1-APPROVE:`. The token expires after
15 minutes and binds the exact run, target/current source boot, candidate,
rollback, tools, source closure, and Download endpoint. Preparation itself
does not authorize candidate transfer. Only the exact token copied back by the
attended operator authorizes that run's one `--execute`.

While the selected S20+ is in Download, the candidate ADB baseline need not be
globally empty. It durably records the bounded sanitized foreign inventory but
requires both the prepared serial and every `model:SM_G986N` row to be absent;
it reports zero other-target commands. Candidate and recovery observation
likewise ignores foreign rows for target-count purposes, selects only the
prepared serial plus exact target metadata, and rechecks the complete inventory
around each selected-target transaction. A foreign row is never probed to
resolve S20+ identity.

Candidate and rollback each have one attempt. A global exact-candidate claim
is consumed before candidate intent; any complete or prefix-partial claim
prevents candidate replay while retaining recovery for the guard-owning run.
Every effect intent is durably complete before its backend and every journal,
guard, and global-claim final name is published with file fsync, atomic
no-replace `O_TMPFILE` plus `linkat(AT_EMPTY_PATH)`, and directory fsync.
Unknown or missing transfer results never authorize candidate replay.
Rollback intent likewise makes the rollback one-shot; after it, only bounded
observation and healthy resident finalization remain.

Every Odin invocation uses the exact pinned binary and a fixed environment
containing only `LANG=C`, `LC_ALL=C`, and `PATH=/usr/bin:/bin`. Candidate,
rollback, and payload-free return execute inside an intent-bound cgroup. A cut,
timeout, or output fault must kill that cgroup, prove it empty, remove it, and
publish quiescence before any device observation, later transfer, or terminal
health. Read-only `odin4 -l` uses a stable transient cgroup and the pinned
static BusyBox ten-second watchdog; a prior owner-death cage must become empty
and be removed before a new listing. Host reboot may prove an old intent-bound
cgroup absent, but does not authorize replay.

Candidate observation requires a new boot. Exact root ADB plus the fixed
marker/PID1/ueventd/service evidence may classify the B0 claim `PROVED` or
`REFUTED`; malformed or incomplete evidence remains `NO_PROOF`. An uncertain
transfer whose prepared Download endpoint never departed is
`download-unquiesced` and cannot authorize rollback on that endpoint. Regardless
of claim verdict, candidate intent makes resident rollback mandatory.

If automatic exact-target rollback entry cannot be proved, physical fallback
is a separate attended arm and confirmation. The arm binds either an exact
already-present qualified Download endpoint or a fresh empty baseline, expires
after 15 minutes, and emits one exact confirmation token. Confirmation is
durably consumed before use. The observer has one bounded attempt and, after a
reporting cut, at most one current read; absence, ambiguity, identity failure,
or expiry publishes a durable miss and permits no further observation or
transfer. A bound arrival permits only the fixed resident rollback.

Terminal `PROVED_B0_RETURNED_RESIDENT_HEALTHY` requires completed candidate
transfer attribution, `PROVED` B0 evidence on a distinct boot, completed
resident rollback transfer, and exact rooted resident health on another fresh
boot. `REFUTED` requires completed candidate attribution; otherwise the
experiment remains `NO_PROOF`. Healthy resident return and exact rollback
transfer provenance remain separate fields. The shared S20+ guard is released
only after the terminal record is durable. S22+, A90, and every other target
receive zero commands.

The dormant H0-qualified owner was `218,089` bytes at SHA-256
`4457bb0179586fcb8edaa88e895aae17ca951ae44ed8ddb0d0c0a592de86a6b7`,
with normalized SHA-256
`7d4299e8a4fc503eee8d41ae0cf051b4f922b72c5550443e2d8cdba3cf2622b5`.
Independent dormant review returned `PASS_GO_H0`, HIGH/MEDIUM/LOW `0/0/0`,
after 48/48 focused tests and host closure
`3623bdb9b4c3d907355808e4653d46dbd6012821ca023ea2240dd0ee4c29501e`.

The first active singleton-inventory owner was `218,203` bytes at SHA-256
`80d961e06c03f4d092efb65ba92f142ec1061227bab55d19068b1b623a69a8ad`,
with reviewed normalized SHA-256
`cdd34821dbc2b555ccb9ce8f14dbeb6dd0ff2baa9af50deb46708684c9167788`.
Its focused test was `48,102` bytes at SHA-256
`872895bfd12277dc35c05c34fa5b2d0105e84df2e640bde1bf52f3a01b14a588`.
That activation received independent `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`
and was committed as `0ae1c30792`.

The active multi-ADB v2 owner is `222,832` bytes at SHA-256
`0246014e50b1ff509568ee019f36680694e3a87644ccca8c340767b3dd75445d`,
with normalized SHA-256
`e2d612fc14549d0b0838ba66473b203126342362480636f3599fd9ea1548ed40`.
Its active 54-test file is
`58,443` bytes at SHA-256
`8a7425b8d63582cda62e55a82c7e2b300990af0fe5809e7e24c5f33f33fb3741`;
the host closure is
`4a28081b9829a8908c079aa110b9e95be20427873367808cd50e81da418502a8`.
Those exact bytes, this contract delta, the goal delta, and the v2 review report
received independent `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0` and become
effective only when their complete diff is committed together. They were
committed as `60f3f9f11a`. The revision creates no standing unattended
authority. Every new run still requires fresh prepare, its exact emitted
approval, and attendance.

The first v2 run consumed its exact approval and completed one attributed
candidate transfer. Candidate observation returned `NO_PROOF` with no ADB or
Download arrival, so mandatory resident rollback remains open and candidate
replay remains forbidden. Its first physical-rollback arm stopped before any
device command because the B0 validator referenced an `argv0_name` attribute
that the pinned raw-capture loader validates in its durable JSON receipt but
does not expose on `RawCaptureHandle`.

The recovery-parser owner keeps `VERSION` v2 so it can consume the
existing journal. It reads the same direct canonical raw-capture receipt,
binds every handle-exposed field back to that validated handle, and derives
`argv0_name` from the receipt bytes whose exact size and SHA-256 are already in
the transfer result. It never accepts a caller value. Its predecessor set
contains only normalized SHA-256
`e2d612fc14549d0b0838ba66473b203126342362480636f3599fd9ea1548ed40`
and accepts that identity only for `rollback` or `health` after a durable
candidate intent; the `candidate` phase and a pre-candidate run reject it.
The existing global candidate claim must still bind the same run, so this
compatibility path cannot replay or open another candidate.

The repaired owner is `224,559` bytes at SHA-256
`82ec4cee48c3a39aa8dc4de6136e8fda3fbefe88d4821a71bdb0df55d2a17c2a`,
with normalized SHA-256
`52f2df6aa1864a956cd4d0e43a3906ffbb613116577d7735788630a43323ea06`.
Its 56-test file is `60,003` bytes at SHA-256
`e7f4add57131bdfe7ba3b2285aa02283ff2110d1e1abb9d507e35acf7cceee7b`;
the host closure is
`aa17bf9d145f4909158b9132a58e81680f94e6007777aa601630bc8104f0812a`.
Those exact bytes, this contract delta, the goal delta, and the incident report
received independent `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0` and become recovery
authority only when their complete diff is committed together. They authorize
only journal-derived recovery and future fresh runs under the unchanged exact
approval gate, never candidate replay.

The repaired closure was committed as `cf8bc38a98`. The attended operator then
returned the exact physical confirmation emitted by the arm. The owner bound
the exact S20+ Download arrival, completed one resident rollback transfer, and
proved fresh exact rooted resident health. The durable terminal is
`NO_PROOF_B0_RETURNED_RESIDENT_HEALTHY`: candidate and rollback attempts are
1/1, candidate experiment pass is false, rollback transfer completion is true,
all recovery-partition access counts and other-target commands are zero, the
shared guard is released, and the global candidate claim remains consumed.
Neither candidate nor rollback may replay.

## Bounded autonomous research session

Status: **H0 POLICY PASS_GO - NOT ACTIVE**

The common S20+ autonomous-research delegation is modeled by
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_research_h0.py`.
It is target-specific and does not inherit A90 unattended authority. The current
runner exposes only `--render-plan`; `RESEARCH_ACTIVE=false`, live authority is
false, and its command and device-effect lists are empty.

The proposed active session may later reuse only the exact reviewed routine D0,
routine-control, and payload-free Download-return primitives pinned by its
binding. The initial action surface contains only public health reads,
`reboot-system`, and one separately reviewed atomic `download-roundtrip`. Root
profiles remain deferred below. The roundtrip begins in healthy Android, records an empty
Download baseline, durably intents one `adb reboot download`, binds the sole
exact arrival, durably intents one exact payload-free
`/usr/bin/odin4 --reboot -d <bound-endpoint>`, and proves healthy returned
Android. It does not reuse or bypass the attended disconnect/arm/reconnect
helper. It must remain in healthy normal Android before publishing
`READY_FOR_ATTENDED_F1` and stop
before any F1 intent, F1 Download entry, approval consumption, Odin payload, or
partition transfer.

One fresh attended campaign opening creates one durable 24-hour allocation:
at most 256 read operations, 128 MiB of private evidence, and 64 control
transactions, split into at most 32 normal reboots and 32 Download roundtrips,
plus an exact 96-component-effect ceiling. Each normal reboot debits one
transaction/effect before intent; each roundtrip debits one transaction and
its entry effect plus a mandatory return reservation before the entry intent.
The return intent converts that reservation to consumed without requiring new
capacity. The allocation cannot renew or reset itself. Each child session is at
most four hours, 64 reads, 32 MiB, 16 transactions, and 24 component effects,
and debits the campaign counters monotonically.
Entry and return each publish one strict canonical atomic no-replace node that
contains both post-debit child/campaign counter snapshots and that effect's
intent. A debit-only, single-scope, malformed, or partially published state
grants no effect or recovery authority. Arrival/return recovery additionally
binds campaign, session, roundtrip ordinal, source identity, endpoint, policy
binding, and exact predecessor node.
A valid unmatched entry and reserved return survive child/campaign time expiry
only as recovery authority to observe the bound arrival, issue the exact
payload-free return, and prove final health. They grant no new baseline, entry,
transaction, or capacity. Endpoint ambiguity retains the guard and requires
attended recovery.
A fresh exact target/boot binding starts every child session. Any unexpected
boot, unhealthy return, unresolved guard, ambiguous endpoint, source drift,
budget exhaustion, or incomplete mode transition parks the session. No control
effect repeats after its durable intent.

Root profiles are deferred and are not actions in this H0 activation surface.
Their paths/node types are recorded only as design inputs. A later unit must
bind the exact root launcher/transport, timeout, per-input size ceilings,
stable no-follow before/after receipts, directory entry count/name grammar,
exact parser source identities, and hostile replacement/cut tests before adding
any root action. No file-byte extraction, root write, package operation, module
marker, mount, property/service mutation, or security/configuration change is
authorized by this unit.

This H0 policy owner is permanently render-only and is not mechanically
activatable. Activation requires a separate exact live coordinator with no
caller callback, its tests/report identities, hostile cut coverage, independent
safety review of this permanent common boundary change, and a separate
mechanical transition of this section and that coordinator. Until then, the
existing attended D0/D1/F1/R1 rules remain unchanged and no autonomous
connected action exists.

The first separate coordinator unit now exists only as the dormant H0
journal/state-machine candidate
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_research_coordinator_h0.py`.
It models the fixed guard, canonical opening/session chain, exact empty
Download baseline, entry/arrival/payload-free-return ordering, two-scope
counters, return reservation, fresh post-effect health, and pre-F1 terminal.
It has no observer, command backend, live action integration, or mechanical
activation path and therefore grants no connected authority. Independent
exact-byte review returned `PASS_GO` for this dormant H0 journal model and its
status was mechanically rotated to `PASS_GO_NOT_ACTIVE`; all activation and
live-integration flags remain false. Exact D0/read evidence, reboot/return
execution, child-session lifecycle, reporting-cut recovery, a new independent
live-integration review, and a later binding rotation remain required.

The first exact public-health consumer closure is
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_health_h0.py`.
Independent review returned `PASS_GO` and its status is
`H0_AUTONOMOUS_PUBLIC_HEALTH_PASS_GO_NOT_ACTIVE`. It binds the six-command
inventory transcript, exact target/build, hashed serial/topology/boot,
stable Android, enforcing SELinux, shell identity, and zero other-target
commands. It remains render-only: durable evidence, campaign accounting,
coordinator consumption, control actions, and activation are not implemented.

The separate public-health read-leaf coordinator is exact-byte qualified only
as `H0_AUTONOMOUS_PUBLIC_HEALTH_READ_LEAF_PASS_GO_NOT_ACTIVE` at
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_coordinator_h0.py`.
It may model only the initial attended session's ordinal-1 lease and a
permanently parked completion. It admits no control or terminal successor and
leaves the base coordinator and qualified evidence source unchanged. Its
evidence reservation covers the exact 19-file set; eight excluded structural
JSON nodes are separately bounded by per-node limits and one 48-KiB aggregate
in both scopes. The final source SHA-256 is
`e2952245bf4433044fae12ff8114ee9ff4239cbacd173a83cdc5a3dfcfa3d2c6`
and the test SHA-256 is
`2f322e064e9f120fc04f019f5244448814a30665698fab9ab3b30d5f74fc72ab`;
46 focused and 140 aggregate tests pass. Trusted writer/clock, durable
cross-root order, execution integration, and activation remain absent. Every
live/mechanical/integration flag is false, so this paragraph grants no
campaign, connected read, standing consent, or device authority.

The separate self-contained recovery-v1 source is qualified only as
`H0_PUBLIC_HEALTH_RECOVERY_V1_STORE_SCANNER_PASS_GO_NOT_ACTIVE` at
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_recovery_v1.py`.
Its final source SHA-256 is
`6186221593b3778475bf3b1ac4bd28bfe013534793eca4ce5fbe0007be8eb0c3`,
normalized SHA-256 is
`1b769167018a2a08e71e67adc00c20148eb4e0a11a6c428bf8fc82b517533b5d`,
and focused-test SHA-256 is
`620d807c8038c145e738d08f4d05ca10e8e8a65e8c7881ecfc1cef8d69a50978`;
76 focused and 216 aggregate tests pass. This qualifies only its embedded
parser, unbound manifest model, inactive three-root scanner/store primitives,
and conservative cut classifier. `RECOVERY_V1_QUALIFIED`, scanner, writer,
finalizer, re-emission, manifest, contract, and live gates all remain false;
the immutable loader and finalizer are qualified separately below. No private bundle,
recovery authority, campaign, connected command, or device authority exists.

The separate immutable-loader and self-contained-finalizer H0 subset is
exact-byte qualified only as
`H0_PUBLIC_HEALTH_RECOVERY_LOADER_V1_PASS_GO_NOT_ACTIVE` and
`H0_PUBLIC_HEALTH_RECOVERY_V1_FINALIZER_PASS_GO_NOT_ACTIVE` at
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_recovery_loader_v1_h0.py`
and
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_recovery_v1_finalizer_h0.py`.
The loader is 35,315 bytes at SHA-256
`a210944447dc33b7593b42ba5c46cde9561c9449e8981523b468a4121c4284cc`
with normalized SHA-256
`8df4dc534a1d4e9ac1a73867151e4bfcf2450a52283a281c7091d9c47e1e09cc`.
The finalizer is 162,875 bytes at SHA-256
`94f6022aebcdc63bcad08757f493349d2e4b198610a367e72181a65694321f0b`
with normalized SHA-256
`38cb154e526e8a1a3ad38f8c857f03668f92fedced786745f5e8e85d91e21dac`;
its derived unbound manifest is 7,669 bytes at SHA-256
`51931dd9a084e1c7ae8d674681d34be7bd2f50b32d8c0b84b2842d51749df593`.
The loader and finalizer tests passed 21/21 and 26/26 respectively, and the
eight-suite autonomous aggregate passed 263/263. Independent exact-byte and
cut reviews returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.

This H0 finalizer can model exactly one no-replace missing-node publication per
invocation from a fully revalidated retained chain: lease mirror, health,
deterministic result, or permanently parked completion. Re-emission is a
sanitized repeatable zero-write envelope. A command-6 receipt time is only a
logical completion lower bound; reporting-cut time, expiry, and drift remain
unproved. The loader verifies exact no-follow private core/manifest bytes under
the fixed lock before compiling them and caps its own source read at 64 KiB.
Direct core execution is not authority. The original store/scanner bytes above
remain unchanged.

Every loader operational-qualification/identity/operation/future-runner/contract/
mechanical/live gate and every finalizer qualification/scanner/writer/
publication/finalizer/re-emission/manifest/contract/live gate remains false.
The future-runner binding is unbound, no private bundle is installed, and the
current scanner still rejects future `opening-v1` and `campaign-binding.json`.
Therefore this qualification grants no recovery operation, campaign,
connected command, standing consent, or device authority. The exact report is
`docs/reports/S20PLUS_G986N_AUTONOMOUS_PUBLIC_HEALTH_RECOVERY_LOADER_FINALIZER_V1_H0_2026-08-31.md`.

The separate campaign-v1 Phase-A artifact model is exact-byte qualified only
as `H0_AUTONOMOUS_PUBLIC_HEALTH_CAMPAIGN_V1_MODEL_PASS_GO_NOT_ACTIVE` at
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_campaign_v1.py`.
Its final source is 92,607 bytes at SHA-256
`43edcfc5bf2c69f96bcef015f305d38be9c310dd92371a2a942e075261dfa8e2`,
with activation-normalized SHA-256
`be1f73de763b7fcce8e1b74da23cb662244b7b1de9bcbb862ffa59c5c296e773`;
its 39,772-byte test is SHA-256
`1ba2d127e02cf950ebd8deac6e618329eea6d1d86f9ec8eb69aa4ea6a8fe2b27`.
Focused validation passed 32 methods/37 cases. The canonical nine-suite
autonomous aggregate passed 295 tests; adding the 13-test routine-D0 suite
produced a ten-suite 308-test pass. Independent exact-byte and status-rotation
reviews returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.

This qualification fixes only a planned two-phase transcript, canonical
opening/forward artifacts, logical receipt-chain cap, storage closure, and
non-authorizing cut model. Both executors and the unforgeable same-process
handoff are absent; the 12 host and six selected-target command counts are
plans only. Actual opening-to-read freshness, attended request, activation
binding, ADB-server provenance, USB generation, trusted clock, durable cut
content, process capability, finalizer resume, cross-code coordination,
private recovery binding, scanner/finalizer grammar rotation, contract,
mechanical activation, and live authority all remain unproved or false.
Durable nodes grant zero commands, and even forced true gates reach only an
unimplemented stub. The exact report is
`docs/reports/S20PLUS_G986N_AUTONOMOUS_PUBLIC_HEALTH_CAMPAIGN_V1_PHASE_A_H0_2026-08-31.md`.

The cross-code start-interlock fixture protocol is exact-byte qualified only
as `H0_AUTONOMOUS_PUBLIC_HEALTH_START_INTERLOCK_V1_MODEL_PASS_GO_NOT_ACTIVE` at
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_start_interlock_v1_h0.py`.
Its final source is 33,130 bytes at SHA-256
`f75c9980b044b4e51748fe92d7ed7e0558a11e8417cba257e7ad36cff77aa7d9`,
with activation-normalized SHA-256
`52e7ad159f6875f2367f0eeeaf6a05024c36bb0e3a7c76745defde79852d1e5d`;
its 33,156-byte test is SHA-256
`03acdaa34619304152fdf743ca46f60775f00992b0a46c00ab80b3e4d36c9b8b`.
Focused validation passed 46/46 and the ten-suite autonomous aggregate passed
341 tests. Independent exact-byte and status-rotation reviews returned
`PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.

This qualifies only temporary-directory fixture behavior: an exact held
leaf-root directory `LOCK_EX|LOCK_NB`, strict modeled `EMPTY` or fully parked
admission, and shared-action-guard absence under the lock. The public-health
`coordinator.lock` remains recovery-only, and modeled owned continuation or
recovery bypass grants no new start, command, replay, or recovery authority.
Fixed real-root reopening, the exact production scanner, runner-owned guard
publication, every D0/D1/F1/R1 integration, legacy-process quiescence,
contract, mechanical activation, and live authority remain unimplemented or
false. The exact report is
`docs/reports/S20PLUS_G986N_AUTONOMOUS_PUBLIC_HEALTH_START_INTERLOCK_V1_H0_2026-08-31.md`.

The separate runtime-primitives source is exact-byte qualified only as
`H0_AUTONOMOUS_PUBLIC_HEALTH_RUNTIME_PRIMITIVES_V1_PASS_GO_NOT_ACTIVE` at
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_runtime_v1_h0.py`.
Its final source is 85,645 bytes at SHA-256
`f6644edc1f8eee80e6f9fc5e7623c96b8e58de23312e71607e51a4658d67652f`,
with activation-normalized SHA-256
`12b993c199a104c2c0f1bdb9706c179005292971428ef26317442e600eb89ac2`;
its 79,428-byte test is SHA-256
`69b90ff55e3a4e7b48f346b9a452c1227dca345e6d334b4e443e6faeef53a403`.
Focused validation passed 64/64 and the eleven-suite autonomous aggregate
passed 405 tests. Independent exact-byte and status-rotation reviews returned
`PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.

This qualifies only the inactive source primitives for exact held-file ADB
execution, preexisting-server continuity detection, bounded clock and USB
generation ownership, direct-child cleanup, and a process-local one-shot
state object. Concrete host observers are import-reachable fixtures and Python
privacy is not authority. No closed executor call graph or journal integration
exists. ADB server autostart is detected after drift but not prevented; the
no-autostart transport remains an explicit blocker. Every execution,
same-process integration, target/cross-code, contract, mechanical, and live
gate remains false. The exact report is
`docs/reports/S20PLUS_G986N_AUTONOMOUS_PUBLIC_HEALTH_RUNTIME_PRIMITIVES_V1_H0_2026-08-31.md`.

The separate terminal-continuity adapter is exact-byte qualified only as
`H0_AUTONOMOUS_PUBLIC_HEALTH_TERMINAL_CONTINUITY_V1_MODEL_PASS_GO_NOT_ACTIVE`
at
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_terminal_continuity_v1_h0.py`.
Its final source is 40,593 bytes at SHA-256
`134c674d4ddfafae958436a011956e144214fc896cb67070bdc4c88e72f610ad`,
with activation-normalized SHA-256
`bba10951e24e798c57d4db103f9d591a09d495c753f106ca144b3b90d923095a`;
its 36,623-byte test is SHA-256
`4d23a89a3526dd83d8af49efdc0f859328cfc1c8b351b33cc0889344a64010d2`.
Focused validation passed 41/41 and the twelve-suite autonomous aggregate
passed 446/446. Two exact post-correction reviews independently returned
`PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.

This H0 model adds one exact `terminal_continuity` field: null on opening
receipts 1–5 and a fixed schema/clock/server/USB object on receipt 6. It hashes
the previous complete extended receipt, strips the extension through the exact
Phase-A validator, authenticates the retained 19-file set, derives the serial
only from command-2 inventory, and derives a sanitized recovery-input envelope
only from `(intent_raw, evidence)`. It exact-loads the frozen runtime solely to
enforce the Linux USB rdev mapping. It does not authenticate shared-guard
absence or a usable source identity, and explicitly leaves runtime-owner
observation false. Recovery loader/core/manifest identities are declarative
pins only; no private bundle is opened or proved.

All 14 gates, opening-result/campaign-binding/loader integration, executor,
target/cross-code coordination, contract, mechanical activation, and live
authority remain false. The scanner/finalizer still rejects this future
grammar. The ADB no-autostart/host-kill blocker also remains open. This unit
grants no campaign, recovery invocation, connected command, standing consent,
or device authority. The exact report is
`docs/reports/S20PLUS_G986N_AUTONOMOUS_PUBLIC_HEALTH_TERMINAL_CONTINUITY_V1_H0_2026-08-31.md`.

The separate restricted-ADB-proxy artifact is exact-byte qualified only as
`H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_V1_MODEL_PASS_GO_NOT_ACTIVE` at
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_adb_proxy_v1_h0.py`.
Its final source is 46,477 bytes at SHA-256
`18993008de3c236211c11de2756dc9b05424d9704cfdcb9c02f3cf70e9e29d92`,
with activation-normalized SHA-256
`8878c5e39f2d34ea90707bf81697aed119db1fdf3141807b56c81480fbe1c8c9`;
its 30,975-byte test is SHA-256
`058977bc8cb16cdf28af3ae2a4828e0eab035caa5d2a6177e788df8efd7f568e`.
Focused validation passed 40/40 and the thirteen-suite autonomous aggregate
passed 486/486. Two independent final reviews returned `PASS_GO` with
HIGH/MEDIUM/LOW `0/0/0`.

This qualifies only an inactive post-run protocol/relay audit model. It fixes
the exact ADB 34 local `0029` version response, per-ordinal allowlist,
`host:tport:serial` plus nonzero eight-byte transport ID and same-connection
exec sequence, fixed Phase-A snapshot escaping, exact response relay, and
server/child/accepted-peer/held-FD composition. It rejects modeled
`host:kill`, `host:start-server`, unknown services, and reconnects before an
accepted forward event. These are caller-constructed normalized trace objects,
not a live observer or causal enforcement proof.

All 17 gates remain false. The exact pins are declarative, and the concrete
AF_UNIX proxy, incremental fragmentation-safe parser/emitter, response stream,
seccomp BPF/install/failure path, FD-reuse closure, ADB child compatibility,
executor, journal/evidence, same-process handoff, target/cross-code
coordination, recovery integration, contract, mechanical activation, and live
authority are absent or unproved. Proxy absence can still trigger a local ADB
launch attempt until the filter is concretely installed. This unit grants no
connected command, campaign, recovery, standing consent, or device authority.
The exact report is
`docs/reports/S20PLUS_G986N_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_V1_H0_2026-08-31.md`.

The separate pure incremental-parser artifact is exact-byte qualified as
`H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_INCREMENTAL_V1_MODEL_PASS_GO_NOT_ACTIVE`
at
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_adb_proxy_incremental_v1_h0.py`.
Its final source is 33,817 bytes at SHA-256
`f956bc65a5e7abedd2f57ab8fa723275be1e7d6fb2b4ae86295de947c42f3f05`,
with normalized SHA-256
`ec1dcd8236f6778bdf6994b5d1a9a26132e95d92d9ce8955cfba08122c95a2cc`;
its 28,068-byte test is SHA-256
`6786cda31d30813e6243ac8189a9f0802b455aa478656456a489f743e2c31cce`.
Focused and committed proxy-audit validation passes 33/33 plus 40/40.

This model accepts only one caller-selected immutable typed transcript. Its
first pass validates the complete ordinal closure without constructing an
emission; only a success-only second pass derives a fresh frozen emission
tuple. Three earlier mutable-sink/reducer candidates remained `NO_GO` until
caller sink, owner, session, duplicated ledger, arbitrary service reducer, and
failure-traceback partial-emission surfaces were removed. Final independent
review returned HIGH/MEDIUM/LOW `0/0/0`. Acceptance authenticates only the
supplied model bytes, not a real wire observation. All 23 operational gates
remain false; there is no socket, peer, relay, process, ADB child, server
binding, journal, executor, integration, campaign, or device authority. The
exact report is
`docs/reports/S20PLUS_G986N_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_INCREMENTAL_V1_H0_2026-08-31.md`.

The separate exact-host seccomp artifact is qualified as
`H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_SECCOMP_V1_PASS_GO_NOT_ACTIVE` at
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_adb_seccomp_v1_h0.py`.
Its final source is 47,577 bytes at SHA-256
`0c5ee2a7c293dd9c04d152945e29a7f5c278bce6f7960cfdc19979d8fc79d23e`,
with normalized SHA-256
`cf041861841f79d9fe158f4c650b27d5b596aff9cea26acb68e66e5a3eabe3e6`;
its 30,103-byte test is SHA-256
`d8ab5ea91385375c5af28b562869a1125cd56fbdca339e21902f44317e7a0db7`.
The deterministic 53-instruction, 424-byte classic-BPF program is SHA-256
`6f2e13a14ff7e17668fa6501535dc097960e5b1d02a83b7443d3ea86e103aaa5`,
and focused validation passes 42/42.

The filter is an inactive x86-64 launch-prevention model, not a general
sandbox. It kills architecture mismatch, traps the complete x32 namespace
before default allow, traps native bind/listen/process creation/path exec, and
compares only the five raw execveat argument values for one held-fd transition.
Classic BPF cannot dereference the pathname, argv, or envp content, retain
one-shot state, or close post-exec fd/address reuse; exact executor-owned
pathname/argv/environment bytes, ADB compatibility, process-death behavior,
production installation, and composition remain unproved. Two independent
`NO_GO` findings for x32 default-allow and omitted argv/env content visibility
were corrected before final HIGH/MEDIUM/LOW `0/0/0` review. All 17 operational
gates remain false. The exact report is
`docs/reports/S20PLUS_G986N_AUTONOMOUS_PUBLIC_HEALTH_ADB_SECCOMP_V1_H0_2026-08-31.md`.

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

Status: **BINDING - ACTIVE R1 CAPABILITY; LAST N1 RUN RECOVERED INTENT-ONLY/DISABLED ROOTED HEALTHY**

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

The active root-data runner is 223,363 bytes at SHA-256
`63e58f99b06275ed0d1eeacc5d87dbb7fdc1a9f471fcd7645f447345b23a3b52`
and normalized SHA-256
`39cdf9eda1eb4fa8240bab49c1a45fdf54b63431908fd6721cdde2453e77544c`.
The active stock-recovery runner is 61,312 bytes at SHA-256
`b029afc3d4a899e4d83304773f8405519bacdb02de742de015a52c97689cc2a6`
and normalized SHA-256
`0bb7eab8a87d11758dac20103ede5ac16c5acbdf3cbc3b511cb30842c4f29f2d`.
These values identify the active capability. They do not identify a prepared
run, approval, target session, or device action.

One attended run prepared under the predecessor active identity consumed its
sole install attempt. Its complete rc-0/empty-stderr transcript was initially
rejected only because the host grammar omitted Magisk v30.7's preceding
system-as-root line. The reviewed no-install continuation then passed the
separate post-install tree audit and performed the first reboot without
reinstalling. The canary wrote its exact intent but no result; that reboot was
not replayed. The preauthorized Android-root recovery created the one disable
marker, performed one recovery reboot, proved the exact target rooted and the
module disabled in `intent-only` state, removed the owned staged inputs, and
released the guard. Terminal verdict is
`RECOVERED_S20PLUS_G986N_NATIVE_CANARY_N1_DISABLED_ROOTED_HEALTHY`.
Stock/Odin attempts were zero and installation/reboot replay remains forbidden.
The exact incident and reviewed continuation are
recorded in
`docs/reports/S20PLUS_G986N_NATIVE_CANARY_R1_INSTALL_TRANSCRIPT_INCIDENT_2026-08-16.md`.

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
The later `unsafe-metadata` stop exposed a separate host expectation defect:
official Magisk v30.7 applies `0755` to the persistent `MAGISKBIN` tree in both
its flash and app direct-install paths. The independently reviewed correction
therefore requires exact `0755` for `util_functions.sh` through one shared
parser/validator table; it adds no command, path, effect, or retry authority.

The later install-transcript incident exposed one further host grammar defect.
Official v30.7 `mount_partitions()` emits
`- Device is system-as-root` on this exact target before the module title, so
the closed successful stdout grammar includes that line and still requires rc
zero, empty stderr, the exact remaining title/extraction lines, and no trailing
bytes. A candidate-only compatibility entrypoint is bound to exact predecessor
binding SHA-256
`89098a4190d3ab2a85ddf0efd8b12ffdd800f79cf4146b8302f8e23832cf1845`
and predecessor runner SHA-256
`35dfc7557c5c9e9b3e62d4865e81122572c57d0464997f4e2a35904a0b15432f`.
It must atomically bind the old and new runner receipts plus the exact install
result/stdout hashes before connected reads, records zero device effects and
`install_replay_permitted=false`, rebinds the same prepared Android boot before
any privileged read, and starts only at the read-only post-install tree audit.
It cannot stage or install. Missing or extra journal state, another binding,
another runner, another transcript, target/boot drift, or helper drift stops
before reboot. Independent review returned `PASS_GO` for candidate full
SHA-256 `e2725e77dc552384eedc669902e35790af940d15fc786240171b50cc608ea420`
and normalized SHA-256
`39cdf9eda1eb4fa8240bab49c1a45fdf54b63431908fd6721cdde2453e77544c`;
the separate identity-only rotation produced the active root-data runner above.

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
and operator attendance remain mandatory for a new transaction. The closed
recovered run grants no fresh authority and cannot be replayed.
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
