# Debian-Eye Hardware Inventory Live

- Date: 2026-07-04
- Scope: read-only Debian userspace hardware inventory from the staged rootfs
- Resident: `A90 Linux init 0.11.151 (v3395-wsta-screenapp-live)`
- Device action: read-only chroot inventory
- Flash: none
- Public exposure: none
- Decision: `debian-eye-hardware-inventory-live-pass`

## Summary

The Debian-eye inventory charter was run before any WSTA55+ persistent-exposure
live rung.  The device stayed on the existing V3395 resident image; no new boot
artifact was built or flashed.

The staged Debian rootfs image was mounted read-only through a loop device, then
Debian-side commands collected a redacted hardware inventory under the native PID1
control plane.  The collection started no Wi-Fi association, no DHCP, no tunnel,
no public smoke request, and no switch-root.  Cleanup detached the temporary mount
and loop state.

Pass decision:

```text
debian-eye-hardware-inventory-live-pass
```

## Method

The first inline command form exceeded the practical cmdv1 script size.  The
collection was rerun with a private uploaded helper script, then removed after
execution.  Public committed artifacts contain only the redacted summary.

Staged Debian image evidence:

```text
remote_image_sha256=9ee7f5b3a865141a9e57d59a6ff01c7363bcd97e9a1712d5b84e40ec469add94
read_only=true
device_action=read-only-chroot-inventory
```

Cleanup markers:

```text
cleanup_mount_absent=true
cleanup_loop_node_absent=true
cleanup_remote_script_removed=true
```

## Debian View

Debian userspace:

```text
debian_version=12.14
kernel=Linux 4.14.190-25818860-abA908NKSU5EWA3
arch=aarch64
```

CPU and memory:

```text
cpu_processor_count=8
mem_total_kb=5504940
```

Block view:

```text
sys_class_block_count=110
partition_count=78
block_sample=loop0..loop15, mmcblk0, mmcblk0p1, ram0, ram1
partition_sample=ram0..ram15 8.0 MiB, loop0 2048.0 MiB, sda 121948.0 MiB, sda1/sda2 2.0 MiB
```

Network interface shape, with address values redacted:

```text
interface_count=12
interfaces=bond0:down:1500, bonding_masters:unknown:unknown, dummy0:down:1500,
  ip6_vti0:down:1500, ip6tnl0:down:1452, ip_vti0:down:1480, lo:down:65536,
  ncm0:up:8178, p2p0:down:1500, sit0:down:1480, wifi-aware0:down:1500,
  wlan0:down:1500
ip_addr_values_redacted=true
mac_values_redacted=true
```

Filesystem view:

```text
ext4=true
proc=true
sysfs=true
tmpfs=true
overlay=false
sample=sysfs, rootfs, ramfs, bdev, proc, cpuset, cgroup, cgroup2, tmpfs,
  configfs, debugfs, tracefs, sockfs, dax, bpf, pipefs, devpts, ext3, ext2,
  ext4, vfat, msdos, sdfat, ecryptfs, sdcardfs, ntfs, fuseblk, fuse, fusectl,
  incremental-fs
```

A bounded hardware-line dmesg sample was present in the private raw run output.
The public report does not commit the raw dmesg text.

## Vendor Stack Shape

Debian userspace command stacks absent from the chroot view:

```text
cloudflared=true
hciconfig=true
mmcli=true
qmicli=true
sensors=true
tinymix=true
tinyplay=true
wpa_supplicant=true
```

Vendor node visibility in the Debian chroot view:

```text
/dev/binder absent=true
/dev/kgsl-3d0 absent=true
/dev/msm_audio_cal absent=true
/dev/radio0 absent=true
/dev/snd absent=true
/dev/video0 absent=true
/system/vendor absent=true
/vendor absent=true
/sys/class/bluetooth absent=false
/sys/class/camera absent=false
```

This means the Debian view can see some raw kernel class paths through sysfs, but
it does not currently carry the matching Android/vendor userspace command stacks.

## Native D0 Cross-Check

The Debian-side view matches the existing native-side D0 public summary for shared
kernel facts:

```text
cpu_count_expected=8
cpu_count_match=true
mem_total_kb_expected_approx=5504936
mem_total_kb_delta=4
ext4_expected=true
ext4_match=true
overlay_expected=false
overlay_observed=false
```

No material divergence was observed for the D0 facts checked here.

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No credentialed Wi-Fi association, DHCP, public tunnel, public smoke request,
  persistent public exposure, userdata format/populate, or switch-root ran.
- The staged Debian rootfs was mounted read-only for inventory.
- Temporary mount, loop, and uploaded script state were cleaned up.
- The final resident remained V3395 with `selftest fail=0`.
- MAC, BSSID, IP, gateway, serial, UUID, PARTUUID, hostname, SSID, PSK, and any
  routable address values are not committed in this report.
- Private raw output remains under `workspace/private/`.

## Validation

Resident health after collection:

```text
status=ok
selftest: pass=12 warn=1 fail=0
public_exposure=false
```

Result: pass.

## Next

The operator-requested Debian-eye inventory gate is now satisfied.  WSTA persistent
exposure work can resume at a non-live WSTA54 private lease artifact, or at a
separately gated live publish path, while preserving the WSTA52/WSTA53 fail-closed
contract.
