# Native Init V1881 Delayed Lower Read-only Sampler Preflight

## Summary

- Cycle: `V1881`
- Type: host-only V1880 delayed lower-response sampler artifact preflight
- Decision: `v1881-delayed-lower-readonly-sampler-preflight-pass`
- Label: `delayed-lower-readonly-sampler-live-ready`
- Result: PASS
- Reason: V1880 boot/helper artifacts are present, hash-matched, v358-marked, and configured for the Android-good delayed read-only lower-response window with scan/connect and RC1 write paths blocked.
- Evidence: `tmp/wifi/v1881-delayed-lower-readonly-sampler-preflight`

## Checks

| check | value |
|---|---:|
| `v1879_report_selected_delayed_sampler` | `True` |
| `v1880_manifest_present` | `True` |
| `v1880_decision_pass` | `True` |
| `v1880_report_present` | `True` |
| `helper_exists` | `True` |
| `boot_image_exists` | `True` |
| `helper_sha_matches_manifest` | `True` |
| `boot_sha_matches_manifest` | `True` |
| `helper_delayed_contract_strings_present` | `True` |
| `boot_init_build_present` | `True` |
| `boot_property_root_present` | `True` |
| `boot_helper_result_present` | `True` |
| `private_sdx50m_route_enabled` | `True` |
| `lower_observer_mode_enabled` | `True` |
| `firmware_mounts_enabled` | `True` |
| `debugfs_mount_enabled_for_readonly_snapshots` | `True` |
| `supervisor_long_enough_for_delayed_window` | `True` |
| `scan_connect_credentials_blocked` | `True` |
| `rc1_writes_blocked` | `True` |

## Delayed Window

- Source: `android-good-delayed-private-sdx50m-readonly-window`
- Offsets seconds: `0,1,2,5,10,20,30,60,90,120,150,180,210,240,250,260,300`
- PID1 watch/supervisor seconds: `330` / `360`

## Artifacts

- V1879 report: `docs/reports/NATIVE_INIT_V1879_ANDROID_DELAYED_LOWER_TIMING_RECONCILE_2026-06-03.md`
- V1880 manifest: `tmp/wifi/v1880-delayed-lower-readonly-sampler-test-boot/manifest.json`
- V1880 report: `docs/reports/NATIVE_INIT_V1880_DELAYED_LOWER_READONLY_SAMPLER_SOURCE_BUILD_2026-06-03.md`
- Helper binary: `tmp/wifi/v1880-delayed-lower-readonly-sampler-test-boot/a90_android_execns_probe_v358`
- Helper SHA256: `1d6cb4bb16e1b35b86eb0a76381f1651a72d87d760756f33562efe2aeef5d7cc`
- Boot image: `tmp/wifi/v1880-delayed-lower-readonly-sampler-test-boot/boot_linux_v1880_delayed_lower_readonly_sampler.img`
- Boot SHA256: `70f862e6c48a5aa69f919154ef4b6cb27c26863948271f5cceaf3e90f9f61a20`

## Next

- Cycle: `V1882`
- Type: `one-run rollbackable live delayed lower-response read-only handoff`
- Boot image: `tmp/wifi/v1880-delayed-lower-readonly-sampler-test-boot/boot_linux_v1880_delayed_lower_readonly_sampler.img`
- Required stop: do not attempt Wi-Fi connect or ping unless WLFW service 69 and wlan0 are both present

## Safety Scope

V1881 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
