# Native Init v231 Linkerconfig Namespace Helper Report

## Summary

- Cycle: `v231`
- Scope: host/device helper path for Android private namespace `linker64 --list` dry-run.
- Device build during validation: `A90 Linux init 0.9.59 (v159)`.
- Result: implementation, local build, NCM deploy, and live helper execution PASS to the intended dry-run boundary.
- Final decision: `android-namespace-manual-review-required`.
- Final reason: Android `linker64 --list` terminated with `SIGSEGV` after private namespace setup succeeded.

## Implemented

- Added `stage3/linux_init/helpers/a90_android_execns_probe.c`.
  - Creates a private mount namespace with `unshare(CLONE_NEWNS)`.
  - Marks mounts private with `MS_REC|MS_PRIVATE`.
  - Creates `/tmp/a90-v231-<pid>/root`.
  - Bind-mounts `/mnt/system/system` as `/system` read-only.
  - Mounts `/dev/block/sda29` as `/vendor` with `ext4 ro,noload`.
  - Mounts `<root>/proc` before `chroot`.
  - Optionally bind-mounts `/mnt/system/system/apex` as `/apex`.
  - Bind-mounts `/mnt/system/linkerconfig` as `/linkerconfig` when present.
  - Creates a temporary block node from `/sys/class/block/sda29/dev` when `/dev/block/sda29` is absent.
  - Executes only `/system/bin/linker64 --list /vendor/bin/cnss-daemon`.
  - Captures stdout/stderr, exit/signal/timeout, then reverse-cleans mounts.
- Added `scripts/revalidation/build_android_execns_probe_helper.sh`.
- Added helper manifest awareness to `scripts/revalidation/helper_deploy.py`.
- Extended `scripts/revalidation/wifi_android_exec_namespace_probe.py`.
  - Adds `--allow-linker-list` and `--helper-timeout-sec`.
  - Requires `--allow-temp-namespace --allow-linker-list --assume-yes` for helper probe.
  - Parses `A90_EXECNS_*` helper output.
  - Classifies results into `android-linker-list-pass`, `android-linkerconfig-documented-absent`, `android-linkerconfig-required`, `android-linker-list-runtime-gap`, `android-namespace-helper-blocked`, or `android-namespace-manual-review-required`.

## Local Validation

- `python3 -m py_compile scripts/revalidation/wifi_android_exec_namespace_probe.py scripts/revalidation/helper_deploy.py` — PASS
- `scripts/revalidation/build_android_execns_probe_helper.sh` — PASS
- `git diff --check` — PASS
- `python3 scripts/revalidation/wifi_android_exec_namespace_probe.py plan --out-dir tmp/wifi/v231-plan-local-check` — PASS

## Artifacts

- `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - SHA256: `e473b7171cb5aa24fc45c93d0ad920c853e3e7fbcd94871949b689f876b66bcb`
- `stage3/linux_init/helpers/a90_android_execns_probe`
  - SHA256: `b200a8608eba661186650a93e380a5e2e0283090774f6cd44519913939316f86`
  - Type: `ELF 64-bit LSB executable, ARM aarch64, statically linked`
  - Dynamic section: none
- `scripts/revalidation/build_android_execns_probe_helper.sh`
  - SHA256: `1521c70968fcf5a04dee69950bb24175e58acb5e374add584ba68967a902c3fb`
- `scripts/revalidation/wifi_android_exec_namespace_probe.py`
  - SHA256: `31d58f62284b3f5958a13fc2282e8c0a890a9cf88019f3337d7c77d4b605d4c6`

## Live Validation

Command:

```bash
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py \
  --out-dir tmp/wifi/v231-android-linker-list-probe-live \
  probe \
  --allow-temp-namespace \
  --allow-linker-list \
  --assume-yes
