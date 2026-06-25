# Native Init V3283 GPU H3 RB_DBG_ECO Live Validation

## Summary

- Cycle: `V3283`
- Track: GPU H3 first-triangle A640 device-DB RB_DBG_ECO init-magic live probe.
- Decision: `v3283-gpu-h3-rb-dbg-eco-live-no-pixel`
- Result: H3 draw still retires with unchanged color readback and unchanged color-flag buffer.
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3282_gpu_h3_rb_dbg_eco_probe.img`
- Boot SHA256: `f2afd2eda2b8632fff582e79c3defe5b9520ecb63d36e0498f3fced945fa9879`
- Init: `A90 Linux init 0.11.67 (v3282-gpu-h3-rb-dbg-eco-probe)`

## Flash Gate

- Rollback `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Final fallback `boot_linux_v48.img`: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Recovery image `workspace/private/inputs/firmware/twrp/recovery.img`: `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash verification: local SHA, pushed remote SHA, and boot readback-prefix SHA matched the V3282 boot SHA.

## Post-Flash Health

- Version: `0.11.67 build=v3282-gpu-h3-rb-dbg-eco-probe`
- Post-flash selftest: `pass=12 warn=1 fail=0`
- Post-probe selftest: `pass=12 warn=1 fail=0`
- Serial note: one immediate post-flash verbose selftest attempt lost framing after prompt noise, then slow-mode `version` and `selftest` completed cleanly.

## H3 Probe Results

The V3282 image emits only the first A640 device-DB magic candidate:

- `gpu.h3.draw.a640_magic_mode=rb-dbg-eco-only`
- `gpu.h3.draw.rb_dbg_eco_cntl=0x4100000`
- `gpu.h3.draw.rb_dbg_eco_cntl_reg=0x8e04`
- `gpu.h3.draw.a640_init_magic_reg_writes=1`
- `gpu.h3.draw.a640_magic_deferred_nonzero_block=sp_chicken_bits,tpl1_dbg_eco,vpc_dbg_eco,rb_rbp,pc_power,vfd_power,uche_unknown_0e12`
- `gpu.h3.draw.rb_render_cntl=0x10010`
- `gpu.h3.draw.rb_mrt0_buf_info=0x330`
- `gpu.h3.draw.color_flag_buffer_pitch=0x4001`
- `gpu.h3.draw.pm4_dwords=313`
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
- `total_elapsed_ms=31`

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

Focused post-probe dmesg filter over the recent tail for `kgsl`, `gpu`, `adreno`, `a6xx`, `a640`, `iommu`, `smmu`, `fault`, `hang`, `snapshot`, `timeout`, `opcode`, and `page fault` produced no matching diagnostic lines. The command exited with grep status `1` and only emitted expected linker-configuration warnings from the Android userland launcher.

## Conclusion

`RB_DBG_ECO_CNTL=0x04100000` alone is not sufficient to make the H3 first-triangle draw write pixels on this A640 path. The no-pixel signature is unchanged from V3281: the draw submits, waits, and retires, but both the color readback and the cffdump-style color-flag buffer remain untouched.

The next bounded unit should follow the operator's probe order step 2: add the rest of the non-zero A640 device-DB init-magic block (`SP_CHICKEN_BITS`, `TPL1_DBG_ECO_CNTL`, `VPC_DBG_ECO_CNTL`, `RB_RBP_CNTL`, `PC_MODE_CNTL`, `PC_POWER_CNTL`, `VFD_POWER_CNTL`, and `UCHE_UNKNOWN_0E12`) while keeping `RB_CCU_CNTL` separate.
