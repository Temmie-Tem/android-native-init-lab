# S20+ G986N attended root-health D0 incident

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **TWO TERMINAL READ-CLOSED INVOCATIONS; ROOT NEVER ATTEMPTED**

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

## No-replay and recovery boundary

Both invocations are terminal and neither was retried. Because neither reached
a root command or device effect, no device recovery action is required. The
active runner must not be bypassed with an interactive, generic, or
caller-selected `su` command. Any host/transport diagnosis remains a separate
bounded action, and a later root-health attempt requires another fresh direct
attended request. Neither consumed request nor either failure receipt grants
replay authority.

The most recent separate routine public-property D0 result remains supportive
only for its own collection time and scope. It does not upgrade this failed
root-health invocation, prove current root availability, or authorize any
root, R1, or F1 action.
