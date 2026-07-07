# S22+ Native-Init M8A Minimal-FS Download Live Result - 2026-07-07

## Verdict

M8A did not survive to its minimal-fs timed Samsung download-mode request.

Safety result passed after manual recovery: the exact SHA-pinned M8A boot-only
AP flashed, the original Odin endpoint disconnected, no later self-download
endpoint appeared within the bounded wait, the operator manually returned the
device to Samsung download mode, the pinned Magisk boot-only rollback AP
flashed successfully, and Android returned to the rooted Magisk baseline.

Native-init result is a useful negative discriminator: M8A had no module
insertion, no module-list file, no configfs, no USB gadget, no UDC binding, and
no USB role forcing. Therefore the M8 failure is not explained by the first
18-module batch itself. The failure is below or inside the minimal freestanding
C PID1 setup path.

## Candidate

```text
AP.tar.md5             c97d29e38fe3293ad145a7743b61ae5fddae8f1b028e619dcd56e2f640de3c19
boot.img               8a816fb3bf8e644de4bbe0409f6cf94fd06a33d16e672569c130535ce139ad44
M8A /init              aac2a03a2b20e72c3d69cfa3c4d3e5c045c817c293c347ac2aaf81f1bfb029b1
source                 830f95cc0f4237f10f2e132ead873a69f543134a503816fa2281205d41362538
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
runtime                freestanding-raw-syscall
```

The AP contained exactly one Odin member:

```text
boot.img.lz4
```

M8A intended runtime:

```text
direct PID1
mount /dev, /proc, /sys, /run only
create basic char nodes for kmsg/console/null/zero
emit S22_NATIVE_INIT_M8A_MINFS_DOWNLOAD
sleep 250 ms
request reboot("download")
park if reboot returns
```

M8A intentionally omitted:

```text
module insertion
module-list file
/lib/modules access
configfs
USB gadget
UDC binding
USB role force
Android/Magisk handoff
persistent partition mounts
block-device writes
```

## Live Timeline

Private live run log:

```text
workspace/private/runs/s22plus_m8a_minfs_download_live_gate_20260707T110638Z/s22plus_m8a_minfs_download_live_gate.txt
```

Key events:

```text
11:06:38Z  live helper start
11:06:49Z  rooted Android dry-run snapshot complete
11:06:49Z  adb reboot download requested
11:07:00Z  Odin/download device appeared for candidate flash
11:07:00Z  M8A candidate AP flash started
candidate_odin_rc=0
11:07:03Z  original Odin endpoint absent; disconnect proof acquired
11:08:03Z  self-download observation ended, m8a_self_download_seen=0
```

After helper exit, host-side checks showed no transport:

```text
adb devices -l      no devices
odin4 -l            no devices
lsusb Samsung scan  no matching Samsung/Odin device
```

Private rollback run log:

```text
workspace/private/runs/s22plus_m8a_minfs_download_live_gate_20260707T111237Z/s22plus_m8a_minfs_download_live_gate.txt
```

Rollback events:

```text
11:12:37Z  rollback helper start from manual Samsung download mode
magisk_rollback_odin_rc=0
11:13:23Z  Android returned with boot_completed=1 and Magisk root
```

## Post-Rollback Verification

Independent host check after helper completion:

```text
sample count            4
sys.boot_completed      1
init.svc.bootanim       stopped
boot reason             reboot,download
Magisk root             available
boot hash               2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Retained evidence:

```text
pstore files             none
/proc/last_kmsg bytes    2097136
M8A marker in retained   no
```

## Interpretation

M8A narrowed the M8/M7 failure below the module and USB layers.

This result removes these suspects from the M8 failure class:

```text
first 18 M7-only modules
module-list parsing
opening stock vendor_boot /lib/modules
configfs
ACM/USB gadget setup
UDC binding
USB role force
host serial handling
```

The remaining live-proven boundary is:

```text
M4T3 raw-asm direct reboot("download") first action       PASS
M5B freestanding C + dev/proc/sys/config + marker/reboot  NO SELF-DOWNLOAD
M8A freestanding C + dev/proc/sys/run + marker/reboot     NO SELF-DOWNLOAD
```

So the next unit should not split the M8 module batch. It should compare the
M4T3 passing raw-assembly path against the C minimal-fs path and isolate the
first failing layer: C entry/runtime shape, stack/use of compiler-emitted
sections, `/dev` setup, `/dev/kmsg` open/write, `mknodat`, `mount`, or
reboot-after-setup. Retained marker absence means the exact failing syscall is
not proven yet.

## Stop Rule

M8A is recovered. Do not repeat M8A or proceed to M8B module split until a
host-only lower-layer postmortem produces a narrower candidate.
