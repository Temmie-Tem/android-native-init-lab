# NATIVE_INIT V2365 — Android route-delta runner plan

Date: 2026-06-15

## Scope

- Unit: host-only route-delta runner planning after V2364 added Android target support to the
  checked flash helper.
- Touched public code:
  - `workspace/public/src/scripts/revalidation/native_audio_android_route_delta_handoff_v2365.py`
  - `tests/test_native_audio_android_route_delta_handoff_v2365.py`
- No boot image was built.
- No device command or flash ran.
- No Android boot, playback, mixer write, or native audio write ran.

## Result

Decision: `v2365-android-route-delta-runner-plan-host-only-pass`.

The project now has a dry-run planner for the future Android route-delta capture. It verifies and
emits the command plan for:

1. sealing the archived Android boot candidate into a private `0600` run-local copy,
2. flashing that copy through `native_init_flash.py --post-flash-target android-adb`,
3. staging read-only `tinymix` and a future AudioTrack stimulus DEX under
   `/data/local/tmp/a90-audio-route-delta/`,
4. capturing baseline/active/post `tinymix -D 0 --all-values`, `dumpsys audio`,
   `dumpsys media.audio_flinger`, `dumpsys media.audio_policy`, and `/proc/asound` snapshots,
5. running a low-amplitude Android framework stimulus through `app_process`, and
6. rolling back to V2321 through the checked helper.

## Findings

- Android boot candidates are present, `ANDROID!`, and SHA-pinned to
  `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`.
- Both archived Android boot candidates are mode `0664`, so the future live runner must copy the
  selected image into the private run directory with mode `0600` before invoking
  `native_init_flash.py`; otherwise the helper correctly rejects the source as group-writable.
- The V2345 `tinymix` manifest remains valid.
- This host currently lacks the Java/Android SDK build chain needed to produce the AudioTrack DEX
  (`javac`/`d8` or `dx` plus `android.jar` were not found by the planner).

## Remaining blocker

Live route-delta is still not ready. The missing artifact is a private `A90AudioRouteStimulus.dex`
that:

- starts with DEX magic,
- is not group/world writable,
- invokes Android framework `AudioTrack` through `app_process`,
- routes to speaker/default output,
- plays a short low-amplitude 48 kHz stereo S16 signal,
- exits after one bounded run.

Once that DEX exists, the V2365 planner's `live_ready` gate can turn true and a later exact-gated
live runner can execute the plan.

## Safety boundary

- No `tinyplay`.
- No native `tinymix set`.
- No native `/dev/snd` open/write.
- No direct recovery `dd`, `fastboot`, or copied flash implementation.
- No Wi-Fi, credentials, DHCP, routes, or network.
- Future flash path remains boot-partition-only through `native_init_flash.py`.
- Future live run still requires the exact gate:

```text
AUD-3D2-android-route-delta go: rollbackable Android AudioTrack speaker route-delta capture, checked-helper boot handoff only, low-amplitude framework playback, no native speaker write, rollback to V2321
```

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_android_route_delta_handoff_v2365.py tests/test_native_audio_android_route_delta_handoff_v2365.py`
- `PYTHONPATH=tests python3 -m unittest tests.test_native_audio_android_route_delta_handoff_v2365 -v`
- `python3 workspace/public/src/scripts/revalidation/native_audio_android_route_delta_handoff_v2365.py --dry-run`
- `python3 -m unittest discover -s tests -p 'test_*.py'`
- `git diff --check`
