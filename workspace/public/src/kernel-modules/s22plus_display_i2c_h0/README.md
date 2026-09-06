# S22+ display-only GPIO I2C module — H0

This patch narrows the retained FYG8 `i2c-gpio.c` platform match to `i2c@50`.
It is not in consumed P350 or an approved flashable successor.

The stock OF match would bind four root buses. Filtering inside `probe` is too
late to prevent driver-core pinctrl effects. The patch removes the OF table and
broad module alias, and uses one exact platform-ID entry plus its sentinel.
The existing GPIO, adapter, child-enumeration and removal code is unchanged.
No DT, kernel policy, driver override or sysfs mutation is introduced.

In the inspected kernel, root `/i2c@50` has no `reg`, so its platform name is
`i2c@50`. This naming/DT condition and absence of driver overrides are required
for this design. It does not generalize to other roots, boards or arbitrary
bus names. No ACPI/OF table may be restored alongside this ID restriction.

Apply with zero fuzz to a private copy matching `source-identities.json`, then
verify the after hash. Build only that external module against the retained
vendor module preparation and exact Image-compatible symbol table, using the
repository Android clang r416183b toolchain, Full-LTO, CFI and MODVERSIONS.
`obj-m += i2c-gpio.o` is the complete external Makefile. Do not change the fixed
Image or reuse the broad stock module as the restricted result.

The H0 build produced a debug-bearing 279,984-byte AArch64 ELF with SHA-256
`591962b082222ced903e7d8901bda637ff3a3c0dc3e156a89ee9c6253349f82a`.
Its sole alias is `platform:i2c@50`. ELF/DWARF inspection confirmed null OF/ACPI
pointers and an ID-table relocation to only `i2c@50` plus the empty sentinel.
The original source, prepared config and symbol table remained unchanged.

Exact kernel matching-function fixtures accepted the intended name and rejected
seven other names. They also confirm that a caller-set driver override can
bypass ordinary matching; the fixed native environment must not set one.
These checks and symbol/CRC compatibility are H0 evidence, not live probe,
GPIO behavior, regulator health, display output or recovery qualification.

Private build recipe, scope enumeration, binary audit and module evidence:
`workspace/private/outputs/s22-display-provider-h0/`.
