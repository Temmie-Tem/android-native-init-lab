# S22+ M33 P30/P40 Post-DWC3 Branch Source

Date: 2026-07-09 03:08 KST / 2026-07-08 18:08 UTC

## Verdict

SOURCE READY / POLICY INERT for P30 and P40.

No live flash was performed. There is no active `AGENTS.md` authorization for
P30 or P40. Default execution for both helpers fail-closes before Android/device
preflight because the variant-specific policy markers and live tokens are absent
from `AGENTS.md`.

## Why These Two

P28 is the selected next live boundary after P27 survived. If P28 survives, the
next useful split is ACM-module loading without runtime configfs/ACM setup:

- P30: ACM function module included, still park-only and no runtime configfs.
- P40: full M32 module closure, still park-only and no runtime configfs.

Both are prepared now so the post-P28 branch can move without rebuilding the
host-side gate shape.

## Helpers

P30:

`workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py`

P40:

`workspace/public/src/scripts/revalidation/s22plus_m33_p40_wdt_prefix_park_live_gate.py`

Both helpers keep the same fail-closed shape:

- `--offline-check`: verifies candidate AP, manifest, and rollback APs only.
- default run: requires active `AGENTS.md` markers before Android/device preflight.
- `--live`: requires a future active variant-specific live token.
- `--rollback-from-download`: requires a future active variant-specific rollback token.

No active token is present in `AGENTS.md` at this checkpoint.

## P30 Candidate

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

P30 boundary:

- module count: 45
- includes `dwc3-msm.ko`
- includes `usb_f_ss_acm.ko`
- excludes runtime USB/configfs/ACM setup
- excludes `phy-msm-ssusb-qmp.ko`
- excludes EUD

## P40 Candidate

Candidate AP:

`workspace/private/outputs/s22plus_native_init/m33_wdt_prefix_park_matrix_v0_1/P40/odin4/AP.tar.md5`

Pinned hashes:

- AP.tar.md5: `420986c447df5cd155aee1ea32ece8ec5a7b021793dd9058d4fe6bc3744b7c34`
- boot.img: `b07bbc97a36f63c92db915829b322ef8200ceb5944a244b0a8406780b46a9621`
- `/init`: `d2500dcf739d5d72c705ff24edbe6332c5a3d51defe08651c6cd517f14607274`
- module list: `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- generated source: `cfd3bb3f510a53d07a1e9f21846953ff13ecf83680debf0aa839c79507eb50da`
- preserved kernel: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- base Magisk boot: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

P40 boundary:

- module count: 45
- full M32 module closure
- includes `dwc3-msm.ko`
- includes `usb_f_ss_acm.ko`
- excludes runtime USB/configfs/ACM setup
- excludes `phy-msm-ssusb-qmp.ko`
- excludes EUD

## Shared Runtime Scope

Both helpers remain park-only:

- no reboot syscall
- no Download beacon
- no runtime USB/configfs/ACM setup
- no Android/Magisk handoff
- no persistent partition mount
- no block write
- no module binary injection into boot ramdisk
- boot AP must contain only `boot.img.lz4`

## Validation

Commands:

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
  workspace/public/src/scripts/revalidation/s22plus_m33_p40_wdt_prefix_park_live_gate.py \
  --offline-check
```

Results:

- `py_compile`: pass
- M33 P30/P40/build tests: 13 passed
- P30 `--offline-check`: pass, no device action
- P40 `--offline-check`: pass, no device action
- P30 default run: fail-closed on missing `AGENTS.md` authorization markers
- P40 default run: fail-closed on missing `AGENTS.md` authorization markers

## Current Device Baseline

Verified before this checkpoint:

- Android device: `SM-S906N/g0q/S906NKSS7FYG8`
- `sys.boot_completed=1`
- `init.svc.bootanim=stopped`
- `ro.boot.verifiedbootstate=orange`
- Magisk root: `uid=0(root) ... context=u:r:magisk:s0`
- boot partition SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Next

Original checkpoint: the next actual live gate remained P28. P30/P40 were
branch-ready artifacts only and required fresh SHA-pinned `AGENTS.md`
exceptions plus explicit operator approval before any flash.

Post-P28 update: P28 later survived its live gate and was consumed. The current
next high-information gate is P30. P40 remains source-ready, but P30 and P40
have the same module-list SHA256 and same 45-module closure, so P40 is
subsumed for live ordering unless a future non-module runtime reason appears.
Current readiness report:

`docs/reports/S22PLUS_NATIVE_INIT_M33_P30_READY_AFTER_P28_2026-07-09.md`
