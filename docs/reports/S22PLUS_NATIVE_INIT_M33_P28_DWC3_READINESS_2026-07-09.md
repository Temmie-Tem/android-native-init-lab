# S22+ M33 P28 DWC3 Readiness

Date: 2026-07-09 03:04 KST / 2026-07-08 18:04 UTC

## Verdict

P28 is selected as the next high-information gate after P27 survived.

No live flash was performed. There is no active `AGENTS.md` authorization for
P28, and default helper execution fail-closes before Android/device preflight.

## Why P28

M33 P27 survived the full 90 second park window with SMMU and HS/eUSB2 PHY
module loading. That makes the next boundary DWC3 module loading without ACM or
runtime configfs.

P28 tests exactly that boundary:

- includes `dwc3-msm.ko`
- includes monitor gadget dependencies
- excludes `usb_f_ss_acm.ko`
- excludes runtime USB/configfs/ACM setup
- remains park-only

## Candidate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m33_p28_wdt_prefix_park_live_gate.py`

Candidate AP:

`workspace/private/outputs/s22plus_native_init/m33_wdt_prefix_park_matrix_v0_1/P28/odin4/AP.tar.md5`

Pinned hashes:

- AP.tar.md5: `4c76ef4df814356a7acfa9ce9a00c2fe003208ff8289c2874535e26b7e1c3f07`
- boot.img: `3bc59d6df58b5c7130e6ca531a6a6cd3a4d35e14ff7fd6667da72e2bd40e9e29`
- `/init`: `2ef661b9e5a1496674b6cc457c9b0e84c60ae7af01914c2403db602c6ebe84b1`
- module list: `ef57a00fbef4b9c89936b30fc5c001974fbe9c2ece590c6a6984cb4695318a8f`
- generated source: `8d752ade0ee5100b5f91cb7fb15c09d24652a97e03721fb8c4d784d1f419f289`
- preserved kernel: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- base Magisk boot: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Scope

P28 remains park-only:

- boot partition only
- direct freestanding PID1
- watchdog-managed prefix closure
- no reboot syscall
- no Download beacon
- no runtime USB/configfs/ACM
- no Android/Magisk handoff
- no persistent partition mount
- no block write
- no module binary injection into boot ramdisk
- AP tar member list must be exactly `["boot.img.lz4"]`

P28 keeps `phy-msm-ssusb-qmp.ko` and EUD excluded.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m33_p28_wdt_prefix_park_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest -q \
  tests/test_s22plus_m33_p28_wdt_prefix_park_live_gate.py \
  tests/test_s22plus_m33_wdt_prefix_park_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p28_wdt_prefix_park_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p28_wdt_prefix_park_live_gate.py
```

Results:

- `py_compile`: pass
- M33 P28 live/build tests: 9 passed
- `--offline-check`: pass, no device action
- default run: fail-closed on missing P28 `AGENTS.md` authorization markers

Default fail-closed evidence includes:

- `S22PLUS-M33-P28-WDT-PREFIX-PARK-LIVE-GATE`
- `S22PLUS-M33-P28-WDT-PREFIX-PARK-ROLLBACK-FROM-DOWNLOAD`
- `4c76ef4df814356a7acfa9ce9a00c2fe003208ff8289c2874535e26b7e1c3f07`
- `DWC3-without-ACM prefix`

## Current Device Baseline

Verified before this readiness checkpoint:

- Android device: `SM-S906N/g0q/S906NKSS7FYG8`
- `sys.boot_completed=1`
- `init.svc.bootanim=stopped`
- `ro.boot.verifiedbootstate=orange`
- Magisk root: `uid=0(root) ... context=u:r:magisk:s0`
- boot partition SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Next

P28 live requires a fresh operator approval and a fresh SHA-pinned `AGENTS.md`
exception. Until then, no P28 flash is authorized.
