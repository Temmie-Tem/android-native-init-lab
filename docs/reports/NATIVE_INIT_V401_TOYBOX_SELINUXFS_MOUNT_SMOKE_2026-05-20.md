# Native Init v401 Toybox SELinuxfs Mount Smoke

## Summary

V401 ran the exact-approved toybox-backed SELinuxfs mount smoke from the V400 approval packet.

The approved live run succeeded. `selinuxfs` is now mounted at `/sys/fs/selinux`, `/sys/fs/selinux/status` is visible, `/sys/fs/selinux/enforce` reads `0`, and a short read of the status page succeeds. The post-mount SELinux proof no longer classifies the native SELinux status page as missing.

This was not Wi-Fi bring-up. It did not start `servicemanager`, start Wi-Fi HAL, scan, connect, write SELinux policy, change enforcement, deploy helpers, or mutate Android partitions. The only approved mutation was the runtime mount of `selinuxfs`.

## Approval Used

```text
approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up
```

## Evidence

Primary evidence:

- approved V401 live run: `tmp/wifi/v401-toybox-selinuxfs-mount-live-20260520-082325/`
- approved V401 manifest: `tmp/wifi/v401-toybox-selinuxfs-mount-live-20260520-082325/manifest.json`
- approved V401 summary: `tmp/wifi/v401-toybox-selinuxfs-mount-live-20260520-082325/summary.md`
- post-mount SELinux proof: `tmp/wifi/v401-post-mount-selinux-proof-20260520-082352/`
- post-mount SELinux manifest: `tmp/wifi/v401-post-mount-selinux-proof-20260520-082352/manifest.json`

V401 executor result:

```text
decision: toybox-selinuxfs-mount-live-executor-run-pass
pass: True
reason: selinuxfs status page is visible after toybox mount
device_commands_executed: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

Direct mount evidence:

```text
cmdv1 run /cache/bin/toybox mount -t selinuxfs selinuxfs /sys/fs/selinux
[exit 0]
[done] run
```

Post-mount `/proc/mounts` evidence:

```text
selinuxfs /sys/fs/selinux selinuxfs rw,relatime 0 0
```

Status page evidence:

```text
stat /sys/fs/selinux/status
mode=0444 uid=0 gid=0 size=0

cat /sys/fs/selinux/enforce
0

xxd -l 64 /sys/fs/selinux/status
00000000: 0100 0000 0000 0000 0000 0000 0000 0000  ................
00000010: 0100 0000                                ....
```

Post-mount SELinux proof result:

```text
decision: service-manager-selinux-surface-native-ready-private-proof-needed
pass: True
reason: native SELinux/status/context inputs are visible, but private namespace status visibility is unproven
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Key post-mount checks:

| check | status | detail |
| --- | --- | --- |
| `native-selinuxfs-mount` | `present` | `proc_filesystems_selinuxfs=True proc_mounts_sysfs_selinux=True` |
| `native-selinux-status-page` | `present` | `status=True enforce=True enforce_value=0` |
| `native-service-manager-class` | `partial` | `service_manager` class/perms paths still absent |
| `mounted-service-context-inputs` | `present` | mounted Android service/hwservice context inputs visible |
| `v392-private-preexec-selinux-evidence` | `status-unproven` | private namespace `/sys/fs/selinux/status` still needs proof |

Postflight device health:

```text
selftest: pass=11 warn=1 fail=0
pid1guard: pass=11 warn=1 fail=0
netservice: disabled tcpctl=stopped
rshell: stopped
```

## Interpretation

V401 removes the native SELinux status-page blocker that V397 identified.

The remaining blocker is narrower:

- native `/sys/fs/selinux/status` is now visible.
- native Android SELinux context inputs remain visible under `/mnt/system`.
- `servicemanager` was not started in V401.
- Wi-Fi HAL/start/scan/connect were not attempted.
- the private Android execution namespace used by the service-manager helper still has not proven that `/sys/fs/selinux/status`, `/sys/fs/selinux/enforce`, binder, properties, and service context files are visible together.

The mount was intentionally left active for the next bounded proof. Cleanup is available through the V400-approved cleanup command if rollback is needed, but cleanup was not run because the next target depends on the mounted runtime surface.

## Validation

Approved live command:

```text
python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v401-toybox-selinuxfs-mount-live-20260520-082325 \
  --approval-phrase "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Post-mount SELinux proof:

```text
python3 scripts/revalidation/wifi_service_manager_selinux_surface_proof.py \
  --out-dir tmp/wifi/v401-post-mount-selinux-proof-20260520-082352 \
  run
```

`git diff --check`: PASS.

## Next Target

Proceed to V402: private namespace SELinux surface proof.

V402 should prove, without starting `servicemanager` or Wi-Fi, that the service-manager execution namespace can see:

- `/sys/fs/selinux/status`
- `/sys/fs/selinux/enforce`
- binder devnodes
- Android property runtime inputs
- `plat_service_contexts` and related service/hwservice context files

If V402 passes, the next separate approval target is a bounded `servicemanager` start-only packet. Wi-Fi HAL/start/scan/connect remains blocked until `servicemanager` is clean or strongly classified as non-blocking.
