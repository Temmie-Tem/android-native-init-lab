# NATIVE_INIT_V2386_PCM_WRITE_PROBE_BUILD_2026-06-15

## Scope

Host-only AUD-4 observability unit after V2385. No flash, no ADSP command, no `/dev/snd` command, no mixer write, and no playback retry.

Goal: replace the ambiguous stock `tinyplay` success/failure signal with a diagnostic PCM write probe for the next live attempt.

## Design

V2385 proved that stock `tinyplay` prints `Error playing sample` when `pcm_write()` fails, but still returns process rc `0`. The next unit needs the exact write failure detail, not route tuning.

V2386 adds:

- Public probe source: `workspace/public/src/native-init/helpers/a90_pcm_write_probe_v2386.c`
- Host-only private builder: `workspace/public/src/scripts/revalidation/build_audio_pcm_write_probe_v2386.py`
- Private output manifest: `workspace/private/builds/audio/v2386-audio-pcm-write-probe/manifest.json`
- AUD-4 runner integration in `workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py`

The probe links against the same pinned tinyalsa source as V2345:

- project: AOSP `platform/external/tinyalsa`
- commit: `e14bf1479ebaaabf60bc4472ce8d304f72f03c32`

The probe intentionally preserves the V2379 playback shape:

```text
a90_pcm_write_probe_v2386 <pilot.wav> -D 0 -d 0
```

It does not change route controls, card/device, sample rate, channel count, bit depth, period size, or period count. Defaults remain `card=0`, `device=0`, `period_size=1024`, `period_count=4`.

## Diagnostic contract

On write failure the probe prints:

```text
A90_PCM_PROBE_WRITE_ERROR chunk=<n> rc=<rc> errno=<errno> strerror="<strerror>" pcm_error="<pcm_get_error>" bytes=<bytes> frames=<frames>
```

It also has explicit markers for:

- `A90_PCM_PROBE_START`
- `A90_PCM_PROBE_PCM_OPEN_OK`
- `A90_PCM_PROBE_PCM_OPEN_ERROR`
- `A90_PCM_PROBE_WRITE_OK`
- `A90_PCM_PROBE_WRITE_ERROR`
- `A90_PCM_PROBE_DONE`

This directly covers the V2385 gap: if the next live run fails at `SNDRV_PCM_IOCTL_WRITEI_FRAMES`, the result should contain the tinyalsa `pcm_get_error()` string and errno rather than only stock `tinyplay`'s generic marker.

## Private build result

Built host-only with:

```bash
python3 workspace/public/src/scripts/revalidation/build_audio_pcm_write_probe_v2386.py
```

Result:

- path: `workspace/private/builds/audio/v2386-audio-pcm-write-probe/bin/a90_pcm_write_probe_v2386`
- SHA256: `629079f4967143262007c54ad464f7a53504bd0b6a8f4e886f4f269b4b947771`
- file: `ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped`
- committed: no; binary and manifest remain private/generated

## Runner integration

The AUD-4 runner now defaults to `--playback-tool pcm-probe` and stages:

1. `tinymix`
2. `a90_pcm_write_probe_v2386`
3. generated 48 kHz stereo S16_LE 0.02-amplitude WAV

Dry-run playback argv is now:

```json
[
  "/cache/a90-runtime/bin/v2379-speaker-pilot/a90_pcm_write_probe_v2386",
  "/cache/a90-runtime/bin/v2379-speaker-pilot/pilot_48k_s16le_stereo_0p02_1s.wav",
  "-D",
  "0",
  "-d",
  "0"
]
```

The old stock `tinyplay` path remains available as `--playback-tool tinyplay`, but the default next live route uses the diagnostic probe.

## Decision

V2386 is source/build/test only. It prepares the next exact-gated live attempt but does not execute it.

Next frontier:

- V2387 live retry of the same V2377 observed route using the V2386 probe.
- Do not tune route controls, period geometry, card/device, sample rate, or amplitude until `A90_PCM_PROBE_WRITE_ERROR` or `A90_PCM_PROBE_DONE` is observed live.

## Validation

Focused validation passed:

- `python3 workspace/public/src/scripts/revalidation/build_audio_pcm_write_probe_v2386.py`
- `file workspace/private/builds/audio/v2386-audio-pcm-write-probe/bin/a90_pcm_write_probe_v2386`
- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_audio_pcm_write_probe_v2386.py workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py tests/test_build_audio_pcm_write_probe_v2386.py tests/test_native_audio_speaker_pilot_live_handoff_v2379.py`
- `PYTHONPATH=tests python3 -m unittest tests.test_build_audio_pcm_write_probe_v2386 tests.test_native_audio_speaker_pilot_live_handoff_v2379 -v` — 11 tests OK
- `python3 workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py --dry-run` — `ok=True`, install artifacts `tinymix`, `pcm_probe`, `pilot_wav_generated_runtime`

Additional validation passed:

- `python3 workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py --dry-run` — checked default probe playback argv
- `PYTHONPATH=tests python3 -m unittest discover -s tests` — 1067 tests OK
- `git diff --check`
