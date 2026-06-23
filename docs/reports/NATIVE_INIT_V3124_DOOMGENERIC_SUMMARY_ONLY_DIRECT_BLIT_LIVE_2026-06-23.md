# Native Init V3124 DOOMGENERIC Summary-Only Direct Blit Live Validation

## Summary

- Decision: `v3124-doomgeneric-summary-only-direct-blit-clean-pass-before-rollback`
- Result before rollback: `1`
- Loop classification: `prescaled-producer-clean`
- Track: DOOM frame IPC/copy reduction / validation-output decongestion.
- Candidate: `A90 Linux init 0.10.116 (v3123-doomgeneric-summary-only-direct-blit)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3123_doomgeneric_summary_only_direct_blit.img`
- Candidate SHA256: `248af9a65bb9d4c30cd1c0cd11db642c1cbcb332697b0387372bd7465175b808`
- Private run dir: `workspace/private/runs/video/v3124-doomgeneric-summary-only-direct-blit-live-20260623-131300`
- Live execution: `1`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Expected reader: `shared-mmap-direct-blit`
- Expected foreground frame log: `0`
- V3119 read/draw avg baseline us: `477` / `4816`

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
- Frame mode/scale/path: `minimal-large-pre-scaled-producer` / `1:1-pre-scaled` / `producer-pre-scaled-raw-rowcopy`
- Timing alloc/read/begin avg us: `1` / `2` / `2`
- Read avg vs V3119: improved=`1` delta_us=`-475` threshold_us=`250` baseline_us=`477`
- Timing draw avg/max us: `4289` / `4664` delta_vs_v3119_us=`-527`
- Timing present avg us: `1972`
- Timing total avg/max us: `6265` / `23766`
- Flip events: `180` delta avg/max us: `16639` / `16663` 60hz_stable=`1` 30hz_stable=`0`
- Shared seq missed/max-gap: `0` / `1` clean=`1`
- Duplicate frame polls: `173`
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
- `video.demo.doom.loop.timing_probe=1`: `1`
- `video.demo.doom.loop.verify.ok=1`: `1`
- `video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop`: `1`

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Interpretation

- If summary-only markers and final timing/seq summaries survive, V3123 fixed the validation-output flood observed in V3122.
- If the direct marker is present and read avg drops, the shared-frame heap staging copy was measurable overhead.
- If read avg stays near V3119, the remaining visible cost is draw/present cadence, producer pixel work, or DOOM's 35 Hz game-tic cadence rather than the presenter staging copy.
- This candidate still uses bounded tone co-run, not real DOOM music/SFX.

## Result Interpretation

V3124 closes the V3122 validation gap. The summary-only foreground path kept
the final loop evidence intact, and the direct shared-blit marker was present.
The shared-frame heap staging copy was measurable: V3119 read average was
`477 us`, while V3124 read average was `2 us` (`-475 us`). Draw also improved
from the V3119 baseline by `527 us` (`4816 us` -> `4289 us`).

This does not change the larger visual conclusion: pageflip is stable and
shared sequence is clean, so residual stepped motion is still dominated by
DOOM's original-speed 35 Hz game-tic cadence on the 60 Hz panel rather than
presenter read/copy overhead.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path hides the auto menu and then runs one bounded foreground `video demo doom loop` over the serial command bridge.
- No Wi-Fi connect/dhcp/ping, PMIC, backlight, GPIO, regulator, GDSC, panel re-init, GPU/GL stack, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.

## Host Validation

- `py_compile`: V3123 builder, V3124 live runner, V3122 live runner, and focused tests: PASS.
- `unittest`: V3123 source, V3124 live, V3122 live, V3120 source, and V3119 live focused suites: 24 tests PASS.
- V3124 dry-run preflight/report: PASS.
- V3123 source build: PASS; boot SHA256 `248af9a65bb9d4c30cd1c0cd11db642c1cbcb332697b0387372bd7465175b808`.
- V3124 live: PASS; rollback to `v2321` and runner-recorded selftest `fail=0`.
- Post-run manual slow serial check: `version` returned `0.9.285 (v2321-usb-clean-identity-rodata)` and `selftest verbose` returned `fail=0`.
- `git diff --check`: PASS
