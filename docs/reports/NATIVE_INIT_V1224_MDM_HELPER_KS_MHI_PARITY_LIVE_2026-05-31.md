# V1224 mdm_helper / ks / MHI Parity Live Gate

- date: 2026-05-31
- cycle: V1224
- objective: prove the lower Android-equivalent image-link contract around the native `pm-service` SDX50M eSoC open.
- safety scope: bounded PM/CNSS/`mdm_helper` observer only; no Wi-Fi HAL, scan/connect/link-up, credentials, DHCP/routes, external ping, boot image write, flash, or partition write.

## Implementation

- runner: `scripts/revalidation/native_wifi_mdm_helper_ks_mhi_parity_live_v1224.py`
- base path: V1222 private CNSS `SDX50M` live path with helper `a90_android_execns_probe v253`
- evidence output: `tmp/wifi/v1224-mdm-helper-ks-mhi-parity-live/manifest.json`
- summary output: `tmp/wifi/v1224-mdm-helper-ks-mhi-parity-live/summary.md`
- postflight:
  - `tmp/wifi/v1224-mdm-helper-ks-mhi-parity-live/host/postflight-selftest.json`
  - `tmp/wifi/v1224-mdm-helper-ks-mhi-parity-live/host/postflight-netservice.json`
  - `tmp/wifi/v1224-mdm-helper-ks-mhi-parity-live/host/postflight-ps.json`
  - `tmp/wifi/v1224-mdm-helper-ks-mhi-parity-live/host/postflight-summary.json`

## Result

- decision: `v1224-mdm-helper-esoc-present-ks-mhi-absent-crash`
- pass: `true`
- reason: `mdm_helper` owns `/dev/esoc-0` and `pm-service` attempts `/dev/subsys_esoc0`, but `ks`/MHI never appears before modem-down/crash markers.

## Evidence

| field | value |
| --- | --- |
| `pm_service_subsys_esoc0_attempt` | `true` |
| `pm_service_subsys_esoc0_fd_count` | `0` |
| `pm_service_subsys_modem_fd_count` | `1` |
| `mdm_helper_esoc_present` | `true` |
| `mdm_helper_esoc0_count_window` | `1` |
| `ks_or_mhi_present` | `false` |
| `ks_count_window` | `0` |
| `mdm_helper_mhi_pipe_count_window` | `0` |
| lower trace samples | `3` |
| `mdm3_state_transitions` | `["OFFLINING"]` |
| modem-down/crash marker max | `4` |
| WLFW/BDF/`wlan0` marker max | `0` |
| `wlan0_seen` | `false` |

Lower trace samples all showed `mdm_helper` alive in `S` state with `/dev/esoc-0` fd count `1`, but `/dev/mhi_0305_01.01.00_pipe_10` fd count `0`, `ks` count `0`, and no MHI cmdline match.

## Interpretation

V1224 narrows the blocker again. The missing piece is no longer simply "`mdm_helper` did not start" or "`mdm_helper` lacks `/dev/esoc-0`". In the current native path, `mdm_helper` does own `/dev/esoc-0` while `pm-service` attempts the SDX50M `/dev/subsys_esoc0` path. The failure is below that point: `ks` is not spawned, no MHI pipe appears, WLFW service 69/BDF/FW-ready/`wlan0` remain absent, and modem-down/crash markers appear.

This points V1225 at the exact sub-boundary between `mdm_helper` holding `/dev/esoc-0` and Android's successful `ks`/MHI image transfer path.

## Postflight

- selftest: `pass=11 warn=1 fail=0`
- netservice: `ncm0=absent tcpctl=stopped`
- actor cleanup: no `pm-service`, `pm_proxy`, `mdm_helper`, `cnss-daemon`, `/vendor/bin/ks`, `servicemanager`, `hwservicemanager`, or `vndservicemanager` remained in `ps`.

## Safety Audit

- `tracefs_write_executed=true`
- `pm_actor_executed=true`
- `cnss_daemon_start_executed=true`
- `wifi_hal_start_executed=false`
- `scan_connect_executed=false`
- `credential_use_executed=false`
- `dhcp_route_executed=false`
- `external_ping_executed=false`
- `wifi_bringup_executed=false`
- `partition_write_executed=false`
- `flash_executed=false`
- `reboot_executed=false`

## Next

V1225 should classify why native `mdm_helper` stays before the Android `ks`/MHI path under SDX50M power-up. Focus on `mdm_helper` eSoC ioctl/wchan state, MHI device creation, and Android timing around `ESOC_WAIT_FOR_REQ`, PCIe/MHI readiness, and `ks` spawn.
