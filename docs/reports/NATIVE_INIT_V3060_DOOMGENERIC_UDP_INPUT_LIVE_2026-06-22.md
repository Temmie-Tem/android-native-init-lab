# Native Init V3060 DOOMGENERIC UDP Input Live Validation

## Summary

- Cycle: `V3060`
- Track: active Video playback / DOOM capstone input responsiveness.
- Decision: `v3060-doomgeneric-udp-input-live-pass`
- Result: PASS
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3059_doomgeneric_udp_input.img`
- Boot SHA256: `d93c564902b8976e91f6b052bfdecef8cfec326a3d8ea13cc22d2e373ea959d3`
- Init after flash: `A90 Linux init 0.10.87 (v3059-doomgeneric-udp-input)`

## Gates

- Rollback baseline SHA checks: PASS for `v2321`, `v2237`, and `v48`.
- Recovery/TWRP availability: PASS.
- Flash path: checked helper `workspace/public/src/scripts/revalidation/native_init_flash.py` only.
- Flash readback SHA256: matched exact V3059 boot SHA.
- Post-flash health: `selftest: pass=12 warn=1 fail=0`.

## Functional Evidence

- DOOM status marker: `video.demo.input.active=udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`.
- UDP status marker: `video.demo.input.udp_port=30570`.
- Host NCM preflight initially reported `a90-ncm-host-needs-address`; repo helper configured the host-side NCM route and ping passed `3/3`.
- DOOM loop start: `video.demo.doom.loop_start.active=1`, `continuous=1`.
- Runtime helper process included `--input-udp 30570`.
- Device UDP listener: `<wildcard>:30570`.
- UDP down packet evidence: state file showed `seq=310`, `forward=1`, `fire=1`, `active=1`.
- UDP release packet evidence: state file showed `seq=311`, all buttons `0`, `active=0`.
- Loop after UDP test: `video.demo.doom.loop_status.active=1`, `continuous=1`.

## Notes

- Serial remains only for status/loop control; gameplay input can now bypass serial cmdv1 through UDP over NCM.
- The Unix datagram input socket remains as the serial doompad fallback.
- One `loop_start.input` line still carries the older V3057 descriptive label, but the canonical `video.demo.input.active` marker, helper argv, UDP listener, and state-file evidence all confirm the V3059 UDP path.
- Device was left on V3059 with the continuous DOOM loop active for operator testing.

## Validation Commands

- `py_compile`: V3059 builder, host keyboard bridge, and focused tests.
- `unittest`: host evdev/UDP input tests, V3059 source contract, and V3057 socket regressions.
- `git diff --check`: PASS.
