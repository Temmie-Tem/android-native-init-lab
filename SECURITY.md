# Security Policy

## Scope

This repository contains host-side analysis tooling, documentation, and
native-userspace source for research on Android vendor kernels. It does not
distribute firmware, vendor binaries, or exploits.

**In scope:** defects in code published in this repository — for example an
analyzer or validator that can be made to accept unsafe input, tooling that
could damage a device outside its declared risk tier, a documented procedure
whose recovery path is unsound, or a private identifier that reached the
published tree.

**Out of scope:** vulnerabilities in Android, in vendor firmware, or in
third-party components. Please report those to the relevant vendor rather than
here. Requests for help attacking a device you do not own are also out of scope
and will not be answered.

## Reporting

Please do **not** open a public issue first for a security-sensitive finding.

Use GitHub's private vulnerability reporting for this repository
(Security → Report a vulnerability). If that is unavailable, open an issue that
states only that you have a security report and requests a private channel —
without the details.

A useful report includes:

- the affected component or file;
- reproduction conditions;
- whether physical ownership or control of a device is required to trigger it;
- the impact you believe it has.

## Expectations

This is a personal research project maintained by one person, so please expect
best-effort rather than guaranteed response times. Reports that turn out to be
real will be fixed in the public tree and credited in the commit unless you ask
otherwise.

## A note on device safety

Much of this repository describes actions that can render a phone unbootable if
performed incorrectly. The safety contract in [`AGENTS.md`](AGENTS.md) exists
precisely to bound that. If you find a case where the documented procedure or
the tooling permits an action **outside** its declared risk tier — for example a
path that could write a forbidden partition, or a flow that lacks a working
rollback — that is a security-relevant defect and is welcome as a report.

## Published identifiers

Device serials and other private identifiers must not appear in the published
tree. The rules and the enforcing check are described in
[`docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md`](docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md).
If you find one that the check does not catch, that is a reportable defect in
the check.
