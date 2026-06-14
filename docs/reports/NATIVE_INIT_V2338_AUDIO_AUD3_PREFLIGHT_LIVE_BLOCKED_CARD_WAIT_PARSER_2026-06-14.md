# Native Init V2338 Audio AUD-3 Preflight Live Blocked By Card-Wait Parser

## Summary

- Cycle: `V2338`
- Track: audio AUD-3 preflight live retry on the V2334 materialization artifact.
- Decision: `aud3-preflight-blocked-before-snd-materialize-card-wait-parser`
- Result: BLOCKED before `/dev/snd` materialization.
- Operator gate: exact `AUD-3-preflight` approval phrase received.
- Candidate flashed: `A90 Linux init 0.9.292 (v2334-audio-snd-nodes-preflight)`.
- Candidate SHA256: `53b1130cd912ca4019a3d76835eb721804bae0460b920eb7fdfad5509a2dfcac`.
- Rollback target: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Private evidence directory: `workspace/private/runs/audio/v2335-snd-nodes-preflight-20260614-225110`.

## Live Result

Completed safely:

1. Dry-run passed with the pinned V2334 candidate and V2321/V2237/V48 rollback/fallback images present.
2. Verified resident V2321 through `native_init_flash.py --verify-only` and `selftest fail=0`.
3. Flashed V2334 through the checked `native_init_flash.py` path with pinned SHA256.
4. Candidate V2334 passed `version`, `status`, and `selftest verbose` after the V2336 slow-input hardening.
5. `audio adsp-status` initially hit one observation-only serial marker loss, then passed on the bounded retry.
6. `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` ran once and returned `write=accepted`.
7. Polling confirmed the ADSP/Q6 side reached the same useful state as V2332: `rpmsg.count=20 adsp_like=7`, `sound_class.count=128 card_like=1 control_like=1`, and `/proc/asound/cards` reported `sm8150-tavil-snd-card`.
8. Automatic rollback to V2321 completed; rollback `version` returned `0.9.285` and rollback `selftest verbose` returned `fail=0`.

Blocked point:

- The runner raised `RuntimeError: ALSA card/control did not appear before timeout` during `wait_for_audio_card()`.
- The last status sample already contained `audio.sound_class.count=128 card_like=1 control_like=1`, but `classify_audio_status()` did not parse inline `control_like=1` from that line into `audio.sound_class.control_like`.
- The same sample had `audio.dev_snd.count=0 control_like=0 pcm_like=0`, with listed sysfs-backed ALSA entries such as `controlC0` and many PCM devices still in `state=missing`.
- Because the wait loop failed before the materializer step, `audio snd-materialize-once AUD3_DEV_SND_MATERIALIZE_ONLY` did **not** run.

Key final V2334 pre-materialization sample:

```text
audio.rpmsg.count=20 adsp_like=7 cdsp_like=0
audio.sound_class.count=128 card_like=1 control_like=1
audio.dev_snd.count=0 control_like=0 pcm_like=0
audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card sm8150-tavil-snd-card
audio.snd.9.name=controlC0 sysfs_dev=116:2 devnode=/dev/snd/controlC0 state=missing
audio.snd_status.entries=128 allowed=61 with_dev=61 listed=61 missing=61 already_ok=0 invalid=0 refused=67 created=0 failed=0
audio.status.audio_playback_attempted=0
```

## Classification

`runner-card-wait-parser-block-before-materializer`

This is not a failed `/dev/snd` materialization result. The materializer command never ran. The useful device finding is that V2334 can again boot ADSP/Q6 and expose the ALSA card/control sysfs inventory, but `/dev/snd` remains empty until the token-gated materializer is allowed to run.

## Safety Boundary Preserved

- No ALSA node open/ioctl.
- No mixer, tinymix, tinyalsa, PCM, HAL, or playback.
- No `adsprpc` invoke/ioctl.
- No `/dev/subsys_adsp` open.
- `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` ran once as expected.
- `audio snd-materialize-once AUD3_DEV_SND_MATERIALIZE_ONLY` did **not** run.
- Boot partition only was flashed.
- Rollback to V2321 completed and final selftest remained `fail=0`.

## Validation

- Live dry-run: PASS.
- V2321 preflight verify: PASS, `selftest fail=0`.
- V2334 candidate flash/readback/boot verify: PASS, `selftest fail=0`.
- V2334 candidate health: PASS, `version/status/selftest verbose`.
- V2321 rollback flash/readback/boot verify: PASS.
- Final rollback health: PASS, `version=0.9.285`, `selftest fail=0`.

## Next Step

Do not rerun live yet. First fix the host runner logic so it treats inline `audio.sound_class.count=... card_like=1 control_like=1` as sufficient card/control presence for the **pre-materialization** gate, and avoids classifying `/dev/snd/control* state=missing` text as existing devnodes. After that host-only fix and tests, a fresh exact AUD-3-preflight operator gate is required before retrying the materializer.
