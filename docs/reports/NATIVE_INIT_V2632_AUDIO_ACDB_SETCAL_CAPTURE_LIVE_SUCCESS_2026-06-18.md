# NATIVE_INIT V2632 — ACDB SET-calibration capture live success

Date: 2026-06-18

## Scope

V2632 reran the V2631 Android-good own-process ACDB SET-calibration capture
after the V2631 pre-flash failure was traced to an ephemeral host bridge process.
The serial bridge was kept alive as a persistent host session, Android was booted
through the checked `native_init_flash.py` path, the V2630 helper/preload captured
fake-successed `AUDIO_SET_CALIBRATION` records, and the device rolled back to V2321.

This remains measurement-only: the V2630 shim intercepted and fake-successed every
`AUDIO_SET_CALIBRATION` call, no real kernel SET reached `/dev/msm_audio_cal`, no
native ACDB replay ran, and no speaker write occurred. Raw buffers remain private.

## Result

- decision: `v2631-setcal-manifest-captured-rollback-pass`
- ok: `True`
- rolled_back: `True`
- counts_toward_fails_twice: `False`
- operator_valuable: `True`
- partial_success: `False`
- success: `True`
- out_dir: `workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701`
- classification: `v2631-setcal-manifest-captured`
- setcal_record_count: `8`
- cal_types_seen: `[9, 11, 12, 13, 15, 16, 21, 23]`
- payload_record_count: `3`
- header_only_record_count: `5`
- arg_dump_count: `8`
- dmabuf_dumped_count: `3`
- dmabuf_failed_count: `0`
- fake_audio_set_count: `8`
- real_audio_set_pass_through_count: `0`
- afe_topology_headers_captured: `True`
- payload_cal_types_captured: `[11, 15, 16]`

## Ordered SET Records (metadata only)

| seq | cal_type | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 |
| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 1 | 13 | 40 | 0 | -1 | `8453ddee2087e1a233b0a00fa977422751cfcb722a5f1567c63b21fb93a0bed1` | `header-only` | `0000000000000000000000000000000000000000000000000000000000000000` |
| 2 | 9 | 52 | 0 | -1 | `903ecb561c583e7bce52d4fbe2e86724fde1048a88baf127fc37556220d42656` | `header-only` | `0000000000000000000000000000000000000000000000000000000000000000` |
| 3 | 11 | 48 | 18084 | 15 | `3c30ad60db999896dfc1a269303b931f53a3510c1eb733be5c571e699ab7114b` | `dumped` | `00c2399f9b763cf12d8b41d973be78776bc5de2fdf386e778d85e11860f3be0d` |
| 4 | 12 | 48 | 0 | 17 | `3a77bcb6d65c89a8044f42bf36c8d9fd5162a4af9278a7967d02e4301eaae3cd` | `header-only` | `0000000000000000000000000000000000000000000000000000000000000000` |
| 5 | 15 | 36 | 28 | 20 | `0cc83a1198438fcaf60324d327c050b9289467a15bbbd72c6ceb7c270f06c742` | `dumped` | `713205fee55c5504a97496b2395ef4f30dac69d785582ed6a520da9ce4349d71` |
| 6 | 23 | 48 | 0 | -1 | `d3b06f1ceb6cf4ebea871be9fc2bdd793d1183a2a9e251bfbcfb9276f1bb0f15` | `header-only` | `0000000000000000000000000000000000000000000000000000000000000000` |
| 7 | 16 | 44 | 1560 | 21 | `452db210d586ecdb17115e33258987cf04848c7ff02404c7408b098281d5257f` | `dumped` | `b76ceb8320f1028f1d8738438112e17b8d00a8658fb16195d721c7909e7faf72` |
| 8 | 21 | 72 | 28 | -1 | `6b5739f3b795921b4961e018e41d5f3b86033f5ae4c3f9a9a083795e2eeedcde` | `no-mem-handle` | `0000000000000000000000000000000000000000000000000000000000000000` |

Interpretation:

- cal_type `9` and `23` AFE topology header records are present;
- payload-backed cal_types `11`, `15`, and `16` were all dumped from same-process dma-buf fds;
- cal_type `12` and `21` were header/no-mem-handle records in this run;
- all eight SET args were dumped and hashed;
- no real SET pass-through was observed.

## Private Artifacts

- run dir: `workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701`
- result: `workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701/v2631-result.json`
- pulled Android artifacts: `workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701/ownget-device-artifacts`
- SET event log: `workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701/ownget-device-artifacts/setcal-events.jsonl`
- raw SET/dma-buf payloads: `workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701/ownget-device-artifacts`

Raw payload bytes and vendor libraries are private and must not be committed.

## Transport Note

The failed V2631 attempt and the first V2632 attempt both used a host background
`nohup ... &` bridge that did not survive the tool execution context. The successful
run used `serial_tcp_bridge.py` as a persistent exec session before invoking the
checked Android handoff. This is host transport behavior, not an ACDB capture issue.

## Rollback / Health

- Android boot image SHA: `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`;
- rollback target: `boot_linux_v2321_usb_clean_identity_rodata.img`;
- rollback completed through `native_init_flash.py`;
- post-rollback `version` reported `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`;
- post-rollback `selftest verbose` reported `fail=0`.

## Validation

- persistent serial bridge session started with `serial_tcp_bridge.py --port 54321`;
- pre-run `a90ctl.py version` and `a90ctl.py selftest verbose` passed on V2321;
- live command: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_capture_live_handoff_v2631.py --run-live --out-dir workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701`;
- post-run `a90ctl.py version` and `a90ctl.py selftest verbose` passed on V2321;
- `git diff --check`.

## Next Step

Hand the V2632 ordered SET metadata and private raw payloads to operator Gate-2 for
cal_type mapping/verification before any native replay manifest update. Native ACDB
replay remains blocked until the operator accepts these payloads.
