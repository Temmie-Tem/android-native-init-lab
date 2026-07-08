# S22+ M33 P12 Watchdog Prefix-Park Live Gate Preflight

Date: 2026-07-09 02:26 KST / 2026-07-08 17:26 UTC

## Verdict

PASS: M33 P12 live gate is prepared and dry-run verified.

No live flash has been performed by this preflight. The operator approved live
progression, and `AGENTS.md` now contains a one-shot SHA-pinned boot-only M33
P12 exception.

## Candidate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m33_p12_wdt_prefix_park_live_gate.py`

Live ack:

`S22PLUS-M33-P12-WDT-PREFIX-PARK-LIVE-GATE`

Rollback-from-Download ack:

`S22PLUS-M33-P12-WDT-PREFIX-PARK-ROLLBACK-FROM-DOWNLOAD`

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

## Scope

M33 P12 is a park-only discriminator:

- boot partition only
- direct freestanding PID1
- watchdog-managed prefix closure
- no reboot syscall
- no Download beacon
- no USB/configfs/ACM
- no Android/Magisk handoff
- no persistent partition mount
- no block write
- no module binary injection into boot ramdisk

Module closure count: 21.

P12 includes early supplier modules plus the watchdog closure and does not cross
the SMMU/HS PHY/DWC3/ACM boundaries.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m33_p12_wdt_prefix_park_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest -q \
  tests/test_s22plus_m33_p12_wdt_prefix_park_live_gate.py \
  tests/test_s22plus_m33_wdt_prefix_park_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p12_wdt_prefix_park_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p12_wdt_prefix_park_live_gate.py
```

Results:

- `py_compile`: pass
- M33 P12 live/build tests: 9 passed
- `--offline-check`: pass, no device action
- dry-run: pass
- `agents_exception_missing=[]`
- Android identity: `SM-S906N/g0q/S906NKSS7FYG8`
- ADB serial: `RFCT519XWGK`
- vbstate: `orange`
- Android boot complete: `1`
- bootanim: `stopped`
- Magisk root: `uid=0(root) ... context=u:r:magisk:s0`
- Android stability: 4 samples OK
- current boot partition SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Dry-run log:

`workspace/private/runs/s22plus_m33_p12_wdt_prefix_park_live_gate_20260708T172627Z/s22plus_m33_p12_wdt_prefix_park_live_gate.txt`

## Next Command

Approved live command:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p12_wdt_prefix_park_live_gate.py \
  --live --ack S22PLUS-M33-P12-WDT-PREFIX-PARK-LIVE-GATE
```

Expected interpretation:

- Survives the observation window: P12 module loading is not the M32 failure
  boundary; manually enter Download when prompted for rollback.
- Unexpected Download/ADB before the window: P12 boundary failed; helper rolls
  back if Download is reachable, otherwise requires manual Download plus
  `--rollback-from-download`.
- PMIC/RDX abnormal reset before the observation window: fail for this boundary.
