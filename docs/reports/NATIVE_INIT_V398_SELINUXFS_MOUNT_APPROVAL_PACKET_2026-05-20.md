# Native Init v398 SELinuxfs Mount Approval Packet

## Summary

V398 prepares the next SELinux runtime-surface repair without performing it. It adds a fail-closed V399 live executor and a non-mutating approval packet that proves the current V397 blocker is still present, verifies executor refusals before any device command, and emits exact future run/cleanup commands.

This was not a SELinuxfs mount. It did not deploy helpers, start Android daemons, start Wi-Fi HAL, scan, connect, write SELinux policy, change enforcement, or mutate Android partitions.

## Added Tooling

- V399 executor: `scripts/revalidation/wifi_selinuxfs_mount_live_executor.py`
- V398 packet: `scripts/revalidation/wifi_selinuxfs_mount_approval_packet.py`
- plan: `docs/plans/NATIVE_INIT_V398_SELINUXFS_MOUNT_APPROVAL_PACKET_PLAN_2026-05-20.md`

The V399 executor is fail-closed:

- `plan` executes no device command.
- `run` refuses before device commands unless the exact V399 approval phrase, `--apply`, and `--assume-yes` are supplied.
- `cleanup` refuses before device commands unless the exact V399 approval phrase, `--apply`, and `--assume-yes` are supplied.
- approved `run` is limited to `mount selinuxfs /sys/fs/selinux selinuxfs` plus read-only verification.
- approved `cleanup` is limited to `umount /sys/fs/selinux` plus read-only verification.

## Source Correlation

AOSP Android init mounts `selinuxfs` at `/sys/fs/selinux` during early init. AOSP `servicemanager` fatal-checks `selinux_status_open(true)` in `Access::Access()`, and `libselinux` opens the discovered SELinux mount plus `/status`.

References:

- https://android.googlesource.com/platform/system/core/+/74bf81443fef2ff48bb80cc24b678aff8bdd462a/init/init.cpp
- https://android.googlesource.com/platform/frameworks/native/+/4257ea6038/cmds/servicemanager/Access.cpp
- https://android.googlesource.com/platform/external/selinux/+/refs/heads/main/libselinux/src/sestatus.c

## Evidence

Primary evidence:

- V398 packet: `tmp/wifi/v398-selinuxfs-mount-approval-packet-final-20260520-080150/`
- packet manifest: `tmp/wifi/v398-selinuxfs-mount-approval-packet-final-20260520-080150/manifest.json`
- packet summary: `tmp/wifi/v398-selinuxfs-mount-approval-packet-final-20260520-080150/summary.md`
- approval command: `tmp/wifi/v398-selinuxfs-mount-approval-packet-final-20260520-080150/approval-command.sh`
- cleanup command: `tmp/wifi/v398-selinuxfs-mount-approval-packet-final-20260520-080150/cleanup-command.sh`
- rollback checklist: `tmp/wifi/v398-selinuxfs-mount-approval-packet-final-20260520-080150/rollback-checklist.md`

Packet result:

```text
decision: selinuxfs-mount-approval-packet-ready
pass: True
reason: V399 selinuxfs mount smoke is ready for exact approval
live_execution_approved: False
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Checks:

| check | status | detail |
| --- | --- | --- |
| `v397-proof-current` | `pass` | `service-manager-selinux-status-native-missing` |
| `kernel-supports-selinuxfs` | `pass` | `proc_filesystems_selinuxfs=True proc_mounts_sysfs_selinux=False` |
| `status-page-currently-missing` | `pass` | `/sys/fs/selinux/status` and `/sys/fs/selinux/enforce` absent |
| `executor-plan` | `pass` | V399 plan mode ready |
| `executor-run-refusal` | `pass` | no approval -> no device commands |
| `executor-cleanup-refusal` | `pass` | no approval -> no device commands |
| `refusals-before-device-commands` | `pass` | no mutation in refusal paths |
| `approval-command-contract` | `pass` | exact approval phrase and mutation flags present |
| `cleanup-command-contract` | `pass` | exact cleanup phrase and mutation flags present |

## Approval Boundary

V399 approval phrase:

```text
approve v399 mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up
```

Approved run command:

```bash
python3 scripts/revalidation/wifi_selinuxfs_mount_live_executor.py --out-dir tmp/wifi/v399-selinuxfs-mount-live-executor --approval-phrase 'approve v399 mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up' --apply --assume-yes run
```

Approved cleanup command:

```bash
python3 scripts/revalidation/wifi_selinuxfs_mount_live_executor.py --out-dir tmp/wifi/v399-selinuxfs-mount-cleanup-approved --approval-phrase 'approve v399 mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up' --apply --assume-yes cleanup
```

V399 approved run scope:

- allowed mutation: `mount selinuxfs /sys/fs/selinux selinuxfs`
- allowed read-only checks: `stat /sys/fs/selinux/status`, `cat /sys/fs/selinux/enforce`, `xxd -l 64 /sys/fs/selinux/status`
- not allowed: service-manager start, Wi-Fi HAL start, scan/connect, policy write, enforcement change

## Validation

Static validation:

```text
python3 -m py_compile \
  scripts/revalidation/wifi_selinuxfs_mount_live_executor.py \
  scripts/revalidation/wifi_selinuxfs_mount_approval_packet.py
```

Fail-closed executor validation:

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

All three returned PASS with:

```text
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Live read-only packet:

```text
python3 scripts/revalidation/wifi_selinuxfs_mount_approval_packet.py \
  --out-dir tmp/wifi/v398-selinuxfs-mount-approval-packet-final-20260520-080150 \
  run
```

Result: PASS as approval packet, with fresh V397 read-only proof and no mutation.

`git diff --check`: PASS.

## Next Target

Proceed to V399 only after exact approval. V399 should mount `selinuxfs`, verify that `/sys/fs/selinux/status` exists, and stop. No `servicemanager` or Wi-Fi component should be started in V399.

If V399 passes, the next separate target is a service-manager SELinux-surface reproof and then a new bounded `servicemanager` start-only packet. Wi-Fi HAL/start/scan/connect remains blocked until service-manager is clean or strongly classified as non-blocking.
