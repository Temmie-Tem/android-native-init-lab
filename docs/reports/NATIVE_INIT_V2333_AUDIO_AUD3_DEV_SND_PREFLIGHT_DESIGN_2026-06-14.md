# Native Init V2333 Audio AUD-3 `/dev/snd` Preflight Design

## Summary

- Cycle: `V2333`
- Track: audio AUD-3 preflight, host-only design.
- Decision: `aud3-dev-snd-materialization-design-ready`
- Device flash: `no`.
- Device action: `none`.
- Trigger: V2332 closed AUD-2 as pass: ADSP/Q6 came up and `sm8150-tavil-snd-card` appeared, but `/dev/snd` stayed empty.

This unit does not attempt playback. It defines the next safe, reviewable step between AUD-2 liveness and AUD-3 tinyalsa playback: enumerate ALSA sysfs devices and materialize only the matching `/dev/snd/*` character nodes from kernel-provided `major:minor` data.

## Inputs Re-read

- `GOAL.md`: active internal-audio epic; AUD-3 is a fresh operator-gated playback step.
- `AGENTS.md`: boot-only flash, rollback target V2321, no forbidden partitions, scoped commits.
- `CLAUDE.md`: V2332 state says AUD-2 passed; `/dev/snd=0`; AUD-3 remains gated.
- `docs/reports/NATIVE_INIT_V2332_AUDIO_AUD2_V2331_ADSP_LIVENESS_LIVE_2026-06-14.md`
- `docs/reports/NATIVE_INIT_V2331_AUDIO_ADSP_FWCLASS_NATIVE_PATH_SOURCE_BUILD_2026-06-14.md`
- `git log --oneline -10`

## V2332 Evidence Boundary

V2332 post-activation evidence after the long hold:

```text
audio.rpmsg.count=20 adsp_like=7 cdsp_like=0
audio.rpmsg_class.count=2
audio.fastrpc_class.count=2
audio.sound_class.count=128 card_like=1 control_like=1
audio.dev_snd.count=0 control_like=0 pcm_like=0
audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card sm8150-tavil-snd-card
```

Timing mattered in V2332: at about 5 seconds after the ADSP boot write, rpmsg had started but `/proc/asound/cards` still showed no soundcards. At about 38 seconds, the card appeared and stayed present through the hold. Any future live AUD-3 preflight must wait for `audio.proc_asound_cards` and `/sys/class/sound` card/control evidence before node materialization.

## Source Findings

Current `workspace/public/src/native-init/a90_audio.c` only reports sound state:

- `print_class_counts()` counts `/sys/class/sound` and `/dev/snd` entries.
- `audio_print_adsp_status()` prints the counts and `/proc/asound/cards`.
- `audio_adsp_boot_once()` refuses a second write when `/sys/class/sound/card*` or `/dev/snd/controlC*` is already present.
- There is no active audio-specific `/dev/snd` materializer and no playback path.

The active root source tree has existing sysfs-to-mknod precedents:

- `a90_input.c` reads `/sys/class/input/<event>/dev` and creates `/dev/input/<event>` with `S_IFCHR | 0600`.
- `a90_kms.c` reads `/sys/class/drm/card0/dev`, creates `/dev/dri/card0`, and accepts an already-correct char node.
- `a90_storage.c` uses stricter exact-node validation for block devices, including `st_rdev` matching.

The old `v319` legacy shell had generic `mknodc`/`mknodb`, but the active command surface does not expose that generic writer. AUD-3 should not revive generic arbitrary mknod. It needs an audio-specific allowlist fed only by `/sys/class/sound/*/dev`.

The Samsung open-source drop available in `workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel` does not contain the stripped `sound/` core tree, matching the already recorded AUD-0 fact that the stock boot image carries proprietary/built-in audio pieces not present in the public drop. The runtime sysfs evidence is therefore the authoritative live source for `major:minor` data.

## Root Cause Hypothesis

The AUD-2 result is consistent with a native-init userspace gap, not an ADSP/kernel liveness failure:

1. The kernel publishes the ALSA card in `/sys/class/sound` and `/proc/asound/cards`.
2. Android normally uses `ueventd`/device-node policy to create `/dev/snd/*` nodes.
3. This native init does not run Android `ueventd` and currently has no audio node materializer.
4. Therefore tinyalsa likely cannot proceed until `/dev/snd/controlC0` and relevant `pcmC*D*[pc]` nodes exist.

This is not proof that playback will work; it only identifies the next missing userspace bridge before playback can be tested.

