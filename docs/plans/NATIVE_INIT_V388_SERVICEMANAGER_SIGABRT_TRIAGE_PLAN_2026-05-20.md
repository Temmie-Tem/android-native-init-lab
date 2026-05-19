# Native Init v388 Servicemanager SIGABRT Triage Plan

## Purpose

V387 fixed the `hwservicemanager` cleanup blocker. The remaining pre-Wi-Fi blocker is `system-servicemanager` exiting early with SIGABRT while cleanup remains safe.

V388 is a host-only evidence triage step. It should not start service-manager again and should not attempt Wi-Fi HAL/start/scan/connect. Its purpose is to decide whether the captured v387 evidence is enough for a targeted runtime repair or whether the next helper needs more crash context.

## Inputs

- V387 approved result: `docs/reports/NATIVE_INIT_V387_APPROVED_LIVE_RESULT_2026-05-20.md`
- V387 live evidence: `tmp/wifi/v387-approved-live-20260520-060136/`
- V387 servicemanager run: `tmp/wifi/v387-approved-live-20260520-060136/native/run-system-servicemanager.txt`
- V387 classifier: `tmp/wifi/v387-approved-live-20260520-060136/classify/manifest.json`

## Source References

AOSP Android 11 sources used for fatal-site candidates:

- `servicemanager` main: `https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-release/cmds/servicemanager/main.cpp`
- `libbinder` ProcessState: `https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-release/libs/binder/ProcessState.cpp`

Relevant fatal candidates:

- `ProcessState::initWithDriver(driver)` opens `/dev/binder`.
- `ProcessState` can fatal if binder open/ioctl/mmap leaves `mDriverFD < 0`.
- `BinderCallback::setupTo()` can fatal if binder polling setup fails.
- Looper/timerfd setup has fatal checks after the context-manager path.

## Implementation

Add `scripts/revalidation/wifi_service_manager_sigabrt_triage.py`:

- read the approved live manifest and `system-servicemanager` evidence file.
- confirm SIGABRT and postflight safety.
- verify current namespace materialization evidence for `/dev/binder`, `/dev/__properties__`, and `/sys/fs/selinux/null`.
- detect whether abort message, register values, stack bytes, or abort-message memory were captured.
- emit a fail-closed JSON manifest and Markdown summary.
- execute no bridge command and no device mutation.

## Expected Decision

The expected decision is:

```text
servicemanager-sigabrt-triage-needs-enhanced-crash-capture
```

Reason: v387 captured SIGABRT and compact crash summaries, but not the abort message, selected register values, stack bytes, or abort-message memory. That makes AOSP fatal-site selection unproven.

## Validation

- Python compile for the new triage script.
- Script regression sample.
- Script analysis against v387 approved evidence.
- Read-only device `status` after analysis to confirm no disruption.
- `git diff --check`.

## Non-Goals

V388 must not perform:

- helper deploy.
- service-manager/hwservicemanager/vndservicemanager start.
- Wi-Fi HAL start.
- Wi-Fi scan/connect/link-up.
- credentials, DHCP, routing, rfkill writes.
- driver bind/unbind or firmware mutation.
- Android partition writes.

## Next Step If Expected Decision Holds

V389 should add enhanced bounded crash capture to the helper:

- selected AArch64 register values from `NT_PRSTATUS`, especially PC/LR/SP and x0-x8.
- bounded stack bytes or stack ASCII summary from the ptrace-stopped crash.
- bounded abort-message memory/string scan if available.
- keep output compact and approval-gated.
