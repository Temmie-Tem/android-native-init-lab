# A90 Native Init Versioning Policy

Date: `2026-05-11`

This project uses two separate version axes.

## 1. Native Build Version: `MAJOR.MINOR.PATCH`

The numeric version is the canonical version for the native init boot artifact.

Examples:

- `A90 Linux init 0.9.60`
- `0.9.60`

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
Native build: A90 Linux init 0.9.60
Device build tag: v261
Boot image: stage3/boot_linux_v261.img
```

The embedded `v261` tag is the current native build tag for the verified
boot image. It does not mean every later `v###` cycle is a flashed
device build.

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
Cycle label: v184
Native build: A90 Linux init 0.9.60
Device flash: none
Host commit: <git-sha>
```

If a cycle does flash the device, it must state:

```text
Cycle label: v185
Native build: A90 Linux init 0.9.60
Device flash: stage3/boot_linux_0.9.60.img
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
0.9.60 = what is running on the phone
v184   = what project/test cycle is being executed
commit = what host/tooling source produced the evidence
hash   = exact binary/evidence artifact identity
```

## Current Example

The v184 24h readiness test is not a v184 boot image.

It is:

```text
Native build: A90 Linux init 0.9.60 (device running v261 build tag)
Cycle label: v184 24h Serverization Readiness Gate
Device flash: none
Purpose: validate long-run host/device stability before serverization work
```
