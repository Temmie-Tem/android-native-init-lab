# S22+ Native-Init M10A1 Stat-Dev Reboot Host Build - 2026-07-07

## Verdict

M10A1 host-only build passed. No device flash was run.

M10A1 is the narrow split after the operator-corrected M10A bootloop result.
M10A added `mkdirat("/dev", 0755)` and did not automatically return to download
mode; the later observed download endpoint was manual operator recovery. M10A1
therefore removes the mkdir mutation and keeps only a read-only pathname VFS
probe:

```text
newfstatat(AT_FDCWD, "/dev", statbuf, 0)
reboot(0xfee1dead, 0x28121969, 0xa1b2c3d4, "download")
```

Any live use still requires a fresh SHA-pinned S22+ boot-only `AGENTS.md`
exception, guarded live helper, default no-flash dry-run, and attended rollback
plan for the exact hashes below.

## Candidate

```text
source                 workspace/public/src/native-init/s22plus_init_m10a1_stat_dev_reboot.c
builder                workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a1_stat_dev_reboot.py
output                 workspace/private/outputs/s22plus_native_init/inplace_m10a1_stat_dev_reboot_v0_1
AP.tar.md5             68a7f1f5b336a32d882e7cdde73f299815d689b6885b724a6b6c7672bdda00bf
boot.img               2fe6b3270f7d493f677f126594061eea33d22de7abe98dc2210fe8050961ecb2
M10A1 /init            477583121c6c29f5eb31866c034352abb2f03c8fe97ec71e2f63ecbddd6f1642
source                 a60b66ec5d07f93bb9e29ac96c342e57621815630c29f31653b104e19f7ff86b
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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a1_stat_dev_reboot.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a1_stat_dev_reboot.py --force
tar -tf workspace/private/outputs/s22plus_native_init/inplace_m10a1_stat_dev_reboot_v0_1/odin4/AP.tar.md5
strings -a workspace/private/outputs/s22plus_native_init/inplace_m10a1_stat_dev_reboot_v0_1/build/s22plus_init_m10a1_stat_dev_reboot
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
intended_syscalls=["newfstatat", "reboot"]
first_runtime_side_effect=newfstatat-/dev-readonly
vfs_setup=newfstatat-dev-readonly-only
vfs_mutation=false
mkdirat=false
marker_write=false
kmsg_write=false
mknodat=false
mounts=false
sleep_before_reboot=false
module_insertions=false
configfs_runtime_gadget=false
udc_binding=false
usb_role_force=false
```

Required strings present in M10A1 `/init`:

```text
/dev
download
```

Forbidden strings absent from M10A1 `/init`:

```text
ld-linux
libc.so
S22_NATIVE_INIT
/dev/kmsg
/proc
/sys
/run
/lib/modules
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

ELF shape:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
BuildID present
Entry point: 0x4001c4
Program headers: LOAD, NOTE, GNU_STACK
Sections: .note.gnu.build-id, .text, .rodata, .eh_frame, .comment
PT_INTERP: absent
M10A1 /init size: 1144
```

Disassembly proof of syscall order:

```text
400160: mov x8, #0x4f
400164: svc #0x0
...
4001b4: mov x8, #0x8e
4001b8: svc #0x0
4001d4: wfe
4001d8: b   0x4001d4
```

This encodes:

```text
newfstatat(AT_FDCWD, "/dev", stack_statbuf, 0)
reboot(0xfee1dead, 0x28121969, 0xa1b2c3d4, "download")
```

## Interpretation

Updated split:

```text
M9A:   freestanding C, first live syscall reboot("download")             delayed download
M10A1: freestanding C, newfstatat("/dev"), then reboot("download")       host ready
M10A:  freestanding C, mkdirat("/dev"), then reboot("download")          bootloop, manual-download rollback
M8A:   freestanding C, mkdir/mount/devnodes/kmsg/sleep before reboot     no self-download
```

Future live branch logic:

```text
M10A1 reaches download without manual entry:
  pathname lookup and read-only VFS access are survivable.
  The M10A failure then points at mkdir mutation or directory-create path.

M10A1 bootloops / no download:
  pathname VFS access itself is suspect before Samsung reboot.
```

No live flash is authorized by this report.
