# Native Init V3296 GPU H5 Strict Triangle KMS Live Validation

## Summary

- Cycle: `V3296`
- Decision: `v3296-gpu-h5-strict-triangle-kms-live-pass`
- Artifact flashed: `workspace/private/inputs/boot_images/boot_linux_v3295_gpu_h5_strict_triangle_kms_probe.img`
- Artifact SHA256: `f20b4ff3ab76fd0c8d854ede72f13079cf0f90fa248dad059768647fa8a7e4ae`
- Resident after flash: `A90 Linux init 0.11.73 (v3295-gpu-h5-strict-triangle-kms-probe)`
- Result: PASS. The strict H5 command proved a linearized first-triangle surface with non-zero interior color,
  zero exterior corner samples, and successful KMS presentation.

## Flash Gate

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Rollback image verified before flash:
  `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
  SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallback verified before flash:
  `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
  SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Final fallback verified before flash:
  `workspace/private/inputs/boot_images/boot_linux_v48.img`
  SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Recovery/TWRP image verified before flash:
  `workspace/private/inputs/firmware/twrp/recovery.img`
  SHA256 `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`
- Flash verification matched the local image SHA, remote staged image SHA, and boot-block readback-prefix SHA.

## Health

- Pre-flash resident: `A90 Linux init 0.11.72 (v3293-gpu-h5-linear-triangle-kms-probe)`
- Pre-flash selftest: `pass=12 warn=1 fail=0`
- Post-flash resident: `A90 Linux init 0.11.73 (v3295-gpu-h5-strict-triangle-kms-probe)`
- Flash-helper status selftest: `pass=12 warn=1 fail=0`
- Standalone post-flash selftest: `pass=12 warn=1 fail=0`
- Post-probe selftest: `pass=12 warn=1 fail=0`

## H5 Probe

The first H5 command attempt was blocked by the auto menu and left trailing tokens in the shell input. `hide` cleared the
menu, then the command was rerun cleanly:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow --timeout 120 \
  gpu h5-triangle-kms-probe --timeout-ms 5000 --materialize-devnode
```

Key telemetry:

- `gpu.h5.kms.scope=first-triangle-h5-a2d-linearized-strict-sample-kms-probe`
- `gpu.h5.kms.raw_tile_order_visualization=0`
- `gpu.h5.kms.linearized_tile6_3_a2d_blit=1`
- `gpu.h5.kms.materialize_rc=0`
- `gpu.h5.kms.child_collect_rc=0`
- `gpu.h5.kms.child_payload_bytes_read=66504`
- `gpu.h5.kms.child_payload_bytes_expected=66504`
- `gpu.h5.kms.h3_result=draw-retired-readback-changed`
- `gpu.h5.kms.h3_submit_rc=0`
- `gpu.h5.kms.h3_wait_rc=0`
- `gpu.h5.kms.h3_readback_sync_rc=0`
- `gpu.h5.kms.h3_readback_changed_count=672`
- `gpu.h5.kms.h3_readback_first_changed_index=9216`
- `gpu.h5.kms.h3_readback_first_changed_value=0xfb9802e6`
- `gpu.h5.kms.h3_color_flag_changed_count=32`
- `gpu.h5.kms.h3_linear_blit_attempted=1`
- `gpu.h5.kms.h3_linear_readback_changed_count=2016`
- `gpu.h5.kms.h3_linear_readback_first_changed_index=8256`
- `gpu.h5.kms.h3_linear_readback_first_changed_value=0xff00b900`
- `gpu.h5.kms.h3_linear_readback_nonzero_count=2016`
- `gpu.h5.kms.h3_linear_readback_first_nonzero_index=8256`
- `gpu.h5.kms.h3_linear_readback_first_nonzero_value=0xff00b900`
- `gpu.h5.kms.h3_linear_readback0=0x0`
- `gpu.h5.kms.h3_linear_readback_center=0xff00b900`
- `gpu.h5.kms.h3_linear_readback_corner_tr=0x0`
- `gpu.h5.kms.h3_linear_readback_corner_bl=0x0`
- `gpu.h5.kms.h3_linear_readback_corner_br=0x0`
- `gpu.h5.kms.h3_linear_center_nonzero=1`
- `gpu.h5.kms.h3_linear_exterior_corners_zero=1`
- `gpu.h5.kms.strict_linear_triangle_sample_proof=1`
- `gpu.h5.kms.h3_total_elapsed_ms=33`
- `gpu.h5.kms.begin_frame_rc=0`
- `gpu.h5.kms.fb_width=1080`
- `gpu.h5.kms.fb_height=2400`
- `gpu.h5.kms.fb_stride=4352`
- `gpu.h5.kms.blit_elapsed_ms=2`
- `gpu.h5.kms.blit_rc=0`
- `gpu.h5.kms.blit_rect=28,176,1024,1024`
- `gpu.h5.kms.blit_scale=8`
- `gpu.h5.kms.present_elapsed_ms=2`
- `gpu.h5.kms.present_rc=0`
- `gpu.h5.kms.result=h3-linear-readback-kms-presented`
- `gpu.h5.kms.total_elapsed_ms=55`

The command also printed:

```text
gpu-h5-triangle-kms: presented framebuffer 1080x2400 on crtc=133
```

## Kernel Log Check

Focused dmesg tail filter:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow --timeout 60 \
  busybox sh -c "dmesg | tail -n 250 | grep -Ei 'kgsl|gpu|adreno|a6xx|a640|iommu|smmu|fault|hang|snapshot|timeout|opcode|page fault|gmu' || true"
```

The focused tail contained no GPU fault, hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature. It showed the
expected first-use `a640_zap` load/reset lines and an unrelated modem firmware wait timeout.

## Conclusion

V3296 closes the H0-H5 first-triangle ladder by telemetry: the GPU submits and retires a 3D triangle draw, CPU readback
shows changed tiled sysmem plus color-flag output, A2D linearization produces a localized non-zero triangle region
(`2016` non-zero pixels) with a non-zero center and zero exterior corners, and the verified linear snapshot presents on
the existing `/dev/dri/card0` KMS framebuffer. No proprietary blob path, power write, zero-copy scanout, or forbidden
partition path was used.
