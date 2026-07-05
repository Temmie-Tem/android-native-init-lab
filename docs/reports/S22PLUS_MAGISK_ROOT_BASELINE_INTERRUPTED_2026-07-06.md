# S22+ Magisk Root Baseline Interrupted - 2026-07-06

## Scope

Attempt to start a Samsung S22+ `SM-S906N` / `g0q` Magisk root baseline after
the TWRP recovery-infra pass.

This unit was interrupted before completing root. Final state is a safe recovery
checkpoint:

- TWRP recovery remains installed and booted.
- Disabled vbmeta remains installed.
- Boot was restored to stock and verified byte-for-byte.
- Android root was not completed.

## External References

- Magisk latest release checked from official GitHub releases:
  `https://github.com/topjohnwu/Magisk/releases`
- Magisk official install guide:
  `https://topjohnwu.github.io/Magisk/install.html`

Reference interpretation:

- Latest release selected: `v30.7`
- Official Samsung direction is Magisk-app patching of AP/boot-family images.
- Custom recovery installation still exists but is documented by Magisk as
  deprecated and maintained with minimum effort.

## Local Magisk Artifact

- Path:
  `workspace/private/inputs/magisk/v30.7/Magisk-v30.7.apk`
- SHA256:
  `e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5`
- Version:
  `30.7`
- Version code:
  `30700`

## Pre-root Baseline

Before Magisk installation, TWRP recovery ADB was live:

```text
ro.twrp.version=3.7.0_12-1_afaneh92
ro.product.device=g0q
ro.product.name=twrp_g0q
ro.boot.verifiedbootstate=orange
```

The full boot partition readback matched stock:

```text
boot_before_sha=4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae
stock_boot_sha=4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae
boot_before_matches_stock=1
```

## Deprecated TWRP Zip Attempt

The Magisk APK was copied as a `.zip` and installed through TWRP:

```text
twrp install /tmp/Magisk-v30.7.zip
twrp_install_rc=0
```

The attempt changed boot:

```text
boot_after_twrp_install_sha=3543b810129a75df8875454d8a3b789dd172125e4e6908cf7c315770cb81d0d6
stock_boot_sha=4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae
boot_changed=1
```

Magisk markers were visible in the changed boot image and in TWRP cache state,
but Android did not complete boot; the device returned to TWRP recovery.

After operator direction, this deprecated route was abandoned in favor of the
Magisk APK patching path.

## Stock Boot Rollback

The pinned stock boot-only Odin AP was flashed:

- Path:
  `workspace/private/outputs/s22plus_native_init/odin4_stock_rollback_short/AP.tar.md5`
- SHA256:
  `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`

Odin result:

```text
boot.img.lz4
(100%)
odin_exit=0
```

Post-rollback boot partition readback matched stock exactly:

```text
boot_after_stock_rollback_sha=4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae
stock_boot_sha=4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae
boot_matches_stock=1
```

## TWRP / vbmeta Preservation

TWRP recovery and disabled vbmeta were not removed by the stock boot rollback.

Recovery readback still matched the pinned TWRP recovery image:

```text
device_recovery_prefix_sha=e4e1861760298da756d1d649029c33b4c953f12272ebda1705214da56245e036
local_recovery_sha=e4e1861760298da756d1d649029c33b4c953f12272ebda1705214da56245e036
```

Vbmeta readback still matched the pinned disabled vbmeta image:

```text
device_vbmeta_prefix_sha=d6b5803d2751aa6d675df90b2b6dd3c772f47acfe3e56ba19fc3e39da082f1a7
local_vbmeta_sha=d6b5803d2751aa6d675df90b2b6dd3c772f47acfe3e56ba19fc3e39da082f1a7
```

## Final State

Current state at pause:

- Device is in TWRP recovery.
- `ro.twrp.version=3.7.0_12-1_afaneh92`
- `ro.product.device=g0q`
- `ro.product.name=twrp_g0q`
- `ro.boot.verifiedbootstate=orange`
- `boot` equals stock `S906NKSS7FYG8` boot exactly.
- `recovery` equals pinned TWRP recovery prefix.
- `vbmeta` equals pinned disabled vbmeta prefix.

## Next

Continue with the Magisk APK patching path:

1. Boot Android from the verified stock boot state.
2. Install the pinned `Magisk-v30.7.apk`.
3. Use the Magisk app on the same device to patch stock `boot.img`.
4. Pull the patched image.
5. Package it as boot-only Odin AP.
6. Flash only boot.
7. Verify Android boot and `su -c id`.

