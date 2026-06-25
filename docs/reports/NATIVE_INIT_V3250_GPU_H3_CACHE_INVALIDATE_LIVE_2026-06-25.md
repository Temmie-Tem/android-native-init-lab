# Native Init V3250 GPU H3 Pre-Draw Cache Invalidate Live Validation

## Summary

- Cycle: `V3250`
- Artifact under test: `0.11.51 (v3249-gpu-h3-cache-invalidate-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3249_gpu_h3_cache_invalidate_probe.img`
- Boot SHA256: `167251fa73fa537c8a3c75716a7b7e3061605b62a0fd24494a11805d089c50a6`
- Result: `draw-retired-readback-unchanged`
- H4 triangle proof: `no`

## Flash Gate

- Rollback assets were present and matched the pinned SHA256 values:
  - `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `boot_linux_v48.img`: present, SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Pre-flash resident health was clean:
  - `version`: `0.11.50 (v3247-gpu-h3-rb-render-cntl-probe)`
  - `status`: `selftest: pass=12 warn=1 fail=0`
  - `selftest verbose`: `pass=12 warn=1 fail=0`
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py --from-native --expect-sha256 167251fa73fa537c8a3c75716a7b7e3061605b62a0fd24494a11805d089c50a6 --expect-version 0.11.51 ...`
- Flash/readback passed:
  - Local image SHA256: `167251fa73fa537c8a3c75716a7b7e3061605b62a0fd24494a11805d089c50a6`
  - Remote pushed image SHA256: `167251fa73fa537c8a3c75716a7b7e3061605b62a0fd24494a11805d089c50a6`
  - Boot block prefix SHA256: `167251fa73fa537c8a3c75716a7b7e3061605b62a0fd24494a11805d089c50a6`
- Post-flash health:
  - `version`: `0.11.51 (v3249-gpu-h3-cache-invalidate-probe)`
  - `status`: `selftest: pass=12 warn=1 fail=0`
  - `selftest verbose`: `pass=12 warn=1 fail=0`

## Live Probe

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Fresh-boot `gpu g0-status` showed the expected pre-materialization state:

- `fwclass_path=/vendor/firmware_mnt/image`
- `/dev/kgsl-3d0` missing
- SQE/GMU/ZAP firmware present in `/cache/a90-runtime/pkg/gpu-g0-fw`

The H3 materialize path ran firmware-class prep and created the KGSL devnode:

- `gpu.g0.materialize.fwclass_prepare_attempted=1`
- `gpu.g0.fwclass_prepare.result=ok`
- `gpu.g0.materialize.fwclass_prepare_rc=0`
- `gpu.g0.materialize.rc=0`

The V3249 candidate state was present:

- `gpu.h3.draw.scope=first-triangle-h3-cache-invalidate-rb-render-cntl-r0-output-mov-f32-shader`
- `gpu.h3.draw.cache_invalidate_source=mesa-freedreno-a6xx-fd6-emit-restore-fd6-cache-inv`
- `gpu.h3.draw.pre_draw_cache_invalidate=ccu-color,ccu-depth,cache`
- `gpu.h3.draw.pre_draw_cache_invalidate_events=0x19,0x18,0x31`
- `gpu.h3.draw.cp_set_marker=0x1`
- `gpu.h3.draw.rb_render_cntl=0x10`
- `gpu.h3.draw.rb_ccu_cntl=0x10000000`
- `gpu.h3.draw.pm4_dwords=240`
- `gpu.h3.draw.state_reg_writes=92`

The draw submitted and retired:

- `gpu.h3.draw.result=draw-retired-readback-unchanged`
- `gpu.h3.draw.submit_rc=0`
- `gpu.h3.draw.wait_rc=0`
- `gpu.h3.draw.retired_timestamp=1`
- `gpu.h3.draw.fence_poll_rc=1`
- `gpu.h3.draw.total_elapsed_ms=29`

Readback did not change:

- `gpu.h3.draw.readback_changed_count=0`
- `gpu.h3.draw.readback_first_changed_index=4294967295`
- `gpu.h3.draw.readback0=0x20202020`
- `gpu.h3.draw.readback_center=0x20202020`

Post-probe `selftest verbose` stayed `pass=12 warn=1 fail=0`. A focused dmesg filter found the expected `a640_zap` KGSL bring-up lines and an unrelated modem firmware timeout, but no KGSL/GPU fault, hang, snapshot, or GPU timeout signature.

## Conclusion

V3249/V3250 removes missing Mesa A6xx pre-draw `fd6_cache_inv()` as the primary H3 no-pixel root cause. The invalidate events are present, the draw retires cleanly, and the sysmem MRT readback still remains unchanged. H4 is still not reached.

The next bounded unit should continue with a narrower first-draw packet diff outside shader bytes, `RB_RENDER_CNTL`, and pre-draw cache invalidation. Good remaining targets are draw-state bootstrap such as `CP_SET_MODE`/`SP_UPDATE_CNTL`/restore state ordering, or another concrete compiler-emitted program/output state delta if it can be isolated before flashing.
