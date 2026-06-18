# NATIVE_INIT V2739 — Audio dynamic output observer support

Date: 2026-06-18

## Scope

V2739 implements the next unit selected after V2738. V2738 proved the native
ACDB SET replay + route + bounded PCM path is active and stable, but its
pre/post `tinymix` snapshots showed no output-side counter/state change. That
left a measurement gap: a transient output indicator could exist only while the
PCM writer is running.

This unit is support-only and host/static validated. It does not flash or run the
device. It adds a read-only dynamic observer around the existing bounded PCM
probe so the next live run can sample output-side mixer controls and relevant
thermal zones during playback, not only before and after.

## Decision

`v2739-dynamic-output-observer-support-ready`

The runner now installs and uses a generated remote wrapper:

`/cache/a90-runtime/bin/v2379-speaker-pilot/a90_pcm_output_observer_v2739.sh`

By default, the wrapper replaces the direct PCM-probe command in the V2639/V2730
runner. It still invokes the same `a90_pcm_write_probe_v2386` binary and the same
low-amplitude PCM file, but it concurrently samples read-only observability data
until the PCM probe exits.

## Why This Is The Right Next Unit

V2738 result:

- route controls remained asserted before and after PCM;
- PCM probe opened card 0/device 0 and wrote all 192000 bytes;
- focused route values did not change across the pre/post snapshots;
- `Get RMS` stayed `-1` and `Backend Device Channel Map` stayed all `-1`.

A pre/post snapshot cannot prove that no output-side signal exists during the
active PCM interval. V2739 therefore narrows the next live test to a dynamic
sampler instead of re-running the same static snapshots.

## Source Basis

The techpack source confirms two safe read-only observability classes:

1. WSA temperature reads are exposed through thermal-zone `.get_temp` via
   `wsa881x_get_temp()`. The implementation reads codec temperature registers and
   returns a temperature; it does not change speaker gain/boost/protection state.
2. Speaker-protection DSP logging exists through
   `afe_get_sp_rx_tmax_xmax_logging_data()`, which issues a GET-param for
   `AFE_PARAM_ID_SP_RX_TMAX_XMAX_LOGGING` and logs `max_excursion`,
   `count_exceeded_excursion`, `max_temperature`, and
   `count_exceeded_temperature` on success. Directly invoking this kernel helper
   from userspace is not available, but the dmesg lines and related mixer/thermal
   observables are useful read-only signals.

V2739 does not introduce any new SET ioctl, mixer write, smart-amp gain change,
or DSP mutation. It only reads `tinymix --all-values` with the existing focus
filter and reads matching `/sys/class/thermal/thermal_zone*/{type,temp}` files.

## Implementation

Modified runner:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py`

New dry-run/state keys:

- `v2739_output_observer.enabled`
- `v2739_output_observer.remote_script`
- `v2739_output_observer.sample_count`
- `v2739_output_observer.sample_sleep_sec`
- `remote_scripts.pcm_output_observer`
- `remote_script_paths.pcm_output_observer`

Runtime behavior when enabled:

1. Install `a90_pcm_output_observer_v2739.sh` alongside the existing ACDB helper
   scripts.
2. Start a background sampler before PCM.
3. Each sample emits:
   - `A90_OUTPUT_OBSERVER_SAMPLE_BEGIN/END` markers;
   - focused `tinymix -D 0 --all-values` lines matching `SPKR|Spkr|WSA|VISENSE|COMP|BOOST|RMS|VI|feedback|RX INT7|SLIMBUS_0_RX|SWR DAC|App Type`;
   - thermal-zone values whose type matches `wsa|spkr|speaker|audio|wcd|tavil|pa`.
4. Run the existing `a90_pcm_write_probe_v2386` command.
5. Stop the sampler and dump its captured samples before returning the PCM probe
   exit code.

Default sampler parameters:

- `--output-observer`: enabled.
- `--output-observer-samples`: `12`.
- `--output-observer-sleep`: `0.10` seconds.
- `--pcm-device`: `0`.

## Safety Boundary

V2739 is read-only with respect to output observation. It preserves the existing
operational invariants:

- exact captured ACDB SET replay order remains unchanged;
- route writes remain the already observed route controls;
- PCM probe remains bounded and low-amplitude;
- no WSA gain/boost/protection controls are changed beyond the existing route;
- cleanup/reset/rollback behavior is unchanged;
- no boot image or private payload is committed.

## Validation

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec before selecting the unit.
- Reviewed V2736/V2738 reports to avoid re-running a saturated route snapshot.
- Reviewed techpack source:
  - `techpack/audio/asoc/codecs/wsa881x-temp-sensor.c`
  - `techpack/audio/dsp/q6afe.c`
  - `techpack/audio/include/dsp/q6afe-v2.h`
  - `techpack/audio/include/dsp/apr_audio-v2.h`
- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- Real V2725 manifest dry-run confirmed:
  - `remote_scripts` includes `pcm_output_observer`;
  - wrapper contains `A90_OUTPUT_OBSERVER_PCM_BEGIN`;
  - wrapper contains `A90_OUTPUT_OBSERVER_THERMAL`;
  - generated wrapper length is 52 lines.
- `git diff --check` passed before commit.

## Next Live Unit

Run the V2639/V2730 live runner once with the V2739 observer enabled. Acceptance
is not audible sound by itself; it is one of:

- `output-observed-dynamic-counter`: PCM writes and a dynamic output-side
  mixer/thermal signal changes during the sampler window;
- `pcm-write-no-dynamic-output-signal`: PCM writes but dynamic samples stay flat;
- `regression`: PCM write, cleanup, rollback, or selftest fails.
