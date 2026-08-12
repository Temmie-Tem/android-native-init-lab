# S20+ G986N Binding Target Contract

Status: **BINDING - D0 ONBOARDING CONSUMED**

This is the binding target contract for the operator-owned Samsung Galaxy S20+
5G `SM-G986N` / `y2q` / `G986NKSS8IYC2`, listed in the binding target registry
in `AGENTS.md`. Its exact one-shot D0 onboarding inventory has been consumed.
The durable active-intent guard remains present and this contract grants no
further connected action. It defines no D1, F1, root, flash, recovery,
rollback, or other connected capability.

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

## D1 and F1 Are Not Defined

This contract defines no S20+ D1, F1, root, flash, recovery, or rollback
capability. Any such work requires a later exact contract amendment, recovery
design, appropriate artifacts, proportional validation, independent safety
review, and fresh authority. Bootloader-unlocked state and a passing D0 do not
grant those capabilities.

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
It does not activate D1 or F1. Any later connected action requires a separately
defined target process, proportional independent review, and fresh authority;
the existing active-intent guard must not be removed or rotated under this
contract.
