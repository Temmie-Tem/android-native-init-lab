# Native Init V781 BPF Idle Attach Report

## Result

- decision: `v781-bpf-idle-attach-detach-pass`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_bpf_idle_attach_v781.py`
- evidence: `tmp/wifi/v781-bpf-idle-attach/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_bpf_idle_attach_v781.py
python3 scripts/revalidation/native_wifi_bpf_idle_attach_v781.py plan
python3 scripts/revalidation/native_wifi_bpf_idle_attach_v781.py \
  --allow-tracefs-mount \
  --allow-bpf-attach \
  --assume-yes \
  run
```

## Evidence Summary

| Signal | Value |
| --- | --- |
| helper | `/cache/bin/a90_bpf_trace_probe` |
| helper sha256 | `9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3` |
| tracepoint | `msm_pil_event:pil_notif` |
| tracepoint id | `595` |
| BPF result | `attach-detach-pass` |
| BPF program fd | `3` |
| attach attempted | `1` |
| mounted before | `false` |
| mounted after | `false` |
| device status after | `BOOT OK`, `selftest pass=11 warn=1 fail=0` |

The final attach output:

```text
a90_bpf_trace_probe v779
target=msm_pil_event:pil_notif
tracepoint_id_path=/sys/kernel/tracing/events/msm_pil_event/pil_notif/id
tracepoint_id=595
bpf_prog_fd=3
result=attach-detach-pass
attach_attempted=1
```

## Interpretation

V781 proves the recovered stock v724 kernel accepts a minimal
`BPF_PROG_TYPE_TRACEPOINT` program attached through `perf_event_open` to
`msm_pil_event:pil_notif`. The proof is idle only: it did not trigger modem,
WLAN, ICNSS, QRTR, service-manager, Wi-Fi HAL, scan, connect, DHCP, or external
networking.

A preliminary no-verbose attach run returned `bpf-load-failed` with `errno=22`.
The passing runner uses `--verbose`, which sets the helper's BPF log level while
loading the same minimal program. Keep that load contract for future BPF gates
unless a separate helper revision explains and removes the need.

## Safety

- modem/WLAN trigger: not executed
- Wi-Fi HAL/service-manager start: not executed
- Wi-Fi scan/connect/link-up: not executed
- credential use: not executed
- DHCP/routes/external ping: not executed
- module load/unload: not executed
- sysfs bind/unbind: not executed
- reboot/flash/partition write: not executed
- tracefs cleanup: passed; tracefs was unmounted after V781

## Next

V782 can use the BPF observer around one bounded modem/WLAN state transition.
The next useful target is to capture `msm_pil_event:pil_notif` while executing a
minimal, previously tested native modem/WLAN readiness transition, still with no
Wi-Fi scan/connect, credentials, DHCP, routes, or external ping.
