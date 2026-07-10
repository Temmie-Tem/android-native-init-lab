# V3431 S22+ PID1 Keystone Proof Design

## Decision

`HOST DESIGN PASS; PID1 PROOF FIRST; NO CANDIDATE; NO LIVE`.

The next S22+ unit must prove direct `/init` execution as PID 1 before USB,
display, distro, or a broad module substrate is attempted. The selected proof is
one minimal conjunctive keystone:

```text
exact candidate /init starts
  -> raw getpid() == 1
  -> mount only volatile proc/sys/dev support
  -> finit_module(exact ramdisk-bundled sec_log_buf.ko) == 0
  -> /proc/last_kmsg and /proc/ap_klog exist
  -> write one exact PID1_ENTER frame to /dev/kmsg
  -> quiet non-returning park
  -> attended RDX/Download + pinned Magisk boot rollback
  -> first rollback /proc/last_kmsg contains the exact frame
```

This is not described as a pure module-free proof. A positive result proves two
facts together: the exact candidate reached the marker path as PID 1, and the
exact retained observer was active. Marker absence remains inconclusive.

This unit creates no candidate source, boot image, AP, live helper, flash
exception, reboot, device contact, or write.

## Why This Comes First

V3430 recovered no current-run marker. Host analysis then found V3429 compared
the live kernel osrelease with the first vermagic token:

```text
generated: 5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8
live:      5.10.226-android12-9-30958166-abS906NKSS7FYG8
```

That gate ran before `finit_module`, so even an executing V3429 PID 1 parked
before its observer existed. Its failure line could not be retained. This
explains the V3430 evidence shape but does not prove `/init` ran.

The successor therefore has no candidate-side osrelease comparison before the
marker. Exact live osrelease equality moves to connected host preflight, where
it can stop before flash. The exact module remains build-time and artifact
pinned.

## Source-Grounded Proof

The exact FYG8 source establishes the kernel path:

```text
ramdisk_execute_command = "/init"
kernel creates kernel_init first so it obtains PID 1
kernel_execve("/init", ...)
```

The exact module loader source establishes:

```text
finit_module -> load_module -> do_init_module
  -> do_one_initcall(mod->init)
  -> MODULE_STATE_LIVE
  -> return 0
```

The exact Samsung source establishes that the load-bearing observer operations
are synchronous. `sec_log_buf` registers the platform driver; the existing
`samsung,kernel_log_buf` device is probed through a synchronous builder loop.
That loop creates `/proc/last_kmsg`, registers the `android_vh_logbuf` capture
path, creates `/proc/ap_klog`, and finishes the probe before module init returns.
Only compression/debugfs follow-up is threaded and is not part of this proof.

The exact module remains:

```text
filename=sec_log_buf.ko
size=76688
sha256=b4751eb8243a2bce4cd2f7b5f157f8429b295798dc310e23e861648906d24b61
hard dependencies=none
soft dependencies=none
future ramdisk path=/observer/sec_log_buf.ko
```

## Web Cross-Check

Public primary sources agree with the local findings:

- [Linux initramfs documentation](https://docs.kernel.org/filesystems/ramfs-rootfs-initramfs.html)
  states that an initramfs `/init` is executed as PID 1.
- [AOSP ramdisk documentation](https://source.android.com/docs/core/architecture/partitions/ramdisk-partitions)
  identifies the boot-ramdisk `/init` as first-stage init.
- [Android common kernel module source](https://android.googlesource.com/kernel/common/+/refs/heads/android12-5.4/kernel/module.c)
  shows `load_module()` calling `do_init_module()`, which runs the module init
  function and transitions the module to `LIVE` before success returns.
- [Linux ramoops documentation](https://docs.kernel.org/admin-guide/ramoops.html)
  requires a correctly reserved persistent-RAM region; built-in pstore symbols
  alone do not establish a working retained channel.

These sources support generic mechanics. The pinned FYG8 kernel source and live
reports remain authoritative for Samsung-specific behavior.

## Rejected Proof Channels

| Channel | Decision | Reason |
|---|---|---|
| intentional panic | reject | `CONFIG_SEC_DEBUG=m`; Android positive control does not prove pre-module direct-PID1 retention; native M18 did not retain a marker |
| pmsg | reject | native M24 produced no retained current-run marker |
| ramoops/pstore | reject | native M22 no-hit; correct reserved-memory operation is not established |
| USB enumeration | defer | it is the later capability being debugged, not an independent PID1 witness |
| timed reboot/download | reject | bare-PID1 reboot behavior and manual transition timing are ambiguous |
| persistent file/partition marker | forbid | violates the no-persistent-write boundary |

## Runtime Contract

The future candidate gate order is fixed:

1. Raw `getpid` syscall returns exactly `1`.
2. Only required volatile proc/sys/dev support is prepared.
3. `/observer/sec_log_buf.ko` is opened read-only.
4. One `finit_module` call returns `0`.
5. `/proc/last_kmsg` and `/proc/ap_klog` both exist.
6. One complete `PID1_ENTER` frame is written to `/dev/kmsg`.
7. The candidate enters a quiet non-returning park.

No fork, clone, exec, panic, reboot, watchdog access, USB/configfs work, sysfs
write, persistent mount, block write, or Android handoff is allowed. The marker
PID field must be formatted from the raw syscall result, not from a literal
claim. Before the marker, failures park silently and do not emit the run token.

The future build context SHA must cover a non-circular canonical input manifest:
target, fresh run ID, exact expected live osrelease, module identity, contract
identity, and candidate-profile revision. Output source/init/boot/AP hashes are
pinned separately after build and must not be inputs to their own context hash.

## Marker And Classification

The single binary-safe ASCII frame is:

```text
[[S22P1K1|LLLL|run=<32hex>;phase=PID1_ENTER;seq=00000001;pid=00000001;module=<64hex>;contract=<64hex>;context=<64hex>|crc=<8hex>]]
```

`LLLL` is the four-hex-digit payload byte count. CRC32 covers the canonical
payload. A fresh 128-bit run ID is created only in the later build unit.

Classification of the first rollback boot's two identical EOF-complete
`/proc/last_kmsg` reads is asymmetric:

```text
PASS     exactly one valid current-run frame with pid=1 and exact identities
NO_PROOF no current-run frame, raw token, or malformed current-run issue
FAIL     malformed, truncated, duplicate, bad CRC, wrong PID, or wrong identity
```

The positive result is
`PASS_PID1_EXECUTION_AND_OBSERVER_LOAD`. Absence is
`NO_PROOF_PID1_VS_OBSERVER_UNRESOLVED_STOP`; it cannot distinguish `/init`
non-entry, pre-marker candidate failure, observer failure, or transition loss.

## Next Unit

V3432 may implement one exact freestanding candidate and host-only builder. It
must add static/disassembly checks that the raw `getpid()==1` branch dominates
module load and marker write, that no fork/clone/exec path exists, and that no
pre-marker osrelease gate remains. QEMU/selftests must cover PID mismatch,
module-load failure, missing proc nodes, short marker write, and the exact happy
path.

Only after deterministic source/init/boot/AP hashes and those tests pass may a
separate live-helper/exception design be considered. V3431 authorizes neither.
