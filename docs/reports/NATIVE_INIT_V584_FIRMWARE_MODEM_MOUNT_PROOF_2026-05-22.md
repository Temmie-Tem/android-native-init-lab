# Native Init V584 Firmware/Modem Mount Proof

- date: `2026-05-22 KST`
- objective: prove Android firmware/modem mount parity in native init before any qcwlanstate, Wi-Fi HAL, scan, connect, or external ping retry
- status: `proof complete`; Wi-Fi external ping is **not** complete

## Scope

- Reference:
  - `tmp/wifi/v583-firmware-mount-parity/manifest.json`
- Live proof:
  - resolve `apnhlos` and `modem` from `/sys/class/block/*/uevent`
  - create temporary block nodes under `/tmp/a90-v584-*`
  - temporarily replace native `/vendor -> /mnt/system/vendor` rootfs symlink with a rootfs directory
  - mount `apnhlos` read-only at `/vendor/firmware_mnt`
  - mount `modem` read-only at `/vendor/firmware-modem`
  - unmount, remove temporary nodes/directories, and restore `/vendor` symlink

## Guardrails

- No partition write.
- No daemon start.
- No sysfs or qcwlanstate write.
- No Wi-Fi HAL or `IWifi.start()` retry.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- Cleanup restores `/vendor -> /mnt/system/vendor`; reboot remains a fallback rollback.

## Implementation

- `scripts/revalidation/native_wifi_firmware_mount_parity_v584.py`
  - `plan`: no device commands
  - `preflight`: read-only block/mount/path classifier
  - `mount-proof`: bounded read-only vfat mount proof with cleanup and post-health checks

## V584 Result

Command result:

```text
decision: v584-firmware-modem-mount-proof-no-readiness-delta
pass: True
reason: read-only firmware/modem mount parity completed and cleaned up, but no QRTR/modem marker delta appeared without companion activity
next: plan next gate to combine mount parity with bounded companion start-only; keep qcwlanstate/IWifi/scan/connect blocked
```

Evidence:

- `tmp/wifi/v584-firmware-modem-mount-proof/`

## Partition Mapping

V584 resolved Android firmware partitions from native sysfs:

```text
apnhlos -> /sys/class/block/sda20, major=259, minor=4, blocks=97280
modem   -> /sys/class/block/sda21, major=259, minor=5, blocks=199680
```

Other preflight facts:

```text
native_healthy=True
vfat_supported=True
/vendor symlink target=/mnt/system/vendor
firmware/modem targets initially mounted=False
```

## Mount Proof

The proof mounted both firmware partitions read-only:

```text
/tmp/a90-v584-*/apnhlos /vendor/firmware_mnt vfat ro,...,gid=1000,fmask=0337,dmask=0227,shortname=lower
/tmp/a90-v584-*/modem   /vendor/firmware-modem vfat ro,...,gid=1000,fmask=0337,dmask=0227,shortname=lower
```

Cleanup result:

```text
cleanup-umount-vendor-firmware-modem=ok
cleanup-umount-vendor-firmware_mnt=ok
cleanup-rmdir-vendor-firmware-modem=ok
cleanup-rmdir-vendor-firmware-mnt=ok
cleanup-rmdir-vendor=ok
cleanup-rm-proof-nodes=ok
cleanup-rmdir-proof-base=ok
restore-vendor-symlink=ok
post_vendor_symlink_target=/mnt/system/vendor
post_healthy=True
```

## Interpretation

- V583's mount-parity gap was real, but it is solvable without writing partitions.
- Native root has `/vendor -> /mnt/system/vendor`, so Android-style firmware mount targets require a bounded rootfs path shim.
- Mount parity alone does not trigger QRTR modem readiness, `sysmon-qmi`, `service-notifier`, WLAN-PD, WLFW, QMI, or firmware-ready markers.
- The next useful gate is not another standalone qcwlanstate or Wi-Fi HAL retry. The next gate should combine this mount parity setup with the bounded companion start-only sequence.

## Next Gate

Recommended V585:

1. Reuse V584 mount parity setup and cleanup.
2. Start only the companion stack in bounded mode:
   - `qrtr-ns`
   - `rmt_storage`
   - `tftp_server`
   - `pd-mapper`
   - `cnss_diag`
   - `cnss-daemon`
3. Observe only QRTR/modem readiness, `sysmon-qmi`, `service-notifier`, WLAN-PD, WLFW/QMI/BDF markers.
4. Keep qcwlanstate retry, Wi-Fi HAL start, scan, connect, DHCP, routing, and external ping blocked until lower readiness markers change.
