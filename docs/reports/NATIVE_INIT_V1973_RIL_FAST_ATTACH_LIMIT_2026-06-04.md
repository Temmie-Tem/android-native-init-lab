# V1973 RIL Fast-Attach Limit

- generated: `2026-06-04`
- decision: `v1973-strace-fastattach-still-post-wlanpd-up-rollback-pass`
- label: `producer-window-still-missed-by-ptrace-attach`
- pass: `False`
- evidence:
  - `tmp/wifi/v1972-ril-qmi-producer-preup-handoff`
  - `tmp/wifi/v1973-ril-qmi-producer-fastattach-handoff`
  - `tmp/wifi/v1973-ril-qmi-producer-fastattach-decode`

## Question

Measure the producer side on the normal Android internal-modem path: attach `strace -s9999 -xx -e trace=sendmsg,recvmsg,sendto,recvfrom` to `rild`, `cnss-daemon`, and `pm-service`; capture unfiltered dmesg/logcat around `wlan_pd` UP; enumerate QRTR services for DMS/NAS/WDS; decode QMI offline; then rollback to native v724 and verify `selftest fail=0`.

## Result

V1972/V1973 both used the approved Android handoff and rolled back cleanly. The fast-attach patch improved `rild` attach timing from `+3.888s` after `wlan_pd` UP to `+0.295s`, but `ptrace` attach still missed the producer edge.

| run | wlan_pd UP | rild attach | cnss-daemon attach | pm-service attach | rild delta | rollback selftest |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| V1972 | 44.571617 | 48.46 | 46.61 | 47.35 | +3.888s | `fail=0` |
| V1973 | 44.564909 | 44.86 | 45.73 | 48.41 | +0.295s | `fail=0` |

V1973 anchors the normal internal-modem boot path:

| event | timestamp |
| --- | ---: |
| `cnss-daemon wlfw_start` | 43.633197 |
| `cnss-daemon wlfw_service_request` | 43.705139 |
| `msm/modem/wlan_pd` UP (`0x1fffffff`) | 44.564909 |
| `icnss_qmi: QMI Server Connected` | 44.567384 |
| `WLAN FW is ready` | 49.524829 |
| `wlan0` event | 49.708131 |

The run is not the degraded PCIe/MHI path: `first_pcie_mhi_time` is `None`, and `wlan0` appears in the normal window.

## Decoded QMI

V1973 decoded substantially more RIL traffic than V1970/V1972 because `rild` was caught close to start:

| field | value |
| --- | --- |
| `rild` strace lines | 1493 |
| `rild` QIPCRTR lines | 890 |
| `rild` send/recv lines | 537 / 923 |
| DMS IDs | `0x0001`, `0x0020`, `0x0025`, `0x002d`, `0x005e`, `0x005f` |
| NAS IDs | `0x0002`, `0x0003`, `0x0034`, `0x0041`, `0x0042`, `0x0043`, `0x004d`, `0x004e`, `0x004f`, `0x0050`, `0x0051`, `0x0052`, `0x0053`, `0x005c`, `0x006b`, `0x0070`, `0x00ac`, `0x00d4`, `0x010c` |

First decoded service requests in the `rild` strace:

| service | first request | msg_id |
| --- | --- | --- |
| WDS | 20:39:04.414007 | `0x00a2` |
| NAS | 20:39:05.887468 | `0x0002` |
| DMS | 20:39:05.913215 | `0x0001` |
| SEC_RIL_SIDE_SERVICE | 20:39:05.934325 | `0x0006` |

These decoded DMS/NAS/WDS requests are all post-attach, and the attach itself is post-`wlan_pd` UP. Therefore V1973 proves that Android RIL uses DMS/NAS/WDS on the internal modem, but it does not prove or exclude an earlier pre-UP RIL QMI trigger.

## QRTR Enumeration

The same live window ran targeted QRTR lookup for DMS (`0x02`), NAS (`0x03`), WDS (`0x01`), plus wildcard enumeration. In V1973 the lookup matrix started at uptime `48.42`, after all straces attached, so it is useful for service presence context but not for the producer edge itself.

| lookup | status |
| --- | --- |
| DMS (`0x02`) | lookup completed; end-of-list/empty event |
| NAS (`0x03`) | lookup completed; end-of-list/empty event |
| WDS (`0x01`) | lookup completed; end-of-list/empty event |
| wildcard | captured 64 events |

## Interpretation

Process polling plus immediate `strace -p` is now empirically too late for the decisive edge. `rild` starts before `wlan_pd` UP and before `wlanmdsp.mbn` request, but the best attach landed `0.295s` after UP; the first decoded DMS/NAS messages are later still. Another `strace` retry is unlikely to close this because the limitation is attach-on-process-start latency, not QRTR parser coverage.

## Next

Use a pre-armed tracefs uprobe before Android userspace reaches `rild`, not another attach-based `strace` run. Reuse the V1934 pattern that already proved boot-prearmed uprobes on `/vendor/lib64/libqmi_cci.so`; add send-path probes for `qmi_client_send_msg_sync`/async or the relevant `libsec-ril.so` PLT callsites so the QMI `msg_id` is recorded before `wlan_pd` UP.

## Safety

V1972/V1973 used only the approved rollbackable Android handoff and restored `stage3/boot_linux_v724.img`. The post-rollback native selftest returned `pass=11 warn=1 fail=0`. No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, PMIC/GPIO/GDSC/regulator write, fake ONLINE state, or sda29 remount-write was performed.
