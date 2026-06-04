# Native Init V2105 MAC Kernel Store Contract

## Summary

- Cycle: `V2105`
- Type: host-only refinement over existing rollback-verified captures; no device boot or mutation.
- Decision: `v2105-mac-real-node-no-write-producer-remains-tftp-bootstrap-host-pass`
- Label: `mac-real-node-no-write-producer-remains-tftp-bootstrap`
- Pass: `True`
- Reason: real ICNSS MAC node and wifi identity are proven, but macloader never writes it; MAC stays bounded and the remaining gap is the missing server_check/ota_firewall/wlanmdsp producer branch
- Evidence: `tmp/wifi/v2105-mac-kernel-store-contract`

## MAC Contract

| check | value | detail |
| --- | --- | --- |
| real_sysfs_node | True | /sys/wifi/mac_addr mode=0220 fs=0x0000000062656572 post_fs=0x0000000062656572 |
| not_tmpfs_standin | True | helper binds `/sys/wifi` RW into the namespace; it does not synthesize a tmpfs mac_addr |
| macloader_wifi_identity | True | source UID/GID/group includes `A90_AID_WIFI` |
| mac_info_source | 1 | bytes=17 readable=1 writable=0 uid=1010 gid=1010 |
| trace_target | 1 | target=/vendor/bin/hw/macloader records=14 raw_mac_payload=0 |
| macloader_read | False | open=False |
| macloader_write | False | open=False colon_hex_shape=False |
| kernel_assign | False | count=0 proof=`icnss: Assigning MAC from Macloader` |

## Producer Frontier

| area | value | detail |
| --- | --- | --- |
| tftp_ready | True |  |
| per_mgr_vote | True | wlfw_service_request_ts=8.097677 |
| wlan_pd_up | 1 | ts=9.318176 icnss_qmi=1 msg21=True |
| server_check_file | True | payload=hello after_wlan_pd_ms=6346 |
| server_check_logdw | 0 | early Android branch remains absent |
| ota_firewall_logdw | 0 |  |
| wlanmdsp_logdw | 0 | fw_ready=0 wlan0=0 |
| mcfg_logdw | 9 | late/noise; Android requests wlanmdsp before mcfg |

## Android Order Anchor

| event | delta_from_tftp_start_ms | line |
| --- | --- | --- |
| server_check_wrq | 374 | 06-04 08:16:52.726  1660  1808 I tftp_server: pid=1660 tid=1808 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/server_check.… |
| ota_firewall_rrq | 381 | 06-04 08:16:52.733  1660  1811 I tftp_server: pid=1660 tid=1811 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/ota_firewall/… |
| wlfw_start | 1411 | 06-04 08:16:53.763  2120  2120 I cnss-daemon: wlfw_start: Starting |
| per_mgr_add_client | 1414 | 06-04 08:16:53.766  1588  1650 D PerMgrSrv: modem state: is on-line, add client cnss-daemon |
| per_mgr_vote | 1416 | 06-04 08:16:53.768  2120  2120 D PerMgrLib: cnss-daemon voting for modem |
| wlfw_service_request | 1446 | 06-04 08:16:53.798  2120  2208 I cnss-daemon: wlfw_service_request: Start the pthread: 0x0K |
| first_wlanmdsp_rrq | 2028 | 06-04 08:16:54.380  1660  2456 I tftp_server: pid=1660 tid=2456 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmwar… |

## Interpretation

- The namespace `/sys/wifi/mac_addr` is the real sysfs ICNSS node: `statfs` reports sysfs magic `0x62656572`, the file is mode `0220`, and the helper source bind-mounts `/sys/wifi` rather than materializing a tmpfs stand-in.
- The macloader identity contract is present in source as UID/GID/group `wifi`; V2091 traced `/vendor/bin/hw/macloader` but saw no `.mac.info` read and no `/sys/wifi/mac_addr` open/write.
- Because there is no write record, the `%x:%x:...` payload shape is not proven or disproven at runtime; the falsifier resolves earlier: no write reached the kernel store, and the kernel emitted zero `icnss: Assigning MAC from Macloader` lines.
- Even a successful assign would feed `cnss_utils` for later qcacld/HDD netdev creation after FW-ready; it does not explain the current producer gap where native skips Android's `server_check -> ota_firewall -> wlanmdsp` TFTP branch.

## Next Unit

- Do not spend another cycle on MAC/macloader unless a new run directly shows a real kernel assign and immediate producer impact.
- Keep the primary measurement on why the internal modem does not enter the Android-order pre-UP TFTP bootstrap branch after AP-side `wlfw_service_request` is already reproduced.
- Do not rerun AP-side RIL/cnss/pm-service strace, QRTR matrix, mcfg readback, server-check reachability, passive DIAG, or SDX50M/eSoC/PCIe/GDSC paths.

## Inputs

| input | path |
| --- | --- |
| mac_runtime | tmp/wifi/v2091-macloader-property-service-handoff/manifest.json |
| native_frontier | tmp/wifi/v2103-tftp-process-namespace-audit-handoff/manifest.json |
| bounded_frontier | tmp/wifi/v2104-mac-bounded-producer-frontier/manifest.json |
| helper_source | stage3/linux_init/helpers/a90_android_execns_probe.c |

## Safety

- Host-only parse/report generation; no flash, reboot, adb mutation, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, tftp ptrace, eSoC/PCIe/GDSC/PMIC/GPIO path, firmware/partition write, EFS write, or `sda29` write.
