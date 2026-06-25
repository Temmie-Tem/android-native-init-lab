# Native Init V3211 GPU H2 3D State Live Validation

## Summary

- Cycle: `V3211`
- Candidate under test: `V3210` / `A90 Linux init 0.11.32 (v3210-gpu-h2-3d-state-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3210_gpu_h2_3d_state_probe.img`
- Boot SHA256: `0d84aeda172b114ac2eaae30b413b3ef3909af2cd9df78c0e981dc5993e9e2c1`
- Source-build report: `docs/reports/NATIVE_INIT_V3210_GPU_H2_3D_STATE_PROBE_SOURCE_BUILD_2026-06-25.md`
- Result: PASS
- Device action: boot partition flash only, through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Safety boundary: no forbidden partition writes, no power rail writes, no proprietary Adreno blob, no draw, no shader execution, no KMS presentation.

## Flash Gate

- Rollback baseline `boot_linux_v2321_usb_clean_identity_rodata.img` present and SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img` present and SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` present.
- TWRP recovery artifacts present.
- Pre-flash resident: `A90 Linux init 0.11.31 (v3208-gpu-h1-shader-state-probe)`.
- Pre-flash health: `status` rc=0, `selftest verbose` pass=12 warn=1 fail=0.

## Flash Result

- `native_init_flash.py` accepted the exact local image SHA256 `0d84aeda172b114ac2eaae30b413b3ef3909af2cd9df78c0e981dc5993e9e2c1`.
- Remote pushed image SHA256 matched the local SHA256.
- Boot partition prefix readback SHA256 matched the expected SHA256.
- Device rebooted to native init and `native_init_flash.py` verify passed `version`/`status` rc=0.
- Post-flash resident: `A90 Linux init 0.11.32 (v3210-gpu-h2-3d-state-probe)`.
- Post-flash health: `selftest verbose` pass=12 warn=1 fail=0.

## H2 Probe

Command:

```text
gpu h2-3d-state-probe --timeout-ms 5000 --materialize-devnode
```

Key output:

```text
gpu.h2.state.result=3d-state-retired-no-draw
gpu.h2.state.timed_out=0
gpu.h2.state.child_killed=0
gpu.h2.state.open_rc=0
gpu.h2.state.create_rc=0
gpu.h2.state.materialize_rc=0
gpu.h2.state.color_width=128
gpu.h2.state.color_height=128
gpu.h2.state.color_stride=512
gpu.h2.state.color_bytes=65536
gpu.h2.state.color_format=0x4b
gpu.h2.state.pm4_dwords=115
gpu.h2.state.state_reg_writes=62
gpu.h2.state.cmd_size=460
gpu.h2.state.submit_rc=0
gpu.h2.state.timestamp_event_rc=0
gpu.h2.state.wait_rc=0
gpu.h2.state.readtimestamp_rc=0
gpu.h2.state.retired_timestamp=1
gpu.h2.state.fence_poll_rc=1
gpu.h2.state.cmd_free_rc=0
gpu.h2.state.color_free_rc=0
gpu.h2.state.destroy_rc=0
gpu.h2.state.close_rc=0
gpu.h2.state.total_elapsed_ms=27
```

The H2 command stream retired a no-draw fixed-function 3D state packet stream with 62 state-register writes into a private 128x128 u32 offscreen object. This does not prove triangle rasterization or shader execution; those remain H3/H4.

## Post-Probe Health

- `selftest verbose`: pass=12 warn=1 fail=0.
- GPU fault filter:

```text
dmesg | grep -Ei 'page fault|cp opcode|a6xx.*(fault|error)|kgsl.*(fault|hang|error)|adreno.*(fault|hang|error)|gpu (fault|hang)' | wc -l
0
```

## Next

- H3: bind a 3-vertex buffer, emit the non-indexed `CP_DRAW_INDX_OFFSET`, wait/readtimestamp, and read back the offscreen target.
- H4: verify interior/exterior triangle pixels.
- H5: present verified output to `/dev/dri/card0`.
