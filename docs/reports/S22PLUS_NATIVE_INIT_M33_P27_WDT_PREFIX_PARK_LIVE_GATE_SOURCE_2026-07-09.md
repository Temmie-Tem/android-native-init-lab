# S22+ M33 P27 Watchdog Prefix-Park Live Gate Source

Date: 2026-07-09 02:40 KST / 2026-07-08 17:40 UTC

## Verdict

SOURCE READY / POLICY INERT.

The guarded M33 P27 live helper is implemented and statically verified, but no
live flash was performed. There is no active `AGENTS.md` authorization for P27.
Default execution fail-closes before Android/device preflight because the P27
policy markers and live tokens are absent from `AGENTS.md`.

## Why P27

M33 P12 survived the full 90 second park window, so the early supplier prefix is
not the M32 no-ACM/bootloop boundary. P27 is the next high-information split:
it includes SMMU and HS/eUSB2 PHY modules but still stops before DWC3 and ACM.

Interpretation for a future approved live run:

- P27 survives: SMMU + HS/eUSB2 PHY module loading is not the M32 failure
  boundary; move to P28 for DWC3.
- P27 fails: run P25 next to separate SMMU/secure-buffer from HS PHY.

## Helper

`workspace/public/src/scripts/revalidation/s22plus_m33_p27_wdt_prefix_park_live_gate.py`

The helper mirrors the P12 live gate shape:

- `--offline-check`: verifies candidate AP, manifest, and rollback APs only.
- default run: also requires active `AGENTS.md` markers and Android baseline.
- `--live`: requires a future active P27 live token.
- `--rollback-from-download`: requires a future active P27 rollback token.

No active token is present in `AGENTS.md` at this checkpoint.

## Candidate Pins

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

## Module Boundary

P27 module count: 40.

P27 includes:

- `arm_smmu.ko`
- `phy-msm-snps-hs.ko`
- `phy-msm-snps-eusb2.ko`
- `usb_f_ss_mon_gadget.ko`

P27 excludes:

- `dwc3-msm.ko`
- `usb_f_ss_acm.ko`
- `phy-msm-ssusb-qmp.ko`
- `eud.ko`

Runtime remains park-only:

- no reboot syscall
- no Download beacon
- no runtime USB/configfs/ACM setup
- no Android/Magisk handoff
- no persistent partition mount
- no block write

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m33_p27_wdt_prefix_park_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest -q \
  tests/test_s22plus_m33_p27_wdt_prefix_park_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p27_wdt_prefix_park_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p27_wdt_prefix_park_live_gate.py
```

Results:

- `py_compile`: pass
- P27 live-gate tests: 4 passed
- `--offline-check`: pass, no device action
- default run: fail-closed on missing P27 `AGENTS.md` authorization markers

Default fail-closed evidence includes missing P27 live and rollback tokens:

- `S22PLUS-M33-P27-WDT-PREFIX-PARK-LIVE-GATE`
- `S22PLUS-M33-P27-WDT-PREFIX-PARK-ROLLBACK-FROM-DOWNLOAD`

## Next Gate

A future live run requires a fresh SHA-pinned `AGENTS.md` exception for P27 and
explicit operator approval. Do not flash from this source-ready checkpoint alone.
