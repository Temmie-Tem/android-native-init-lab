# S22+ Native-Init M10A2 Getpid Reboot Host Build - 2026-07-07

## Verdict

M10A2 host-only build passed. No device flash was run.

M10A2 is the narrow split after the M10A1 bootloop/manual-download result. It
removes pathname/VFS access entirely and adds only one non-VFS syscall before
the Samsung download reboot request:

```text
getpid()
reboot(0xfee1dead, 0x28121969, 0xa1b2c3d4, "download")
```

Any live use still requires a fresh SHA-pinned S22+ boot-only `AGENTS.md`
exception, guarded live helper, default no-flash dry-run, and attended rollback
plan for the exact hashes below.

## Candidate

```text
source                 workspace/public/src/native-init/s22plus_init_m10a2_getpid_reboot.c
builder                workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a2_getpid_reboot.py
output                 workspace/private/outputs/s22plus_native_init/inplace_m10a2_getpid_reboot_v0_1
AP.tar.md5             108c0a5e2a1fd80efed5ae93ea01b4b98c4990f7d3d8b292ef35ccc0de2fdb60
boot.img               f0238a82cad63a3d8017a0892a3a85bfe79c8c503848a4ac0fa4a21a77a72c94
M10A2 /init            0839562fbef74328abb17646d957516154ae85ab954667782c809249cf8bde99
source                 5b15166dfc405a7ee1297ac1cd0da3bd844779099748cf98ee3aca8e2e665d9a
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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a2_getpid_reboot.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m10a2_getpid_reboot.py --force
tar -tf workspace/private/outputs/s22plus_native_init/inplace_m10a2_getpid_reboot_v0_1/odin4/AP.tar.md5
strings -a workspace/private/outputs/s22plus_native_init/inplace_m10a2_getpid_reboot_v0_1/build/s22plus_init_m10a2_getpid_reboot
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
intended_syscalls=["getpid", "reboot"]
first_runtime_side_effect=getpid-non-vfs
vfs_setup=none
vfs_mutation=false
pathname_access=false
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

Required string present in M10A2 `/init`:

```text
download
```

Forbidden strings absent from M10A2 `/init`:

```text
ld-linux
libc.so
S22_NATIVE_INIT
/dev
/proc
/sys
/run
/lib/modules
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

ELF shape:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
BuildID present
Entry point: 0x4001a4
Program headers: LOAD, NOTE, GNU_STACK
Sections: .note.gnu.build-id, .text, .rodata, .eh_frame, .comment
PT_INTERP: absent
M10A2 /init size: 1104
```

Disassembly proof of syscall and call order:

```text
400194: mov x8, #0xac
400198: svc #0x0
...
400150: mov x8, #0x8e
400154: svc #0x0
...
4001ac: bl  0x400160
4001b0: bl  0x40010c
4001b4: wfe
4001b8: b   0x4001b4
```

The helper-start metadata confirms:

```text
getpid_func_start=0x400160
reboot_func_start=0x40010c
branch_targets=["0x400160", "0x40010c"]
```

This encodes `_start` calling:

```text
getpid()
reboot(0xfee1dead, 0x28121969, 0xa1b2c3d4, "download")
```

## Interpretation

Updated split:

```text
M9A:   freestanding C, first live syscall reboot("download")             delayed download
M10A2: freestanding C, getpid(), then reboot("download")                 host ready
M10A1: freestanding C, newfstatat("/dev"), then reboot("download")       bootloop, manual-download rollback
M10A:  freestanding C, mkdirat("/dev"), then reboot("download")          bootloop, manual-download rollback
M8A:   freestanding C, mkdir/mount/devnodes/kmsg/sleep before reboot     no self-download
```

Future live branch logic:

```text
M10A2 reaches download without manual entry:
  one non-VFS pre-reboot syscall is survivable.
  M10A1 points at pathname VFS access.

M10A2 bootloops / requires manual download:
  failure is broader than pathname VFS; inspect pre-reboot syscall/timing/state.
```

No live flash is authorized by this report.
