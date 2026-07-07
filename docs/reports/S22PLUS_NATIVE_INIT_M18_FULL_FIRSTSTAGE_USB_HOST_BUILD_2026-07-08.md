# S22+ Native-Init M18 Full First-Stage USB Host Build (2026-07-08)

## Verdict

PASS, host-only build.

Codex implemented the latest operator steer from
`docs/reports/S22PLUS_NATIVE_INIT_M18_FULL_FIRSTSTAGE_SUBSTRATE_STEER_2026-07-08.md`:
load the vendor first-stage module substrate first, exclude only reset/anomaly
modules, append the USB/Type-C tail, bind only `a600000.dwc3`, force USB role
`device`, and park.

This commit does not authorize or claim a live flash. The produced AP remains a
private artifact and the manifest records `live_flash_authorized=false`. A later
operator observation reported bootloop behavior; without a Codex-captured flash
transcript in this unit, treat that as an operator observation, not a tool-verified
live result. If the observation corresponds to the SHA-pinned M18 AP below, the
M18 decision gate resolves to: stop blind module permutations and move to UART
or an equivalent non-persistent kernel console capture.

## Public Sources

- Native init:
  `workspace/public/src/native-init/s22plus_init_usb_acm_m18_full_firststage_park.c`
- Builder:
  `workspace/public/src/scripts/revalidation/build_s22plus_inplace_m18_full_firststage_usb_park.py`

## Private Artifact

- Output directory:
  `workspace/private/outputs/s22plus_native_init/inplace_m18_full_firststage_usb_v0_1`
- Odin AP member set: `boot.img.lz4` only.
- Boot ramdisk changes:
  - replaced `/init`, mode `750`
  - added `/s22plus_m18_full_firststage_usb.modules`, mode `640`
  - injected zero module binaries into boot ramdisk

## Artifact Hashes

| Artifact | SHA256 |
| --- | --- |
| `AP.tar.md5` | `9382f91bf2cd3235410368ca08208b9343d8584da48c29b25c46a931b1f42805` |
| `boot.img` | `a99a09fa062d1aaa848a41037c649a43abc983f177714dfc24c39d0df4d84083` |
| `/init` | `e73f39f7cc6f3a70e62ab2837b9e2d23422e2b6a5747e94f77bafcf0443baa40` |
| module list | `153921f2cd886e31a5989ba589f6e5058fda4cc8eb6eb196e843293f8fae8e78` |
| base Magisk boot | `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e` |
| kernel | `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff` |
| vendor ramdisk | `41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193` |

## Module Derivation

The candidate derives a 141-line runtime module list:

- vendor `modules.load`: 140 entries
- unique first-stage entries after reset/anomaly blocklist: 129
- appended USB tail: 12 entries
- final list: 141 entries, 2284 bytes

Excluded reset/anomaly modules:

- `abc.ko`
- `gh_virt_wdt.ko`
- `minidump.ko`
- `qcom_wdt_core.ko`
- `sec_debug.ko`
- `sec_debug_region.ko`

USB tail:

- `phy-msm-snps-hs.ko`
- `phy-msm-snps-eusb2.ko`
- `phy-msm-ssusb-qmp.ko`
- `dwc3-msm.ko`
- `usb_f_ss_acm.ko`
- `i2c-msm-geni.ko`
- `mfd_max77705.ko`
- `pdic_max77705.ko`
- `usb_typec_manager.ko`
- `if_cb_manager.ko`
- `pdic_notifier_module.ko`
- `vbus_notifier.ko`

## Caveat

The builder intentionally implements the operator-directed 141-module shape,
not a fully dependency-closed USB tail. The manifest preserves non-reset missing
tail dependencies as an interpretation caveat. If a SHA-pinned live attempt parks
but exposes no ACM, the missing non-reset tail dependencies remain a concrete
follow-up hypothesis. If the SHA-pinned attempt bootloops, this caveat does not
justify more blind permutations; the M18 steer already defines UART as the next
instrument.

## Safety Manifest

- `host_only_build=true`
- `live_flash_authorized=false`
- `boot_only=true`
- `block_device_writes=false`
- `auto_reboot=false`
- `host_commanded_reboot_download=false`
- `reboot_syscall=false`
- `module_binary_injection=false`
- `persistent_partition_mount=false`
- `configfs_runtime_gadget=ss_acm.0 only`
- `udc_binding=a600000.dwc3 only; never dummy_udc.0`

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m18_full_firststage_usb_park.py \
  --force

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m18_full_firststage_usb_park.py

aarch64-linux-gnu-gcc -nostdlib -static -ffreestanding -fno-builtin \
  -fno-stack-protector -Os -Wall -Wextra -Werror -Wl,-e,_start \
  -o /tmp/s22_m18_full_test \
  workspace/public/src/native-init/s22plus_init_usb_acm_m18_full_firststage_park.c

tar -tf \
  workspace/private/outputs/s22plus_native_init/inplace_m18_full_firststage_usb_v0_1/odin4/AP.tar.md5

wc -l \
  workspace/private/outputs/s22plus_native_init/inplace_m18_full_firststage_usb_v0_1/build/s22plus_m18_full_firststage_usb.modules
```

Results:

- builder completed successfully
- Python bytecode compile passed
- freestanding static AArch64 compile passed
- `/init` contains `svc` and `finit_module` syscall usage
- builder rejected arm64 reboot syscall presence
- AP tar contains exactly `boot.img.lz4`
- module list has 141 lines
- manifest preserves `live_flash_authorized=false`

## Next

Do not continue with the earlier M18 prefix-download/P00 path as the current live
target; it is superseded by this later full-first-stage steer.

The next safe unit depends on what was live-tested:

- If the operator bootloop observation corresponds to the SHA-pinned M18 AP in
  this report, stop blind module permutations and move to UART/kernel-console
  capture.
- If it does not correspond to this SHA-pinned AP, the only permissible live step
  is a fresh SHA-pinned live-gate preflight and attended flash/rollback flow.
