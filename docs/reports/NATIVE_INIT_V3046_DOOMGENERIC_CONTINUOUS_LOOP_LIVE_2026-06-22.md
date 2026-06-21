# Native Init V3046 DOOMGENERIC Continuous Loop Live

Date: 2026-06-22

## Summary

- Run ID: `V3046`
- Candidate: `A90 Linux init 0.10.81 (v3045-doomgeneric-continuous-loop)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3045_doomgeneric_continuous_loop.img`
- Candidate SHA256: `57385f405357f981a3d3f45878dff7e20f2f3ea251cfea30f349d1418604c9a4`
- Decision: `v3046-doomgeneric-continuous-loop-live-pass`
- Device flash: `yes`
- Rollback attempted: `no`
- Result: PASS

## Flash Gates

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flashed partition scope: boot image only.
- Forbidden partitions touched: `0`
- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img`: present, SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img`: present, SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Final fallback `boot_linux_v48.img`: present, SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Recovery/TWRP path: native-to-recovery request succeeded; TWRP ADB accepted image push and boot partition write.

## Flash Result

Command:

```console
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-android-magic \
  --expect-sha256 57385f405357f981a3d3f45878dff7e20f2f3ea251cfea30f349d1418604c9a4 \
  --expect-version "A90 Linux init 0.10.81 (v3045-doomgeneric-continuous-loop)" \
  workspace/private/inputs/boot_images/boot_linux_v3045_doomgeneric_continuous_loop.img
```

Result:

```console
local image sha256: 57385f405357f981a3d3f45878dff7e20f2f3ea251cfea30f349d1418604c9a4
remote image sha256: 57385f405357f981a3d3f45878dff7e20f2f3ea251cfea30f349d1418604c9a4
boot block prefix sha256: 57385f405357f981a3d3f45878dff7e20f2f3ea251cfea30f349d1418604c9a4
cmdv1 verify passed: version/status rc=0 status=ok
phase.native_init_flash.total.elapsed_sec=63.422 ok=1
```

## Health Check

Post-flash sequential health commands:

```console
cmdv1 version
A90 Linux init 0.10.81 (v3045-doomgeneric-continuous-loop)

cmdv1 status
selftest: pass=12 warn=1 fail=0
transport.serial=ready
storage: sd present=yes mounted=yes expected=yes rw=yes

cmdv1 selftest verbose
selftest: pass=12 warn=1 fail=0 duration=41ms entries=13
```

Final cleanup health:

```console
cmdv1 version
A90 Linux init 0.10.81 (v3045-doomgeneric-continuous-loop)

cmdv1 selftest verbose
selftest: pass=12 warn=1 fail=0 duration=41ms entries=13

cmdv1 video demo doom loop-status
video.demo.doom.loop_status.active=0
video.demo.doom.loop_status.pid=-1
video.demo.doom.loop_status.continuous=0
video.demo.doom.loop_status.frames=0
```

## Functional Validation

The first DOOM command attempt returned `rc=-16 status=busy` because the auto
menu was active. Running `cmdv1 hide` cleared the gate. The live validation was
then re-run.

Continuous loop start:

```console
loop_start_0.rc 0 status ok
video.demo.doom.loop_start.active=1
video.demo.doom.loop_start.frames=0
video.demo.doom.loop_start.continuous=1
video.demo.doom.loop_start.rc=0
```

Input and loop status across the old finite-loop lifetime:

```console
tick.t_s 0.23  down_rc 0 down_ms 11.7 up_rc 0 up_ms 7.4 active 1 continuous 1 frames 0
tick.t_s 5.09  down_rc 0 down_ms 38.8 up_rc 0 up_ms 7.2 active 1 continuous 1 frames 0
tick.t_s 11.03 down_rc 0 down_ms 12.4 up_rc 0 up_ms 7.7 active 1 continuous 1 frames 0
tick.t_s 15.06 down_rc 0 down_ms 10.4 up_rc 0 up_ms 6.0 active 1 continuous 1 frames 0
```

Dashboard light refresh:

```console
dashboard.light_refresh_ms 18.5 loop_active True loop_frames 0 continuous 1 failures 0
```

Cleanup:

```console
cleanup.doompad_reset.rc 0
cleanup.loop_stop.rc 0
```

## Decision

The V3045 candidate is installed and passes the V3046 live gate. `loop-start 0`
now creates a continuous background DOOM loop, and input remains accepted past
the previous 300-frame lifetime. This removes the host-side need to restart the
visible helper every roughly 10 seconds.

## Notes

- Serial health commands must be run sequentially; parallel `a90ctl.py` calls
  contend on `a90-serial-bridge.lock` and can mix protocol output.
- Auto menu can block DOOM/doompad commands with `status=busy`; `hide` clears
  the menu before gameplay validation.
