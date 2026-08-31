# S20+ G986N attended root-health D0 incident

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **TERMINAL READ-CLOSED; ROOT COMMAND NOT ATTEMPTED**

## Outcome

One fresh direct attended request invoked the active fixed root-health D0
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

## No-replay and recovery boundary

The invocation is terminal and was not retried. Because no root command or
device effect occurred, it requires no device recovery action. The active
runner must not be bypassed with an interactive, generic, or caller-selected
`su` command. A later root-health attempt requires a separately justified and
reviewed host correction if needed, followed by a new direct attended request;
the consumed request and this failure receipt grant no replay authority.

The most recent separate routine public-property D0 result remains supportive
only for its own collection time and scope. It does not upgrade this failed
root-health invocation, prove current root availability, or authorize any
root, R1, or F1 action.
