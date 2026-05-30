# V1225 mdm_helper WAIT_FOR_REQ Gap Classifier

- date: 2026-05-31
- runner: `scripts/revalidation/native_wifi_mdm_helper_wait_req_gap_classifier_v1225.py`
- evidence: `tmp/wifi/v1225-mdm-helper-wait-req-gap-classifier/manifest.json`
- summary: `tmp/wifi/v1225-mdm-helper-wait-req-gap-classifier/summary.md`
- result: `v1225-mdm-helper-post-wait-sleep-gap-classified`
- pass: `true`

## Summary

V1225 is host-only. It consumes V1224 live evidence plus V911, V1144, V1158,
V1160, and V1193/V1194 references. It performs no device command, live eSoC
retry, Wi-Fi HAL start, scan/connect, DHCP/route, external ping, flash, boot
image write, or partition write.

V1224 already reaches the Android-like upper path: `mdm_helper` owns
`/dev/esoc-0`, and `pm-service` attempts `/dev/subsys_esoc0` from
`mdm_subsys_powerup`. The failure is now lower: `ks`,
`/dev/mhi_0305_01.01.00_pipe_10`, WLFW service 69, BDF, FW-ready, and `wlan0`
remain absent, while `mdm3` stays `OFFLINING` and modem-down/crash markers rise.

The key refinement is that V1224 did not merely lack `mdm_helper` visibility:
its lower thread probe observed `mdm_helper` threads in `SyS_nanosleep`, not in
`ESOC_WAIT_FOR_REQ`, and did not capture the return value or subsequent
open/exec/ioctl errors. Historical V911/V1144 evidence still identifies
`ESOC_WAIT_FOR_REQ` as the earlier request-engine boundary, so the active gap is
now the post-wait sleep/no-MHI branch.

## Classification

| evidence | ok | detail |
| --- | --- | --- |
| V1224 decision | `true` | `v1224-mdm-helper-esoc-present-ks-mhi-absent-crash` |
| `pm-service` `/dev/subsys_esoc0` | `true` | `mdm_subsys_powerup` |
| `mdm_helper` `/dev/esoc-0` | `true` | count `1` |
| `ks`/MHI absent | `true` | `ks=0`, MHI pipe count `0` |
| WLFW/`wlan0` absent | `true` | `max_dmesg_wlfw_count=0`, `wlan0_seen=false` |
| `mdm3` crash/offlining | `true` | states `["OFFLINING"]`, modem-down marker count `4` |
| worker sleep/no wait value | `true` | thread probe present, syscall/wchan present, all wchans `SyS_nanosleep`, no `ESOC_WAIT_FOR_REQ` value |
| historical wait boundary | `true` | V911/V1144 |
| Android trigger reference | `true` | V1158/V1160 |
| safety clean | `true` | no HAL/scan/credential/DHCP/ping/flash |

## Interpretation

- CNSS peripheral naming and PM eSoC routing are no longer the primary blocker.
- Direct `mdm_helper` launch is no longer the blocker either; V1224 proves
  `/dev/esoc-0` ownership in the native path.
- The remaining unknown is what `mdm_helper` receives from `ESOC_WAIT_FOR_REQ`
  and why the following Android `ks`/MHI path does not start.
- The next gate should trace `mdm_helper` from process start through the
  `pm-service` `/dev/subsys_esoc0` trigger, rather than repeating a blind
  CNSS/PM selection retry.

## Next

V1226 should add a bounded lower-trace v2 live gate in the V1224 PM/CNSS path:

- enable `mdm_helper` syscall/return tracing from process start;
- capture `ESOC_WAIT_FOR_REQ` return value and every subsequent
  open/exec/ioctl error;
- poll `/dev/mhi_0305_01.01.00_pipe_10`, `/sys/bus/mhi/devices`, PCIe link
  state, and `/vendor/bin/ks`;
- compare before and after `pm-service` opens `/dev/subsys_esoc0`;
- keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash,
  boot image write, and partition writes blocked.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_wait_req_gap_classifier_v1225.py
python3 scripts/revalidation/native_wifi_mdm_helper_wait_req_gap_classifier_v1225.py
```

## Safety

- `device_commands_executed=false`
- `live_esoc_ioctl_executed=false`
- `wifi_hal_start_executed=false`
- `scan_connect_executed=false`
- `credential_use_executed=false`
- `dhcp_route_executed=false`
- `external_ping_executed=false`
- `wifi_bringup_executed=false`
- `boot_image_write_executed=false`
- `partition_write_executed=false`
- `flash_executed=false`
