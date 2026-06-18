# NATIVE_INIT V2740 — Dynamic output observer live result

Date: 2026-06-18

## Scope

Live-check the V2739 dynamic output observer on top of the already working native ACDB SET replay path.
The unit stays inside the recoverable envelope: one-shot exact SET replay, bounded low-amplitude PCM write,
route/control observation only, reverse deallocation/cleanup, and checked rollback to `v2321`.

## Decision

`v2740-output-observer-partial-single-slow-snapshot-pcm-ok`

V2740 did not produce a useful dynamic time-series. It did prove the observer wrapper is safe to run around
the SET replay + PCM probe, but the current implementation uses a full `tinymix -D 0 --all-values` scan per
sample; that scan is slow enough that only one completed sample was emitted before the stop marker. Therefore
V2740 does **not** answer whether speaker/WSA/RMS counters change during the PCM write.

## Evidence

- Run directory: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-233443`
- Current post-run device state confirmed over the bridge:
  - `version: 0.9.285 build=v2321-usb-clean-identity-rodata`
  - `selftest: pass=11 warn=1 fail=0`
- Rollback images were checked before the live run, and the run rolled back to `v2321` with `selftest fail=0`.
- Global `App Type Config` writer succeeded:
  - file: `49_v2733-atomic-app-type-config.txt`
  - marker: `A90_APP_TYPE_CFG_WRITE_OK num_entries=1`
  - payload: `69941:48000:16`
- ACDB SET replay completed every SET in the corrected sequence:
  - file: `64_acdb-setcal-replay-start-wait-all-set.txt`
  - marker: `A90_SETCAL_REPLAY_ALL_SET_OK pid=862 final_index=10`
- PCM write probe succeeded again:
  - file: `69_pcm-output-observer-during-playback.txt`
  - marker: `A90_PCM_PROBE_DONE chunks=12 bytes=192000 drain_us=85333`
  - marker: `A90_OUTPUT_OBSERVER_PCM_END rc=0`
- Observer request vs actual completion:
  - requested: `A90_OUTPUT_OBSERVER_BEGIN samples=12 sleep=0.10`
  - completed: one `A90_OUTPUT_OBSERVER_SAMPLE_BEGIN index=0`
  - reason: one full `tinymix --all-values` pass dominates the playback window; after PCM finishes, the stop marker prevents more samples.
- The single completed snapshot captured the expected active route controls, but no time-series:
  - `SLIMBUS_0_RX Audio Mixer MultiMedia1     On Off`
  - `RX INT7_1 MIX1 INP0 ... >RX0 ...`
  - `COMP7 Switch                             On`
  - `SpkrLeft COMP Switch                     On`
  - `SpkrLeft BOOST Switch                    On`
  - `SpkrLeft VISENSE Switch                  On`
  - `SpkrLeft SWR DAC_Port Switch             On`
  - `Get RMS                                  -1`
  - `Backend Device Channel Map               -1 ...`
- Focused before/after snapshots are materially stable. The only diff observed in the filtered focus set is a `Failed to mixer_ctl_get_array` text coalescing artifact near `SEC MI2S RX Format`, not a route-state change.
- Dmesg frontier remains the same post-app-type frontier:
  - `__afe_port_start: port id: 0x4000`
  - `q6asm_callback: cmd = 0x10da1 returned error = 0x12`
  - `q6asm_set_pp_params: DSP returned error[ADSP_ENEEDMORE]`
  - `q6asm_send_cal: audio audstrm cal send failed`
  - `adm_open:port 0x4000 path:1 rate:48000 mode:1 perf_mode:0,topo_id 0x10004000`
  - `adm_open:bit_width:16 app_type:0x11135 acdb_id:15`

## Interpretation

V2740 is a safe partial success for the harness, not a new audio-path discriminator. The PCM path still writes
all low-amplitude data with `rc=0`, and rollback is clean, but the observer is too heavyweight for sub-second
playback correlation when it samples by running a full `tinymix --all-values` each time.

The next meaningful unit should narrow the observer instead of repeating V2740:

1. Replace full `tinymix --all-values` sampling with a small allowlist of direct control reads, or snapshot the
   full control list once and poll only stable numids for speaker/WSA/RMS/route controls.
2. Start the sampler before PCM, emit each sample immediately, and do not wait for a long all-values scan inside
   one sample.
3. Keep the same ACDB SET replay, low-amplitude PCM probe, cleanup, and rollback contract.

## Validation

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec before continuing the unit.
- Verified rollback bridge state after live run: `version` = `0.9.285`, `selftest fail=0`.
- Parsed private live artifacts from `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-233443`.
- `git diff --check` before commit.
