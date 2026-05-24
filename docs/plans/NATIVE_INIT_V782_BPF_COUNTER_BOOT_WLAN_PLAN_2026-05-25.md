# Native Init V782 BPF Counter Boot WLAN Plan

## Goal

Use the V781-proven tracepoint attach path as a real observer by counting
`msm_pil_event:pil_notif` events during one bounded lower-window `boot_wlan`
transition.

## Scope

- new helper source: `stage3/linux_init/helpers/a90_bpf_trace_counter.c`
- remote helper: `/cache/bin/a90_bpf_trace_counter`
- tracepoint: `msm_pil_event:pil_notif`
- transition: firmware read-only mounts → `subsys_modem` holder → lower
  companion stack → bounded `a90_wlanbootctl boot-observe`
- observer: BPF array-map counter attached before the lower transition and
  collected before reboot cleanup

## Safety Contract

- no Wi-Fi HAL/service-manager start
- no Wi-Fi scan/connect/link-up
- no credential use
- no DHCP, route changes, or external ping
- no `qcwlanstate ON`
- no module load/unload
- no sysfs bind/unbind or `driver_override`
- no `esoc0` access
- no boot image or partition write
- reboot cleanup is allowed after the bounded runtime mutation

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_bpf_counter_boot_wlan_v782.py
python3 scripts/revalidation/native_wifi_bpf_counter_boot_wlan_v782.py plan
python3 scripts/revalidation/native_wifi_bpf_counter_boot_wlan_v782.py \
  --allow-bpf-counter-deploy \
  --allow-tracefs-mount \
  --allow-bpf-attach \
  --allow-lower-window-boot-wlan \
  --assume-yes \
  run
```

## Success Criteria

- BPF counter helper builds as static aarch64 with no interpreter.
- BPF counter helper deploys and passes `--check-only`.
- BPF counter returns `result=attach-count-pass`.
- The lower-window transition executes and is classified with BPF event count.
- Cleanup returns to healthy stock v724 native init.

## Next

If `wlan0` or wiphy appears, move to a scan-only readiness gate. If the result
remains control-surface-only, use the BPF count and dmesg delta to choose the
next lower trigger instead of repeating blind `boot_wlan`.
