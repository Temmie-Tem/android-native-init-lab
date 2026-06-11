# Native Init V2220 A90 Helper Summary Trace Parser

## Result

- decision: `v2220-helper-summary-parser-validated-existing-hit-current-nohit`
- pass: `true`
- runner: `workspace/public/src/scripts/revalidation/a90_kernel_v2220_helper_summary_trace_parser.py`
- evidence: `workspace/private/runs/kernel/v2220-helper-summary-trace-parser-20260612-064823/`
- mode: host-only parser validation

## What Ran

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_kernel_v2220_helper_summary_trace_parser.py
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/a90_kernel_v2220_helper_summary_trace_parser.py
```

The run parsed existing on-disk artifacts only. It did not talk to the device,
write tracefs controls, attach BPF, execute `probe_write_user`, scan/connect
Wi-Fi, change routes, reboot, flash, or write partitions.

## Evidence Summary

| Signal | Value |
| --- | ---: |
| parsed sources | `7` |
| normalized events | `219` |
| surface rollups | `12` |
| hit events | `141` |
| key hit events | `5` |
| event hits | `304` |
| surface-rollup hits | `199` |
| V2219 current-window no-hit summaries | `2` |

Key event hits normalized by the parser:

| Event | Hits | First Timestamp | First Line |
| --- | ---: | ---: | --- |
| `nonlog:wlfw_start` | `3` | `3.438180` | `cnss-daemon-558 ... wlfw_start: (0x557e183c00)` |
| `uprobe:wlfw_start` | `3` | `6.732163` | `cnss-daemon-620 ... wlfw_start: (0x556109dc00)` |
| `uprobe:wlfw_service_request` | `3` | `6.737597` | `cnss-daemon-631 ... wlfw_service_request: (0x556109c9fc)` |
| `uprobe:wlfw_cap_qmi` | `2` | `7.953156` | `cnss-daemon-631 ... wlfw_cap_qmi: (0x556109e460)` |
| `uprobe:wlfw_bdf_entry` | `2` | `9.266491` | `cnss-daemon-625 ... wlfw_bdf_entry: (0x556275c76c) bdf_type=0x4` |

Inputs used by the default parser run:

- `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-v2168-hidl-exact-v8/helper.strings.txt`
- `tmp/wifi/v1998-helper-strings.txt`
- `tmp/wifi/v1719-cnss-peripheral-client-uprobe-handoff/manifest.json`
- `tmp/wifi/v1710-cnss-wlfw-pre-dms-microtrace-handoff/manifest.json`
- `tmp/wifi/v1705-cnss-wlfw-downstream-uprobe-handoff/manifest.json`
- `workspace/private/runs/kernel/v2219-a90-uprobe-trace-buffer-20260612-063915/summary.json`
- `workspace/private/runs/kernel/v2219-a90-uprobe-trace-buffer-20260612-063949/summary.json`

## Interpretation

V2220 closes the immediate post-V2219 tooling gap. The same parser now accepts:

1. helper-owned summary lines such as
   `wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_start.hit_count=...`;
2. legacy manifest fields such as `nonlog_wlfw_start_hit_count`;
3. raw trace-buffer lines for `a90cnss`, `a90libqmi`, and `a90pmsrv`;
4. V2219 `summary.json` files with current-window no-hit state.

The output separates surface-level rollups from real event hits, so aggregate
counts such as `uprobe.hit_count` do not mask the concrete WLFW/QMI events.

The result is intentionally not a new boot-window capture. The current goal is
read-only continuation from the active state, and the relevant WLFW/QMI events
fire during early boot/helper windows. Capturing those live again requires an
approved reboot/test-boot or a helper-owned boot-window route. V2220 prepares
the parser and proves it against existing boot-window hits plus current V2219
no-hit summaries.

## Next

V2221 should use this parser as the common post-processor for the next approved
boot-window helper run. The expected capture path remains:

1. keep `a90*` dynamic uprobes on the helper-owned tracefs route;
2. collect immediately around the WLFW/QMI boot window;
3. parse with `a90_kernel_v2220_helper_summary_trace_parser.py`;
4. compare `wlfw_start → wlfw_service_request → cap_req → BDF` against current
   stock kernel/cfg80211 observer output.

Do not retry BPF attach on `a90*` dynamic trace_uprobe events; V2218 already
showed that path returns `EINTR`.
