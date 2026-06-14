# NATIVE_INIT V2362 — Android speaker route-delta capture design

Date: 2026-06-15

## Scope

Host-only AUD-3D2 design after V2361. No bridge command, no flash, no Android boot,
no ADSP command, no `/dev/snd` materialization, no `tinymix set`, no PCM open/write,
no `tinyplay`, no audio HAL execution on the host, and no device mutation.

Goal: design the next safe way to learn the stock Android speaker mixer route before
any native internal-speaker playback attempt.

## Result

Decision: `v2362-android-route-delta-design-ready-helper-gap`.

The correct next measurement is a rollbackable Android route-delta capture: boot
normal Android, use Android's own framework/HAL path to produce a bounded low-amplitude
speaker playback event, capture `tinymix --all-values` before/during/after, then roll
back to V2321 and diff the mixer state offline.

However, the current checked flash helper is native-init verify oriented. Historical
Android handoff scripts used direct recovery-side `dd`; that is no longer allowed by
`AGENTS.md`. Therefore a live Android route-delta run must first add or wrap a checked
flash-helper mode that can flash a pinned Android boot image and verify **Android ADB
normal-device availability**, not native serial `version/status`, before later restoring
V2321 through the same checked helper.

## Why this beats native speaker guessing

V2361 showed the native speaker route is unresolved:

- platform mapping says speaker backend/interface is `SEC_TDM_RX_0`,
- live native tinymix exposes `SEC_TDM_RX_0 Audio Mixer MultiMedia*`, `WSA_CDC_DMA_RX_0*`,
  `COMP7`, and `RX INT7*`,
- vendor `mixer_paths_tavil.xml` still routes `deep-buffer-playback speaker` through
  `SLIMBUS_0_RX Audio Mixer MultiMedia1` plus `spk` controls that are missing by exact
  live name.

A guessed native `tinymix set` sequence would be acting on smart-amp / SoundWire / ADSP
state without a proven reset path. Android already knows the vendor HAL route. Capturing
Android's actual control delta is the shortest safe path to a grounded native speaker
route, or to a defensible "HAL mandatory" conclusion.

## Existing reusable pieces

