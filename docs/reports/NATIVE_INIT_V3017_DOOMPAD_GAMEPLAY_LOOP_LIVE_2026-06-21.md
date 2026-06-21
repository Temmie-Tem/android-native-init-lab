# Native Init V3017 DOOMPAD Gameplay Loop Live Validation

## Summary

- Decision: `v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback`
- Result before rollback: `1`
- Track: active Video playback / DOOM input handoff.
- Candidate: `A90 Linux init 0.10.71 (v3016-doompad-gameplay-loop)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3016_doompad_gameplay_loop.img`
- Candidate SHA256: `e5303f7b79b8ebc100ffd5361c965753c6e325a94d3b6f3316d13ebcd22006e6`
- Private run dir: `workspace/private/runs/video/v3017-doompad-gameplay-loop-live-20260621-155622`
- Live execution: `1`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `none; gameplay-loop validation uses only the serial command bridge`

## Evidence

- Candidate version ok: `1`
- Candidate selftest fail=0: `1`
- `video status` rc: `0` markers_ok=`1`
- `video demo doom status` rc: `0` markers_ok=`1`
- `doompad` setup ok: `1`
- `video demo doom play 8` rc: `0` markers_ok=`1`
- Player movement parsed: `1` moved_forward=`1`
- Player initial: `x=540 y=1200`
- Player final: `x=540 y=1128`
- `doompad` cleanup ok: `1`
- Candidate post-doomplay selftest fail=0: `1`

## DOOMPAD Setup Steps

| step | rc | markers_ok |
| --- | ---: | ---: |
| `doompad-fire-down` | `0` | `1` |
| `doompad-forward-down` | `0` | `1` |
| `doompad-reset-before-play` | `0` | `1` |

## DOOMPLAY Markers

- `doomplay.frames_presented=8`: `1`
- `doomplay.frames_requested=8`: `1`
- `doomplay.input.forward=1 back=0 left=0 right=0 fire=1`: `1`
- `doomplay.rc=0`: `1`
- `doomplay.rendered=1`: `1`
- `doomplay.source=doompad-state`: `1`
- `doomplay.version=1`: `1`
- `video.demo.doom.play=doompad-frame-loop`: `1`

## DOOMPAD Cleanup Steps

| step | rc | markers_ok |
| --- | ---: | ---: |
| `doompad-fire-up` | `0` | `1` |
| `doompad-forward-up` | `0` | `1` |
| `doompad-reset-after-play` | `0` | `1` |

## DOOM Status Markers

- `video.demo.asset.wad=not-bundled`: `1`
- `video.demo.asset_id=doompad-loop-v3016`: `1`
- `video.demo.doom.status_rc=0`: `1`
- `video.demo.engine=doompad-loop-not-doomgeneric`: `1`
- `video.demo.gameplay_loop=doompad-kms-v3016`: `1`
- `video.demo.input.consumed=doompad-serial-v3014`: `1`
- `video.demo.input.hardware_gate=none-serial-control`: `1`
- `video.demo.input=serial-doompad-consumed`: `1`
- `video.demo.play.command=video demo doom play [frames]`: `1`
- `video.demo.preset=doom`: `1`
- `video.demo.status=doompad-frame-loop-ready`: `1`

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Interpretation

- V3017 validates that V3016 boots and `video demo doom play 8` consumes the serial `doompad` state snapshot.
- The pass condition is a bounded foreground KMS proof surface; this still is not a WAD-backed `doomgeneric` engine.
- USB keyboard/OTG remains a fallback diagnostic path, not the primary proof path.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path uses status, `doompad`, and one bounded foreground `video demo doom play 8` command over the serial bridge.
- No input injection, `uinput`, `EVIOCGRAB`, evdev read window, keymap change, sysfs write, Wi-Fi, audio route/playback, PMIC, backlight, GPIO, regulator, GDSC, WAD asset, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doompad_gameplay_loop_live_validation_v3017.py tests/test_native_doompad_gameplay_loop_live_v3017.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doompad_gameplay_loop_live_v3017`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doompad_gameplay_loop_live_validation_v3017.py`: PASS (dry-run preflight/report)
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doompad_gameplay_loop_live_validation_v3017.py --live`: PASS (doompad gameplay loop consumed serial state and rollback v2321/selftest fail=0)
- `git diff --check`: PASS
