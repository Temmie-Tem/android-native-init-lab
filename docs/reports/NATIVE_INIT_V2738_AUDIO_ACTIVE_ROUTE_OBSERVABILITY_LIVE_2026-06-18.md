# NATIVE_INIT V2738 — Audio active-route observability live run

Date: 2026-06-18

## Scope

V2738 reran the V2737-instrumented ACDB SET-cal replay path live, adding
active-route mixer snapshots immediately before the bounded PCM probe and again
after the PCM probe but before route reset. The goal was to determine whether
the successful PCM write window also exposes route-state or output-side state
changes that were previously missed by post-hoc snapshots.

The run stayed inside the recoverable envelope: checked V2334 candidate boot,
ACDB SET replay with the V2725 corrected manifest, bounded low-amplitude PCM
probe, reverse deallocate/reset cleanup, and rollback to V2321.

## Result

- decision: `v2738-active-route-observability-live-pass-before-rollback`
- private run dir: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-231606`
- replay result: all exact ACDB SET entries reached final index 10
- App Type Config gate: `69941:48000:16` write succeeded before route/PCM
- PCM probe: opened card 0/device 0 and wrote 192000 bytes in 12 chunks
- active snapshots: full + focused `tinymix --all-values` captured before PCM and after PCM before reset
- rollback: returned to `v2321-usb-clean-identity-rodata`, selftest `fail=0`

## Evidence

### Replay And PCM

- `48_v2733-atomic-app-type-config.txt`: `A90_APP_TYPE_CFG_WRITE_OK num_entries=1`, entry `69941:48000:16`.
- `63_acdb-setcal-replay-start-wait-all-set.txt`: `A90_SETCAL_REPLAY_ALL_SET_OK pid=860 final_index=10`.
- `68_tinyplay-low-amplitude-speaker-pilot.txt`: `A90_PCM_PROBE_PCM_OPEN_OK`, then 12 successful writes, `A90_PCM_PROBE_DONE chunks=12 bytes=192000 drain_us=85333`.

### Active Route Snapshot

The new V2737 capture points both succeeded:

- `66_tinymix-all-values-active-before-pcm.txt`: 2050 lines.
- `67_tinymix-focus-active-before-pcm.txt`: 349 lines.
- `71_tinymix-all-values-active-after-pcm-before-reset.txt`: 2050 lines.
- `72_tinymix-focus-active-after-pcm-before-reset.txt`: 349 lines.

Focused controls were stable across the PCM window:

- `SLIMBUS_0_RX Audio Mixer MultiMedia1`: `On Off` before and after PCM.
- `RX INT7_1 MIX1 INP0`: `RX0` before and after PCM.
- `COMP7 Switch`: `On` before and after PCM.
- `AIF4_VI Mixer SPKR_VI_1`: `On` before and after PCM.
- `AIF4_VI Mixer SPKR_VI_2`: `On` before and after PCM.
- `SpkrLeft COMP Switch`: `On` before and after PCM.
- `SpkrLeft BOOST Switch`: `On` before and after PCM.
- `SpkrLeft VISENSE Switch`: `On` before and after PCM.
- `SpkrLeft SWR DAC_Port Switch`: `On` before and after PCM.
- `Audio Stream 0 App Type Cfg`: `69941 15 48000 2 ...` before and after PCM.

The focused diff contains only command sequence/PID noise and ordering/noise from
`Failed to mixer_ctl_get_array`; no route-control value changed during the PCM
window.

### Kernel Events

Before PCM, the focused dmesg capture contained no new matched route/ASM/AFE
lines. After PCM, it captured the active playback edge:

- `__afe_port_start: port id: 0x4000`
- `q6asm_callback: cmd = 0x10da1 returned error = 0x12`
- `q6asm_set_pp_params: DSP returned error[ADSP_ENEEDMORE]`
- `q6asm_send_cal: audio audstrm cal send failed`
- `adm_open:port 0x4000 path:1 rate:48000 mode:1 perf_mode:0,topo_id 0x10004000`
- `adm_open:bit_width:16 app_type:0x11135 acdb_id:15`

## Interpretation

V2738 confirms that the V2735 PCM path is not a stale/post-hoc artifact: the
speaker route controls remain asserted during the PCM write window and `adm_open`
uses the expected `bit_width:16 app_type:0x11135 acdb_id:15` tuple.

The added snapshots do not show a positive output-side counter or state change.
`Get RMS` remains `-1`, `Backend Device Channel Map` remains all `-1`, and the
focused mixer route values are unchanged before and after PCM. Therefore V2738
classifies the current frontier as:

`pcm-write-active-route-no-output-counter`

This preserves the earlier conclusion that `q6asm_send_cal` and AFE cal errors
are not fatal to `pcm_prepare`/PCM writes, but it does not independently prove
audible speaker output. The next useful unit should add a real output-side
observable, not rerun the same route snapshot: examples include a safe WSA/VI/RMS
read path, a kernel-side speaker/WSA event trace, or operator-observed audible
validation if acceptable.

## Validation

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec section before execution.
- Confirmed rollback images before live run.
- Confirmed pre-run v2321 bridge health and selftest `fail=0`.
- Ran V2738 live command with `--run-live --write-report`.
- Confirmed post-run current device: `version` = `0.9.285 build=v2321-usb-clean-identity-rodata`.
- Confirmed post-run current device: `selftest: pass=11 warn=1 fail=0`.
- `git diff --check` passed before commit.
