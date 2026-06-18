# NATIVE_INIT V2742 — Direct-control output observer live result

Date: 2026-06-18

## Scope

Live-run the V2741 direct-control output observer around the existing native ACDB SET replay and bounded
low-amplitude PCM probe. The unit remains inside the recoverable envelope and rolls back to `v2321`.

## Decision

`v2742-direct-output-observer-single-sample-pcm-ok`

The V2741 observer fixed the control-read semantics: all 20 allowlisted direct `tinymix` reads returned `rc=0`.
However, the observer still produced only one completed sample during the 1-second PCM probe. The bottleneck is no
longer full `--all-values`; it is process-per-control `tinymix` overhead across 20 controls. V2742 still does not
produce a dynamic time-series.

## Evidence

- Run directory: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-234924`
- Post-run device state over bridge:
  - `version: 0.9.285 build=v2321-usb-clean-identity-rodata`
  - `selftest: pass=11 warn=1 fail=0`
- Rollback:
  - `90_rollback-v2321.txt`: `cmdv1 verify passed: selftest rc=0 status=ok fail=0`
  - `91_rollback-version-attempt-1.txt`: `version: 0.9.285 build=v2321-usb-clean-identity-rodata`
  - `92_rollback-selftest-content-attempt-1-attempt-1.txt`: `selftest: pass=11 warn=1 fail=0`
- ACDB/App-Type/PCM path:
  - `49_v2733-atomic-app-type-config.txt`: global `App Type Config` write succeeded.
  - `64_acdb-setcal-replay-start-wait-all-set.txt`: `A90_SETCAL_REPLAY_ALL_SET_OK pid=... final_index=10`.
  - `69_pcm-output-observer-during-playback.txt`: `A90_PCM_PROBE_DONE chunks=12 bytes=192000 drain_us=85333`.
  - `69_pcm-output-observer-during-playback.txt`: `A90_OUTPUT_OBSERVER_PCM_END rc=0`.
- Observer result:
  - begin marker: `A90_OUTPUT_OBSERVER_BEGIN mode=direct-controls samples=12 sleep=0.10 controls=20`
  - completed samples: `1`
  - completed control reads: `20`
  - control read rc distribution: `{'0': 20}`
  - failed control reads: `0`
- Representative direct controls captured successfully:
  - `Get RMS: -1`
  - `Backend Device Channel Map: -1 ...`
  - `SLIMBUS_0_RX Audio Mixer MultiMedia1: On Off`
  - `RX INT7_1 MIX1 INP0: ... >RX0 ...`
  - `SpkrLeft COMP Switch: On`
  - `SpkrLeft BOOST Switch: On`
  - `SpkrLeft VISENSE Switch: On`
  - `SpkrLeft SWR DAC_Port Switch: On`
  - `AIF4_VI Mixer SPKR_VI_1: On`
  - `WSA_CDC_DMA_RX_0 Audio Mixer MultiMedia1: Off Off`
- Dmesg frontier is unchanged from the app-type-fixed path:
  - `__afe_port_start: port id: 0x4000`
  - `q6asm_callback: cmd = 0x10da1 returned error = 0x12`
  - `q6asm_set_pp_params: DSP returned error[ADSP_ENEEDMORE]`
  - `q6asm_send_cal: audio audstrm cal send failed`
  - `adm_open:port 0x4000 path:1 rate:48000 mode:1 perf_mode:0,topo_id 0x10004000`
  - `adm_open:bit_width:16 app_type:0x11135 acdb_id:15`

## Interpretation

V2742 validates that the selected direct control names are readable under the active route, but `tinymix` process
spawn overhead is still too high for a 1-second dynamic observer. Repeating the same shell/tinymix approach is low
value.

The next meaningful unit should choose one of two bounded fixes:

1. **Preferred:** build a small native/tinyalsa control reader that opens the mixer once and polls the allowlist in
   one process, emitting the same `A90_OUTPUT_OBSERVER_CTL` schema.
2. **Fallback discriminator:** extend only the PCM probe duration while keeping low amplitude, to determine whether
   the existing shell observer can ever emit multiple samples. This is less clean because it changes the playback
   window rather than fixing the observer overhead.

## Validation

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec before the unit.
- Verified rollback image SHA values and current bridge `selftest fail=0` before live.
- Ran the V2742 live handoff with `--run-live`, V2725 corrected manifest, and V2741 direct observer support.
- Parsed private live artifacts from `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-234924`.
- Verified post-run bridge state after rollback: `version` = `0.9.285`, `selftest fail=0`.
- `git diff --check` before commit.