## Proposed Staging

### V2334 — Source/build-only: ALSA node inventory + gated materializer

Implement in `a90_audio.c`:

- `audio snd-status`: read-only enumeration of `/sys/class/sound/*` entries.
  - Print each allowed node basename, its `/sys/class/sound/<name>/dev` value, parsed major/minor, and whether `/dev/snd/<name>` exists and matches `st_rdev`.
  - Include card/control/pcm totals and `/proc/asound/cards`.
- `audio snd-materialize-once AUD3_DEV_SND_MATERIALIZE_ONLY`: no playback, no open/ioctl of the created nodes.
  - Create `/dev/snd` with `0755` if missing.
  - Only accept basenames matching a strict allowlist:
    - `controlC[0-9]+`
    - `pcmC[0-9]+D[0-9]+p`
    - `pcmC[0-9]+D[0-9]+c`
    - optionally `timer` and `seq` if present in `/sys/class/sound` and carrying a valid `dev` attribute.
  - Read only `/sys/class/sound/<basename>/dev`; parse `major:minor`.
  - Create `S_IFCHR | 0600` nodes at `/dev/snd/<basename>`.
  - If a node exists, accept it only when it is a char device and `st_rdev` matches; otherwise refuse and report, not unlink.
  - Never create paths from arbitrary arguments; never traverse out of `/dev/snd`; never infer major/minor.
  - Print a one-shot summary: discovered, created, already_ok, refused, failed.
- Keep `audio adsp-boot-once` unchanged: still AUD-2-only, token-gated, and not safe-retryable.
- Update controller policy so `snd-status` is menu/power safe but `snd-materialize-once` is blocked from menu/power contexts like `adsp-boot-once`.

V2334 remains source/build-only. It must run `py_compile` for the build wrapper, cross-compile/file through the build script, full unittest, and `git diff --check`. No device action.

### V2335 — Device, operator-gated: materialization-only live check

Requires a fresh explicit operator phrase, separate from AUD-2 and separate from AUD-3 playback, for example:

```text
AUD-3-preflight go: materialize ALSA /dev/snd nodes only on V2334, no open/ioctl/mixer/playback, rollback to V2321
```

Bounded live sequence:

1. Reconfirm V2321/V2237/V48 rollback images and bridge health.
2. Flash only the V2334 boot artifact through `native_init_flash.py` with expected SHA.
3. Health check: `version`, `status`, `selftest verbose` must stay `fail=0`.
4. Run AUD-2 activation only if the card is not already up, using the existing AUD-2 token and one-shot semantics.
5. Wait until `/proc/asound/cards` reports `sm8150-tavil-snd-card` and `/sys/class/sound` reports at least one card/control entry, with a bounded timeout.
6. Run `audio snd-status`.
7. Run `audio snd-materialize-once AUD3_DEV_SND_MATERIALIZE_ONLY` exactly once.
8. Run `audio snd-status` again and confirm `/dev/snd/controlC0` plus at least one relevant `pcmC*` node exists when sysfs advertised it.
9. Hold briefly, confirm `selftest fail=0`, then rollback to V2321 and confirm rollback health.

Hard stop conditions:

- No `/sys/class/sound/*/dev` entries after card appears.
- Only card text appears but no control/PCM sysfs device appears.
- Any existing `/dev/snd/*` path is not a matching char device.
- Any materialization failure returns nonzero.
- Any selftest regression or device unreachable condition.

### Later AUD-3 — Device, operator-gated: first playback attempt

Playback remains out of scope until V2335 materialization-only passes. A future AUD-3 live attempt needs a fresh approval phrase and its own design, likely including:

- exact tinyalsa binary/source provenance,
- safe mixer route selection from `mixer_paths_tavil.xml`,
- bounded low-volume PCM payload,
- no modem/call-audio/q6voice path,
- no full HAL unless a separate design proves it is required and safe.

## Safety Boundary

- This V2333 unit is host-only and does not modify source.
- No flash, ADSP write, ALSA node creation, mixer, tinyalsa, PCM, HAL, adsprpc invoke/ioctl, or `/dev/subsys_adsp` open was run.
- The next live step must not be called "AUD-3 playback"; it is only `/dev/snd` materialization preflight.
- Actual playback remains a separate fresh operator-gated risk domain.
- All device variants keep V2321 as rollback target and may only flash the boot partition through `native_init_flash.py`.

## Validation

- Host source inspection: PASS.
- V2332 private evidence review: PASS.
- `git diff --check`: PASS.
