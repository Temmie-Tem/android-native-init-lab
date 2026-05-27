# V1123 Private Firmware PM Observer Helper Build Report

Date: `2026-05-27`

## Result

- Decision: `v1123-private-firmware-pm-observer-helper-build-pass`
- Pass: `true`
- Evidence: `tmp/wifi/v1123-execns-helper-v212-build/manifest.json`
- Collector: `scripts/revalidation/native_wifi_private_firmware_pm_observer_helper_build_v1123.py`
- Helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`

## Summary

V1123 adds an opt-in private firmware mount path for PM observer mode.

Changes:

- Bumped helper marker to `a90_android_execns_probe v212`.
- Added flag `--pm-observer-private-firmware-mounts`.
- Kept existing PM observer behavior unchanged unless that flag is present.
- Reused the existing private-namespace `apnhlos` and `modem` mount machinery.
- Added PM observer output markers:
  - `private_firmware_mounts_requested`;
  - `private_firmware_mnt_mounted`;
  - `private_firmware_modem_mounted`.

Build output:

```text
artifact=tmp/wifi/v1123-execns-helper-v212-build/a90_android_execns_probe
sha256=65fe14f0d7095786d8228750e309e0a1b5d40c33825d1debb87870d9caba0ef3
```

## Safety

- `device_commands_executed=false`
- `deploy_executed=false`
- `pm_actor_executed=false`
- `cnss_daemon_start_executed=false`
- `wifi_hal_start_executed=false`
- `scan_connect_executed=false`
- `credential_use_executed=false`
- `external_ping_executed=false`
- `reboot_executed=false`

## Validation

Executed:

```bash
python3 scripts/revalidation/native_wifi_private_firmware_pm_observer_helper_build_v1123.py run
python3 -m py_compile scripts/revalidation/native_wifi_private_firmware_pm_observer_helper_build_v1123.py scripts/revalidation/wifi_execns_helper_v212_deploy_preflight.py scripts/revalidation/native_wifi_private_firmware_pm_observer_live_v1124.py
git diff --check
```

## Next

V1124 should deploy helper `v212`, then run the private-firmware PM observer
live gate. Wi-Fi HAL and scan/connect remain forbidden.
