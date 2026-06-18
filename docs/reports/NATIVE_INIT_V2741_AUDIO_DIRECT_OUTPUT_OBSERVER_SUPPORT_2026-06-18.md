# NATIVE_INIT V2741 — Direct-control output observer support

Date: 2026-06-18

## Scope

Host-only support update after V2740 showed that the dynamic output observer was too heavy: one
`tinymix --all-values` scan consumed the bounded PCM window, so the live run emitted only one completed
sample. V2741 changes the observer script generation only; no device action was run in this unit.

## Decision

`v2741-direct-output-observer-host-ready`

The replay runner now generates a narrow, direct-control output observer instead of sampling the full mixer
state repeatedly.

## Changes

- Renamed the runtime observer script to `a90_pcm_output_observer_v2741.sh`.
- Added `v2741_output_observer` dry-run metadata while keeping the legacy `v2739_output_observer` key mapped
  to the same plan for compatibility.
- Replaced full `tinymix -D 0 --all-values | grep ...` sampling with a 20-control allowlist of direct reads:
  - route/front-end controls such as `SLIMBUS_0_RX Audio Mixer MultiMedia1`, `RX INT7_1 MIX1 INP0`, and
    `Audio Stream 0 App Type Cfg`;
  - output-side controls such as `Get RMS`, `Backend Device Channel Map`, `SpkrLeft COMP Switch`,
    `SpkrLeft BOOST Switch`, `SpkrLeft VISENSE Switch`, and `SpkrLeft SWR DAC_Port Switch`;
  - VI/WSA-related controls such as `AIF4_VI Mixer SPKR_VI_1`, `AIF4_VI Mixer SPKR_VI_2`,
    `WSA_CDC_DMA_RX_0 Audio Mixer MultiMedia1`, and `WSA_CDC_DMA_RX_1 Audio Mixer MultiMedia1`.
- Each direct control read emits `A90_OUTPUT_OBSERVER_CTL_BEGIN`, `A90_OUTPUT_OBSERVER_CTL`, and
  `A90_OUTPUT_OBSERVER_CTL_END` with the sample index, label, read rc, and raw tinymix output.
- The observer still changes no WSA gain/boost/protection control and keeps the same bounded PCM probe contract.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --dry-run --v2636-manifest workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json --manifest-path workspace/private/builds/audio/v2741-direct-output-observer-support/dry-run-manifest.json`
- Dry-run confirmed:
  - observer name: `v2741-direct-output-observer`
  - sampling mode: `direct-control-allowlist`
  - direct controls: `20`
  - generated script contains `A90_OUTPUT_OBSERVER_CTL_BEGIN`
  - generated script does **not** contain `--all-values`
- `git diff --check`

## Next

Run one V2741/V2742 live discriminator with the same ACDB SET replay + low-amplitude PCM path. Success for the
observer layer is at least two completed `A90_OUTPUT_OBSERVER_SAMPLE_BEGIN` samples during the PCM window, with
per-control `CTL` records for the allowlist. If samples still collapse to one, reduce the control list further
or move to a purpose-built tinyalsa control reader.
