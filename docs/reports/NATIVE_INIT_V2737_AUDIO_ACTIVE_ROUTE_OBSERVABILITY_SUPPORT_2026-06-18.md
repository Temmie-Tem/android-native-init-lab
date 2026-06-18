# NATIVE_INIT V2737 — Active-route audio observability runner support

Date: 2026-06-18

## Scope

Host-only runner update following V2736.  V2735 proved the native route can pass
`pcm_prepare` and write a full bounded PCM buffer, but listener-visible output is
not independently proven.  V2737 adds active-route observation points to the
existing V2639 replay runner so the next live cycle can capture mixer state while
the known speaker route is still applied.

No device action in this unit.

## Decision

`v2737-active-route-observability-support-ready`

The runner now captures these additional artifacts before route reset:

- full `tinymix -D 0 --all-values` snapshot after route apply + ACDB replay,
  before PCM starts;
- focused mixer snapshot at the same point;
- full `tinymix -D 0 --all-values` snapshot immediately after PCM write,
  before helper deallocate and route reset;
- focused mixer snapshot at the same point.

The focused mixer grep is intentionally limited to output/amp/feedback/AppType
terms:

`SPKR|Spkr|WSA|VISENSE|COMP|BOOST|RMS|VI|feedback|RX INT7|SLIMBUS_0_RX|SWR DAC|App Type`

## Changed Files

- `workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`

## Inserted Observation Points

Before PCM:

- `tinymix-all-values-active-before-pcm`
- `tinymix-focus-active-before-pcm`
- result keys: `active_snapshot_before_pcm`, `active_focus_before_pcm`

After PCM, before cleanup/reset:

- `tinymix-all-values-active-after-pcm-before-reset`
- `tinymix-focus-active-after-pcm-before-reset`
- result keys: `active_snapshot_after_pcm_before_reset`,
  `active_focus_after_pcm_before_reset`

These are observation-only.  They do not add any new mixer writes, gain changes,
or smart-amp configuration changes.

## Next Live Unit

Run the existing recoverable V2639 live replay with the V2725 corrected manifest,
now using the V2737 observation points.  Classify the result using V2736's
frontier:

- `output-observed-active-route`: active route and output/WSA indicators change
  during PCM;
- `pcm-write-only-no-output-signal`: PCM writes but no observable output-side
  state changes;
- `calibration-warning-only`: AFE/q6asm warnings remain but active output state
  still changes;
- `regression`: PCM write or rollback fails.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v` — 11 tests passed.
- `git diff --check`
