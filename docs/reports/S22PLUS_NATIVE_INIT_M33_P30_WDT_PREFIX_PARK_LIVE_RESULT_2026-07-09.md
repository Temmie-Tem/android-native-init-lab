# S22+ M33 P30 WDT Prefix Park Live Result

Date: 2026-07-09 KST / 2026-07-08 UTC

## Verdict

PASS / CONSUMED / ROLLBACK CLEAN.

M33 P30 survived the full 90 second observation window. This proves the full
45-module closure including `usb_f_ss_acm.ko` is not the M32 failure boundary
when runtime configfs/ACM binding is absent.

The next unit is M34 S1 host build: configfs gadget/function/config creation
only, no `usb_role=device`, no `UDC` bind.

## Command

Live gate ran under commit `e709ea75`:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py \
  --live \
  --ack S22PLUS-M33-P30-WDT-PREFIX-PARK-LIVE-GATE
```

Run directory:

`workspace/private/runs/s22plus_m33_p30_wdt_prefix_park_live_gate_20260708T183832Z`

## Candidate

- AP.tar.md5 SHA256:
  `e7cadd856da852e577adf32e088c0fee668904f265cdad1e9309072ccb2b18fd`
- boot.img SHA256:
  `0a972bcb4af2b75d5177ae9767e34a4caa8b8c94237afa708bb4a577b2ba7bfe`
- `/init` SHA256:
  `48afc2af4fc1bdbfa7724cbff02d68249fc75a62005da073d5092e6c12dd4baa`
- module-list SHA256:
  `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- generated source SHA256:
  `88d05498dc8956c95799cd0e6edb3b7080a8cd5d12b662a17545a7de7ffadf68`
- preserved kernel SHA256:
  `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- base Magisk boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The AP contained exactly one member, `boot.img.lz4`.

## Live Timeline

From `timeline.json`:

- `live_session_start`: `2026-07-08T18:38:43.054807Z`
- `candidate_flash_start`: `2026-07-08T18:38:54.637949Z`
- `candidate_flash_done`: `2026-07-08T18:38:56.135063Z`
- `candidate_boot_ready`: `2026-07-08T18:38:57.410687Z`
- `rollback_flash_start`: `2026-07-08T18:42:17.956685Z`
- `rollback_flash_done`: `2026-07-08T18:42:19.307528Z`
- `rollback_boot_ready`: `2026-07-08T18:43:04.622709Z`
- `live_session_end`: `2026-07-08T18:43:04.978512Z`

Observation result:

- `m33_p30_survival_window_pass=1`
- `m33_p30_result=survived-observation-window-manual-download-required`
- no host ADB/Odin endpoint returned during the 90 second observation window

Operator observation:

- no bootloop during the observation window
- RDX screen observed while entering manual rollback
- normal Download endpoint later appeared and rollback completed

## Rollback And Final Baseline

Rollback used the pinned Magisk boot-only AP:

`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`

Final baseline was independently verified after rollback:

- `adb devices -l`: S22+ Android device online
- `sys.boot_completed=1`
- `init.svc.bootanim=stopped`
- `ro.boot.verifiedbootstate=orange`
- `ro.boot.bootloader=S906NKSS7FYG8`
- Magisk root: `uid=0(root) ... context=u:r:magisk:s0`
- boot partition SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Retained Evidence

Post-rollback pstore was empty. `/proc/last_kmsg` was collected:

- path:
  `workspace/private/runs/s22plus_m33_p30_wdt_prefix_park_live_gate_20260708T183832Z/android_pstore/post_m33_p30_manual_after_survival_rollback_last_kmsg.bin`
- bytes: `2097136`
- SHA256:
  `02befc94d2767f1166b6794aeaab85e2d78da8c8d55e8711e32e7eeb71522845`
- M33 P30 marker: absent

The retained log contains bootloader/RDX evidence consistent with the operator
observation:

- `collect_rr_data : upload_cause = PMIC abnormal reset`
- `RDX is locked`
- `PonReason.HARD_RESET = 1`
- `boot_update_abnormal_reset_status`

As with earlier parked candidates, retained marker absence is not interpreted as
candidate non-execution after a survival-window pass plus successful rollback.

## Interpretation

P30 is M34 S0: it adds `usb_f_ss_acm.ko` while still doing no configfs gadget
creation, no role force, and no UDC bind. Since P30 survived where M32 failed,
the failure boundary is not the ACM function module load itself.

The active hypothesis is now the runtime gadget sequence:

1. configfs gadget/function/config object creation
2. `usb_role=device`
3. `UDC=a600000.dwc3` bind / pullup

## Policy State

`AGENTS.md` now marks the M33 P30 one-shot exception consumed/retired. The live
and rollback ack tokens are no longer active authorization.

No M34 live flash is authorized. The next safe step is host-only M34 S1/S2/S3
artifact preparation, with S1 first in live ordering after a future
SHA-pinned exception.
