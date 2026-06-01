# Native Init V1392 Wi-Fi Test Boot Plan

## Summary

- Cycle: `V1392`
- Type: host/source design plan
- Native baseline: `A90 Linux init 0.9.68 (v724)`
- Target artifact: separate rollbackable Wi-Fi test boot image, not the main
  `v724` image
- Decision: `v1392-plan-wifi-test-boot-pid1-timing-path`

V1391 proved the helper-side early observer gate works, but the external helper
still reaches RC1 too late: RC1 assert appeared about `3.605s` after
`__subsystem_get(esoc0)`, while the Android reference path has shown a much
tighter early boot timing window. Another same-shape `/cache/bin` helper retry
is therefore low value. The next useful path is a dedicated test boot image
that moves the timing-critical observer/trigger sequence into PID1/native-init
boot flow.

## Goal

Build a dedicated native-init Wi-Fi test boot that can exercise the current
MDM3/RC1 timing experiment earlier than the external helper path, while keeping
the stable `v724` image as the rollback target.

The first test-boot target is not credentialed Wi-Fi usage. The first target is
evidence for one or more of:

- MDM2AP/GPIO142 response
- PCIe RC1 reaching L0
- MHI device or MHI pipe creation
- WLFW service `69`
- `wlan0` netdev creation

Only after `wlan0` appears reliably should a later, explicit gate add scan,
connect, DHCP, route, or external ping handling.

## Current Evidence

- V1391 report:
  `docs/reports/NATIVE_INIT_V1391_ANDROID_PARTICIPANT_EARLY_POWERUP_CORRECTED_RC1_LIVE_2026-06-01.md`
- Current stable native source:
  `stage3/linux_init/init_v724.c`
- Current v724 boot builder:
  `scripts/revalidation/build_native_init_boot_v724.py`
- Existing v724 one-shot boot hook:
  `stage3/linux_init/v724/90_main.inc.c`

The existing v724 QRTR/service-locator hook is useful precedent, but it is not
the right final form for this gate because it depends on `/cache/bin` and runs
as a post-ACM one-shot helper path. V1392 should treat it as a pattern for
private logs, one-shot flags, timeout handling, and safe fallback behavior.

## Design Options

### Option A: Reuse `/cache/bin/a90_android_execns_probe`

- Minimal code churn.
- Still depends on prior deploy state under `/cache/bin`.
- Still risks starting too late if cache/helper setup occurs after the narrow
  boot timing window.

Verdict: acceptable for emergency reproduction only, not preferred.

### Option B: Bundle the exact helper in the test ramdisk

- Add the verified `a90_android_execns_probe` helper to the test boot ramdisk as
  `/bin/a90_android_execns_probe`.
- Invoke the ramdisk helper from PID1 with a bounded mode and private log path.
- Removes `/cache/bin` deploy timing and missing-helper variance.
- Keeps the complex Android namespace experiment in the helper instead of
  duplicating it inside PID1.

Verdict: preferred V1393 implementation path.

### Option C: Move the minimal experiment directly into PID1 C

- Earliest possible control path.
- Highest code duplication and rollback risk.
- Harder to keep all prior helper safety checks in sync.

Verdict: defer until Option B proves helper spawn latency is still the blocker.

## Selected V1393 Path

Create a separate source/build-only test image using Option B:

1. Copy or include the v724 native init source under a new test build identity.
2. Add a Wi-Fi test-boot hook that uses `/bin/a90_android_execns_probe` from the
   ramdisk, not `/cache/bin`.
3. Keep the hook opt-in and bounded:
   - compile-time test image identity, plus
   - one-shot runtime flag or explicit test-mode marker.
4. Use private output files under `/cache` or `/mnt/sdext/a90/logs`.
5. Preserve console/shell availability and normal native boot fallback even if
   the helper is missing, times out, or exits non-zero.
6. Build the boot image locally only; do not flash during V1393.

## Proposed Hook Placement

The hook should run after the minimum surfaces needed by the helper exist:

- `/dev`, `/proc`, `/sys`
- block device nodes required for Android layout preparation
- enough native logging/timeline support to record outcome

It should run before late interactive services and before any slow external
control path:

- before autohud and optional netservice/rshell startup
- before any long soak/background tests
- before relying on `/cache/bin`

The test hook may call `prepare_android_layout(false)` and mount `selinuxfs` if
needed, matching the v724 precedent. The hook must not silently widen into
credentialed Wi-Fi behavior.

## Safety Scope

V1392/V1393 design and source/build gates remain below Wi-Fi bring-up.

Explicitly excluded until a later gate:

- Wi-Fi credential use
- Wi-Fi scan/connect
- DHCP, route changes, or external ping
- Wi-Fi HAL start
- direct PMIC/GPIO/GDSC writes
- blind eSoC notify or `BOOT_DONE` spoofing
- global PCI rescan or broad platform unbind/bind
- partition write
- flashing the test image during the source/build-only gate

The later live handoff gate may flash only the dedicated test image and must
name the rollback image explicitly, normally `stage3/boot_linux_v724.img`.

## Artifact Rules

- The main stable artifact remains `stage3/boot_linux_v724.img`.
- The test artifact should use a distinct filename such as
  `tmp/wifi/v1393-wifi-test-boot/boot_linux_v1393_wifi_test.img` or a clearly
  named `stage3/boot_linux_<test-tag>.img` only if that convention is chosen
  explicitly.
- Generated boot images and ramdisk CPIOs should stay out of commits unless the
  repository convention explicitly requires tracking them.
- The source, builder, plan, and verifier scripts may be committed.
- Reports must not contain SSID, passphrase, saved Android Wi-Fi config, or
  private token material.

## Verification Gates

### V1393 — source/build only

Required checks:

- static aarch64 PID1 build succeeds
- ramdisk contains `/init` and `/bin/a90_android_execns_probe`
- helper marker matches the expected helper version
- boot image strings contain the new test identity and no credentials
- boot image unpacks with expected ramdisk replacement and stable boot header
- `git diff --check` passes

No device command, flash, reboot, partition write, Wi-Fi scan/connect, DHCP, or
external ping.

### V1394 — artifact sanity verifier

Required checks:

- boot image mode is private if staged under `tmp`
- SHA256 manifest recorded
- expected markers present
- rollback image exists and is readable
- no credential strings in staged artifact or report

No live mutation.

### V1395 — bounded live handoff

Only after V1393/V1394 pass:

- flash the test boot through the existing flash helper/runbook path
- verify the test image banner
- collect boot log, dmesg RC1/MDM2AP/MHI/WLFW/`wlan0` evidence
- rollback to `stage3/boot_linux_v724.img` unless explicitly kept
- verify final `v724` health after rollback

No scan/connect/DHCP/external ping in this gate.

### V1396 — result classifier

Classify whether the test boot improved the downstream state:

- `gpio142-or-rc1-l0-progress`
- `mhi-or-wlfw-progress`
- `wlan0-created-below-connect`
- `no-progress-test-boot-clean`
- `test-boot-rollback-required`

Only if `wlan0` is stable should a later gate introduce credentialed connect
and `google.com` ping validation with private runtime credential handling.

## Next Action

Proceed to V1393 source/build-only implementation using a ramdisk-bundled helper
and a separate test boot artifact. Do not flash the test boot until the artifact
verifier passes and the live handoff gate explicitly names rollback evidence.
