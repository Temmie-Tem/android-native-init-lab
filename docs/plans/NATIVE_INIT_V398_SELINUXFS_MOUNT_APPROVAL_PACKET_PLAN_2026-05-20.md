# Native Init v398 SELinuxfs Mount Approval Packet Plan

## Goal

Prepare the next live SELinux runtime-surface repair without performing it yet.

V397 proved the `servicemanager` blocker is no active `selinuxfs` mount/status page at `/sys/fs/selinux`. V398 must convert that finding into a guarded, reviewable approval packet and fail-closed live executor for a future V399 mount smoke.

V398 itself is non-mutating. It must not mount `selinuxfs`, unmount anything, deploy helpers, start Android daemons, start Wi-Fi HAL, scan, connect, write SELinux policy, or change SELinux enforcement.

## Starting Evidence

- V397 plan: `docs/plans/NATIVE_INIT_V397_SELINUX_SURFACE_PROOF_PLAN_2026-05-20.md`
- V397 report: `docs/reports/NATIVE_INIT_V397_SELINUX_SURFACE_PROOF_2026-05-20.md`
- V397 final evidence: `tmp/wifi/v397-selinux-surface-final-20260520-075153/`

V397 result:

```text
decision: service-manager-selinux-status-native-missing
proc_filesystems_selinuxfs=True
proc_mounts_sysfs_selinux=False
/sys/fs/selinux/status: absent
/sys/fs/selinux/enforce: absent
```

## External Source Notes

Android init mounts `selinuxfs` at `/sys/fs/selinux` during early init. AOSP `servicemanager` then expects libselinux status APIs to discover that mount and open `/status`.

References:

- https://android.googlesource.com/platform/system/core/+/74bf81443fef2ff48bb80cc24b678aff8bdd462a/init/init.cpp
- https://android.googlesource.com/platform/frameworks/native/+/4257ea6038/cmds/servicemanager/Access.cpp
- https://android.googlesource.com/platform/external/selinux/+/refs/heads/main/libselinux/src/sestatus.c

## Implementation

Add two host tools:

- `scripts/revalidation/wifi_selinuxfs_mount_live_executor.py`
  - fail-closed V399 executor.
  - `plan` produces the exact future steps without device commands.
  - `run` refuses before device commands unless exact approval phrase plus `--apply --assume-yes` are supplied.
  - `cleanup` refuses before device commands unless exact approval phrase plus `--apply --assume-yes` are supplied.
  - approved `run` is limited to `version`, `status`, `mount selinuxfs /sys/fs/selinux selinuxfs`, and post-mount read-only status checks.
  - approved `cleanup` is limited to `umount /sys/fs/selinux` and post-cleanup read-only status checks.

- `scripts/revalidation/wifi_selinuxfs_mount_approval_packet.py`
  - runs a fresh V397 read-only proof.
  - runs the V399 executor plan mode.
  - runs V399 no-approval refusal checks for both `run` and `cleanup`.
  - emits approval and cleanup commands as artifacts.
  - emits a rollback checklist.

Future V399 approval phrase:

```text
approve v399 mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up
```

## Validation Plan

Static validation:

```text
python3 -m py_compile \
  scripts/revalidation/wifi_selinuxfs_mount_live_executor.py \
  scripts/revalidation/wifi_selinuxfs_mount_approval_packet.py
```

Executor fail-closed validation:

```text
python3 scripts/revalidation/wifi_selinuxfs_mount_live_executor.py \
  --out-dir tmp/wifi/v398-v399-executor-plan \
  plan

python3 scripts/revalidation/wifi_selinuxfs_mount_live_executor.py \
  --out-dir tmp/wifi/v398-v399-executor-noapproval-run \
  run

python3 scripts/revalidation/wifi_selinuxfs_mount_live_executor.py \
  --out-dir tmp/wifi/v398-v399-executor-noapproval-cleanup \
  cleanup
```

Expected:

```text
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Live read-only packet validation:

```text
python3 scripts/revalidation/wifi_selinuxfs_mount_approval_packet.py \
  --out-dir tmp/wifi/v398-selinuxfs-mount-approval-packet-$(date +%Y%m%d-%H%M%S) \
  run
```

Expected:

```text
decision: selinuxfs-mount-approval-packet-ready
pass: True
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next Step

If V398 passes, V399 can run the approved SELinuxfs mount smoke. V399 still must not start `servicemanager` or Wi-Fi. The service-manager clean-start attempt remains a later separate approval after V399 proves `/sys/fs/selinux/status` exists.
