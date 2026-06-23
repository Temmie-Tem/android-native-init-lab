# Native Init V3113 DOOMGENERIC Hardware Plane Cached CRTC Live Validation

## Summary

- Decision: `v3113-doomgeneric-hw-plane-cached-crtc-loop-summary-missing`
- Result before rollback: `0`
- Loop classification: `loop-summary-missing`
- Track: DOOM large-frame scale-path optimization.
- Candidate: `A90 Linux init 0.10.111 (v3112-doomgeneric-hw-plane-cached-crtc)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3112_doomgeneric_hw_plane_cached_crtc.img`
- Candidate SHA256: `e58d08d57de91831738b3fc48911e2c6da02e50059c77935203b03409df6e5b0`
- Private run dir: `workspace/private/runs/video/v3113-doomgeneric-hw-plane-cached-crtc-live-20260623-110259`
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
- DOOM loop rc: `None` transport_rc=`0` protocol_end=`1`
- Loop summary present/missing-with-END: `0` / `1`
- Frames requested/presented: `180` / `None`
- Display presented logs / max dashboard seq: `49` / `163`
- HW plane presented: `0` count=`0`
- HW plane fallback: `1` value=`fast-3to2-rowcopy`
- HW plane last id/fb/rc: `84` / `206` / `-22`
- HW plane stage/id: `setplane` / `11`
- HW plane stage counts setplane/fetch-resources/scan-planes/presented: `73` / `0` / `0` / `0`
- HW plane crtc_index/cached-last/cached-count/reuse-evidence/fetch_resources_rc: `0` / `0` / `0` / `1` / `0`
- HW plane counts plane/compatible/idle_xbgr: `0` / `0` / `0`
- HW plane EINVAL count: `61`
- HW plane client caps universal/atomic rc: `-19` / `-19`
- Frame mode/scale/path: `minimal-large-hw-plane-scale` / `3:2` / `drm-plane-srcdst`
- Timing draw avg/max us: `None` / `None`
- Timing total avg/max us: `None` / `None`
- Flip events: `None` delta avg/max us: `None` / `None` stable=`0`
- Shared seq missed/max-gap: `None` / `None` clean=`0`
- Candidate post-loop selftest fail=0: `1`

## Loop Markers

- `video.demo.doom.dashboard.hw_plane.cached_crtc_index=`: `1`
- `video.demo.doom.dashboard.hw_plane.stage=`: `1`
- `video.demo.doom.dashboard.hw_plane_scale=1`: `1`
- `video.demo.doom.dashboard.scale_path=drm-plane-srcdst`: `1`
- `video.demo.doom.loop.flip_telemetry=pageflip-event-delta-us`: `1`
- `video.demo.doom.loop.seq_telemetry=1`: `0`
- `video.demo.doom.loop.timing_probe=1`: `1`
- `video.demo.doom.loop.verify.ok=1`: `0`
- `video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop`: `0`

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Interpretation

- `hw-plane-presented` means the next check is visual/z-order plus timing quality.
- `cpu-fallback-observed` means V3112 safely ran but the large path still used the known stuttering CPU 3:2 scaler; proceed to the pre-scaled-producer fallback.
- `cached_crtc_index=1` means V3112 bypassed the legacy `GETRESOURCES` hot path and used the KMS init CRTC index for plane enumeration.
- `cached_crtc_index=0` after `stage=setplane` is a diagnostic limitation: once a plane was selected, later frames reuse it without replaying the original selection metadata.
- `hw_plane.stage=fetch-resources` with `cached_crtc_index=0` means the cached index was unavailable and the old resources fallback still failed.
- `hw_plane.stage=scan-planes` with `rc=-19` means there was no compatible idle XBGR plane; `stage=setplane` means the next unit should try atomic plane commit.
- `loop-summary-missing` with protocol END means the serial command completed but per-frame diagnostic output likely drowned or interleaved the final summary markers; treat it as a logging/validation problem, not a boot-health failure.
- `protocol-end-missing` means the foreground loop returned prompt-visible output but did not emit a cmdv1 END marker, so host validation waits for timeout even when frame evidence is present.
- If pageflip is stable and shared sequence is clean, residual stepped motion is the known DOOM 35 Hz game-tic cadence on the 60 Hz panel.
- This candidate still uses a bounded tone corun, not real DOOM music/SFX.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path hides the auto menu and then runs one bounded foreground `video demo doom loop` over the serial command bridge.
- No Wi-Fi connect/dhcp/ping, PMIC, backlight, GPIO, regulator, GDSC, panel re-init, GPU/GL stack, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_hw_plane_cached_crtc_live_validation_v3113.py tests/test_native_doomgeneric_hw_plane_cached_crtc_live_v3113.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_hw_plane_cached_crtc_live_v3113`: PASS
- dry-run preflight/report: PASS when preflight assets are present.
- `git diff --check`: PASS
