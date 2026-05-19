# Native Init v397 SELinux Surface Proof

## Summary

V397 adds a read-only SELinux runtime-surface proof tool and runs it against the live device after V396 frame ELF symbolization.

The live result identifies a concrete blocker for `servicemanager`: the kernel advertises `selinuxfs`, but native init has no active `selinuxfs` mount at `/sys/fs/selinux`, and `/sys/fs/selinux/status` plus `/sys/fs/selinux/enforce` are absent. This directly matches the V396 fatal candidate around `selinux_status_open(true)`.

This was not Wi-Fi bring-up. It did not deploy helpers, start Android daemons, start Wi-Fi HAL, scan, connect, write SELinux policy, or mutate Android partitions.

## Added Tooling

- tool: `scripts/revalidation/wifi_service_manager_selinux_surface_proof.py`
- plan: `docs/plans/NATIVE_INIT_V397_SELINUX_SURFACE_PROOF_PLAN_2026-05-20.md`

The tool performs:

- host-only plan manifest generation.
- read-only native `selinuxfs`/`/proc/mounts`/`/proc/filesystems` inventory.
- read-only `/sys/fs/selinux/*` status/class/perms checks.
- read-only mounted Android `service_contexts` and `hwservice_contexts` discovery.
- V392 private preexec context correlation.
- V396 fatal-string/framechain correlation.

## Source Correlation

AOSP `servicemanager` `Access::Access()` fatal-checks `selinux_status_open(true /*fallback*/)` and `getcon(&mThisProcessContext)`. Its `getSehandle()` path also fatal-checks the service context handle.

AOSP `libselinux` status support discovers the SELinux mount and opens the mount plus `/status`; if no SELinux mount is discovered, `selinux_status_open()` returns an error before the normal status page path can work.

References:

- https://android.googlesource.com/platform/frameworks/native/+/4257ea6038/cmds/servicemanager/Access.cpp
- https://android.googlesource.com/platform/external/selinux/+/refs/heads/main/libselinux/src/sestatus.c
- https://android.googlesource.com/platform/external/selinux/+/refs/heads/main/libselinux/src/init.c

## Evidence

Primary evidence:

- final plan: `tmp/wifi/v397-selinux-surface-final-plan/`
- final live run: `tmp/wifi/v397-selinux-surface-final-20260520-075153/`
- final manifest: `tmp/wifi/v397-selinux-surface-final-20260520-075153/manifest.json`
- final summary: `tmp/wifi/v397-selinux-surface-final-20260520-075153/summary.md`

Live result:

```text
decision: service-manager-selinux-status-native-missing
pass: True
reason: native SELinux status page is absent or unreadable
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Key checks:

| check | status | severity | detail |
| --- | --- | --- | --- |
| `native-selinuxfs-mount` | `incomplete` | `blocker` | `proc_filesystems_selinuxfs=True proc_mounts_sysfs_selinux=False` |
| `native-selinux-status-page` | `missing` | `blocker` | `/sys/fs/selinux/status` and `/sys/fs/selinux/enforce` absent |
| `native-service-manager-class` | `partial` | `warning` | SELinux `service_manager` class/perms paths absent |
| `mounted-service-context-inputs` | `present` | `info` | `service_contexts=2/9`, `hwservice_contexts=2/9` |
| `v392-private-preexec-selinux-evidence` | `status-unproven` | `warning` | private `/sys/fs/selinux/null` was present, `/status` was not proven |
| `v396-fatal-candidate` | `present` | `info` | `selinux_status_open`, `gSehandle`, `getcon`, `Access.cpp` present |

Direct device evidence:

```text
/proc/filesystems contains selinuxfs
/proc/mounts has no selinuxfs mounted at /sys/fs/selinux
stat /sys/fs/selinux/status -> No such file or directory
cat /sys/fs/selinux/enforce -> No such file or directory
```

Mounted context inputs are visible under the Android system tree:

```text
/mnt/system/system/etc/selinux/plat_hwservice_contexts
/mnt/system/system/etc/selinux/plat_service_contexts
/mnt/system/system/system_ext/etc/selinux/system_ext_service_contexts
/mnt/system/system/system_ext/etc/selinux/system_ext_hwservice_contexts
```

## Interpretation

V397 changes the service-manager blocker from a broad runtime-gap hypothesis to a concrete SELinux runtime-surface blocker:

- The kernel supports `selinuxfs`.
- Native init has not mounted `selinuxfs` at `/sys/fs/selinux`.
- Therefore `/sys/fs/selinux/status`, `/sys/fs/selinux/enforce`, and service-manager SELinux class/perms files are absent.
- V396 showed `servicemanager` aborting through a fatal-log path containing `selinux_status_open(true)`.
- V392 private preexec context only proved `/sys/fs/selinux/null`, not a real `selinuxfs` status page.

The next repair candidate is not Wi-Fi-specific. It is a minimal SELinux runtime surface for Android service-manager execution.

## Validation

Static validation:

```text
python3 -m py_compile scripts/revalidation/wifi_service_manager_selinux_surface_proof.py
```

Plan-only validation:

```text
python3 scripts/revalidation/wifi_service_manager_selinux_surface_proof.py \
  --out-dir tmp/wifi/v397-selinux-surface-final-plan \
  plan
```

Plan result:

```text
decision: service-manager-selinux-surface-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Live read-only validation:

```text
python3 scripts/revalidation/wifi_service_manager_selinux_surface_proof.py \
  --out-dir tmp/wifi/v397-selinux-surface-final-20260520-075153 \
  run
```

Live result: PASS as a blocker classification, with no mutation, no daemon start, and no Wi-Fi bring-up.

`git diff --check`: PASS.

## Next Target

Proceed to V398: minimal SELinux runtime surface plan.

V398 should decide whether to:

- mount real `selinuxfs` read-only/standard at native `/sys/fs/selinux` before private namespace creation, then bind it into the service-manager private root; or
- add helper v22 private-context proof first, printing `/sys/fs/selinux`, `/sys/fs/selinux/status`, `/sys/fs/selinux/enforce`, and service-context file visibility inside the private root before any start.

The safer immediate path is helper v22 private-context proof plus explicit mount plan. Wi-Fi HAL/start/scan/connect remains blocked.
