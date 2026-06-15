# NATIVE_INIT V2539 — ACDB acdb_ioctl enter-trace discriminator

Date: 2026-06-16  
Scope: ACDB own-process measurement path, single combined ARM32 preload with pre-return `acdb_ioctl` call logging.  
Result: **new discriminator captured; rollback clean**.

## Purpose

V2538 eliminated multi-`LD_PRELOAD` ambiguity but still produced zero `ioctl_trace` and zero `acdbtap` rows, timing out at `ACDB_CMD_INITIALIZE_V2`. The ambiguity left open was whether the `acdb_ioctl` wrapper never ran, or whether it ran and the wrapped real `acdb_ioctl` never returned.

V2539 adds a bounded enter-trace variant:

- Reuses the V2475 `acdb_ioctl` wrapper source, but compiles it with `A90_ACDBTAP_LOG_ENTER=1`.
- Emits lightweight `acdb_ioctl_call` rows before resolving/calling the real `acdb_ioctl`.
- Links the same V2531 `ioctl` fake/trace wrapper into one ARM32 shared object.
- Runs through the existing V2490 own-process handoff with `A90_ACDB_FAKE_ALLOCATE=1`.

This remains measurement-only: no native speaker write, no committed raw payloads, no persistent module install, and no native replay.

## Implementation

Public changes:

- `workspace/public/src/android/acdb_payload_capture/libacdbtap_v2475.c`
  - Adds compile-time optional enter logging with `A90_ACDBTAP_LOG_ENTER`.
  - Emits `event=acdb_ioctl_call` rows with phases `enter`, `before_real`, and `resolve_failed`.
- `workspace/public/src/scripts/revalidation/build_android_acdb_enter_combined_preload_v2539.py`
  - Builds one ARM32 `.so` from the enter-logging `acdb_ioctl` object plus the V2531 `ioctl` fake/trace object.
- `workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py`
  - Separates `acdbtap` output rows from `acdb_ioctl_call` enter rows.
  - Adds classifications for enter-only/no-return cases.
- `tests/test_build_android_acdb_enter_combined_preload_v2539.py`
- `tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py`

Private build artifact:

- Path: `workspace/private/builds/audio/v2539-acdb-enter-combined-preload-host-only/bin/liba90_acdb_enter_combined_preload_v2539.so`
- SHA256: `fd3c0ab0b7ed4432ffad4ec7389414540d576d99eb918376d213d21670fd9617`
- Size: `10124` bytes
- Mode: `0600`
- Exports: `acdb_ioctl` and `ioctl`

## Validation before live

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_acdb_enter_combined_preload_v2539.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  tests/test_build_android_acdb_enter_combined_preload_v2539.py \
  tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_build_android_acdb_enter_combined_preload_v2539 \
  tests.test_build_android_acdbtap_v2475 \
  tests.test_build_android_ioctl_trace_preload_v2531 \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490
```

Result: `Ran 44 tests ... OK`.

Dry-run with the V2539 artifact:

- `build_ok=true`
- `live_ready=true`
- `command_safety.ok=true`
- `combined_preload.ok=true`
- `combined_preload.sha256_ok=true`

Preflight before live:

- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img` exists and SHA256 matches `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v48.img` exists.
- Native V2321 preflight `version` and `selftest verbose` passed with `fail=0`.

## Live execution

Private run directory:

- `workspace/private/runs/audio/v2539-acdb-enter-combined-preload-20260616-071208`

Command shape:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  --run-live \
  --from-native \
  --fake-audio-cal-allocate \
  --use-combined-preload \
  --combined-preload-so workspace/private/builds/audio/v2539-acdb-enter-combined-preload-host-only/bin/liba90_acdb_enter_combined_preload_v2539.so \
  --combined-preload-sha256 fd3c0ab0b7ed4432ffad4ec7389414540d576d99eb918376d213d21670fd9617 \
  --helper-timeout 60 \
  --adb-command-timeout 90 \
  --adb-pull-timeout 180 \
  --out-dir workspace/private/runs/audio/v2539-acdb-enter-combined-preload-20260616-071208
```

## Result

Runner decision:

```text
v2490-helper-timeout-acdbtap-enter-before-real-no-return-before-rollback-rollback-pass
```

Parsed summary:

| Field | Value |
| --- | --- |
| classification | `acdbtap-enter-before-real-no-return` |
| `acdbtap_call_row_count` | `2` |
| `acdbtap_row_count` | `0` |
| `row_count` | `0` |
| `ioctl_trace_event_count` | `0` |
| phases | `enter`, `before_real` |
| cmds | `0x0001138c` |
| full_success | `false` |
| partial_success | `false` |
| operator_valuable | `true` |
| counts_toward_fails_twice | `true` |

Captured `acdbtap-events.jsonl` rows:

```json
{"event":"acdb_ioctl_call","seq":"0x00000000","pid":"0x00000fbd","tid":"0x00000fbd","cmd":"0x0001138c","in_len":"0x00001454","out_len":"0x00000000","phase":"enter"}
{"event":"acdb_ioctl_call","seq":"0x00000000","pid":"0x00000fbd","tid":"0x00000fbd","cmd":"0x0001138c","in_len":"0x00001454","out_len":"0x00000000","phase":"before_real"}
```

The ACDB loader log stopped at the same point:

```text
ACDB-LOADER: ACDB -> ACDB_CMD_INITIALIZE_V2
```

## Interpretation

V2539 closes the V2538 ambiguity:

- The combined preload **does load** and the `acdb_ioctl` wrapper **does intercept** the ACDB init call.
- The intercepted command is `0x1138c`, with `in_len=0x1454` and `out_len=0`.
- The wrapper reaches `before_real`, so `dlsym(RTLD_NEXT, "acdb_ioctl")` succeeded enough to proceed to the real call.
- The real call never returns within the helper timeout, so no output rows or ioctl fake events are produced.

This means the current `acdb_ioctl` interposition strategy perturbs the ACDB initialization command itself. V2535 already proved that with only the `ioctl` fake/trace preload, the same helper gets past init into the custom topology path and emits 57 `ioctl_trace` events. Therefore the blocker is now specifically the `acdb_ioctl` wrapper around command `0x1138c`, not the audio-calibration fake path.

## Rollback and health

The runner rolled back to V2321. Final health check after completion:

```text
version: 0.9.285 build=v2321-usb-clean-identity-rodata
selftest: pass=11 warn=1 fail=0
```

No raw ACDB payload was captured or committed.

## Next

Do not keep retrying generic `acdb_ioctl` preloads. The next useful unit should target one of these specific discriminators:

1. Log the resolved `real_acdb_ioctl` pointer and link-map/library address to exclude wrong-symbol/self-resolution.
2. Build a selective wrapper that does **not** wrap/log command `0x1138c` and only starts observing later commands, if RE confirms this can avoid init perturbation.
3. RE command `0x1138c` and the init dispatch path enough to identify why a wrapper call changes return behavior.

Native replay remains blocked because no `ret==0` non-zero ACDB payload has been captured.
