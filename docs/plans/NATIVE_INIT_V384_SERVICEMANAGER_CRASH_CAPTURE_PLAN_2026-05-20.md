# V384 Plan: Service-Manager SIGABRT Early-Crash Capture

## Summary

- V384 targets the remaining V382/V383 blocker: `system-servicemanager` exits with `SIGABRT` before becoming observable, while `system-hwservicemanager` survives the bounded start-only window.
- Scope is local/helper-only preparation unless an explicit deploy/live approval is provided later.
- Goal: build `a90_android_execns_probe v15` with service-manager start-only crash-capture support, then add guarded host wrappers for plan/preflight/deploy/live sequencing.
- Wi-Fi HAL/start/scan/connect/link-up remains blocked.

## Evidence Baseline

- V382 approved result: `docs/reports/NATIVE_INIT_V382_APPROVED_DEPLOY_LIVE_RESULT_2026-05-20.md`
- V383 classifier: `docs/reports/NATIVE_INIT_V383_SERVICEMANAGER_SIGABRT_CLASSIFIER_2026-05-20.md`
- Current remote helper: `/cache/bin/a90_android_execns_probe` v14, SHA `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7`
- V383 decision: `service-manager-runtime-gap-servicemanager-sigabrt-capture-required`

## Source Notes

- AOSP Android 11 `servicemanager` calls Binder setup paths that use fatal checks around Binder polling, Looper registration, and context-manager setup.
- AOSP Android 11 `Access` construction uses SELinux service-context handles and `CHECK`-style required setup.
- AOSP `servicemanager.rc` runs `servicemanager` as `user system`, `group system readproc`; the helper already approximates this identity contract.

References:

- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-gsi/cmds/servicemanager/main.cpp
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-gsi/cmds/servicemanager/Access.cpp
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-gsi/cmds/servicemanager/servicemanager.rc

## Key Changes

### Helper v15

- Bump helper marker to `a90_android_execns_probe v15`.
- Allow `--capture-mode ptrace-lite` for `--mode service-manager-start-only` only when `--allow-service-manager-start-only` is also present.
- Add a service-manager-specific ptrace-lite execution path or adapt the existing ptrace-lite capture primitive to service-manager start-only.
- Capture, at minimum:
  - exec stop marker
  - crash stop marker
  - signal and siginfo
  - limited register snapshot
  - `/proc/<pid>/status`
  - `/proc/<pid>/maps`
  - `/proc/<pid>/mountinfo`
  - stdout/stderr before abort
- Preserve bounded lifecycle:
  - timeout remains `1..30s`
  - postflight must prove process/group stopped
  - no Wi-Fi HAL/CNSS/wificond/supplicant/hostapd start
  - no scan/connect/link-up/DHCP/routing

### Host Tooling

- Add v15 local build artifact under `tmp/wifi/v384-a90_android_execns_probe-v15/`.
- Add a deploy wrapper equivalent to V382 but with v15 marker/SHA and exact V384 approval phrase.
- Add a live runner profile that uses:
  - helper v15 SHA
  - `--capture-mode ptrace-lite`
  - `--property-root /mnt/sdext/a90/private-property-v317/dev/__properties__`
  - `--data-wifi-mode private-empty`
- Add classifier support for ptrace evidence keys:
  - `capture.crash_stop=1`
  - `capture.crash.siginfo.*`
  - `capture.crash.regset.*`
  - `capture.crash.mountinfo/maps/status`

## Approval Boundaries

V384 local build/regression requires no device mutation.

Deploy approval phrase candidate:

```text
approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up
```

Live crash-capture approval phrase candidate:

```text
approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

Without exact approval, the wrappers must return approval-required and execute no bridge/device mutation.

## Test Plan

### Local Static

```bash
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra \
  -o tmp/wifi/v384-a90_android_execns_probe-v15/a90_android_execns_probe \
  stage3/linux_init/helpers/a90_android_execns_probe.c

file tmp/wifi/v384-a90_android_execns_probe-v15/a90_android_execns_probe
sha256sum tmp/wifi/v384-a90_android_execns_probe-v15/a90_android_execns_probe
strings tmp/wifi/v384-a90_android_execns_probe-v15/a90_android_execns_probe | \
  rg 'a90_android_execns_probe v15|service-manager-start-only|ptrace-lite'
```

### Host Regression

- no-approval deploy: `approval-required`, no device command/mutation
- no-approval live: `approval-required`, no daemon start, no Wi-Fi bring-up
- classifier regression: PASS including synthetic ptrace crash evidence
- `git diff --check`
- `python3 -m py_compile` for modified host scripts

### Optional Live Later

Only after explicit approval:

1. deploy v15 helper
2. run bounded service-manager ptrace-lite crash capture
3. route/classify evidence
4. verify postflight clean and Wi-Fi bring-up false

## Acceptance

- Local v15 helper builds and exposes the new marker and allowed capture mode.
- Existing v14 behavior remains conceptually unchanged unless v15 is explicitly deployed.
- No unapproved live service-manager start occurs.
- V384 produces enough evidence to determine whether the SIGABRT is due to Binder context-manager setup, SELinux/service-context setup, property runtime, missing mount namespace material, or another fatal check.
