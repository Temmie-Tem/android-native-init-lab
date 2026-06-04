# Native Init V2047 WLANMDSP Pre-RRQ Trigger Compare

## Summary

- Cycle: `V2047`
- Type: host-only comparison over existing captures; no new device boot
- Decision: `v2047-android-pre-wlanmdsp-branch-present-native-mcfg-only`
- Label: `android-pre-wlanmdsp-branch-present-native-mcfg-only`
- Evidence:
  - Android: `tmp/wifi/v1982-v1753-minimal-android-good-baseline-rerun/android-postfs-evidence/a90-v1753-wlan-pd-fwreq/`
  - Native: `tmp/wifi/v2046-fallback-persist-rfs-mcfg-handoff/`
- Correction applied: `mcfg.tmp` is not selected as the gate. Android requests `wlanmdsp.mbn` before any `mcfg` path in the compared normal boot window, so V2046's `mcfg` readback branch is demoted to off-branch evidence.

## Result

Native now proves that `tftp_server` is alive and reachable by the modem, but the modem enters only the `mcfg.tmp` branch. Android's normal boot enters a different pre-WLAN image branch:

`server_check.txt` WRQ -> `ota_firewall/ruleset` RRQ failures -> `cnss-daemon` `wlfw_start`/pm-service vote/`wlfw_service_request` -> first `wlanmdsp.mbn` RRQ -> `wlan_pd` UP.

Native V2046 has the AP-side `cnss-daemon`/pm-service/WLFW worker path and reaches `wlan_pd` UP, but the logdw TFTP records contain no `server_check.txt`, no `ota_firewall/ruleset`, and no `wlanmdsp.mbn` transfer. Therefore the next discriminator is the modem-side trigger for the Android `server_check`/`ota_firewall`/`wlanmdsp` branch, not `mcfg.tmp` persistence.

## Android Normal Pre-`wlanmdsp` Edge

Source: `tmp/wifi/v1982-v1753-minimal-android-good-baseline-rerun/android-postfs-evidence/a90-v1753-wlan-pd-fwreq/logcat-filtered.txt`

| logcat line | wall time | event |
| --- | --- | --- |
| 68-69 | `08:16:52.352` | `tftp_server` initializes and starts |
| 70-73 | `08:16:52.724`-`08:16:52.727` | first modem TFTP request is `readwrite/server_check.txt`; request opcode field shows `[2]`, then OACK/open |
| 74-89 | `08:16:52.733`-`08:16:52.736` | modem requests `readwrite/ota_firewall/ruleset` twice; both fail `ENOENT` |
| 90-95 | `08:16:52.983` | `server_check.txt` WRQ completes with `total-bytes = 5` |
| 117 | `08:16:53.763` | `cnss-daemon: wlfw_start: Starting` |
| 118-122 | `08:16:53.766`-`08:16:53.768` | `PerMgrSrv` registers/votes `cnss-daemon` for modem; `PerMgrLib` vote succeeds |
| 125 | `08:16:53.798` | `cnss-daemon: wlfw_service_request: Start the pthread` |
| 126-133 | `08:16:54.375`-`08:16:54.384` | first `wlanmdsp` RRQ: `readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`; Android path probe fails `ENOENT` |
| 134-136 | `08:16:54.385`-`08:16:54.404` | fallback `readonly/vendor/firmware/wlanmdsp.mbn` RRQ is accepted; OACK advertises `4251884` bytes |
| 170 | `08:16:54.644` | fallback `wlanmdsp.mbn` transfer completes with `total-bytes = 4251884` |

Kernel anchor from `dmesg-filtered.txt`:

| dmesg line | uptime | event |
| --- | --- | --- |
| 91 | `8.638178` | `cnss-daemon wlfw_start: Starting` |
| 92 | `8.674380` | `cnss-daemon wlfw_service_request: Start the pthread` |
| 96-97 | `9.567253`-`9.567447` | `msm/modem/wlan_pd` reaches `0x1fffffff`; listener ACKs instance 180 |
| 98 | `9.569576` | `icnss_qmi: QMI Server Connected` |
| 99-100 | `9.722886`-`9.744363` | BDF requests for `regdb.bin` and `bdwlan.bin` |
| 106 | `14.623212` | `icnss: WLAN FW is ready` |
| 110-114 | `14.866239`-`14.872382` | `wlan0`/`swlan0` netdevice events |

