# S22+ M23 DTS-QMP Reset-Summary Policy Active Dry-Run - 2026-07-08

## Summary

Activated the SHA-pinned `AGENTS.md` exception for one bounded attended S22+
M23 DTS-exact QMP/DWC3 reset-summary native-init boot-only live gate, then ran
the helper dry-run.  The dry-run passed and no live flash, reboot, partition
write, sysfs write, or Odin transfer was performed.

The next action, if authorized, is the attended live gate with ack
`S22PLUS-M23-DTS-QMP-RESET-SUMMARY-LIVE-GATE`.

## Policy Change

`AGENTS.md` now authorizes only this exact M23 boot-only candidate:

- Helper:
  `workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py`
- Live ack:
  `S22PLUS-M23-DTS-QMP-RESET-SUMMARY-LIVE-GATE`
- Rollback ack:
  `S22PLUS-M23-DTS-QMP-ROLLBACK-FROM-DOWNLOAD`
- Candidate AP SHA256:
  `558eddb4b78b68c86d65f171072145c63210e9b33b5d0b56f2a3e4a00f0ba2d8`
- Candidate boot SHA256:
  `277bf33c0f7cc62fe2b635b83c22b052d35a4e97dfb2e1cadaf60fdcb961184e`
- Base Magisk boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- M23 `/init` SHA256:
  `745131e23a657905542697cc1c0573a87e484df2e9a06810344d8d4d0be6f357`
- M23 module list SHA256:
  `a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349`

The exception is boot-only.  It does not authorize vendor_boot, DTBO, vbmeta,
recovery, BL, CP, CSC, super, userdata, EFS, RPMB, keymaster, modem, bootloader,
raw host `dd`, fastboot, EUD writes, broad module permutation, display/distro
candidates, kernel rebuild, multidisabler, format data, or any A90 action.

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m23_dts_qmp_reset_summary_live_gate

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py

git diff --check
```

Results:

- unit tests: pass (`Ran 4 tests ... OK`)
- offline check: pass, no device action
- default dry-run: pass
- `git diff --check`: pass

Dry-run evidence:

```text
agents_exception_missing=[]
android_stability_result=ok samples=4
current_boot_hash_rc=0
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

ADB identity during dry-run:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

Private dry-run log:

```text
workspace/private/runs/s22plus_m23_dts_qmp_reset_summary_live_gate_20260708T092147Z/s22plus_m23_dts_qmp_reset_summary_live_gate.txt
```

## Host Storage

The root filesystem had reached 100% usage before dry-run validation.  Retired
private S22+ native-init output caches for older M19/M20/M21/M22 branches were
removed from `workspace/private/outputs/s22plus_native_init/`, leaving the
current M23 output and rollback artifacts in place.  After cleanup, the host had
about 22 GiB free.

## Next Step

Live gate command shape, if the operator authorizes it:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py \
  --live \
  --ack S22PLUS-M23-DTS-QMP-RESET-SUMMARY-LIVE-GATE
```

If the candidate loops and the operator enters Download mode manually, run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py \
  --rollback-from-download \
  --ack S22PLUS-M23-DTS-QMP-ROLLBACK-FROM-DOWNLOAD
```

The rollback path is required for the post-rollback
`/proc/reset_summary`/`reset_klog` capture.
