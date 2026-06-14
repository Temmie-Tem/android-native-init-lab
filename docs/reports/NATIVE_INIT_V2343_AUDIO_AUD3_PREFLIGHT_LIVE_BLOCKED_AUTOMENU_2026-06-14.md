# NATIVE_INIT V2343 — AUD-3 preflight live blocked by auto-menu busy

Date: 2026-06-14  
Scope: DEVICE, exact-gated AUD-3 `/dev/snd` materialization preflight  
Runner: `workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py`  
Private evidence: `workspace/private/runs/audio/v2335-snd-nodes-preflight-20260614-233039/`

## Gate

Operator approval was present for the runner's exact phrase:

```text
AUD-3-preflight go: materialize ALSA /dev/snd nodes only on V2334, no open/ioctl/mixer/playback, rollback to V2321
```

Hard boundary retained:

- No ALSA open/ioctl.
- No mixer, `tinymix`, `tinyplay`, PCM playback, or audio HAL.
- No adsprpc invoke/ioctl.
- No `/dev/subsys_adsp` open.
- Maximum one `audio snd-materialize-once` command, which was never reached in this run.

## Images

| Role | Image | SHA256 | Result |
| --- | --- | --- | --- |
| Candidate | `workspace/private/inputs/boot_images/boot_linux_v2334_audio_snd_nodes_preflight.img` | `53b1130cd912ca4019a3d76835eb721804bae0460b920eb7fdfad5509a2dfcac` | Flashed and booted |
| Rollback | `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img` | `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb` | Restored |
| Fallback | `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img` | `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f` | Present |
| Final fallback | `workspace/private/inputs/boot_images/boot_linux_v48.img` | recorded privately | Present |

## Execution summary

1. Resident V2321 verify-only passed: `selftest fail=0`.
2. V2334 candidate flashed through the checked `native_init_flash.py` path.
3. V2334 booted and passed initial health:
   - version `0.9.292 (v2334-audio-snd-nodes-preflight)`
   - `selftest fail=0`
4. Initial audio read-only state on V2334:
   - firmware path complete under `/vendor/firmware_mnt/image`
   - `audio.remoteproc.count=0`
   - `audio.rpmsg.count=13 adsp_like=0 cdsp_like=0`
   - `audio.sound_class.count=1 card_like=0 control_like=0`
   - `audio.dev_snd.count=0 control_like=0 pcm_like=0`
   - `/proc/asound/cards` reported no sound cards
   - `/dev/snd/timer` was listed as expected but missing as a devnode
5. The runner attempted the token-gated `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` step.
6. Native init rejected that command before ADSP activation:

```text
[busy] auto menu active; send hide/q before command
A90P1 END seq=9 cmd=audio rc=-16 errno=16 duration_ms=0 flags=0x0 status=busy
```

The serial recovery layer sent `hide` after detecting busy, but the command was correctly not retried because `adsp-boot-once` is token-gated and unsafe to retry automatically.

## Result

Decision: `blocked-runner-auto-menu-before-adsp-boot`.

This is not evidence that ADSP boot or `/dev/snd` materialization fails. The run stopped before the ADSP write, before `audio snd-materialize-once`, and before any ALSA operation.

Rollback completed successfully:

- V2321 restored by `native_init_flash.py`.
- Rollback version check returned `0.9.285 (v2321-usb-clean-identity-rodata)`.
- Rollback selftest returned `fail=0`.
- A post-run direct `a90ctl selftest verbose` also returned `fail=0`.

## Root cause

The remaining blocker is runner control sequencing after candidate boot: the automatic menu can still be active when the first token-gated audio command is issued. The transport recovery helper can repair read-only observations, but it intentionally refuses to retry one-shot mutation commands.

## Next unit

Host-only fix before another live attempt:

- Add an explicit pre-hide / menu-settle step before each token-gated one-shot audio command.
- Keep token-gated commands non-retried after dispatch.
- Add regression coverage proving the command plan hides/settles before `adsp-boot-once` and `snd-materialize-once`.
- Re-run AUD-3 live only with a fresh exact approval gate.
