# Native Init V2339 Audio Runner Card-Wait Parser Fix

## Summary

- Cycle: `V2339`
- Track: audio AUD-3 preflight runner hardening, host-only.
- Decision: `v2339-audio-runner-card-wait-parser-fix-pass`
- Result: PASS
- Device flash: `no`.
- Device action: `none`.
- Touched runner: `workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py`.
- Touched tests: `tests/test_native_audio_snd_nodes_preflight_handoff_v2335.py`.

## Reason

V2338 proved V2334 can again boot ADSP/Q6 and expose the ALSA card/control sysfs inventory, but the live runner stopped before `audio snd-materialize-once` because `wait_for_audio_card()` missed inline fields in this native output:

```text
audio.sound_class.count=128 card_like=1 control_like=1
audio.dev_snd.count=0 control_like=0 pcm_like=0
audio.snd.9.name=controlC0 sysfs_dev=116:2 devnode=/dev/snd/controlC0 state=missing
```

Two host parser bugs were involved:

1. `parse_key_values()` stored only `audio.sound_class.count = "128 card_like=1 control_like=1"`, so `audio.sound_class.control_like` was absent.
2. `/dev/snd` regex fallback treated `devnode=/dev/snd/controlC0 state=missing` as an existing devnode.

## Change

- Extended `parse_key_values()` to split inline summary attributes into namespaced keys, for example:
  - `audio.sound_class.count=128 card_like=1 control_like=1`
  - becomes `audio.sound_class.count=128`, `audio.sound_class.card_like=1`, `audio.sound_class.control_like=1`.
- Kept full free-form values, such as `audio.proc_asound_cards=... sm8150-tavil-snd-card`, intact when no inline attributes are present.
- Replaced broad `/dev/snd` regex fallback with `state=ok`-qualified patterns, so `state=missing` lines no longer count as materialized nodes.

## Regression Coverage

Added tests that replay the V2338 pre-materialization sample and assert:

- `has_audio_card=True`.
- `has_sound_class_control=True`.
- `has_dev_snd_control=False` while `/dev/snd/controlC0 state=missing` is present.
- `has_dev_snd_pcm=False` while PCM entries are also `state=missing`.
- Summary counts and `state=ok` lines still mark materialized control/PCM nodes correctly.

## Safety Boundary

- Host-only parser change.
- No bridge, flash, ADSP write, `/dev/snd` materialization, mixer, tinyalsa, PCM, HAL, playback, or `adsprpc` action.
- A fresh exact AUD-3-preflight operator gate is still required before any live retry.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py tests/test_native_audio_snd_nodes_preflight_handoff_v2335.py`: PASS.
- `python3 workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py --dry-run`: PASS.
- `python3 -m unittest discover -s tests -p 'test_native_audio_snd_nodes_preflight_handoff_v2335.py'`: PASS (`7` tests).
- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS (`1003` tests).
- `git diff --check`: PASS.

## Next Step

The runner is now ready to retry the V2334 AUD-3 preflight materializer, but only after a fresh exact operator gate:

```text
AUD-3-preflight go: materialize ALSA /dev/snd nodes only on V2334, no open/ioctl/mixer/playback, rollback to V2321
```
