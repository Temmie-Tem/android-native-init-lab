# S22+ M33 P27 Watchdog Prefix-Park Live Result

Date: 2026-07-09 03:00 KST / 2026-07-08 18:00 UTC

## Verdict

PASS: M33 P27 survived the full observation window and rollback completed.

The P27 one-shot live gate is consumed and retired. `AGENTS.md` no longer
contains the active P27 live/rollback tokens, so default helper execution must
fail closed again.

## Candidate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m33_p27_wdt_prefix_park_live_gate.py`

Run log:

`workspace/private/runs/s22plus_m33_p27_wdt_prefix_park_live_gate_20260708T175410Z/s22plus_m33_p27_wdt_prefix_park_live_gate.txt`

Candidate AP:

`workspace/private/outputs/s22plus_native_init/m33_wdt_prefix_park_matrix_v0_1/P27/odin4/AP.tar.md5`

Pinned hashes:

- AP.tar.md5: `9110e793f5cc812c856dedf35aaa4cc2f2c692f8561bba9dbe10c7b1e8a29371`
- boot.img: `16efd35b4bb340b2c8d5d5b99e3e3d3e19d4c01a60e87f6ed3cf60acc90386ea`
- `/init`: `4ce13d65264c2e887aadeefe66c812e4079340b14745bfb277b37a9fde7e8785`
- module list: `11f8ccac67944d689d327d0157eb2f504e794d205df91c480506a3247d9c830e`
- generated source: `b57c37678ec5b145d3b1c6208c6ee685ba40401512115e08e4f92afa63627f33`
- preserved kernel: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- base Magisk boot: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Result

- Candidate Odin flash: pass.
- Original Download endpoint disconnected after flash: pass.
- Observation window: 90 seconds.
- Host observed no ADB endpoint during the window.
- Host observed no Odin/Download endpoint during the window.
- Helper result: `m33_p27_survival_window_pass=1`.
- Helper result: `m33_p27_result=survived-observation-window-manual-download-required`.
- Operator observation during the window: no bootloop.
- After survival proof, operator reported PMIC/RDX while entering manual
  recovery.
- Manual Download endpoint appeared later and rollback ran from that endpoint.
- Magisk boot rollback Odin flash: pass.
- Android boot after rollback: pass.
- Final boot partition SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.

Final Android baseline:

- `sys.boot_completed=1`
- `init.svc.bootanim=stopped`
- `ro.boot.verifiedbootstate=orange`
- Magisk root: `uid=0(root) ... context=u:r:magisk:s0`
- bootloader/build: `S906NKSS7FYG8`

## Timing

From `timeline.json`:

- live session: 242.982 s
- candidate flash: 1.484 s
- candidate boot-ready to rollback flash start: 181.424 s
- rollback flash: 1.342 s
- rollback flash done to Android boot-ready: 45.638 s

Timeline events use the standard single `events:[{name,timestamp_utc}]` schema.

## Retained Evidence

Collected files:

- `android_pstore/post_m33_p27_manual_after_survival_rollback_last_kmsg.bin`
- host observation snapshots under `host_observation/`
- `timeline.json`

Retained evidence summary:

- pstore files: none
- `/proc/last_kmsg`: readable, 2,097,136 bytes
- P27 marker in pstore/last_kmsg: absent
- `/proc/last_kmsg` contains XBL/PMIC `boot_update_abnormal_reset_status`
  material, consistent with the operator's PMIC/RDX observation, but not a P27
  marker.

## Interpretation

P27 includes SMMU and HS/eUSB2 PHY module loading while excluding DWC3 and ACM.
Because it survived the 90 second window, this boundary is not the M32 no-ACM/
bootloop failure boundary.

Next high-information live target is P28, already source-ready, to isolate
`dwc3-msm.ko` before reintroducing ACM/configfs.
