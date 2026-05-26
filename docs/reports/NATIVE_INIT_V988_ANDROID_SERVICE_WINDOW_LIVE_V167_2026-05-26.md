# V988 Android Service-Window Live v167

- generated: `2026-05-26`
- scope: bounded start-only live proof
- decision: `v970-android-service-window-runtime-gap`
- pass: `True`
- evidence: `tmp/wifi/v988-android-service-window-live-v167/manifest.json`
- helper: `a90_android_execns_probe v167`

## Summary

V988 reran the Android service-window proof with helper `v167`. The new
`wificond` ptrace path worked and captured the crash stop.

The blocker remains a runtime gap, not a cleanup or safety failure:

- all planned service-window actors were spawned
- property service shim started and handled bounded requests
- `wificond` was traced and stopped on `SIGABRT`
- WLFW/BDF/`wlan0` preconditions remained absent
- cleanup completed without reboot

## Wificond Crash Capture

Key captured markers:

```text
wifi_hal_composite_start.child.wificond.traced=1
wifi_hal_composite_child.wificond.ptrace_traceme=1
wifi_hal_composite_start.child.wificond.trace.initial_stop=1
wifi_hal_composite_start.child.wificond.trace.exec_stop=1
wifi_hal_composite_start.child.wificond.trace.crash_stop=1
capture.crash.siginfo.signo=6
capture.crash.siginfo.code=-1
capture.crash.exe=/tmp/a90-v231-1178/root/system/bin/wificond
capture.crash.maprow.pc.path=/tmp/a90-v231-1178/root/apex/com.android.runtime/lib64/bionic/libc.so
capture.crash.maprow.pc.relative_offset=0x8bebc
capture.crash.maprow.frame0_ra.path=/tmp/a90-v231-1178/root/system/bin/wificond
capture.crash.maprow.frame0_ra.relative_offset=0x2ab04
capture.crash.maprow.frame1_ra.relative_offset=0x2c540
capture.crash.maprow.frame2_ra.relative_offset=0x2bc30
capture.crash.maprow.frame3_ra.relative_offset=0x199b4
```

Interpretation:

- `SIGABRT` is confirmed by ptrace, not just stderr.
- PC/LR are in bionic `libc.so`, consistent with abort delivery.
- The useful next diagnostic is symbol/string classification of the
  `wificond` return-address offsets.
- The remaining stderr still includes the old property protocol warning, but
  V988 proves the service-window property shim itself is running.

## Guardrails

- no `qcwlanstate`
- no `IWifi.start`
- no `/dev/subsys_esoc0` open
- no eSoC ioctl
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no cleanup reboot required

## Validation

Command:

```bash
python3 scripts/revalidation/native_wifi_android_service_window_live_v970.py \
  --out-dir tmp/wifi/v988-android-service-window-live-v167 \
  --local-helper tmp/wifi/v986-execns-helper-v167-build/a90_android_execns_probe \
  --helper-sha256 fa96337b9103a411d6e229fe9ada744a6ed7df296f3d986e5a9d00a861736626 \
  --helper-marker "a90_android_execns_probe v167" \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-android-wifi-service-window \
  --allow-cleanup-reboot \
  --assume-yes \
  run
```

Result:

```text
decision: v970-android-service-window-runtime-gap
pass: True
wifi_bringup_executed: False
external_ping_executed: False
cleanup_reboot_executed: False
```

Post-run device status:

```text
boot: BOOT OK shell 4.6s
selftest: pass=11 warn=1 fail=0
```

## Next

V989 should classify the `wificond` crash offsets against a matching
`/system/bin/wificond` binary and its available symbols/strings. If symbols are
not available, capture a bounded binary fingerprint plus disassembly window
around offsets `0x199b4`, `0x2ab04`, `0x2bc30`, and `0x2c540`.
