# S22+ Native-Init M8 Timed-Download Bisect Host Build - 2026-07-07

## Verdict

PASS: host-only M8 timed-download module-bisect candidate built and statically
validated.

No live flash was run. The built AP is not live-authorized. Any M8 device test
still needs a fresh SHA-pinned boot-only `AGENTS.md` exception plus a guarded
live helper/dry-run and attended rollback path.

## Why M8

M7 did not expose ACM/ADB and boot-looped even after removing the explicit
watchdog modules. The next useful discriminator is therefore not another ACM
milestone attempt. M8 narrows the question to:

```text
Can native PID1 survive the first half of the M7-only module delta and request
Samsung download mode by itself?
```

This avoids depending on configfs, UDC binding, ttyGS0, or host serial I/O.

## Built Artifact

```text
source        workspace/public/src/native-init/s22plus_init_m8_timed_download_bisect.c
builder       workspace/public/src/scripts/revalidation/build_s22plus_inplace_m8_timed_download_bisect.py
manifest      workspace/private/outputs/s22plus_native_init/inplace_m8_timed_download_bisect_v0_1/manifest.json
AP            workspace/private/outputs/s22plus_native_init/inplace_m8_timed_download_bisect_v0_1/odin4/AP.tar.md5
```

Hashes:

```text
AP.tar.md5             59433518e7bea2d16f5efb62ee226c190f6a3af8673336310a2ef0fff7bee36b
boot.img               3c10c9232b8579b552d791d24e65b7b4dd8ec3625941766894a08725a7abae52
M8 /init               5c8591023d0ad801155535e9b535993fb3122c4d3e4c86139d36a819ee72c3b2
M8 delta batch         6831a24ac12ddf0bfdb9b5695dcd3aada7f200aa4a998864874c207efa31bc9d
base boot              2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
vendor ramdisk         41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193
```

The AP contains exactly one Odin member:

```text
boot.img.lz4
```

## Runtime Behavior

M8 `/init` is freestanding raw-syscall PID1:

```text
S22_NATIVE_INIT_M8_TIMED_DOWNLOAD version=0.1
runtime=freestanding raw_syscalls=1
module_batch=/s22plus_m8_delta_batch.modules
module_source=stock_vendor_boot_ramdisk
module_injection=list_only
batch_strategy=m7_only_first_half
expected_module_count=18
no_usb_acm=1 no_configfs=1
auto_reboot_download_after_batch=1
no_android_handoff=1
```

Runtime sequence:

1. Mount minimal `/proc`, `/sys`, `/dev`, and `/run`.
2. Emit `S22_NATIVE_INIT_M8_TIMED_DOWNLOAD` kmsg markers.
3. Read `/s22plus_m8_delta_batch.modules`.
4. Attempt `finit_module()` on each listed module from stock `/lib/modules`.
5. If exactly 18 module names were parsed, sleep 250 ms and call
   `reboot(..., "download")`.
6. If the list count is wrong, park instead of auto-download.

## Batch

M8 compares M5 and M7 by module name:

```text
M5 module count                 26
M7 subset count                 53
M7-only delta count             36
M7 overlap with M5              17
M5-only not in M7                9
M8 batch count                  18
M8 batch bytes                 255
```

M8 loads the first half of the M7-only delta in M7 recovery order:

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
gdsc-regulator.ko
icc-bcm-voter.ko
icc-debug.ko
minidump.ko
phy-generic.ko
proxy-consumer.ko
qcom_rpmh.ko
qcom-scm.ko
```

The inherited watchdog blocklist remains absent from the batch:

```text
gh_virt_wdt.ko
qcom_soc_wdt.ko
qcom_wdt_core.ko
sec_qc_qcom_wdt_core.ko
```

## Static Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m8_timed_download_bisect.py

aarch64-linux-gnu-gcc -nostdlib -static -ffreestanding -fno-builtin \
  -fno-stack-protector -Os -Wall -Wextra -Werror -Wl,-e,_start \
  -o /tmp/s22plus_m8_compile/s22plus_init_m8_timed_download \
  workspace/public/src/native-init/s22plus_init_m8_timed_download_bisect.c

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m8_timed_download_bisect.py --force
```

Checks:

```text
ELF type                  EXEC
machine                   AArch64
program interpreter       absent
nochange repack           byte-identical to base boot
boot size                 100663296
AP tar members            boot.img.lz4 only
ramdisk replaced entry    init mode 750
ramdisk added entry       s22plus_m8_delta_batch.modules mode 640
module binaries in boot   0
module list files in boot 1
live flash authorized     false
```

Actual M8 binary string scan contains the expected M8/download/module-batch
markers and no `ttyGS0`, `ss_acm`, `usb_gadget`, or `/config` runtime strings.

Manifest gate passed:

```text
live_flash_authorized=false
boot_only=true
module_binary_injection=false
module_files_injected_into_boot_ramdisk=0
module_list_files_injected_into_boot_ramdisk=1
batch_count=18
m7_only_count=36
tar_members=["boot.img.lz4"]
nochange_repack_boot == base_boot
```

## Interpretation

M8 is a safer next live discriminator than repeating M7:

- If a future M8 live run auto-returns to Odin/download mode, PID1 survived
  the first 18 M7-only modules; the culprit is later in the M7-only delta,
  overlap modules, or the USB/configfs path.
- If M8 boot-loops or fails to self-download, the culprit is in or before this
  first 18-module batch.

## Next

Do not flash M8 from this host-build commit. Next bounded unit, if supervised
testing is desired, is a fresh M8 live-gate preflight:

1. Add a SHA-pinned S22+ boot-only exception for the exact M8 AP/boot/init/list
   hashes above.
2. Add a guarded live helper that observes for automatic Odin/download return,
   not ACM.
3. Default to dry-run; require an explicit live ack before any Odin flash.
4. Keep Magisk boot-only rollback as the first rollback path.
