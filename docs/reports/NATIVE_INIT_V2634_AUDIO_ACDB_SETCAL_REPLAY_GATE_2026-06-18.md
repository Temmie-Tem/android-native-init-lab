# NATIVE_INIT V2634 — ACDB SET-cal replay gate

Date: 2026-06-18

## Scope

Host-only staging gate for native ACDB replay after the V2633 SET-layer
handoff. This unit validates the private SET arg/dma-buf artifacts and
the operator-verified topology payload, then writes a private manifest for
future replay-helper work.

It does **not** run native replay, does not issue `/dev/msm_audio_cal` ioctls,
does not flash or boot the device, and does not copy raw ACDB bytes into tracked paths.

## Result

- decision: `v2634-setcal-replay-gate-ready`
- ok: `True`
- inputs_ok: `True`
- source_v2633_manifest: `workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701/v2633-acdb-setcal-gate2-handoff-manifest.json`
- private_manifest: `workspace/private/builds/audio/v2634-audio-acdb-setcal-replay-gate/setcal-replay-gate-manifest.json`
- topology_ok: `True`
- record_count: `8`
- validated_record_count: `8`
- captured_set_order: `[13, 9, 11, 12, 15, 23, 16, 21]`
- native_replay_ready: `False`
- safe_to_run_native_replay: `False`

## Redacted Replay Inputs

| seq | cal_type | role | data_size | cal_size | dmabuf | arg_sha256 | dmabuf_sha256 | status |
| ---: | ---: | --- | ---: | ---: | --- | --- | --- | --- |
| 1 | 13 | `APP_META_HEADER` | 40 | 0 | `header/no-payload` | `8453ddee2087e1a233b0a00fa977422751cfcb722a5f1567c63b21fb93a0bed1` | `None` | `True` |
| 2 | 9 | `AFE_TOPOLOGY_HEADER` | 52 | 0 | `header/no-payload` | `903ecb561c583e7bce52d4fbe2e86724fde1048a88baf127fc37556220d42656` | `None` | `True` |
| 3 | 11 | `AUDPROC_COMMON_PAYLOAD` | 48 | 18084 | `payload` | `3c30ad60db999896dfc1a269303b931f53a3510c1eb733be5c571e699ab7114b` | `00c2399f9b763cf12d8b41d973be78776bc5de2fdf386e778d85e11860f3be0d` | `True` |
| 4 | 12 | `VOL_HEADER_NO_PAYLOAD` | 48 | 0 | `header/no-payload` | `3a77bcb6d65c89a8044f42bf36c8d9fd5162a4af9278a7967d02e4301eaae3cd` | `None` | `True` |
| 5 | 15 | `ASM_STREAM_PAYLOAD` | 36 | 28 | `payload` | `0cc83a1198438fcaf60324d327c050b9289467a15bbbd72c6ceb7c270f06c742` | `713205fee55c5504a97496b2395ef4f30dac69d785582ed6a520da9ce4349d71` | `True` |
| 6 | 23 | `AFE_TOPOLOGY_ID_HEADER` | 48 | 0 | `header/no-payload` | `d3b06f1ceb6cf4ebea871be9fc2bdd793d1183a2a9e251bfbcfb9276f1bb0f15` | `None` | `True` |
| 7 | 16 | `AFE_COMMON_PAYLOAD` | 44 | 1560 | `payload` | `452db210d586ecdb17115e33258987cf04848c7ff02404c7408b098281d5257f` | `b76ceb8320f1028f1d8738438112e17b8d00a8658fb16195d721c7909e7faf72` | `True` |
| 8 | 21 | `SPEAKER_VI_HEADER` | 72 | 28 | `header/no-payload` | `6b5739f3b795921b4961e018e41d5f3b86033f5ae4c3f9a9a083795e2eeedcde` | `None` | `True` |

## Replay Gate

- V2634 packages replay inputs only; it is **not** a live replay approval.
- Native replay remains blocked until operator Gate-2 accepts the V2633 SET-layer package.
- The current V2625 native helper reconstructs payload-only packets and does not support
  exact SET-arg/header-only replay required by V2633.
- Future helper work must consume the private manifest, preserve exact header-only SET args,
  and patch fresh dmabuf handles only for payload-backed records.

### Blockers

- operator Gate-2 has not accepted the V2633 SET-layer package
- current native replay helper does not support exact SET-arg/header-only replay
- V2634 is a host-only staging gate, not a live native replay approval

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_gate_v2634.py tests/test_native_audio_acdb_setcal_replay_gate_v2634.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_gate_v2634 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_gate_v2634.py --write-report`
- `git diff --check`
