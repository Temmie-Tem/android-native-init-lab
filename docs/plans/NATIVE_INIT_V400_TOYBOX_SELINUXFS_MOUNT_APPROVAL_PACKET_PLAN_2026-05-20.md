# Native Init v400 Toybox SELinuxfs Mount Approval Packet Plan

## Goal

Correct the V399 command-surface mistake without performing a new live mount.

V399 proved that `cmdv1 mount` is not implemented. It did not prove that the kernel cannot mount `selinuxfs`. V400 prepares a new fail-closed executor that uses the available `cmdv1 run /cache/bin/toybox mount` path and emits an approval packet for a future V401 live retry.

V400 itself is non-mutating. It must not mount `selinuxfs`, unmount anything, deploy helpers, start Android daemons, start Wi-Fi HAL, scan, connect, write SELinux policy, or change SELinux enforcement.

## Starting Evidence

- V399 report: `docs/reports/NATIVE_INIT_V399_SELINUXFS_MOUNT_SMOKE_2026-05-20.md`
- V399 approved live evidence: `tmp/wifi/v399-selinuxfs-mount-live-20260520-080657/`
- V399 post-smoke proof: `tmp/wifi/v399-post-smoke-proof-20260520-080750/`

V399 result:

```text
decision: selinuxfs-mount-live-executor-run-review
direct failure: cmdv1 mount -> unknown command: mount
post-proof decision: service-manager-selinux-status-native-missing
daemon_start_executed: False
wifi_bringup_executed: False
```

## Implementation

Add two host tools:

- `scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py`
  - fail-closed V401 executor.
  - `plan` produces exact future steps without device commands.
  - `run` refuses before device commands unless exact V401 approval phrase plus `--apply --assume-yes` are supplied.
  - `cleanup` refuses before device commands unless exact V401 approval phrase plus `--apply --assume-yes` are supplied.
  - approved `run` mutation is limited to `run /cache/bin/toybox mount -t selinuxfs selinuxfs /sys/fs/selinux`.
  - approved `cleanup` mutation is limited to `run /cache/bin/toybox umount /sys/fs/selinux`.

- `scripts/revalidation/wifi_selinuxfs_toybox_mount_approval_packet.py`
  - runs a fresh read-only SELinux proof.
  - verifies read-only `cmdv1 run /cache/bin/toybox mount` inventory works.
  - runs the V401 executor plan mode.
  - runs V401 no-approval refusal checks for both `run` and `cleanup`.
  - emits approval and cleanup commands as artifacts.
  - emits a rollback checklist.

Future V401 approval phrase:

```text
approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up
```

## Validation Plan

Static validation:

```text
python3 -m py_compile \
  scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  scripts/revalidation/wifi_selinuxfs_toybox_mount_approval_packet.py
```

Executor fail-closed validation:

```text
python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v400-v401-executor-plan \
  plan

python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v400-v401-executor-noapproval-run \
  run

python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v400-v401-executor-noapproval-cleanup \
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
python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_approval_packet.py \
  --out-dir tmp/wifi/v400-toybox-selinuxfs-mount-approval-packet-$(date +%Y%m%d-%H%M%S) \
  run
```

Expected:

```text
decision: toybox-selinuxfs-mount-approval-packet-ready
pass: True
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next Step

If V400 passes, V401 can run the exact-approved toybox-backed SELinuxfs mount smoke. V401 still must not start `servicemanager` or Wi-Fi. The service-manager clean-start attempt remains a later separate approval after V401 proves `/sys/fs/selinux/status` exists.
