# S20+ G986N attended root-health D0 incident

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **EARLIER FAILURES RETAINED; LATER FRESH ROOT-HEALTH PASS; ZERO EFFECTS**

## Outcome

The first fresh direct attended request invoked the active fixed root-health D0
runner once. The runner selected the exact healthy S20+ row, bound its sole USB
metadata token to `get-devpath`, and then stopped while parsing the fixed
unprivileged pre-snapshot. It did not reach its fixed `su -c` ordinal.

The durable private failure receipt records:

- verdict `FAIL_S20PLUS_G986N_ATTENDED_ROOT_HEALTH_D0_READ_CLOSED`;
- three host commands: one global inventory and two exact-selected-target
  commands;
- one public snapshot command and zero root commands;
- zero commands to S22+, A90, or every other target; and
- zero device effects, writes, reboots, mode transitions, transfers, package,
  property/service, or partition operations.

The private `failure.json` is 1,110 bytes at SHA-256
`ddbab45528249b7c6c65e61d53e2a036ce5a4c67834ec78f7483038c5ebc1296`.
It is a direct link-count-one regular file owned by the invoking user, mode
`0400`, inside a newly allocated mode-`0700` run directory. Raw serial,
topology, boot ID, and inventory bytes were not retained in the receipt.

## Failure classification

The receipt intentionally retains only the exception class and a SHA-256
failure signature. Its class is `RootHealthD0Error`, and its signature is
`a796e18647a44a3cbf815f57dc6e2539c7ab8d6852ae83397affafaa04f007e7`.
Host-only comparison against the exact active runner's fixed exception strings
maps that signature to:

```text
selected target public snapshot has the wrong field count
```

This is a parser-stage classification, not retained raw transcript evidence.
The current evidence cannot distinguish a command-framing defect, unexpected
device stdout, or another source of extra/missing lines. No root-health field
was observed, so this run proves neither current root health nor root absence.

## Post-repair fresh invocation

Host-only qualification subsequently proved and corrected the public
`exec-out` double-escaping defect. The corrected active runner is 39,819 bytes
at SHA-256
`24f69cc5aa43c70558e3594534ee684db0a038e972d1b0db2f1b8d8446af2d44`.
A second fresh direct attended request invoked that corrected runner exactly
once.

The second invocation stopped earlier than the first: its initial global ADB
inventory command returned nonzero before any target row was selected. The
durable receipt records:

- one host command and one inventory command;
- zero selected-target, public-snapshot, and root commands;
- zero commands to S22+, A90, or every other selected target; and
- zero device effects, writes, reboots, mode transitions, transfers, package,
  property/service, or partition operations.

Its 1,110-byte mode-`0400`, link-count-one `failure.json` has SHA-256
`2b3839be4e8870f7e7d5778e064b0968d64d779086342edb7ee56cf6ba419b63`
inside a mode-`0700` runner-allocated directory. Its failure class is
`RootHealthD0Error`; signature
`50535d49f4116369bc60039e0610ce58a8a1da7b7b95feb34d37532feb6e6133`
maps against the corrected runner's fixed exception closure to:

```text
initial ADB inventory failed
```

The private receipt intentionally contains no raw inventory, stdout, stderr,
serial, topology, or boot ID. It therefore proves only a nonzero initial ADB
inventory result. It cannot distinguish device disconnect, authorization,
transport, daemon, client, or another host-side cause, and it proves nothing
about current Android or root health.

After the operator physically reconnected the device, a separately requested
routine public-property D0 invocation succeeded. Its private `result.json` has
SHA-256
`eaf9d0a7fe02b8d7088626fcdb304f4effed58cb319a6737ccf4a53173046004`.
It selected exactly one healthy
`SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2` row and observed
`boot_completed=1`, `bootanim=stopped`, verified-boot `orange`, and vbmeta
device state `unlocked`. Its command counts are four host commands, two global
inventories, two selected-target commands, zero other-target commands, and
zero root, write, reboot, mode-transition, transfer, or partition operations.

This later result supports restored ADB connectivity only at its collection
time. It neither identifies the cause of the earlier nonzero inventory result
nor proves SELinux or root health, and it does not authorize a root-health
invocation.

## Successful post-reconnect root-health invocation

A third, separately requested attended root-health invocation then ran the
corrected active runner exactly once and returned
`PASS_S20PLUS_G986N_ATTENDED_ROOT_HEALTH_D0`. Its 3,281-byte mode-`0400`,
link-count-one `result.json` has SHA-256
`88412056fb713ca127ea2bd56c0b86b1491435356faae2a371375b083ff1a180`
inside a mode-`0700` runner-allocated directory.

The exact fixed read observed:

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

Both public snapshots bound the same exact
`SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2` target and current boot with
`boot_completed=1`, `bootanim=stopped`, and SELinux enforcing. The final
inventory remained unchanged. Counts were six host commands, two inventories,
four selected-target commands, two public snapshots, and one fixed root read;
S22+, A90, every other target, device effects, writes, root writes, package or
property/service changes, reboots, mode transitions, transfers, and partition
access were all zero.

This proves only the fixed root/Magisk/SELinux/PID-1 health fields at that
collection time. It is not generic root authority, a standing lease, module or
native-init health, recovery/rollback proof, R1 authority, or F1 readiness.

## No-replay and recovery boundary

Both failed invocations remain terminal and neither was retried. The later
successful invocation was a new request, not a replay or continuation. No
device recovery action is required because all three invocations had zero
device effects. The active runner must not be bypassed with an interactive,
generic, or caller-selected `su` command. A later root-health attempt still
requires another fresh direct attended request; no consumed request, failure
receipt, or success result grants replay or standing authority.

The separate routine public-property D0 result remains supportive only for its
own collection time and scope. The later fixed root-health success is likewise
time-bounded and authorizes no further root, R1, or F1 action.
