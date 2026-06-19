# NATIVE_INIT_V2918_BADAPPLE_PLAYER_HUD_FLASH_HEALTH_2026-06-20

## Scope

Flash and health-check the V2917 Bad Apple Player HUD boot image. This unit does
not seed or play the 150 MiB V2903 stream; it only verifies that the new image
boots, keeps the control transport, and exposes the Player HUD command surface.

## Safety gates

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flashed partition: `boot` only
- Rollback target confirmed before flash:
  - `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
  - SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallbacks confirmed before flash:
  - `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
  - SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `workspace/private/inputs/boot_images/boot_linux_v48.img`
  - SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Pre-flash resident baseline: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Pre-flash selftest: `pass=11 warn=1 fail=0`

## Artifact

- Image: `workspace/private/inputs/boot_images/boot_linux_v2917_badapple_player_hud.img`
- SHA256: `495fc109704d7a4c2bccd7e9f836a8f96db854cfe171c7bb38e225e7ac749daf`
- Expected version: `A90 Linux init 0.10.38 (v2917-badapple-player-hud)`
- Build report: `docs/reports/NATIVE_INIT_V2917_BADAPPLE_PLAYER_HUD_SOURCE_BUILD_2026-06-20.md`

## Flash command

```sh
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
    workspace/private/inputs/boot_images/boot_linux_v2917_badapple_player_hud.img \
    --from-native \
    --expect-sha256 495fc109704d7a4c2bccd7e9f836a8f96db854cfe171c7bb38e225e7ac749daf \
    --expect-version 'A90 Linux init 0.10.38 (v2917-badapple-player-hud)' \
    --expect-android-magic \
    --verify-protocol auto
```

## Flash result

- Local image Android boot magic: pass
- Local marker check: pass
- Recovery handoff from native bridge: pass
- ADB recovery ready: pass
- ADB push throughput: `85.7 MB/s`
- Remote pushed image SHA256: matched
- Boot partition write: pass
- Boot partition readback prefix SHA256: matched
- Reboot to native init: pass
- Flash helper native verify: pass
- Total flash elapsed: `64.631s`

## Post-flash health

`version`:

```text
A90 Linux init 0.10.38 (v2917-badapple-player-hud)
version: 0.10.38 build=v2917-badapple-player-hud
```

`status`:

```text
boot: BOOT OK shell 5.0s
helpers: entries=7 warn=1 fail=0 manifest=no
transport.serial=ready
transport.ncm=ready
transport.tcpctl=ready
storage: sd present=yes mounted=yes expected=yes rw=yes
```

`selftest`:

```text
selftest: pass=12 warn=1 fail=0 duration=36ms entries=13
```

## Player HUD surface

`video status` exposes the new cache/demo surface:

```text
video.status.next_cache=video cache [status|verify|play] SHA256 [--trust-cache] [--present pageflip] [--layout full|player-hud] | video cache preset [badapple|badapple-scale] play [--trust-cache]
video.status.next_demo=video demo [badapple|badapple-scale] [status|verify|play] [--trust-cache]
```

`video demo badapple status` correctly resolves the V2903 asset identity and fails
only because the stream has not yet been seeded to SD cache:

```text
video.demo.asset_id=badapple-480x360-full-v2903
video.cache.preset.sha256=9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0
video.stream.error=manifest-read-failed rc=-2
video.cache.error=manifest-invalid rc=-2
```

## Decision

- `v2917-badapple-player-hud` is bootable and resident after this unit.
- Control channels survived the flash and boot.
- Selftest remains `fail=0`.
- The V2903 Bad Apple stream still needs the SD-cache seed step before playback.
- No rollback was needed.
