# NATIVE_INIT_V2530_AUDIO_ACDB_OWNPROCESS_SOFTFAIL_LIVE_ZERO_OUTBUF_2026-06-16

## Scope

Live run of the V2529 own-process ARM32 ACDB helper under stock Android, using
the checked Android handoff and rollback path.  The helper soft-continues after
`acdb_loader_init_v3 == -12` and issues the bounded pure-read `acdb_ioctl` GET
matrix only.

No native `/dev/msm_audio_cal` SET ioctl was issued.  No in-HAL injection,
playback, `tinymix`, `tinyplay`, or native calibration replay was run.

## Device Envelope

The run used the V2490/V2529 Android-handoff runner and rolled back to the
resident native checkpoint:

```text
rollback target: v2321-usb-clean-identity-rodata
post-rollback version: A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
post-rollback selftest: fail=0
```

The device is reachable over the native serial bridge after rollback.

## Private Inputs

Private helper artifact, not committed:

```text
workspace/private/builds/audio/v2529-acdb-ownprocess-softfail-get-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2529
sha256: c97b17dc0cc35f0450f04d179ec2e2cbb1b6ec5c11cdfa58bee20c53c927a9c4
```

Private run artifacts, not committed:

```text
workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-051924/
```

## Live Result

The original live runner result labeled the run as
`v2490-acdb-get-success-4916-before-rollback-rollback-pass` because it only
checked for preserved `out_len == 4916` raw files.

That label was too permissive.  Re-analysis of the pulled events shows:

```text
error_count: 1
init event: acdb_loader_init_v3 code=-12 detail=soft_continue_after_allocate_cal_failure
row_count: 40
raw_file_count: 40
target_4916_count: 20
ret_values: [-2]
successful_row_count: 0
successful_nonzero_row_count: 0
target_4916_success_count: 0
zero_outbuf_count: 40
missing_raw_seq: []
```

All `acdb_ioctl` calls returned `ret == -2`.  The preserved buffers are all the
helper's zero-initialized output buffers:

```text
sha256(zero[4]):    df3f619804a92fdb4057192dc43dd748ea778adc52bc498ce80524c014b81119
sha256(zero[4916]): 9af4895ee511379e7a2d0620ea158c535f88c853de6df2eb2cd32f0cb4a2cb8c
```

Corrected classification:

```text
acdb-get-dispatch-ret-failed-zero-outbuf
```

This is useful negative evidence, not a topology capture.  The direct GET matrix
does reach the `acdb_ioctl` dispatch point after the `-12` soft-continue, but
the current zero-input brute-force calls do not produce a valid out-buffer.

## Parser Fix

The live runner parser now separates "raw file preserved" from "valid payload
captured":

- full topology success requires `out_len == 4916`, `ret == 0`, raw present,
  correct raw size, and non-zero raw bytes;
- partial success requires at least one `ret == 0` non-zero out-buffer with raw
  files preserved;
- all failed zero-buffer rows classify as
  `acdb-get-dispatch-ret-failed-zero-outbuf`.

The parser also records return values, successful row counts, zero-buffer
counts, zero hashes by length, and raw size/hash mismatch diagnostics.

## Interpretation

V2530 closes the V2529 discriminator:

```text
Question: after init_v3 returns -12, can direct pure-read acdb_ioctl GET calls
          still return useful topology bytes?
Answer:   no, not with the current zero-input command/in_len/out_len matrix.
```

The likely remaining issue is request structure, not transport:

- `libacdbloader` did load ACDB files and reached ACPH/RTAC setup before the
  allocation-side-effect failure;
- the helper continued and emitted all 40 planned `acdb_ioctl` rows;
- every row failed with `ret == -2`, and every output buffer stayed zero.

Do not rerun V2529 unchanged.  The next useful unit is host-only RE of the
`acdb_ioctl` request input layout or a lower-level DB-only initialization path
that can issue the GET commands with valid request structs while still avoiding
`/dev/msm_audio_cal` SET.

## Validation

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490
# Ran 22 tests: OK

PYTHONPATH=workspace/public/src/scripts/revalidation python3 - <<'PY'
from pathlib import Path
import native_audio_acdb_ownprocess_get_live_handoff_v2490 as v
p = Path('workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-051924/ownget-device-artifacts')
print(v.parse_ownget_artifacts(v.select_pulled_artifact_dir(p))['classification'])
PY
# acdb-get-dispatch-ret-failed-zero-outbuf

python3 workspace/public/src/scripts/revalidation/a90ctl.py version
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest verbose
# v2321-usb-clean-identity-rodata, selftest fail=0
```

## Next Unit

Recommended next unit: host-only ACDB GET request-struct RE.

Concrete target:

- derive the input struct required by the candidate commands
  `0x11394`, `0x12E01`, `0x130DA`, `0x130DC`;
- explain why zero-length/zero-filled inputs return `-2`;
- update the own-process helper only after the request layout is pinned.

Live native calibration replay remains blocked until valid payload bytes,
lengths, SHA-256 values, memory-handle policy, and cleanup are pinned.
