# Native Init V3122 DOOMGENERIC Direct Shared Blit Live Validation

## Summary

- Decision: `v3122-doomgeneric-direct-shared-blit-loop-not-clean`
- Result before rollback: `0`
- Loop classification: `loop-not-clean`
- Track: DOOM frame IPC/copy reduction.
- Candidate: `A90 Linux init 0.10.115 (v3120-doomgeneric-direct-shared-blit)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3120_doomgeneric_direct_shared_blit.img`
- Candidate SHA256: `fb7d561731a0b426f03fc70050a80d57ad33897f3befffd9d22d187d22fbb9e3`
- Private run dir: `workspace/private/runs/video/v3122-doomgeneric-direct-shared-blit-live-20260623-125552`
- Live execution: `1`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Recovery gate: `native_init_flash.py wait_recovery_adb during candidate flash; rollback_v2321 on failure`
- Expected reader: `shared-mmap-direct-blit`
- V3119 read/draw avg baseline us: `477` / `4816`

## Live Evidence

- Pre-flash current version: `0.9.285 (v2321-usb-clean-identity-rodata)`
- Pre-flash selftest fail=0: `1`
- Candidate version ok: `1`
- Candidate selftest fail=0: `1`
- Candidate hide-before-loop ok: `1`
- DOOM loop rc: `None` transport_rc=`0` protocol_end=`1`
- Frames requested/presented: `180` / `None`
- Direct reader marker: `None` ok=`0`
- Pre-scaled marker count: `58` markers_ok=`1`
- No-full-clear markers: full_clear=`0` clear_path=`dirty-dashboard-regions` ok=`1`
- Frame mode/scale/path: `minimal-large-pre-scaled-producer` / `1:1-pre-scaled` / `producer-pre-scaled-raw-rowcopy`
- Timing alloc/read/begin avg us: `None` / `None` / `None`
- Read avg vs V3119: improved=`0` delta_us=`None` threshold_us=`250` baseline_us=`477`
- Timing draw avg/max us: `None` / `None` delta_vs_v3119_us=`None`
- Timing present avg us: `None`
- Timing total avg/max us: `None` / `None`
- Flip events: `180` delta avg/max us: `16641` / `16659` 60hz_stable=`1` 30hz_stable=`0`
- Shared seq missed/max-gap: `None` / `None` clean=`0`
- Duplicate frame polls: `None`
- Candidate post-loop selftest fail=0: `1`

## Loop Markers

- `video.demo.doom.dashboard.clear_path=dirty-dashboard-regions`: `1`
- `video.demo.doom.dashboard.frame_mode=minimal-large-pre-scaled-producer`: `1`
- `video.demo.doom.dashboard.frame_scale=1:1-pre-scaled`: `1`
- `video.demo.doom.dashboard.full_clear=0`: `1`
- `video.demo.doom.dashboard.pre_scaled_large_frame=1`: `1`
- `video.demo.doom.dashboard.scale_path=producer-pre-scaled-raw-rowcopy`: `1`
- `video.demo.doom.loop.flip_telemetry=pageflip-event-delta-us`: `0`
- `video.demo.doom.loop.presenter.reader=shared-mmap-direct-blit`: `0`
- `video.demo.doom.loop.seq_telemetry=1`: `0`
- `video.demo.doom.loop.timing_probe=1`: `1`
- `video.demo.doom.loop.verify.ok=1`: `1`
- `video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop`: `1`

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Interpretation

- `direct-shared-blit-marker-missing` means the image did not exercise the intended direct mmap source path.
- If the direct marker is present and read avg drops, the shared-frame heap staging copy was measurable overhead.
- If the direct marker is present but read avg stays near V3119, the remaining visible cost is draw/present cadence, producer pixel work, or DOOM's 35 Hz game-tic cadence rather than the presenter staging copy.
- If pageflip is stable and shared sequence is clean, residual motion stepping is still the known original-speed DOOM 35 Hz cadence on a 60 Hz panel.
- This candidate still uses bounded tone co-run, not real DOOM music/SFX.

## Post-Run Diagnosis

V3122 safely booted the V3120 candidate, presented 180 pageflips, and rolled
back cleanly, but it did not prove the direct shared-blit timing delta. Raw
private output showed the candidate status marker
`video.demo.doom.presenter.reader=shared-mmap-direct-blit`, and the final
pageflip summary was stable (`flip_delta_avg_us=16641`,
`flip_delta_max_us=16659`), but the foreground loop emitted over 1,600 serial
lines of per-frame dashboard output. Several summary lines were lost from the
serial capture, including `frames_presented`, timing read/draw totals,
sequence telemetry, and `loop.presenter.reader`.

Conclusion: this is a validation-output congestion issue, not a boot-health or
rollback failure. The next unit is V3123: keep the direct shared-blit behavior
but disable foreground per-frame serial dashboard logs and preserve the needed
loop summary markers.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path hides the auto menu and then runs one bounded foreground `video demo doom loop` over the serial command bridge.
- No Wi-Fi connect/dhcp/ping, PMIC, backlight, GPIO, regulator, GDSC, panel re-init, GPU/GL stack, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.

## Host Validation

- `py_compile`: V3122 live runner and focused tests.
- `unittest`: V3122 live parser/report/preflight contract.
- dry-run preflight/report: PASS when preflight assets are present.
- `git diff --check`: PASS
