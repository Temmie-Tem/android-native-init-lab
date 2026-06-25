# Native Init V3201 GPU G4 CCU Flush Live Incident

## Summary

- Cycle: `V3201`
- Resident under test: `A90 Linux init 0.11.28 (v3200-gpu-g4-solid-fill-ccu-flush-probe)`
- Source/build commit: `d736f177 Build V3200 GPU G4 CCU flush probe`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3200_gpu_g4_solid_fill_ccu_flush_probe.img`
- Boot SHA256: `913f010d3bad4f1a8972d9e3f3f930e1a294e9daaf0f56b4c3d372388c2b11c5`
- Decision: V3200 live validation FAIL. Do not promote.

## Flash And Health

- Rollback gate: confirmed `v2321` rollback SHA, `v2237` fallback SHA, `v48` fallback presence, and TWRP recovery image before flash.
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py` only.
- Post-flash verify: `version` and `status` returned V3200 with `selftest pass=12 warn=1 fail=0`.
- Post-probe health: `selftest verbose` remained `pass=12 warn=1 fail=0`.

## Live Probe Results

- `gpu g0-fwclass-prepare`: initial host parse missed `A90P1 END`; retry with longer timeout passed, `gpu.g0.fwclass_prepare.result=ok`.
- `gpu g1-context-probe --timeout-ms 5000 --materialize-devnode`: PASS, `created-destroyed`, elapsed about `26ms`.
- `gpu g2-mmap-probe --timeout-ms 5000 --materialize-devnode`: PASS, `mapped-unmapped`, elapsed about `8ms`.
- `gpu g3-noop-submit-probe --timeout-ms 5000 --materialize-devnode`: PASS, `submitted-fenced-retired`, elapsed about `9ms`.
- `gpu g4-solid-fill-probe --timeout-ms 5000 --materialize-devnode`: FAIL, completed without timeout but returned `returned-error`.

## G4 Evidence

- PM4 source marker: `mesa-freedreno-a6xx-fd6-clear-buffer-cp-blit-a2d-ccu-color-flush`.
- Post-blit event marker: `pc_ccu_flush_color_ts`.
- `CACHE_INVALIDATE` marker: `excluded-after-v3197-incident`.
- `GPU_COMMAND` submitted successfully with timestamp `1`.
- KGSL timestamp wait returned success but took about `423ms`.
- Destination cache sync from GPU succeeded.
- Readback did not verify: `readback_verified=0`, `readback_mismatch_count=16`.
- First readback words stayed sentinel: `0x11111111`.
- PM4 dwords were `31`, confirming only the single CCU color flush event was restored over V3198.

## Dmesg

Focused post-G4 dmesg contained GPU hang/fault lines:

- `adreno_hang_int_callback| MISC: GPU hang detected`
- `init[654]: gpu fault ctx 1 ctx_type GL ts 1 status 00800005 rb 0100/0100 ib1 0000000500030000/0000`
- `gpu fault rb 2 rb sw r/w 0100/0100`

The focused filter did not show the V3197 `CP opcode` or `GPU PAGE FAULT` signature, but the GPU hang/fault is still a functional failure.

## Interpretation

- V3198 no-event removed the dmesg fault path but left readback at the sentinel.
- V3200 restoring only `PC_CCU_FLUSH_COLOR_TS` did not make the fill visible and introduced a GPU hang/fault.
- The next candidate should not promote V3200's CCU-flush-only tail. The remaining source-derived Mesa delta is the surrounding blit-mode/cache sequence: either a fuller Mesa post-blit clean sequence without `CACHE_INVALIDATE`, or `RB_DBG_ECO_CNTL` blit-mode handling if a safe device-specific value can be derived without inventing magic.

## Next

- Keep G4 bounded, child-only, and with G0/G1/G2/G3 prerequisites.
- Do not reintroduce `CACHE_INVALIDATE` (`0x31`) unless a separate source-backed reason appears.
- Prefer the next source unit as a narrow diagnostic variant, with live promotion requiring both readback success and an empty focused GPU fault filter.
