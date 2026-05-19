# Native Init v388 Servicemanager SIGABRT Triage

## Summary

V388 adds a host-only triage tool for the `system-servicemanager` SIGABRT captured by V387. The tool confirms the remaining blocker is not cleanup safety and not a missing private `/dev/binder` node. It also confirms the current evidence is still insufficient to select the exact AOSP fatal site.

No helper deploy, daemon start, Wi-Fi HAL start, scan, connect, credentials, DHCP, routing, rfkill write, firmware mutation, driver bind/unbind, or Android partition write was executed.

## Inputs

- V387 live manifest: `tmp/wifi/v387-approved-live-20260520-060136/manifest.json`
- V387 servicemanager evidence: `tmp/wifi/v387-approved-live-20260520-060136/native/run-system-servicemanager.txt`
- V387 approved result: `docs/reports/NATIVE_INIT_V387_APPROVED_LIVE_RESULT_2026-05-20.md`

## Source References

AOSP Android 11 source references:

- `servicemanager` main: `https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-release/cmds/servicemanager/main.cpp`
- `libbinder` ProcessState: `https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-release/libs/binder/ProcessState.cpp`

The relevant source-level fatal candidates are early startup paths around binder driver initialization, binder polling setup, and looper/timerfd setup. V388 does not claim one as proven because v387 did not capture the abort message or concrete PC/LR values.

## Artifact

New script:

```text
scripts/revalidation/wifi_service_manager_sigabrt_triage.py
```

Analysis evidence:

```text
tmp/wifi/v388-sigabrt-triage-20260520-060749/
```

## Result

Triage decision:

```text
decision: servicemanager-sigabrt-triage-needs-enhanced-crash-capture
pass: True
reason: SIGABRT is captured but abort message and register values are missing
next: add a bounded ptrace crash capture that records abort message/stack bytes and selected register values
remaining: abort-message-capture, register-value-capture
```

Safety flags:

```text
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Findings

Confirmed:

- SIGABRT is captured: `capture.crash.siginfo.signo=6`, `service_manager_start.signal=6`, and generic libc `Fatal signal 6` stderr are present.
- Postflight is safe: `service_manager_start.reaped=1`, `residual_cleared=1`, `postflight_safe=1`.
- Private `/dev/binder` exists in the namespace: `context.dev_binder.exists=1`.
- Private property root exists: `context.dev_properties.exists=1`.
- SELinux null compatibility node exists: `context.selinux_null.exists=1`.

Missing:

- No abort message, such as `Binder driver '/dev/binder' could not be opened` or `Failed to setupPolling`, was captured.
- No selected register values were captured; current evidence only has `capture.crash.regset.nt_prstatus.bytes=272`.
- No bounded stack bytes or abort-message memory/string scan was captured.

## Interpretation

V388 narrows the state as follows:

- The V386 cleanup blocker is closed by V387.
- The current private namespace has the expected Binder/property/SELinux-null surfaces at the file-node level.
- File-node presence does not prove Binder `open`, `ioctl(BINDER_VERSION)`, `BINDER_SET_MAX_THREADS`, or `mmap` success.
- AOSP fatal candidates are known, but current v387 evidence cannot select one without an abort message or PC/LR/register values.

Therefore, the next change should improve evidence capture before attempting a runtime repair.

## Validation

Commands run:

```text
python3 -m py_compile scripts/revalidation/wifi_service_manager_sigabrt_triage.py
python3 scripts/revalidation/wifi_service_manager_sigabrt_triage.py --out-dir tmp/wifi/v388-sigabrt-triage-20260520-060749/regression regression
python3 scripts/revalidation/wifi_service_manager_sigabrt_triage.py --out-dir tmp/wifi/v388-sigabrt-triage-20260520-060749/analyze --manifest tmp/wifi/v387-approved-live-20260520-060136/manifest.json analyze
python3 scripts/revalidation/a90ctl.py --json status
```

Validation results:

- Python compile: PASS.
- Regression: `servicemanager-sigabrt-triage-regression-pass`.
- Analysis: `servicemanager-sigabrt-triage-needs-enhanced-crash-capture` PASS.
- Read-only device status: PASS, `selftest: pass=11 warn=1 fail=0`, `netservice: disabled`, `rshell: stopped`.

`git diff --check`: PASS.

## Next Step

V389 should add enhanced bounded ptrace crash capture:

- selected AArch64 registers from `NT_PRSTATUS`, especially PC/LR/SP and x0-x8.
- bounded stack bytes or stack ASCII summary while the process is ptrace-stopped.
- bounded abort-message memory/string scan if available.
- compact output and approval-gated live execution.

Wi-Fi HAL/start/scan/connect remains blocked until the `servicemanager` SIGABRT fatal site is mapped or proven irrelevant to the Wi-Fi path.
