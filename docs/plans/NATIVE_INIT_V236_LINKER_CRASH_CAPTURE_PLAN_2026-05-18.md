# v236 Plan: Bounded Linker Crash Context Capture

## Summary

- v236 is a host/helper investigation step, not a native-init PID1 boot image update.
- Baseline remains `A90 Linux init 0.9.59 (v159)` unless a later boot image is explicitly flashed.
- Goal: capture bounded crash context for the reproducible Android linker `SIGSEGV(11)` found in v233-v235.
- The helper still runs only `linker64 --list`; no Wi-Fi daemon entrypoint, scan, connect, credential, DHCP, routing, or RF mutation is allowed.

## Current Evidence

- v233: real Android generated `/linkerconfig` did not prevent `linker64 --list` crash.
- v234: safe system targets and `cnss-daemon` all crashed, so the failure is not target-specific.
- v235: `/system/bin/linker64` and direct `/apex/com.android.runtime/bin/linker64` both crashed, so the failure is not just the `/system/bin/linker64` symlink path.
- Therefore the next useful evidence is process context at exec/crash time: auxv, maps, mountinfo, exe/cwd, siginfo, and register state.

## Key Changes

- Extend `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper v5.
- Add `--capture-mode none|ptrace-lite`.
- `ptrace-lite` is bounded and only traces the helper's own child process:
  - child calls `PTRACE_TRACEME` and stops before chroot/exec;
  - parent sets `PTRACE_O_TRACEEXEC | PTRACE_O_EXITKILL`;
  - parent captures exec-stop `/proc/<pid>/auxv`, `/proc/<pid>/maps`, `/proc/<pid>/mountinfo`, `/proc/<pid>/exe`, `/proc/<pid>/cwd`, and `NT_PRSTATUS` regset;
  - parent captures crash-stop `siginfo`, regset, and the same bounded `/proc` context;
  - parent then delivers the original crash signal so normal wait status remains visible.
- Add host wrapper `scripts/revalidation/wifi_linker_crash_capture_probe.py`.
- Keep v236 matrix intentionally small:
  - linker paths: `system-linker`, `apex-linker`
  - targets: `system-toybox`, `apex-linker64-self`, `cnss-daemon`
  - env: `clean`

## Decision Labels

- `android-linker-crash-context-captured`: all selected cases reproduced `SIGSEGV(11)` and ptrace-lite captured crash context markers.
- `android-linker-crash-capture-partial`: crash reproduced but one or more capture markers are missing.
- `android-linker-debug-output-ready`: stdout/stderr diagnostics appeared.
- `android-linker-list-baseline-pass`: at least one selected case exited 0.
- `android-linker-crash-capture-blocked`: bridge/helper/input prerequisite is missing.
- `android-linker-crash-capture-manual-review-required`: matrix completed but does not fit stronger labels.

## Guardrails

- No daemon entrypoint execution.
- No `cnss_diag`, Wi-Fi scan/connect/link-up, credentials, DHCP, routing, public listener, or RF state mutation.
- No global bind mounts; helper uses private mount namespace only.
- No persistent Android partition writes.
- `ptrace-lite` must only trace the helper's own child, never arbitrary system processes.
- Capture output is bounded: text `/proc` captures are capped and binary auxv/registers are summarized.

## Test Plan

Static validation:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh
python3 -m py_compile scripts/revalidation/wifi_linker_crash_capture_probe.py
git diff --check
```

Live validation when ACM bridge and NCM transfer are available:

```bash
python3 scripts/revalidation/tcpctl_host.py \
  --device-binary /cache/bin/a90_android_execns_probe \
  --toybox /cache/bin/toybox \
  install \
  --local-binary stage3/linux_init/helpers/a90_android_execns_probe \
  --transfer-timeout 120

python3 scripts/revalidation/tcpctl_host.py \
  --device-binary /cache/bin/a90_real_ld.config.txt \
  --toybox /cache/bin/toybox \
  install \
  --local-binary tmp/wifi/v233-android-linkerconfig-source-live/files/linkerconfig__ld.config.txt \
  --transfer-timeout 120

python3 scripts/revalidation/tcpctl_host.py \
  --device-binary /cache/bin/a90_real_apex.libraries.config.txt \
  --toybox /cache/bin/toybox \
  install \
  --local-binary tmp/wifi/v233-android-linkerconfig-source-live/files/linkerconfig__apex.libraries.config.txt \
  --transfer-timeout 120

python3 scripts/revalidation/wifi_linker_crash_capture_probe.py \
  --out-dir tmp/wifi/v236-linker-crash-capture-live \
  --linkerconfig-mode copy-real \
  --linkerconfig-source /cache/bin/a90_real_ld.config.txt \
  --apex-libraries-source /cache/bin/a90_real_apex.libraries.config.txt \
  --linker-profiles system-linker,apex-linker \
  --target-profiles system-toybox,apex-linker64-self,cnss-daemon \
  --env-modes clean \
  probe
```

Cleanup:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 20 run /cache/bin/toybox rm -f \
  /cache/bin/a90_real_ld.config.txt \
  /cache/bin/a90_real_apex.libraries.config.txt
```

## Acceptance

- Live matrix produces `android-linker-crash-context-captured`, or documents why capture was blocked.
- Each selected crash case includes `capture.exec_captured=1`, `capture.crash_captured=1`, `capture.crash.siginfo.signo=11`, and nonzero `capture.crash.regset.nt_prstatus.bytes`.
- Temporary real linkerconfig inputs are removed after probing.
- Final native `selftest verbose` remains `fail=0`.
- If crash context points to a process-context mismatch, v237 should compare Android-vs-native process context rather than attempting Wi-Fi daemon start.
