# NATIVE_INIT_V2381_AUD4_RUNNER_TRANSPORT_FIX_2026-06-15

## Scope

Host-only fix for the V2379/V2380 native speaker pilot runner. No device flash, no mixer write, and no playback were executed in this unit.

## V2380 Root Cause

V2380 kept the recoverable boot envelope intact but did not prove speaker playback:

- V2334 booted, ADSP and `/dev/snd` materialized, candidate selftest stayed `fail=0`, and rollback to V2321 ended with `rollback_selftest_fail0=True`.
- The runner selected `tcpctl` for `tinymix` route apply/reset commands.
- `tcpctl` split space-containing mixer control names, so device output reported `Invalid mixer control` for all 13 route apply commands and all 12 reset commands.
- Host step status still returned ok because remote `ERR exit=` / `[exit N]` text was not treated as hard failure.
- `tinyplay` then ran without the intended route and printed `Error playing sample`; this also was not treated as hard failure.

## Changes

`workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py` now:

- defaults route apply/reset to serial `cmdv1x` transport via `--route-transport serial`, preserving mixer control names as argv entries;
- keeps snapshot/playback transfer transport auto-selected, so NCM/tcpctl can still be used for large artifact transfer and non-space-sensitive commands;
- parses remote tool text for `ERR exit=N` and `[exit N]`; any non-zero remote exit marks the step failed;
- treats `Invalid mixer control` as a route apply/reset failure marker;
- treats `Error playing sample` as a playback failure marker even if the wrapper prints `[exit 0]`;
- exposes dry-run/preflight metadata: `route_transport=serial`, `tcpctl_remote_failure_is_hard_failure=true`.

## Magisk Direction

Magisk remains useful in the same role it had in earlier Wi-Fi-style Android handoffs: Android-side measurement or delivery support when normal `adb`/APK/framework stimulus delivery is blocked.

It is not part of the AUD-4 native runtime path:

- `aud4_uses_magisk=false`;
- `native_runtime_dependency=false`;
- native playback must remain boot-image based, exact-gated, and rollbackable to V2321 without Android services.

Allowed future Magisk uses stay Android-only and private-only: temporary route-delta stimulus packaging, boot-time Android framework hooks, or vendor-log probes. Module zips and payloads must remain under `workspace/private/` and must not be committed.

## Dry-Run Summary

```json
{
  "decision": "v2379-native-speaker-pilot-runner-dry-run",
  "ok": true,
  "route_transport": "serial",
  "remote_dir": "/cache/a90-runtime/bin/v2379-speaker-pilot",
  "tcpctl_hard_failure": true,
  "magisk_role": "android_measurement_fallback_only",
  "aud4_uses_magisk": false,
  "native_runtime_dependency": false
}
```

## Validation

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py tests/test_native_audio_speaker_pilot_live_handoff_v2379.py
PYTHONPATH=tests python3 -m unittest tests.test_native_audio_speaker_pilot_live_handoff_v2379 -v
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py --dry-run
PYTHONPATH=tests python3 -m unittest discover -s tests -v
git diff --check
```

Focused tests pass, including:

- dry-run route transport defaults to `serial`;
- preflight records Magisk as Android measurement fallback only;
- remote `Invalid mixer control` with non-zero tcpctl exit fails;
- `Error playing sample` fails even when the wrapper emits `[exit 0]`.

## Next

Retry the exact-gated AUD-4 live run once with the fixed runner. Success criteria are stricter than V2380: route apply/reset commands must not contain `Invalid mixer control`, remote non-zero exits must fail the run, and `tinyplay` output must not contain `Error playing sample`.
