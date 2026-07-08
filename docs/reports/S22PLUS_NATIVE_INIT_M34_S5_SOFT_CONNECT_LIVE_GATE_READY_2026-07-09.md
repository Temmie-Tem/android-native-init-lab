# S22+ M34 S5 Soft Connect Live Gate Ready

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: LIVE-GATE HELPER READY. Default execution fails closed until a fresh
SHA-pinned `AGENTS.md` exception exists.

## Scope

S5 is the next bounded live discriminator after S4 survived 90 seconds but
never exposed a host-visible USB device. The candidate keeps S4's
`ssusb/speed=high-speed` plus `ssusb/mode=peripheral` role lever, keeps final
`UDC=a600000.dwc3`, and adds exactly one post-bind action:

```text
/sys/class/udc/a600000.dwc3/soft_connect = connect
```

No descriptor, string, companion-function, module-closure, or boot-construction
change is included in S5.

## Helper

Path:

`workspace/public/src/scripts/revalidation/s22plus_m34_s5_soft_connect_live_gate.py`

Test:

`tests/test_s22plus_m34_s5_soft_connect_live_gate.py`

The helper preserves the S4 live flow:

- verify candidate AP, manifest, and rollback APs before any live action
- verify Android/Magisk current baseline and boot partition hash before live
- reboot Android to Download mode
- flash boot-only candidate AP
- require original Download endpoint disconnect before counting candidate boot
- observe the candidate park window with enhanced host USB snapshots
- require manual Download rollback after survival or ACM sighting
- rollback boot-only to the pinned Magisk boot AP, with stock boot fallback
- collect retained evidence from Android after rollback
- emit canonical `events` timeline phases

## Pins

S5 candidate pins:

- AP.tar.md5 SHA256:
  `3a63dc339577d4aaf550159743b81edd9c1318ef5c6c4b745ed363f171d30d5e`
- padded `boot.img` SHA256:
  `09751f5fce9f25be3ce7b814f00c04cafd22ae9a96d8c69ab9d52b6274951a95`
- direct `/init` SHA256:
  `efecaf1842aff95907b2f2780dc12531b0980acff6cbe64f789e9ad4b6c3c55c`
- template source SHA256:
  `bf90fbadbaf72bb9287150d769104b97ec8faaae0ce1c0591aaafdeb88004fb8`
- module-list SHA256:
  `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- preserved kernel SHA256:
  `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- known-booting Magisk boot base SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Rollback pins remain:

- Magisk boot-only rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- stock boot-only fallback AP SHA256:
  `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`

The S5 AP contains exactly one tar member: `boot.img.lz4`.

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/s22plus_m34_s5_soft_connect_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_m34_s5_soft_connect_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s5_soft_connect_live_gate.py --offline-check
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s5_soft_connect_live_gate.py
```

Results:

- helper `py_compile`: pass
- S5 helper unit tests: pass, 8 tests
- helper `--offline-check`: pass, no device action
- default execution before `AGENTS.md` authorization: fail-closed with rc=1
  before Android/flash actions
- default fail-closed missing markers included the S5 helper path, live token,
  rollback token, S5 hashes, `soft_connect=connect`,
  `/sys/class/udc/a600000.dwc3/soft_connect`, `phase=soft_connect`, enhanced
  host USB observation, and no descriptor/companion-function change

## Authorization State

No active live authorization exists in this report. The operator has given
in-thread pre-approval, but live execution still requires inserting a fresh
SHA-pinned active S5 exception into `AGENTS.md`, then running the helper dry-run
successfully before `--live`.

This report does not authorize S5 live flash by itself, S4 repeat, DTBO,
vendor_boot, recovery, vbmeta, non-boot flash, raw host `dd`, fastboot, EUD
writes, RDX PC dump retrieval, Magisk modules, format data, or any A90 action.
