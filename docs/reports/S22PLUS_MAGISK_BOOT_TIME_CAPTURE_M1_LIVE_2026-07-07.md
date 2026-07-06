# S22+ Magisk Boot-Time Capture M1 Live - 2026-07-07

## Scope

Live execution of the temporary S22+ Magisk boot-time capture M1 unit.

This unit installed two temporary Magisk hook scripts, rebooted Android once,
collected the generated private logs, and removed the remote capsule. It did
not use Odin, flash any partition, install a Magisk module, load/unload modules,
write sysfs/configfs, run `multidisabler`, format data, or flash a native-init
candidate.

## Authorization / Gate

Preflight commit:

- `f665cbc0 Gate S22+ Magisk boot-time capture M1`

Preflight report:

- `docs/reports/S22PLUS_MAGISK_BOOT_TIME_CAPTURE_M1_PREFLIGHT_2026-07-07.md`

Helper:

- `workspace/public/src/scripts/revalidation/s22plus_magisk_boot_time_capture_m1.py`

Live command:

```text
python3 workspace/public/src/scripts/revalidation/s22plus_magisk_boot_time_capture_m1.py \
  --live-run \
  --ack S22PLUS-MAGISK-BOOT-CAPTURE-M1
```

## Live Sequence

The helper verified rooted Android first:

```text
model=SM-S906N
device=g0q
build=S906NKSS7FYG8
bootloader=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
su=/product/bin/su
su_v=30.7:MAGISKSU
su -c id -> uid=0(root) ... context=u:r:magisk:s0
```

Generated hook script hashes:

```text
post_script_sha256=129472e86ae164181e82ad896e9b98d59a8f4251c4beffea7892ac9ef94f8645
service_script_sha256=d4497f881601c8775c7d4f798be0eca782b12ca81f0981f94a9d2ba8a82e7646
```

The helper installed:

```text
/data/adb/post-fs-data.d/s22plus_boot_capture_m1.sh
/data/adb/service.d/s22plus_boot_capture_m1.sh
```

Then it rebooted Android normally. Android and Magisk root returned cleanly.

## Pull Fallback

The first post-reboot host pull attempted:

```text
adb pull /data/adb/s22plus_boot_capture_m1 ...
```

Result:

```text
Permission denied
```

Interpretation: the capsule and reboot path worked, but direct `adb pull` of
the Magisk-owned `/data/adb` directory is not allowed from the shell context.
The helper was updated with a root-owned tar fallback plus `--collect-existing`.
It then recovered the already-created logs without another reboot:

```text
python3 workspace/public/src/scripts/revalidation/s22plus_magisk_boot_time_capture_m1.py \
  --collect-existing
```

Final private run:

```text
workspace/private/runs/s22plus_magisk_boot_time_capture_m1_20260706T173432Z
```

## Captured Stages

Two stage files were collected:

```text
capture_file_count=2
remote_cleanup_ok=true
```

Stage summary:

```text
post_fs_data:
  file=post_fs_data_19700108T054017Z.txt
  uptime=6.67s
  bytes=550428
  proc_modules_lines=482
  dmesg_lines=2578
  usb_function_mentions=18
  display_mentions=27

service:
  file=service_20250801T093108Z.txt
  uptime=8.81s
  bytes=527979
  proc_modules_lines=482
  dmesg_lines=2315
  usb_function_mentions=19
  display_mentions=22
```

The `post-fs-data` timestamp uses an unset early wall clock, so uptime is the
authoritative time source for that stage.

## Boot-Time Findings

At `post-fs-data` uptime 6.67s:

- Magisk root is already active.
- `/proc/modules` already lists 482 modules.
- `msm_drm`, `dwc3_msm`, `usb_f_gsi`, `usb_f_qdss`, `usb_f_ss_mon_gadget`,
  `gpucc_waipio`, `dispcc_waipio`, and `msm_kgsl` are already loaded.
- USB configfs already exposes `ffs.adb` and `ncm.0`.
- DRM/display nodes are already visible, including `card0`, `renderD128`, and
  `panel0-backlight`.
- `sys.boot_completed`, `init.svc.adbd`, and `sys.usb.*` props were still blank
  in the captured prop block.

At `service.d` uptime 8.81s:

- Magisk root is still active.
- module count remains 482.
- `init.svc.adbd=running`.
- `sys.usb.config=mtp,conn_gadget,adb`.
- `sys.usb.state=mtp,conn_gadget,adb`.

Interpretation:

- The Magisk hook is too late to observe the true kernel-side module load order
  live; by 6.67s the major USB/display/GPU stack is already loaded.
- It is still early enough to prove the first practical Android-side
  observation envelope: root exists, configfs exists, USB functions exist, and
  DRM exists before Android reports boot complete.
- For native init, the next design should treat `modules.load` / `modules.dep`
  as the order source and use M1 as the early-state validation target.

## Cleanup / Health

The helper removed the remote capsule:

```text
CLEAN:/data/adb/post-fs-data.d/s22plus_boot_capture_m1.sh
CLEAN:/data/adb/service.d/s22plus_boot_capture_m1.sh
CLEAN:/data/adb/s22plus_boot_capture_m1
CLEAN:/data/local/tmp/s22plus_boot_capture_m1.tar
```

Final Android state:

```text
boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
su=/product/bin/su
su -c id -> uid=0(root) ... context=u:r:magisk:s0
```

## Result

PASS with one helper fix:

- The temporary Magisk capsule ran at both `post-fs-data` and `service.d`.
- Android rebooted and Magisk root returned.
- The logs were recovered through the root-tar fallback.
- Remote capsule cleanup completed.
- The device remains normal rooted Android.

The useful conclusion is also a constraint: Magisk `post-fs-data` is not early
enough to observe raw driver load order before USB/display/DRM are ready. The
native-init plan should now build a USB-first observable boot recipe from
`modules.load` / `modules.dep`, then compare native state against the M1
early-state target.

## Next

Build the host-only S22+ observable-native-init recipe:

1. derive a minimal USB-first module list from `modules.load` / `modules.dep`;
2. define the configfs/FunctionFS path needed for an ADB or NCM observation
   channel;
3. define the pstore marker fallback;
4. stop at the next boot-artifact flash boundary until a fresh SHA-pinned
   `AGENTS.md` boot-only exception exists.
