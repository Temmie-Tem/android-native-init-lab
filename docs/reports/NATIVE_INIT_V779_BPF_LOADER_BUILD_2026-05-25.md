# Native Init V779 BPF Loader Build Report

## Result

- decision: `v779-bpf-loader-build-pass`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_bpf_loader_build_v779.py`
- evidence: `tmp/wifi/v779-bpf-loader-build/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_bpf_loader_build_v779.py
python3 scripts/revalidation/native_wifi_bpf_loader_build_v779.py plan
python3 scripts/revalidation/native_wifi_bpf_loader_build_v779.py run
```

## Evidence Summary

| Signal | Value |
| --- | --- |
| source | `stage3/linux_init/helpers/a90_bpf_trace_probe.c` |
| output | `tmp/wifi/v779-bpf-loader-build/a90_bpf_trace_probe-aarch64-static` |
| output size | `597920` bytes |
| output sha256 | `9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3` |
| ELF target | `ARM aarch64` |
| static linked | yes |
| `INTERP` program header | absent |
| version marker | `a90_bpf_trace_probe v779` |
| default mode | `--check-only` |
| attach gate | explicit `--allow-attach` required |

## Helper Contract

The helper is intentionally minimal and targets only
`msm_pil_event:pil_notif`.

- default execution is check-only and does not attach BPF;
- attach requires `--allow-attach`;
- attach path reads the tracepoint id from
  `/sys/kernel/tracing/events/msm_pil_event/pil_notif/id`;
- attach path loads a two-instruction `BPF_PROG_TYPE_TRACEPOINT` program that
  returns `0`;
- attach path uses `perf_event_open` and `PERF_EVENT_IOC_SET_BPF`;
- attach path enables the event for a short bounded idle window, disables it,
  and closes file descriptors.

V779 only built and inspected the helper. It did not deploy or run it.

## Safety

V779 executed no device command. It did not attach BPF, write ftrace controls,
trigger Wi-Fi, start service-manager/Wi-Fi HAL, scan, connect, use credentials,
change DHCP/routes, ping externally, reboot, flash, or write partitions.

## Next

V780 should deploy the helper and run only `--check-only` on device. The first
live deployment gate must verify binary hash, static execution, version marker,
and default no-attach behavior. BPF attach remains blocked until a later
separate gate.
