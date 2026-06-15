# V2548 — ACDB replay real-payload gate

Date: 2026-06-16

## Scope

Host-only gate after V2547 captured the real ACDB `CORE_CUSTOM_TOPOLOGIES` payload.
This unit promotes the private raw payload into a stable private replay-input path and records the
replay metadata/policies needed by the V2474 native replay scaffold.

No device action ran. No Android boot, flash, Magisk action, `/dev/msm_audio_cal` open,
`AUDIO_SET_CALIBRATION`, mixer write, PCM write, or speaker playback ran in this unit.

## Implementation

Added:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_replay_real_payload_gate_v2548.py`
- `tests/test_native_audio_acdb_replay_real_payload_gate_v2548.py`

Private generated/staged outputs:

- Manifest: `workspace/private/builds/audio/v2548-audio-acdb-real-payload-gate/manifest.json`
- Stable payload input: `workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin`

The raw payload and private manifest are not committed.

## Payload gate result

Source payload:

- Path: `workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-080716/ownget-device-artifacts/acdbtap/acdbtap-00000003-cmd-00013296-len-00001334.bin`
- Size: `4916`
- SHA256: `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`
- All-zero check: `false`
- Zero-buffer SHA rejected: `9af4895ee511379e7a2d0620ea158c535f88c853de6df2eb2cd32f0cb4a2cb8c`

Stable private replay input:

- Path: `workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin`
- Mode: `0600`
- Size: `4916`
- SHA256: `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`
- All-zero check: `false`

The V2548 manifest reports `ok=true`, `payload_ready=true`, and `native_calibration_ioctls=none`.

## Replay policy pinned for the next unit

The next native replay unit should consume the stable private payload above with these public metadata
checks:

- `cal_type=39` (`CORE_CUSTOM_TOPOLOGIES_CAL_TYPE`)
- `buffer_number=0`
- `payload_len=4916`
- `payload_sha256=7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`
- Android's observed `mem_handle=37` must **not** be reused as a literal value. The native process must
  allocate a fresh dma-buf/ION fd and use that fd as `mem_handle`.
- Keep both `/dev/msm_audio_cal` and the dma-buf fd open across the bounded PCM probe.
- Cleanup must explicitly issue `AUDIO_DEALLOCATE_CALIBRATION` for the same cal type, buffer, and native
  dma-buf fd, then close `/dev/msm_audio_cal`, unmap/close the dma-buf, and close `/dev/ion`.

V2548 does not authorize live `AUDIO_SET_CALIBRATION` by itself. It only proves that the V2474/V2462
payload input is now pinned and available under a stable private path.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_replay_real_payload_gate_v2548.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_acdb_replay_real_payload_gate_v2548

python3 workspace/public/src/scripts/revalidation/native_audio_acdb_replay_real_payload_gate_v2548.py \
  --stage-payload --require-stable-payload
```

Results:

- Focused tests: `5` passed.
- Payload staging: passed; stable file mode `0600`.
- Private manifest: `ok=true`.

## Decision

`v2548-acdb-real-payload-gate-host-only` is complete. The replay input is now stable and pinned.

Next meaningful unit: build a separate exact-gated native replay runner around the V2474 scaffold that
loads this stable private payload, verifies its SHA before staging, allocates a fresh native dma-buf,
runs the minimal topology `ALLOC`/`SET` sequence, holds fds across the existing bounded PCM probe,
then deallocates and rolls back to V2321. That future live unit must remain fail-closed if the payload
path/SHA, dma-buf allocation, `/dev/msm_audio_cal` reachability, or cleanup policy is missing.
