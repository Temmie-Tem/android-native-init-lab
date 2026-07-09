# S22+ M34 S10B Module-Load Prefix Ladder Host Build (2026-07-09)

## Verdict

M34 `S10B0`..`S10B6` host-build artifacts are ready. This is host-only: no
flash, no reboot, and no device write was performed by this unit.

S10B starts from the same S9/S10A 89-module recipe and splits S10A's all-core
`/proc/modules` predicate into prefix predicates. The purpose is to identify the
first missing module/load-failure boundary using the already-proven one-bit
download beacon.

Output:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_12/
```

No active live authorization exists. A future live run still needs a dedicated
fail-closed live helper or a checked extension of the S10A helper, a fresh
SHA-pinned `AGENTS.md` boot-only exception, default dry-run, rollback proof, and
explicit operator approval.

## Ladder

Each stage loads the same S9/S10A module list, then checks whether its prefix
modules are visible in `/proc/modules`. Predicate true requests
`reboot(download)`; predicate false parks and requires manual Download rollback.

```text
S10B0 stage=13 probe=proc_modules_prefix_1 modules=cmd_db
S10B1 stage=14 probe=proc_modules_prefix_2 modules=cmd_db,qcom_rpmh
S10B2 stage=15 probe=proc_modules_prefix_3 modules=cmd_db,qcom_rpmh,gcc_waipio
S10B3 stage=16 probe=proc_modules_prefix_5 modules=cmd_db,qcom_rpmh,gcc_waipio,pinctrl_waipio,qcom_pdc
S10B4 stage=17 probe=proc_modules_prefix_6 modules=cmd_db,qcom_rpmh,gcc_waipio,pinctrl_waipio,qcom_pdc,i2c_msm_geni
S10B5 stage=18 probe=proc_modules_prefix_7 modules=cmd_db,qcom_rpmh,gcc_waipio,pinctrl_waipio,qcom_pdc,i2c_msm_geni,mfd_max77705
S10B6 stage=19 probe=proc_modules_prefix_8 modules=cmd_db,qcom_rpmh,gcc_waipio,pinctrl_waipio,qcom_pdc,i2c_msm_geni,mfd_max77705,pdic_max77705
```

Interpretation for later live use:

```text
First MISS at S10B0: cmd_db never appears, or /proc/modules cannot be trusted in native-init.
S10B0 HIT then S10B1 MISS: qcom_rpmh boundary.
S10B1 HIT then S10B2 MISS: gcc_waipio boundary.
S10B2 HIT then S10B3 MISS: pinctrl_waipio/qcom_pdc boundary.
S10B3 HIT then S10B4 MISS: i2c_msm_geni boundary.
S10B4 HIT then S10B5 MISS: mfd_max77705 boundary.
S10B5 HIT then S10B6 MISS: pdic_max77705 boundary; this is consistent with S10A MISS.
S10B6 HIT: contradicts S10A live MISS and requires rechecking S10A/run conditions.
```

## Shared Inputs

```text
Base Magisk boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
No-change MagiskBoot repack SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
Template source SHA256: 6ac888ddf29e559a9a9b7522eda4edd54c5a38264782dddd2bd5c80d6d8e21a6
Module-list SHA256: c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26
```

S10A stayed byte-stable in v0.12:

```text
S10A AP.tar.md5 SHA256: 064cc0431e649eb78bc8c8d1d89fcd16d09426f898120edb3c31c375275e3182
S10A boot.img SHA256: a1ca7a4bf64ec8ecfc56d28d3f5e8511e6045bb1b2513fbafdb4249f75e15217
S10A /init SHA256: f8ad5df4ef3ff5db7229b3c7f55f2453bc8fe5a72260ca539534e9cddbbdc4e8
```

## Artifacts

```text
S10B0 AP.tar.md5 SHA256: c117d8789b4ed990afd047ef3a6bb8d32f0b7b5d76bdce58eecf8ae98725d47c
S10B0 boot.img SHA256: a30120d094d3484b6b4234e0a285f6c26e95120f032ed9ec3671fd287661b610
S10B0 /init SHA256: 50bd942c92d6aad3b143e1f215c0e7a313819994f5dbfa580c11666d32d5f761

