# S22+ Magisk Root Boot-Only Live - 2026-07-06

## Scope

Proceed with the operator-provided Magisk-patched firmware artifact for Samsung
S22+ `SM-S906N` / `g0q` on `S906NKSS7FYG8`, while staying inside the existing
AGENTS boot-only Magisk root baseline exception.

The operator-provided Magisk output was a full AP-style tar, so it was not flashed
directly. This run extracted only `boot.img`, packaged only `boot.img.lz4` into a
new boot-only Odin AP, and flashed that boot-only AP.

No BL, CP, CSC, vbmeta, recovery, vendor_boot, super, persist, userdata, EFS,
RPMB, keymaster, or modem payload was flashed in this unit.

## Inputs

- Magisk APK:
  `workspace/private/inputs/magisk/v30.7/Magisk-v30.7.apk`
- Magisk APK SHA256:
  `e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5`
- Operator-provided Magisk output tar:
  `workspace/private/inputs/firmware/SAMFW.COM_SM-S906N_SKC_S906NKSS7FYG8_fac/magisk_patched-30700_NJTCd.tar`
- Magisk output tar SHA256:
  `100ef6ab0f6c82461a696bd8acf85824678b33033c81905941aeee15fe3c3f48`
- Stock boot SHA256:
  `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`
- Stock boot-only rollback AP:
  `workspace/private/outputs/s22plus_native_init/odin4_stock_rollback_short/AP.tar.md5`
- Stock boot-only rollback AP SHA256:
  `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`

Existing pre-root evidence already proved the full boot partition matched stock
before the Magisk path; later disabled-vbmeta work was vbmeta-only and did not
touch boot.

## Magisk Tar Inspection

The operator-provided tar contains many AP members:

```text
dtbo.img.lz4
vendor_boot.img.lz4
super.img.lz4
persist.img.lz4
recovery.img.lz4
vbmeta.img
vbmeta_system.img.lz4
vm-bootsys.img.lz4
misc.bin.lz4
meta-data/
meta-data/fota.zip
boot.img
```

Only `boot.img` was extracted. The extracted `boot.img` is 96 MiB, same size as
stock boot, but has a different SHA:

```text
magisk_boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
stock_boot_sha256=4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae
```

String evidence in the extracted boot image includes:

```text
proca_magisk
/.magisk
KEEPVERITY=true
overlay.d
/init-ld.xz
overlay.d/sbin/stub.xz
```

## Boot-Only AP

Output directory:

```text
workspace/private/outputs/s22plus_magisk_root_boot_only/
```

Packaged artifacts:

```text
boot.img_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
boot.img.lz4_sha256=b33b63d9d2c56cbe10170820e88cf136be8fe9ad621a21752da19fdd9b642d31
ap_tar_sha256=27094526f33ef9bf4f0009089f242f5374913562538ccfbd60740ae60848b336
ap_tar_md5_sha256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
```

The AP tar contains exactly one member:

```text
boot.img.lz4
```

The LZ4 roundtrip decoded to the same SHA as `boot.img`:

```text
roundtrip_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

## Flash

Command shape:

```text
odin4 --reboot \
  -a workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5 \
  -d /dev/bus/usb/<redacted>
```

Odin4 transcript:

```text
Reboot into normal mode
Check file : workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5
Setup Connection
initializeConnection
Receive PIT Info
success getpit
Upload Binaries
boot.img.lz4
(31%)
(62%)
(93%)
(100%)
Close Connection
```

Result: Odin4 exited `0`.

## Android Boot Result

Android returned after the boot-only Magisk flash:

```text
sys.boot_completed=1
ro.bootloader=S906NKSS7FYG8
ro.build.version.incremental=S906NKSS7FYG8
ro.boot.boot_recovery=0
ro.boot.verifiedbootstate=orange
ro.boot.flash.locked=0
ro.boot.avb_version=1.2
```

## Magisk / Root State

Magisk package is installed:

```text
package:com.topjohnwu.magisk
versionName=30.7
versionCode=30700
```

MagiskSU is present:

```text
/product/bin/su
30.7:MAGISKSU
30700
```

Root proof is not complete yet. `su -c id` currently returns:

```text
Permission denied
```

Interpretation: the Magisk-patched boot image boots and MagiskSU is installed,
but ADB shell superuser access is denied by Magisk policy. The device screen is
locked, so the Magisk app's Superuser settings/request cannot be completed from
host-side ADB. The operator needs to unlock the phone, set Magisk Superuser
Access to `Apps and ADB` if needed, and allow `Shell`/ADB shell in Magisk.

No stock boot rollback has been run because the device boots Android normally and
the current blocker is Magisk superuser policy, not a boot failure.
