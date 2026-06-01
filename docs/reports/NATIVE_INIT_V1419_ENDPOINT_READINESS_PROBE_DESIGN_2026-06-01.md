# Native Init V1419 Endpoint Readiness Probe Design

## Summary

- Cycle: `V1419`
- Type: host/source-only design gate
- Decision: `v1419-endpoint-readiness-sampler-design-ready`
- Result: PASS for design; still BLOCKED for Wi-Fi connect readiness
- Inputs:
  - `docs/reports/NATIVE_INIT_V1418_WIFI_TEST_BOOT_DELAYED_RC1_EXPANDED_DMESG_HANDOFF_2026-06-01.md`
  - `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md`
  - `docs/reports/NATIVE_INIT_V1239_POST_ESOC0_POWERUP_GAP_CLASSIFIER_2026-05-31.md`
  - `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt`
  - `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/android/commands/interrupts-focus.txt`
  - `tmp/wifi/v1418-wifi-test-boot-delayed-rc1-expanded-dmesg-handoff/test-v1393-dmesg.stdout.txt`

## Current Classification

V1418 closes the previous uncertainty: the delayed test boot executes the
normal corrected RC1 enumerate path.

| Signal | Android V852 | Native V1418 |
| --- | --- | --- |
| `esoc0` to RC1 assert | about `0.255s` | about `0.277s` |
| RC1 assert/reset path | present | present |
| `PCIE20_PARF_INT_ALL_MASK` | `0x7f80c202` | `0x7f80c202` |
| PHY ready | present | present |
| reset release | present | present |
| first downstream LTSSM | `DETECT_QUIET -> L0` | `DETECT_QUIET -> POLL_ACTIVE -> POLL_COMPLIANCE` |
| RC1 link result | L0/GEN2 | fail, `LTSSM_STATE:0x3` |
| GPIO142 / `mdm status` IRQ | count `1` in Android evidence | not sampled in V1418 |
| MHI / WLFW / BDF / `wlan0` | present | absent |

The remaining blocker is not scan/connect, credentials, DHCP, or Wi-Fi HAL. It
is the endpoint response after PERST release. Android proves SDX50M responds
and reaches L0; native V1418 releases PERST but the endpoint never exits
poll-compliance.

## V1420 Candidate

Build a new rollbackable test boot that keeps the V1414 delayed-RC1 behavior
but adds a read-only PID1 RC1-window sampler. The sampler should run in the
same PID1 watcher child that already detects `esoc0`/powerup and triggers
corrected RC1.

### Required Samples

Capture these snapshots into a private result file:

1. `pre_delay`: after the first `esoc0`/powerup marker is detected and before
   the `250ms` delay.
2. `pre_rc1`: after the delay and immediately before writing corrected RC1.
3. `post_rc1_50ms`: about `50ms` after the RC1 write.
4. `post_rc1_150ms`: about `150ms` after the RC1 write.
5. `post_rc1_500ms`: about `500ms` after the RC1 write.

Each snapshot should attempt read-only collection of:

- `/proc/interrupts` lines matching `mdm status`, `gpio`, `142`, `pcie`, `mhi`
- `/sys/kernel/debug/gpio` lines matching GPIO `102`, `104`, `135`, `142`
- pinctrl debug lines for the same GPIOs if a readable pinctrl debugfs path is
  available
- optional PCIe debugfs status files that are ordinary reads only

Do not write pci-msm `case=26` in this sampler. Although V1368 showed that
status read can be clean, it is still a debugfs write path and should remain
outside this read-only sampler until specifically justified.

### Output Contract

Use a new result path, for example:

- `/cache/native-init-wifi-test-boot-v1420-rc1-window.result`

The result should include:

- watcher trigger line
- detect/write elapsed times
- delay value
- each snapshot label
- interrupt counts or `unreadable`
- GPIO/pinctrl excerpts or `unreadable`
- whether any snapshot observed GPIO142/`mdm status` count increase

## Success Criteria

V1420 source/build passes if:

- static PID1 build succeeds
- test boot artifact has a new version/build identity
- existing V1414 delayed-RC1 behavior is preserved
- new sampler markers appear in the boot image
- no credential-like bytes appear in staged artifacts
- no live command, flash, partition write, scan/connect, DHCP/routes, or
  external ping occurs

V1421 should independently sanity-check the exact artifact.

V1422 rollbackable live handoff may then classify:

- GPIO142/`mdm status` count remains zero across RC1 window:
  endpoint never signals readiness after PERST release.
- GPIO142/`mdm status` changes but no L0:
  AP sees endpoint status but PCIe link training still fails.
- L0/MHI/WLFW/`wlan0` appears:
  proceed to the next lower Wi-Fi gate, still below scan/connect unless
  `wlan0` is stable.

## Safety Scope

This design is below Wi-Fi bring-up. It does not permit Wi-Fi scan/connect,
credential handling, DHCP/routes, external ping, Wi-Fi HAL start, PMIC/GPIO/GDSC
direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan,
platform bind/unbind, pci-msm `case` writes, or partition writes.