| Piece | Current state | V2362 use |
| --- | --- | --- |
| V1521/V1753 Android handoff pattern | historical Magisk/Android boot handoff and rollback logic exists under `workspace/public/archive/scripts/revalidation/` | reuse concepts only; do **not** reuse direct `dd` flash path |
| V2345 tinyalsa tools | static AArch64 `tinymix`/`tinypcminfo`/`tinyplay` staged privately | reuse `tinymix` only for read-only Android mixer snapshots |
| V2359 native inventory | canonical native `tinymix --all-values` baseline for materialized V2334 | diff Android-active controls against native-visible names |
| Android boot candidate | `workspace/private/backups/baseline_a_20260423_030309/boot.img` and duplicate `...025322/boot.img`, both 64 MiB `ANDROID!`, SHA256 `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b` | usable private candidate, but future preflight must verify SHA/magic and never commit it |
| Rollback | V2321 SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`; V2237/V48 deeper fallbacks | mandatory before any live run |

## Flash-helper gap

`workspace/public/src/scripts/revalidation/native_init_flash.py` currently:

1. inspects a pinned local boot image,
2. optionally requests native `recovery`,
3. waits for TWRP/recovery ADB,
4. pushes and writes boot via its checked implementation,
5. reboots system,
6. verifies native-init over the serial bridge.

That final native serial verification is correct for native images, but wrong for an
Android handoff. A compliant Android route-delta runner needs one of these before live use:

- **Preferred:** add an explicit checked-helper target mode such as `--post-flash-target android-adb`,
  which after reboot waits for `adb` state `device` and optionally verifies `su -c id`.
- **Acceptable wrapper:** call a shared checked flash primitive from a new runner, but keep the boot
  write/readback implementation inside the checked helper path, not inline `dd`.

Direct recovery `dd`, direct `fastboot`, or a copied flash implementation is out of scope.

## Proposed live flow after helper support

All steps are future design. None were run in V2362.

1. **Preflight**
   - verify V2321, V2237, and V48 fallback images exist and match pinned SHA values,
   - verify TWRP/recovery availability,
   - verify current native V2321 bridge health: `version`, `status`, `selftest fail=0`,
   - verify Android boot candidate: regular file, 4 KiB aligned, `ANDROID!` magic, SHA
     `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`,
   - verify static `tinymix` SHA from V2345.

2. **Boot Android through checked helper**
   - flash only the boot partition with the pinned Android boot candidate,
   - post-flash target is Android ADB `device`, not native serial,
   - verify root availability with a redacted `su -c id` check,
   - do not start Wi-Fi, use credentials, DHCP, routes, or network.

3. **Stage temporary route-delta tools**
   - create `/data/local/tmp/a90-audio-route-delta/`,
   - push static `tinymix`,
   - push a small `app_process`/`AudioTrack` playback jar or dex,
   - do not install an APK and do not persist to system/vendor/data app locations.

4. **Baseline snapshots**
   - `/data/local/tmp/a90-audio-route-delta/tinymix -D 0 --all-values`,
   - `dumpsys audio`, `dumpsys media.audio_flinger`, and `dumpsys media.audio_policy`,
   - `/proc/asound/cards`, `/proc/asound/pcm`, selected `/sys/class/sound` metadata,
   - filtered `logcat -d` and `dmesg` for audio HAL / AudioFlinger / AudioPolicy / WSA / SEC_TDM strings.

5. **Playback stimulus**
   - run a one-shot framework playback helper using `AudioTrack`, not `tinyplay`, so the
     path goes through Android AudioFlinger / audio policy / vendor HAL,
   - parameters: speaker/default route, 48 kHz stereo S16 PCM, low amplitude, short duration
     (about 2 seconds), no loop,
   - do not run `tinymix set`, do not open native `/dev/snd` directly, and do not adjust
     mixer controls manually.

6. **Active and post snapshots**
   - capture `tinymix -D 0 --all-values` while playback is active at multiple offsets,
   - capture the same dumpsys/logcat/dmesg filters,
   - capture post-playback snapshots after route teardown,
   - pull all evidence to `workspace/private/runs/audio/v236X-android-route-delta-*`,
   - delete the temporary Android directory.

7. **Rollback**
   - reboot recovery,
   - restore V2321 using the checked helper with pinned SHA and native serial verification,
   - require final `version/status/selftest fail=0`.

## Offline parser / classifier

The postprocessor should parse `tinymix --all-values` snapshots into a stable map:

```text
control_name -> type, num_values, values[]
```

Then classify deltas:

- **route-on controls:** baseline off/zero/enum A -> active on/nonzero/enum B,
- **route-cleanup controls:** active value returns to baseline after playback,
- **sticky controls:** active differs from baseline and does not return; these require special
  caution and cannot be copied into native until a reset path is known,
- **noise controls:** counters, timestamps, unrelated gains, or controls that change without
  matching audio route evidence.

Priority names for the speaker problem:

- `SEC_TDM_RX_0 Audio Mixer*`,
- `WSA_CDC_DMA_RX_0*`,
- `RX INT7*`,
- `COMP7*`,
- `Spkr*` / `SPKR*`,
- `SLIMBUS_0_RX Audio Mixer*`.

## Branch outcomes

| Outcome | Meaning | Next action |
| --- | --- | --- |
| `android-route-delta-speaker-controls-found` | Android reveals exact SEC_TDM/WSA/RX/COMP control set and cleanup | design a native exact-gated speaker smoke using only that minimal route |
| `android-playback-active-no-mixer-delta` | AudioFlinger/HAL plays but mixer state does not visibly change | route may be preconfigured, hidden below tinymix, or HAL/ACDB mandatory; inspect dumpsys/logcat before native writes |
| `android-playback-trigger-failed` | Android boot/root works but AudioTrack helper cannot start playback | fix the Android playback stimulus; do not fall back to native `tinyplay` as route evidence |
| `android-handoff-helper-gap` | checked helper cannot support Android target verification | implement helper target-mode support first |
| `rollback-failed` | V2321 restore or selftest fails | stop the loop and write incident report; no further flash |

## Exact future gate

Suggested future approval phrase after the helper gap is closed:

```text
AUD-3D2-android-route-delta go: rollbackable Android AudioTrack speaker route-delta capture, checked-helper boot handoff only, low-amplitude framework playback, no native speaker write, rollback to V2321
```

That phrase permits Android framework playback only. It does **not** permit native `tinymix set`,
`tinyplay`, PCM playback under native init, speaker route writes under native init, Wi-Fi, network,
credentials, or any partition write other than boot through the checked helper.

## Safety outcome

- Host-only design.
- No live device command.
- No flash.
- No Android boot.
- No mixer write.
- No PCM open/write.
- No playback.
- No proprietary binary or raw log committed.

## Validation

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and `git log --oneline -15`: PASS.
- Inspected V2361/V2360/V2359 reports: PASS.
- Inspected historical Android handoff engines (`V1521`, `V1753`, `V1899`): PASS.
- Verified private Android boot candidates are 64 MiB `ANDROID!` images with SHA256
  `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`: PASS.
- Inspected `native_init_flash.py` and identified native-only post-flash verification gap: PASS.
- Consulted AOSP `AudioService` / `AudioManagerShellCommand` source to avoid assuming `cmd audio`
  can provide deterministic playback; route-delta design uses `AudioTrack` instead: PASS.
- `git diff --check`: PASS.

## External references

- AOSP `AudioService.java` shell-command entry point: https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/audio/AudioService.java
- AOSP `AudioManagerShellCommand.java` command surface: https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/audio/AudioManagerShellCommand.java
