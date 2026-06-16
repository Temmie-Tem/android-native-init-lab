# NATIVE_INIT V2625 — ACDB multi-cal replay helper gate

Date: 2026-06-16

## Scope

Host-only build gate for the future native multi-cal replay helper. No device action, no flash, no ACDB ioctl execution, no PCM probe, and no raw payload publication occurred.

## Decision

- decision: `v2625-acdb-multical-replay-helper-gate-host-only`
- ok: `True`
- native_calibration_ioctls_run: `False`
- source_v2624_manifest: `workspace/private/builds/audio/v2624-audio-acdb-multical-replay-gate/multical-replay-gate-manifest.json`
- gate2_accepted_for_manifest: `False`
- safe_to_run_native_replay: `False`

## Helper

- source: `workspace/public/src/native-init/helpers/a90_acdb_multical_replay_scaffold_v2625.c`
- built: `True`
- private_tool: `workspace/private/builds/audio/v2625-audio-acdb-multical-replay-helper-gate/bin/a90_acdb_multical_replay_execute_v2625`
- private_tool_sha256: `de7ec415d0c47f6883a67ab3e2fb48c02ea990b52f03bb6a88e780033f7dd991`
- private_tool_file: `/home/temmie/dev/A90_5G_rooting/workspace/private/builds/audio/v2625-audio-acdb-multical-replay-helper-gate/bin/a90_acdb_multical_replay_execute_v2625: ELF 64-bit LSB executable, ARM aarch64, version 1 (GNU/Linux), statically linked, BuildID[sha1]=aa6878f358faea6203eee30251efb036d5f1b1f8, for GNU/Linux 3.7.0, not stripped`

The helper accepts repeated `--entry CAL_TYPE:BUFFER:PATH`, allocates one dma-buf per entry, keeps `/dev/msm_audio_cal` and all dma-buf fds open across the future PCM probe window, then deallocates entries in reverse order on every exit path.

## Redacted Replay Entries

| order | kind | cal_type | buffer | size | sha256 | status |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `topology` | `39` | `0` | 4916 | `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89` | `operator-verified` |
| 1 | `per_device_candidate` | `11` | `0` | 18084 | `d1df14cd31bfa6a72b09e9e5075b629a215f10bbdb8e928849b9e2927190895c` | `pending-operator-mapping` |
| 2 | `per_device_candidate` | `15` | `0` | 28 | `999e3e7ae5713992a3e03c247dbd9ceee7069d85053f6192486eb6c236c15d50` | `pending-operator-mapping` |
| 3 | `per_device_candidate` | `16` | `0` | 1560 | `f995c6c2d52a41d2e9be7d40ed9179a5c8ba037e62fccd9a9747b16d890e4fc0` | `pending-operator-mapping` |

## Blockers

- Native replay remains blocked until operator Gate-2 accepts the current V2624 manifest and VOL-negative boundary.
- This unit only removes the local topology-only helper gap; it does not authorize live replay.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_multical_replay_helper_gate_v2625.py tests/test_native_audio_acdb_multical_replay_helper_gate_v2625.py`
- `PYTHONPATH=tests python3 -m unittest tests.test_native_audio_acdb_multical_replay_helper_gate_v2625`
- `python3 workspace/public/src/scripts/revalidation/native_audio_acdb_multical_replay_helper_gate_v2625.py --build-helper --write-report --no-strip`
- `git diff --check`

## Next

After operator Gate-2 acceptance, wire this private helper into a checked live runner that stages the accepted payload set, verifies hashes on-device, waits for all `A90_ACDB_MULTICAL_SET_OK` markers, runs one bounded PCM probe while fds are held, then requires reverse cleanup and V2321 rollback health.
