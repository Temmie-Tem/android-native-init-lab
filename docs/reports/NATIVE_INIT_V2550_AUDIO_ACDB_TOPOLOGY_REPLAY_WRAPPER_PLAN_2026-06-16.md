# V2550 — ACDB topology replay live-wrapper plan

Date: 2026-06-16

## Scope

Host-only wrapper-plan unit after V2549. This unit does **not** run live replay. It composes the
V2549 execute-enabled ACDB helper with the already-proven native speaker path pieces:

- V2547/V2548 pinned `CORE_CUSTOM_TOPOLOGIES` payload
- V2549 private execute-enabled replay helper
- V2407 observed `Audio Stream 0 App Type Cfg` tuple
- V2377 observed speaker route controls
- V2379/V2386 bounded low-amplitude PCM probe path
- V2334 ADSP + `/dev/snd` materialization path
- V2413 `/dev/msm_audio_cal` runtime devnode reachability

No device action ran. No flash, ADSP command, `/dev/msm_audio_cal` open, calibration ioctl,
`tinymix`, PCM write, `tinyplay`, speaker output, or rollback ran in this unit.

## Implementation

Added:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_topology_replay_live_handoff_v2550.py`
- `tests/test_native_audio_acdb_topology_replay_live_handoff_v2550.py`

The script is intentionally source-only for live mode in V2550. `--dry-run` emits the reviewed live
sequence and writes a private manifest. `--run-live` refuses even if the future exact phrase is
provided; actual replay belongs in the next bounded V-iteration after this wrapper plan is reviewed
and committed.

Private generated manifest:

- `workspace/private/builds/audio/v2550-audio-acdb-topology-replay-live-wrapper-plan/manifest.json`

## Dry-run result

Decision:

- `v2550-acdb-topology-replay-live-wrapper-plan-host-only`

Input gates:

- V2549 helper ready: `true`
- V2549 helper SHA256: `acbd11dfef7fcce187f55f966e357952b5a986fddb79b2ff0b4f3ed727c62792`
- V2547 payload ready: `true`
- V2547 payload SHA256: `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`
- Speaker preflight: `true`
- V2407 App-Type command enabled: `true`
- V2377 route apply commands: `13`
- V2377 route reset commands: `12`
- Safety scanner: `ok=true`

Future exact gate recorded:

```text
AUD-5N-native-acdb-topology-replay go: one-shot V2550 topology replay wrapper with pinned V2547 payload, V2407 app-type, V2377 route, bounded PCM probe, explicit deallocate, rollback to V2321
```

## Future live sequence

The next live unit should implement/run this sequence, still inside the recoverable envelope:

1. Verify resident V2321 and `selftest fail=0`.
2. Flash V2334 through the checked helper and verify candidate health.
3. Run ADSP boot-one-shot only if the card is not already up.
4. Run `/dev/snd` materialize-once and require control + PCM nodes.
5. Stage V2549 helper, V2547 payload, `tinymix`, PCM probe, and low-amplitude WAV into a runtime temp dir.
6. Verify payload SHA-256 on device.
7. Capture `tinymix --all-values` baseline.
8. Set the V2407 `Audio Stream 0 App Type Cfg` tuple.
9. Apply only V2377-observed speaker route controls.
10. Start V2549 helper and wait for `AUDIO_SET_CALIBRATION ok`.
11. Run the bounded PCM probe during the helper hold window.
12. Capture helper stdout/stderr and require `AUDIO_DEALLOCATE_CALIBRATION` evidence.
13. Reverse route reset and verify reset snapshot.
14. Remove staged runtime files.
15. Roll back to V2321 and require `selftest fail=0`.

The V2550 remote replay script also requires the on-device payload SHA check before helper execution,
materializes `/dev/msm_audio_cal` from `/proc/misc` only at runtime if needed, and fails closed if
`AUDIO_SET_CALIBRATION ok` does not appear before the PCM probe window.

## Boundaries

Allowed in the future live unit:

- V2407 observed App-Type write
- V2377 observed speaker route controls
- V2549 topology `AUDIO_ALLOCATE/SET/DEALLOCATE` sequence
- Bounded low-amplitude PCM probe
- Runtime temp files only
- Rollback to V2321

Still forbidden:

- Raw non-boot partition writes
- Forbidden partitions
- Magisk/Android framework dependency for native replay
- Blind mixer/gain/boost exploration
- Raw payload or private helper commits
- Continuing if deallocate or rollback health is not proven

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_topology_replay_live_handoff_v2550.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_acdb_topology_replay_live_handoff_v2550

python3 workspace/public/src/scripts/revalidation/native_audio_acdb_topology_replay_live_handoff_v2550.py \
  --dry-run
```

Results:

- Focused tests: `5` passed.
- Dry-run manifest: `ok=true`.
- Safety scanner: `ok=true`, no forbidden tokens, no missing required markers.

## Decision

`v2550-acdb-topology-replay-live-wrapper-plan-host-only` is complete. It does not run live replay.
The next meaningful unit is the actual V2551 live handoff implementation/execution using this reviewed
sequence, with checked rollback to V2321.
