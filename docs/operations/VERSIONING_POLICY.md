# A90 Native Init Versioning Policy

Date: `2026-05-11` (refreshed `2026-06-12`)

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
- `V2187` baseline-promotion run for the `v2187-screenapp-ui-validation`
  artifact
- `V2190` baseline-promotion run for the `v2189-security-p0-stage-fix`
  artifact
- `V2234` baseline-promotion run for the `v2232-service-object-fwclass-bridge`
- `V2236` baseline-promotion run for the `v2236-strict-wifi-connect`
  artifact
- `V2237` baseline-promotion run for the `v2237-supplicant-terminate-poll`
  artifact
- `V2256` baseline-promotion run for the `v2254-wifi-detail-surface`
  artifact

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
- `A90 Linux init 0.9.261`
- `A90 Linux init 0.9.266`
- `A90 Linux init 0.9.267`
- `A90 Linux init 0.9.268`
- `A90 Linux init 0.9.272`

Increase this version when the flashed boot artifact changes:

- PID 1 native init source changes and is rebuilt into `/init`
- ramdisk helper binaries or ramdisk layout change
- boot image, kernel command line, or boot packaging changes
- device-visible UI, shell, storage, network, service, or runtime behavior changes
- a fix requires flashing a new `workspace/private/inputs/boot_images/boot_linux_*.img`

Do not increase this version for host-only tooling, reports, plans, or validation
runs against an unchanged device image.

### 2.1 Which field moves (`MAJOR` / `MINOR` / `PATCH`) — adopted 2026-06-19

The three fields carry distinct meaning. Historically only `PATCH` ever moved
(`0.9.68` → `0.9.293`); going forward:

- **`PATCH` (the `z` in `0.9.z`)** — bump per flashed boot artifact change, exactly as
  the rules above describe. This is the default and the common case.
- **`MINOR` (the `y` in `0.y.z`)** — bump when a **chartered major-feature epic reaches
  device-proven promotion** (the capability works on-device *and* its image is adopted as a
  kept/promoted baseline), e.g. audio → `0.10.0`, then video → `0.11.0`. **Reset `PATCH` to
  `0`** on a `MINOR` roll (`0.10.0`, `0.10.1`, …); absolute build history is preserved by the
  monotonic run ID `VNNNN` and build tag `vNNNN`, so the reset loses nothing. **Epic-level
  only** — do not roll `MINOR` for sub-features, mid-epic progress, or host-only work. Do
  **not** retroactively renumber already-closed epics (WLAN / USB gadget / kernel recon all
  landed during `0.9.x`); the convention starts prospectively with audio → `0.10.0`.
- **`MAJOR` (the `x` in `x.y.z`) → `1.0.0`** — reserved for a **full distribution / userspace
  release**: a real init/service manager bringing up a usable userland (shell + networking +
  the feature set) as a releasable image. This is deliberately distinct from the current
  single static-`/init` PID 1 with a command/menu surface — that line stays `0.y.z`. Do not
  reach `1.0` until that distro-userspace bar is actually met.

## 3. Build Tag: `vNNNN-purpose`

The build tag is embedded into the native init banner and usually appears in the
boot image filename.

Examples:

- `v726-wifi-lifecycle`
- `v2169-transport-contract`
- `v2182-hud-menu-cleanup`
- `v2189-security-p0-stage-fix`
- `v2232-service-object-fwclass-bridge`
- `v2236-strict-wifi-connect`
- `v2237-supplicant-terminate-poll`
- `v2254-wifi-detail-surface`

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
Run ID: V2191
Native init: A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)
Build tag: unchanged
Helper: unchanged
Device flash: no
Host commit: <git-sha-or-uncommitted>
```

## 7. Practical Reading Rule

Read versions in this order:

```text
V2190  = what project/test/promotion run was executed
0.9.261 = what native init build is visible on the phone
v2189-security-p0-stage-fix = what boot/init baseline role was flashed
helper-v427 = which helper binary marker is embedded or deployed
sha256 = exact binary/evidence artifact identity
```

## Current Example

Current promoted audio-core candidate evidence is based on:

```text
Run ID: V2815
Native init: A90 Linux init 0.10.0 (v2812-audio-core-promotion-candidate)
Build tag: v2812-audio-core-promotion-candidate
Helper: native init embedded audio command surface; helper marker unchanged unless a report states otherwise
Boot image: workspace/private/inputs/boot_images/boot_linux_v2812_audio_core_promotion_candidate.img
Boot SHA256: 9cf680ae7dce1dac53b58a72e98668f5f6347bc14d6a64428f06ce2af830cdd0
Evidence: V2812 source/build, V2814 audio play live validation, and V2815 promotion report
Safety rollback net: v2321 remains the flash-gate rollback target until AGENTS.md is deliberately updated
```

Current post-promotion audio observability candidate evidence is based on:

```text
Run ID: V2837
Native init: A90 Linux init 0.10.9 (v2835-audio-help-surface)
Build tag: v2835-audio-help-surface
Boot image: workspace/private/inputs/boot_images/boot_linux_v2835_audio_help_surface.img
Boot SHA256: 53ef5d1155b7833dcb05d6ecc6d9dfabfd336b9c66f695b1aa789eb9e5ba6aca
Evidence: V2828 source/build, V2829 audio status/selftest/screenapp route-map live validation, V2830 read-only audio profile/stage/speaker-map API live validation, V2831 source/build, V2832 screenapp audio-profile live validation, V2833 source/build, V2834 screenapp audio-stages live validation, V2835 source/build, V2836 help/cmdmeta live validation, and V2837 same-candidate audio-play regression validation
Safety rollback net: v2321 remains the flash-gate rollback target until AGENTS.md is deliberately updated
```

Current post-promotion audio productization candidate evidence is based on:

```text
Run ID: V2840
Native init: A90 Linux init 0.10.11 (v2840-audio-chime-screen)
Build tag: v2840-audio-chime-screen
Boot image: workspace/private/inputs/boot_images/boot_linux_v2840_audio_chime_screen.img
Boot SHA256: 57a61bf47f5da326d7faf6a9fcf1284accf6f9628b4a8bb25679a670c31dbb58
Evidence: V2840 source/build report plus V2841 live validation of display-only screenapp audio-chime and APPS/AUDIO CHIME surface; V2839 remains the live audio chime execution proof
Adoption state: device-validated post-promotion candidate
Safety rollback net: v2321 remains the flash-gate rollback target until AGENTS.md is deliberately updated
```

Historical Wi-Fi detail surface promotion evidence remains:

```text
Run ID: V2256
Native init: A90 Linux init 0.9.272 (v2254-wifi-detail-surface)
Build tag: v2254-wifi-detail-surface
Helper: a90_android_execns_probe helper-v427 marker, SHA256 062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910
Boot image: workspace/private/inputs/boot_images/boot_linux_v2254_wifi_detail_surface.img
Boot SHA256: c668e9cd9a3621c955fa369c5d106271a96a949dcaec3774a5719d24b8ba19e9
Evidence: V2254 source/build, V2255 Wi-Fi detail surface live validation, and V2256 promotion report
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
