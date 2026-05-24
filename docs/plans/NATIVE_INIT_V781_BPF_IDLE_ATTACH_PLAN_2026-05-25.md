# Native Init V781 BPF Idle Attach Plan

## Goal

Classify whether the stock v724 kernel accepts a minimal BPF tracepoint
attach/detach on `msm_pil_event:pil_notif` using the reviewed V779/V780 helper.

## Scope

- helper: `/cache/bin/a90_bpf_trace_probe`
- helper sha256: `9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3`
- target tracepoint: `msm_pil_event:pil_notif`
- target id path: `/sys/kernel/tracing/events/msm_pil_event/pil_notif/id`
- mode: one idle attach attempt, no modem/WLAN trigger

## Safety Contract

- no Wi-Fi HAL/service-manager start
- no Wi-Fi scan/connect/link-up
- no credential use
- no DHCP, route changes, or external ping
- no modem/WLAN trigger commands such as `boot_wlan` or `qcwlanstate`
- no module load/unload, sysfs bind/unbind, reboot, flash, or partition write
- tracefs may be temporarily mounted only to read the tracepoint id; V781 must
  unmount it if V781 mounted it
- BPF attach is allowed only through `/cache/bin/a90_bpf_trace_probe --allow-attach --verbose`

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_bpf_idle_attach_v781.py
python3 scripts/revalidation/native_wifi_bpf_idle_attach_v781.py plan
python3 scripts/revalidation/native_wifi_bpf_idle_attach_v781.py \
  --allow-tracefs-mount \
  --allow-bpf-attach \
  --assume-yes \
  run
```

## Success Criteria

- V780 input manifest is `v780-bpf-loader-deploy-checkonly-pass`.
- Remote helper sha256 matches the reviewed V779 artifact.
- Tracepoint id is readable.
- The attach attempt is classified as either:
  - `attach-detach-pass`, meaning BPF observation can be used for the next gate;
  - or a bounded kernel denial/failure result, meaning BPF observation should not
    be relied on without a separate loader/kernel feasibility change.
- Tracefs cleanup returns to the pre-V781 mount state.

## Next

If attach/detach passes, V782 can wrap the observer around one bounded
read-only modem/WLAN state transition. If attach is denied, V782 should use
non-BPF tracepoint/eventfs or userspace QRTR observation instead.
