# S22+ Native-Init M10A3 Probe Reboot Host Build - 2026-07-07

## Verdict

M10A3 host-only build passed. No device flash was run.

M10A3 is the narrow split after the operator-corrected M10A2 result. M10A2
bootlooped and required manual download-mode rollback after a non-VFS
`getpid()` syscall before `reboot("download")`. M10A3 keeps the extra
pre-reboot helper call and stack-probe shape, but removes the pre-reboot
syscall. The only syscall left in the binary is `reboot(2)`.

This tests whether M10A2 failed because of the prior syscall itself, or because
the extra helper/timing/stack shape before the Samsung download reboot request
is already enough to lose self-download.

## Artifacts

```text
source                 workspace/public/src/native-init/s22plus_init_m10a3_probe_reboot.c
builder                workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a3_probe_reboot.py
output                 workspace/private/outputs/s22plus_native_init/inplace_m10a3_probe_reboot_v0_1
AP.tar.md5             7415538ac9cbfdf4af27f294927c3c81d2656412a7f779fce515138ec28e7e3b
boot.img               eb2d1cfc278e63cdfe009379f05139e5299b49859a2b247d4e6996be5f24959c
M10A3 /init            4c7908026430658250a0999fad2d47c7e5d99c212dc8daa3ba8fbafb0f4a8371
source                 9b5e3669a7a790a369bf8ed4beb662cb5262189e5d8f22011c731fc827955856
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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a3_probe_reboot.py
aarch64-linux-gnu-gcc -fsyntax-only -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -Os -Wall -Wextra -Werror workspace/public/src/native-init/s22plus_init_m10a3_probe_reboot.c
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a3_probe_reboot.py --force
tar -tf workspace/private/outputs/s22plus_native_init/inplace_m10a3_probe_reboot_v0_1/odin4/AP.tar.md5
strings -a workspace/private/outputs/s22plus_native_init/inplace_m10a3_probe_reboot_v0_1/build/s22plus_init_m10a3_probe_reboot
aarch64-linux-gnu-objdump -d workspace/private/outputs/s22plus_native_init/inplace_m10a3_probe_reboot_v0_1/build/s22plus_init_m10a3_probe_reboot
```

Static validation confirmed:

```text
ELF                    AArch64 static executable
program interpreter    absent
svc count              1
syscall numbers        __NR_reboot=142 only
getpid syscall         absent
branch order           pre-reboot probe helper, then reboot helper
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
pre_reboot_helper=stack-probe-no-syscall
first_runtime_side_effect=none-before-reboot
first_externally_observable_action=probe-helper-then-reboot-download
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

M10A3 changes exactly one meaningful runtime factor from M10A2: it removes the
pre-reboot `getpid()` syscall while preserving the extra helper call and
stack-probe shape. Future live interpretation:

```text
M10A3 reaches download without manual entry:
  the extra helper/stack shape is survivable.
  M10A2 points at the prior getpid syscall.

M10A3 bootloops / requires manual download:
  the extra helper/timing/stack shape is enough to lose self-download.
  compare directly against M9A instruction shape before adding any filesystem work.
```

## Live Status

No live flash is authorized by this host-build unit. The next unit, if selected,
must add a fresh SHA-pinned `AGENTS.md` exception and a guarded live helper
preflight before flashing this candidate.
