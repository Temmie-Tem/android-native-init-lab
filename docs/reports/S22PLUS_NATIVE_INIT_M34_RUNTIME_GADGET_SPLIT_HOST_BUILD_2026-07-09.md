# S22+ M34 Runtime Gadget Split Host Build

Date: 2026-07-09 KST / 2026-07-08 UTC

## Verdict

HOST BUILD PASS / SOURCE READY / POLICY INERT.

M34 S1/S2/S3 v0.2 artifacts are built and statically gated. No live flash is
authorized by this report.

## Why This Exists

M33 P30 survived the full observation window with the P30/M32 45-module closure,
including `usb_f_ss_acm.ko`, while doing no runtime configfs/ACM binding. A live
read-only stock pull then showed Samsung's active gadget recipe uses
`ss_acm.0` in config `b.1` on UDC `a600000.dwc3`. The remaining failure boundary
is therefore the runtime gadget sequence, not module loading.

## Files

- C template:
  `workspace/public/src/native-init/s22plus_init_m34_runtime_gadget_split.c`
- Builder:
  `workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py`
- Tests:
  `tests/test_s22plus_m34_runtime_gadget_split_build.py`
- Private output:
  `workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_2/`
- Stock recipe input:
  `docs/reports/S22PLUS_STOCK_USB_GADGET_ACM_RECIPE_2026-07-09.md`

## Stages

S1:

- stock-ordered configfs gadget/function/config creation
- writes `UDC=none` before composition selection
- sets stock-style IDs (`0x04E8:0x6860`)
- creates and links `functions/ss_acm.0`
- no `g1/max_speed=high-speed`
- no `/sys/class/usb_role`
- no final `UDC=a600000.dwc3`

S2:

- includes S1 state
- writes `high-speed` to `/config/usb_gadget/g1/max_speed`
- writes `device` to `/sys/class/usb_role/*/role`
- no final `UDC=a600000.dwc3`

S3:

- includes S2 state
- selects only `a600000.dwc3`
- writes it to `/config/usb_gadget/g1/UDC`

## Hashes

Template source SHA256:

`ac20dcf724cf6864540d65958332d561d45409e7e85785a8c014882b37e29193`

Common module-list SHA256:

`2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`

S1:

- AP.tar.md5:
  `77e8858ea6becc3e988232d464f97827f55594f16ed6edebd23c3529c972d237`
- boot.img:
  `bb46233068890bb6849c63b4dab845ca48b65a9ffeac9e24ad08e81416b63f85`
- `/init`:
  `5339170f3138843a8f8da6cfd5f20f85696d3a9d18ae22bda439e21d0dd259cd`

S2:

- AP.tar.md5:
  `d235e6fd7c77c9fc2b63bd7280dcbf430783c9b62b5f361f43441c24687c38b3`
- boot.img:
  `f8838867e0b0fab5ffe5aa8717565d9304f635ef04487596a0baeb03b2dd7a70`
- `/init`:
  `fba33555bcc73d834a7dbfe87dc5e6fe3b622184d163ae72d478e18a0ce653b8`

S3:

- AP.tar.md5:
  `0ef55db2d38bec3df83cb77cd83f8ee6644054447ae7da10f8ecaecc8faa2957`
- boot.img:
  `87351f4955740aa4d83567406567c1ef4d6fcfa217d9ee5b0d7c446f2db09142`
- `/init`:
  `2f391e50ff271b2dfe14dce31dbfdd0f0fb2b6d353ae89a2079acad5b46e668f`

## Safety

Every generated AP is boot-only and contains exactly `boot.img.lz4`. The builder
uses MagiskBoot unpack/repack from the known-booting Magisk boot, not mkbootimg
from scratch. The no-change repack remains byte-identical to the base boot.

Static gates verify:

- no reboot syscall
- no Download beacon
- no Android/Magisk handoff
- no persistent partition mount
- no block write
- no module binary injection into boot ramdisk
- QMP and EUD modules remain excluded
- stock `UDC=none` is present before final bind
- S1 has no max-speed, role-force, or final UDC-bind strings
- S2 has max-speed and role-force but no final UDC-bind strings
- S3 binds only `a600000.dwc3`

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest -q \
  tests/test_s22plus_m34_runtime_gadget_split_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py \
  --force

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest -q \
  tests/test_s22plus_m34_runtime_gadget_split_build.py \
  tests/test_s22plus_m33_p30_wdt_prefix_park_live_gate.py \
  tests/test_s22plus_m33_wdt_prefix_park_build.py
```

Results:

- builder `py_compile`: pass
- M34 tests before manifest: 4 passed, 1 skipped
- builder `--force`: pass
- combined tests after manifest: 15 passed

## Next

The next live target is M34 S1 only. It needs a fresh SHA-pinned `AGENTS.md`
exception and explicit operator approval. S2/S3 must remain host-only until S1
has a live result.
