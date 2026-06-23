# Native Init V3109 DOOMGENERIC Hardware Plane Scale Live Validation

## Summary

- Decision: `v3109-doomgeneric-hw-plane-scale-cpu-fallback-observed-protocol-end-missing`
- Result before rollback: `0`
- Loop classification: `cpu-fallback-observed`
- Track: DOOM large-frame scale-path optimization.
- Candidate: `A90 Linux init 0.10.109 (v3108-doomgeneric-hw-plane-scale)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3108_doomgeneric_hw_plane_scale.img`
- Candidate SHA256: `58affe427e1f9417f7c89f539528a3f693f5f38ae47ed3fae16124fc64055001`
- Private run dir: `workspace/private/runs/video/v3109-doomgeneric-hw-plane-scale-live-20260623-101545`
- Live execution: `1`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Recovery gate: `native_init_flash.py wait_recovery_adb during candidate flash; rollback_v2321 on failure`
- Operator prerequisite: `runtime-private WAD must already be staged on SD; host input is not required for this bounded loop`

## Live Evidence

- Pre-flash current version: `0.9.285 (v2321-usb-clean-identity-rodata)`
- Pre-flash selftest fail=0: `1`
- Candidate version ok: `1`
- Candidate selftest fail=0: `1`
- Candidate hide-before-loop ok: `1`
- DOOM loop rc: `0` transport_rc=`None` protocol_end=`0`
- Frames requested/presented: `180` / `180`
- HW plane presented: `0` count=`0`
- HW plane fallback: `1` value=`fast-3to2-rowcopy`
- HW plane last id/fb/rc: `0` / `0` / `-14`
- Frame mode/scale/path: `minimal-large-hw-plane-scale` / `3:2` / `drm-plane-srcdst`
- Timing draw avg/max us: `4404` / `5154`
- Timing total avg/max us: `11415` / `23742`
- Flip events: `180` delta avg/max us: `None` / `None` stable=`0`
- Shared seq missed/max-gap: `0` / `1` clean=`1`
- Candidate post-loop selftest fail=0: `1`

## Loop Markers

- `video.demo.doom.dashboard.hw_plane_scale=1`: `1`
- `video.demo.doom.dashboard.scale_path=drm-plane-srcdst`: `1`
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

- `hw-plane-presented` means the next check is visual/z-order plus timing quality.
- `cpu-fallback-observed` means V3108 safely ran but the large path still used the known stuttering CPU 3:2 scaler; proceed to the pre-scaled-producer fallback.
- `protocol-end-missing` means the foreground loop returned prompt-visible output but did not emit a cmdv1 END marker, so host validation waits for timeout even when frame evidence is present.
- If pageflip is stable and shared sequence is clean, residual stepped motion is the known DOOM 35 Hz game-tic cadence on the 60 Hz panel.
- This candidate still uses a bounded tone corun, not real DOOM music/SFX.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path hides the auto menu and then runs one bounded foreground `video demo doom loop` over the serial command bridge.
- No Wi-Fi connect/dhcp/ping, PMIC, backlight, GPIO, regulator, GDSC, panel re-init, GPU/GL stack, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_hw_plane_scale_live_validation_v3109.py tests/test_native_doomgeneric_hw_plane_scale_live_v3109.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_hw_plane_scale_live_v3109`: PASS
- dry-run preflight/report: PASS when preflight assets are present.
- `git diff --check`: PASS
