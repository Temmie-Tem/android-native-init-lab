# Native Init V2238 Static Tracepoint Object-Chain Audit

Date: `2026-06-12`

## Identity

| Field | Value |
| --- | --- |
| Run ID | `V2238` |
| Track | `T1 kernel observation` |
| Device baseline | `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)` |
| Runner | `workspace/public/src/scripts/revalidation/native_kernel_static_tracepoint_object_chain_audit_v2238.py` |
| Private evidence | `workspace/private/runs/kernel/v2238-static-tracepoint-object-chain-audit-20260612-104909/` |
| Device flash | no |
| Wi-Fi scan/connect/DHCP/ping | no |

## Track Selection

The north-star order in `GOAL.md` requires T1 before T2. T1 was still safely
actionable because V2216/V2217 pinned exact live-register symbolization, and the
next unresolved question was whether WLAN-adjacent static tracepoints expose raw
object pointers suitable for `bpf_probe_read()` object-chain reads.

No track transition occurred. T2 WLAN work was not selected because the T1
object-chain feasibility boundary had not been closed.

## Question

Can the current stock static tracepoints serve as object anchors for read-only
WLAN/cfg80211/QRTR kernel object-chain observation?

Specifically, do records such as `cfg80211:*`, `msm_pil_event:*`, or QRTR-related
static tracepoints retain raw pointers like `struct wiphy *`, `struct net_device
*`, `struct wireless_dev *`, `struct cfg80211_scan_request *`, or `struct
pil_desc *` that a BPF tracepoint program can dereference?

## Method

The runner performed a read-only source/live audit:

1. parsed stock kernel source trace definitions from
   `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`;
2. classified `TRACE_EVENT`, `DECLARE_EVENT_CLASS`, and `DEFINE_EVENT` records in:
   - `net/wireless/trace.h` (`cfg80211`);
   - `include/trace/events/trace_msm_pil_event.h` (`msm_pil_event`);
   - `include/trace/events/dfc.h` (`dfc`);
3. compared `TP_PROTO` pointer arguments against `TP_STRUCT__entry` fields;
4. detected scalarizing macros such as `WIPHY_ENTRY`, `WDEV_ENTRY`,
   `NETDEV_ENTRY`, `CHAN_ENTRY`, `MAC_ENTRY`, and `SINFO_ENTRY`;
5. checked the current V2237 device state and selftest without mounting tracefs,
   attaching BPF, enabling events, scanning Wi-Fi, or mutating network state.

Validation commands:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_kernel_static_tracepoint_object_chain_audit_v2238.py
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_static_tracepoint_object_chain_audit_v2238.py
```

## Result

Decision:

```text
v2238-static-tracepoint-object-chain-audit-pass
```

Summary:

| Metric | Value |
| --- | ---: |
| `cfg80211` source events/classes resolved as events | `162` |
| `dfc` events | `11` |
| `msm_pil_event` events | `3` |
| `record-pointer-chain-possible` events | `0` |
| `caller-pointer-record-scalarized` events | `159` |
| `caller-pointer-not-retained` events | `1` |
| `scalar-only` events | `16` |
| important scalarized events | `7` |
| QRTR static trace definitions | `0` |
| current V2237 `selftest fail=0` | `true` |
| current live tracefs readable without mounting | `false` |

Important scalarized events:

```text
cfg80211:cfg80211_inform_bss_frame
cfg80211:cfg80211_scan_done
cfg80211:cfg80211_send_rx_assoc
cfg80211:rdev_connect
cfg80211:rdev_return_int
cfg80211:rdev_scan
msm_pil_event:pil_event
```

QRTR source candidates existed (`net/qrtr/qrtr.c`, `net/qrtr/qrtr.h`, and UAPI /
DT bindings), but no source `TRACE_EVENT` definitions were found outside build
outputs.

## Interpretation

The static tracepoint object-chain route is not viable on this kernel as a raw
pointer anchor path.

`cfg80211` tracepoints receive rich object pointers in `TP_PROTO`, but the trace
records intentionally scalarize them:

- `WIPHY_ENTRY` stores `wiphy_name`, not `struct wiphy *`;
- `WDEV_ENTRY` stores `wdev->identifier`, not `struct wireless_dev *`;
- `NETDEV_ENTRY` stores interface name and ifindex, not `struct net_device *`;
- `CHAN_ENTRY` stores band/frequency, not `struct ieee80211_channel *`;
- `MAC_ENTRY` copies MAC bytes, not the source pointer;
- `SINFO_ENTRY` copies selected counters, not `struct station_info *`.

`msm_pil_event` likewise records event strings, firmware name, and notification
code. It does not retain the `struct pil_desc *` from `pil_event` as a raw
pointer field.

QRTR has source files but no exposed static tracepoint definitions in this stock
source tree. Therefore there is no QRTR static tracepoint record to use as an
object-chain anchor.

This matches V2218's live attach boundary: static kernel tracepoints remain
useful for scalar lifecycle correlation, while dynamic `a90*` WLFW/QMI events
must stay on the helper-owned tracefs route because BPF tracepoint attach is not
the right path for those trace_uprobe records.

## Decision

Do not spend another T1 iteration trying to dereference cfg80211, PIL, or QRTR
objects from stock static tracepoint records. The records do not retain the raw
object pointers needed for that chain.

Use these T1 paths instead:

1. static tracepoints for scalar lifecycle correlation (`cfg80211`, `msm_pil_event`,
   `dfc`, net stack);
2. helper-owned `a90cnss`/`a90libqmi`/`a90pmsrv` tracefs records for WLFW/QMI
   edge sequencing;
3. exact-slide live-register sampling for code-path identity;
4. if raw object pointers are required, use a different anchor class, not the
   scalarized static tracepoint record.

## Safety

- `host_only_source_analysis`: false, because the runner also queried the live
  device status/selftest.
- `tracefs_control_write`: false.
- `bpf_attach`: false.
- `probe_write_user_executed`: false.
- `wifi_scan_connect`: false.
- `network_route_change`: false.
- `flash_reboot`: false.
- `partition_write`: false.
- final live selftest: `fail=0`.
