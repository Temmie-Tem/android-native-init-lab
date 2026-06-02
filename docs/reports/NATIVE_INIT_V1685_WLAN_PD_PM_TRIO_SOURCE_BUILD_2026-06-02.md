# Native Init V1685 WLAN-PD PM-trio Source Build

## Summary

- Cycle: `V1685`
- Type: source/build-only
- Decision: `v1685-wlan-pd-pm-trio-source-build-pass`
- Result: PASS
- Artifact: `tmp/wifi/v1685-wlan-pd-pm-trio-source-build/boot_linux_v1393_wifi_test.img`
- Boot SHA256: `4b59d0b89ce2ecf590ccfa6c99b54f66ea27b5f6ea35bfbe0ef5ab60046dfa41`

## Scope

V1685 implements the source/build unit selected by V1684:

- preserve the V1683 internal-modem WLAN-PD firmware-serve route and `/dev/subsys_modem` holder;
- add only `pm_proxy_helper`, `per_mgr`, and `per_proxy` before `cnss-daemon`;
- emit `wlan_pd_pm_service_window_trigger.*` label evidence;
- keep `mdm_helper`, `/dev/subsys_esoc0`, raw eSoC ioctl, forced RC1, fake-ONLINE, Wi-Fi HAL, `wificond`, scan/connect, credentials, DHCP/routes, and external ping disabled.

No live execution, flash, partition write, firmware write, Wi-Fi HAL start, scan/connect, DHCP, routing, credential use, or external ping occurred in this cycle.

## Changes

- `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - Bumped helper marker to `a90_android_execns_probe v308`.
  - Added mode `wifi-companion-wlan-pd-pm-service-window-trigger-start-only`.
  - Added fail-closed flag `--allow-wlan-pd-pm-service-window-trigger`.
  - Added PM-trio children (`pm_proxy_helper`, `per_mgr`, `per_proxy`) before `cnss-daemon`.
  - Added `wlan_pd_pm_service_window_trigger.*` classification keys.

- `stage3/linux_init/v724/90_main.inc.c`
  - Added `A90_WIFI_TEST_BOOT_WLAN_PD_PM_SERVICE_WINDOW_TRIGGER`.
  - Generates PID1 helper argv for the new PM-trio mode.

- `scripts/revalidation/build_native_init_wifi_test_boot_v1393.py`
  - Added `--wifi-test-helper-mode wlan-pd-pm-service-window-trigger`.
  - Updated helper marker/SHA contract for v308.
  - Added source/build contract checks for the new mode and allow flag.

## Validation

Command:

```text
python3 scripts/revalidation/build_native_init_wifi_test_boot_v1393.py \
  --cycle v1685 \
  --decision v1685-wlan-pd-pm-trio-source-build-pass \
  --cycle-label v1685 \
  --wifi-test-klog-prefix A90v1685 \
  --wifi-test-disable /cache/native-init-wifi-test-boot-v1685.disable \
  --wifi-test-log /cache/native-init-wifi-test-boot-v1685.log \
  --wifi-test-summary /cache/native-init-wifi-test-boot-v1685.summary \
  --wifi-test-helper-result /cache/native-init-wifi-test-boot-v1685-helper.result \
  --wifi-test-pid /cache/native-init-wifi-test-boot-v1685.pid \
  --wifi-test-watcher-pid /cache/native-init-wifi-test-boot-v1685-watcher.pid \
  --wifi-test-helper-mode wlan-pd-pm-service-window-trigger \
  --wifi-test-firmware-mounts \
  --out-dir tmp/wifi/v1685-wlan-pd-pm-trio-source-build
```

Checks:

| check | result |
| --- | --- |
| helper marker | `a90_android_execns_probe v308` |
| helper SHA256 | `63cd24cf0fb99c3cf294149809bc2dedfb90b70f70f0269b250e3c61e885663c` |
| helper static | PASS, no dynamic section / no `INTERP` |
| init static | PASS, no dynamic section / no `INTERP` |
| new runtime mode present | PASS |
| `--allow-wlan-pd-pm-service-window-trigger` present | PASS |
| `wlan_pd_pm_service_window_trigger.*` label keys present | PASS |
| no `mdm_helper` contract in PM label | PASS |
| no Wi-Fi HAL/wificond contract in PM label | PASS |
| exact credential bytes absent | PASS |
| out-dir artifacts private | PASS, `0600` |

Build warnings were pre-existing truncation/unused-function warnings in older helper/PID1 paths; the build completed and all contract checks passed.

## Next Gate

Next cycle should be one rollbackable live handoff only:

- flash the V1685 test boot;
- run one bounded window;
- collect `wlan_pd_pm_service_window_trigger.label`;
- rollback to `stage3/boot_linux_v724.img`;
- verify `selftest fail=0`.

Allowed live labels:

- `wlfw-start-reached`
- `pm-trio-still-no-wlfw`
- `pm-trio-child-failed`
- `service-window-child-failed`
- `modem-holder-regression`

Do not proceed to MSA/BDF, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping until `wlfw-start-reached` or WLFW service 69 appears.
