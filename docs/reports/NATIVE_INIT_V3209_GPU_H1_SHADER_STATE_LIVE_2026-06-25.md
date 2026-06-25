# Native Init V3209 GPU H1 Shader State Live Validation

## Summary

- Cycle: `V3209`
- Track: GPU first-triangle H1 live validation: A6xx shader processor state upload and `CP_LOAD_STATE6` shader preload, with no draw.
- Decision: `v3209-gpu-h1-shader-state-live-pass`
- Flashed image: `workspace/private/inputs/boot_images/boot_linux_v3208_gpu_h1_shader_state_probe.img`
- Boot SHA256: `ce17810bc9099a2e3b97cacc6299a552bc331355238f18b6b978ac0fb9e06c35`
- Init: `A90 Linux init 0.11.31 (v3208-gpu-h1-shader-state-probe)`

V3208 was flashed successfully and health-checked. The H1 shader-state probe
retired a no-draw KGSL command stream that allocates VS/FS shader GPU objects,
sets A6xx SP VS/PS state, emits `CP_LOAD_STATE6_GEOM` and
`CP_LOAD_STATE6_FRAG`, waits on the timestamp, reads the retired timestamp, and
cleans up without GPU fault signatures.

## Safety Gate

- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img` existed and
  matched SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img` existed and
  matched SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` existed.
- TWRP/recovery artifacts existed under `workspace/private/inputs/firmware/twrp/`.
- Pre-flash resident was V3204 with `selftest fail=0`.
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py --from-native`.
- Partition scope: boot image only.

## Flash Result

- Local artifact contained expected marker `0.11.31`.
- Local artifact SHA256 matched `ce17810bc9099a2e3b97cacc6299a552bc331355238f18b6b978ac0fb9e06c35`.
- Recovery handoff completed.
- Remote staging SHA256 matched the local artifact.
- Boot write completed through the checked helper.
- Boot readback prefix SHA256 matched `ce17810bc9099a2e3b97cacc6299a552bc331355238f18b6b978ac0fb9e06c35`.
- TWRP reboot completed.
- Post-boot cmdv1 verify passed for `version` and `status`.

## Health

After bridge resynchronization for post-flash ACM framing noise:

- `version`: `0.11.31 build=v3208-gpu-h1-shader-state-probe`.
- `status`: `BOOT OK`, selftest summary `pass=12 warn=1 fail=0`, transport ready.
- `selftest verbose`: `pass=12 warn=1 fail=0`; only `helpers` remained warn with `manifest=no`.

## H1 Probe Result

- G0 firmware class prepare: `gpu.g0.fwclass_prepare.result=ok`.
- H1 result: `gpu.h1.shader.result=shader-state-retired-no-draw`.
- Child process: exited cleanly, not killed, no timeout.
- KGSL path: `/dev/kgsl-3d0`, materialize requested and succeeded.
- Context create: `create_rc=0`, `context_id=1`.
- GPU objects: command, VS, and FS alloc/info/mmap succeeded.
- Shader payload size: VS `8` dwords, FS `8` dwords.
- PM4 stream: `34` dwords, `136` bytes.
- Packet basis: `CP_LOAD_STATE6_GEOM=0x32`, `CP_LOAD_STATE6_FRAG=0x34`.
- Sync: command `136` bytes, VS `32` bytes, FS `32` bytes.
- Submit: `submit_rc=0`, `submit_timestamp=1`.
- Fence/timestamp: `timestamp_event_rc=0`, `wait_rc=0`,
  `readtimestamp_rc=0`, `retired_timestamp=1`, fence poll returned readable.
- Cleanup: command/VS/FS GPUOBJ free and context destroy returned `0`.
- Timing: child total `29ms`; cmdv1 command duration `33ms`.

Post-probe checks:

- Post-H1 `selftest`: `pass=12 warn=1 fail=0`.
- GPU fault dmesg filter: `0` matches for page fault, CP opcode, A6xx fault/error,
  KGSL fault/hang/error, Adreno fault/hang/error, or GPU fault/hang signatures.

## Limits

- This is not a triangle proof.
- The shader payload is explicitly a no-execute placeholder; it is not yet a
  pass-through vertex shader or constant-color fragment shader.
- No draw, rasterizer, readback, KMS presentation, zero-copy dmabuf, EGL/GLES,
  OpenCL, proprietary blob, PMIC, regulator, GDSC, GPIO, or power-rail write was
  attempted in H1.
- The final V3208 boot image preserves the V3204 ramdisk contents and overlays
  only the new `/init`, helper, and `bin/a90_doomgeneric_private_engine_v3208`.

## Commands

```sh
sha256sum \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img \
  workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img \
  workspace/private/inputs/boot_images/boot_linux_v48.img

python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-version 0.11.31 \
  --expect-sha256 ce17810bc9099a2e3b97cacc6299a552bc331355238f18b6b978ac0fb9e06c35 \
  --expect-readback-sha256 ce17810bc9099a2e3b97cacc6299a552bc331355238f18b6b978ac0fb9e06c35 \
  workspace/private/inputs/boot_images/boot_linux_v3208_gpu_h1_shader_state_probe.img

A90CTL_INPUT_CHAR_DELAY_SEC=0.05 python3 workspace/public/src/scripts/revalidation/a90ctl.py \
  --timeout 50 --input-mode slow --hide-on-busy --retry-unsafe status

A90CTL_INPUT_CHAR_DELAY_SEC=0.05 python3 workspace/public/src/scripts/revalidation/a90ctl.py \
  --timeout 60 --input-mode slow --hide-on-busy --retry-unsafe selftest verbose

A90CTL_INPUT_CHAR_DELAY_SEC=0.05 python3 workspace/public/src/scripts/revalidation/a90ctl.py \
  --timeout 60 --input-mode slow --hide-on-busy --retry-unsafe \
  gpu g0-fwclass-prepare

A90CTL_INPUT_CHAR_DELAY_SEC=0.05 python3 workspace/public/src/scripts/revalidation/a90ctl.py \
  --timeout 90 --input-mode slow --hide-on-busy --retry-unsafe --allow-error \
  gpu h1-shader-state-probe --timeout-ms 5000 --materialize-devnode
```

## Conclusion

V3209 passes. H1 proves that the first-triangle path can safely preload bounded
A6xx shader/SP state through KGSL and retire the command stream. The next rung
should replace the placeholder shader payload with a real minimal hand-assembled
ir3 VS/FS pair and only then attempt a bounded draw.
