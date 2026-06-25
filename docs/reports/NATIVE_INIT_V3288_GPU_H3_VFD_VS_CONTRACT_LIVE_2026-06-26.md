# Native Init V3288 GPU H3 VFD/VS Contract Live Validation

## Summary

- Cycle: `V3288`
- Track: GPU H3 first-triangle cffdump-shaped VFD/VS contract live validation.
- Decision: `v3288-gpu-h3-vfd-vs-contract-live-no-pixel`
- Result: H3 draw still retires with unchanged color readback and unchanged color-flag buffer.
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3287_gpu_h3_vfd_vs_contract_probe.img`
- Boot SHA256: `560538eb253daa013971a2492575f80797082b3359d51e159c3a76e990aa9255`
- Init: `A90 Linux init 0.11.69 (v3287-gpu-h3-vfd-vs-contract-probe)`

## Flash Gate

- Rollback `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Final fallback `boot_linux_v48.img`: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Recovery image `workspace/private/inputs/firmware/twrp/recovery.img`: `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash verification: local SHA, pushed remote SHA, and boot readback-prefix SHA matched the V3287 boot SHA.

## Post-Flash Health

- Pre-flash resident: `0.11.68 (v3284-gpu-h3-a640-magic-block-probe)`, `selftest pass=12 warn=1 fail=0`.
- Post-flash resident: `0.11.69 (v3287-gpu-h3-vfd-vs-contract-probe)`.
- Flash-helper health check: version/status passed.
- Post-flash selftest: `pass=12 warn=1 fail=0`.
- Post-probe selftest: `pass=12 warn=1 fail=0`.
- Serial note: one parallel post-flash `version/status/selftest` attempt caused bridge lock contention and a truncated `version` transaction. Sequential `version` and `selftest` reruns completed cleanly.

## H3 Probe Results

The V3287 image emits the cffdump-shaped VFD/VS input contract while preserving the V3284/V3285 A640 non-zero magic block:

- `gpu.h3.draw.shader_payload=verified-ir3-vs-r1xyzw-to-r2-position-preserve-r0-varying-and-cffdump-bary-fs`
- `gpu.h3.draw.vfd_cntl_0=0x303`
- `gpu.h3.draw.vfd_cntl_1=0xfcfcfc09`
- `gpu.h3.draw.vfd_fetch_instr0=0xc8200000`
- `gpu.h3.draw.vfd_fetch_instr1=0xc8200200`
- `gpu.h3.draw.vfd_fetch_instr2=0x44c00400`
- `gpu.h3.draw.vfd_dest_cntl0=0xf`
- `gpu.h3.draw.vfd_dest_cntl1=0x4f`
- `gpu.h3.draw.vfd_dest_cntl2=0x81`
- `gpu.h3.draw.vertex_stride=36`
- `gpu.h3.draw.vertex_bytes=108`
- `gpu.h3.draw.pm4_dwords=335`
- `gpu.h3.draw.state_reg_writes=121`
- `gpu.h3.draw.vfd_reg_writes=20`

Run 1:

- `submit_rc=0`
- `wait_rc=0`
- `retired_timestamp=1`
- `readback_sync_rc=0`
- `readback_changed_count=0`
- `readback0=0x20202020`
- `readback_center=0x20202020`
- `color_flag_changed_count=0`
- `color_flag0=0x0`
- `result=draw-retired-readback-unchanged`
- `total_elapsed_ms=30`

Run 2:

- `submit_rc=0`
- `wait_rc=0`
- `retired_timestamp=1`
- `readback_sync_rc=0`
- `readback_changed_count=0`
- `readback0=0x20202020`
- `readback_center=0x20202020`
- `color_flag_changed_count=0`
- `color_flag0=0x0`
- `result=draw-retired-readback-unchanged`
- `total_elapsed_ms=11`

## Kernel Log Check

Focused post-probe dmesg filter over the recent tail for `kgsl`, `gpu`, `adreno`, `a6xx`, `a640`, `iommu`, `smmu`, `fault`, `hang`, `snapshot`, `timeout`, `opcode`, `page fault`, and `gmu` produced no GPU fault, hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature.

The matching lines were:

- an unrelated modem firmware state wait timeout;
- expected first-use `a640_zap` subsystem get/load/reset lines.

## Conclusion

The coherent cffdump-shaped VFD/VS input contract is not sufficient to make the H3 first-triangle draw write pixels on this KGSL-direct sysmem path. The no-pixel signature is unchanged from V3285: the draw submits, waits, and retires, but both the color readback and cffdump-style color-flag buffer remain untouched.

This removes the VFD/VS input contract mismatch as the primary no-pixel cause. The next bounded live unit should test the smaller direct-sysmem-compatible blend/output group from the V3286 diff: `SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and `RB_MRT[0].BLEND_CONTROL=0x08040804`.
