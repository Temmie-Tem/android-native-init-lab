# Native Init V3087 DOOMGENERIC Pageflip Cadence Live Validation

## Summary

- Cycle: `V3087`
- Candidate flashed: `V3086`
- Build: `A90 Linux init 0.10.100 (v3086-doomgeneric-pageflip-cadence)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3086_doomgeneric_pageflip_cadence.img`
- Boot SHA256: `71c84e04f5ec9357393ebdc682f7095777d395173b22fb7323e591a5bdd4d0b5`
- Decision: `v3087-doomgeneric-pageflip-cadence-live-pass`
- Result: PASS
- Rollback: not needed

## Flash Gate

- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img` matched the required SHA256.
- Rollback image `boot_linux_v2237_supplicant_terminate_poll.img` matched the required SHA256.
- Final fallback `boot_linux_v48.img` exists.
- TWRP recovery image and archive exist.
- Pre-flash resident health was clean: `version`, `status`, and `selftest` completed with fail count `0`.
- Flash used only `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Remote boot-block readback SHA256 matched the local V3086 image SHA256.

## Post-Flash Health

- `native_init_flash.py` verified V3086 after reboot through cmdv1.
- Post-flash `selftest` completed with fail count `0`.
- Final post-validation `selftest` also completed with fail count `0`.

## DOOM Live Markers

- `video demo doom status` confirmed the V3086 engine and helper.
- Runtime WAD was present, regular, size-ok, and SHA256 matched the expected runtime-private hash.
- Shared-frame IPC remained active.
- Fast 3:2 dashboard scale path remained active.
- Background serial-preserve marker remained active.
- Pageflip pacing marker changed as intended:
  - V3085 baseline: `video.demo.doom.presenter.pageflip_min_submit_interval_ms=18`
  - V3087 candidate: `video.demo.doom.presenter.pageflip_min_submit_interval_ms=0`

The first post-boot DOOM status attempt returned only residual serial text and no A90P1 END marker. A subsequent `version` command proved cmdv1 was healthy; sending `hide` explicitly synchronized the menu/display state, and the repeated DOOM status command completed normally.

## Bounded Loop Timing

Command:

`video demo doom loop 180 --wad runtime-private --sha256 <expected-runtime-wad-sha256>`

Result:

- Frames presented: `180`
- Loop rc: `0`
- Buffer allocations: `1`
- Shared-frame reader: active
- Pace socket active: `1`
- Pace tokens sent: `180`
- Pace socket failures: `0`
- Pace socket wait timeouts: `0`

Timing:

- Read avg/max: `180us / 939us`
- Begin avg/max: `4536us / 4810us`
- Draw avg/max: `4255us / 4850us`
- Present avg/max: `2255us / 3547us`
- Total avg/max: `11226us / 13451us`
- Pageflip delta min/max/avg: `16611us / 16642us / 16624us`

V3085 comparison:

- V3085 pageflip delta avg: about `33244us`
- V3087 pageflip delta avg: about `16624us`
- V3085 total frame avg: about `27732us`
- V3087 total frame avg: about `11226us`

Interpretation:

- V3085's visible 30fps cadence was caused by the extra pageflip min-submit guard.
- With that guard disabled, DOOM presentation reaches the same 60Hz cadence as the KMS pageflip baseline.
- Frame IPC, fast 3:2 scaling, and pageflip itself are not the current dominant stutter source in this candidate.

## KMS Baseline

Command:

`video flipprobe 120`

Result:

- Frames presented: `120`
- Measured fps: about `59.7fps`
- Path: KMS dumb-buffer pageflip

This matches the V3087 DOOM loop pageflip cadence.

## Background Serial Preserve Recheck

Command:

`video demo doom loop-start 0 --wad runtime-private --sha256 <expected-runtime-wad-sha256>`

Result:

- Background continuous loop started.
- `background_cancel=disabled-serial-preserve` marker was present.
- `pageflip_min_submit_interval_ms=0` marker was present.
- Audio co-run start returned rc `0`.
- While the background loop was active, these serial/cmdv1 commands completed normally:
  - `version`
  - `status`
  - `video demo doom loop-status`
- `video demo doom loop-stop` completed with rc `0`.
- Audio stop/reset path completed with rc `0`.

## Remaining Issues / Next Suspects

1. Per-frame foreground validation logs are still noisy. They do not affect continuous background play, but they make timing captures large.
2. Real DOOM SFX is still not implemented; current audio remains the `native-audio-corun-tone-v3053` co-run tone path.
3. The first DOOM command after boot can still require an explicit `hide` because autohud/menu owns the display.
4. Now that presentation reaches 60Hz, the next gameplay quality check should be hands-on: host keyboard over UDP/NCM during continuous loop, with input responsiveness and perceived smoothness observed together.

## Recommended Next Unit

- Run ID: `V3088`
- Purpose: hands-on continuous gameplay validation on V3086.
- Scope:
  - run continuous background DOOM loop,
  - start host keyboard UDP/NCM input path,
  - verify movement/menu/fire responsiveness,
  - watch for dropped input after several minutes,
  - record whether perceived stutter remains now that pageflip cadence is 60Hz.
