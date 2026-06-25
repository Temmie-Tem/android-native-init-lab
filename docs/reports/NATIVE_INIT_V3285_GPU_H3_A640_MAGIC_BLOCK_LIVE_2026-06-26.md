# Native Init V3285 GPU H3 A640 Magic Block Live Validation

## Summary

- Cycle: `V3285`
- Track: GPU H3 first-triangle A640 device-DB non-zero init-magic block live probe.
- Decision: `v3285-gpu-h3-a640-magic-block-live-no-pixel`
- Result: H3 draw still retires with unchanged color readback and unchanged color-flag buffer.
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3284_gpu_h3_a640_magic_block_probe.img`
- Boot SHA256: `7eacd6670856beaeea681d1df6deb3169bcee68fe730c8dcb050b6fdc28b6572`
- Init: `A90 Linux init 0.11.68 (v3284-gpu-h3-a640-magic-block-probe)`

## Flash Gate

- Rollback `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Final fallback `boot_linux_v48.img`: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Recovery image `workspace/private/inputs/firmware/twrp/recovery.img`: `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash verification: local SHA, pushed remote SHA, and boot readback-prefix SHA matched the V3284 boot SHA.

## Post-Flash Health

- Version: `0.11.68 build=v3284-gpu-h3-a640-magic-block-probe`
- Flash-helper health check: version/status passed.
- Post-flash selftest: `pass=12 warn=1 fail=0`
- Post-probe selftest: `pass=12 warn=1 fail=0`
- Serial note: one immediate standalone post-flash selftest attempt lost framing (`A90P1 END marker not found`) after a truncated `cmdv1 selftest` input and prompt noise. A slow-mode `version` resync and selftest rerun completed cleanly.

## H3 Probe Results

The V3284 image emits the A640/a6xx_gen2 non-zero device-DB magic block:

- `gpu.h3.draw.a640_magic_mode=nonzero-block`
- `gpu.h3.draw.a640_init_magic_reg_writes=9`
- `gpu.h3.draw.rb_dbg_eco_cntl=0x4100000`, reg `0x8e04`
- `gpu.h3.draw.sp_chicken_bits=0x420`, reg `0xae03`
- `gpu.h3.draw.tpl1_dbg_eco_cntl=0x8000`, reg `0xb600`
- `gpu.h3.draw.vpc_dbg_eco_cntl=0x2000000`, reg `0x9600`
- `gpu.h3.draw.rb_rbp_cntl=0x1`, reg `0x8e01`
- `gpu.h3.draw.pc_mode_cntl_magic=0x1f`, reg `0x9804`
- `gpu.h3.draw.pc_power_cntl=0x1`, reg `0x9805`
- `gpu.h3.draw.vfd_power_cntl=0x1`, reg `0xa0f8`
- `gpu.h3.draw.uche_unknown_0e12=0x1`, reg `0x0e12`
- `gpu.h3.draw.pm4_dwords=329`
- `gpu.h3.draw.state_reg_writes=121`
- `gpu.h3.draw.vfd_reg_writes=14`

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
- `total_elapsed_ms=32`

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
- `total_elapsed_ms=12`

## Kernel Log Check

Focused post-probe dmesg filter over the recent tail for `kgsl`, `gpu`, `adreno`, `a6xx`, `a640`, `iommu`, `smmu`, `fault`, `hang`, `snapshot`, `timeout`, `opcode`, `page fault`, and `gmu` produced no GPU fault, hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature.

The matching lines were:

- an unrelated modem firmware state wait timeout;
- expected first-use `a640_zap` subsystem get/load/reset lines.

## Conclusion

The full non-zero A640/a6xx_gen2 device-DB magic block is not sufficient to make the H3 first-triangle draw write pixels on this KGSL-direct sysmem path. The no-pixel signature is unchanged from V3281 and V3283: the draw submits, waits, and retires, but both the color readback and cffdump-style color-flag buffer remain untouched.

This removes the A640 magic-reg block as the primary no-pixel cause. The next bounded unit should stop probing isolated magic/register guesses and switch to the definitive packet-level path: capture or assemble a real Mesa/freedreno A640 sysmem single-triangle `.rd`/cffdump stream and diff it against current H3, admitting only remaining direct-sysmem-compatible packet groups.
