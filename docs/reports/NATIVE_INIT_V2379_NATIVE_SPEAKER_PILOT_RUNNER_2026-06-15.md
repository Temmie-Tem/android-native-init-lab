# NATIVE_INIT V2379 — Exact-Gated Native Speaker Pilot Runner

## Scope

V2379 implements the next AUD-4 source/build/test unit after V2378. It adds an exact-gated native speaker pilot runner but does **not** execute live playback in this iteration.

Primary artifact:

- `workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py`

Test artifact:

- `tests/test_native_audio_speaker_pilot_live_handoff_v2379.py`

## Inputs Reused

- V2377 Android route-delta evidence: `workspace/private/runs/audio/v2377-android-route-delta-modern-apk-20260615-042113`
- V2378 route recipe: `native_audio_speaker_route_recipe_v2378.py`
- V2334 ADSP + `/dev/snd` materialization candidate image, via existing V2335 helper path
- V2345 tinyalsa tools:
  - `tinymix` SHA256 `747b19a5a263a3f2f02223ba2bad2aa0e34f9e8a3948093d612d57e3ada15411`
  - `tinyplay` SHA256 `03fd8faa9363f97f58a0b094c1504ae4c6f7d8d37f7befd908eaecc6afe81db0`

The script reads the V2345 raw manifest for `tinyplay` because the V2346 inventory verifier intentionally excludes `tinyplay` from read-only inventory use.

## Implemented Live Sequence

The live path is present but guarded by the exact AUD-4 phrase. If run later, it will:

1. Verify resident V2321 and `selftest fail=0`.
2. Flash V2334 only via `native_init_flash.py`.
3. Confirm V2334 version/status/selftest.
4. Bring up ADSP if the card is not already present.
5. Materialize `/dev/snd` once via the token-gated V2334 command.
6. Stage run-local artifacts to `/cache/a90-runtime/bin/v2379-speaker-pilot/`:
   - `tinymix`
   - `tinyplay`
   - generated `pilot_48k_s16le_stereo_0p02_1s.wav`
7. Snapshot `tinymix -D 0 --all-values` before route apply.
8. Apply exactly the 13 V2377-observed route controls from V2378.
9. Run one low-amplitude `tinyplay`:

```text
/cache/a90-runtime/bin/v2379-speaker-pilot/tinyplay /cache/a90-runtime/bin/v2379-speaker-pilot/pilot_48k_s16le_stereo_0p02_1s.wav -D 0 -d 0
```

10. Reverse-reset the 12 resettable route controls, even if playback fails after apply.
11. Snapshot `tinymix -D 0 --all-values` after reset and compare resettable controls to the pre-apply snapshot.
12. Verify candidate selftest.
13. Roll back to V2321 and verify rollback version/selftest.

## Safety Boundaries

Hard boundaries encoded in the runner and tests:

- default mode is `--dry-run`, device action `none`;
- live mode requires the exact AUD-4 phrase;
- route writes are limited to V2377-observed controls only;
- no Android framework playback, `app_process`, `am start`, Magisk, audio HAL, or adsprpc path;
- no raw flash, fastboot, `/dev/block`, `/efs`, or `/sec_efs` command tokens;
- generated PCM is 48 kHz, stereo, signed 16-bit, 1000 ms max, amplitude max `0.05` and default `0.02`;
- reverse reset is mandatory after attempted route apply;
- V2321 rollback is mandatory after V2334 candidate flash.

Magisk remains an Android-side measurement fallback only. It is not a dependency of the native AUD-4 runtime path.

## Dry-Run Result

Command:

```text
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py --dry-run
```

Summary:

```text
decision: v2379-native-speaker-pilot-runner-dry-run
ok: True
materialization_preflight: True
route_apply_commands: 13
route_reset_commands: 12
tinymix_sha256_ok: True
tinyplay_sha256_ok: True
```

Required future live gate:

```text
AUD-4-native-speaker-pilot go: one-shot V2377 observed route apply, low-amplitude tinyplay, reverse reset, rollback to V2321
```

## Validation

Commands run:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py tests/test_native_audio_speaker_pilot_live_handoff_v2379.py
PYTHONPATH=tests python3 -m unittest tests.test_native_audio_speaker_pilot_live_handoff_v2379 -v
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py --dry-run
```

Focused test result:

```text
Ran 6 tests
OK
```

## Decision

`v2379-native-speaker-pilot-runner-dry-run`

The native speaker pilot runner is source/test ready. The next unit can run the exact-gated AUD-4 live pilot under the existing overnight recoverable-device preauthorization, or perform an additional host-side review first if desired.
