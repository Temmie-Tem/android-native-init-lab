# Native Init V3215 GPU H3 ir3-End Terminator Live Validation

## Summary

- Cycle: `V3215`
- Candidate under test: `V3214`
- Track: GPU first-triangle H3.1 live validation.
- Decision: `v3215-gpu-h3-ir3-end-terminator-live-boundary`
- Result: PASS for boot health and H3 command retirement; still NOT H4 triangle proof.
- Resident after validation: `A90 Linux init 0.11.34 (v3214-gpu-h3-ir3-end-terminator-probe)`
- Corrected boot image: `workspace/private/inputs/boot_images/boot_linux_v3214_gpu_h3_ir3_end_terminator_probe.img`
- Corrected boot SHA256: `bbdbefdfdf3bc1226b974f8919311f6a8b73bd82abc70824ecc2977d4842d500`

## Flash Sequence

An initial V3214 image was built at `67252224` bytes, larger than the 64MiB boot partition. Flashing it through the
checked helper failed during the recovery-side boot write with `No space left on device`, leaving the device in a failed
candidate state.

Recovery followed the invariant path immediately:

- Rolled back through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Rollback target: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Rollback booted and passed health: version/status/selftest all clean, `fail=0`.

The V3214 builder was then fixed before retry:

- Removed stale preserved-ramdisk `bin/a90_doomgeneric_private_engine_v3212` before packing V3214.
- Added a hard build-time boot-image size gate: `<= 67108864` bytes.
- Rebuilt image size: `66052096` bytes.
- Rebuilt SHA256: `bbdbefdfdf3bc1226b974f8919311f6a8b73bd82abc70824ecc2977d4842d500`.

The corrected image was flashed through `native_init_flash.py`, the helper readback SHA matched, the device rebooted to
system, and the resident version/status checks passed.

## Health Checks

- Pre-probe resident: `0.11.34 / v3214-gpu-h3-ir3-end-terminator-probe`.
- Pre-probe status: boot OK, storage mounted RW, transport ready, display `1080x2400`, selftest `pass=12 warn=1 fail=0`.
- Pre-probe `selftest verbose`: `pass=12 warn=1 fail=0`.
- Post-probe `selftest verbose`: `pass=12 warn=1 fail=0`.
- Post-probe status: boot OK, transport ready, display `1080x2400`, selftest `pass=12 warn=1 fail=0`.

Device-specific serial, storage UUID, and network endpoint values were intentionally omitted from this report.

## H3 Live Result

`gpu g0-fwclass-prepare` completed successfully on retry with cached firmware materialized and no ioctl/mmap work in that
prepare step.

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Key telemetry:

```text
gpu.h3.draw.scope=first-triangle-h3-draw-envelope-ir3-end-terminator
gpu.h3.draw.shader_payload=hand-assembled-ir3-end-only-no-full-compiler
gpu.h3.draw.ir3_end_opcode_hi=0x3000000
gpu.h3.draw.result=draw-retired-readback-unchanged
gpu.h3.draw.timed_out=0
gpu.h3.draw.open_rc=0
gpu.h3.draw.create_rc=0
gpu.h3.draw.submit_rc=0
gpu.h3.draw.submit_timestamp=1
gpu.h3.draw.wait_rc=0
gpu.h3.draw.wait_errno=0
gpu.h3.draw.retired_timestamp=1
gpu.h3.draw.readback_changed_count=0
gpu.h3.draw.readback0=0x20202020
gpu.h3.draw.readback_center=0x20202020
gpu.h3.draw.fence_poll_rc=1
gpu.h3.draw.cmd_free_rc=0
gpu.h3.draw.color_free_rc=0
gpu.h3.draw.event_free_rc=0
gpu.h3.draw.vs_free_rc=0
gpu.h3.draw.fs_free_rc=0
gpu.h3.draw.vertex_free_rc=0
gpu.h3.draw.destroy_rc=0
gpu.h3.draw.total_elapsed_ms=451
```

Latest bridge log scan found the expected prior H3 timeout entry from the earlier placeholder-shader run and the new V3214
retired result. No `GPU PAGE FAULT`, CP opcode fault, KGSL fault, Adreno hang, or GPU hang signature was found in the
current bridge log.

## Interpretation

V3214 materially advances H3: the same draw envelope that previously submitted but timed out now submits, fences, retires,
and cleans up. That strongly localizes the V3212/V3213 timeout to the non-terminating zero shader-stream boundary rather
than to KGSL context creation, BO allocation, VFD state emission, direct draw packet submission, or fence waiting itself.

This is still not a visible triangle. The terminator-only shader streams do not write clip-space position from the vertex
buffer and do not write a fragment color, so unchanged readback is expected. The next bounded unit should implement the
minimal real hand-assembled ir3 VS/FS payload:

- VS: fetch/pass through or otherwise write `gl_Position`.
- FS: write one constant color.
- Keep the existing H3 timeout guard, offscreen readback, and no-KMS boundary.
- Promote to H4 only after interior pixels change and exterior pixels remain clear.

## Safety

- Boot partition only; no forbidden partition write.
- Flash path only: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Rollback baseline was confirmed and used successfully after the oversized image failure.
- No PMIC, regulator, GDSC, GPIO, power-rail, proprietary blob, EGL, OpenCL, or full Mesa compiler path was attempted.
- KGSL work stayed child-bounded with timeout/reap cleanup.
