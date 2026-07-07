# S22+ Native-Init M7 USB-Subset Host Build - 2026-07-07

## Verdict

PASS: host-only M7 USB-subset native-init candidate built and statically
validated.

No live flash was run. The built AP is not live-authorized; any M7 device test
requires a fresh SHA-pinned S22+ boot-only `AGENTS.md` exception and an attended
rollback path.

## Why M7

M6 replayed the whole `modules.load.recovery` list and then boot-looped. The
operator postmortem identified that as an over-correction: recovery order is
useful, but the whole 446-module list includes watchdog/reset-prone and
unrelated subsystem modules that a bare PID1 cannot service.

M7 keeps the M6 freestanding/configfs/`a600000.dwc3` design, but changes the
module input:

- derive the USB bring-up dependency closure from stock `modules.dep`;
- order that closure by stock `modules.load.recovery`;
- exclude watchdog/reset-prone modules and unrelated non-USB classes;
- inject only a small text list into boot ramdisk;
- still load all `.ko` binaries from stock vendor_boot `/lib/modules`.

## Added

```text
workspace/public/src/native-init/s22plus_init_usb_acm_m7_usb_subset.c
workspace/public/src/scripts/revalidation/build_s22plus_inplace_m7_usb_subset.py
```

Generated private package:

```text
workspace/private/outputs/s22plus_native_init/inplace_m7_usb_subset_v0_1/odin4/AP.tar.md5
```

## Candidate Hashes

```text
AP.tar.md5             be0e1e34ec9452a14b7cfac66cc7ac57a0b29e92343945c35c1f836282563c4d
boot.img               7e58de4cfbf50eabef73f62ed1c30a1b4bc83089307cca083c304b9a9b360206
M7 /init               530ff86247270c5a48db22f009e5f659d4403643a90486842938200c8192514d
M7 subset list         b630d318d1a95f596cbd97699d04d2bf60a53e634f35c00bbabc8000fb3315b7
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
vendor_ramdisk00       41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193
```

The Odin AP contains exactly one member:

```text
boot.img.lz4
```

## Module Subset Gate

```text
modules.load.recovery count      446
modules.dep count                441
required USB roots                20
dependency closure                54
M7 subset count                   53
M7 subset bytes                  802
runtime subset buffer           8192
module binaries injected           0
module list files injected         1
```

The only closure member removed by the non-USB blocklist was:

```text
qc_usb_audio.ko
```

Watchdog blocklist:

```text
gh_virt_wdt.ko
qcom_wdt_core.ko
qcom_soc_wdt.ko
sec_qc_qcom_wdt_core.ko
```

No watchdog module survived into the M7 subset. The final subset begins with:

```text
abc.ko
clk-rpmh.ko
gcc-waipio.ko
icc-rpmh.ko
qcom_ipc_logging.ko
rpmh-regulator.ko
clk-dummy.ko
clk-qcom.ko
cmd-db.ko
debug-regulator.ko
```

Critical USB entries are present in recovery order:

```text
dwc3-msm.ko             recovery position 262
usb_f_ss_acm.ko         recovery position 273
ucsi_glink.ko           recovery position 274
usb_typec_manager.ko    recovery position 379
mfd_max77705.ko         recovery position 401
pdic_max77705.ko        recovery position 405
```

## Build Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m7_usb_subset.py

aarch64-linux-gnu-gcc -nostdlib -static -ffreestanding -fno-builtin \
  -fno-stack-protector -Os -Wall -Wextra -Werror -Wl,-e,_start \
  -o /tmp/s22plus_m7_usb_subset_check \
  workspace/public/src/native-init/s22plus_init_usb_acm_m7_usb_subset.c

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m7_usb_subset.py --force
```

Static result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked
No INTERP/program interpreter
M7 binary contains /s22plus_m7_usb_subset.modules
M7 binary does not contain modules.load.recovery
```

MagiskBoot gates:

```text
no-change repack byte-identical  true
construction                     magiskboot unpack/repack
mkbootimg_from_scratch           false
replaced ramdisk entry            init
added ramdisk entry               s22plus_m7_usb_subset.modules
kernel hash unchanged            true
SAMSUNG_SEANDROID/VBMETA          preserved
```

Odin invalid-device parse gate:

```text
Check file : .../inplace_m7_usb_subset_v0_1/odin4/AP.tar.md5
/dev/bus/usb/999/999
No such file or directory
usb device Fail
```

## Next

M7 is ready only as a host-built candidate. Before live use, add a fresh
SHA-pinned S22+ boot-only exception for the exact AP/boot/init/subset hashes
above, then add a guarded M7 live helper/dry-run. The expected live discriminator
is park-vs-loop first, then ACM presence if it parks.
