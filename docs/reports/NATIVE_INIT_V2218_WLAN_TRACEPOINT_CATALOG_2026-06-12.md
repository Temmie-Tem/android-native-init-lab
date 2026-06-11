# Native Init V2218 WLAN Tracepoint Catalog

## Result

- decision: `v2218-a90-uprobes-cataloged-bpf-attach-blocked-stock-tracepoints-ok`
- pass: `true`
- runner: `workspace/public/src/scripts/revalidation/native_kernel_wlan_tracepoint_catalog_v2218.py`
- evidence: `workspace/private/runs/kernel/v2218-wlan-tracepoint-catalog-20260612-062845/`
- selftest: `fail=0`

## What Ran

```bash
python3 -m py_compile workspace/public/src/scripts/revalidation/native_kernel_wlan_tracepoint_catalog_v2218.py
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_wlan_tracepoint_catalog_v2218.py
```

The run was read-only except bounded BPF/perf observer attaches. It did not
write tracefs controls, execute `probe_write_user`, scan/connect Wi-Fi, change
routes, reboot, flash, or write partitions.

## Evidence Summary

| Signal | Value |
| --- | ---: |
| `available_events` total | `1456` |
| `a90cnss` WLFW uprobes | `114` |
| `a90libqmi`/`a90pmsrv` QMI/PM uprobes | `67` |
| kernel Wi-Fi/cfg80211-ish events | `162` |
| PIL/subsystem events | `3` |
| qmi/dfc transport events | `11` |
| stock net stack events | `19` |
| scheduler/context events | `88` |
| power/clock events | `66` |

Representative event formats:

| Event | ID | Useful fields |
| --- | ---: | --- |
| `a90cnss:wlfw_start` | `1268` | `__probe_ip` |
| `a90cnss:wlfw_service_request` | `1269` | `__probe_ip` |
| `a90cnss:wlfw_cap_qmi` | `1271` | `__probe_ip` |
| `a90cnss:wlfw_bdf_entry` | `1331` | `__probe_ip`, `bdf_type` |
| `a90cnss:wlfw_qmi_ind_cb_entry` | `1368` | `__probe_ip`, `msg_id`, `payload_len` |
| `a90cnss:wlfw_handle_ind_type` | `1378` | `__probe_ip`, `ind_type` |
| `a90libqmi:libqmi_client_init_instance_entry` | `1456` | `__probe_ip`, `svc`, `instance`, `ind_cb`, `timeout`, `handle` |
| `msm_pil_event:pil_notif` | `595` | `event_name`, `code`, `fw_name` |
| `cfg80211:rdev_return_int` | `1107` | `wiphy_name`, `ret` |

Attach proof:

| Target | Field | Result | Count |
| --- | --- | --- | ---: |
| `timer:timer_start` | `function` | `extract-pass` | `23` |
| `msm_pil_event:pil_notif` | `code` | `extract-pass` | `0` |
| `cfg80211:rdev_return_int` | `ret` | `extract-pass` | `0` |
| `a90cnss:wlfw_start` | `__probe_ip` | `attach-failed errno=4` | `0` |
| `a90cnss:wlfw_service_request` | `__probe_ip` | `attach-failed errno=4` | `0` |
| `a90cnss:wlfw_cap_qmi` | `__probe_ip` | `attach-failed errno=4` | `0` |
| `a90cnss:wlfw_bdf_entry` | `__probe_ip` | `attach-failed errno=4` | `0` |

## Interpretation

V2218 changes the next observer design in two ways:

1. The best WLAN-side names are no longer generic `cfg80211` alone. The current
   boot exposes a rich `a90cnss`/`a90libqmi`/`a90pmsrv` trace surface for the
   exact WLFW/QMI path: `wlfw_start`, `wlfw_service_request`, capability QMI,
   BDF, indication decode, DMS, PM client register/connect, and libqmi service
   lookup/client-init.
2. Those `a90*` events are trace_uprobe events created by
   `a90_android_execns_probe`, not ordinary static kernel tracepoints. Their
   `format`/`id` files are readable, but the existing v2192
   `perf_event_open(PERF_TYPE_TRACEPOINT)+BPF_PROG_TYPE_TRACEPOINT` attach path
   returns `EINTR` on them. The same helper attaches normally to stock
   `timer`, `msm_pil_event`, and `cfg80211` tracepoints, so this is not a
   generic BPF/perf failure.

Source checks match the live result:

- `BPF_PROG_TYPE_TRACEPOINT` direct ctx access is the trace record window; this
  kernel only unwraps the hidden `pt_regs` pointer for helper paths such as
  `bpf_get_stackid` and `bpf_perf_event_output`, not for arbitrary ctx register
  reads.
- `a90_android_execns_probe` registers `a90cnss` events by writing
  `p:a90cnss/<event> <target>:<offset> ...` into tracefs uprobe events and then
  enabling each event through tracefs.

Therefore V2218 should not claim tracepoint `ctx->regs` exact-reg sampling.
For `a90cnss` exact event PCs, the usable source is the `__probe_ip` field
already present in the trace_uprobe records. The missing piece is the collection
transport: BPF/perf attach is blocked for those dynamic uprobe events, while
tracefs trace-buffer collection remains the appropriate path.

## Next

V2219 should be a boot-window `a90cnss` tracefs-buffer collector, not another
BPF tracepoint attach attempt:

1. keep the existing `a90cnss`/`a90libqmi`/`a90pmsrv` uprobe registration path;
2. read the trace buffer or per-event hit accounting through the helper route
   that already owns those tracefs writes;
3. resymbolize `__probe_ip` values using the V2216/V2217 exact slide where
   kernel addresses are present;
4. use stock BPF tracepoint attach only for static kernel events such as
   `msm_pil_event` and `cfg80211`.

No Wi-Fi scan/connect or network mutation is needed for the next observer unit.
