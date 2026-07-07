# S22+ Native-Init M10A4 Inline Probe Reboot Host Build - 2026-07-07

## Verdict

M10A4 host-only build passed. No device flash was run.

M10A4 is the split after the operator-corrected M10A3 live result. M10A3
bootlooped and required operator manual download-mode rollback even after the
pre-reboot `getpid()` syscall was removed. M10A4 removes the separate
no-syscall probe helper call/return before reboot, but keeps a small inline
stack probe in `_start`, then branches once to the reboot helper. The only
syscall in the stripped `/init` is `reboot(2)`.

This tests whether M10A3 failed because of the separate pre-reboot helper
call/return boundary, or because any extra stack/instruction work before the
Samsung download reboot request is enough to lose self-download.

## Artifacts

```text
source                 workspace/public/src/native-init/s22plus_init_m10a4_inline_probe_reboot.c
builder                workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a4_inline_probe_reboot.py
output                 workspace/private/outputs/s22plus_native_init/inplace_m10a4_inline_probe_reboot_v0_1
AP.tar.md5             a4d7c9d05536d22c3f56bd1891a7fbc0c8fa6d3500cf8b1036e11bd0c9569c26
boot.img               38986a19454d7fd49e8860d025ad4241e2c130b5fc28956bed892c26842fb3a9
M10A4 /init            d70c794979bc16f12917871f5e6e7b2231569f72682a5f6ebcd87f901a11837b
source                 2d168c28dbdef67bedc7d9d39250c7e61c928daf89a2b973616534453a835a84
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
original Magisk /init  383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468
```

AP tar contents:

```text
boot.img.lz4
```

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a4_inline_probe_reboot.py
aarch64-linux-gnu-gcc -fsyntax-only -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -Os -Wall -Wextra -Werror workspace/public/src/native-init/s22plus_init_m10a4_inline_probe_reboot.c
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a4_inline_probe_reboot.py --force
tar -tf workspace/private/outputs/s22plus_native_init/inplace_m10a4_inline_probe_reboot_v0_1/odin4/AP.tar.md5
strings -a workspace/private/outputs/s22plus_native_init/inplace_m10a4_inline_probe_reboot_v0_1/build/s22plus_init_m10a4_inline_probe_reboot
aarch64-linux-gnu-objdump -d workspace/private/outputs/s22plus_native_init/inplace_m10a4_inline_probe_reboot_v0_1/build/s22plus_init_m10a4_inline_probe_reboot
```

Static validation confirmed:

```text
ELF                    AArch64 static executable
program interpreter    absent
svc count              1
syscall numbers        __NR_reboot=142 only
getpid syscall         absent
branch shape           inline _start probe, then one branch to reboot helper
branch target          0x40010c
reboot helper start    0x40010c
required string        download
AP members             ["boot.img.lz4"]
no-change repack       byte-identical to base Magisk boot
patched kernel         preserved
```

Printable strings in the stripped `/init`:

```text
download
```

Forbidden strings verified absent from the stripped `/init`:

```text
ld-linux
libc.so
S22_NATIVE_INIT
/dev
/proc
/sys
/run
/lib/modules
getpid
newfstatat
mkdir
mknod
mount
finit_module
modules.load
ttyGS0
ss_acm.0
usb_gadget
/config
```

Manifest safety flags:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
runtime=freestanding-c-raw-syscall
pre_reboot_work=inline-stack-probe-no-syscall
separate_pre_reboot_probe_helper_call=false
first_runtime_side_effect=none-before-reboot
first_externally_observable_action=inline-probe-then-reboot-download
intended_syscalls=["reboot"]
intended_syscall_count=1
vfs_setup=none
pathname_access=false
getpid=false
mkdirat=false
mknodat=false
mounts=false
kmsg_write=false
marker_write=false
sleep_before_reboot=false
module_insertions=false
configfs_runtime_gadget=false
udc_binding=false
usb_role_force=false
block_device_writes=false
```

## Interpretation

M10A4 changes exactly one meaningful runtime factor from M10A3: it removes the
separate no-syscall pre-reboot probe helper call/return, while preserving small
stack work before the reboot request. Future live interpretation:

```text
M10A4 reaches download without manual entry:
  inline stack work is survivable.
  M10A3 points at the separate helper call/return boundary.

M10A4 bootloops / requires manual download:
  any pre-reboot stack work or instruction delay before the reboot helper is suspect.
  compare against an even narrower first-action reboot shape before adding filesystem work.
```

## Live Status

No live flash is authorized by this host-build unit. The next unit, if selected,
must add a fresh SHA-pinned `AGENTS.md` exception and a guarded live helper
preflight before flashing this candidate.
