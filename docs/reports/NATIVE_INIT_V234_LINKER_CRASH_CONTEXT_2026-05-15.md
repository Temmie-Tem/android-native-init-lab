# Native Init v234 Linker Crash Context Comparison

## Summary

- Goal: decide whether the `linker64 --list` crash is specific to
  `/vendor/bin/cnss-daemon` or generic to Android linker invocation inside the
  current private native-init namespace.
- Result: PASS / `android-linker-crash-generic`.
- Device baseline: `A90 Linux init 0.9.59 (v159)`.
- No Wi-Fi daemon entrypoint, `cnss_diag`, scan, connect, credential, DHCP,
  routing, global bind mount, or persistent Android partition write was used.

## Implementation

Updated helper:

- source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper version: `a90_android_execns_probe v3`
- local SHA256: `f7ab13868960fdff70b70508ed504db9934bd245ad16206c3f36f034ebf51afe`
- deployed path: `/cache/bin/a90_android_execns_probe`

Added host wrapper:

- `scripts/revalidation/wifi_linker_crash_context_probe.py`
- output: `tmp/wifi/v234-linker-crash-context-live`

v3 helper changes:

- allowlisted target profiles:
  - `system-toybox` -> `/system/bin/toybox`
  - `system-sh` -> `/system/bin/sh`
  - `linker64-self` -> `/system/bin/linker64`
  - `cnss-daemon` -> `/vendor/bin/cnss-daemon`
- env modes:
  - `clean`
  - `ld-debug-1`
  - `ld-debug-2` and `auxv` supported for follow-up use
- pre-exec context output:
  - linker/target path, symlink, access, size, hash
  - `/linkerconfig/ld.config.txt`
  - `/linkerconfig/apex.libraries.config.txt`
  - `/apex/com.android.runtime`
  - `/system/lib64`, `/vendor/lib64`, `/proc/self/exe`

## Inputs

Real Android generated linkerconfig captured during v233:

| device source | temporary native path | SHA256 |
| --- | --- | --- |
| `/linkerconfig/ld.config.txt` | `/cache/bin/a90_real_ld.config.txt` | `1ab340f0ee1e5f6d7c43e372dfe3bc9164d34b348dd9c716ded1b4e56e079f1a` |
| `/linkerconfig/apex.libraries.config.txt` | `/cache/bin/a90_real_apex.libraries.config.txt` | `5419adf6ed8f74c480d79096681a19a8570470ab8359c6e8c0be110da434f16e` |

Both temporary files were removed after the probe and verified absent.

## Commands

Deploy v3 helper over NCM:

```bash
python3 scripts/revalidation/tcpctl_host.py \
  --device-binary /cache/bin/a90_android_execns_probe \
  --toybox /cache/bin/toybox \
  install \
  --local-binary stage3/linux_init/helpers/a90_android_execns_probe \
  --transfer-timeout 120
```

Deploy captured linkerconfig inputs:

```bash
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
```

Run matrix:

```bash
python3 scripts/revalidation/wifi_linker_crash_context_probe.py \
  --out-dir tmp/wifi/v234-linker-crash-context-live \
  --linkerconfig-mode copy-real \
  --linkerconfig-source /cache/bin/a90_real_ld.config.txt \
  --apex-libraries-source /cache/bin/a90_real_apex.libraries.config.txt \
  --target-profiles system-toybox,system-sh,linker64-self,cnss-daemon \
  --env-modes clean,ld-debug-1 \
  probe
```

Cleanup:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 20 run /cache/bin/toybox rm -f \
  /cache/bin/a90_real_ld.config.txt \
  /cache/bin/a90_real_apex.libraries.config.txt
```

## Matrix Result

| env | target profile | result | signal | exit | stdout | stderr |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `clean` | `system-toybox` | crashed | 11 | -1 | 0 | 0 |
| `clean` | `system-sh` | crashed | 11 | -1 | 0 | 0 |
| `clean` | `linker64-self` | crashed | 11 | -1 | 0 | 0 |
| `clean` | `cnss-daemon` | crashed | 11 | -1 | 0 | 0 |
| `ld-debug-1` | `system-toybox` | crashed | 11 | -1 | 0 | 0 |
| `ld-debug-1` | `system-sh` | crashed | 11 | -1 | 0 | 0 |
| `ld-debug-1` | `linker64-self` | crashed | 11 | -1 | 0 | 0 |
| `ld-debug-1` | `cnss-daemon` | crashed | 11 | -1 | 0 | 0 |

Decision:

```text
android-linker-crash-generic
```

Reason:

```text
all clean target profiles crashed signals=[11]
```

## Context Evidence

Representative `system-toybox` and `cnss-daemon` clean runs both showed:

- helper status: `namespace-ready`
- linker: `/system/bin/linker64 -> /apex/com.android.runtime/bin/linker64`
- `/linkerconfig/ld.config.txt`: present, size `134256`, readable
- `/linkerconfig/apex.libraries.config.txt`: present, size `366`, readable
- `/apex/com.android.runtime`: present
- `/system/lib64`: present
- `/vendor/lib64`: present
- `/proc/self/exe`: points to `/cache/bin/a90_android_execns_probe`
- child result: `SIGSEGV(11)`, stdout/stderr empty

This rules out a `cnss-daemon`-only failure at the current evidence level.  The
same crash happens before useful diagnostics for simple system targets.

## Postflight

- wrapper postflight `selftest verbose`: PASS from host perspective.
- wrapper postflight `/proc/mounts`: PASS from host perspective.
- manual cleanup verified both temporary real linkerconfig files absent.
- final `selftest verbose`: `pass=11 warn=1 fail=0`.

## Interpretation

v234 shifts the blocker from Wi-Fi daemon dependency resolution to generic
Android linker execution context.  The next step should not be controlled CNSS
start.  The next defensible direction is one of:

1. compare direct `/apex/com.android.runtime/bin/linker64 --list` invocation
   versus `/system/bin/linker64` symlink invocation inside the same namespace;
2. capture a bounded crash context with a ptrace/register/maps helper;
3. compare Android boot process context values that may matter to bionic linker
   startup, especially auxv, executable path, and procfs assumptions.

Wi-Fi scan/connect/link-up remains blocked until the Android linker invocation
crash is understood or a safer daemon execution path is found.
