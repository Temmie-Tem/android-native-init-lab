# NATIVE_INIT_V2383_AUD4_ROUTE_VALUE_ENCODING_FIX_2026-06-15

## Scope

Host-only fix for the V2382 AUD-4 blocker. No device flash, no mixer write, and no playback were executed.

## Problem

V2382 proved the V2381 route transport fix but stopped on the first string-valued route switch:

```text
apply-453-SLIMBUS_0_RX Audio Mixer MultiMedia1
Error: only enum types can be set with strings
[exit 22]
```

The control name was preserved correctly by serial `cmdv1x`, so this was no longer a transport/splitting issue. The blocker was value encoding: Android `tinymix --all-values` prints `BOOL` values as `On`/`Off`, but this tinyalsa `tinymix` build accepts string values only for enum controls.

## Change

`workspace/public/src/scripts/revalidation/native_audio_speaker_route_recipe_v2378.py` now encodes `BOOL` controls numerically:

```text
Off -> 0
On  -> 1
```

Enum controls keep their selected string values. Integer controls are unchanged.

This updates both the standalone V2378 recipe dry-run and the V2379/V2381 speaker pilot dry-run because the live runner imports the recipe plan.

## Dry-Run Evidence

Selected route controls after the fix:

```text
SLIMBUS_0_RX Audio Mixer MultiMedia1 BOOL active=['1', '0'] baseline=['0', '0']
SLIM RX0 MUX ENUM active=['AIF1_PB'] baseline=['ZERO']
RX INT7_1 MIX1 INP0 ENUM active=['RX0'] baseline=['ZERO']
COMP7 Switch BOOL active=['1'] baseline=['0']
SpkrLeft SWR DAC_Port Switch BOOL active=['1'] baseline=['0']
```

The live pilot dry-run now emits the previously failing command as numeric bool values:

```text
/cache/a90-runtime/bin/v2379-speaker-pilot/tinymix -D 0 \
  'SLIMBUS_0_RX Audio Mixer MultiMedia1' 1 0
```

Pilot dry-run remains `ok=True` and keeps `route_transport=serial`.

## Magisk Direction

Unchanged: Magisk remains Android-side measurement/delivery fallback only. It is not needed for this native route encoding fix and must not become a dependency of AUD-4 native playback.

## Validation

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_speaker_route_recipe_v2378.py \
  tests/test_native_audio_speaker_route_recipe_v2378.py \
  workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py \
  tests/test_native_audio_speaker_pilot_live_handoff_v2379.py
PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_speaker_route_recipe_v2378 \
  tests.test_native_audio_speaker_pilot_live_handoff_v2379 -v
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_route_recipe_v2378.py --dry-run
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py --dry-run
```

Focused tests pass. They now assert numeric `BOOL` command values and preserved enum strings.

## Next

Retry the exact-gated AUD-4 live run once. Expected first discriminator: whether `apply-453-SLIMBUS_0_RX Audio Mixer MultiMedia1 1 0` succeeds. If it does, continue through the remaining route controls to bounded `tinyplay`; if any later control fails, stop, rollback, and classify the next exact encoding or route blocker.
