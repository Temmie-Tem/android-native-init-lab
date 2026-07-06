# S22+ TWRP + Magisk Boot-Capture Restore Preflight - 2026-07-07

## Scope

Prepare one bounded S22+ maintenance window to restore two pieces of
infrastructure before the Magisk boot-capture measurement unit:

1. refresh TWRP recovery and prove it by direct recovery boot;
2. restore the already proven Magisk boot-only Android root baseline.

This is a preflight plus guard-script unit. No live Odin transfer, partition
write, reboot, recovery boot, or Magisk re-root was performed by this report.

## Why This Exists

`GOAL.md` was corrected on 2026-07-07: stop blind S22+ native-init first-light
flashes and measure the stock rooted Android bring-up first. The P3 rollback
left the device normally booting Android but without `su`, so the next useful
step is to recover the rooted Android measurement environment.

The operator also asked to include TWRP in the same re-root maintenance window.
This preflight does that narrowly:

- TWRP is refreshed as a recovery-only flash.
- Magisk is restored as a boot-only flash.
- No new vbmeta write is planned because Android preflight already shows
  `ro.boot.verifiedbootstate=orange`.
- TWRP persistence after a later Android boot is not claimed. If persistent
  custom recovery is needed, that is a separate unit and must not silently pull
  in `multidisabler` or `format data`.

## Current Device State

ADB preflight observed one normal Android device:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
su=
```

The serial number is intentionally omitted from this public report.

## Pinned Inputs

TWRP recovery tar:

```text
path=workspace/private/inputs/s22plus_twrp/g0q/twrp-3.7.0_12-1_afaneh92-g0q.tar
sha256=0914c68a5353c367216805a3a2fdeb4982c6629368dc021c7fefc10d3d3bd034
tar_members=recovery.img
```

Magisk boot-only AP:

```text
path=workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5
sha256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
tar_members=boot.img.lz4
boot.img_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
boot.img.lz4_sha256=b33b63d9d2c56cbe10170820e88cf136be8fe9ad621a21752da19fdd9b642d31
```

Rollback packages:

```text
stock_recovery_rollback_AP=workspace/private/outputs/s22plus_twrp/stock_recovery_rollback/AP.tar.md5
stock_recovery_rollback_sha256=8d3647313d2e100134f77984d13c7e5dc9946510ab57d8e34dd0cd192ca8586d
stock_recovery_rollback_members=recovery.img.lz4

stock_boot_rollback_AP=workspace/private/outputs/s22plus_native_init/odin4_stock_rollback_short/AP.tar.md5
stock_boot_rollback_sha256=1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
stock_boot_rollback_members=boot.img.lz4

full_stock_firmware_zip=workspace/private/inputs/firmware/SAMFW.COM_SM-S906N_SKC_S906NKSS7FYG8_fac.zip
full_stock_firmware_sha256=f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8
```

## Guard Script

Added:

```text
workspace/public/src/scripts/revalidation/s22plus_twrp_magisk_restore_window.py
```

The helper refuses live mode unless:

- every pinned artifact SHA matches;
- each tar has exactly the expected single member;
- current Android preflight proves `SM-S906N` / `g0q` / `S906NKSS7FYG8`;
- current Android preflight proves `ro.boot.verifiedbootstate=orange`;
- live mode includes the ack token:
  `S22PLUS-TWRP-MAGISK-RESTORE-WINDOW`.

Live sequence:

```text
adb reboot download
odin4 -a <pinned-twrp-recovery-tar> -d <download-device>
wait for operator to boot directly into TWRP recovery
prove ro.twrp.version=3.7.0_12-1_afaneh92 and device=g0q
adb reboot download
odin4 --reboot -a <pinned-magisk-boot-only-AP> -d <download-device>
wait for Android boot_completed=1
check Magisk/su and try su -c id
```

If TWRP proof fails, the helper stops before the Magisk step. If Android boots
but Magisk superuser policy has not yet allowed ADB Shell, the helper returns a
distinct pending-root-policy result rather than treating the boot as failed.

## Static Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_twrp_magisk_restore_window.py
```

Result: pass.

Dry-run:

```text
python3 workspace/public/src/scripts/revalidation/s22plus_twrp_magisk_restore_window.py
```

Result:

```text
dry-run ok: artifacts and Android preflight verified
```

Private dry-run log:

```text
workspace/private/runs/s22plus_twrp_magisk_restore_20260706T171824Z/s22plus_twrp_magisk_restore_window.txt
```

## Authorization Update

`AGENTS.md` now contains a narrow 2026-07-07 S22+ TWRP+Magisk
boot-capture restore exception. It authorizes only:

- the exact recovery-only TWRP tar above;
- the exact boot-only Magisk AP above;
- the exact stock recovery-only and stock boot-only rollback APs above;
- no vbmeta write, no Magisk module, no multidisabler, no format data, no
  native-init candidate flash, and no non-recovery/boot partition write.

## Next Live Command

Run only when ready to watch the device and manually boot directly into TWRP
after the first Odin transfer:

```text
python3 workspace/public/src/scripts/revalidation/s22plus_twrp_magisk_restore_window.py \
  --live \
  --ack S22PLUS-TWRP-MAGISK-RESTORE-WINDOW
```

Expected operator action during the run: after the TWRP Odin transfer completes,
force the device to boot directly into recovery. The helper will wait for TWRP
ADB, verify it, then continue to the Magisk boot-only flash.
