# S22+ Native-Init M8A Minimal-FS Download Host Build - 2026-07-07

## Verdict

M8A host-only build passed. No device flash was run.

M8A is the first split after the M8 live bootloop. It removes every module,
configfs, and USB gadget variable from M8: direct PID1 mounts only
`/dev`, `/proc`, `/sys`, and `/run`, emits a kmsg marker, sleeps 250 ms, then
requests Samsung `reboot(..., "download")`.

Any live use still requires a fresh SHA-pinned S22+ boot-only `AGENTS.md`
exception and a guarded live helper for these exact hashes.

## Candidate

```text
source                 workspace/public/src/native-init/s22plus_init_m8a_minfs_download.c
builder                workspace/public/src/scripts/revalidation/build_s22plus_inplace_m8a_minfs_download.py
output                 workspace/private/outputs/s22plus_native_init/inplace_m8a_minfs_download_v0_1
AP.tar.md5             c97d29e38fe3293ad145a7743b61ae5fddae8f1b028e619dcd56e2f640de3c19
boot.img               8a816fb3bf8e644de4bbe0409f6cf94fd06a33d16e672569c130535ce139ad44
M8A /init              aac2a03a2b20e72c3d69cfa3c4d3e5c045c817c293c347ac2aaf81f1bfb029b1
source                 830f95cc0f4237f10f2e132ead873a69f543134a503816fa2281205d41362538
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
runtime                freestanding-raw-syscall
```

The AP contains exactly one Odin member:

```text
boot.img.lz4
```

## Static Gates

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m8a_minfs_download.py
aarch64-linux-gnu-gcc -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -Os -Wall -Wextra -Werror -Wl,-e,_start ...
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m8a_minfs_download.py --force
jq manifest safety gate
strings required/forbidden string gate
tar member + sha256 verification
```

Manifest gate result:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
module_insertions=false
module_binary_injection=false
configfs_runtime_gadget=false
module_files_injected_into_boot_ramdisk=0
module_list_files_injected_into_boot_ramdisk=0
nochange_repack_boot == base_boot
tar_members=["boot.img.lz4"]
```

Required strings present in M8A `/init`:

```text
S22_NATIVE_INIT_M8A_MINFS_DOWNLOAD
version=0.1
runtime=freestanding
raw_syscalls=1
minfs=dev,proc,sys,run
no_modules=1
no_configfs=1
no_usb_acm=1
no_gadget_setup=1
auto_reboot_download_after_minfs=1
phase=timed_download
download
```

Forbidden strings absent from M8A `/init`:

```text
ld-linux
libc.so
/lib/modules
finit_module
modules.load
s22plus_m8_delta_batch
ttyGS0
ss_acm.0
usb_gadget
/config
```

## Interpretation

M8 failed before its timed download request and left no retained M8 marker.
M8A is the sharper next discriminator:

```text
M8A returns to download mode:
  Direct PID1 + minimal virtual fs + kmsg/reboot path works.
  The M8 failure is likely in module-list parsing/opening or one of the first
  18 module insertions.

M8A does not return to download mode:
  The failure is before or during minimal freestanding PID1/fs/reboot path.
  Do not spend more time splitting the M8 module batch until that lower layer is understood.
```

No live flash is authorized by this report.
