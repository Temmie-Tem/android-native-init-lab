# NATIVE_INIT_V2348_AUDIO_SND_MATERIALIZE_LIVE_PASS

Date: 2026-06-15
Scope: exact-gated AUD-3 `/dev/snd` materialization preflight
Runner: `workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py`
Private evidence: `workspace/private/runs/audio/v2335-snd-nodes-preflight-20260615-001534/`

## Operator Gate

The live run used the exact required phrase:

```text
AUD-3-preflight go: materialize ALSA /dev/snd nodes only on V2334, no open/ioctl/mixer/playback, rollback to V2321
```

Allowed live action was bounded to:

- verify current V2321 rollback checkpoint,
- flash V2334 `0.9.292 (v2334-audio-snd-nodes-preflight)`,
- run the token-gated ADSP boot once if needed,
- run the token-gated `/dev/snd` materializer once,
- observe `audio snd-status`,
- rollback to V2321 and verify health.

Explicitly out of scope and not performed:

- ALSA open/ioctl,
- mixer/tinymix writes,
- `tinyplay` / PCM playback,
- audio HAL,
- adsprpc invoke/ioctl,
- `/dev/subsys_adsp` open.

## Inputs

Candidate boot image:

- path: `workspace/private/inputs/boot_images/boot_linux_v2334_audio_snd_nodes_preflight.img`
- expected SHA256: `53b1130cd912ca4019a3d76835eb721804bae0460b920eb7fdfad5509a2dfcac`
- version expected: `0.9.292`

Rollback boot image:

- path: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- expected SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- version expected: `0.9.285`

Deeper fallbacks were present:

- V2237 SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- V48 image existed

## Timeline Summary

1. V2321 preflight verify passed: `selftest fail=0`.
2. V2334 flash passed: boot readback SHA matched candidate SHA, V2334 booted, and candidate selftest passed.
3. Before ADSP/materialization, `audio adsp-status` showed no ADSP rpmsg and no `/dev/snd` nodes.
4. Token-gated `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` ran once.
5. ADSP/Q6 came up again: `audio.rpmsg.count=20 adsp_like=7 cdsp_like=0`.
6. Before materialization, sound class was populated but `/dev/snd` was empty:
   - `audio.sound_class.count=128 card_like=1 control_like=1`
   - `audio.dev_snd.count=0 control_like=0 pcm_like=0`
   - `audio.snd_status.entries=128 allowed=61 with_dev=61 listed=61 missing=61 already_ok=0 invalid=0 refused=67 created=0 failed=0`
7. Token-gated `audio snd-materialize-once AUD3_DEV_SND_MATERIALIZE_ONLY` ran once.
8. Materializer created all allowed device nodes and did not open/ioctl/playback:
   - `audio.snd_materialize.entries=128 allowed=61 with_dev=61 listed=61 missing=61 already_ok=0 invalid=0 refused=67 created=61 failed=0`
   - `audio.snd_materialize.open_attempted=0`
   - `audio.snd_materialize.ioctl_attempted=0`
   - `audio.snd_materialize.playback_attempted=0`
9. After materialization, `/dev/snd` was populated:
   - `audio.dev_snd.count=61 control_like=1 pcm_like=59`
   - `audio.snd_status.entries=128 allowed=61 with_dev=61 listed=61 missing=0 already_ok=61 invalid=0 refused=67 created=0 failed=0`
   - `audio.status.audio_playback_attempted=0`
10. Candidate selftest after materialization passed: `fail=0`.
11. Rollback to V2321 passed: boot readback SHA matched V2321 SHA, V2321 booted, final version was `0.9.285`, and final `selftest fail=0`.

## Result

Runner decision:

```text
v2335-snd-materialize-live-pass-before-rollback
```

Structured result fields:

```json
{
  "rolled_back": true,
  "before_materialize": {
    "audio.sound_class.count": "128",
    "audio.sound_class.card_like": "1",
    "audio.sound_class.control_like": "1",
    "audio.dev_snd.count": "0",
    "audio.dev_snd.control_like": "0",
    "audio.dev_snd.pcm_like": "0"
  },
  "after_materialize": {
    "audio.sound_class.count": "128",
    "audio.sound_class.card_like": "1",
    "audio.sound_class.control_like": "1",
    "audio.dev_snd.count": "61",
    "audio.dev_snd.control_like": "1",
    "audio.dev_snd.pcm_like": "59"
  },
  "rollback_version_ok": true,
  "rollback_selftest_fail0": true
}
```

## Interpretation

AUD-3 `/dev/snd` materialization preflight is now closed as **PASS**:

- ADSP/Q6 can be booted under native init in V2334.
- The stock ALSA sound class exposes the `sm8150-tavil-snd-card` control/PCM device metadata.
- Native init can create the allowed `/dev/snd` device nodes from sysfs major/minor data.
- The materializer created 61 nodes and refused 67 non-device entries.
- No ALSA open/ioctl, mixer command, PCM write, audio HAL, adsprpc invoke, or playback path was touched.
- Device was rolled back to V2321 and health-checked cleanly.

This does **not** prove audio playback. It only removes the `/dev/snd` node absence as the next blocker.

## Next Safe Step

The next step should be a separate exact-gated tinyalsa inventory run, not playback:

1. flash an audio-capable test image that includes or stages the V2345 tinyalsa tools,
2. bring up ADSP/Q6,
3. materialize `/dev/snd`,
4. run read-only `tinypcminfo` / `tinymix` inventory only,
5. rollback to V2321.

Playback remains a later, separately gated step after read-only mixer/PCM inventory identifies a safe route and PCM device.
