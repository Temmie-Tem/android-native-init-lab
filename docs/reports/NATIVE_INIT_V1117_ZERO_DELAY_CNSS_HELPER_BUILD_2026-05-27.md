# V1117 Zero-delay CNSS Helper Build Report

Date: `2026-05-27`

## Result

- Decision: `v1117-zero-delay-cnss-helper-build-pass`
- Pass: `true`
- Evidence: `tmp/wifi/v1117-execns-helper-v211-build/manifest.json`
- Collector: `scripts/revalidation/native_wifi_zero_delay_cnss_helper_build_v1117.py`
- Helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`

## Summary

V1117 adds helper support for a zero-delay CNSS-after-`per_mgr` order.

Changes:

- Bumped helper marker to `a90_android_execns_probe v211`.
- Added flag `--pm-observer-start-cnss-zero-delay-after-per-mgr`.
- Added validation requiring PM observer mode and
  `--pm-observer-start-cnss-before-per-proxy`.
- Made the zero-delay and 20 ms immediate flags mutually exclusive.
- Added PM observer output markers:
  - `start_cnss_zero_delay_after_per_mgr=1`;
  - `child.per_mgr.post_start_probe_wait_ms=0`;
  - `child.per_mgr.post_start_probe_deferred_until_after_cnss=1`.

Build output:

```text
artifact=tmp/wifi/v1117-execns-helper-v211-build/a90_android_execns_probe
sha256=6bcf4ad606453f56c4cc25744f6ab90ff6b4cb89942b13c4cc86a7b2f024e44d
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

## Next

V1118 should deploy helper `v211` and run the global-holder zero-delay CNSS live
gate. Wi-Fi HAL and scan/connect remain forbidden.
