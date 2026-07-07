# S22+ Native-Init M10A Mkdir-Dev Reboot Host Build - 2026-07-07

## Verdict

M10A host-only build passed. No device flash was run.

M10A is the next side-effect discriminator after M9A's delayed automatic
download-mode return. It keeps the M9A freestanding C ELF/build shape and adds
exactly one M8A-style runtime side effect before reboot:
`mkdirat("/dev", 0755)`.

Any live use still requires a fresh SHA-pinned S22+ boot-only `AGENTS.md`
exception, guarded live helper with a longer self-download window, default
no-flash dry-run, and attended rollback plan for the exact hashes below.

## Candidate

```text
source                 workspace/public/src/native-init/s22plus_init_m10a_mkdir_dev_reboot.c
builder                workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a_mkdir_dev_reboot.py
output                 workspace/private/outputs/s22plus_native_init/inplace_m10a_mkdir_dev_reboot_v0_1
AP.tar.md5             d71c8c82d2703892802228dd61ded561a9b4f90c678db15452014f2477170105
boot.img               c62fce5e444bad47e2b934f6e9e82bc731058a0c9494629f0eb9044ff92e8b24
M10A /init             8f954dfcd5d5887f8c1659e7e658617561627d9c7fecc518972a795ac20422b3
source                 c12b710f93b957313ad1018de40ebe2dec53883c5de6d018c9d5577b1a426cf0
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
runtime                freestanding-c-raw-syscall
```

The AP contains exactly one Odin member:

```text
boot.img.lz4
```

## Static Gates

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a_mkdir_dev_reboot.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a_mkdir_dev_reboot.py --force
tar -tf workspace/private/outputs/s22plus_native_init/inplace_m10a_mkdir_dev_reboot_v0_1/odin4/AP.tar.md5
strings -a workspace/private/outputs/s22plus_native_init/inplace_m10a_mkdir_dev_reboot_v0_1/build/s22plus_init_m10a_mkdir_dev_reboot
```

Manifest gate result:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
nochange_repack_boot == base_boot
tar_members=["boot.img.lz4"]
intended_syscall_count=2
intended_syscalls=["mkdirat", "reboot"]
first_runtime_side_effect=mkdirat-/dev-0755
marker_write=false
kmsg_write=false
vfs_setup=mkdirat-dev-only
mknodat=false
mounts=false
sleep_before_reboot=false
module_insertions=false
configfs_runtime_gadget=false
udc_binding=false
usb_role_force=false
```

Required strings present in M10A `/init`:

```text
/dev
download
```

Forbidden strings absent from M10A `/init`:

```text
ld-linux
libc.so
S22_NATIVE_INIT
/dev/kmsg
/proc
/sys
/run
/lib/modules
finit_module
modules.load
ttyGS0
ss_acm.0
usb_gadget
/config
```

ELF shape:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
BuildID present
Entry point: 0x4001a8
Program headers: LOAD, NOTE, GNU_STACK
Sections: .note.gnu.build-id, .text, .rodata, .eh_frame, .comment
PT_INTERP: absent
M10A /init size: 1112
```

Disassembly proof of syscall order:

```text
400144: mov x8, #0x22
400148: svc #0x0
...
400198: mov x8, #0x8e
40019c: svc #0x0
4001b8: wfe
4001bc: b   0x4001b8
```

This encodes:

```text
mkdirat(AT_FDCWD, "/dev", 0755)
reboot(0xfee1dead, 0x28121969, 0xa1b2c3d4, "download")
```

## Interpretation

M10A is intentionally between M9A and M8A:

```text
M9A:  freestanding C, first live syscall reboot("download")            delayed download
M10A: freestanding C, mkdirat("/dev"), then reboot("download")         host ready
M8A:  freestanding C, mkdir/mount/devnodes/kmsg/sleep before reboot    no self-download
```

Future live branch logic:

```text
M10A delayed/in-window download:
  mkdirat("/dev") and basic pathname VFS access are survivable.
  Next add one side effect: either devtmpfs mount or /dev/kmsg node creation.

M10A no download:
  The first VFS syscall or pathname access is the failing boundary.
```

No live flash is authorized by this report.
