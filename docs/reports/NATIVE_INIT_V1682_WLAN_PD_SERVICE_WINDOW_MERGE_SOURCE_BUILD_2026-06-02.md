# Native Init V1682 WLAN-PD Service-window Merge Source Build

## Summary

- Cycle: `V1682`
- Type: source/build-only
- Decision: `v1682-wlan-pd-service-window-merge-source-build-pass`
- Result: PASS
- Artifact: `tmp/wifi/v1682-wlan-pd-service-window-merge-source-build/boot_linux_v1393_wifi_test.img`
- Boot SHA256: `5b3a5d44dbcefb44f264c4404d449e2ce134129c2f12540f877e94417eb351d5`

## Scope

V1682 implements the next source/build unit after V1681:

- preserve the V1680 WLAN-PD firmware-serve route and modem-only `/dev/subsys_modem` holder;
- add service-manager surface only, not Android Wi-Fi HAL or scan/connect;
- emit a route-specific `wlan_pd_service_window_trigger.*` summary;
- keep `/dev/subsys_esoc0`, raw eSoC ioctl, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, DHCP/routes, credentials, and external ping disabled.

No live device execution, flash, partition write, firmware write, scan/connect, DHCP, routing, credential use, or external ping occurred in this cycle.

## Changes

- `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - Bumped helper marker to `a90_android_execns_probe v307`.
  - Added mode `wifi-companion-wlan-pd-service-window-trigger-start-only`.
  - Added fail-closed flag `--allow-wlan-pd-service-window-trigger`.
  - Reused the V1680 modem-only holder and firmware-serve summary.
  - Added bounded `wlan_pd_service_window_trigger.*` evidence keys for WLFW-start classification.

- `stage3/linux_init/v724/90_main.inc.c`
  - Added `A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_WINDOW_TRIGGER`.
  - Generates PID1 helper argv for the new mode with service-manager, CNSS, QRTR readback, service-locator, and service-notifier allow flags.

- `scripts/revalidation/build_native_init_wifi_test_boot_v1393.py`
  - Added `--wifi-test-helper-mode wlan-pd-service-window-trigger`.
  - Added source/build contract checks for the new mode and allow flag.
  - Pins helper v307 SHA256.
  - Forces out-dir helper/init/boot/manifest artifacts to `0600`.

## Validation

Command:

```text
python3 scripts/revalidation/build_native_init_wifi_test_boot_v1393.py \
  --cycle v1682 \
  --decision v1682-wlan-pd-service-window-merge-source-build-pass \
  --cycle-label v1682 \
  --wifi-test-klog-prefix A90v1682 \
  --wifi-test-disable /cache/native-init-wifi-test-boot-v1682.disable \
  --wifi-test-log /cache/native-init-wifi-test-boot-v1682.log \
  --wifi-test-summary /cache/native-init-wifi-test-boot-v1682.summary \
  --wifi-test-helper-result /cache/native-init-wifi-test-boot-v1682-helper.result \
  --wifi-test-pid /cache/native-init-wifi-test-boot-v1682.pid \
  --wifi-test-watcher-pid /cache/native-init-wifi-test-boot-v1682-watcher.pid \
  --wifi-test-helper-mode wlan-pd-service-window-trigger \
  --wifi-test-firmware-mounts \
  --out-dir tmp/wifi/v1682-wlan-pd-service-window-merge-source-build
```

Checks:

| check | result |
| --- | --- |
| helper marker | `a90_android_execns_probe v307` |
| helper SHA256 | `ac8f4904c72f1688ebd88510c883060d17e2439b1c514fe12cf9077b4ecca90a` |
| helper static | PASS, no dynamic section / no `INTERP` |
| init static | PASS, no dynamic section / no `INTERP` |
| new runtime mode present | PASS |
| `--allow-wlan-pd-service-window-trigger` present | PASS |
| `--allow-service-manager-start-only` present | PASS |
| Android Wi-Fi service-window allow flag absent | PASS |
| forced PCIe/eSoC observer flags absent from PID1 argv contract | PASS |
| SSID/password bytes absent | PASS |
| out-dir artifacts private | PASS, `0600` |

Build warnings were pre-existing truncation/unused-function warnings in older helper/PID1 paths; the build completed and all contract checks passed.

## Next Gate

Next cycle should be one rollbackable live handoff only after review:

- flash the V1682 test boot;
- run one bounded window;
- collect `wlan_pd_service_window_trigger.label`;
- rollback to `stage3/boot_linux_v724.img`;
- verify `selftest fail=0`.

Allowed live labels:

- `wlfw-start-reached`
- `service-window-still-no-wlfw`
- `modem-holder-regression`
- `service-window-child-failed`

Do not proceed to MSA/BDF, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping until `wlfw-start-reached` or WLFW service 69 appears.
