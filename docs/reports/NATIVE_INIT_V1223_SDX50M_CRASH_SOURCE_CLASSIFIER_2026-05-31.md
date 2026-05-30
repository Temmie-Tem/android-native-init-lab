# V1223 SDX50M Crash Source Classifier

- date: 2026-05-31
- cycle: V1223
- objective: classify why native V1222 reaches `subsys_esoc0` but fails before WLFW/BDF/`wlan0`, using existing Android and native evidence only.
- safety scope: host-only classifier; no device contact, live daemon start, Wi-Fi HAL, scan/connect/link-up, credentials, DHCP/routes, external ping, boot image write, or partition write.

## Implementation

- runner: `scripts/revalidation/native_wifi_sdx50m_crash_source_classifier_v1223.py`
- evidence output: `tmp/wifi/v1223-sdx50m-crash-source-classifier/manifest.json`
- summary output: `tmp/wifi/v1223-sdx50m-crash-source-classifier/summary.md`
- inputs:
  - V1222 live boundary: `tmp/wifi/v1222-post-esoc-power-boundary-live/manifest.json`
  - V904 Android/native runtime parity: `tmp/wifi/v904-mdm-helper-runtime-input-parity/manifest.json`
  - V896 Android image-link contract: `tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json`

## Result

- decision: `v1223-sdx50m-crash-source-contract-gap-classified`
- pass: `true`
- missing contract: Android-equivalent init-managed `mdm_helper`/`ks` MHI image-link lifetime/order around `pm-service` eSoC open.

## Evidence Join

| check | value |
| --- | --- |
| V1222 reaches `/dev/subsys_esoc0` | `true` |
| V1222 reaches `mdm_subsys_powerup` | `true` |
| V1222 `mdm3` state | `OFFLINING` |
| V1222 modem-down/crash marker max | `4` |
| V1222 WLFW/BDF/`wlan0` marker max | `0` |
| Android `mdm_helper` owns `/dev/esoc-0` | `true` |
| Android `ks` reaches `/dev/mhi_0305_01.01.00_pipe_10` | `true` |
| Android `pm-service` owns `/dev/subsys_esoc0` | `true` |
| Native direct `mdm_helper` result | `mdm-helper-no-esoc-fd` |

## Interpretation

V1223 closes the CNSS/PM-selection branch as the primary blocker for this stage. V1222 already proved private CNSS `SDX50M` registration and `pm-service` entry into `/dev/subsys_esoc0`. The remaining failure happens after eSoC power-up starts and before WLFW service 69, BDF transfer, FW-ready, or `wlan0`.

The Android positive path has an additional runtime contract: init-managed `vendor_mdm_helper` in `u:r:vendor_mdm_helper:s0` owns `/dev/esoc-0`, `ks` uses `/dev/mhi_0305_01.01.00_pipe_10`, and `pm-service` owns both `/dev/subsys_esoc0` and `/dev/subsys_modem`. Direct native `mdm_helper` evidence showed no `/dev/esoc-0`, no `ks`, and no MHI pipe.

The next gate should therefore prove Android-equivalent `mdm_helper`/`ks` MHI image-link lifetime/order around the `pm-service` eSoC open, not retry CNSS selection or move to Wi-Fi HAL.

## Safety Audit

- `device_contact=false`
- `live_action_executed=false`
- `wifi_hal_start_executed=false`
- `scan_connect_executed=false`
- `credential_use_executed=false`
- `dhcp_route_executed=false`
- `external_ping_executed=false`
- `wifi_bringup_executed=false`
- `boot_image_write_executed=false`
- `partition_write_executed=false`

## Next

V1224 should run a bounded live parity gate that proves `mdm_helper` owns `/dev/esoc-0` and `ks`/MHI appears before or while `pm-service` opens `/dev/subsys_esoc0`. Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until WLFW/BDF/`wlan0` readiness is proven.
