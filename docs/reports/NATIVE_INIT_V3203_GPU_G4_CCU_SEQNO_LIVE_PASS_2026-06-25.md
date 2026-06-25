# Native Init V3203 GPU G4 CCU Seqno Live Pass

## Summary

- Cycle: `V3203`
- Track: live validation of V3202 GPU G4 KGSL A6xx A2D solid-fill/readback probe.
- Source build commit: `275e5334 Build V3202 GPU G4 CCU seqno probe`.
- Flashed init: `A90 Linux init 0.11.29 (v3202-gpu-g4-solid-fill-ccu-seqno-probe)`.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3202_gpu_g4_solid_fill_ccu_seqno_probe.img`.
- Boot SHA256: `2574f594da4e8e06c3ed4c3541ab112c71c2476aa7490b5d8634dd860c0ed763`.
- Result: PASS.

## Flash Gate

- Rollback precondition: v2321 and v2237 rollback SHA256 values matched the AGENTS.md contract; v48 and TWRP recovery image were present.
- Pre-flash resident health: V3200 was reachable over the managed bridge and `selftest verbose` passed with `pass=12 warn=1 fail=0`.
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py` only.
- Flash verification: local image SHA, recovery-pushed image SHA, and boot block prefix SHA all matched `2574f594da4e8e06c3ed4c3541ab112c71c2476aa7490b5d8634dd860c0ed763`.
- Post-flash native verify: `version` and `status` returned V3202 with `status=ok`.
- Rollback performed: no.

## Health

- Post-flash `status`: V3202 resident booted, storage/runtime ready, serial transport ready, native selftest summary `pass=12 warn=1 fail=0`.
- A first standalone `selftest verbose` retry saw a serial framing parse miss, but the selftest body already reported `pass=12 warn=1 fail=0`; an immediate retry returned a normal `A90P1 END` marker and `status=ok`.
- Post-GPU `selftest verbose`: `pass=12 warn=1 fail=0`.

## Functional Validation

- `gpu g0-fwclass-prepare`: PASS, `gpu.g0.fwclass_prepare.result=ok`.
- `gpu g1-context-probe --timeout-ms 5000 --materialize-devnode`: PASS, `gpu.g1.context.result=created-destroyed`, `total_elapsed_ms=27`.
- `gpu g2-mmap-probe --timeout-ms 5000 --materialize-devnode`: PASS, `gpu.g2.gpuobj.result=mapped-unmapped`, `total_elapsed_ms=8`.
- `gpu g3-noop-submit-probe --timeout-ms 5000 --materialize-devnode`: PASS, `gpu.g3.noop.result=submitted-fenced-retired`, `total_elapsed_ms=9`.
- `gpu g4-solid-fill-probe --timeout-ms 5000 --materialize-devnode`: PASS, `gpu.g4.fill.result=solid-fill-readback-ok`, `timed_out=0`, `child_killed=0`, `wait_rc=0`, `readtimestamp_rc=0`, `readback_sync_rc=0`, `readback_verified=1`, `readback_mismatch_count=0`, `readback0..3=0xa5c3f00d`, `event_free_rc=0`, `total_elapsed_ms=10`.

## GPU Fault Filter

- Post-G4 dmesg fault filter matched 0 lines for:
  - `GPU PAGE FAULT`
  - `CP opcode`
  - `a6xx_cp_hw_err`
  - `adreno_hang`
  - `GPU hang`
  - `fault ctx`
  - `KGSL.*fault`

## Conclusion

V3202 fixes the V3198/V3201 split: the G4 private KGSL A2D `CP_BLIT` output is now visible in CPU readback without GPU hang/fault signatures. The effective change is the Mesa-style four-payload-dword `PC_CCU_FLUSH_COLOR_TS` timestamp event targeting a dedicated KGSL object in the command objlist.

This validates a private GPU object solid-fill/readback path only. It does not validate triangle rendering, compute dispatch, KMS/display handoff, or broad framebuffer integration.
