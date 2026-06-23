# Native Init V3127 DOOMGENERIC Smooth Demo Direct Blit Live Validation

## Summary

- Decision: `v3127-doomgeneric-smooth-demo-direct-blit-smooth-demo-cadence-clean`
- Result before rollback: `1`
- Loop classification: `smooth-demo-cadence-clean`
- Track: residual DOOM cadence diagnosis / non-original smooth demo comparison.
- Candidate: `A90 Linux init 0.10.117 (v3126-doomgeneric-smooth-demo-direct-blit)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3126_doomgeneric_smooth_demo_direct_blit.img`
- Candidate SHA256: `bda5dffce49ae0e590d2dc629f299e39d54c097ce60d63aa022f146d2fa1f75d`
- Private run dir: `workspace/private/runs/video/v3127-doomgeneric-smooth-demo-direct-blit-live-20260623-134314`
- Live execution: `1`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Expected smooth mode: `non-original-smooth-demo`
- Expected tic quantum us: `28571`
- V3124 read/draw avg baseline us: `2` / `4289`

## Live Evidence

- Pre-flash current version: `0.9.285 (v2321-usb-clean-identity-rodata)`
- Pre-flash selftest fail=0: `1`
- Candidate version ok: `1`
- Candidate selftest fail=0: `1`
- Candidate hide-before-loop ok: `1`
- DOOM loop rc: `0` transport_rc=`0` protocol_end=`1`
- Frames requested/presented: `180` / `180`
- Direct reader marker: `shared-mmap-direct-blit` ok=`1`
- Summary-only marker: foreground_frame_log=`0` ok=`1`
- Pre-scaled/no-full-clear ok: producer=`1` no_full_clear=`1`
- Timing read/draw/total avg us: `3` / `4277` / `6266`
- Timing deltas vs V3124 read/draw us: `1` / `-12`
- Flip events: `180` delta avg/max us: `16639` / `16666` 60hz_stable=`1`
- Shared seq missed/max-gap: `0` / `1` clean=`1`

## Smooth Telemetry

- Telemetry available: `1` open_rc=`0` lines=`23`
- Tick telemetry marker: `a90.doomgeneric.v3126.tick_telemetry=smooth-demo-paced-time-direct-blit`
- Paced-time marker/model: `a90.doomgeneric.v3126.paced_time=smooth-demo-presenter-token-doom-tic-quantum` / `presenter-token-doom-tic-quantum` ok=`1`
- Smooth mode: `non-original-smooth-demo`
- Tic quantum us: `28571` ok=`1`
- Paced advance calls/us_total: `180` / `5142780`
- Loop gametic changed/repeated/max_delta: `180` / `0` / `5`
- Draw gametic changed/repeated/max_same_run: `180` / `41` / `42` internal_repeats=`1`
- Dump gametic changed/repeated/max_same_run/max_delta: `179` / `0` / `1` / `1`
- Output gametic repetition bounded: `1`
- Candidate post-loop selftest fail=0: `1`

## Loop Markers

- `video.demo.doom.dashboard.clear_path=dirty-dashboard-regions`: `1`
- `video.demo.doom.dashboard.frame_mode=minimal-large-pre-scaled-producer`: `1`
- `video.demo.doom.dashboard.frame_scale=1:1-pre-scaled`: `1`
- `video.demo.doom.dashboard.full_clear=0`: `1`
- `video.demo.doom.dashboard.pre_scaled_large_frame=1`: `1`
- `video.demo.doom.dashboard.scale_path=producer-pre-scaled-raw-rowcopy`: `1`
- `video.demo.doom.loop.flip_telemetry=pageflip-event-delta-us`: `1`
- `video.demo.doom.loop.foreground_frame_log=0`: `1`
- `video.demo.doom.loop.presenter.reader=shared-mmap-direct-blit`: `1`
- `video.demo.doom.loop.seq_telemetry=1`: `1`
- `video.demo.doom.loop.tick_telemetry.open_rc=0`: `1`
- `video.demo.doom.loop.tick_telemetry.paced_time_marker=a90.doomgeneric.v3126.paced_time=smooth-demo-presenter-token-doom-tic-quantum`: `1`
- `video.demo.doom.loop.tick_telemetry.paced_time_model=presenter-token-doom-tic-quantum`: `1`
- `video.demo.doom.loop.tick_telemetry.smooth_demo_mode=non-original-smooth-demo`: `1`
- `video.demo.doom.loop.tick_telemetry.summary=1`: `1`
- `video.demo.doom.loop.timing_probe=1`: `1`
- `video.demo.doom.loop.verify.ok=1`: `1`
- `video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop`: `1`

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Interpretation

- If pageflip remains 60Hz stable, shared seq stays clean, and smooth telemetry has bounded output-frame gametic repetition, the residual V3124 stutter was original DOOM 35Hz game-tic cadence rather than presenter/IPC/display overhead.
- `draw_gametic` is an internal draw-call sample; repeated draw samples are review evidence only when `dump_gametic` also repeats.
- If smooth telemetry is present but output-frame gametic repetition remains high, the remaining problem is inside the engine time/tic model.
- If pageflip or shared sequence regresses, the remaining cause is still in presenter/display synchronization and not DOOM semantics.
- This candidate intentionally changes DOOM virtual time and is a comparison/demo mode, not original-speed gameplay.
- This candidate still uses bounded tone co-run, not real DOOM music/SFX.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path hides the auto menu and then runs one bounded foreground `video demo doom loop` over the serial command bridge.
- No Wi-Fi connect/dhcp/ping, PMIC, backlight, GPIO, regulator, GDSC, panel re-init, GPU/GL stack, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.

## Host Validation

- `py_compile`: V3127 live runner and focused tests.
- `unittest`: V3127 live parser/report/preflight contract.
- dry-run preflight/report: PASS when preflight assets are present.
- `git diff --check`: PASS
