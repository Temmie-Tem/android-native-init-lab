# S22+ M34 Runtime Gadget Split Host Build

Date: 2026-07-09 KST / 2026-07-08 UTC

## Verdict

HOST BUILD PASS / SOURCE READY / POLICY INERT.

M34 S1/S2/S3 artifacts are built and statically gated. No live flash is
authorized by this report.

## Why This Exists

M33 P30 survived the full observation window with the P30/M32 45-module closure,
including `usb_f_ss_acm.ko`, while doing no runtime configfs/ACM binding. The
remaining failure boundary is therefore the runtime gadget sequence, not module
loading.

## Files

- C template:
  `workspace/public/src/native-init/s22plus_init_m34_runtime_gadget_split.c`
- Builder:
  `workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py`
- Tests:
  `tests/test_s22plus_m34_runtime_gadget_split_build.py`
- Private output:
  `workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_1/`

## Stages

S1:

- configfs gadget/function/config creation
- creates and links `functions/ss_acm.0`
- no `/sys/class/usb_role`
- no `/config/usb_gadget/g1/UDC`
- no `a600000.dwc3`

S2:

- includes S1 state
- writes `device` to `/sys/class/usb_role/*/role`
- no `/config/usb_gadget/g1/UDC`
- no `a600000.dwc3`

S3:

- includes S2 state
- selects only `a600000.dwc3`
- writes it to `/config/usb_gadget/g1/UDC`

## Hashes

Template source SHA256:

`4caf29f8ef29fbbf3e0ae3bd00956e33c8d6fc2d8af87e1b9aabeb40f682d47a`

Common module-list SHA256:

`2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`

S1:

- AP.tar.md5:
  `8ab6d8a0fda1e61e17dffd37657e4d36326bc08f4c056d6eb25dcdbf684e2f0e`
- boot.img:
  `fe6a4e6533835bcb208bc01242e6e05c0e3a75bb47045f542abd84a7ff0d8f84`
- `/init`:
  `40a3a8a670cda4eaed3e909503781f23f18fc43f2b8f327a848c5f96d37cc199`

S2:

- AP.tar.md5:
  `d51937eee0955ab4fec77cade2da9f7245cb4d9b3ed3c22077c2eddede995afe`
- boot.img:
  `cd89e2be44e51b1b957dfb8f8d33aecabe2b6c628b267641788a2c547cff41ae`
- `/init`:
  `7901789fff98cf899b632bb229357c24d1dee515651e6e5399dd18dc16bd12c7`

S3:

- AP.tar.md5:
  `2972a00048a4dfe9acc5a98f789b49f9fe5f731a3f701790e89fa97f6344c921`
- boot.img:
  `e5b884ade62b23c18f28627328f42b0a7dc6ccea66705bb4fee24198061c9a24`
- `/init`:
  `fe5597e6145f443d5bb779b74492be4bf42737540eb1e21c7e6998b35efc939b`

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
- S1 has no role-force or UDC-bind strings
- S2 has no UDC-bind strings
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
- combined tests after manifest: 14 passed

## Next

The next live target is M34 S1 only. It needs a fresh SHA-pinned `AGENTS.md`
exception and explicit operator approval. S2/S3 must remain host-only until S1
has a live result.
