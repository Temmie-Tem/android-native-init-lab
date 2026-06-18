# NATIVE_INIT V2676 — ACDB ADM custom-topology GET reconnaissance

Date: 2026-06-18

## Scope

Host-only reconciliation of the V2675 partial capture.  No device step,
no ACDB replay, no `/dev/msm_audio_cal` ioctl, and no raw private payload
bytes are included in this report.

## Result

- decision: `v2676-adm-custom-topology-cal10-absent-not-capture-gap-host-recon`
- ok: `True`
- v2675_run: `workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431`
- libacdbloader: `workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431/ownget-device-artifacts/libacdbloader.so`
- libacdbloader_sha256: `25ae25afda6f52fc75d9b72e7f9df22094c7e3b243efb7257654ec9445bcd0a1`
- v2461_report: `docs/reports/NATIVE_INIT_V2461_AUDIO_ACDB_COMPAT_IOCTL_LIVE_CAPTURE_2026-06-15.md`

## Evidence

| Check | Result |
| --- | --- |
| V2675 lower GET return codes | `{10: [-12], 14: [0], 24: [0]}` |
| V2675 captured custom SET cal_types | `[14, 24]` |
| V2675 missing custom SET cal_types | `[10]` |
| V2461 Android-good allocated cal_type 10 | `True` |
| V2461 Android-good SET cal_type 10 | `False` |
| V2461 `AUDIO_SET_CALIBRATION` text mentions | `4` |
| ADM Thumb geometry verified | `True` |
| ADM uses block[0]/block[8] as 8-byte input | `True` |
| ADM command is 0x11394 | `True` |

The ADM disassembly check verifies the same input geometry used by V2674:
`block+0` and `block+8` are copied to the `acdb_ioctl` input buffer,
`in_len` is 8, and the command ID is `0x11394`.  That removes the main
V2675 helper-geometry suspicion.

## Interpretation

cal_type 10 is not a V2675 capture-plumbing miss: V2675 used the same ADM block GET geometry as libacdbloader, create/allocate succeeded, but cmd 0x11394 returned -12 while 14/24 returned real sizes.  V2461 Android-good likewise allocated cal_type 10 but did not emit an AUDIO_SET_CALIBRATION record for it.  Treat ADM custom topology as absent for this route until new operator RE identifies a different command/input.

This revises the previous working assumption that cal_type 10 was still a
capture gap.  The stronger reading is that cal_type 10 exists in the
allocation table but has no SET payload for this Android speaker route,
whereas cal_types 24 and 14 do have real non-zero payloads.

## Next Unit

V2677 should stop re-running cal_type 10 capture variants and instead splice the captured 24+14 custom topology records into the native ACDB replay manifest before the bounded PCM probe, with dmesg deciding whether ADM still rejects and which remaining topology/calibration path is actually missing.

If the next native replay still reports `adm_open 0x10004000 ADSP_EFAILED`,
then the blocker should be reclassified away from 'missing ADM custom
topology capture' and toward ADM topology 9/core topology/order or another
DSP-side route dependency.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_adm_custom_topology_v2676.py tests/test_analyze_audio_acdb_adm_custom_topology_v2676.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_adm_custom_topology_v2676 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_adm_custom_topology_v2676.py --write-report`
- `git diff --check`
