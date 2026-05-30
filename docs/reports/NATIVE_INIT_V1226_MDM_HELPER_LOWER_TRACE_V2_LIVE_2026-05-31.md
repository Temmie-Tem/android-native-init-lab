# V1226 mdm_helper Lower Trace v2 Live Gate

- date: 2026-05-31
- runner: `scripts/revalidation/native_wifi_mdm_helper_lower_trace_v2_live_v1226.py`
- evidence: `tmp/wifi/v1226-mdm-helper-lower-trace-v2-live/manifest.json`
- summary: `tmp/wifi/v1226-mdm-helper-lower-trace-v2-live/summary.md`
- result: `v1226-ptrace-lite-perturbed-mdm-helper-window`
- pass: `true`

## Summary

V1226 reused the V1224 PM/CNSS path and forced helper `ptrace-lite` capture in
order to trace `mdm_helper` syscall returns around `/dev/esoc-0` and
`ESOC_WAIT_FOR_REQ`.

The result is a valid negative classification: the existing coarse
`ptrace-lite` mode perturbs the V1224 path before `mdm_helper` becomes
observable in the post-PM window. `mdm_helper` was started, but the post-PM
observer reported `mdm-helper-not-observable`; `pm-service` never attempted
`/dev/subsys_esoc0`; and no `mdm_helper` syscall records were captured.

This means V1226 did not prove the lower `ESOC_WAIT_FOR_REQ` return branch. It
proved that the current helper capture mode is too broad for this boundary and
must be replaced by either `mdm_helper`-only syscall tracing or compact
helper-side eSoC event capture.

## Classification

| evidence | value |
| --- | --- |
| decision | `v1226-ptrace-lite-perturbed-mdm-helper-window` |
| capture mode | `ptrace-lite` |
| `mdm_helper_start_executed` | `1` |
| `post_pm_result` | `mdm-helper-not-observable` |
| `post_pm_reason` | `mdm-helper-exited-before-post-pm-window` |
| `subsys_esoc0_open_attempted` | `0` |
| `mdm_helper` syscall records | `0` |
| `ESOC_WAIT_FOR_REQ` records | `0` |
| `per_mgr_syscall_trace_started` | `1` |
| `per_mgr_syscall_trace_truncated` | `1` |
| `per_proxy_exit_code` | `1` |
| `ks` / MHI pipe | absent |
| WLFW / `wlan0` | absent |
| `mdm3` state | `OFFLINING` |

## Interpretation

- V1224 remains the better behavioral baseline for the real PM/CNSS path.
- Existing helper `ptrace-lite` is not suitable as-is for this specific lower
  boundary because it also traces earlier PM actors and changes timing enough
  that `mdm_helper` is not observable when the post-PM window opens.
- The next implementation should not repeat broad `ptrace-lite` on the whole
  PM observer chain. It should either trace only `mdm_helper`, or add a compact
  helper-side marker for `openat`/`ioctl` around `/dev/esoc-0` and
  `ESOC_WAIT_FOR_REQ`.

## Next

V1227 should implement one of these focused approaches:

- helper-side `mdm_helper`-only syscall tracing, leaving `per_mgr` untraced;
- compact in-helper capture of `/dev/esoc-0` open, `ESOC_WAIT_FOR_REQ` return,
  and following `openat`/`ioctl`/`exec` errors;
- unchanged V1224 ordering and safety gates.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_lower_trace_v2_live_v1226.py
python3 scripts/revalidation/native_wifi_mdm_helper_lower_trace_v2_live_v1226.py plan
python3 scripts/revalidation/native_wifi_mdm_helper_lower_trace_v2_live_v1226.py run
```

Postflight:

- selftest: `pass=11 warn=1 fail=0`
- netservice: disabled, `ncm0=absent`, `tcpctl=stopped`

## Safety

- `wifi_hal_start_executed=false`
- `scan_connect_executed=false`
- `credential_use_executed=false`
- `dhcp_route_executed=false`
- `external_ping_executed=false`
- `wifi_bringup_executed=false`
- `boot_image_write_executed=false`
- `partition_write_executed=false`
- `flash_executed=false`
