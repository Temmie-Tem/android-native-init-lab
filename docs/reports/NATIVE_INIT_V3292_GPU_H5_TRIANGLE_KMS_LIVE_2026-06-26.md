# Native Init V3292 GPU H5 Triangle KMS Live Validation

## Summary

- Cycle: `V3292`
- Decision: `v3292-gpu-h5-triangle-kms-live-telemetry-pass`
- Artifact flashed: `workspace/private/inputs/boot_images/boot_linux_v3291_gpu_h5_triangle_kms_probe.img`
- Artifact SHA256: `eea6c10b184ea19ce7c391899dae26c4bbf8b8ed4ac828409355b1d789a67f95`
- Resident after flash: `A90 Linux init 0.11.71 (v3291-gpu-h5-triangle-kms-probe)`
- Result: H5 KMS telemetry pass. The command returned the H3 readback snapshot from the KGSL child, blitted it into the
  parent-owned KMS dumb framebuffer, and presented it through `/dev/dri/card0` with `present_rc=0`.
- Visual note: host-side telemetry proves KMS presentation; operator panel visual confirmation is still the final human
  checkpoint because this run has no camera/display capture.

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

- Pre-flash resident: `A90 Linux init 0.11.70 (v3289-gpu-h3-blend-output-probe)`
- Pre-flash selftest: `pass=12 warn=1 fail=0`
- Post-flash resident: `A90 Linux init 0.11.71 (v3291-gpu-h5-triangle-kms-probe)`
- Flash-helper status selftest: `pass=12 warn=1 fail=0`
- One immediate standalone post-flash selftest attempt lost protocol framing due serial `AT` fragment noise (`A90P1 END`
  not found), but bridge and `version` immediately passed and the slow-mode selftest retry completed cleanly:

```text
selftest: pass=12 warn=1 fail=0 duration=34ms entries=13
```

- Post-probe selftest:

```text
selftest: pass=12 warn=1 fail=0 duration=34ms entries=13
```

## H5 Probe

Command:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow --timeout 120 \
  gpu h5-triangle-kms-probe --timeout-ms 5000 --materialize-devnode
```

Key telemetry:

- `gpu.h5.kms.result=h3-readback-kms-presented`
- `gpu.h5.kms.materialize_rc=0`
- `gpu.h5.kms.child_collect_rc=0`
- `gpu.h5.kms.child_payload_bytes_read=66368`
- `gpu.h5.kms.child_payload_bytes_expected=66368`
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
- `gpu.h5.kms.h3_total_elapsed_ms=31`
- `gpu.h5.kms.begin_frame_rc=0`
- `gpu.h5.kms.fb_initialized=1`
- `gpu.h5.kms.fb_width=1080`
- `gpu.h5.kms.fb_height=2400`
- `gpu.h5.kms.fb_stride=4352`
- `gpu.h5.kms.blit_rc=0`
- `gpu.h5.kms.blit_rect=28,176,1024,1024`
- `gpu.h5.kms.blit_scale=8`
- `gpu.h5.kms.present_rc=0`
- `gpu.h5.kms.total_elapsed_ms=53`

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

The V3291 H5 path is live by telemetry: the H3 readback proof surface is captured from the KGSL child, copied into a
parent-owned KMS dumb framebuffer, and presented on `/dev/dri/card0`. This moves H5 from source-only to device-proven
KMS presentation by serial evidence.

The remaining quality checkpoint is visual: because the source is still raw `RGBA8 tile6_3` readback, the first pass may
appear as a raw tile-order proof surface rather than a geometrically untiled triangle. If the operator confirms the
panel shows the proof surface, H5 presentation is satisfied. If a literal centered triangle is required, the next bounded
unit should add a tile/format conversion or change the H3 render target to a KMS-friendly linear presentation buffer.
