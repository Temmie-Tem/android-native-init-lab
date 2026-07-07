# S22+ Native-Init M9A C First-Reboot Host Build - 2026-07-07

## Verdict

M9A host-only build passed. No device flash was run.

M9A is the next lower-layer discriminator after M8A. It keeps the M5B/M8A
freestanding C ELF/build shape, but removes every VFS, kmsg, mount, sleep,
module, configfs, USB, marker-write, Android-handoff, and Magisk-handoff
variable. The first externally observable action is one direct arm64
`reboot(2)` syscall requesting Samsung download mode.

Any live use still requires a fresh SHA-pinned S22+ boot-only `AGENTS.md`
exception, guarded live helper, default no-flash dry-run, and attended rollback
plan for the exact hashes below.

## Candidate

```text
source                 workspace/public/src/native-init/s22plus_init_m9a_c_first_reboot.c
builder                workspace/public/src/scripts/revalidation/build_s22plus_inplace_m9a_c_first_reboot.py
output                 workspace/private/outputs/s22plus_native_init/inplace_m9a_c_first_reboot_v0_1
AP.tar.md5             c953f74fe7e3cdc226ebd3e1f0bac2142ee39e14483d87022714ae98e336d6b1
boot.img               4c998680a1ccdbd5017053d7da58858ab818fc0644f08ef5bb0fc5d0dcc2d981
M9A /init              46dfc4ecf92457260484d38360c70c0a45a1b7aead3a5cac567ec21ab2c7d97f
source                 6248617a4d2fe077768aef1324937659d33a0c93a453d0ecf9cd8cc3d3ec34a8
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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m9a_c_first_reboot.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m9a_c_first_reboot.py --force
tar -tf workspace/private/outputs/s22plus_native_init/inplace_m9a_c_first_reboot_v0_1/odin4/AP.tar.md5
strings -a workspace/private/outputs/s22plus_native_init/inplace_m9a_c_first_reboot_v0_1/build/s22plus_init_m9a_c_first_reboot
```

Manifest gate result:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
nochange_repack_boot == base_boot
tar_members=["boot.img.lz4"]
intended_syscall_count=1
intended_syscalls=["reboot"]
marker_write=false
kmsg_write=false
vfs_setup=false
mounts=false
sleep_before_reboot=false
module_insertions=false
configfs_runtime_gadget=false
udc_binding=false
usb_role_force=false
```

Required string present in M9A `/init`:

```text
download
```

Forbidden strings absent from M9A `/init`:

```text
ld-linux
libc.so
S22_NATIVE_INIT
/dev
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
Entry point: 0x400160
Program headers: LOAD, NOTE, GNU_STACK
Sections: .note.gnu.build-id, .text, .rodata, .eh_frame, .comment
PT_INTERP: absent
M9A /init size: 1008
```

Disassembly proof of the single live syscall:

```text
400160: stp x29, x30, [sp, #-16]!
400164: mov x29, sp
400168: bl  0x40010c
...
400138: mov  x0, #0xdead
40013c: mov  x1, #0x1969
400140: mov  x2, #0xc3d4
400144: movk x0, #0xfee1, lsl #16
400148: movk x1, #0x2812, lsl #16
40014c: movk x2, #0xa1b2, lsl #16
400150: mov  x8, #0x8e
400154: svc  #0x0
40016c: wfe
400170: b    0x40016c
```

This encodes:

```text
reboot(0xfee1dead, 0x28121969, 0xa1b2c3d4, "download")
```

## Interpretation

M9A is intentionally between M4T3 and M8A:

```text
M4T3: raw assembly, no stack use, first action reboot("download")       live PASS
M9A:  freestanding C, stack/helper path, first live syscall reboot      host ready
M8A:  freestanding C, VFS/kmsg/sleep before reboot                     live NO SELF-DOWNLOAD
```

Future live branch logic:

```text
M9A returns to download mode:
  Freestanding C entry, compiler-emitted NOTE/.eh_frame, stack use, and
  immediate reboot syscall path are viable.
  The M8A failure moves to a runtime side effect: VFS, /dev, mknodat,
  /dev/kmsg, mount, nanosleep, or reboot-after-setup.

M9A does not return to download mode:
  Freestanding C entry, compiler metadata, or stack/helper path remains suspect.
  Next split should remove build-id/unwind metadata or stage the first VFS
  syscall in raw assembly before adding any module or USB work.
```

No live flash is authorized by this report.
