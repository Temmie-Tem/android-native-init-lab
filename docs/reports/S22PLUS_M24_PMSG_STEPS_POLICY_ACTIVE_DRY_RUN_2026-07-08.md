# S22+ M24 PMSG-Steps Policy Active Dry-Run - 2026-07-08

## Summary

Activated the narrow `AGENTS.md` exception for the exact M24 pmsg-step
DTS-exact QMP/DWC3 boot-only candidate and ran the guarded helper through
offline validation plus default dry-run.

No live flash, reboot, rollback, partition write, sysfs write, or Odin transfer
was performed.

## Active Scope

- Helper:
  `workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py`
- Live ack token:
  `S22PLUS-M24-PMSG-STEPS-LIVE-GATE`
- Rollback ack token:
  `S22PLUS-M24-PMSG-STEPS-ROLLBACK-FROM-DOWNLOAD`
- Candidate AP SHA256:
  `e09538024abe89585486d54856a5c86bef666da456f314084d4d4d8bb6553fe8`
- Candidate boot SHA256:
  `0cccc003687227c4265081fa59d440f4be3e7f40fbb64aca2a3930ca7d5ca3df`
- Candidate `/init` SHA256:
  `4086d18f453980893fa1b8022f93991775b0ee28a6088f1216de82b74cbaf341`
- Module-list SHA256:
  `a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349`

The active exception authorizes only this one M24 boot-only AP through the M24
helper and only the pinned Magisk/stock boot-only rollback APs. It does not
authorize M23 repeats, non-boot partitions, EUD writes, module permutations,
kernel rebuilds, raw writes, fastboot, format data, or any A90 action.

## Dry-Run Evidence

- Dry-run log:
  `workspace/private/runs/s22plus_m24_pmsg_steps_live_gate_20260708T111721Z/s22plus_m24_pmsg_steps_live_gate.txt`
- `agents_exception_missing=[]`
- M24 candidate AP members:
  `['boot.img.lz4']`
- Magisk rollback AP members:
  `['boot.img.lz4']`
- Stock fallback AP members:
  `['boot.img.lz4']`
- Android preflight:
  - `model=SM-S906N`
  - `device=g0q`
  - `bootloader=S906NKSS7FYG8`
  - `incremental=S906NKSS7FYG8`
  - `vbstate=orange`
  - `boot_recovery=0`
  - `boot_completed=1`
  - Magisk root `uid=0(root)`
- Android stability:
  `android_stability_result=ok samples=4`
- Current boot hash:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- Host snapshot dry-run Odin listing:
  no Odin device reported

Final explicit baseline check after dry-run:

- ADB device:
  `SM-S906N/g0q`
- `sys.boot_completed=1`
- verified boot:
  `orange`
- boot reason:
  `reboot,download`
- Magisk root:
  `uid=0(root)`
- boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- vendor_boot SHA256:
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py \
  tests/test_s22plus_m24_pmsg_steps_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m24_pmsg_steps_live_gate

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py
```

Results:

- `py_compile`: pass
- unit tests: `Ran 5 tests ... OK`
- offline check: pass, no device action
- dry-run: pass, no flash/reboot/write

## Next Step

M24 is now policy-active and dry-run clean. The next step requires explicit live
approval before running:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py \
  --live --ack S22PLUS-M24-PMSG-STEPS-LIVE-GATE
```

If the operator observes a loop and manually enters Download mode, immediately
run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py \
  --rollback-from-download --ack S22PLUS-M24-PMSG-STEPS-ROLLBACK-FROM-DOWNLOAD
```

The rollback path is what preserves the intended pmsg/pstore/last_kmsg/reset
surface capture.
