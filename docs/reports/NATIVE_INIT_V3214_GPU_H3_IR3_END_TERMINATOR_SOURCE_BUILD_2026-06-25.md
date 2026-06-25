# Native Init V3214 GPU H3 ir3-End Terminator Source Build

## Summary

- Cycle: `V3214`
- Track: GPU first-triangle H3.1: replace the zero shader payload with a hand-encoded ir3 `end` terminator stream, then retry the same draw envelope.
- Decision: `v3214-gpu-h3-ir3-end-terminator-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3214_gpu_h3_ir3_end_terminator_probe.img`
- Boot SHA256: `bbdbefdfdf3bc1226b974f8919311f6a8b73bd82abc70824ecc2977d4842d500`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3212_gpu_h3_draw_envelope_probe.img`
- Init: `A90 Linux init 0.11.34 (v3214-gpu-h3-ir3-end-terminator-probe)`

## Included Delta

- Keeps the V3212 H3 command envelope, VFD state, direct non-indexed `CP_DRAW_INDX_OFFSET`, timeout guard, and readback telemetry.
- Replaces the VS/FS zero payload with `end + nop + nop + nop` (`0x0300000000000000` followed by three 64-bit NOPs) so the shader stream is terminable.
- Removes the stale V3212 DOOM engine from the preserved ramdisk before packing V3214 and gates the final boot image at 64MiB to protect the boot partition.
- This is a retire-boundary diagnostic, not H4 triangle proof: the VS still does not write clip-space position and the FS still does not write a shaded color.

## Source Basis

- Mesa ir3 ISA documentation: `https://docs.mesa3d.org/drivers/freedreno/ir3-notes.html`.
- Mesa ir3 cat0 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat0.xml`.
- Mesa ir3 root ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3.xml`.
- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3214 builder and focused H3 source test.
- `unittest`: V3214 GPU H3 ir3-end source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3214 identity plus ir3-end H3 markers.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-ir3-end-terminator-probe-candidate`.
