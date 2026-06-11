# Native Init V2219 A90 Uprobe Trace Buffer Collector

## Result

- decision: `v2219-a90-uprobe-trace-buffer-ready-current-window-nohit`
- pass: `true`
- runner: `workspace/public/src/scripts/revalidation/native_kernel_a90_uprobe_trace_buffer_collector_v2219.py`
- evidence: `workspace/private/runs/kernel/v2219-a90-uprobe-trace-buffer-20260612-063949/`
- selftest: `fail=0`

## What Ran

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_kernel_a90_uprobe_trace_buffer_collector_v2219.py
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_a90_uprobe_trace_buffer_collector_v2219.py
```

The run used tracefs buffer reads only. It did not write tracefs controls,
attach BPF, execute `probe_write_user`, scan/connect Wi-Fi, change network
routes, reboot, flash, or write partitions.

## Evidence Summary

| Signal | Value |
| --- | ---: |
| selected `a90*` events | `21` |
| event dirs present | `21` |
| events enabled | `21` |
| current trace-buffer `a90*` lines | `0` |
| parsed hits | `0` |
| selftest | `fail=0` |

Enabled event set:

| Group | Events |
| --- | --- |
| `a90cnss` | `wlfw_start`, `wlfw_service_request`, `wlfw_ind_register_qmi`, `wlfw_cap_qmi`, `wlfw_bdf_entry`, `wlfw_bdf_send_ret`, `wlfw_qmi_ind_cb_entry`, `wlfw_handle_ind_type`, `wlfw_handle_ind_type_0x28`, `wlfw_handle_ind_type_0x2a`, `wlfw_handle_ind_type_0x41`, `dms_service_request`, `dms_get_wlan_address_entry`, `wlan_send_status_entry`, `wlan_send_version_entry`, `pm_init_pm_client_register_call`, `pm_init_pm_client_connect_call` |
| `a90libqmi` | `libqmi_client_init_instance_entry`, `libqmi_get_service_list_lookup_call`, `libqmi_get_service_list_lookup_ret` |
| `a90pmsrv` | `pm_service_post_ack_qmi_restart_ind_call` |

## Interpretation

V2219 implements the correct collection path for the V2218 boundary:

- V2218 proved stock tracepoints can use the existing BPF/perf attach path, but
  dynamic `a90*` trace_uprobe events return `EINTR` through that path.
- V2219 therefore does not retry BPF. It reads the trace buffer directly and
  parses `a90cnss`/`a90libqmi`/`a90pmsrv` trace lines into structured hit
  records.
- The current live device already has all 21 selected `a90*` events present and
  enabled, so the collector is compatible with the active boot state.

The current-window result has no `a90*` hits. That is expected for this late
idle validation window and must not be interpreted as absence during boot. The
important V2219 result is narrower: the read-only collector can verify
registration/enabled state, snapshot the trace buffer, parse matching lines,
and preserve private artifacts without BPF attach or tracefs writes.

## Next

V2220 should move the same collector into the relevant boot or helper window so
that it observes events while `cnss-daemon`, `pm-service`, and libqmi actually
run their WLFW/QMI paths. The next unit should still avoid Wi-Fi scan/connect
and should not add BPF attach for `a90*` events.

Concrete next gate:

1. reuse the existing helper route that registers/enables `a90*` uprobes;
2. collect trace buffer immediately after the bounded WLFW/QMI boot window;
3. parse first-hit lines for `wlfw_start`, `wlfw_service_request`,
   `wlfw_cap_qmi`, `wlfw_bdf_*`, `libqmi_*`, and PM register/connect edges;
4. keep stock BPF tracepoint attach limited to stock kernel tracepoints only.
