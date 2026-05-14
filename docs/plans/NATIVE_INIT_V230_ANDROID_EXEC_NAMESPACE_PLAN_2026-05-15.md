# v230 Plan: Temporary Android Execution Namespace Probe

## Summary

v230 follows v229 `start-only-runtime-gap`. The goal is not to start Wi-Fi and
not to start `cnss-daemon` yet. The goal is to prove that native init can build a
safe, temporary Android-like execution namespace where Android dynamic binaries
can see their expected absolute paths.

v229 preflight result:

```text
decision=start-only-runtime-gap
live_daemon_start=False
required_failures=['stat-mnt-system-vendor-bin-cnss-daemon']
runandroid_required_missing=['stat-system-bin-toybox', 'stat-system-vendor-bin-cnss-daemon', 'stat-system-bin-linker64']
```

Observed state:

- `/mnt/system/system/bin/linker64` exists.
- `/mnt/system/system/bin/toybox` exists.
- `/mnt/system/vendor/bin/cnss-daemon` does not exist.
- `/system/bin/linker64`, `/system/bin/toybox`, and
  `/system/vendor/bin/cnss-daemon` are not visible in the current native
  execution namespace.

v230 must therefore bridge two things safely:

1. Android `/system` absolute paths from the read-only mounted system image.
2. Android `/vendor` and `/system/vendor` absolute paths from the read-only
   vendor source captured in v222/v226.

## Reference Notes

- Android Treble separates generic OS framework content and hardware-specific
  vendor content into separate partitions. This matches our observed split where
  `/mnt/system/system` exists but `cnss-daemon` is not under `/mnt/system/vendor`.
  Reference: Android shared system image / partitions documentation.
- Android dynamic linker namespace behavior depends on linker configuration and
  vendor/system library search paths. Vendor processes normally search under
  `/vendor/${LIB}` and related VNDK paths, so the v230 namespace must preserve
  Android-like `/system`, `/vendor`, `/system_ext`, `/product`, `/odm`, `/apex`,
  and `/linkerconfig` visibility where present.
- Android init service metadata normally lives under the partition-local
  `etc/init` directories and Android init supports service options such as
  `setenv` and mount namespaces. We are not reimplementing Android init, but the
  namespace probe should model only the minimal execution surface needed for the
  existing `cnss-daemon` service metadata.
- Linux mount namespaces and bind mounts allow a process to see a private mount
  tree. v230 should prefer child/private mount namespace probing over global
  rootfs mutation whenever feasible.

Reference URLs:

- https://source.android.com/docs/core/architecture/partitions/shared-system-image
- https://source.android.google.cn/docs/core/architecture/vndk/linker-namespace
- https://android.googlesource.com/platform/system/core/+/android16-release/init/README.md
- https://docs.kernel.org/filesystems/sharedsubtree.html

## Goal

Produce a reviewed v230 tool/plan that can answer:

> Can native init materialize a temporary Android execution namespace where the
> exact v229 daemon command would have all required paths available, without
> starting the daemon and without persistent mutation?

Expected v230 decision labels:

- `android-exec-namespace-ready`: all required absolute paths are visible inside
  a private/temporary namespace; no daemon execution performed.
- `android-exec-namespace-runtime-gap`: namespace materialization was attempted
  safely, but required path/linkerconfig/APEX/vendor/system component is still
  missing.
- `android-exec-namespace-blocked`: prerequisite manifests or safety guards fail
  before any namespace work.
- `manual-review-required`: unexpected path drift, mount drift, or exposure drift
  requires review.

## Non-Goals

v230 must not perform:

- `cnss-daemon` execution;
- `cnss_diag` execution;
- `wificond`, Wi-Fi HAL, supplicant, hostapd execution;
- `ip link set wlan* up`, `rfkill unblock`, `iw scan`, `iw connect`;
- DHCP, routing, NAT, DNS changes;
- credential path reads/writes;
- persistent writes under `/system`, `/vendor`, `/data`, `/efs`, firmware paths;
- generic ICNSS unbind/bind, `driver_override`, or debugfs/sysfs recovery writes.

## Proposed Implementation

Add host-side planner/prober:

```text
scripts/revalidation/wifi_android_exec_namespace_probe.py
```

Optional helper if shell-only bind mounting is too global/risky:

```text
stage3/linux_init/helpers/a90_android_execns_probe.c
```

The preferred implementation is a device-side helper because it can create a
private child mount namespace with `unshare(CLONE_NEWNS)`, make mount propagation
private, set up temporary bind mounts, verify paths, and exit without touching
the PID1/global namespace. If this helper is not added in v230, the host tool
must stop at dry-run/preflight and not perform global bind mounts.

Recommended host subcommands:

```text
plan       validate v221/v222/v223/v224/v225/v227/v228/v229 evidence only
preflight  read-only live checks; no namespace mount
probe      opt-in temporary namespace probe; no daemon execution
cleanup    remove stale temporary v230 paths if any are found
```

`probe` must require explicit flags:

```text
--allow-temp-namespace
--assume-yes
```

## Namespace Model

Temporary root base:

```text
/tmp/a90-v230-<run-id>/root
```

