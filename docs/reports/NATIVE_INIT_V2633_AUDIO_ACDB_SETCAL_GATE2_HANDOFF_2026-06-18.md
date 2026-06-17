# NATIVE_INIT V2633 — ACDB SET-cal Gate-2 handoff package

Date: 2026-06-18

## Scope

Host-only handoff of the V2632 SET-layer ACDB capture. This unit verifies
private raw SET-argument and dma-buf artifacts, writes a private manifest for
operator Gate-2, and publishes only metadata, sizes, and SHA-256 hashes.

It does **not** build or modify a native replay manifest, does not issue audio
ioctls, does not boot or flash the device, and does not copy raw bytes into
tracked paths.

## Result

- decision: `v2633-setcal-gate2-handoff-ready`
- ok: `True`
- source_run_dir: `workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701`
- source_decision: `v2631-setcal-manifest-captured-rollback-pass`
- source_rolled_back: `True`
- private_manifest: `workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701/v2633-acdb-setcal-gate2-handoff-manifest.json`
- record_count: `8`
- verified_record_count: `8`
- ordered_cal_types: `[13, 9, 11, 12, 15, 23, 16, 21]`
- order_matches_expected: `True`
- payload_cal_types: `[11, 15, 16]`
- header_cal_types: `[9, 12, 13, 21, 23]`
- previous_payload_tail_match_count: `3`
- real_audio_set_pass_through_count: `0`

## Redacted SET Records

| seq | cal_type | role | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 | prev_tail_match |
| ---: | ---: | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| 1 | 13 | `APP_META_HEADER` | 40 | 0 | -1 | `8453ddee2087e1a233b0a00fa977422751cfcb722a5f1567c63b21fb93a0bed1` | `header-only` | `None` | `None` |
| 2 | 9 | `AFE_TOPOLOGY_HEADER` | 52 | 0 | -1 | `903ecb561c583e7bce52d4fbe2e86724fde1048a88baf127fc37556220d42656` | `header-only` | `None` | `None` |
| 3 | 11 | `AUDPROC_COMMON_PAYLOAD` | 48 | 18084 | 15 | `3c30ad60db999896dfc1a269303b931f53a3510c1eb733be5c571e699ab7114b` | `dumped` | `00c2399f9b763cf12d8b41d973be78776bc5de2fdf386e778d85e11860f3be0d` | `True` |
| 4 | 12 | `VOL_HEADER_NO_PAYLOAD` | 48 | 0 | 17 | `3a77bcb6d65c89a8044f42bf36c8d9fd5162a4af9278a7967d02e4301eaae3cd` | `header-only` | `None` | `None` |
| 5 | 15 | `ASM_STREAM_PAYLOAD` | 36 | 28 | 20 | `0cc83a1198438fcaf60324d327c050b9289467a15bbbd72c6ceb7c270f06c742` | `dumped` | `713205fee55c5504a97496b2395ef4f30dac69d785582ed6a520da9ce4349d71` | `True` |
| 6 | 23 | `AFE_TOPOLOGY_ID_HEADER` | 48 | 0 | -1 | `d3b06f1ceb6cf4ebea871be9fc2bdd793d1183a2a9e251bfbcfb9276f1bb0f15` | `header-only` | `None` | `None` |
| 7 | 16 | `AFE_COMMON_PAYLOAD` | 44 | 1560 | 21 | `452db210d586ecdb17115e33258987cf04848c7ff02404c7408b098281d5257f` | `dumped` | `b76ceb8320f1028f1d8738438112e17b8d00a8658fb16195d721c7909e7faf72` | `True` |
| 8 | 21 | `SPEAKER_VI_HEADER` | 72 | 28 | -1 | `6b5739f3b795921b4961e018e41d5f3b86033f5ae4c3f9a9a083795e2eeedcde` | `no-mem-handle` | `None` | `None` |

## Gate-2 Boundary

- This is a handoff package, not a native replay manifest.
- Private manifest rows include `raw_path_private`; public rows intentionally do not.
- cal_type `11`, `15`, and `16` dma-buf payloads match previous Gate-2 payloads
  from byte offset 4 onward; the first word differs as expected between capture methods.
- Header-only SET records (`9`, `12`, `13`, `21`, `23`) are preserved via full SET arg dumps.
- Native ACDB replay remains blocked until operator Gate-2 accepts this package.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_gate2_handoff_v2633.py tests/test_native_audio_acdb_setcal_gate2_handoff_v2633.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_gate2_handoff_v2633 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_gate2_handoff_v2633.py --write-report`
- `git diff --check`
