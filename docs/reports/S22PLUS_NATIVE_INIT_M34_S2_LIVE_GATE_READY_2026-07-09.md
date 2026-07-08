# S22+ M34 S2 Live Gate Ready

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: S2 host-side live gate helper is ready and fail-closed. The operator
has approved live in-thread, but the run still requires a fresh active
SHA-pinned `AGENTS.md` exception before any flash.

## Context

M34 S1 survived the full 90 second observation window and was rolled back
cleanly. S1 proved that the following are not the observed 35 second reset
boundary:

- full 45-module closure including `dwc3-msm.ko` and `usb_f_ss_acm.ko`
- stock-ordered configfs gadget/function/config creation
- `UDC=none`
- stock IDs `0x04E8:0x6860`
- `functions/ss_acm.0` link

M34 S2 is the next isolated runtime-gadget discriminator. It adds only the two
off-stock pullup knobs while still not binding the final UDC.

## Helper

New helper:

`workspace/public/src/scripts/revalidation/s22plus_m34_s2_runtime_gadget_live_gate.py`

The helper is copied from the S1 live-gate structure but pins S2-specific
artifacts and semantics.

Candidate pins:

- AP.tar.md5 SHA256: `d235e6fd7c77c9fc2b63bd7280dcbf430783c9b62b5f361f43441c24687c38b3`
- padded `boot.img` SHA256: `f8838867e0b0fab5ffe5aa8717565d9304f635ef04487596a0baeb03b2dd7a70`
- direct `/init` SHA256: `fba33555bcc73d834a7dbfe87dc5e6fe3b622184d163ae72d478e18a0ce653b8`
- template source SHA256: `ac20dcf724cf6864540d65958332d561d45409e7e85785a8c014882b37e29193`
- module-list SHA256: `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- preserved kernel SHA256: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- known-booting Magisk boot base SHA256: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The default candidate AP path is:

`workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_2/S2/odin4/AP.tar.md5`

## Contract

The S2 manifest gate requires:

- stage `S2`
- stock-ordered configfs gadget/function/config
- `UDC=none`
- stock IDs `0x04E8:0x6860`
- `functions/ss_acm.0` link
- `max_speed_high_speed=true`
- `usb_role_force=true`
- `udc_bind=false`
- no final `UDC=a600000.dwc3`

The helper also verifies:

- boot-only single-member AP
- exact S2 AP/boot/init/source/module/kernel/base hashes
- no reboot syscall in the S2 `/init`
- no Android/Magisk handoff
- no persistent partition mount
- no block write
- no module binary injection into boot ramdisk
- `phy-msm-ssusb-qmp.ko` excluded
- EUD excluded
- rollback AP hashes pinned

## Validation

Commands passed:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m34_s2_runtime_gadget_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_s2_runtime_gadget_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s2_runtime_gadget_live_gate.py \
  --offline-check
```

The S2 helper also failed closed without an active `AGENTS.md` exception:

```text
AGENTS.md missing M34 S2 runtime-gadget authorization markers
```

That failure occurs after artifact verification and before Android/flash
actions.

## Next Gate

Before live:

1. Add a fresh SHA-pinned active S2 one-shot exception to `AGENTS.md`.
2. Commit that active authorization.
3. Run the helper with `--live` and its S2 live ack token.

During live, the expected high-information outcomes are:

- survives 60-90 seconds: `max_speed=high-speed` + `usb_role=device` are not the
  reset wall; proceed to S3/final UDC bind design.
- PMIC/RDX/Odin return before the survival window: one of the two off-stock
  knobs is implicated; split `max_speed` vs `usb_role` before any S3/final
  pullup.

S3 and final UDC pullup remain blocked until the S2 result is known.

