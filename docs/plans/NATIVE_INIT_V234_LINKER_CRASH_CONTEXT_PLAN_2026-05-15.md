# v234 Plan: Linker Crash Context Comparison

## Summary

- v234 is a host/helper investigation step, not a native-init PID1 boot image update.
- Baseline remains `A90 Linux init 0.9.59 (v159)` unless a later boot image is explicitly flashed.
- Goal: decide whether `/system/bin/linker64 --list /vendor/bin/cnss-daemon` crashing with `SIGSEGV(11)` is target-specific or a generic private Android namespace/linker invocation problem.
- v234 must run before any Wi-Fi daemon start, scan, connect, credential, DHCP, routing, or public network exposure work.

## Current Evidence

- v231 private namespace helper mounted vendor privately and supplied no `/linkerconfig`; result was child `SIGSEGV(11)` with empty stdout/stderr.
- v232 supplied a private synthetic `minimal-vendor` `/linkerconfig/ld.config.txt`; result stayed child `SIGSEGV(11)` with empty stdout/stderr.
- v233 captured stock Android generated `/linkerconfig/ld.config.txt` and re-tested `copy-real`; result stayed child `SIGSEGV(11)` with empty stdout/stderr.
- v233 did not leak mounts, restored native v159, and verified selftest `fail=0`.
- Therefore, the next question is not "which linkerconfig file should be copied" but "what exact context makes the linker crash."

## Reference Notes

- Android linker config is namespace-based and controls search/permitted paths for sections mapped from executables: https://android.googlesource.com/platform/bionic/+/main/linker/ld.config.format.md
- Android 11+ generates linker configuration at runtime under `/linkerconfig`, so a captured real `ld.config.txt` is necessary evidence but may not be sufficient context: https://source.android.com/docs/core/architecture/partitions/linker-namespace
- `platform/system/linkerconfig` documents generated APEX/system linker configuration inputs, including APEX library metadata: https://android.googlesource.com/platform/system/linkerconfig/
- Android native crash debugging normally relies on logcat/tombstones via Android services; native init private namespace probes may only have parent `waitpid()` status and captured stdout/stderr: https://source.android.com/devices/tech/debug

## Hypotheses

1. **Target-specific crash**: `cnss-daemon` or one of its vendor dependencies triggers a linker bug or unsupported private namespace condition.
2. **Generic linker-direct crash**: invoking Android `linker64 --list` directly from the native init helper crashes regardless of target.
3. **Incomplete runtime context**: real `ld.config.txt` alone is insufficient because companion `/linkerconfig` files, APEX metadata, properties, or mount layout differ from Android boot.
4. **Process context mismatch**: `/proc`, `/dev`, `AT_EXECFN`, `/proc/self/exe`, mountinfo, chroot path, or symlink resolution differs enough to crash before diagnostics are emitted.
5. **Output blind spot**: linker diagnostics may go to Android logging paths instead of stdout/stderr, so the current probe may miss useful failure text.

## Key Changes

- Extend `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper v3.
- Keep the helper static and opt-in; do not change PID1 native init or boot image.
- Replace the single hard-coded target with a small allowlisted target-profile matrix:
  - `cnss-daemon`: `/vendor/bin/cnss-daemon`
  - `system-toybox`: `/system/bin/toybox`
  - `system-sh`: `/system/bin/sh`
  - `linker64-self`: `/system/bin/linker64`
  - optional later `vendor-light`: a small vendor executable chosen only after read-only inventory
- Keep raw arbitrary target paths disabled by default.
- Add environment/debug modes:
  - `clean`: current minimal environment
  - `ld-debug-1`: set `LD_DEBUG=1`
  - `ld-debug-2`: set `LD_DEBUG=2`
  - optional `auxv`: set `LD_SHOW_AUXV=1` if local linker behavior suggests it is useful
- Emit pre-exec context before launching linker:
  - target/linker path, `stat`, readlink resolution, hash if cheap
  - existence/access for `/linkerconfig/ld.config.txt`, `/linkerconfig/apex.libraries.config.txt`, `/apex/com.android.runtime`, `/system/lib64`, `/vendor/lib64`
  - private root mode, linkerconfig mode, linkerconfig hash, target profile, env mode
  - child-visible mountinfo/proc availability marker where safe
- Keep parent result model explicit:
  - `child_exit`, `child_signal`, stdout length, stderr length, duration
  - no mount leak observed / mount leak detected
  - decision label
- Add a host matrix wrapper:
  - path: `scripts/revalidation/wifi_linker_crash_context_probe.py`
  - input: captured real linkerconfig from v233 evidence
  - deploy: temporary `/cache/bin/a90_real_ld.config.txt`, then remove after run
  - output: private evidence directory under `tmp/wifi/`

## Decision Labels

- `android-linker-list-baseline-pass`: at least one safe baseline target lists dependencies successfully.
- `android-linker-crash-target-specific`: safe baseline target passes but `cnss-daemon` crashes.
- `android-linker-crash-generic`: all safe targets crash in the same way.
- `android-linker-debug-output-ready`: debug/env mode produced meaningful stdout/stderr or context output.
- `android-linker-crash-context-blocked`: helper cannot build/run the matrix safely.
- `android-linker-crash-manual-review-required`: matrix is inconclusive but preserves enough evidence for manual ELF/context review.

## Guardrails

- No daemon entrypoint execution.
- No `cnss_diag`, Wi-Fi scan, Wi-Fi connect, credentials, DHCP, routing, public listener, or RF state mutation.
- No global bind mounts; helper must use private mount namespace only.
- No persistent Android partition writes.
- No ptrace by default. If all non-ptrace comparisons crash, plan v235 around explicit ptrace/register/map capture.
- ACM/NCM rescue control must remain available after every probe run.

## Test Plan

- Static build helper v3 with `aarch64-linux-gnu-gcc -static -Os -Wall -Wextra`.
- Run host Python `py_compile` for the new wrapper.
- Verify helper strings/usage include target profiles and debug modes.
- Run wrapper against native v159 with NCM available:
  - `copy-real + clean + system-toybox`
  - `copy-real + clean + system-sh`
  - `copy-real + clean + linker64-self`
  - `copy-real + clean + cnss-daemon`
  - repeat selected cases with `ld-debug-1` and `ld-debug-2`
- After every run:
  - confirm no mount leak
  - confirm `/cache/bin/a90_real_ld.config.txt` cleanup
  - confirm `a90ctl.py selftest verbose` still reports `fail=0`
  - confirm host NCM ping still works

## Acceptance

- If safe system targets pass and only `cnss-daemon` crashes, v235 should focus on vendor ELF/dependency analysis and `cnss-daemon` target context.
- If all targets crash, v235 should focus on generic Android linker invocation context or a ptrace/debug capture helper.
- If debug mode emits useful diagnostics, use that text to choose the next narrow blocker instead of attempting daemon start.
- If matrix is blocked, document the exact missing prerequisite and do not proceed to Wi-Fi daemon execution.
