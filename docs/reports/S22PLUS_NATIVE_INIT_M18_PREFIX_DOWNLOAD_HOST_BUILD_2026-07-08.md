# S22+ Native-Init M18 Prefix-Download Host Build - 2026-07-08

## Verdict

PASS: M18 prefix-download discriminator artifacts were built host-only.

No device action, reboot, Odin live transfer, partition write, recovery action,
Magisk action, or connected-device mutation was performed.

M18 is the fallback observation-channel plan from the M17 postmortem. It does
not attempt ACM. It loads a monotonic prefix of the M17 power-QMP module list,
then requests download mode if execution reaches the checkpoint. This turns the
next live signal from "loop vs park" into "did the candidate reach prefix N?"

## Files

Source:

```text
workspace/public/src/native-init/s22plus_init_m18_prefix_download.c
```

Builder:

```text
workspace/public/src/scripts/revalidation/build_s22plus_inplace_m18_prefix_download.py
```

Private output:

```text
workspace/private/outputs/s22plus_native_init/inplace_m18_prefix_download_v0_1
```

## Built Matrix

```text
P00  prefix_count=0   AP.tar.md5 b79ac94aac341ab5e4c08cb3c568c20be28bb71ccd4f1b047f712bd1dcf5225b
P00  boot.img         f8f362bdd0d0f75ae9ae0ce69d86bcfe47362f246504b02fc6175a4aa0a83133
P00  /init            467947f7ba0c4b4088c9a21a19e5202609b833298f2e95256b1f011eb9af034e

P10  prefix_count=10  AP.tar.md5 ee46e5eef52d85f6bbfecbede8b7a2d374cce47140f900c2bbb57ce07beddca8
P10  boot.img         ddf72d5cc213008f67bb71d5382989fd94f32787cd85b736dfcc0b54630c0aa7
P10  /init            f600c98e019bb779b3f338bd9cfd7915793c8f3c94d39cc3faeaeef97aa33831
```

Shared hashes:

```text
base Magisk boot     2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
M18 module-list text 1e00da43ae2b22c56855a28967201733b66b65ec4e91086faa67a4d9b3177fb8
```

Each AP contains exactly:

```text
boot.img.lz4
```

## Prefix Content

P00 loads no modules. It proves whether the M18 minimal-fs plus checkpoint
download path is usable at all.

P10 loads the first ten M17 modules:

```text
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
```

The next module after P10 is:

```text
icc-bcm-voter.ko
```

## Safety Shape

Both artifacts are boot-only AP packages built from the known-booting Magisk
boot baseline.

Manifest gates for both:

```text
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
boot_only=true
construction=magiskboot unpack/repack; replace ramdisk /init and add one text module list
runtime=freestanding-raw-syscall
glibc_static_startup=false
mkbootimg_from_scratch=false
no_android_or_magisk_handoff=true
intended_reboot_syscall=true
reboot_request=download
persistent_partition_mount=false
block_device_writes=false
module_binary_injection=false
configfs_runtime_gadget=false
usb_role_force=false
acm=false
```

The boot ramdisk receives only:

```text
init
s22plus_m18_power_qmp.modules
```

No vendor module binaries are injected into the boot ramdisk.

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m18_prefix_download.py

aarch64-linux-gnu-gcc ... -DM18_PREFIX_LIMIT=0 -DM18_PREFIX_LABEL='"P00"' \
  workspace/public/src/native-init/s22plus_init_m18_prefix_download.c

aarch64-linux-gnu-gcc ... -DM18_PREFIX_LIMIT=10 -DM18_PREFIX_LABEL='"P10"' \
  workspace/public/src/native-init/s22plus_init_m18_prefix_download.c

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m18_prefix_download.py --force
```

Results:

```text
py_compile pass
P00 standalone cross-compile pass; reboot syscall immediate present
P10 standalone cross-compile pass; reboot and finit_module syscall immediates present
builder --force pass
P00/P10 no-change MagiskBoot repack byte-identical to base
P00/P10 patched boot kernel unchanged
P00/P10 AP tar members = boot.img.lz4 only
P00/P10 ramdisk replaced /init mode 750
P00/P10 ramdisk added module-list text mode 640
```

## Future Live Interpretation

No live flash is authorized by this report.

If a live run is later approved, run P00 first:

```text
P00 self-download appears:
  M18 checkpoint channel is viable after minimal fs setup.
  P10 can be considered as the next supervised live discriminator.

P00 does not self-download:
  the prefix-download channel is invalid at this runtime layer.
  Stop M18 and return to UART or raw-assembly checkpoint design.
```

Only after P00 passes should P10 be interpreted:

```text
P10 self-download appears:
  first ten M17 modules did not reset before checkpoint.
  next host-only build should add P16/P20.

P00 passed but P10 loops/no-download:
  first reset boundary is inside M17 module indices 1..10.
  next host-only build should split P05/P08/P10, not add later modules.
```

Keep all existing S22+ constraints: boot-only AP, no forbidden partitions, no
raw host partition writes, no fastboot, attended ack for any live flash, and
pinned Magisk boot-only rollback.
