# Native Init V3290 GPU H3 Blend Output Live Validation

## Summary

- Cycle: `V3290`
- Decision: `v3290-gpu-h3-blend-output-live-first-pixels`
- Artifact flashed: `workspace/private/inputs/boot_images/boot_linux_v3289_gpu_h3_blend_output_probe.img`
- Artifact SHA256: `10e43f8fc8c751774d830b797b783f3a058f10efaeeccab5d0dd57f806e6f34d`
- Resident after flash: `A90 Linux init 0.11.70 (v3289-gpu-h3-blend-output-probe)`
- Result: H3 submitted, retired, and changed the sysmem readback plus the color-flag buffer. This reaches the H4
  first-pixel/readback proof. H5 visible KMS presentation is still pending.

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

- Pre-flash resident: `A90 Linux init 0.11.69 (v3287-gpu-h3-vfd-vs-contract-probe)`
- Pre-flash selftest: `pass=12 warn=1 fail=0`
- Post-flash resident: `A90 Linux init 0.11.70 (v3289-gpu-h3-blend-output-probe)`
- Post-flash status selftest: `pass=12 warn=1 fail=0`
- Post-probe selftest:

```text
cmdv1 selftest
A90P1 BEGIN seq=8 cmd=selftest argc=1 flags=0x0
selftest: pass=12 warn=1 fail=0 duration=38ms entries=13
[done] selftest (0ms)
A90P1 END seq=8 cmd=selftest rc=0 errno=0 duration_ms=0 flags=0x0 status=ok
```

One immediate standalone selftest attempt after flash lost serial framing (`ftest`), but the body still reported
`pass=12 warn=1 fail=0`; the slow-mode rerun above completed cleanly.

## H3 Probe

Command:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow --timeout 120 \
  gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Run 1:

- `gpu.h3.draw.result=draw-retired-readback-changed`
- `submit_rc=0`
- `wait_rc=0`
- `retired_timestamp=1`
- `readback_sync_rc=0`
- `readback_sync_errno=0`
- `readback_changed_count=672`
- `readback_first_changed_index=9216`
- `readback_first_changed_value=0xfb9802e6`
- `readback0=0x20202020`
- `readback_center=0x20202020`
- `color_flag_changed_count=32`
- `color_flag_first_changed_index=256`
- `color_flag_first_changed_value=0x1010101`
- `color_flag0=0x0`
- `pm4_dwords=335`
- `state_reg_writes=121`
- `vfd_reg_writes=20`
- `sp_blend_cntl=0x100`
- `rb_blend_cntl=0xffff0100`
- `rb_mrt0_blend_control=0x8040804`
- `total_elapsed_ms=30`

Run 2:

- `gpu.h3.draw.result=draw-retired-readback-changed`
- `submit_rc=0`
- `wait_rc=0`
- `retired_timestamp=1`
- `readback_changed_count=672`
- `readback_first_changed_index=9216`
- `readback_first_changed_value=0xfb9802e6`
- `readback0=0x20202020`
- `readback_center=0x20202020`
- `color_flag_changed_count=32`
- `color_flag_first_changed_index=256`
- `color_flag_first_changed_value=0x1010101`
- `color_flag0=0x0`
- `total_elapsed_ms=12`

## Kernel Log Check

Focused dmesg tail filter:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow --timeout 60 \
  busybox sh -c "dmesg | tail -n 250 | grep -Ei 'kgsl|gpu|adreno|a6xx|a640|iommu|smmu|fault|hang|snapshot|timeout|opcode|page fault|gmu' || true"
```

The focused tail contained no GPU fault, hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature. The only matched
kernel line was the unrelated WLAN firmware wait timeout:

```text
[  136.160079] [3:  kworker/u16:7:  255] firmware wlan!qca_cld!WCNSS_qcom_cfg.ini: _request_firmware_load: firmware state wait timeout: rc = -110
```

## Conclusion

The direct-sysmem-compatible blend/output group was the load-bearing H3 no-pixel fix:

- `SP_BLEND_CNTL=0x100`
- `RB_BLEND_CNTL=0xffff0100`
- `RB_MRT[0].BLEND_CONTROL=0x08040804`

The A640 magic block and the cffdump-shaped VFD/VS contract were necessary context but not sufficient by themselves.
With the blend/output group added, H3 now retires and writes visible non-clear data into the offscreen sysmem readback
region and the color-flag buffer. H4 is reached. The next bounded unit is H5: present or blit the proven offscreen
triangle result to the KMS display path, or first inspect/reposition the changed region if a centered visible triangle
is required.
