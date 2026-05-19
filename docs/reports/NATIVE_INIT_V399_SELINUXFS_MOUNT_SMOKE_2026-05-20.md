# Native Init v399 SELinuxfs Mount Smoke

## Summary

V399 ran the exact-approved SELinuxfs mount smoke from the V398 approval packet.

The approved live run did not start `servicemanager`, Wi-Fi HAL, scan, connect, write SELinux policy, change SELinux enforcement, or mutate Android partitions. It attempted only the approved SELinuxfs runtime-surface activation path and post-checks.

The result is a transport/tooling gap, not a kernel SELinuxfs conclusion: the live executor attempted `cmdv1 mount selinuxfs /sys/fs/selinux selinuxfs`, but the current native command table returned `unknown command: mount`. A follow-up read-only proof confirmed `/sys/fs/selinux/status` is still absent. A read-only `toybox mount` inventory works through `cmdv1 run`, so the next bounded target is a corrected toybox-backed mount executor.

## Approval Used

```text
approve v399 mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up
```

## Evidence

Primary evidence:

- approved V399 live run: `tmp/wifi/v399-selinuxfs-mount-live-20260520-080657/`
- approved V399 manifest: `tmp/wifi/v399-selinuxfs-mount-live-20260520-080657/manifest.json`
- approved V399 summary: `tmp/wifi/v399-selinuxfs-mount-live-20260520-080657/summary.md`
- post-smoke SELinux proof: `tmp/wifi/v399-post-smoke-proof-20260520-080750/`
- post-smoke SELinux manifest: `tmp/wifi/v399-post-smoke-proof-20260520-080750/manifest.json`

V399 executor result:

```text
decision: selinuxfs-mount-live-executor-run-review
pass: False
reason: selinuxfs mount did not produce a visible status page
device_commands_executed: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

Important nuance: `device_mutations=True` means the approved mutation path was reached. The direct command evidence shows the mount command itself did not execute because `cmdv1` rejected `mount` as an unknown command.

Direct failure:

```text
cmdv1 mount selinuxfs /sys/fs/selinux selinuxfs
[err] unknown command: mount
A90P1 END ... rc=-2 errno=2 ... status=unknown
```

Post-check result:

```text
stat /sys/fs/selinux/status
stat: /sys/fs/selinux/status: No such file or directory

cat /sys/fs/selinux/enforce
cat: /sys/fs/selinux/enforce: No such file or directory
```

Post-smoke SELinux proof:

```text
decision: service-manager-selinux-status-native-missing
pass: True
reason: native SELinux status page is absent or unreadable
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Toybox mount inventory check:

```text
cmdv1 run /cache/bin/toybox mount
rootfs on / type rootfs (rw)
proc on /proc type proc (rw,relatime)
sysfs on /sys type sysfs (rw,relatime)
tmpfs on /tmp type tmpfs (...)
/dev/block/sda31 on /cache type ext4 (...)
/dev/block/mmcblk0p1 on /mnt/sdext type ext4 (...)
configfs on /config type configfs (...)
/dev/block/sda28 on /mnt/system type ext4 (...)
```

## Interpretation

V399 did not prove that `selinuxfs` cannot mount. It proved that the V399 executor used the wrong device command surface:

- `cmdv1` has `stat`, `cat`, and `run`, but no built-in `mount`.
- `/cache/bin/toybox mount` is callable through `cmdv1 run`.
- `/proc/filesystems` still advertises `selinuxfs` from V397/V398 evidence.
- `/sys/fs/selinux` exists as a directory but has no active SELinuxfs status page.

Therefore the current blocker remains the same SELinux runtime surface, with a narrower tooling fix needed before retrying the mount smoke.

## Validation

Approved live command:

```text
python3 scripts/revalidation/wifi_selinuxfs_mount_live_executor.py \
  --out-dir tmp/wifi/v399-selinuxfs-mount-live-20260520-080657 \
  --approval-phrase "approve v399 mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Post-smoke read-only proof:

```text
python3 scripts/revalidation/wifi_service_manager_selinux_surface_proof.py \
  --out-dir tmp/wifi/v399-post-smoke-proof-20260520-080750 \
  run
```

`git diff --check`: PASS.

## Next Target

Proceed to V400: toybox-backed SELinuxfs mount approval packet.

V400 should not reuse the V399 approval as-is. It should update the executor command surface to:

- approved run mutation: `run /cache/bin/toybox mount -t selinuxfs selinuxfs /sys/fs/selinux`
- approved cleanup mutation: `run /cache/bin/toybox umount /sys/fs/selinux`
- required checks: `/proc/mounts`, `stat /sys/fs/selinux/status`, `cat /sys/fs/selinux/enforce`, and a short hex read of `/sys/fs/selinux/status`

`servicemanager`, Wi-Fi HAL, scan, connect, and Wi-Fi bring-up remain blocked until the SELinuxfs status page is proven visible.
