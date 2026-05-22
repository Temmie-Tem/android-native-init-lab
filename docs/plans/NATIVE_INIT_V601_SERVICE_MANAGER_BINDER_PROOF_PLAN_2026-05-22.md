# Native Init V601 Service-Manager Binder Proof Plan

- date: `2026-05-22 KST`
- status: `planned`; live proof requires current-boot preconditions
- runner: `scripts/revalidation/native_wifi_modem_holder_service_manager_v601.py`

## Objective

Validate whether the V600 CNSS blocker is caused by missing Android binder
service-manager runtime around `cnss-daemon`.

V601 preserves the V598 lower-readiness path:

- global `/vendor/firmware_mnt` and `/vendor/firmware-modem` mounts;
- `subsys_modem`-only holder, with no `esoc0` open;
- QRTR RX gate before companion start;
- companion order `qrtr-ns`, `rmt_storage`, `tftp_server`, `pd-mapper`,
  `cnss_diag`, `cnss-daemon`;
- WLFW QRTR nameservice readback for service `69` instances `0` and `1`.

The only deliberate expansion is service-manager runtime:

- `servicemanager`;
- `hwservicemanager`;
- `vndservicemanager /dev/vndbinder`;
- Android-captured copy-real linkerconfig.

## Inputs

- V490 current-boot SELinux policy load manifest:
  `tmp/wifi/v601-v490-current-run/manifest.json`
- Android companion identity contract:
  `tmp/wifi/v525-android-companion-identity/manifest.json`
- Android-captured linkerconfig files on device:
  - `/cache/bin/a90_real_ld.config.txt`
  - `/cache/bin/a90_real_apex.libraries.config.txt`
- Helper v100 or newer:
  `/cache/bin/a90_android_execns_probe`

## Method

1. Run V601 preflight and require:
   - native baseline is healthy;
   - V490 policy load is current for this boot;
   - helper exposes `wifi-companion-vnd-service-manager-start-only`,
     `--allow-service-manager-start-only`, and `--allow-qrtr-ns-readback`;
   - copy-real linkerconfig files are present on device;
   - no target companion/service-manager process is already active;
   - no `wlan0` or Wi-Fi link surface is already present.
2. During the live proof:
   - materialize global firmware mounts;
   - open only `subsys_modem`;
   - wait for QRTR RX;
   - start the bounded service-manager companion window;
   - read back WLFW QRTR nameservice without sending QMI payloads;
   - capture dmesg, QRTR, process, child lifecycle, and helper transcript;
   - reboot for cleanup.
3. Classify whether service-manager runtime:
   - clears the V600 binder transaction failures;
   - advances to service-notifier `74`, WLAN-PD, WLFW, BDF, FW-ready, or
     `wlan0`;
   - or leaves WLFW service `69` unpublished.

## Guardrails

- No Wi-Fi HAL, `wificond`, supplicant, or hostapd start.
- No `qcwlanstate` or sysfs driver-state write.
- No scan/connect/link-up.
- No credential, DHCP, route, or external ping.
- No boot image or persistent partition write.
- `esoc0` must not be opened.
- Reboot is the cleanup boundary after live execution.

## Success Criteria

- Evidence is written under `tmp/wifi/v601-modem-holder-service-manager/`.
- The manifest records `service_manager_start_executed=True` only for the
  bounded live service-manager companion window.
- `wifi_hal_start_executed=False`.
- `wlan_driver_state_write_executed=False`.
- `scan_connect_executed=False`.
- `external_ping_executed=False`.
- The decision separates one of these outcomes:
  - service-manager linker gap;
  - binder gap persists;
  - binder gap clears but WLFW remains missing;
  - service-notifier `74`/WLAN-PD/WLFW registration advances.

## Expected Next Gate

If binder failures clear but service-notifier `74` and WLFW service `69` are
still missing, the next gate should classify the missing sibling service
registry/sysmon or WLAN-PD trigger before retrying `qcwlanstate`, Wi-Fi HAL, or
any scan/connect path.
