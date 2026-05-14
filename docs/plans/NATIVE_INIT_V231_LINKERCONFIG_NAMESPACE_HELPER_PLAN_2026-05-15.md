# v231 Plan: Linkerconfig Decision + Private Android Namespace Helper

## Summary

v231 follows v230 `android-exec-namespace-runtime-gap`. The goal is to close the
remaining `linkerconfig-need-unproven` blocker without starting Wi-Fi and without
running `cnss-daemon`.

v231 should add a private namespace helper and use Android linker `--list` mode
as the first executable dry-run. This verifies dependency resolution while
avoiding daemon entrypoint execution.

Current v230 evidence:

- fresh v229 preflight still returns `start-only-runtime-gap`.
- `/mnt/system/system/vendor` is a symlink to `/vendor`.
- vendor source is `needs-remount`: `sda29` is visible but not live-mounted into
  Android runtime paths.
- APEX runtime is available.
- remaining blocker is `linkerconfig-need-unproven`.

## Reference Notes

- Android linker namespaces isolate and link exported libraries between
  namespaces. Vendor process behavior can depend on namespace configuration, so
  v231 must not assume `/linkerconfig` absence is harmless.
- Android `linkerconfig` generates linker configuration from runtime state and
  APEX/library metadata. If `/linkerconfig` is absent in native init, v231 must
  either prove the target daemon links without it or record a narrower blocker.
- Android bionic linker supports direct invocation with `--list`, which behaves
  like `ldd` and exits before transferring control to the target executable.
  This is the preferred v231 dry-run because it loads/links dependencies without
  running `cnss-daemon` business logic.
- Linux mount namespaces are created with `unshare(CLONE_NEWNS)`. To prevent
  mount propagation back to PID1/global namespace, the helper must make the new
  namespace private or slave before mounting.

Reference URLs:

- https://source.android.google.cn/docs/core/architecture/vndk/linker-namespace?hl=en
- https://android.googlesource.com/platform/system/linkerconfig/
- https://android.googlesource.com/platform/bionic/+/refs/heads/main/linker/linker_main.cpp
- https://man7.org/linux/man-pages/man7/mount_namespaces.7.html

## Goal

Answer this question:

> Can native init create a private Android-like execution namespace where
> `/system/bin/linker64 --list /vendor/bin/cnss-daemon` resolves the daemon's
> dynamic dependencies, without executing the daemon and without global mounts?

Expected v231 decision labels:

- `android-linker-list-pass`: private namespace exists and `linker64 --list`
  resolves `cnss-daemon`.
- `android-linker-list-runtime-gap`: private namespace exists, but `--list`
  reports a missing library/path/linkerconfig/APEX component.
- `android-linkerconfig-documented-absent`: `/linkerconfig` is absent, but
  `linker64 --list` proves the daemon can still resolve dependencies through
  fallback/default namespace behavior.
- `android-linkerconfig-required`: `--list` or stderr proves
  `/linkerconfig`/namespace config is required before daemon start.
- `android-namespace-helper-blocked`: helper build/deploy/preflight/safety guard
  fails before private namespace work.
- `android-namespace-manual-review-required`: v230/v229 assumptions changed or
  postflight state drift is observed.

## Non-Goals

v231 must not perform:

- direct `cnss-daemon` execution;
- `cnss_diag` execution;
- Wi-Fi interface link-up, scan, connect, credential access, DHCP, routing, NAT,
  or DNS changes;
- ICNSS unbind/bind, `driver_override`, debugfs/sysfs recovery writes;
- global `/system`, `/vendor`, `/apex`, or `/linkerconfig` bind mounts;
- persistent writes under `/system`, `/vendor`, `/data`, `/efs`, firmware paths.

## Proposed Implementation

Add device-side static helper:

```text
stage3/linux_init/helpers/a90_android_execns_probe.c
```

Add build script:

```text
scripts/revalidation/build_android_execns_probe_helper.sh
```

Extend host tool:

```text
scripts/revalidation/wifi_android_exec_namespace_probe.py
```

The helper is a probe tool, not a service. It should exit after one run and leave
no live child process.

## Helper Contract

Recommended helper command:

```text
/cache/bin/a90_android_execns_probe \
  --system-root /mnt/system/system \
  --vendor-block /dev/block/sda29 \
  --vendor-fstype ext4 \
  --target /vendor/bin/cnss-daemon \
  --linker /system/bin/linker64 \
  --mode linker-list \
  --timeout-sec 10
```

Required helper behavior:

1. Validate all arguments against exact allowlists from the host wrapper.
2. Create a private mount namespace with `unshare(CLONE_NEWNS)`.
3. Immediately call `mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL)` or
   equivalent private/slave propagation.
