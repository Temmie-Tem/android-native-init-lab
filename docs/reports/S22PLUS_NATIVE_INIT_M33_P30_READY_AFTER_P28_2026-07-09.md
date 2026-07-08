# S22+ M33 P30 Readiness After P28

Date: 2026-07-09 KST / 2026-07-08 UTC

## Verdict

P30 is the next high-information live gate after P28 survived.

No live flash is authorized by this report. `AGENTS.md` has no active P30
exception or live/rollback token, so default helper execution must continue to
fail closed before Android/device preflight.

Post-P28 USB analysis reframes P30 as M34 S0: ACM function module load only,
with no runtime configfs/ACM binding. If P30 survives, stop module-list bisection
and move to the M34 runtime gadget split.

## Why P30

The M33 P28 live run proved the DWC3-without-ACM prefix survived the full 90
second observation window. The next remaining module boundary is therefore the
ACM function module itself, still with runtime configfs/ACM setup disabled.

P30 is that boundary:

- includes `usb_f_ss_acm.ko`
- includes `dwc3-msm.ko`
- includes monitor gadget dependencies
- still does no runtime configfs or ACM binding
- remains park-only: no reboot syscall, no Download beacon, no Android/Magisk
  handoff, no persistent mount, no block write

## P40 Priority

P40 remains source-ready, but it is lower priority for live ordering. Manifest
comparison proves P30 and P40 have the same 45-module closure and the same
module-list SHA256:

`2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`

The AP images and `/init` hashes differ because the variants carry different
labels, markers, and prefix metadata, but they do not differ in module-boundary
coverage. A P30 live result therefore carries the same module-closure signal as
P40 unless a future non-module runtime reason appears.

## P30 Candidate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py`

Candidate AP:

`workspace/private/outputs/s22plus_native_init/m33_wdt_prefix_park_matrix_v0_1/P30/odin4/AP.tar.md5`

Pinned hashes:

- AP.tar.md5: `e7cadd856da852e577adf32e088c0fee668904f265cdad1e9309072ccb2b18fd`
- boot.img: `0a972bcb4af2b75d5177ae9767e34a4caa8b8c94237afa708bb4a577b2ba7bfe`
- `/init`: `48afc2af4fc1bdbfa7724cbff02d68249fc75a62005da073d5092e6c12dd4baa`
- module list: `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- generated source: `88d05498dc8956c95799cd0e6edb3b7080a8cd5d12b662a17545a7de7ffadf68`
- preserved kernel: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- base Magisk boot: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Required Live Gate Shape

A future live run needs a fresh SHA-pinned `AGENTS.md` exception and explicit
operator approval. The exception should authorize only one boot-only P30 run
and should keep the existing safety boundary:

- candidate AP contains only `boot.img.lz4`
- rollback uses pinned Magisk boot-only AP first
- stock boot-only rollback is fallback only if Magisk rollback fails and
  Download mode remains available
- no P30 repeat
- no P40 live under the P30 gate
- no M33 rebuild, M32 repeat, kernel rebuild, recovery/vendor_boot/vbmeta/DTBO/
  non-boot flash, raw host `dd`, fastboot, multidisabler, format data, EUD
  writes, or A90 action

## Validation To Run Before Live

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest -q \
  tests/test_s22plus_m33_p30_wdt_prefix_park_live_gate.py \
  tests/test_s22plus_m33_wdt_prefix_park_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py
```

The final command should fail closed until the one-shot `AGENTS.md` exception is
present.

## Validation Result

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_m33_p40_wdt_prefix_park_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest -q \
  tests/test_s22plus_m33_p30_wdt_prefix_park_live_gate.py \
  tests/test_s22plus_m33_p40_wdt_prefix_park_live_gate.py \
  tests/test_s22plus_m33_wdt_prefix_park_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py
```

Results:

- `py_compile`: pass
- M33 P30/P40/build tests: 14 passed
- P30 `--offline-check`: pass, no device action
- P30 default execution: `rc=1`, fail-closed on missing P30 `AGENTS.md`
  authorization markers before Android/device preflight

Current Android baseline:

- Android device: `SM-S906N/g0q/S906NKSS7FYG8`
- `sys.boot_completed=1`
- `init.svc.bootanim=stopped`
- `ro.boot.verifiedbootstate=orange`
- Magisk root: `uid=0(root) ... context=u:r:magisk:s0`
- boot partition SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Next

Do not flash P30 until there is fresh operator approval and a fresh SHA-pinned
`AGENTS.md` exception for exactly one P30 boot-only live gate. P40 should stay
parked unless P30's result creates a non-module reason to test the P40-labeled
image separately.

If P30 survives, build M34 S1/S2/S3 host-only artifacts:

- S1: configfs gadget/function/config, no role force, no UDC
- S2: role force, no UDC
- S3: UDC bind / pullup on `a600000.dwc3`

Design report:

`docs/reports/S22PLUS_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_DESIGN_2026-07-09.md`
