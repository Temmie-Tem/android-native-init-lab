# Native Init V3001 DOOM Status Stub Live Validation

## Summary

- Decision: `v3001-doom-status-stub-status-surface-pass-before-rollback`
- Result before rollback: `1`
- Track: active Video playback / DOOM input prerequisite.
- Candidate: `A90 Linux init 0.10.68 (v3000-doom-status-stub)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3000_doom_status_stub.img`
- Candidate SHA256: `bca4afa1300dac66499c71a45774547eb9625fdf07e7be09f76259c08e1e8e2d`
- Private run dir: `workspace/private/runs/video/v3001-doom-status-stub-live-20260620-192940`
- Live execution: `1`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `none; status-only live validation does not require button/touch input`

## Evidence

- Candidate version ok: `1`
- Candidate selftest fail=0: `1`
- `video status` rc: `0` markers_ok=`1`
- `video demo doom status` rc: `0` markers_ok=`1`
- Candidate post-status selftest fail=0: `1`

## Video Status Markers

- `video.status.doom_input=not-proven`: `1`
- `video.status.doom_stub=1`: `1`
- `video.status.next_demo=video demo [badapple|badapple-scale|nyan|doom]`: `1`

## DOOM Status Markers

- `video.demo.audio=optional-ready`: `1`
- `video.demo.boot_asset_policy=boot-image-carries-status-not-doom`: `1`
- `video.demo.display=ready-kms-player-path`: `1`
- `video.demo.doom.status_rc=0`: `1`
- `video.demo.input.button_mux=v2999-doominput-mux-live`: `1`
- `video.demo.input.next=doominputmux event3,event0 24 45000`: `1`
- `video.demo.input.touch=event6,event8-zero-events`: `1`
- `video.demo.input=not-proven`: `1`
- `video.demo.preset=doom`: `1`
- `video.demo.status=blocked-input-prerequisite`: `1`

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Interpretation

- V3001 stages live validation for the V3000 status-only DOOM demo surface.
- Pass requires only candidate health plus `video status` and `video demo doom status` blocker markers.
- This intentionally does not run `doominputmux`, open an evdev read window, start gameplay, or start video/audio playback.
- The next input liveness step remains `v2999-doominput-mux-live` when an operator can press VOLUMEUP/VOLUMEDOWN/POWER during the bounded mux window.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path is status-only over the serial command bridge.
- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_status_stub_live_handoff_v3001.py tests/test_native_doom_status_stub_live_handoff_v3001.py`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_status_stub_live_handoff_v3001`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_status_stub_live_handoff_v3001.py`: PASS (dry-run preflight/report)
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_status_stub_live_handoff_v3001.py --live`: PASS (status markers and rollback v2321/selftest fail=0)
- `git diff --check`: PASS
