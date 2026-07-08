# S22+ M34 S7A2 GENI I2C Transport Host Build

Date: 2026-07-09 KST

Status: HOST-BUILD COMPLETE. No live flash is authorized by this report.

## Scope

S7A2 follows the corrected S7A root-cause:

- S7A loaded the max77705/PDIC/altmode producer modules.
- S7A did not load the GENI I2C transport for the discrete max77705 on
  `994000.i2c`.
- Therefore S7A did not actually prove whether the max77705 producer chain could
  create a TypeC peripheral session.

S7A2 keeps the S7A runtime shape and adds only:

- GENI I2C transport closure: `gpi.ko`, `msm-geni-se.ko`,
  `i2c-msm-geni.ko`
- a bounded TypeC role-write discriminator before UDC bind: if
  `/sys/class/typec/port0-partner/uevent` is absent/unreadable, write
  `/sys/class/typec/port0/data_role=device` and
  `/sys/class/typec/port0/power_role=sink`

It still keeps minimal `ss_acm.0` configfs, `ssusb/mode=peripheral`,
`UDC=a600000.dwc3`, no `soft_connect`, no FunctionFS, no stock composite, no
Android/Magisk handoff, no reboot request, no persistent mount, and no block
writes.

## Artifacts

Output root:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_7/
```

S7A2 artifact hashes:

```text
AP.tar.md5   cb89ccf9c8c5481938ddd415930c78a23e1a679d45fdc57f95e6d1b48776bd59
AP.tar       9d61973bdb06f9e82afe6c282d220fd3e465e833dcc4637443fb82e87c8bb8bc
boot.img     b9a4d4c2170da2ed6125aa44734005303d81d874b72402513def97b2f8406a54
boot.img.lz4 97f9ea1b002954ccc65599a4e688451ab307d9964e347e19309dba58d9dbee12
/init        8f8eb4a6f4d94bc552ec61819b9c2b4ea4ec4de7fb7aa097fab7193c6f117e5a
module list  c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998
```

The AP tar contains exactly one member: `boot.img.lz4`.

## Module Closure

S7A2 module count is `86`. The GENI I2C target list is:

```text
gpi.ko
msm-geni-se.ko
i2c-msm-geni.ko
```

The actual dep-safe load order in the final module list is:

```text
msm-geni-se.ko
gpi.ko
i2c-msm-geni.ko
```

This differs from the shorthand order in the root-cause note, but matches
`modules.dep` and stock `modules.load.recovery` tie-breaks. The important
invariant is satisfied: `i2c-msm-geni.ko` is loaded before
`pdic_max77705.ko`.

S7A2 still includes the S7A risk modules through the stock charger/fuelgauge
closure, including `sec_debug_region.ko`; this requires a fresh live risk review
before any flash.

## Runtime Markers

The S7A2 `/init` required strings include:

```text
stage=S7A2
runtime_step=S7A2
geni_i2c_transport=1
i2c_msm_geni=1
gpi_dma=1
msm_geni_se=1
role_write_discriminator=1
phase=typec_partner_check
phase=typec_role_write
role_device_rc=
role_sink_rc=
```

The candidate does not contain `high-speed`, `phase=ssusb_speed`, or
`/sys/class/udc/a600000.dwc3/soft_connect`.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_runtime_gadget_split_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_s7a_session_producer_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py --force

git diff --check
```

Results:

```text
build test: Ran 5 tests, OK
S7A live-helper regression: Ran 10 tests, OK
git diff --check: OK
builder: v0.7 artifacts generated
```

## Authorization

No active live authorization exists. S7A2 live would require a fresh
SHA-pinned `AGENTS.md` boot-only exception for the exact AP hash above, explicit
operator approval, and the usual rollback gate. This report does not authorize
S7A repeat, S7A2 live flash, non-boot flashing, DTBO/vendor_boot/vbmeta/recovery
writes, raw host `dd`, fastboot, Magisk modules, format data, EUD writes,
charge-current/OTG/rail/regulator/GDSC/GPIO writes, or any A90 action.
