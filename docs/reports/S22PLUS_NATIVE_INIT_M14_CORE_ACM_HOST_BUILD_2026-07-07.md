# S22+ Native-Init M14 Core-ACM Host Build - 2026-07-07

## Verdict

M14 host-only build passed.

This candidate starts from the stable M13 no-module/no-transport floor and
reintroduces only four M12 core USB/ACM modules. It keeps the M13
freestanding PID1, minimal mounts, configfs `ss_acm.0` gadget attempt,
USB role-force attempt, `a600000.dwc3`-only bind policy, no Android/Magisk
handoff, no auto reboot, and no reboot beacon.

No live flash was executed. M14 is not live-authorized until a fresh
SHA-pinned `AGENTS.md` boot-only exception and guarded live helper are added.

## Candidate

Output directory:

```text
workspace/private/outputs/s22plus_native_init/inplace_m14_core_acm_v0_1
```

Hashes:

```text
AP.tar.md5             080fedea35c111020f68b5fb64eb260402dbc45ac4398e282523c94bf9a8922b
boot.img               dee741af20fb3dbcd347c2fa4d45099018f54f577ddf7ae64ac3dca4a357c2e4
M14 /init              0a144b2ddde32d78b4dfe051e009f5275f2e67c8276b0fa2d1a61e3280b7eed4
M14 module list        5b52cd5c1ae26d0bf24e7654b27f254ee478673c9313afdb955a0ec4fcf35f7c
source                 8acc0bfff03ec3adbde160a7ad6975be4154c8a219e8e59ebe1a6d8b1a19b8a7
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The AP contains exactly one member:

```text
boot.img.lz4
```

## Module Add-Back

M14 injects one boot-ramdisk text list and no module binaries. Runtime module
binaries are still read from stock vendor_boot `/lib/modules`.

Injected list:

```text
phy-msm-ssusb-qmp.ko
phy-msm-snps-eusb2.ko
dwc3-msm.ko
usb_f_ss_acm.ko
```

Recovery-order positions:

```text
phy-msm-ssusb-qmp.ko   259
phy-msm-snps-eusb2.ko  261
dwc3-msm.ko            262
usb_f_ss_acm.ko        273
```

M14 deliberately withholds the remaining 20 M12 floor modules. This keeps the
next live result interpretable:

```text
M14 loops        => fault is inside the core USB/ACM add-back or finit path
M14 parks/no ACM => core group is tolerated; next add role/PD chain
M14 exposes ACM  => control channel milestone reached
```

## Static Validation

Builder:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m14_core_acm_park.py --force
```

Additional checks passed:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m14_core_acm_park.py
jq manifest safety gate == true
tar member list == ["boot.img.lz4"]
file(M14 /init) == ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
no arm64 reboot syscall pattern for __NR_reboot=142
no forbidden strings: download, modules.load.recovery, s22plus-m5, /vendor_dlkm, ld-linux, libc.so
required M14 strings present, including module_group=core_acm and module_count=4
```

Manifest safety summary:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
reboot_syscall=false
host_commanded_reboot_download=false
block_device_writes=false
module_binary_injection=false
module_files_injected_into_boot_ramdisk=0
module_list_files_injected_into_boot_ramdisk=1
module_subset_count=4
configfs_runtime_gadget=ss_acm.0 only
udc_binding=a600000.dwc3 only; never dummy_udc.0
```

## Interpretation

M13 proved the no-module configfs/role-force candidate was not boot-looping but
also did not expose ACM. M12 showed the full 24-module floor boot-looped. M14
is the first small add-back below M12: it tests only the UDC/ACM core path while
preserving the M13 configfs/role-force behavior.

This is intentionally not dependency-complete. It is a bounded fault-isolation
probe: `finit_module` failures are acceptable evidence, while boot loop versus
park remains the primary live branch.

## Next

Next bounded unit is M14 live-gate preflight only:

1. Add a SHA-pinned `AGENTS.md` boot-only/Odin exception for the exact M14 AP.
2. Add a guarded live helper with explicit live and rollback ack tokens.
3. Dry-run the helper against Android/Magisk baseline and the exact M14 hashes.
4. Only then consider an attended live flash.
