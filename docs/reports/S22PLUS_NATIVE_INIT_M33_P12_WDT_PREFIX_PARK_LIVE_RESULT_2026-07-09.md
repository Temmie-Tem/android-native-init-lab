# S22+ M33 P12 Watchdog Prefix-Park Live Result

Date: 2026-07-09 02:35 KST / 2026-07-08 17:35 UTC

## Verdict

PASS for the P12 boundary: M33 P12 survived the full 90 second observation
window without bootloop, ADB return, or Odin/Download return.

Rollback is also complete: after an initial RDX/protocol mismatch, normal
Download mode was entered and Magisk boot rollback succeeded. Final Android/
Magisk baseline is clean.

## Candidate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m33_p12_wdt_prefix_park_live_gate.py`

Candidate AP:

`workspace/private/outputs/s22plus_native_init/m33_wdt_prefix_park_matrix_v0_1/P12/odin4/AP.tar.md5`

Pinned hashes:

- AP.tar.md5: `47a7acd9f953de4464848aa02413b629064c512e2250356da0e33df5c46a3ce0`
- boot.img: `72afa113caf0bd8fc2f3c4d2a27108f3be94dd00f405071d3b7e609af8d8a2f2`
- `/init`: `8ce2d3aea3008b476fbc8113f8c5712abd120f0dc90cb158956b9ba1a6962405`
- module list: `b44e23aa5e38c1327bc3286f3b722558b56daa3198982434a474b4bff8c6d052`
- generated source: `a7d0f6cf2bd0ca217a92478a8f03c977d3e3d23e40383a050f1215853fa6d3b4`
- preserved kernel: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- base Magisk boot: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Live Timeline

Live run log:

`workspace/private/runs/s22plus_m33_p12_wdt_prefix_park_live_gate_20260708T172815Z/s22plus_m33_p12_wdt_prefix_park_live_gate.txt`

Rollback-only log:

`workspace/private/runs/s22plus_m33_p12_wdt_prefix_park_live_gate_20260708T173322Z/s22plus_m33_p12_wdt_prefix_park_live_gate.txt`

Observed sequence:

1. Candidate flashed boot-only.
2. Candidate left the original Download endpoint.
3. Host observed the full 90 second park window.
4. No ADB endpoint returned during the window.
5. No Odin/Download endpoint returned during the window.
6. Operator reported no bootloop during the window.
7. Helper logged `m33_p12_survival_window_pass=1`.
8. Helper logged `m33_p12_result=survived-observation-window-manual-download-required`.
9. During manual rollback, operator observed RDX.
10. First detected endpoint `/dev/bus/usb/003/027` failed Odin setup with `Protocol error 71` for both Magisk and stock fallback APs.
11. Operator entered normal Download mode.
12. Rollback-from-Download flashed the pinned Magisk boot AP successfully.
13. Android/Magisk returned cleanly.

## Recovery Result

Rollback command result:

- `manual_magisk_boot_rollback_odin_rc=0`
- boot upload reached 100%
- Android returned on ADB serial `<S22_SERIAL_REDACTED>`

Final independent checks:

- `adb devices -l`: `<S22_SERIAL_REDACTED> device ... model:SM_S906N device:g0q`
- model: `SM-S906N`
- `sys.boot_completed=1`
- bootanim: `stopped`
- Magisk root: `uid=0(root) gid=0(root) ... context=u:r:magisk:s0`
- boot partition SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Retained evidence after rollback:

- pstore files: empty
- `/proc/last_kmsg`: readable, 2,097,136 bytes
- M33 P12 marker in retained logs: absent

## Interpretation

P12 did not reproduce the M32 failure. That means M32's no-ACM/bootloop behavior
is not caused by the early supplier prefix plus watchdog closure alone.

Boundary state after P12:

- early clocks/interconnect suppliers: survived
- `sec_debug.ko` / `minidump.ko` in this prefix: survived
- `qcom_rpmh` / RPMh regulator supplier layer included in this prefix path:
  survived
- SMMU boundary: not yet tested
- HS/eUSB2 PHY boundary: not yet tested
- DWC3 boundary: not yet tested
- ACM function module boundary: not yet tested
- configfs/ACM runtime setup: not tested by M33 P12

Recommended next live split, after a fresh SHA-pinned exception:

1. P25 or P27 to jump to the SMMU/HS PHY boundary.
2. P28 if P27 survives, to isolate `dwc3-msm.ko`.
3. P30/P40 if P28 survives, to test full M32 module closure without configfs.

Do not reuse the M33 P12 exception or tokens. `AGENTS.md` now marks the P12
exception consumed/retired.
