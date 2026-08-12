# Routine connected actions

Status: **BINDING - TARGET-CONTRACT ACTIVATION REQUIRED**

This process keeps ordinary owned-device maintenance proportional to its
actual effect. It does not grant standing authority. A binding target contract
must name the exact target, activate the permitted actions, and bind every
artifact, package, destination, and executable needed by a write.

## Action classes

### Routine D0 read

A current direct operator request may authorize one fixed, unprivileged,
read-only snapshot when the target contract has an active routine D0 process.
The process may inventory transports and read public properties, procfs, or
sysfs named by that contract. It must not use root, enumerate user data or
credentials, or mutate the target.

### Routine D1 control

A current direct operator request while the operator is attending may
authorize exactly one allowlisted control action:

- normal reboot;
- enter Download mode;
- enter stock recovery mode; or
- exit a non-normal mode through an exact target-bound no-payload command when
  the target contract defines that transport.

The command is dispatched once. A normal reboot is not healthy until a later
bounded health read proves the exact target returned. Mode entry is a
dispatch-only result until the bound endpoint observer or operator-visible
state confirms the requested mode. Absence, timeout, or ambiguous observation
is `HEALTH_PENDING`, never permission to resend the reboot. While health or
mode is pending, no later setup/control action may start; only bounded reads,
operator observation, physical return, or a target-defined no-payload return
command is allowed.

### Routine D1 setup

A binding target contract may activate either of these narrow persistent
data-plane actions after one independent review of its exact implementation:

1. install or replace one cryptographically pinned, non-privileged APK through
   Android Package Manager; or
2. copy one cryptographically pinned, inert regular file to one fixed path in
   shared user storage.

These actions are D1 only while all of the following remain true:

- the device is in healthy normal Android and exact model/device/product/build
  identity is checked immediately before the write;
- the host executable, regular input path, size, SHA-256, package name or
  destination, and command argv are closed by the target contract;
- the APK install grants no runtime permissions, device-owner role, root,
  accessibility, VPN, debug-state, or security-setting change;
- a staged file is inactive data, is never sent to a bootloader, recovery,
  partition, package installer, shell interpreter, or service by this action;
- shared-storage free space is checked, an artifact-specific staging directory
  is claimed by one atomic failing-if-present `mkdir`, and the file is written
  only inside that newly owned directory before device-side SHA-256
  verification;
- no credential, key, configuration, user database, or existing file is
  overwritten;
- one invocation has one effect attempt and no automatic retry; and
- a verification or reporting failure after an effect is treated as possible
  completion and does not permit replay.

Installing an APK or staging a file does not authorize launching it, patching
another file, deleting it, granting permissions, rebooting, entering a mode,
or flashing. Each additional effect needs its own current operator request and
an action explicitly represented by the selected contract.

## Common execution shape

Every connected invocation follows this small sequence:

1. validate fixed host inputs before contacting a device;
2. atomically create one fixed private active-action guard and durably write
   the D1 intent before the first connected command;
3. inventory every attached row and resolve exactly one target using its full
   model/device/product tuple;
4. read the selected target's USB topology and fixed normal-health snapshot;
5. dispatch the one allowlisted effect at most once;
6. perform only the action-specific verification; and
7. write one no-clobber private result or failure receipt with raw serial,
   topology, and boot ID represented only by SHA-256.

A direct request such as “read it”, “reboot normally”, “enter Download”,
“enter recovery”, “install the pinned APK”, or “stage the pinned file” is the
fresh approval for that one named action. It does not approve a later action
and does not survive a material runner, artifact, target, or contract change.
No special approval sentence or campaign-specific policy is required.

The fixed guard blocks every later routine setup/control invocation. An
effect-free preflight failure may durably close and remove it. Setup success
removes it only after the result is durable. Any effect-attempted failure and
every reboot/mode dispatch retain it. A separate reviewed host-only finalizer
may remove a control guard only after the operator explicitly confirms the
matching normal return or requested Download/recovery observation and durable
dispatch evidence is present. A guard inconsistency fails closed.

## Permanent exclusions

This process never permits `su`, arbitrary shell input, settings/property
mutation, service control, package permission grants, sideload, OTA, bootloader
unlock/lock, Odin payload options, fastboot, partition reads/writes, raw block
access, or any F1/X operation. Inactive shared-storage staging is not a
partition payload. Any command that hands bytes to a bootloader, recovery,
partition writer, package other than the exact APK installer, or executable
runtime leaves this process.

The permanent boot-only and forbidden-partition rules in `AGENTS.md` remain
unchanged. More restrictive target contracts continue to win; this common
process does not silently activate any action for S22+ or A90.

## Review lifetime

Independent review qualifies only the named common text, target contract,
runner, and tests at their reviewed hashes. Review is required again when an
allowlist grows, an artifact/package/destination changes, a new mutation type
is introduced, target selection weakens, or an incident exposes a new hazard.
Routine invocations do not require repeated review while that closure remains
unchanged.
