# S22+ TWRP + Root + 116-Package Checkpoint

Date: 2026-07-06

Device:
- Samsung Galaxy S22+ `SM-S906N` / `g0q`
- Build: `S906NKSS7FYG8`
- Root: Magisk 30.7

Scope:
- Re-patch TWRP recovery after the current recovery block was found to be stock
  FYG8 recovery again.
- Preserve the existing FYG8 disabled vbmeta.
- Return to Android and verify the existing 116-package cleanup checkpoint.
- No Magisk reinstall, multidisabler, format-data, bootloader/modem/EFS/RPMB, or
  A90 partition write.

## Authorization / Gate

This used the existing narrow S22+ recovery-infra exception from:

```text
078f4a65 Authorize S22+ recovery infra flash gate
```

The live operation was limited further than the original gate: Odin4 wrote only
the pinned TWRP recovery tar through the AP slot. `vbmeta` was not rewritten
because Android-side readback already matched the generated FYG8 disabled vbmeta
prefix.

## Pre-State

Android preflight:

```text
sys.boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
verifiedbootstate=orange
flash_locked=0
warranty_bit=1
root=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
user-0 packages=116
disabled packages=0
```

Recovery/vbmeta preflight:

```text
current recovery full sha256:
93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4

FYG8 stock recovery full sha256:
93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4

current vbmeta FYG8-disabled prefix sha256:
9c0e5b9615f8dac2a902f709927ff3fccaa4e074b34adbd0f8cd7498db78ba13
```

Interpretation: recovery had returned to stock; vbmeta was already disabled.

## Pinned Inputs

TWRP tar:

```text
workspace/private/inputs/s22plus_twrp/g0q/twrp-3.7.0_12-1_afaneh92-g0q.tar
0914c68a5353c367216805a3a2fdeb4982c6629368dc021c7fefc10d3d3bd034
```

Extracted TWRP recovery image:

```text
workspace/private/inputs/s22plus_twrp/g0q/twrp-3.7.0_12-1_afaneh92-g0q.extract/recovery.img
e4e1861760298da756d1d649029c33b4c953f12272ebda1705214da56245e036
```

Generated FYG8 disabled vbmeta:

```text
workspace/private/outputs/s22plus_fyg8_disabled_vbmeta/vbmeta.img
9c0e5b9615f8dac2a902f709927ff3fccaa4e074b34adbd0f8cd7498db78ba13
```

Rollback anchors present:

```text
stock recovery-only rollback AP:
8d3647313d2e100134f77984d13c7e5dc9946510ab57d8e34dd0cd192ca8586d

full FYG8 stock firmware:
f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8
```

## Live Operation

The device was rebooted to download mode. Odin4 detected the device, then TWRP
was flashed with no auto-reboot:

```text
odin4 -a workspace/private/inputs/s22plus_twrp/g0q/twrp-3.7.0_12-1_afaneh92-g0q.tar -d <redacted-download-device>
```

Odin4 result:

```text
Upload Binaries
recovery.img
(56%)
(100%)
Close Connection
odin_exit=0
```

The first post-flash reboot entered Android, not recovery, but recovery was not
restored to stock. Android readback immediately after that boot showed:

```text
recovery prefix sha256:
e4e1861760298da756d1d649029c33b4c953f12272ebda1705214da56245e036

vbmeta FYG8-disabled prefix sha256:
9c0e5b9615f8dac2a902f709927ff3fccaa4e074b34adbd0f8cd7498db78ba13
```

## TWRP Boot Proof

Android was then rebooted to recovery. Recovery ADB came up as TWRP:

```text
ro.twrp.version=3.7.0_12-1_afaneh92
ro.product.device=g0q
ro.product.name=twrp_g0q
ro.product.model=SM-S906E
ro.boot.verifiedbootstate=orange
kernel=5.10.81-afaneh92-g0418bf01a3e2
```

The TWRP ramdisk reports `SM-S906E`, matching the previous g0q recovery-infra
result. The target Android preflight remains `SM-S906N`; both are in the same
upstream g0q recovery family used for this unofficial build.

TWRP readback:

```text
device recovery prefix sha256:
e4e1861760298da756d1d649029c33b4c953f12272ebda1705214da56245e036

local TWRP recovery sha256:
e4e1861760298da756d1d649029c33b4c953f12272ebda1705214da56245e036

device vbmeta FYG8-disabled prefix sha256:
9c0e5b9615f8dac2a902f709927ff3fccaa4e074b34adbd0f8cd7498db78ba13

local FYG8 disabled vbmeta sha256:
9c0e5b9615f8dac2a902f709927ff3fccaa4e074b34adbd0f8cd7498db78ba13
```

## Final Android Checkpoint

The device was rebooted back to Android and validated:

```text
sys.boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
verifiedbootstate=orange
flash_locked=0
warranty_bit=1
root=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
user-0 packages=116
disabled packages=0
```

Core package presence:

```text
ok:com.android.settings
ok:com.sec.android.app.launcher
ok:com.android.systemui
ok:com.google.android.gms
ok:com.android.vending
ok:com.topjohnwu.magisk
```

Android-side final readback still matched the pinned payloads:

```text
recovery prefix sha256:
e4e1861760298da756d1d649029c33b4c953f12272ebda1705214da56245e036

vbmeta FYG8-disabled prefix sha256:
9c0e5b9615f8dac2a902f709927ff3fccaa4e074b34adbd0f8cd7498db78ba13
```

## Result

PASS.

Current checkpoint state:

```text
Android boots normally.
Magisk root works.
TWRP recovery boots and exposes recovery ADB.
Recovery prefix is pinned TWRP 3.7.0_12-1_afaneh92.
vbmeta prefix is generated FYG8 disabled vbmeta.
Package cleanup checkpoint remains at 116 user-0 packages.
Safe mode is not active.
```

This is now the preferred S22+ experiment checkpoint before native-init or
serverization work: stock Android userspace remains bootable, root is available,
TWRP recovery is available as a recovery shell, and the package surface is the
reboot-validated 116-package baseline.
