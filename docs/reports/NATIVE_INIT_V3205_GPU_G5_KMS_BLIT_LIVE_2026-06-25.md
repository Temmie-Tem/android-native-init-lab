# Native Init V3205 GPU G5 KMS Blit Live Pass

## Summary

- Cycle: `V3205`
- Track: GPU G5 KGSL A6xx A2D solid-fill readback copied into the existing KMS dumb-buffer display path.
- Decision: `v3205-gpu-g5-kms-blit-live-pass`
- Result: PASS
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3204_gpu_g5_kms_blit_probe.img`
- Boot SHA256: `3cd91db7aa26fd85c03e91e97596ba005dea1f58f04d28047de2c89fc223b8ed`
- Init after flash: `A90 Linux init 0.11.30 (v3204-gpu-g5-kms-blit-probe)`
- Rollback triggered: no

## Flash Gate

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash scope: boot partition only.
- Rollback baseline `boot_linux_v2321_usb_clean_identity_rodata.img` SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img` SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` exists.
- TWRP recovery image exists.
- Native flash verification completed for the exact V3204 boot SHA above.

## Live Validation

Pre-G5 resident health:

- `version`: `A90 Linux init 0.11.30 (v3204-gpu-g5-kms-blit-probe)`
- `status`: selftest `pass=12 warn=1 fail=0`; SD runtime mounted read-write; transport ready. Device identifiers, IPs, and storage UUIDs are intentionally omitted.

GPU ladder sanity checks reran as short slow-input commands to avoid serial prompt corruption:

- G2 mmap probe: `gpuobj.result=mapped-unmapped`, `timed_out=0`, `mmap_rc=0`, `free_rc=0`, `destroy_rc=0`, `total_elapsed_ms=9`, command status ok.
- G3 noop submit probe: `noop.result=submitted-fenced-retired`, `submit_rc=0`, `timestamp_event_rc=0`, `wait_rc=0`, `readtimestamp_rc=0`, `retired_timestamp=1`, `total_elapsed_ms=10`, command status ok.
- G4 solid fill probe: `fill.result=solid-fill-readback-ok`, `timed_out=0`, `child_killed=0`, `readback_verified=1`, `readback_mismatch_count=0`, `readback0..3=0xa5c3f00d`, `total_elapsed_ms=10`, command status ok.

G5 KMS blit probe:

- Command: `gpu kms-blit-probe --timeout-ms 5000 --materialize-devnode`
- Result: `gpu.g5.kms.result=kms-blit-presented`
- KGSL source: `g4-solid-fill-pc-ccu-flush-color-ts-seqno`
- Blit mode: KGSL private-buffer readback copied into existing KMS dumb framebuffer.
- Zero-copy attempted: `0`
- Parent KGSL open/ioctl attempted: `0` / `0`
- G4 child result: `solid-fill-readback-ok`
- G4 readback verified: `1`
- G4 readback mismatch count: `0`
- G4 raw pixel: `0xa5c3f00d`
- KMS framebuffer: `1080x2400`, stride `4352`, framebuffer id allocated.
- Blit rectangle: `180,840,720,720`
- Blit raw pixel: `0xa5c3f00d`
- `begin_frame_rc=0`, `blit_rc=0`, `present_rc=0`
- Timing: G4 child `9ms`, begin frame `3ms`, blit `1ms`, present `2ms`, total `19ms`
- Command END: `status=ok`

Post-G5 checks:

- GPU fault dmesg filter: `0` matches for page fault, CP opcode, A6xx hardware error, hang, or KGSL fault signatures.
- Post-G5 `selftest verbose`: `pass=12 warn=1 fail=0`.

## Safety Notes

- No forbidden partition was touched.
- No PMIC, GDSC, regulator, GPIO, or power-rail write was attempted.
- No proprietary Adreno blob, EGL, Bionic userspace, shader compiler, compute grid, or triangle pipeline was attempted.
- This rung proves a bounded KGSL-direct render/readback result can be visibly presented through the existing KMS path. It does not prove zero-copy GPU/KMS buffer sharing.

## Conclusion

V3205 live validation passes. The G5 rung successfully presents a verified G4 GPU-produced raw pixel value through KMS without GPU fault signatures or selftest regression. The next GPU rung can either make this KMS bridge more visual/diagnostic or move toward a more direct shared-buffer path, but the current proven baseline is still readback-to-KMS-copy rather than zero-copy.
