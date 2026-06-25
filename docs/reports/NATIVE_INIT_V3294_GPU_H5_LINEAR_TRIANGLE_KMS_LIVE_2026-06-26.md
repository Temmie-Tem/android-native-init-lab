# Native Init V3294 GPU H5 Linear Triangle KMS Live Validation

## Summary

- Cycle: `V3294`
- Decision: `v3294-gpu-h5-linear-triangle-kms-live-telemetry-pass`
- Artifact flashed: `workspace/private/inputs/boot_images/boot_linux_v3293_gpu_h5_linear_triangle_kms_probe.img`
- Artifact SHA256: `59b7973d99a7d5a44384d3390ad261231f9fab1b16ee21fce48b9f0537e89e70`
- Resident after flash: `A90 Linux init 0.11.72 (v3293-gpu-h5-linear-triangle-kms-probe)`
- Result: H5 linearized KMS telemetry pass. The H3 draw again retired with changed sysmem readback, the A6xx A2D stage
  copied the `RGBA8 tile6_3` color target into a linear RGBA8 buffer, and the parent KMS path presented that linear
  snapshot through `/dev/dri/card0`.
- Important caveat: this is an A2D-linearized presentation proof, not the final strict H4-style interior/exterior
  geometry proof. The linear destination was initialized with `0x20202020`, while the A2D copy resolved untouched clear
  areas to `0x00000000`, so `linear_readback_changed_count=16384` covers the full 128x128 buffer. The next bounded unit
  should zero-initialize the linear destination and count non-zero/interior plus zero exterior samples before claiming a
  literal triangle proof.

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

- Pre-flash resident: `A90 Linux init 0.11.71 (v3291-gpu-h5-triangle-kms-probe)`
- Pre-flash selftest: `pass=12 warn=1 fail=0`
- Post-flash resident: `A90 Linux init 0.11.72 (v3293-gpu-h5-linear-triangle-kms-probe)`
- Flash-helper status selftest: `pass=12 warn=1 fail=0`
- One immediate standalone `selftest verbose` attempt returned busy while the resident menu was active, then a `hide`
  attempt lost serial framing (`A90P1 END` marker not found with an `ATAT` fragment). The managed bridge was restarted,
  after which `version`, `hide`, and slow-mode selftest all passed.
- Post-restart selftest:

```text
selftest: pass=12 warn=1 fail=0
```

- Post-probe selftest:

```text
selftest: pass=12 warn=1 fail=0
```

## H5 Probe

Command:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow --timeout 120 \
  gpu h5-triangle-kms-probe --timeout-ms 5000 --materialize-devnode
```

Key telemetry:

- `gpu.h5.kms.scope=first-triangle-h5-a2d-linearized-h3-readback-to-kms-probe`
- `gpu.h5.kms.blit_mode=h3-private-buffer-a2d-linearized-snapshot-to-kms-dumb-framebuffer`
- `gpu.h5.kms.raw_tile_order_visualization=0`
- `gpu.h5.kms.linearized_tile6_3_a2d_blit=1`
- `gpu.h5.kms.materialize_rc=0`
- `gpu.h5.kms.child_collect_rc=0`
- `gpu.h5.kms.child_payload_bytes_read=66472`
- `gpu.h5.kms.child_payload_bytes_expected=66472`
- `gpu.h5.kms.h3_result=draw-retired-readback-changed`
- `gpu.h5.kms.h3_timed_out=0`
- `gpu.h5.kms.h3_child_killed=0`
- `gpu.h5.kms.h3_child_reaped=1`
- `gpu.h5.kms.h3_child_status=0x0`
- `gpu.h5.kms.h3_submit_rc=0`
- `gpu.h5.kms.h3_wait_rc=0`
- `gpu.h5.kms.h3_readback_sync_rc=0`
- `gpu.h5.kms.h3_readback_changed_count=672`
- `gpu.h5.kms.h3_readback_first_changed_index=9216`
- `gpu.h5.kms.h3_readback_first_changed_value=0xfb9802e6`
- `gpu.h5.kms.h3_color_flag_changed_count=32`
- `gpu.h5.kms.h3_linear_blit_attempted=1`
- `gpu.h5.kms.h3_linear_readback_changed_count=16384`
- `gpu.h5.kms.h3_linear_readback_first_changed_index=0`
- `gpu.h5.kms.h3_linear_readback_first_changed_value=0x0`
- `gpu.h5.kms.h3_linear_readback0=0x0`
- `gpu.h5.kms.h3_linear_readback_center=0xff00b900`
- `gpu.h5.kms.h3_total_elapsed_ms=32`
- `gpu.h5.kms.begin_frame_rc=0`
- `gpu.h5.kms.fb_initialized=1`
- `gpu.h5.kms.fb_width=1080`
- `gpu.h5.kms.fb_height=2400`
- `gpu.h5.kms.fb_stride=4352`
- `gpu.h5.kms.fb_id=207`
- `gpu.h5.kms.current_buffer=0`
- `gpu.h5.kms.blit_elapsed_ms=2`
- `gpu.h5.kms.blit_rc=0`
- `gpu.h5.kms.blit_rect=28,176,1024,1024`
- `gpu.h5.kms.blit_scale=8`
- `gpu.h5.kms.present_elapsed_ms=5`
- `gpu.h5.kms.present_rc=0`
- `gpu.h5.kms.result=h3-linear-readback-kms-presented`
- `gpu.h5.kms.total_elapsed_ms=58`

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

The focused tail contained no GPU fault, hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature. Only expected
first-use `a640_zap` load/reset lines matched the filter.

## Conclusion

The V3293 image is live on-device and proves the next H5 presentation step by telemetry: H3 still produces changed
readback, A2D can linearize that tiled/flagged render target into a CPU-readable snapshot, and KMS can present the
linear snapshot in `58ms` total with clean post-probe health.

Do not overclaim the geometry proof from this unit. The useful new evidence is `linear_readback_center=0xff00b900`
while `linear_readback0=0x0`, which strongly suggests the linearized surface contains localized triangle color. The
current success gate still counts every word as changed because the linear clear baseline differs from the previous
`0x20202020` sentinel. The next unit should make the proof strict by zero-clearing the linear buffer and reporting
`linear_nonzero_count`, first non-zero sample, fixed exterior-corner zero samples, and one or more expected interior
samples before moving to the after-triangle backlog.
