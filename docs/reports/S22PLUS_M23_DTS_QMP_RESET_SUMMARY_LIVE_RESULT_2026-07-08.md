# S22+ M23 DTS-QMP Reset-Summary Live Result - 2026-07-08

## Verdict

M23 was live-flashed once under the SHA-pinned boot-only exception, then rolled
back successfully to the known Magisk boot baseline. The candidate did not
expose the expected M23 ACM/ADB control path. The operator manually entered
Download mode after the bootloop, the helper detected Odin, restored the pinned
Magisk boot AP, and collected reset-context surfaces.

The reset-summary hypothesis did not yield a native-init hang payload in this
run: `/proc/reset_summary`, `/proc/reset_klog`, `/proc/reset_history`, and
`/proc/reset_tzlog` still opened as empty/missing reset-header surfaces after
rollback.

## Artifacts

- Run directory:
  `workspace/private/runs/s22plus_m23_dts_qmp_reset_summary_live_gate_20260708T104736Z`
- Candidate AP SHA256:
  `558eddb4b78b68c86d65f171072145c63210e9b33b5d0b56f2a3e4a00f0ba2d8`
- Candidate boot SHA256:
  `277bf33c0f7cc62fe2b635b83c22b052d35a4e97dfb2e1cadaf60fdcb961184e`
- Rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`

## Live Evidence

- `m23_candidate_odin_rc=0`
- `m23_odin_returned=1 device=/dev/bus/usb/002/007`
- `magisk_boot_rollback_odin_rc=0`
- `m23_capture_pstore_marker_found=0`
- `m23_reset_reason_result=pass`
- `pstore_files=[]`
- `/proc/reset_reason`: `NPON`
- `/proc/reset_rwc`: `0`
- `/proc/store_lastkmsg`: `0`
- `/proc/reset_summary`: `cat: /proc/reset_summary: No such file or directory`
- `/proc/reset_klog`: `cat: /proc/reset_klog: No such file or directory`
- `/proc/reset_history`: `cat: /proc/reset_history: No such file or directory`
- `/proc/reset_tzlog`: `cat: /proc/reset_tzlog: No such file or directory`

Final Android/Magisk baseline was re-verified after rollback:

- `sys.boot_completed=1`
- `ro.boot.verifiedbootstate=orange`
- Magisk root `uid=0(root)`
- boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- vendor_boot SHA256:
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`

## Timing

Canonical timing is present at `timeline.json` with a single top-level
`events` schema:

- `live_session_start -> candidate_flash_start`: 10.600s
- `candidate_flash_start -> candidate_flash_done`: 1.552s
- `candidate_flash_done -> candidate_boot_ready`: 41.429s
- `candidate_boot_ready -> rollback_flash_start`: 0.000s
- `rollback_flash_start -> rollback_flash_done`: 1.364s
- `rollback_flash_done -> rollback_boot_ready`: 44.613s
- `rollback_boot_ready -> live_session_end`: 11.423s
- total: 110.982s

## Interpretation

M23 did not prove the DTS-exact QMP/DWC3 substrate. It failed before the
expected visible success signal (`S22M23DTSQMP01` ACM or M23 banner), and the
reset-summary surfaces did not capture a useful watchdog reset payload after
the manual Download rollback path.

The next useful unit should not repeat M23 unchanged. It needs either
per-step retained markers (`A90_STEP:` to `/dev/pmsg0` before each risky module
or subsystem action) or a separately gated watchdog-dump variant that changes
the reset-capture preconditions, such as the `qcom_wdt_core` path called out in
`GOAL.md`. A fresh SHA-pinned exception is required for any next boot candidate.