```

Initial result:

- decision: `android-namespace-helper-blocked`
- pass: `False`
- reason: `device helper is not present at /cache/bin/a90_android_execns_probe`
- evidence dir: `tmp/wifi/v231-android-linker-list-probe-live`

Important supporting facts from the live run:

- Fresh v229 gate: `start-only-runtime-gap`, accepted `True`.
- `/mnt/system/system/vendor -> /vendor`.
- vendor source: `needs-remount`.
- APEX runtime: `available`.
- remaining read-only blocker before helper run: `linkerconfig-need-unproven`.

This was the expected safe blocker for the first v231 implementation pass.

## Helper Deploy

NCM path was used for operator-assisted helper deployment.

- Host NCM ping to `192.168.7.2`: PASS.
- Local helper SHA256: `b200a8608eba661186650a93e380a5e2e0283090774f6cd44519913939316f86`.
- Remote path: `/cache/bin/a90_android_execns_probe`.
- Remote stat: `mode=0755 uid=0 gid=0 size=728992`.
- Remote SHA256: `b200a8608eba661186650a93e380a5e2e0283090774f6cd44519913939316f86`.

The first deployed helper revision reached `setup_error=mount vendor: No such file or directory` because `/dev/block/sda29` was absent even though `/sys/class/block/sda29/dev` was visible. The helper was updated to create a temporary private block node from sysfs major:minor.

## Live Helper Result

Command:

```bash
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py \
  --out-dir tmp/wifi/v231-android-linker-list-probe-live-with-helper-v3 \
  probe \
  --allow-temp-namespace \
  --allow-linker-list \
  --assume-yes
```

Result:

- decision: `android-namespace-manual-review-required`
- pass: `False`
- reason: `linker process terminated by signal 11`
- evidence dir: `tmp/wifi/v231-android-linker-list-probe-live-with-helper-v3`

Helper parsed fields:

- `helper_status=namespace-ready`
- `vendor_mount_source=/tmp/a90-v231-2395/vendor-block-sda29`
- `linkerconfig_mount_source=/mnt/system/linkerconfig`
- `probe_run_rc=0`
- `child_exit_code=-1`
- `child_signal=11`
- `timed_out=0`
- stdout/stderr: empty
- cleanup: attempted

Postflight:

- `version`, `status`, `netservice status`, `selftest verbose`: PASS.
- `/proc/mounts` does not show leaked `/tmp/a90-v231-*` private mounts.
- `selftest verbose`: `fail=0`.

## Linkerconfig Finding

Evidence:

- `/mnt/system/linkerconfig` exists but is empty.
- `/mnt/system/system/etc/ld.config.txt`, `ld.config.arm64.txt`, and `ld.config.vndk_lite.txt` are absent.
- `/mnt/system/system/bin/linker64` is a symlink to `/apex/com.android.runtime/bin/linker64`.
- `strings` on the live linker shows `--list`, `/linkerconfig/ld.config.txt`, `/system/etc/ld.config.arm64.txt`, and namespace/permitted path diagnostics.
- Android bionic upstream documents that `linker64 --list` is intended to provide ldd-like behavior.

References:

- Android bionic `ldd` wrapper calls `linker64 --list` for 64-bit binaries: https://android.googlesource.com/platform/bionic/+/7128923e5/linker/ldd
- Android bionic commit introducing ldd-like `--list`: https://android.googlesource.com/platform/bionic/+/90f96b9f483b8effefd6a6fe8a8f0562f616837e

Interpretation:

- v231 successfully proved private namespace mount setup and safe cleanup.
- v231 did not prove a runnable Android linker namespace because the live system image does not provide linkerconfig content in the mounted native environment.
- The next step should be a private-only linkerconfig materialization probe, not daemon execution.

## Next Step

Do not start `cnss-daemon` yet. Plan v232 around private linkerconfig materialization:

- Generate or source a minimal `ld.config.txt` inside the temporary private root only.
- Keep global mounts and persistent Android partition writes forbidden.
- Re-run only `linker64 --list /vendor/bin/cnss-daemon`.
- Accept only `android-linker-list-pass`, `android-linkerconfig-required`, or `android-linker-list-runtime-gap` as narrowed results.
