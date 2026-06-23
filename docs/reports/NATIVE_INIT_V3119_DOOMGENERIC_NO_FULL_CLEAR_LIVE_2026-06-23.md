# Native Init V3119 DOOMGENERIC No-Full-Clear Live Validation

## Summary

- Decision: `v3119-doomgeneric-no-full-clear-clean-pass-before-rollback`
- Result before rollback: `1`
- Loop classification: `prescaled-producer-clean`
- Track: DOOM large-frame scale-path optimization / residual stutter audit.
- Candidate: `A90 Linux init 0.10.114 (v3118-doomgeneric-no-full-clear)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3118_doomgeneric_no_full_clear.img`
- Candidate SHA256: `579cb45707e1e7fd366fdfebf52d5d34befffc355e6e34d9cc167b03493a97a8`
- Private run dir: `workspace/private/runs/video/v3119-doomgeneric-no-full-clear-live-20260623-123005`
- Live execution: `1`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Recovery gate: `native_init_flash.py wait_recovery_adb during candidate flash; rollback_v2321 on failure`
- Expected clear path: `dirty-dashboard-regions`
- V3117 begin avg baseline us: `4574`

## Live Evidence

- Pre-flash current version: `0.9.285 (v2321-usb-clean-identity-rodata)`
- Pre-flash selftest fail=0: `1`
- Candidate version ok: `1`
- Candidate selftest fail=0: `1`
- Candidate hide-before-loop ok: `1`
- DOOM loop rc: `0` transport_rc=`0` protocol_end=`1`
- Frames requested/presented: `180` / `180`
- Pre-scaled marker count: `180` markers_ok=`1`
- No-full-clear markers: full_clear=`0` clear_path=`dirty-dashboard-regions` ok=`1`
- Frame mode/scale/path: `minimal-large-pre-scaled-producer` / `1:1-pre-scaled` / `producer-pre-scaled-raw-rowcopy`
- Timing alloc/read/begin avg us: `1` / `477` / `2`
- Timing begin improved vs V3117: `1` threshold_us=`3000` baseline_us=`4574`
- Timing draw avg/max us: `4816` / `5510`
- Timing present avg us: `890`
- Timing total avg/max us: `6187` / `22576`
- Flip events: `180` delta avg/max us: `16730` / `33268` 60hz_stable=`1` 30hz_stable=`0`
- Shared seq missed/max-gap: `0` / `1` clean=`1`
- Duplicate frame polls: `174`
- Candidate post-loop selftest fail=0: `1`

## Loop Markers

- `video.demo.doom.dashboard.clear_path=dirty-dashboard-regions`: `1`
- `video.demo.doom.dashboard.frame_mode=minimal-large-pre-scaled-producer`: `1`
- `video.demo.doom.dashboard.frame_scale=1:1-pre-scaled`: `1`
- `video.demo.doom.dashboard.full_clear=0`: `1`
- `video.demo.doom.dashboard.pre_scaled_large_frame=1`: `1`
- `video.demo.doom.dashboard.scale_path=producer-pre-scaled-raw-rowcopy`: `1`
- `video.demo.doom.loop.flip_telemetry=pageflip-event-delta-us`: `1`
- `video.demo.doom.loop.seq_telemetry=1`: `1`
- `video.demo.doom.loop.timing_probe=1`: `1`
- `video.demo.doom.loop.verify.ok=1`: `1`
- `video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop`: `1`

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Interpretation

- If `begin` drops sharply and cadence becomes 60Hz, full-frame KMS clear was the practical blocker.
- If `begin` drops but cadence remains two-vblank, the remaining cause is the synchronous present/vblank structure or producer timing, not dashboard scaling.
- If pageflip is stable and shared sequence is clean, any residual motion stepping is the known DOOM 35Hz game-tic cadence on a 60Hz panel.
- This candidate still uses bounded tone co-run, not real DOOM music/SFX.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path hides the auto menu and then runs one bounded foreground `video demo doom loop` over the serial command bridge.
- No Wi-Fi connect/dhcp/ping, PMIC, backlight, GPIO, regulator, GDSC, panel re-init, GPU/GL stack, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.

## Host Validation

- `py_compile`: V3119 live runner and focused tests.
- `unittest`: V3119 live parser/report/preflight contract.
- dry-run preflight/report: PASS when preflight assets are present.
- `git diff --check`: PASS