Required mappings inside the private namespace:

| Android path | Source | Mode | Notes |
| --- | --- | --- | --- |
| `/system` | live `/mnt/system/system` | read-only bind | required for `/system/bin/linker64` and framework libs |
| `/vendor` | v222/v226 live vendor root or ro,noload vendor mount | read-only bind | required for vendor libs and daemon |
| `/system/vendor` | same vendor root | symlink or read-only bind | required because service evidence uses `/system/vendor/bin/cnss-daemon` |
| `/system_ext` | `/mnt/system/system_ext` if present | read-only bind/symlink | preserve Android search layout |
| `/product` | `/mnt/system/product` if present | read-only bind/symlink | preserve Android search layout |
| `/odm` | `/mnt/system/odm` if present | read-only bind/symlink | vendor/ODM search path candidate |
| `/apex` | `/mnt/system/system/apex` or existing APEX source if present | read-only bind/symlink | bionic/runtime namespace candidate |
| `/linkerconfig` | `/mnt/system/linkerconfig` if present | read-only bind/symlink | dynamic linker namespace config candidate |
| `/dev`, `/proc`, `/sys` | existing kernel pseudo filesystems | read-only/minimal bind where needed | probe only; no writes |

v230 should verify both canonical service path candidates:

```text
/system/vendor/bin/cnss-daemon
/vendor/bin/cnss-daemon
```

If only `/vendor/bin/cnss-daemon` exists, the plan must decide whether
`/system/vendor` should be a symlink to `/vendor` or a bind mount to the same
vendor source. This must remain temporary.

## Required Path Checks

Inside the temporary namespace, verify:

```text
/system/bin/linker64
/system/bin/toybox
/system/lib64/libc.so
/vendor/bin/cnss-daemon
/system/vendor/bin/cnss-daemon
/vendor/bin/cnss_diag
/vendor/lib64
/linkerconfig/ld.config.txt or documented absence
/apex/com.android.runtime or documented absence
```

Also verify denied paths/actions were not touched:

```text
/proc/net/dev unchanged except existing USB/NCM state
/sys/class/net no new active wlan* state
/sys/class/rfkill unchanged
/sys/module/firmware_class/parameters/path unchanged
ICNSS uevent/bound state unchanged
```

## Safety Guard

Before `probe`:

- require v229 `start-only-runtime-gap` or `dry-run-ready` manifest;
- require v223 `reboot-recovery-accepted`;
- require v225/v228 exposure boundary still local-only;
- require bridge/cmdv1 `version`, `status`, `bootstatus`, `selftest verbose`;
- require no active Wi-Fi interface is unexpectedly up;
- require no `cnss-daemon` process is already running in native init.

During `probe`:

- use a private mount namespace if helper is available;
- make propagation private/slave before bind mounts;
- use read-only bind/remount where supported;
- never mount over global `/system` or `/vendor` from PID1 namespace;
- no daemon execution;
- no property mutation;
- no ICNSS write/reprobe.

After `probe`:

- unmount private namespace by process exit or explicit cleanup;
- verify no v230 temporary paths remain if global temp directories were used;
- rerun read-only postflight inventory;
- produce private evidence.

## Evidence Output

```text
tmp/wifi/v230-android-exec-namespace-probe/
├── manifest.json
├── namespace-plan.json
├── preflight.json
├── probe-result.json
├── postflight.json
├── commands/
└── summary.md
```

Evidence must use `EvidenceStore` / private no-follow output helpers.

## Test Plan

Static checks:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_android_exec_namespace_probe.py \
  scripts/revalidation/wifi_cnss_start_experiment.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Host-only plan:

```bash
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py plan \
  --out-dir tmp/wifi/v230-android-exec-namespace-probe
```

Live read-only preflight:

```bash
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py preflight \
  --out-dir tmp/wifi/v230-android-exec-namespace-probe-preflight
```

Opt-in namespace probe, no daemon execution:

```bash
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py probe \
  --out-dir tmp/wifi/v230-android-exec-namespace-probe-live \
  --allow-temp-namespace \
  --assume-yes
```

Post-probe regression:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py bootstatus
python3 scripts/revalidation/a90ctl.py 'selftest verbose'
python3 scripts/revalidation/wifi_cnss_start_experiment.py preflight \
  --out-dir tmp/wifi/v229-controlled-cnss-start-experiment-preflight-after-v230
```

## Acceptance

v230 is accepted if:

- default plan/preflight perform no namespace mount and no daemon execution;
- opt-in probe, if executed, uses only temporary/private namespace materialization;
- required Android paths become visible inside the probe namespace or gaps are
  recorded precisely;
- global native namespace remains unchanged after probe;
- v229 preflight improves from missing global system/vendor paths to either
  `dry-run-ready`-equivalent namespace-ready evidence or a narrower runtime gap;
- scan/connect/link-up/credential/routing remain blocked.

## Next Work After v230

If v230 returns `android-exec-namespace-ready`, v231 can update v229 runner to
execute the start-only daemon command inside that temporary namespace. If v230
returns a narrower runtime gap, v231 should close that gap before any daemon
start attempt.