Inference from the timestamped edge: Android's first `wlanmdsp.mbn` request is downstream of the early `server_check`/`ota_firewall` modem TFTP branch and the `cnss-daemon` pm-service/WLFW worker edge, and upstream of the published `wlan_pd` UP indication.

## Native V2046 Equivalent Window

Source: `tmp/wifi/v2046-fallback-persist-rfs-mcfg-handoff/manifest.json` and inner `v2045-handoff/test-v1393-helper-result.stdout.txt`

| area | value |
| --- | --- |
| route | `route_ok=True`; start order includes `tftp_server`, `per_mgr`, `subsys_modem_holder`, `cnss_diag`, `cnss_daemon` |
| readwrite bridge | tmpfs `readwrite` exists; `server_check.txt` exists with size `5`; `sda29_write=0` |
| WLAN image availability | fallback `/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn` exists, size `4251884`, open rc `0` |
| cnss worker | `wlfw_start_seen=1`; `wlfw_service_request_seen=1`; corresponding uprobes each hit once |
| WLFW client | `wlfw_client_init_instance_retcheck rc=0x0`; `wlfw_fw_mem_wait_return` hit |
| WLAN-PD | `msm/modem/wlan_pd` reaches `0x1fffffff` at uptime `7.841667`; `icnss_qmi` connects at `7.844078` |
| downstream hold | post-UP hold `82.372138s`; `icnss_qmi` connects, but no textual WLFW-69 dmesg line, no BDF dmesg, no FW-ready, no `wlan0` |
| TFTP summary | `datagrams=27`, `mcfg=3`, `server_check=0`, `ota_firewall=0`, `wlanmdsp=0`, `fallback_wlanmdsp=0`, `total_bytes_4251884=0` |
| TFTP records | only modem request payload names are `readwrite/mcfg.tmp`; native has no Android-style `server_check.txt` or `ota_firewall/ruleset` records |

This makes `mcfg.tmp` evidence useful only as a reachability proof: native can receive modem-originated TFTP requests, but it is not in Android's first WLAN firmware-fetch branch.

## Branch Decision

- `mcfg` gate: refuted for this unit. Android's first `wlanmdsp.mbn` request occurs before the compared `mcfg` path, so `mcfg.tmp` readback must not be optimized as the next gate.
- AP-side pm-service/cnss trigger: not sufficient by itself. Native V2046 has `wlfw_start`, pm-service route, `wlfw_service_request`, WLFW client init success, and `wlan_pd` UP.
- Selected gap: native lacks the modem-originated Android pre-`wlanmdsp` TFTP branch (`server_check.txt` -> `ota_firewall/ruleset` -> `wlanmdsp.mbn`) and instead sees only `mcfg.tmp`.

## Next Unit

Run one light native lower-window discriminator only if new measurement is required:

1. Keep the existing readonly + readwrite tmpfs RFS bridges.
2. Capture exact ordering of:
   - pm-service vote/open success
   - `cnss-daemon` `wlfw_start`
   - `cnss-daemon` `wlfw_service_request`
   - first modem TFTP request names
   - `msm/modem/wlan_pd` state/ACK
   - `icnss_qmi`/WLFW service publication
3. Stop classifying `mcfg.tmp` persistence as a candidate gate.

If native still shows `wlfw_service_request` + `wlan_pd` UP but no `server_check`/`ota_firewall`/`wlanmdsp`, the missing trigger is inside the modem's WLAN image-request branch and should be escalated to modem-side DIAG or an equivalent modem-side event trace. Do not use AP-side RIL/cnss/pm-service strace repeats or boot-time QRTR matrix for this discriminator.

## Safety

- Host-only analysis; no new boot, no new flash, no device mutation.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
- No `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, forced RC1/case, fake ONLINE, PMIC/GPIO/GDSC/regulator writes, or `sda29` write.
