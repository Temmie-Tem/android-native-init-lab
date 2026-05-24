# Native Init V776 Tracepoint Inventory Report

## Result

- decision: `v776-tracepoint-candidates-found`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_tracepoint_inventory_v776.py`
- evidence: `tmp/wifi/v776-tracepoint-inventory/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_tracepoint_inventory_v776.py
python3 scripts/revalidation/native_wifi_tracepoint_inventory_v776.py plan
python3 scripts/revalidation/native_wifi_tracepoint_inventory_v776.py preflight
python3 scripts/revalidation/native_wifi_tracepoint_inventory_v776.py run \
  --allow-tracefs-mount \
  --assume-yes
```

## Evidence Summary

| Signal | Value |
| --- | --- |
| native version | `A90 Linux init 0.9.68 (v724)` |
| mounted before V776 | `false` |
| tracefs mount step | pass |
| mounted during inventory | `true` |
| unmount step | pass |
| mounted after cleanup | `false` |
| `available_events` readable | `true` |
| `available_events` total | `1250` |
| candidate total | `153` |
| BPF attach executed | `false` |
| Wi-Fi action executed | `false` |
| scan/connect/credential use | `false` |
| DHCP/routes/external ping | `false` |
| reboot/flash/partition write | `false` |

Candidate counts:

| Candidate Group | Count | Most Relevant Sample |
| --- | ---: | --- |
| ICNSS/WLAN/Wi-Fi | `1` | `cfg80211:cfg80211_report_wowlan_wakeup` |
| QMI/QRTR/service | `1` | `dfc:dfc_qmi_tc` |
| subsystem/remoteproc | `3` | `msm_pil_event:pil_event`, `msm_pil_event:pil_notif`, `msm_pil_event:pil_func` |
| network stack | `39` | `net:*`, `skb:*`, `napi:*`, `sock:*`, `udp:*` |
| scheduler/workqueue/IRQ | `109` | `sched:*`, `workqueue:*`, `irq:*`, `timer:*` |

## Interpretation

V776 proves that the recovered stock v724 kernel has usable tracefs event
inventory even though function ftrace, kprobes, and dynamic debug remain
unavailable. This does not yet prove that attaching a BPF program is safe or
useful; it only proves that candidate tracepoints can be enumerated.

The most useful Wi-Fi-adjacent static tracepoints are not direct ICNSS/QCACLD
function boundaries. The practical candidates are:

1. `msm_pil_event:*` for modem/PIL/subsystem progression;
2. `dfc:dfc_qmi_tc` as a coarse QMI-adjacent signal;
3. generic `net:*`/`skb:*`/`napi:*` if a later WLAN interface exists;
4. scheduler/workqueue events only as broad timing context, not primary Wi-Fi
   evidence.

V777 should therefore classify candidate event format/fields before any attach
proof. If `msm_pil_event:*` exposes useful fields around modem/PIL transitions,
that is a better next stock-kernel observer than returning to custom kernel
instrumentation.

## Safety

V776 performed only temporary tracefs mount/read/cleanup. It did not write trace
controls, attach BPF, trigger Wi-Fi, start service-manager/Wi-Fi HAL, scan,
connect, use credentials, change DHCP/routes, ping externally, reboot, flash, or
write partitions.

## Next

V777 should stay on stock v724 and inspect tracepoint `format` files for:

- `msm_pil_event:pil_event`
- `msm_pil_event:pil_notif`
- `msm_pil_event:pil_func`
- `dfc:dfc_qmi_tc`
- `cfg80211:cfg80211_report_wowlan_wakeup`

Only after field semantics are useful should a bounded BPF tracepoint attach
proof be considered. Custom OSRC kernel flashing remains paused.
