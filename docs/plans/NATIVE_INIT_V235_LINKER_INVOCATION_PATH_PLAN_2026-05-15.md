# v235 Plan: Linker Invocation Path Comparison

## Summary

- v235 is a host/helper investigation step, not a native-init PID1 boot image update.
- Baseline remains `A90 Linux init 0.9.59 (v159)` unless a later boot image is explicitly flashed.
- Goal: compare `/system/bin/linker64` symlink invocation with direct `/apex/com.android.runtime/bin/linker64` invocation inside the same private namespace.
- This is the lowest-risk follow-up to v234 because it still runs only `linker64 --list` and does not execute Wi-Fi daemons.

## Current Evidence

- v231/v232/v233 all reached `linker64 --list /vendor/bin/cnss-daemon` and crashed with child `SIGSEGV(11)`, empty stdout/stderr.
- v234 expanded the target matrix to `system-toybox`, `system-sh`, `linker64-self`, and `cnss-daemon`; all clean and `ld-debug-1` cases crashed with `SIGSEGV(11)`.
- v234 decision was `android-linker-crash-generic`, so the next question is whether the crash depends on using `/system/bin/linker64` as a symlink to the APEX runtime linker.

## Key Changes

- Extend `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper v4.
- Keep the helper static, opt-in, allowlisted, and private-namespace only.
- Add direct APEX linker support:
  - `system-linker`: `/system/bin/linker64`
  - `apex-linker`: `/apex/com.android.runtime/bin/linker64`
- Add target profile:
  - `apex-linker64-self`: `/apex/com.android.runtime/bin/linker64`
- Add host wrapper:
  - `scripts/revalidation/wifi_linker_invocation_path_probe.py`
  - compares linker profiles across target profiles and env modes
  - writes private evidence under `tmp/wifi/v235-linker-invocation-path*`

## Decision Labels

- `android-linker-apex-direct-pass`: direct APEX linker path passes while `/system/bin/linker64` crashes.
- `android-linker-system-symlink-pass`: `/system/bin/linker64` passes while direct APEX linker crashes.
- `android-linker-crash-path-independent`: both linker invocation paths crash.
- `android-linker-list-baseline-pass`: at least one clean linker invocation path exits 0.
- `android-linker-debug-output-ready`: debug/env mode produced meaningful output.
- `android-linker-crash-context-blocked`: bridge/helper/input prerequisite is missing.
- `android-linker-path-manual-review-required`: matrix completed but does not match a stronger label.

## Guardrails

- No daemon entrypoint execution.
- No `cnss_diag`, Wi-Fi scan, Wi-Fi connect, credentials, DHCP, routing, public listener, or RF state mutation.
- No global bind mounts; helper uses private mount namespace only.
- No persistent Android partition writes.
- Temporary real linkerconfig copies under `/cache/bin/a90_real_*` must be removed after live probing.

## Test Plan

Static validation:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh
python3 -m py_compile scripts/revalidation/wifi_linker_invocation_path_probe.py
python3 scripts/revalidation/wifi_linker_invocation_path_probe.py --out-dir tmp/wifi/v235-plan-smoke plan
git diff --check
```

Live validation when ACM bridge and NCM/tcpctl are both available:

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

python3 scripts/revalidation/wifi_linker_invocation_path_probe.py \
  --out-dir tmp/wifi/v235-linker-invocation-path-live \
  --linkerconfig-mode copy-real \
  --linkerconfig-source /cache/bin/a90_real_ld.config.txt \
  --apex-libraries-source /cache/bin/a90_real_apex.libraries.config.txt \
  --linker-profiles system-linker,apex-linker \
  --target-profiles system-toybox,system-sh,linker64-self,apex-linker64-self,cnss-daemon \
  --env-modes clean,ld-debug-1 \
  probe
```

Cleanup:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 20 run /cache/bin/toybox rm -f \
  /cache/bin/a90_real_ld.config.txt \
  /cache/bin/a90_real_apex.libraries.config.txt
```

## Current Blocker

At implementation time, static validation passed but live validation could not proceed because the active bridge reported `serial device is not connected`, `/dev/ttyACM*` was absent, and tcpctl was not reachable on either `192.168.7.2:2325` or the transient `192.168.0.1:2325` interface.  Reopen native ACM/NCM control before running the live matrix.

## Acceptance

- If direct APEX linker passes, v236 should focus on `/system/bin/linker64` symlink/execfn/process context.
- If both linker paths crash, v236 should move to bounded crash context capture or Android process-context comparison.
- If debug mode emits diagnostics, prefer that evidence over daemon start attempts.
- If live validation remains blocked, do not proceed to Wi-Fi daemon start.
