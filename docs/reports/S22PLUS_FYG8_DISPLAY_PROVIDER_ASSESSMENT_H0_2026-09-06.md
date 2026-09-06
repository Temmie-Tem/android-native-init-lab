# S22+ FYG8 display provider assessment — H0

Date: 2026-09-06. Exact target: SM-S906N / g0q / S906NKSS7FYG8.
Result: **provider linkage and display-only bus-match H0 checks passed**.
No connected command, module load, boot candidate construction or flash occurred.
P350 remains consumed and closed with healthy Magisk rollback.

## Result

The panel path needs three additions to the existing 82-module plan:
`pmic_class.ko`, `s2dos05-regulator.ko` and a **restricted** `i2c-gpio.ko`.
The stock GPIO-I2C module must not be substituted for the restricted artifact:
it would bind four enabled buses, including non-display devices.

The three providers' 91 versioned imports resolve against the exact P350 Image
and the proposed 85-module union, without missing, ambiguous or CRC-mismatched
providers. Vermagic matches the retained FYG8 kernel. This is symbol/config
compatibility evidence, not complete runtime ABI or probe qualification.

The smallest required bus restriction was implemented and built as an external
module. Independent review found no concrete defect in that restriction or this
bounded provider assessment. This is not approval of a flashable successor.

## Exact artifacts and dependency order

Original stock modules were extracted only from the retained vendor_boot with
SHA-256 `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`
and checked against the retained module inventory.

| Module | Bytes | SHA-256 | Versioned imports |
| --- | ---: | --- | ---: |
| Stock `pmic_class.ko` | 14408 | `9fd0b4fd098ed0d5e8110c7e12966d5ce4844be313345088d9dfa533588a10e5` | 7 |
| Stock `s2dos05-regulator.ko` | 79256 | `e7a194604a55b6c4ef5843a57d6d27e4613281b6e9f45dbca144b63a5abb5381` | 61 |
| Stock `i2c-gpio.ko` (comparison only) | 18200 | `3fdf0bf9d3b9cd0f1e12f90e6a7a1a9d1f32b2bfe04b6f3de75b5e06baf86859` | 23 |
| Restricted `i2c-gpio.ko` (debug-bearing H0 build) | 279984 | `591962b082222ced903e7d8901bda637ff3a3c0dc3e156a89ee9c6253349f82a` | 23 |

S2DOS05 imports the Image plus `pmic_class`, `sec_class`, `debug-regulator` and
`abc`; the last three are already in the existing plan. The proposed order is:
existing providers, then `pmic_class`, then S2DOS05 driver registration, then the
restricted display bus (which can instantiate/probe its PMIC), then display
additions ending with `msm_drm`. Actual regulator and DRM readiness must be
observed; completed insertion alone is insufficient.

## GPIO bus scope and restriction

All eleven retained DTBO entries contain the same enabled GPIO-I2C bus scope:

| Root bus | Firmware children |
| --- | --- |
| `/i2c@50` | S2DOS05 display PMIC |
| `/i2c@51` | S2MPB02 PMIC |
| `/i2c@52` | P9320, S2MIW04 and SB-MFC charging devices |
| `/i2c@55` | ISG6320 sensor |

Generic matching would request/configure each bus's pins and register each
adapter. Other client-driver binding is a separate effect from bus creation;
this assessment does not claim those other client drivers are loaded.

The display bus uses DT GPIO cells for pins 20/21, no `reg`, and an overlay root
target `/`; these conditions are uniform across the eleven entries. The exact
kernel names this root platform device `i2c@50`. Its platform matcher can use an
exact ID table after absent OF/ACPI tables. Matching happens before driver-core
`pinctrl_bind_pins`; a filter inside the probe callback would be too late.

[Patch and reproduction inputs](../../workspace/public/src/kernel-modules/s22plus_display_i2c_h0/README.md)
remove the generic OF match/table and broad alias, and add only the exact
`i2c@50` platform ID plus sentinel. The GPIO/probe/adapter code is unchanged.
The fixed native environment must not set `driver_override`; the kernel's
explicit override path can bypass ordinary matching. This is a named-environment
constraint, not a general defense against arbitrary privileged device writes.

## S2DOS05 initialization effects

`pmic_class` creates the kernel class before dependent device creation. The
S2DOS05 driver registers seven regulator descriptors; the DT marks three rails
boot-on. Regulator-core constraints may therefore invoke voltage/enable
operations. GPIO-I2C probe requests open-drain/output-high GPIOs, registers the
adapter and lets I2C core enumerate the display PMIC child.

The inspected S2DOS05 source and actual probe disassembly include these actions:

- Register regulators and their existing debug interfaces.
- Read device identification at register `0x61` (`DEVICE_ID_PGM`). The inspected
  initialization uses a read here, not a programming command.
- Update UVLO/FD control at `0x0f` and interrupt masks at `0x0d`; request the DT
  interrupt and wake handling. The display PMIC interrupt is GPIO 62.
- Create PMIC/sec-class interfaces. Raw register read/write sysfs handlers exist
  in this stock binary; the fixed renderer/readiness path must not access them.

All eleven DT definitions have `adc_mode=0` and no `ocl_elvss` property. Thus the
inspected optional powermeter-init and OCL-programming branches are excluded by
those inputs. This does not remove their code or authorize arbitrary property
changes. No direct partition/file/OTP writer was identified in the inspected
init/import path. This is not a universal claim about hardware register
volatility, every diagnostic callback or all transitive kernel effects.

## Validation and remaining qualification

- Hash-verified three extracted modules and exact Image; checked stock and
  restricted proposed unions (85 modules, 91 new-provider imports, zero errors).
- Built the restricted module using the repository Android clang r416183b,
  Full-LTO, CFI and MODVERSIONS. Original source, prepared configuration and
  Module.symvers remained byte-identical. `file` reports AArch64 ELF.
- Inspected ELF/DWARF: OF/ACPI pointers are zero with no relocations; the platform
  ID pointer relocates to only `i2c@50` and its empty sentinel. The sole alias is
  `platform:i2c@50`.
- Exact kernel match-function bodies accepted the intended name and rejected
  seven other names. The fixture separately demonstrates the override caveat;
  it does not pretend to load the kernel module. Host and AArch64 builds passed.
- Zero-fuzz patch roundtrip reproduced the expected after hash. Python helper
  compilation, document links, diff and repository-boundary checks passed.
- Independent review confirmed the implemented scope restriction and bounded
  effect assessment. Reviewed source SHA-256 is
  `afecb14e03dcf5a222ddebd3ea1a3b078f596739aae4522ea8a3973a9e18e607`;
  the reviewed module identity is in the table above.

Next H0 work is to integrate the exact provider order, bounded probe/regulator/
DRM readiness observation and the white high-visibility renderer in a fresh
successor. Its complete packaging, execution prerequisites, failure evidence
and review remain separate. No live provider, display, or recovery qualification
is claimed here and no ready manifest or approval was created.

Private evidence is under `workspace/private/outputs/s22-display-provider-h0/`:
extraction, stock/scoped linkage, DT scope, match fixture, source patch, build
recipe/log, binary-field audit and probe disassembly. P350 and other-target
artifacts were not altered. A90/S20+ received no command.
