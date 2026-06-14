# V2409 — AUD-5B native App Type gate runner support

Scope: host-only runner/planner update. No device action, no flash, no ADSP command, no mixer write, no playback.

## Decision

`v2409-app-type-gate-runner-ready`

V2409 implements the N1 gate from V2408 in the existing native speaker pilot runner: an optional, exact-gated App Type command can now be inserted before the V2377 speaker route and V2386 PCM write probe.

## Implemented change

Updated `workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py`:

- Added `--set-observed-app-type`.
- When enabled, dry-run/live planning inserts this command before route apply:

```text
/cache/a90-runtime/bin/v2379-speaker-pilot/tinymix -D 0 "Audio Stream 0 App Type Cfg" 69941 15 48000 2
```

- The command is kept separate from the 13 route-apply controls, so the original V2377 route recipe remains auditable.
- Live runs with this option require a separate exact gate:

```text
AUD-5B-native-app-type-gate go: one-shot V2407 App Type Cfg before V2377 route, low-amplitude PCM probe, reverse reset, rollback to V2321
```

- The default AUD-4 path is unchanged and still requires the original AUD-4 phrase.
- Live execution, if later run, executes the App Type command after the baseline `tinymix --all-values` snapshot and before the first route write.

## Magisk module direction

The user noted that the Wi-Fi work used Android/Magisk-style helper packaging effectively. The audio direction is consistent with that pattern but keeps the boundary strict:

- **Native runtime:** no Magisk dependency, no Android framework dependency, no Magisk artifact inside the native boot image.
- **Default Android measurement mode:** M0 transient `su -c` helper remains enough; V2407 successfully captured ACDB/App Type evidence with this mode.
- **Temporary Magisk boot module:** reserve as a measurement escalation only if transient `su -c` misses an early Android ACDB/App Type edge or vendor log/probe hook. It is not justified for N1 because V2407 already captured the needed App Type tuple and M1 is not needed.
- **Output contract:** any future Magisk module output must be an offline recipe/payload fact for a native helper, not a runtime dependency.

This mirrors the Wi-Fi lesson: use Android/Magisk as a controlled measurement capsule when Android owns the producer edge, then port only the minimum observed native-facing action into native-init.

## Host dry-run evidence

Command:

```bash
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py --dry-run --set-observed-app-type
```

Observed summary:

```text
ok=True
approval_phrase_required=AUD-5B-native-app-type-gate go: one-shot V2407 App Type Cfg before V2377 route, low-amplitude PCM probe, reverse reset, rollback to V2321
app_type_command.argv=[tinymix, -D, 0, Audio Stream 0 App Type Cfg, 69941, 15, 48000, 2]
route_apply_commands=13
route_reset_commands=12
magisk_direction.role=android_measurement_fallback_only
magisk_direction.native_runtime_dependency=False
```

## Validation

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py \
  tests/test_native_audio_speaker_pilot_live_handoff_v2379.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_speaker_pilot_live_handoff_v2379 -v
```

Result: focused test suite passed, 12 tests OK.

## Next unit

Run the bounded live N1 App-Type-first discriminator under the new AUD-5B exact gate. Interpret outcomes as:

- **prepare/probe advances past V2389 `pcm_prepare()` `EINVAL`:** App Type was a missing gate; continue downstream with dmesg and PCM probe evidence.
- **same `cal_block is NULL` / `adm_open ADSP_EFAILED`:** App Type alone is insufficient; proceed to N2 `/dev/msm_audio_cal` preflight and only then consider pinned ACDB payload replay.
- **App Type command fails:** classify mixer-control reachability/encoding, reset route, rollback to V2321, and stop the live unit.

