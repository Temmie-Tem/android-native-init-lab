# A90 Native Init Versioning Policy

Date: `2026-05-11` (refreshed `2026-06-09`)

This project uses separate version axes. Do not collapse them into one `vNNN`
number.

For the combined day-to-day rulebook covering version axes, workspace paths, and
commit boundaries, read `docs/operations/WORKING_RULES.md` first.

## 1. Run ID: `VNNNN`

The run ID is the global project execution number.

Use it for:

- validation scripts
- live handoff runs
- source-build checks
- baseline-promotion reports
- host-only classifiers
- documentation decisions

Examples:

- `V2167` connect/DHCP/ping validation
- `V2168` QCACLD firmware_class validation route
- `V2169` next baseline-promotion run after `V2168`
- `V2175` baseline-promotion run for the `v2174-wifi-urandom-connect`
  artifact
- `V2179` baseline-promotion run for the `v2178-wifi-profile-autoconnect`
  artifact
- `V2183` baseline-promotion run for the `v2182-hud-menu-cleanup` artifact

Rules:

- A run ID is never a helper version.
- A run ID may or may not produce a new boot image.
- If a run promotes a new flashed baseline, use the next run ID for that
  promotion instead of reusing an older validation run ID.

## 2. Native Init Version: `MAJOR.MINOR.PATCH`

The numeric init version is the device-visible version for the native init boot
artifact.

Examples:

- `A90 Linux init 0.9.246`
- `A90 Linux init 0.9.247`
- `A90 Linux init 0.9.251`
- `A90 Linux init 0.9.253`
- `A90 Linux init 0.9.255`

Increase this version when the flashed boot artifact changes:

- PID 1 native init source changes and is rebuilt into `/init`
- ramdisk helper binaries or ramdisk layout change
- boot image, kernel command line, or boot packaging changes
- device-visible UI, shell, storage, network, service, or runtime behavior changes
- a fix requires flashing a new `workspace/private/inputs/boot_images/boot_linux_*.img`

Do not increase this version for host-only tooling, reports, plans, or validation
runs against an unchanged device image.

## 3. Build Tag: `vNNNN-purpose`

The build tag is embedded into the native init banner and usually appears in the
boot image filename.

Examples:

- `v726-wifi-lifecycle`
- `v2169-transport-contract`
- `v2182-hud-menu-cleanup`

Rules:

- The build tag describes the boot/init baseline, not the helper binary.
- When a promoted baseline corresponds to a global run, prefer using that run ID
  in the build tag: `v2169-*`.
- Do not use an older validation-route ID such as `V2167` or `V2168` as the
  promoted baseline tag unless that exact run produced and promoted the image.

## 4. Helper Version: `helper-vNNN`

Helper binaries have their own marker stream.

Example:

- `a90_android_execns_probe helper-v427`

Rules:

- Do not write bare `v427` in baseline summaries; write `helper-v427`.
- Do not use helper numbers in boot image filenames, run IDs, or init build tags.
- If a helper is embedded in a boot image, record both the helper marker and its
  SHA256.

## 5. Artifact Hash

SHA256 is the final identity for binary artifacts.

Record hashes for:

- boot images
- ramdisks
- static helper binaries
- important evidence bundles

If a boot image SHA changes, treat it as a distinct artifact even when the source
intent is unchanged. If that image becomes the rollback/test baseline, promote it
under a new run/build tag instead of silently replacing the old baseline SHA.

## 6. Required Report Header

Every non-trivial run or baseline report should state all relevant axes:

```text
Run ID: V2170
Native init: A90 Linux init 0.9.248
Build tag: v2170-<purpose>
Helper: a90_android_execns_probe helper-v427
Boot image: workspace/private/inputs/boot_images/boot_linux_v2170_<purpose>.img
Boot SHA256: <sha256>
Device flash: yes|no
Host commit: <git-sha-or-uncommitted>
```

For host-only or unchanged-image validation:

```text
Run ID: V2184
Native init: A90 Linux init 0.9.255 (v2182-hud-menu-cleanup)
Build tag: unchanged
Helper: unchanged
Device flash: no
Host commit: <git-sha-or-uncommitted>
```

## 7. Practical Reading Rule

Read versions in this order:

```text
V2183  = what project/test/promotion run was executed
0.9.255 = what native init build is visible on the phone
v2182-hud-menu-cleanup = what boot/init baseline role was flashed
helper-v427 = which helper binary marker is embedded or deployed
sha256 = exact binary/evidence artifact identity
```

## Current Example

Current verified HUD/menu cleanup baseline evidence is based on:

```text
Run ID: V2183
Native init: A90 Linux init 0.9.255 (v2182-hud-menu-cleanup)
Build tag: v2182-hud-menu-cleanup
Helper: a90_android_execns_probe helper-v427
Boot image: workspace/private/inputs/boot_images/boot_linux_v2182_hud_menu_cleanup.img
Boot SHA256: 8e3e16f68d019ef5f56d2246ddcc7dbf14aa5ae08b40a0b983688812d792f839
Evidence: V2182 source/build plus live UI validation and V2183 baseline promotion report
```

If this artifact is reproduced unchanged, keep the build tag and record the
same artifact SHA. If a future boot image changes, promote it under a new
run/build identity such as:

```text
Run ID: V2176
Native init: A90 Linux init 0.9.252
Build tag: v2176-<purpose>
Boot image: workspace/private/inputs/boot_images/boot_linux_v2176_<purpose>.img
Helper: a90_android_execns_probe helper-v427
```
