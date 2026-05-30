# V1227 mdm_helper Focused Trace Live Gate

- date: 2026-05-31
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper marker: `a90_android_execns_probe v254`
- helper build: `tmp/wifi/v1227-execns-helper-v254-build/a90_android_execns_probe`
- helper sha256: `6dd38887f6431db6748ff60d90600deb1650a37c735f05f21824d3e1b58bda8c`
- deploy evidence: `tmp/wifi/v1227-execns-helper-v254-deploy/manifest.json`
- live runner: `scripts/revalidation/native_wifi_mdm_helper_focused_trace_live_v1227.py`
- live evidence: `tmp/wifi/v1227-mdm-helper-focused-trace-live/manifest.json`
- live summary: `tmp/wifi/v1227-mdm-helper-focused-trace-live/summary.md`
- result: `v1227-focused-ptrace-stops-mdm-helper-before-esoc`
- pass: `true`

## Summary

V1227 added helper v254 with
`--pm-observer-mdm-helper-only-syscall-trace`. This narrows the V1226 broad
`ptrace-lite` behavior so earlier PM actors are not syscall-traced; only
`mdm_helper` is traced when `--allow-post-pm-mdm-helper-lower-trace` is active.

The deploy gate passed. The bounded live gate also reached the new focused
configuration: `pm_observer_mdm_helper_only_syscall_trace=1`,
`mdm_helper` tracing started, `per_mgr` syscall tracing stayed disabled, and
the safety gates remained closed.

The result is still an instrumentation blocker: pre-gate ptrace stops
`mdm_helper` before it opens `/dev/esoc-0`. The observer sees the traced
`mdm_helper` thread in `ptrace_stop`, `fd_esoc0_count.window=0`, no selected
syscall return records, no `ESOC_WAIT_FOR_REQ` record, and no `ks`/MHI/WLFW
progress.

## Classification

| evidence | value |
| --- | --- |
| helper deploy | `execns-helper-v254-deploy-pass` |
| live decision | `v1227-focused-ptrace-stops-mdm-helper-before-esoc` |
| focused flag seen | `true` |
| capture mode | `ptrace-lite` |
| `mdm_helper.trace_syscalls` | `1` |
| `mdm_helper.syscall_stop_count` | `3` |
| `mdm_helper.syscall_record_count` | `0` |
| `per_mgr.syscall_trace_started` | `0` |
| `mdm_helper_observable` | `1` |
| `mdm_helper` wchan | `ptrace_stop` |
| `/dev/esoc-0` fd count | `0` |
| `/dev/subsys_esoc0` attempt | `0` |
| `ESOC_WAIT_FOR_REQ` records | `0` |
| `ks` / MHI pipe | absent |
| WLFW / `wlan0` | absent |
| `mdm3` state | `OFFLINING` |

## Interpretation

- V1226's broad PM tracing was fixed enough to prove `per_mgr` no longer gets
  syscall-traced in V1227.
- The remaining issue is intrinsic to pre-gate ptrace: the parent waits for the
  `/dev/esoc-0` fd while the child is stopped by ptrace, so the fd can never
  appear.
- Repeating pre-gate ptrace with different filters is not useful.
- The next implementation should either attach after `mdm_helper` has opened
  `/dev/esoc-0`, or add compact helper-side event capture that does not stop
  `mdm_helper`.

## Next

V1228 should avoid pre-gate ptrace and implement one of:

- delayed attach after the existing `/dev/esoc-0` fd gate is satisfied;
- non-ptrace compact event markers inside the helper around
  `mdm_helper`/eSoC state;
- a dedicated post-gate observer that keeps the V1224 behavior intact and only
  captures `ESOC_WAIT_FOR_REQ` / post-request evidence after the fd exists.

## Validation

Executed:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v1227-execns-helper-v254-build/a90_android_execns_probe
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v254_deploy_preflight_v1227.py scripts/revalidation/native_wifi_mdm_helper_focused_trace_live_v1227.py
python3 scripts/revalidation/wifi_execns_helper_v254_deploy_preflight_v1227.py plan
python3 scripts/revalidation/native_wifi_mdm_helper_focused_trace_live_v1227.py plan
python3 scripts/revalidation/wifi_execns_helper_v254_deploy_preflight_v1227.py --apply --assume-yes --approval-phrase 'approve v1227 deploy execns helper v254 only; no daemon start and no Wi-Fi bring-up' run
python3 scripts/revalidation/native_wifi_mdm_helper_focused_trace_live_v1227.py run
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