S10B1 AP.tar.md5 SHA256: eae1397e027039f081f0a2bc4e24289493a813ed4c7cd8c764041d43c6049119
S10B1 boot.img SHA256: 81181ff9c09d639d94edd34bd0599f0ae28cb31a219ce32026492ef6e7c6c4ab
S10B1 /init SHA256: 49858e0a3d51da1724e2d1a4c2c9e52f75bde486d00d91ec020ef242980cd591

S10B2 AP.tar.md5 SHA256: ca9dec63b6e039a85d15a0c50720bc59ca6bbb69048e51ccb66a6fd20de62a84
S10B2 boot.img SHA256: 46bc97ee4176f96911045aabdfea17792f296df659126043fb0131e1540c46ae
S10B2 /init SHA256: 6724c4515ad6abd96831a799680c6672b8e684505d8535193e4bffca58583353

S10B3 AP.tar.md5 SHA256: cb0290e3d1c361ad5cf019a940f58095832a795417f6e54710425f37270af49a
S10B3 boot.img SHA256: 6e21f06edff3cd6e9c3ae8d52711fc37a22dc2e49af578af6b4a5ecb9c03a9ad
S10B3 /init SHA256: c01dbcbfda24ba6a2b657e908f6571f7d7da72a41d469dea5b52f8ba6cd4aaed

S10B4 AP.tar.md5 SHA256: 97a6fed0b09cabab746f6a1409659d7d6e12adc2385373d283e589a7eb5cc15f
S10B4 boot.img SHA256: 3684168e5d9ef5001443f20a654d10861d144e17edd601846db981cc89b1188f
S10B4 /init SHA256: 776627102e7a77a5a242cbc8070f3388cac0968b03b645c3717a7801249563d8

S10B5 AP.tar.md5 SHA256: 567643284f71b1e66f4827eddf5c827222990df31a779b42067a236157acdf09
S10B5 boot.img SHA256: 87fe40226923d95bc8361d0a4f9cac7943d2a6cdcaa1eed6972d0cacf52dc51e
S10B5 /init SHA256: c643be1d4072eedb4546ea3c34f6be13476a999bfbe69d77f875d5ef02952f33

S10B6 AP.tar.md5 SHA256: bd4b25f28a64b8f65f7f7cec3393a7679362412af9c02d2e3f1848e207610282
S10B6 boot.img SHA256: a346a9ab09e8b9f4cafe53bf5733ab44fa0c0b2f5e9b831bbbaaf653b37c8689
S10B6 /init SHA256: 0d7f00f431596a1bb4fc55378efa2f50a54a7708c6caf529702fa0d79a6a0460
```

Every AP contains exactly one tar member:

```text
boot.img.lz4
```

## Safety

S10B keeps the S10A isolation constraints:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
module_files_injected_into_boot_ramdisk=0
configfs_gadget=0
udc_bind=0
role_write_discriminator=0
typec_readback=0
driver_load_only=1
manual_power_write=0
persistent_partition_mount=false
block_device_writes=false
```

The candidates do not touch configfs, UDC, TypeC role nodes, ssusb role nodes,
EUD sysfs, charge/OTG/VBUS boost, regulators, GDSC, GPIO, display, persistent
partitions, or block devices. Predicate true performs only the already-used
`reboot(download)` beacon; predicate false parks.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py \
  --out workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_s10b_smoke \
  --stages S10B0 S10B6 --force

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py \
  --force

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_runtime_gadget_split_build.py
```

Result:

```text
py_compile: OK
S10B0/S10B6 smoke build: OK
Full v0.12 host build: OK
M34 runtime-gadget split tests: Ran 5, OK
```

## Next

The next live unit should start with `S10B0` only. A HIT proves `cmd_db` appears
in `/proc/modules` under native-init and advances to `S10B1`; a MISS localizes
the break to the first module or to `/proc/modules` observability itself.

No S10B live flash is authorized by this report.
