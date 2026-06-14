# Native Init V2332 Audio AUD-2 V2331 ADSP Liveness Live

## Summary

- Cycle: `V2332`
- Track: audio AUD-2 live ADSP liveness probe.
- Decision: `aud2-adsp-liveness-pass-alsa-card-present`
- Result: PASS for AUD-2.
- Operator gate: AUD-2 live approval received in chat.
- Candidate flashed: `A90 Linux init 0.9.291 (v2331-audio-adsp-fwclass-native-path)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v2331_audio_adsp_fwclass_native_path.img`
- Candidate SHA256: `8d3e95f7a638fff508d893ee321c0569a04debbad2d16ed7c34188c0a9d9de74`
- Rollback target: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence directory: `workspace/private/runs/audio/v2332-aud2-v2331-fwclass-native-path-20260614-215602`

## Live Flow

1. Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, latest audio reports, and recent git log for the V2332 iteration.
2. Confirmed rollback/fallback images by SHA256:
   - V2331 candidate matched `8d3e95f7a638fff508d893ee321c0569a04debbad2d16ed7c34188c0a9d9de74`.
   - V2321 rollback matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
   - V2237 fallback matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
   - V48 final fallback existed and hashed to `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
3. Confirmed pre-flash resident V2321 health: `selftest fail=0`.
4. Flashed V2331 through `workspace/public/src/scripts/revalidation/native_init_flash.py` only, with pinned `--expect-sha256`.
5. V2331 booted and passed `version`, `status`, and `selftest verbose` with `fail=0`.
6. Ran `audio adsp-status` before activation and confirmed the effective firmware loader path now exposed the complete sparse ADSP set.
7. First `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` command hit the UI busy guard before reaching the handler; `activation_write_attempted` stayed `0`.
8. Re-ran the same token command once with `--hide-on-busy`; the audio handler accepted the single AUD-2 write.
9. Observed ADSP/Q6 liveness via new rpmsg ADSP-like endpoints, sound class card/control presence, and `/proc/asound/cards`.
10. Held for about 30 seconds and re-read `audio adsp-status`; the ALSA card remained present and selftest stayed `fail=0`.
11. Rolled back to V2321 through `native_init_flash.py` with pinned `--expect-sha256`.
12. Confirmed V2321 restored and final `selftest verbose` returned `fail=0`.

## Key Evidence

Pre-activation firmware loader path was corrected by V2331:

```text
audio.firmware_class_path=/vendor/firmware_mnt/image
audio.firmware_class.adsp_mdt=yes
audio.firmware_class.adsp_segments_present=16 expected=16
audio.firmware_class.adsp_segments_missing=none
audio.firmware_class.adsp_complete=yes
```

The actual AUD-2 write was accepted exactly once after the busy-guard retry:

```text
audio.adsp_boot_once.version=1
audio.adsp_boot_once.scope=AUD-2-liveness-only
audio.status.audio_playback_attempted=0
audio.status.activation_write_attempted=1
audio.adsp_boot_once.write=accepted
audio.adsp_boot_once.retry=forbidden
```

Post-activation ADSP/Q6 and ALSA-card evidence:

```text
audio.rpmsg.count=20 adsp_like=7 cdsp_like=0
audio.rpmsg_class.count=2
audio.fastrpc_class.count=2
audio.sound_class.count=128 card_like=1 control_like=1
audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card sm8150-tavil-snd-card
```

Thirty-second hold retained the same card evidence and selftest stayed clean:

```text
audio.rpmsg.count=20 adsp_like=7 cdsp_like=0
audio.sound_class.count=128 card_like=1 control_like=1
audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card sm8150-tavil-snd-card
selftest: pass=11 warn=1 fail=0
```

Rollback health:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

## Classification

`aud2-adsp-liveness-pass-alsa-card-present`

V2331 fixed the effective firmware serve-path blocker from V2330. With `firmware_class.path` left at the boot cmdline path `/vendor/firmware_mnt/image`, the ADSP firmware preflight passed, the single gated `/sys/kernel/boot_adsp/boot` write was accepted, and the stock kernel brought up ADSP/Q6 enough to publish ADSP rpmsg endpoints and the `sm8150-tavil-snd-card` ALSA card.

This closes AUD-2's stated success condition: DSP comes up and a sound card appears. It does not prove playback.

## Residual Boundary Before AUD-3

- `/dev/snd` node count remained `0` even though `sound_class` and `/proc/asound/cards` show a card. AUD-3 needs a fresh design/preflight for safe ALSA device-node materialization or proof that tinyalsa can open the card path available under this native-init environment.
- No mixer route, `tinymix`, `tinyplay`, PCM, HAL, adsprpc invoke/ioctl, `/dev/subsys_adsp` open, or audio playback was attempted.
- AUD-3 remains a separate operator-gated device-risk step.

## Safety Result

- Boot partition only was flashed.
- Flash path was only `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- No forbidden partitions were touched.
- ADSP activation: exactly one accepted AUD-2 liveness write after preflight; no retry after acceptance.
- Audio playback/mixer/HAL/tinyalsa: not attempted.
- `/dev/subsys_adsp` open: not attempted.
- adsprpc invoke/ioctl: not attempted.
- Rollback to V2321 completed and final selftest remained `fail=0`.
