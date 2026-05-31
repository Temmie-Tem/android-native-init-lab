# A90 Native Init Versioning Policy

Date: `2026-05-11` (refreshed `2026-05-31`)

This project uses two separate version axes.

## 1. Native Build Version: `MAJOR.MINOR.PATCH`

The numeric version is the canonical version for the native init boot artifact.

Examples:

- `A90 Linux init 0.9.68`
- `0.9.68`

Increase this version only when the device boot artifact changes:

- PID 1 native init source changes and is rebuilt into `/init`
- ramdisk helper binaries or ramdisk layout change
- boot image, kernel command line, or boot image packaging changes
- device-visible native UI, shell, storage, network, service, or runtime behavior changes
- a fix requires flashing a new `stage3/boot_linux_*.img`

Do not increase this version for host-only tooling, reports, plans, or validation
cycles that run on an unchanged device image.

Current canonical native build:

```text
Native build: A90 Linux init 0.9.68
Device build tag: v724
Boot image: stage3/boot_linux_v724.img
```

When a boot image is built, the **latest `v###` cycle at build time is embedded
into the image** and shown in the banner as `0.9.68 (v724)`. The embedded tag
stays fixed until the next flash, even as later `v###` cycles advance. So the
embedded `v724` does not mean every later cycle (the project is at V1253) is a
flashed device build — it only marks which cycle produced the image now running.

## 2. Project Cycle: `v###`

The `v###` label is the project execution cycle.

It may represent:

- host validation tooling
- security patch batches
- planning/reporting milestones
- long-soak or mixed-soak gates
- documentation-only decisions
- native boot image releases

Therefore a `v###` cycle may or may not flash the device.

Every `v###` plan or report must state:

```text
Cycle label: V1253
Native build: A90 Linux init 0.9.68 (v724)
Device flash: none
Host commit: <git-sha>
```

If a cycle does flash the device, it must state (and bump the numeric version):

```text
Cycle label: v724
Native build: A90 Linux init 0.9.68 (v724)
Device flash: stage3/boot_linux_v724.img
Boot image SHA256: <sha256>
Host commit: <git-sha>
```

## 3. Git Commit

The Git commit identifies the exact repository state used for a test, report,
or artifact build.

Reports should record the commit even when neither the native build version nor
the project cycle changes.

## 4. Artifact Hash

Boot images, ramdisks, static helpers, and important evidence bundles should
record SHA256 hashes.

The artifact hash is the final identity for reproduced deployment or validation.

## Practical Reading Rule

Read versions in this order:

```text
0.9.68 = what is running on the phone (boot image identity)
V1253  = what project/test cycle is being executed now
commit = what host/tooling source produced the evidence
hash   = exact binary/evidence artifact identity
```

## Current Example

The current device build `v724` was a native boot image release because it
changed PID 1 boot behavior (qrtr-ns boot hook). It is:

```text
Native build: A90 Linux init 0.9.68 (device running v724 build tag)
Cycle label: v724 QRTR service-locator boot proof
Device flash: stage3/boot_linux_v724.img
Purpose: qrtr-ns boot hook so service-locator connects ~4.4s from boot
```

By contrast, a host-only research cycle such as `V1253` runs against this same
unchanged `0.9.68 (v724)` image, so it states `Device flash: none`. See the
per-release numeric history in `CHANGELOG.md` and the cycle history in
`CLAUDE.md`.
