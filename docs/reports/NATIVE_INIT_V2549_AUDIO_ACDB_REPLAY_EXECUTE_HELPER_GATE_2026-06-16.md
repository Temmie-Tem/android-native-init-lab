# V2549 — ACDB replay execute-helper gate

Date: 2026-06-16

## Scope

Host-only follow-up to V2547/V2548. This unit builds the native ACDB replay helper with
`A90_ENABLE_NATIVE_CALIBRATION_EXECUTE` enabled, using the already-reviewed V2474 scaffold, and pins the
future live execution contract around the stable private V2547 `CORE_CUSTOM_TOPOLOGIES` payload.

No device action ran. No flash, Android boot, Magisk action, `/dev/msm_audio_cal` open,
`AUDIO_ALLOCATE_CALIBRATION`, `AUDIO_SET_CALIBRATION`, `AUDIO_DEALLOCATE_CALIBRATION`, PCM write,
`tinymix`, `tinyplay`, or speaker playback ran in this unit.

## Inputs

Stable private payload:

- Path: `workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin`
- Size: `4916`
- SHA256: `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`
- All-zero check: `false`
- Mode: `0600`
- Public metadata: `cal_type=39`, `buffer_number=0`, `payload_len=4916`

The raw payload remains private and is not committed.

## Implementation

Added:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_replay_execute_helper_gate_v2549.py`
- `tests/test_native_audio_acdb_replay_execute_helper_gate_v2549.py`

The runner verifies the stable private payload and compiles:

- Source: `workspace/public/src/native-init/helpers/a90_acdb_replay_scaffold_v2474.c`
- Define: `A90_ENABLE_NATIVE_CALIBRATION_EXECUTE`
- Linkage: static AArch64
- Private output: `workspace/private/builds/audio/v2549-audio-acdb-replay-execute-helper-gate/bin/a90_acdb_replay_execute_v2549`
- Private manifest: `workspace/private/builds/audio/v2549-audio-acdb-replay-execute-helper-gate/manifest.json`

Private built helper:

- SHA256: `acbd11dfef7fcce187f55f966e357952b5a986fddb79b2ff0b4f3ed727c62792`
- `file`: `ELF 64-bit LSB executable, ARM aarch64, statically linked, not stripped`
- Static probe: `strings_has_execute_format=true`, `strings_has_execute_ioctl_marker=true`,
  `strings_has_blocked_default_message=false`

The binary is a private generated artifact and is not committed.

## Future live contract

V2549 does not authorize live replay by itself. The future live unit must use an exact gate and should
run only after the usual rollback/health preflight.

Future exact gate recorded by the manifest:

```text
AUD-5N-native-acdb-topology-replay go: one-shot V2549 execute-enabled ACDB topology replay with pinned V2547 payload, no smart-amp gain changes, bounded PCM probe, explicit deallocate, rollback to V2321
```

Required future live sequence:

1. Confirm V2321 rollback image, v48 fallback, recovery/TWRP, bridge health, and `selftest fail=0`.
2. Flash/use the existing audio materialization path if required and verify candidate health.
3. Materialize ADSP, `/dev/snd`, `/dev/ion`, and `/dev/msm_audio_cal` using already-gated audio paths.
4. Stage the private V2549 helper and V2547 payload to an ephemeral runtime directory.
5. Verify payload SHA-256 on the device before execution.
6. Start the helper with `--execute --payload <staged_payload> --hold-sec 10`.
7. Wait for the helper stderr marker `AUDIO_SET_CALIBRATION ok` before starting the bounded PCM probe.
8. Run the bounded low-amplitude PCM probe only inside the helper hold window.
9. Let the helper issue `AUDIO_DEALLOCATE_CALIBRATION`, then close `/dev/msm_audio_cal`, dma-buf, and `/dev/ion`.
10. Collect redacted metadata only, remove staged files, rollback to V2321, and require `selftest fail=0`.

Abort conditions:

- Payload size or SHA mismatch on host or device.
- Helper static metadata does not show execute-enabled build.
- ADSP, `/dev/snd`, `/dev/ion`, or `/dev/msm_audio_cal` is missing.
- ION allocation or dma-buf mmap fails.
- `AUDIO_ALLOCATE_CALIBRATION` or `AUDIO_SET_CALIBRATION` fails.
- Helper does not emit `AUDIO_SET_CALIBRATION ok` before the PCM probe window.
- `AUDIO_DEALLOCATE_CALIBRATION` cleanup fails or rollback health is not clean.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_replay_execute_helper_gate_v2549.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_acdb_replay_execute_helper_gate_v2549

python3 workspace/public/src/scripts/revalidation/native_audio_acdb_replay_execute_helper_gate_v2549.py \
  --build-helper --require-payload --no-strip

file workspace/private/builds/audio/v2549-audio-acdb-replay-execute-helper-gate/bin/a90_acdb_replay_execute_v2549
sha256sum workspace/private/builds/audio/v2549-audio-acdb-replay-execute-helper-gate/bin/a90_acdb_replay_execute_v2549
```

Results:

- Focused tests: `6` passed.
- Private helper build: passed.
- Payload gate: `ready=true`.
- Manifest: `ok=true`.

## Decision

`v2549-acdb-replay-execute-helper-gate-host-only` is complete. The execute-enabled native replay
helper can now be staged in a future exact-gated live unit, but no live calibration ioctl has been run
by this unit.
