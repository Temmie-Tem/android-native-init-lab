# Native Init V3066 DOOMGENERIC Large Scale Off Live

## Summary

- Cycle: `V3066`
- Track: active Video playback / DOOM capstone frame pacing.
- Decision: `v3066-doomgeneric-large-scale-off-live-pass`
- Result: PASS
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3065_doomgeneric_large_scale_off.img`
- Boot SHA256: `e1d7d6e2af78422fb5fadf2847205c8bbda5f45d191835030fe80cc6338ef42b`
- Init after flash: `A90 Linux init 0.10.90 (v3065-doomgeneric-large-scale-off)`

## Flash Gate

- Built artifact was checksummed before flash.
- Rollback images were present and matched the required SHA256 values for `v2321` and `v2237`; `v48` fallback was present.
- Recovery/TWRP files were present under the private firmware input path.
- Flash path: `native_init_flash.py` only.
- Flash helper verified local marker, remote pushed-image SHA256, boot readback prefix SHA256, reboot to native init, and post-boot `version`/`status`.

## Health

- Pre-flash resident: `0.10.89 (v3063-doomgeneric-frame-ms28)`.
- Pre-flash DOOM loop was stopped before flashing.
- Post-flash health: `selftest pass=12 warn=1 fail=0`.
- Post-flash storage/runtime: SD-backed runtime mounted and writable.
- Post-flash transport: serial ready, NCM/tcpctl ready on the device side.
- Note: the first standalone `selftest` call after flash returned a serial parse failure with `A90P1 END marker not found`; bridge status and `version` remained healthy, and `selftest verbose` passed on immediate retry. Treat this as a transport/noise observation, not a device health failure.

## DOOM Status Markers

- `video.demo.engine.bridge=v3065-doomgeneric-large-scale-off`
- `video.demo.engine.active=doomgeneric-private-link-v3065-large-scale-off`
- `video.demo.engine.helper=/bin/a90_doomgeneric_private_engine_v3065`
- `video.demo.doom.loop.frame_ms=28`
- `video.demo.doom.presenter.pacing=helper-frame-mtime`
- `video.demo.doom.presenter.poll_ms=4`
- `video.demo.doom.dashboard.native=1`
- `video.demo.doom.dashboard.large_frame=0`
- `video.demo.doom.dashboard.frame_mode=standard-dashboard`
- `video.demo.doom.dashboard.frame_scale=1:1`
- `video.demo.input.active=udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`
- `video.demo.input.udp_port=30570`

## Live Functional Check

- Started continuous loop with `video demo doom loop-start 0 --wad runtime-private --sha256 EXPECTED`.
- Loop status after start: `active=1`, `continuous=1`.
- Frame artifact existed at the V3065 frame path with expected byte size `1024000`.
- Repaired host NCM route with the checked `ncm_host_setup.py setup --interface <host-ncm-iface>` helper after reboot re-enumerated the host interface.
- Sent compact UDP input packets over USB NCM.
- Device input-state file advanced to `seq=403` and returned to all-up state.
- Loop status after UDP input remained `active=1`, `continuous=1`.

## Pacing Probe

- Short in-device mtime sampling showed the frame file changing mostly in `30ms` and `40ms` steps after large scaling was disabled.
- `top` during the continuous loop showed the presenter process around `5.6%` CPU and the DOOM engine around `2.8%` CPU, with the system mostly idle.
- This makes whole-system CPU saturation and thermal throttling unlikely as the primary stutter cause in this run.

## Additional Findings

- Disabling large-dashboard software scaling is bootable and preserves playability, UDP input, audio corun startup, and native dashboard visibility.
- The repeated host-side NCM route issue reproduced again after reboot/re-enumeration. Any input test over UDP should preflight `ncm_host_setup.py status|setup` before judging keyboard responsiveness.
- If the operator still sees visible stutter on V3065, the strongest remaining code-path suspect is the 1MB raw frame file IPC: the engine writes a full frame to `/tmp`, while the presenter opens/reads/blits that file repeatedly. The next structural rendering step should avoid the frame-file handoff or replace it with a lower-copy shared/direct KMS buffer path.

## Safety

- No forbidden partition was touched.
- No raw host-side partition command was used outside `native_init_flash.py`.
- No Wi-Fi credential action was attempted.
- Public report redacts host/device IP, MAC, interface, and serial identifiers.
- DOOM loop was left active for operator visual inspection.
