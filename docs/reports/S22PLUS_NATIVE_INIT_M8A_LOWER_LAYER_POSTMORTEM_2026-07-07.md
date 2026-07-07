# S22+ Native-Init M8A Lower-Layer Postmortem - 2026-07-07

## Verdict

The next live target must not be M8B/module splitting.

The current evidence puts the failing boundary between:

```text
M4T3 raw assembly first-action reboot("download")     PASS
M5B freestanding C + VFS/kmsg before reboot           NO SELF-DOWNLOAD
M8A freestanding C + smaller VFS/kmsg before reboot   NO SELF-DOWNLOAD
```

M8A removed module insertion, module-list parsing, `/lib/modules`, configfs,
USB gadget setup, UDC binding, and USB role forcing. Since it still did not
self-enter download mode, the failure is below the module/USB layer.

## Evidence

Live evidence:

```text
M4T3:
  raw static PID1, no stack use, no marker write
  first action = direct reboot("download")
  result = later Odin/download endpoint observed, rollback clean

M5B:
  freestanding C PID1
  mkdir/mount /dev /proc /sys /config, create /dev/kmsg nodes, emit marker
  then reboot("download")
  result = no self-download, no retained marker, rollback clean

M8A:
  freestanding C PID1
  mkdir/mount only /dev /proc /sys /run, create /dev/kmsg nodes, emit marker
  then reboot("download")
  result = no self-download, no retained marker, rollback clean
```

Artifact comparison:

```text
                     M4T3 raw asm       M5B C mount/reboot       M8A C minfs/reboot
init size            616                2336                     4008
program headers      LOAD+GNU_STACK     LOAD+NOTE+GNU_STACK      LOAD+NOTE+GNU_STACK
sections             .text .rodata      + .note .eh_frame        + .note .eh_frame
build-id note        absent             present                  present
entry                0x4000b0           0x4002d0                 0x400664
first live syscall   reboot #142        mkdirat path             mkdirat path
first reboot timing  first action       after VFS/kmsg/sleep     after VFS/kmsg/sleep
result               pass               no self-download         no self-download
```

Packaging is not the differentiator:

```text
all three use the same known-booting Magisk boot base
all three preserve the same kernel hash
all three replace only ramdisk /init
all three package exactly one Odin member: boot.img.lz4
M4T3 passed through the same in-place MagiskBoot/Odin path
```

## Interpretation

M8A makes the old "first 18 modules" hypothesis stale. The first failing layer
is one of these:

```text
normal C entry/runtime shape
compiler-emitted note/unwind metadata
stack frame / compiler-generated helper path
mkdirat path before reboot
/dev mount / devtmpfs fallback path
mknodat basic char nodes
/dev/kmsg open/write
mount proc/sys/run
nanosleep before reboot
reboot after setup rather than reboot as first action
```

Retained marker absence is not strong enough to name the exact syscall. Both
M5B and M8A write markers only after `/dev` setup and `/dev/kmsg` availability,
and the retained channel was empty after rollback.

## Next Candidate

Next bounded unit should be host-only M9A:

```text
M9A = freestanding C, same in-place MagiskBoot construction, but first action
      is direct reboot("download") with no marker, no VFS, no kmsg, no sleep.
```

Branch logic:

```text
M9A self-downloads:
  C entry/ELF/stack shape is viable.
  Failure is in VFS/dev/kmsg/mount/nanosleep or reboot-after-setup.
  Next split one runtime side effect at a time.

M9A does not self-download:
  C entry/ELF/stack/compiler metadata is suspect.
  Build M9B with build-id and unwind metadata removed, or use raw assembly for
  staged VFS syscalls.
```

Do not flash M9A until it has a host build report, SHA-pinned `AGENTS.md`
exception, guarded helper, and dry-run preflight. No new live flash is
authorized by this report.
