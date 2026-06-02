# Native Init V1703 CNSS WLFW Downstream Static Classifier

## Summary

- Cycle: `V1703`
- Type: host-only cnss-daemon WLFW downstream static classifier
- Decision: `v1703-cnss-wlfw-downstream-static-map-pass`
- Result: `PASS`
- Reason: V1702 proved cnss-daemon reaches wlfw_start; debug symbols and disassembly map the downstream WLFW worker/QMI wait path
- Evidence: `tmp/wifi/v1703-cnss-wlfw-downstream-static`

## V1702 Basis

- V1702 decision: `v1702-cnss-wlfw-entry-hit-downstream-wait-rollback-pass`
- V1702 non-log label: `cnss-wlfw-entry-hit-downstream-wait`
- Rollback OK: `True`
- `wlfw_start` uprobe hit count: `1`
- First hit: `cnss-daemon-561   [000] ....     3.572363: wlfw_start: (0x55798bac00)`
- Legacy firmware-serve label: `firmware-not-requested`
- `cnss-daemon` / `tftp_server` running: `1` / `1`
- MHI pipe fd / `ks` process count: `0` / `0`

## Static Inputs

- Binary: `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`
- SHA256: `bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc`
- SHA256 expected: `True`
- `.gnu_debugdata` available: `True`

## WLFW Control Flow

- `wlfw_start@0xec00` is the confirmed entry hit by V1702.
- `pthread_initialize_dms@0xeb14` creates `dms_service_request@0xe808` at `pthread_create@0xebb4`.
- `wlfw_start@0xec00` creates `wlfw_service_request@0xd9fc` at `pthread_create@0xecf0`.
- `wlfw_service_request@0xd9fc` is the primary downstream worker: WLFW QMI client init, service instance resolution, indication registration, condition waits, then capability/BDF flow.
- `dms_service_request@0xe808` is secondary: DMS/system-info/MAC path that waits until WLFW state permits sending MAC data.

## Key Symbols

| Symbol | Expected | Actual | Match |
| --- | --- | --- | --- |
| `wlfw_start` | `0xec00` size `464` `GLOBAL` | `0xec00` size `464` `GLOBAL` | `True` |
| `wlfw_stop` | `0xedd0` size `1176` `GLOBAL` | `0xedd0` size `1176` `GLOBAL` | `True` |
| `pthread_initialize_dms` | `0xeb14` size `236` `GLOBAL` | `0xeb14` size `236` `GLOBAL` | `True` |
| `dms_service_request` | `0xe808` size `780` `GLOBAL` | `0xe808` size `780` `GLOBAL` | `True` |
| `dms_get_wlan_address` | `0xe544` size `324` `GLOBAL` | `0xe544` size `324` `GLOBAL` | `True` |
| `wlfw_service_request` | `0xd9fc` size `1796` `GLOBAL` | `0xd9fc` size `1796` `GLOBAL` | `True` |
| `wlfw_send_ind_register_req` | `0xf268` size `364` `LOCAL` | `0xf268` size `364` `LOCAL` | `True` |
| `wlfw_send_cap_req` | `0xf3d4` size `460` `LOCAL` | `0xf3d4` size `460` `LOCAL` | `True` |
| `wlfw_send_bdf_download_req` | `0xf76c` size `1576` `LOCAL` | `0xf76c` size `1576` `LOCAL` | `True` |
| `wlfw_send_cal_report_req` | `0xf5a0` size `460` `LOCAL` | `0xf5a0` size `460` `LOCAL` | `True` |
| `wlfw_qmi_ind_cb` | `0xe100` size `952` `LOCAL` | `0xe100` size `952` `LOCAL` | `True` |
| `wlfw_qmi_err_cb` | `0xe4b8` size `140` `LOCAL` | `0xe4b8` size `140` `LOCAL` | `True` |
| `wlfw_handle_ind_data` | `0xce24` size `2724` `GLOBAL` | `0xce24` size `2724` `GLOBAL` | `True` |
| `pm_init` | `0xc39c` size `760` `GLOBAL` | `0xc39c` size `760` `GLOBAL` | `True` |

## QMI Sync Calls

| Function | Call Site | Message | Req | Resp | Timeout | Meaning |
| --- | --- | --- | --- | --- | --- | --- |
| `dms_get_wlan_address` | `0xe59c` | `0x5c` | `0x4` | `0x18` | `10000 ms` | DMS WLAN MAC/address query before DMS thread sends MAC to FW |
| `dms_service_request` | `0xea90` | `0x33` | `0x7` | `0x8` | `10000 ms` | DMS path sends MAC/address data once WLFW state allows it |
| `wlfw_send_ind_register_req` | `0xf32c` | `0x20` | `0x30` | `0x18` | `10000 ms` | WLFW indication registration; first concrete QMI sync after WLFW service client exists |
| `wlfw_send_cap_req` | `0xf460` | `0x24` | `0x1` | `0x108` | `10000 ms` | WLFW capability query; follows indication registration and gates BDF/CAL flow |
| `wlfw_send_bdf_download_req` | `0xfc44` | `0x25` | `0x1824` | `0x18` | `10000 ms` | BDF/REGDB transfer chunks; downstream and not expected before WLFW service is published |

## Interpretation

- The corrected premise stands: `cnss-daemon` reaches `wlfw_start`; previous missing dmesg/log evidence was a logging artifact.
- The next unknown is not whether `wlfw_start` is entered, but whether `wlfw_service_request` starts and reaches WLFW QMI sends.
- If `wlfw_service_request@0xd9fc` is hit but `wlfw_send_ind_register_req@0xf32c` is not, the block is before WLFW QMI client/service readiness.
- If `0xf32c` is hit and later WLFW 69 remains absent, the block is the modem/WLAN-PD side not publishing or responding to WLFW QMI.
- `wlfw_send_bdf_download_req@0xfc44` is downstream; do not chase BDF/REGDB until WLFW service and capability flow exist.

## V1704 Proposed Gate

- Type: one-run rollbackable read-only tracefs uprobe classifier.
- Route: reuse V1702 internal-modem firmware-serve route only.
- Primary trace targets: `cnss-daemon+0xd9fc`, `cnss-daemon+0xf32c`, `cnss-daemon+0xf460`; optional secondary target `cnss-daemon+0xe808`.
- Fixed labels: `wlfw-worker-thread-started-waiting-for-qmi-service`, `wlfw-worker-thread-started-qmi-ind-register-sent`, `wlfw-worker-thread-started-qmi-cap-sent`, `wlfw-worker-thread-missing-after-wlfw-start`, `cnss-target-unavailable`.
- Forbidden: PM/service-window actors, `boot_wlan` as a WLFW trigger, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.
