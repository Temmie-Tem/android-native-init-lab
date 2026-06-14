# NATIVE_INIT_V2392_BOUNDED_FAILURE_DMESG_TAIL_2026-06-15

## Scope

V2392 is a host-only fix to the V2390/V2391 failure-log capture path. It does not change audio route controls, PCM format, PCM geometry, card/device, amplitude, ADSP activation, Android handoff, Magisk use, or flash policy.

V2391 proved that the previous unbounded `/bin/toybox dmesg` capture ran but was not useful: over tcpctl it hit the output cap and truncated in early boot logs before any playback-time audio lines.

## Change

The AUD-4 native speaker pilot runner now captures a bounded playback-failure kernel-log tail:

- Step remains: `dmesg-after-playback-failure-before-reset`
- Command becomes: `/bin/busybox sh -c 'dmesg | tail -n 240'`
- Transport is forced to serial `cmdv1x` for this step, independent of the selected artifact/snapshot transfer transport.
- Result metadata records `transport=serial-cmdv1x` and `bounded_tail_lines=240` under `speaker_pilot.playback_failure_dmesg`.
- Dry-run advertises the exact bounded command under `runtime_plan.playback_failure_dmesg_capture`.

## Rationale

The failure of interest occurs after route apply and immediately after the V2386 PCM probe calls into tinyalsa `pcm_prepare()`. Capturing the full boot log through tcpctl spends the output budget on early boot noise. A bounded tail taken immediately after the playback failure should retain the current driver messages while staying read-only.

## Safety

- Read-only dmesg query only.
- No new mixer writes.
- No playback change.
- No shell mutation: the shell command is a read-only pipeline ending in `tail`.
- No native Magisk dependency; Magisk remains Android-side measurement fallback only.
- Existing route reset and V2321 rollback behavior remains unchanged.

## Validation

Commands run:

```bash
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py tests/test_native_audio_speaker_pilot_live_handoff_v2379.py
PYTHONPATH=tests python3 -m unittest tests/test_native_audio_speaker_pilot_live_handoff_v2379.py
python3 -m unittest discover tests
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py --dry-run > /tmp/v2392-dry-run.json
git diff --check
```

Results:

- Focused V2379 tests: 10/10 pass.
- Full unittest discover: 1069/1069 pass.
- Dry-run: `decision=v2379-native-speaker-pilot-runner-dry-run`, `ok=True`.
- Dry-run advertises `argv=['/bin/busybox', 'sh', '-c', 'dmesg | tail -n 240']`, `transport=serial-cmdv1x`, `bounded_tail_lines=240`, and `read_only=True`.
- `git diff --check`: pass.

## Next

Run the pre-authorized AUD-4 native speaker pilot again as V2393. If the PCM probe reproduces the `SNDRV_PCM_IOCTL_PREPARE` `EINVAL`, inspect the bounded dmesg tail before changing route controls, period geometry, card/device, sample rate, or amplitude.