4. Create a temp root under `/tmp/a90-v231-<pid>/root`.
5. Bind `/mnt/system/system` read-only to `<root>/system`.
6. Mount `sda29` read-only with `noload` to `<root>/vendor`.
7. Preserve `/system/vendor -> /vendor` by relying on the symlink already present
   in the mounted system tree.
8. Bind or mount minimal `/proc` for bionic linker path/proc introspection.
9. Bind `/sys` and `/dev` only if dry-run requires them; default should avoid
   broad writable device exposure.
10. Bind `/mnt/system/system/apex` to `<root>/apex` if present.
11. Do not synthesize `/linkerconfig` unless a later explicit plan proves a safe
    generated config is required and reviewed.
12. `chroot(<root>)`, then execute only:

```text
/system/bin/linker64 --list /vendor/bin/cnss-daemon
```

13. Capture stdout/stderr, exit code, duration, and missing-library messages.
14. Kill the child on timeout.
15. Exit and let the private namespace tear down automatically.
16. Post-run, host wrapper verifies no global `/tmp/a90-v231-*` mount remains.

## Host Tool Changes

Extend `wifi_android_exec_namespace_probe.py`:

- `probe` should check `/cache/bin/a90_android_execns_probe` first.
- If helper is absent, return a safe blocker with deploy/build instructions.
- If helper is present, require:

```text
--allow-temp-namespace
--assume-yes
--allow-linker-list
```

- Before helper execution:
  - rerun v230-style inventory;
  - require fresh v229 `start-only-runtime-gap`;
  - require `/mnt/system/system/vendor -> /vendor`;
  - require vendor source `needs-remount` or `live-mounted`;
  - require APEX runtime available or documented absence.
- After helper execution:
  - rerun `version`, `netservice status`, `selftest verbose`;
  - compare `/proc/mounts`, `/proc/net/dev`, ICNSS uevent, rfkill, and Wi-Fi
    interface inventory against preflight;
  - write `linker-list.txt`, `helper-result.json`, and `postflight.json`.

## Linkerconfig Decision Rule

`/linkerconfig` is considered closed only if one of these is true:

1. `/linkerconfig/ld.config.txt` or equivalent generated config is visible inside
   the private namespace and `linker64 --list` passes; or
2. `/linkerconfig` is absent, but `linker64 --list /vendor/bin/cnss-daemon`
   passes and the report records `android-linkerconfig-documented-absent`.

If `--list` fails with namespace/config/permitted-path/library resolution
errors, v231 must return `android-linkerconfig-required` or
`android-linker-list-runtime-gap`. It must not continue to daemon start.

## Safety Guard

The host wrapper and helper must both enforce:

- no daemon direct exec path except as the argument to `linker64 --list`;
- no `cnss_diag`;
- no shell command string execution;
- no global bind mount;
- no network interface activation;
- no persistent Android partition writes;
- timeout and child process cleanup;
- private evidence output with no-follow file handling.

## Test Plan

Static build:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh
file stage3/linux_init/helpers/a90_android_execns_probe
aarch64-linux-gnu-readelf -l stage3/linux_init/helpers/a90_android_execns_probe
```

Static host checks:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_android_exec_namespace_probe.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Device preflight:

```bash
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py \
  --out-dir tmp/wifi/v231-android-linker-list-preflight \
  inventory
```

Helper deploy check:

```bash
python3 scripts/revalidation/helper_deploy.py push \
  stage3/linux_init/helpers/a90_android_execns_probe \
  a90_android_execns_probe \
  --role android-exec-namespace-probe
```

Opt-in linker-list probe:

```bash
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py \
  --out-dir tmp/wifi/v231-android-linker-list-probe \
  probe \
  --allow-temp-namespace \
  --allow-linker-list \
  --assume-yes
```

Postflight:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py netservice status
python3 scripts/revalidation/a90ctl.py selftest verbose
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py \
  --out-dir tmp/wifi/v231-android-linker-list-postflight \
  inventory
```

## Acceptance

v231 is accepted if:

- private namespace helper builds as a static ARM64 binary;
- helper refuses unsafe arguments;
- helper performs only private namespace work;
- `linker64 --list` result is captured without daemon entrypoint execution;
- `/linkerconfig` status is converted from `unknown` to either documented absent,
  required, or a concrete runtime gap;
- postflight shows no global mount/network/ICNSS drift;
- v229/v230 guardrails remain intact.

## Next Work After v231

If v231 returns `android-linker-list-pass` or
`android-linkerconfig-documented-absent`, v232 can consider a bounded
`cnss-daemon` start-only attempt inside the same private namespace. If v231
returns a runtime gap, v232 must close that exact dependency/config gap first.
