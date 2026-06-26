# Native Init V3310 GPU 2D D1 Bbox Checkerboard Live

## Summary

- Cycle: `V3310`
- Track: GPU accelerated 2D D1, bbox-local checkerboard texture readback.
- Candidate: `workspace/private/inputs/boot_images/boot_linux_v3310_gpu_2d_d1_bbox_checkerboard_probe.img`
- Boot SHA256: `77c26859a449e73abf96bbb66c8087e687ba8cc9301ed9d41c885419008c15f3`
- Init after flash: `A90 Linux init 0.11.82 (v3310-gpu-2d-d1-bbox-checkerboard-probe)`
- Result: PASS

## Flash Gate

- Built via `workspace/public/src/scripts/revalidation/build_native_init_boot_v3310_gpu_2d_d1_bbox_checkerboard_probe.py`.
- Flashed only through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Local image size: `66117632` bytes, within the `67108864` byte boot partition limit.
- Rollback image checks before flash:
  - `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `boot_linux_v48.img`: present, SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
  - TWRP recovery image present, SHA256 `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`
- Flash helper verified local SHA, pushed image SHA, boot partition readback SHA, and post-boot native `version`/`status`.

## Health

- Post-flash `version`: `0.11.82 build=v3310-gpu-2d-d1-bbox-checkerboard-probe`.
- Post-flash `status`: `BOOT OK`, display path present, SD runtime mounted read-write.
- Post-flash explicit `selftest`: `pass=12 warn=1 fail=0`.
- Post-probe explicit `selftest`: `pass=12 warn=1 fail=0`.
- Post-probe `status`: `BOOT OK`, `selftest: pass=12 warn=1 fail=0`.
- Narrow kernel fault grep for `kgsl.*fault|gpu.*fault|adreno.*fault|context.*fault|page fault|gpu.*hang|kgsl.*hang|iommu.*fault` returned no matching fault lines.

## D1 Probe

Command:

```text
gpu d1-texture-checkerboard-probe --timeout-ms 5000 --materialize-devnode
```

The first attempt returned `busy` because the auto menu was active. After `hide`, the same command completed successfully.

Key output:

```text
gpu.d1.texture.result=bbox-checkerboard-readback-pass
gpu.d1.texture.viewport_scale_mode=inherited-default-clip-space-bbox
gpu.d1.texture.viewport_scale_xy=64,64
gpu.d1.texture.viewport_offset_xy=64,64
gpu.d1.texture.pm4_dwords=409
gpu.d1.texture.state_reg_writes=121
gpu.d1.texture.vfd_reg_writes=20
gpu.d1.texture.submit_rc=0
gpu.d1.texture.wait_rc=0
gpu.d1.texture.retired_timestamp=1
gpu.d1.texture.readback_sync_rc=0
gpu.d1.texture.readback_changed_count=2048
gpu.d1.texture.linear_readback_changed_count=16384
gpu.d1.texture.linear_readback_nonzero_count=16384
gpu.d1.texture.linear_readback_bbox_found=1
gpu.d1.texture.linear_readback_bbox=0,0,127,127
gpu.d1.texture.texture_dark_count=8192
gpu.d1.texture.texture_light_count=8192
gpu.d1.texture.texture_other_count=0
gpu.d1.texture.texture_sample_count=64
gpu.d1.texture.texture_sample_match_count=64
gpu.d1.texture.texture_sample_mismatch_count=0
gpu.d1.texture.texture_bbox_sample_count=64
gpu.d1.texture.texture_bbox_sample_match_count=64
gpu.d1.texture.texture_bbox_sample_mismatch_count=0
gpu.d1.texture.cmd_free_rc=0
gpu.d1.texture.linear_free_rc=0
gpu.d1.texture.texture_free_rc=0
gpu.d1.texture.destroy_rc=0
gpu.d1.texture.close_rc=0
gpu.d1.texture.total_elapsed_ms=39
```

## Interpretation

- V3310 closes the D1 checkerboard pattern gate: the textured draw submitted, retired, linearized, and the readback matched all 64 expected checkerboard samples.
- The measured bbox is now the full `128x128` target, not just the earlier `64x64` quadrant from V3306/V3307.
- Dark/light counts are exactly balanced at `8192/8192`, and `texture_other_count=0`, so the linear readback is a clean checkerboard.
- The V3308/V3309 forced viewport path is no longer needed and was removed from the D1 PM4 stream.

## Prior Evidence Folded In

- V3306/V3307 proved that the D1 texture path could draw real checkerboard pixels but only partially passed the original full-target gate.
- V3308 moved the forced viewport override into the D1 PM4 path and blanked the draw.
- V3309 tried positive coordinates plus zero-offset viewport and also blanked.
- V3310 restored the inherited clip-space viewport path and added bbox-local sample telemetry; live results show the restored path now satisfies both bbox-local and full-target sample checks.

## Safety Boundary

- KGSL userspace draw/readback only.
- No KMS present, backlight/PWM/PMIC/regulator/GDSC/GPIO writes, panel re-init, proprietary blob writes, or forbidden partition writes.
- Device mutation was limited to the boot image through the checked flash helper.
