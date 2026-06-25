# Native Init V3233 GPU H3 Static Context Live

## Summary

- Cycle: `V3233`
- Flashed build: `A90 Linux init 0.11.43 (v3232-gpu-h3-static-context-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3232_gpu_h3_static_context_probe.img`
- Boot SHA256: `08392c39698d52df7794fca1f36f9e2ce14d4fa88e27ad2cae2f644e84dae02d`
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Result: SAFE RETIRED DRAW, NO H4 PIXELS

## Flash Gate

- Rollback images verified before flash:
  - `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `boot_linux_v48.img`: present
- Recovery artifacts present: TWRP recovery image and TAR.
- Pre-flash resident: V3230, `selftest: pass=12 warn=1 fail=0`.
- Flash command used `--expect-sha256` and `--expect-version`; boot readback SHA matched the local image SHA.
- Post-flash native-init verify: V3232 version/status OK.

## Live Probe

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Key result:

```text
gpu.h3.draw.scope=first-triangle-h3-static-context-mov-f32-shader
gpu.h3.draw.static_context_source=mesa-freedreno-a6xx-fd6-emit-static-context-regs
gpu.h3.draw.vpc_so_override=0x1
gpu.h3.draw.sp_reg_prog_id_3=0xfcfc
gpu.h3.draw.result=draw-retired-readback-unchanged
gpu.h3.draw.pm4_dwords=223
gpu.h3.draw.state_reg_writes=88
gpu.h3.draw.submit_rc=0
gpu.h3.draw.wait_rc=0
gpu.h3.draw.retired_timestamp=1
gpu.h3.draw.readback_changed_count=0
gpu.h3.draw.readback0=0x20202020
gpu.h3.draw.readback_center=0x20202020
gpu.h3.draw.total_elapsed_ms=31
```

## Health

- Post-probe selftest: `pass=12 warn=1 fail=0`.
- GPU fault filter: no KGSL/Adreno/GMU/SMMU fault, hang, snapshot, or iommu fault signature was observed after the probe.
- One selftest attempt was retried because serial input was corrupted by console noise; the retry completed normally.

## Conclusion

V3232 correctly programs the intended static-context delta and remains safe: the command retires, frees all BOs, and
does not regress device health. It still does not produce changed pixels, so H4 is not reached. This removes the tested
Mesa static-context no-op/disable group as the primary blocker. The next bounded unit should revisit the hand-assembled
shader output contract or compare the remaining Mesa first-draw packet stream for a smaller shader-output/RB linkage
delta before claiming triangle rendering.
