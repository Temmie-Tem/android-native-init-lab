# S22+ M34 S7A2 GENI I2C Live Gate Ready

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: S7A2 host-side live gate helper is ready and fail-closed. No live
flash was run in this unit. A live run is still blocked until a fresh active
SHA-pinned `AGENTS.md` exception is added and committed.

## Context

S7A survived its 90 second observation window but produced no host-visible USB
device. The follow-up stock/root-cause analysis found that S7A loaded the
max77705 producer chain onto a dead I2C bus: the max77705 device sits behind
the GENI I2C transport on `994000.i2c`, but S7A did not load `gpi.ko`,
`msm-geni-se.ko`, or `i2c-msm-geni.ko`.

S7A2 is the bounded next discriminator:

- start from S7A
- add GENI I2C transport closure: `gpi.ko`, `msm-geni-se.ko`,
  `i2c-msm-geni.ko`
- preserve dep-safe actual order:
  `msm-geni-se.ko` -> `gpi.ko` -> `i2c-msm-geni.ko`
- keep `i2c-msm-geni.ko` before `pdic_max77705.ko`
- if no TypeC partner appears, write only
  `/sys/class/typec/port0/data_role=device` and
  `/sys/class/typec/port0/power_role=sink` before UDC bind
- keep minimal `ss_acm.0` configfs, `ssusb/mode=peripheral`, final
  `UDC=a600000.dwc3`
- keep `soft_connect` off and avoid FunctionFS/stock composite parity

## Helper

New helper:

`workspace/public/src/scripts/revalidation/s22plus_m34_s7a2_geni_i2c_live_gate.py`

New tests:

`tests/test_s22plus_m34_s7a2_geni_i2c_live_gate.py`

The helper pins S7A2-specific artifacts and refuses to use draft-only
authorization text. It also verifies the v0.7 manifest contract, including the
GENI I2C transport target list, actual transport order, S7A session-producer
baseline, S7A2 role-write discriminator, and the no-charge/OTG/rail/GPIO write
safety marker.

Candidate pins:

- AP.tar.md5 SHA256: `cb89ccf9c8c5481938ddd415930c78a23e1a679d45fdc57f95e6d1b48776bd59`
- padded `boot.img` SHA256: `b9a4d4c2170da2ed6125aa44734005303d81d874b72402513def97b2f8406a54`
- direct `/init` SHA256: `8f8eb4a6f4d94bc552ec61819b9c2b4ea4ec4de7fb7aa097fab7193c6f117e5a`
- template source SHA256: `ce12ea11a6c0f73f5f042801435b419637b473eff6631155f45d4ad382d8a80a`
- module-list SHA256: `c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998`
- preserved kernel SHA256: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- known-booting Magisk boot base SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

The default candidate AP path is:

`workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_7/S7A2/odin4/AP.tar.md5`

## Contract

The S7A2 manifest gate requires:

- stage `S7A2`
- module count `86`
- `stock_softdep_parity=true`
- `session_producer_parity=true`
- `geni_i2c_transport_parity=true`
- `typec_role_write_discriminator=true`
- `stage_s7a2_starts_from_s7a=true`
- `stage_s7a2_adds_geni_i2c_transport=true`
- `stage_s7a2_geni_i2c_transport_order_dep_safe=true`
- `stage_s7a2_role_write_discriminator_if_no_partner=true`
- `stage_s7a2_no_charge_otg_rail_gpio_writes=true`
- no reboot syscall in the S7A2 `/init`
- no Android/Magisk handoff
- no persistent partition mount
- no block write
- no module binary injection into boot ramdisk

The default run remains fail-closed until `AGENTS.md` carries an active
operator-approved S7A2 exception with the exact helper path, ack tokens, hashes,
GENI I2C markers, role-write markers, and no-charge/OTG/rail/GPIO write
markers.

## Validation

Commands passed:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m34_s7a2_geni_i2c_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_s7a2_geni_i2c_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s7a2_geni_i2c_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_runtime_gadget_split_build.py \
  tests/test_s22plus_m34_s7a_session_producer_live_gate.py \
  tests/test_s22plus_m34_s7a2_geni_i2c_live_gate.py
```

Results:

- S7A2 helper `py_compile`: pass
- S7A2 tests: `Ran 10 tests`, `OK`
- S7A2 offline-check: pass, no device action
- combined M34/S7A/S7A2 regression: `Ran 25 tests`, `OK`
- default helper run without active authorization: rejected at
  `AGENTS.md missing M34 S7A2 runtime-gadget authorization markers`

The fail-closed default occurs after artifact verification and before any live
Android reboot or flash action.

## Current Host State

After the operator reported an RDX-to-Download transition, the host-side check
observed the S22+ back on normal Android/MTP+ADB:

- `sys.boot_completed=1`
- `SM-S906N/g0q`
- bootloader `S906NKSS7FYG8`
- verified boot state `orange`
- `boot_recovery=0`
- Magisk `su` returned `uid=0(root)`

## Next Gate

Before live:

1. Add a fresh SHA-pinned active S7A2 one-shot exception to `AGENTS.md`.
2. Commit that active authorization.
3. Run the helper with `--live` and its S7A2 live ack token.

No S7A2 live flash is authorized by this report alone.
