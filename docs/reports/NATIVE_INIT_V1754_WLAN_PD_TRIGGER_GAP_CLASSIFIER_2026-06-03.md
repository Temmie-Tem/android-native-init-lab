# Native Init V1754 WLAN-PD Trigger-gap Classifier

## Summary

- Cycle: `V1754`
- Type: host-only trigger-gap classifier from retained V1753/V1736 evidence
- Decision: `v1754-android-good-permgr-vote-before-wlanmdsp-native-pm-absent-host-pass`
- Label: `peripheral-manager-vote-delta-before-firmware-request`
- Result: PASS
- Reason: Android-good shows cnss-daemon PM manager register/vote before the first wlanmdsp request, while the native V1736 SM route has PM disabled/absent and still never requests wlanmdsp
- Evidence: `tmp/wifi/v1754-wlan-pd-trigger-gap-classifier`

## Android-good Timeline

| Event | Time | Delta to first `wlanmdsp` request |
| --- | ---: | ---: |
| `rmt_storage_ready` | `15449.309` | `-2.071s` |
| `tftp_server_started` | `15449.322` | `-2.058s` |
| `cnss_diag_started` | `15450.426` | `-0.954s` |
| `cnss_daemon_started` | `15450.592` | `-0.788s` |
| `cnss_wlfw_start` | `15450.687` | `-0.693s` |
| `per_mgr_register` | `15450.688` | `-0.692s` |
| `per_mgr_vote` | `15450.688` | `-0.692s` |
| `cnss_wlfw_service_request` | `15450.756` | `-0.624s` |
| `wlanmdsp_request` | `15451.380` | `+0.000s` |
| `bdf_regdb` | `15451.805` | `+0.425s` |
| `bdf_bdwlan` | `15451.819` | `+0.439s` |

## Native V1736 SM-route State

- Manifest: `tmp/wifi/v1736-wlan-pd-timestamped-observer-handoff/manifest.json`
- Decision/pass: `v1736-wlfw-start-reached-downstream-block-rollback-pass` / `True`
- `wlfw_start` / `wlfw_service_request` / worker hits: `1` / `1` / `1`
- `requested_wlanmdsp`: `0`
- firmware label: `firmware-not-requested`
- `wifi_companion_start.peripheral_manager.enabled`: `0`
- native PM register/vote text present: `0`

## Android-good Key Lines

```text
06-03 04:17:29.309  1680  1680 I vendor.rmt_storage: Shared memory initialised successfully.
06-03 04:17:29.322  1684  1684 I tftp_server: Starting...
06-03 04:17:30.426  2053  2053 I CLD80211: cnss_diag: initialized exit socket pair
06-03 04:17:30.592  2124  2124 I CLD80211: cnss-daemon: initialized exit socket pair
06-03 04:17:30.687  2124  2124 I cnss-daemon: wlfw_start: Starting
06-03 04:17:30.688  1630  1662 D PerMgrSrv: modem state: is on-line, add client cnss-daemon
06-03 04:17:30.688  2124  2124 D PerMgrLib: cnss-daemon voting for modem
06-03 04:17:30.756  2124  2227 I cnss-daemon: wlfw_service_request: Start the pthread: 0x0K
06-03 04:17:31.380  1684  2518 I tftp_server: pid=1684 tid=2518 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmware_mnt/image/wlanmdsp.mbn] : [/vendor/rfs/msm/mpss/readonly/vendor
06-03 04:17:31.805  2124  2227 I cnss-daemon: wlfw_send_bdf_download_req: BDF file : regdb.bin
06-03 04:17:31.819  2124  2227 I cnss-daemon: wlfw_send_bdf_download_req: BDF file : bdwlan.bin
```

## Native Key Lines

```text
[    2.837467] [3:    rmt_storage:  559] rmt_storage:INFO:main: Done with init now waiting for messages!
[    4.768233] [7:a90_android_exe:  578] subsys-pil-tz 4080000.qcom,mss: modem: Brought out of reset
[    4.822556] I[0:    kworker/0:0:    4] qrtr: Modem QMI Readiness RX cmd:0x2 node[0x0]
```

## Interpretation

- V1753 already fixed the redirect label as `firmware-not-requested`.
- Android-good reaches `wlfw_start`, then records `cnss-daemon` PM manager registration/vote, then starts the WLFW request worker, then the internal modem asks `tftp_server` for `wlanmdsp.mbn`.
- Native V1736 reaches the CNSS WLFW worker and has `tftp_server` running, but the PM manager path is disabled/absent in that route and no `wlanmdsp.mbn` request appears.
- This is not authorization to add PM actors blindly. Earlier PM actor attempts still remain a known dead-end unless a new narrow gate repairs the specific native PM registration/vote contract without returning to eSoC/RC1 or Wi-Fi HAL work.

## Safety Scope

This classifier is host-only and reads retained evidence. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or new actor start.
