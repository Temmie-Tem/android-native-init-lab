# S22+ Stock Vbmeta Recovery-Loop Fix - 2026-07-06

## Scope

Live minimal rollback of only `vbmeta` to the stock `S906NKSS7FYG8` image after
the S22+ repeatedly returned to TWRP recovery despite stock `boot` being
installed.

This unit did not flash `boot`, `vendor_boot`, `recovery`, BL, CP, CSC, modem,
EFS, or userdata.

## Preflight

Starting state:

```text
adb_state=recovery
ro.twrp.version=3.7.0_12-1_afaneh92
ro.boot.bootloader=S906NKSS7FYG8
ro.boot.em.model=SM-S906N
ro.boot.sales_code=SKC
```

Prepared stock-vbmeta-only AP:

```text
path=workspace/private/outputs/s22plus_stock_vbmeta_rollback/AP.tar.md5
sha256=fdf42fb913ac82bba7414d41a2995300c9bc56d31e7cddf907b487e7b2ae707b
contents=vbmeta.img.lz4
```

Before flashing, TWRP root readback still proved:

```text
boot_sha=4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae
stock_boot_sha=4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae

vendor_boot_sha=096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
stock_vendor_boot_sha=096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
```

The installed `vbmeta` at that point was still the older disabled payload from
the previous TWRP unit, not the stock FYG8 vbmeta.

## Flash

The device was rebooted to download mode from TWRP recovery. Odin4 saw Samsung
download mode and flashed only the AP package above:

```text
odin4 --reboot \
  -a workspace/private/outputs/s22plus_stock_vbmeta_rollback/AP.tar.md5 \
  -d /dev/bus/usb/<redacted>
```

Odin4 transcript:

```text
Reboot into normal mode
Check file : workspace/private/outputs/s22plus_stock_vbmeta_rollback/AP.tar.md5
Setup Connection
initializeConnection
Receive PIT Info
success getpit
Upload Binaries
vbmeta.img.lz4
(100%)
Close Connection
```

## Result

Android userspace appeared 17 seconds after the Odin-triggered normal reboot:

```text
adb_seen_after_sec=17
adb_state=device
ro_twrp=
ro_boot_recovery=0
ro_product_device=g0q
ro_product_model=SM-S906N
ro_build_fingerprint=samsung/g0qksx/g0q:15/AP3A.240905.015.A2/S906NKSS7FYG8:user/release-keys
ro_boot_verifiedbootstate=orange
```

Boot completion was already set on first poll:

```text
sys.boot_completed=1
dev.bootcomplete=1
```

Android shell is not rooted after this rollback:

```text
uid=2000(shell)
su: inaccessible or not found
```

Post-boot block-device readback from Android shell was intentionally not used as
evidence because normal Android `shell` lacks permission to read these block
devices:

```text
dd: /dev/block/by-name/boot: Permission denied
dd: /dev/block/by-name/vendor_boot: Permission denied
dd: /dev/block/by-name/vbmeta: Permission denied
```

## Interpretation

PASS.

The recovery loop was not caused by the stock `boot.img` rollback failing.
Stock `boot` and `vendor_boot` were already present before this unit. Replacing
only the mismatched disabled `vbmeta` with stock FYG8 `vbmeta` was sufficient to
boot Android 15 stock userspace.

The previous strongest hypothesis is now confirmed: the recovery loop was caused
by the old generic disabled-vbmeta payload being incompatible with the
`SM-S906N` / `S906NKSS7FYG8` Android 15 stack.

## Final State

At the end of this unit:

- Android stock userspace is booted.
- `sys.boot_completed=1`.
- `boot` and `vendor_boot` were stock-matched before the `vbmeta` flash.
- `vbmeta` was flashed back to stock FYG8.
- TWRP recovery partition was not changed in this unit.
- Recovery boot after stock-vbmeta restore was not tested.
- Magisk/root is not installed.

## Next

If the next target is stock stability, keep this state and do not boot recovery
until deciding whether to restore stock recovery too.

If the next target is root, use the Magisk APK patching path from Android
userspace. Do not reuse the old generic disabled `vbmeta`.

