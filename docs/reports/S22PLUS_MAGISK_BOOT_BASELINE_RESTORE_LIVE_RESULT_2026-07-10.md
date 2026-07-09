# S22+ Magisk Boot Baseline Restore Live Result

Date: 2026-07-10 KST  
Scope: one bounded S22+ boot-partition-only Magisk measurement-baseline restore

## Result

The Magisk boot baseline restore gate completed successfully after explicit
operator flash approval.

```text
run_dir=workspace/private/runs/s22plus_magisk_boot_baseline_restore_20260709T162708Z
helper=workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py
result=magisk-baseline-restored
rc=0
target=SM-S906N/g0q/S906NKSS7FYG8
vbstate=orange
root_path=/debug_ramdisk/su
verified_boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The helper flashed exactly the pinned Magisk boot-only AP:

```text
AP.tar.md5 SHA256  d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
member             boot.img.lz4
member SHA256      b33b63d9d2c56cbe10170820e88cf136be8fe9ad621a21752da19fdd9b642d31
```

No recovery, vendor_boot, vbmeta, dtbo, BL, CP, CSC, super, userdata, EFS,
sec_efs, RPMB, keymaster, modem, bootloader, Magisk module, multidisabler,
format-data, native-init candidate, kernel rebuild, raw host `dd`, fastboot, or
A90 action was performed.

## Live Trace

The helper first verified the stock Android recovery state before rebooting to
download mode:

```text
pre_restore_props:
boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
pre_restore_identity=ok
adb_reboot_download_rc=0
```

Odin then accepted the pinned AP and rebooted normally:

```text
magisk_restore_odin_rc=0
Upload Binaries
boot.img.lz4
(31%)
(62%)
(93%)
(100%)
Close Connection
```

Post-flash Android returned and the helper proved both Magisk root and the boot
partition hash:

```text
post_magisk_props:
boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
root_probe_/debug_ramdisk/su_rc=0
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
boot_hash_rc=0
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e  -
```

A separate read-only post-check also saw:

```text
boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
/product/bin/su
/debug_ramdisk/su -> ./magisk
```

## Safety State

The one-shot Magisk restore exception has been consumed and retired in
`AGENTS.md`. It must not be reused for another restore or for any native-init
candidate. Future S22+ native-init live gates still require a fresh, narrow
`AGENTS.md` exception plus explicit operator approval.

The current S22+ baseline is again the rooted Magisk measurement environment.
The next host-only unit can resume the M34/S11 design: instrument the module
load mechanism one level finer than S10C0, including per-module attempted/rc/
errno and a positive-control `/proc/modules` visibility predicate.
