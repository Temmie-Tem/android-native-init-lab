# Native Init V2104 MAC Bounded Producer Frontier

## Summary

- Cycle: `V2104`
- Type: host-only refinement over committed rollback-verified captures; no device boot or mutation.
- Decision: `v2104-mac-bounded-native-skips-android-order-tftp-bootstrap-host-pass`
- Label: `mac-bounded-native-skips-android-order-tftp-bootstrap`
- Pass: `True`
- Reason: MAC is bounded as downstream/cosmetic; native reaches AP-side prerequisites but skips Android-order ota_firewall/wlanmdsp transfer evidence
- Evidence: `tmp/wifi/v2104-mac-bounded-producer-frontier`

## MAC Bound

| field | value | detail |
| --- | --- | --- |
| identity_source | True | stage3/linux_init/helpers/a90_android_execns_probe.c uid/gid wifi groups wifi/inet/net_raw/net_admin |
| real_sysfs_mac_addr | True | /sys/wifi/mac_addr mode=0220 fs=0x0000000062656572 uid=0 gid=0 |
| mac_info | 1 | bytes=17 readable=1 writable=0 uid=1010 gid=1010 |
| macloader_trace | 1 | target=/vendor/bin/hw/macloader records=14 |
| mac_write | False | open=False shape=False raw_payload=0 |
| kernel_assign | 0 | proof line `icnss: Assigning MAC from Macloader` |

## Android Producer Order

| event | delta_from_tftp_start_ms | line |
| --- | --- | --- |
| server_check_wrq | 374 | 06-04 08:16:52.726  1660  1808 I tftp_server: pid=1660 tid=1808 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/server_check.… |
| ota_firewall_rrq | 381 | 06-04 08:16:52.733  1660  1811 I tftp_server: pid=1660 tid=1811 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/ota_firewall/… |
| wlfw_start | 1411 | 06-04 08:16:53.763  2120  2120 I cnss-daemon: wlfw_start: Starting |
| per_mgr_add_client | 1414 | 06-04 08:16:53.766  1588  1650 D PerMgrSrv: modem state: is on-line, add client cnss-daemon |
| per_mgr_vote | 1416 | 06-04 08:16:53.768  2120  2120 D PerMgrLib: cnss-daemon voting for modem |
| wlfw_service_request | 1446 | 06-04 08:16:53.798  2120  2208 I cnss-daemon: wlfw_service_request: Start the pthread: 0x0K |
| first_wlanmdsp_rrq | 2028 | 06-04 08:16:54.380  1660  2456 I tftp_server: pid=1660 tid=2456 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmwar… |

## Native Frontier

| area | value | detail |
| --- | --- | --- |
| tftp_ready | True | safe=True |
| per_mgr_vote | True | wlfw_service_request_ts=8.097677 |
| wlan_pd_up | 1 | ts=9.318176 icnss_qmi=1 msg21=True |
| server_check_file | True | payload=hello after_wlan_pd_ms=6346 |
| ota_firewall | False | file=False |
| wlanmdsp_transfer | False | first_lines=0 fw_ready=0 wlan0=0 |
| mcfg | True | late/noise; Android requests wlanmdsp before mcfg |

## Corrected Request Semantics

- V2103 legacy `wlan_pd_firmware_serve_gate.requested_wlanmdsp=1` is not transfer proof: `tftp_logdw` has no `wlanmdsp`, `first_wlanmdsp_lines=[]`, and `classification.wlanmdsp_seen=False`.
- Treat visible transfer/request evidence as the `tftp_logdw` records, dmesg lines, and first-line lists; those remain zero for native `ota_firewall/ruleset` and `wlanmdsp.mbn`.
- Native only shows a `server_check.txt=hello` file transition after `wlan_pd` UP, plus later `mcfg`; it does not enter Android's pre-UP `server_check -> ota_firewall -> wlanmdsp` bootstrap order.

## Next Unit

- Do not rerun MAC/macloader unless a new unit directly proves a kernel store and immediately falsifies producer impact.
- Do not rerun AP-side RIL/cnss/pm-service strace, QRTR matrix, mcfg readback, server-check reachability, or SDX50M/eSoC/PCIe/GDSC paths.
- Next live measurement should target the modem-internal branch that chooses Android's pre-UP TFTP bootstrap path after AP-side `wlfw_service_request` is already reproduced.

## Inputs

| input | path |
| --- | --- |
| android_order | tmp/wifi/v2053-pre-wlanmdsp-trigger-event-diff/summary.json |
| mac_runtime | tmp/wifi/v2091-macloader-property-service-handoff/manifest.json |
| mac_aggregate | tmp/wifi/v2094-mac-closed-post-server-check-timing/manifest.json |
| native_frontier | tmp/wifi/v2103-tftp-process-namespace-audit-handoff/manifest.json |

## Safety

- Host-only parse/report generation; no flash, reboot, adb mutation, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, tftp ptrace, eSoC/PCIe/GDSC/PMIC/GPIO path, firmware/partition write, or `sda29` write.
