# Native Init V3213 GPU H3 Draw Envelope Live

## Summary

- Cycle: `V3213`
- Track: live validation of V3212 GPU first-triangle H3 draw-envelope probe.
- Source build: `v3212-gpu-h3-draw-envelope-probe` / init `0.11.33`.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3212_gpu_h3_draw_envelope_probe.img`.
- Boot SHA256: `a2c7e223b30d361716363e2b8a37b45cecce41b50a35690c2265d0aa6499b938`.
- Result: PARTIAL. V3212 flashed and health-checked cleanly; H3 submitted a direct draw packet but did not retire before the KGSL timestamp wait timeout.

## Flash Gate

- Rollback precondition: matched required rollback SHA256 values for `boot_linux_v2321_usb_clean_identity_rodata.img` (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) and `boot_linux_v2237_supplicant_terminate_poll.img` (`b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`); `boot_linux_v48.img` was present; TWRP recovery artifacts were present under `workspace/private/inputs/firmware/twrp/`.
- Pre-flash bridge: managed `a90_bridge.py` running on the local control endpoint, selected ACM transport.
- Pre-flash resident: `A90 Linux init 0.11.32 (v3210-gpu-h2-3d-state-probe)`.
- Pre-flash health: `status` and `selftest verbose` returned `selftest fail=0`.
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py` only.
- Flash verification: local image SHA, recovery-pushed image SHA, and boot block prefix SHA all matched `a2c7e223b30d361716363e2b8a37b45cecce41b50a35690c2265d0aa6499b938`.
- Rollback performed: no.

## Post-Flash Health

- Native verify after reboot: `version` and `status` returned V3212 with `status=ok`.
- Post-flash `selftest verbose`: `pass=12 warn=1 fail=0`.
- Post-H3 `selftest verbose`: `pass=12 warn=1 fail=0`.
- Post-H3 `status`: V3212 resident remained reachable; storage/runtime/serial/NCM/tcpctl ready; native selftest summary `pass=12 warn=1 fail=0`.

## Functional Validation

- `gpu g0-fwclass-prepare`: PASS, `gpu.g0.fwclass_prepare.result=ok`.
- First attempt hit `busy` because the auto menu was active; `hide` returned `menu: hide requested`, then the GPU command path was available.
- `gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode`:
  - parent KGSL open/ioctl: `0`.
  - materialize devnode: `gpu.h3.draw.materialize_rc=0`.
  - child timeout: `timed_out=0`, `child_killed=0`, `child_reaped=1`, `child_status=0x0`.
  - alloc/map/write: command/color/event/VS/FS/vertex allocations all `rc=0`; `color_init_rc=0`, `shader_write_rc=0`, `vertex_write_rc=0`, `cmd_write_rc=0`.
  - draw packet: `cp_draw_packet=0x38`, `draw_initiator=0x84`, `num_instances=1`, `num_indices=3`.
  - PM4 stream: `pm4_dwords=170`, `state_reg_writes=62`, `vfd_reg_writes=8`, `cmd_size=680`.
  - submit: `sync_rc=0`, `submit_rc=0`, `submit_timestamp=1`, `timestamp_event_rc=0`, `fence_fd=6`.
  - retire/readback: `wait_rc=-1`, `wait_errno=110`, `readtimestamp_rc=0`, `retired_timestamp=0`, `readback_sync_rc=-1`, `readback_changed_count=0`.
  - cleanup: command/color/event/VS/FS/vertex free all `rc=0`, `destroy_rc=0`, `close_rc=0`, `total_elapsed_ms=2104`.

## GPU Fault Filter

- Focused grep over the managed bridge raw capture (`workspace/private/logs/bridge/bridge-20260625-185201.raw.log`) matched 0 lines for:
  - `GPU PAGE FAULT`
  - `CP opcode`
  - `a6xx_cp_hw_err`
  - `adreno_hang`
  - `GPU hang`
  - `fault ctx`
  - `KGSL.*fault`
  - `gpu fault`

## Conclusion

V3212 is bootable and the H3 command safely reaches KGSL submit with a real `CP_DRAW_INDX_OFFSET` packet and bound vertex buffer. The draw did not retire with the current placeholder shader payload, so this is not a shaded triangle or H4 proof. The next bounded unit should replace the zero placeholder with a real minimal hand-assembled ir3 VS/FS payload or narrow the remaining draw-state gap before retrying triangle readback.
