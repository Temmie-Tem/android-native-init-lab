# Native Init V3206 GPU Epic Completion Audit

## Summary

- Cycle: `V3206`
- Track: completion audit for the GPU compute/render bring-up epic via freedreno/KGSL-direct.
- Decision: `v3206-gpu-epic-completion-audit-pass`
- Result: PASS
- Device flash: no new flash in this audit unit.
- Current resident checked during audit: `A90 Linux init 0.11.30 (v3204-gpu-g5-kms-blit-probe)`.
- Scope boundary: this audit closes the chartered G0-to-G5 ladder. It does not claim EGL/blob bring-up, shader compiler bring-up, compute dispatch, triangle rendering, or zero-copy KMS/GPU buffer sharing.

## Objective Requirements Audit

| Requirement | Evidence | Verdict |
| --- | --- | --- |
| Do not start GPU until Video `0.11.0` promotion is closed. | Current project state records V3157 Video `0.11.0` promotion close before the GPU block was activated. The GPU build lineage starts after that promotion and the current resident is V3204. | Satisfied |
| Use freedreno/Mesa/KGSL-direct only; no proprietary Adreno blob/EGL/Bionic path. | GPU source contracts and reports emit `proprietary_blob_attempted=0`; G4/G5 source basis is KGSL UAPI plus Mesa/freedreno A6xx packet construction. | Satisfied |
| Keep work legitimate driver bring-up, not exploitation or kernel-security recon. | Reports and source tests cover normal KGSL open/context/gpuobj/submit paths only; no exploit, CVE, UAF, heap-spray, or memory-corruption path was added. | Satisfied |
| Enforce bright lines: no GDSC/regulator/PMIC/GPIO/power writes. | G0/G1/G2/G3/G4/G5 source and live outputs include no-power-write markers, including `gpu.g5.kms.power_write_attempted=0`; V3205 safety section records no forbidden partition or power-rail writes. | Satisfied |
| G0 diagnose the unbounded KGSL open hang using host-source reading and bounded probes only. | G0 reports identify the first-open hang as firmware visibility / first-open GPU-GMU cold-start blocking, not devnode creation. The clean path was firmware-class visibility preparation followed by bounded open. | Satisfied |
| G0 determine whether a bright-line-clean path exists. | V3184, V3186, and V3187 show bounded open success after firmware-class preparation with no selftest regression and without forbidden power writes. | Satisfied |
| Never run unbounded blocking open as a loop unit. | `gpu g0-open-probe` forks a child and parent enforces `--timeout-ms`; G1-G5 probes remain bounded and timeout-guarded. | Satisfied |
| G1 open a KGSL context, bounded and device-verifiable. | V3189 live: `gpu.g1.context.result=created-destroyed`, selftest remained `pass=12 warn=1 fail=0`. V3203/V3205 reruns also kept G1/G2/G3 prerequisites passing. | Satisfied |
| G2 allocate and mmap a GPU buffer, bounded and device-verifiable. | V3191 live: `gpu.g2.gpuobj.result=allocated-freed`. V3193 and V3205 live: `gpu.g2.gpuobj.result=mapped-unmapped`, `mmap_rc=0`, cleanup rc values zero. | Satisfied |
| G3 submit a noop command stream and get a fence, bounded and device-verifiable. | V3195 live: `gpu.g3.noop.result=submitted-fenced-retired`, with timestamp event and fence retirement. V3205 rerun showed `submit_rc=0`, `timestamp_event_rc=0`, `wait_rc=0`, `readtimestamp_rc=0`, `retired_timestamp=1`. | Satisfied |
| G4 render a solid fill or triangle into a buffer, bounded and device-verifiable. | V3203 live: `gpu.g4.fill.result=solid-fill-readback-ok`, `readback_verified=1`, `readback_mismatch_count=0`, `readback0..3=0xa5c3f00d`, no GPU fault signatures. | Satisfied |
| G5 blit the GPU-rendered buffer to existing KMS display `/dev/dri/card0`, bounded and device-verifiable. | V3205 live and this audit rerun: `gpu.g5.kms.result=kms-blit-presented`, `g4_readback_verified=1`, `blit_raw_pixel=0xa5c3f00d`, framebuffer `1080x2400`, `present_rc=0`, command END status ok. | Satisfied |
| Each rung must produce device-verifiable result. | Live reports V3184/V3186/V3187/V3189/V3191/V3193/V3195/V3203/V3205 plus the V3206 rerun provide command outputs, resident health checks, and selftest/fault-filter results. | Satisfied |
| Recoverable boot-partition flashes only, rollback `v2321`. | GPU live reports record boot-only flashing via `native_init_flash.py` and rollback-gate checks. V3205 records the V3204 boot SHA and no rollback needed. | Satisfied |

## Current Audit Evidence

- Managed serial bridge: running and connected with no immediate error after live checks.
- Resident: `A90 Linux init 0.11.30 (v3204-gpu-g5-kms-blit-probe)`.
- Current selftest: `pass=12 warn=1 fail=0`.
- Current G5 rerun: `gpu.g5.kms.result=kms-blit-presented`, `present_rc=0`, `g4_readback_verified=1`, `g4_readback0=0xa5c3f00d`, `blit_raw_pixel=0xa5c3f00d`, `total_elapsed_ms=18`, command status ok.
- Current GPU fault dmesg filter: `0` matches for page fault, CP opcode, A6xx hardware error, hang, or KGSL fault signatures.
- Static validation: `PYTHONPATH=tests python3 -m unittest` over the current G0 firmware path, G1, G2, G3, G4 CCU seqno, and G5 KMS blit source contracts ran `37` tests and passed.

## Important Boundaries

- The completed G5 path is `KGSL private buffer -> GPUOBJ_SYNC/readback -> CPU copy into KMS dumb framebuffer -> KMS present`.
- The completed G5 path is not zero-copy dmabuf or shared GPU/KMS plane scanout.
- The completed G4 path is solid fill through the A6xx A2D blit path, not triangle rasterization.
- These boundaries do not leave the chartered ladder incomplete because the GOAL ladder explicitly allowed "solid fill / single triangle" at G4 and "blit that GPU-rendered buffer to existing KMS display" at G5.

## Conclusion

The chartered GPU G0-to-G5 ladder is complete and device-proven within the stated bright lines. No further work is required for the objective as written. Any next GPU work should be a new explicitly chartered epic, such as zero-copy KMS sharing, triangle/shader bring-up, or compute dispatch.
