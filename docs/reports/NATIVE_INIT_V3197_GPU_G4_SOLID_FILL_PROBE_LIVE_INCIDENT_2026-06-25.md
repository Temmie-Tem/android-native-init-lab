# Native Init V3197 GPU G4 Solid Fill Probe Live Incident

## Summary

- Cycle: `V3197`
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3196_gpu_g4_solid_fill_probe.img`
- Boot SHA256: `8cc402691a7c08a760f53a4fe3104a61f84dd844cf6f817ec5dd54c6af6ff430`
- Resident after flash: `A90 Linux init 0.11.26 (v3196-gpu-g4-solid-fill-probe)`
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash result: PASS, boot partition write/readback SHA matched, V3196 `version/status` verified.
- Device health after incident: `selftest: pass=12 warn=1 fail=0`; rollback condition was not triggered.
- Decision: G4 live validation FAIL due GPU dmesg fault/hang despite readback success.

## Gate Evidence

- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img` SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img` SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` existed and was hashed.
- TWRP/recovery image existed at `workspace/private/inputs/firmware/twrp/recovery.img`.
- Pre-flash resident V3194 health: `selftest: pass=12 warn=1 fail=0`.

## Functional Validation

- `gpu g0-fwclass-prepare`: `gpu.g0.fwclass_prepare.result=ok`.
- `gpu g1-context-probe --timeout-ms 5000 --materialize-devnode`: `created-destroyed`, timed out `0`.
- `gpu g2-mmap-probe --timeout-ms 5000 --materialize-devnode`: `mapped-unmapped`, timed out `0`.
- `gpu g3-noop-submit-probe --timeout-ms 5000 --materialize-devnode`: `submitted-fenced-retired`, timed out `0`.
- `gpu g4-solid-fill-probe --timeout-ms 5000 --materialize-devnode`: command output returned `solid-fill-readback-ok`, timed out `0`, `readback_verified=1`, `readback_mismatch_count=0`, and readback words `0xa5c3f00d`.

## Incident Evidence

Focused dmesg after G4 contained KGSL fault/hang lines:

- `a6xx_cp_hw_err_callback| CP opcode error interrupt | opcode=0x00000031`
- `kgsl_iommu_fault_handler| GPU PAGE FAULT: addr = 470460000 pid= 653 name=init`
- `kgsl_iommu_fault_handler| context=gfx3d_user ... (write translation fault)`
- `kgsl_iommu_fault_handler| FAULTING BLOCK: CP`
- `adreno_hang_int_callback| MISC: GPU hang detected`
- `init[653]: gpu fault ctx 1 ctx_type GL ts 1 status 00800005`

The fault address pattern and opcode `0x31` point at the V3196 post-blit event-write tail, especially emitting timestamp-style/cache events as one-dword no-address `CP_EVENT_WRITE` packets. The solid fill itself completed, but the command stream tail was not clean enough to promote.

## Next Action

- Do not promote V3196 G4 live.
- Build a follow-up candidate that removes the post-blit flush/invalidate event writes and uses a minimal source-derived sequence: A2D state writes, `CP_BLIT(BLIT_OP_SCALE)`, `CP_WAIT_FOR_IDLE`, KGSL timestamp wait, and destination `GPUOBJ_SYNC FROM_GPU`.
- Keep G4 bounded, child-only, and with the same rollback/health gates before any follow-up flash.
