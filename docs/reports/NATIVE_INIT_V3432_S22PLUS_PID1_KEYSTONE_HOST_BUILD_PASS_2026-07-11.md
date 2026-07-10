# V3432 S22+ PID1 Keystone Host Build Pass

## Verdict

`PASS; EXACT BOOT-ONLY CANDIDATE BUILT; HOST ONLY; NO LIVE AUTHORIZATION`.

V3432 implements the V3431 PID1-first contract as a 1,856-byte freestanding
AArch64 `/init`. Its first runtime syscall is `getpid`. It advances only when
that return value is exactly 1, prepares volatile `/dev`, `/proc`, and `/sys`,
loads one exact ramdisk-bundled `sec_log_buf.ko`, requires both observer proc
nodes, writes one PID-derived `PID1_ENTER` frame, and parks forever.

No device contact, reboot, Odin transfer, partition write, or flash occurred.
The produced manifest explicitly keeps live flash unauthorized and requires a
fresh exact SHA-pinned `AGENTS.md` exception.

## Exact Artifacts

```text
run_id              db4d3b66480bec29158c9ac9bfede880
source_sha256       0a69f55947fa148928d10741c10bb5433f493434cb734d9a1f276bbfd40fc664
init_sha256         59d4a11fd66528a3be4d4749b8191449a8675fdb0f7148b3cb9bdded6263b2db
module_sha256       b4751eb8243a2bce4cd2f7b5f157f8429b295798dc310e23e861648906d24b61
kernel_sha256       bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
boot_img_sha256     67075d7f26486c3e4130dc6a935c5ed98ded8b817d9d5ec4beeddd05bef7f232
boot_lz4_sha256     c698d5acf84ea10c5cf8ed8e95ed101a59483abf38b7977d16a2af0c95f67d5b
AP.tar.md5_sha256   264acafa1320e6faee1f6b3a569c6de1742ca6712e61003d114ec4a6d549bf34
context_sha256      b44f060a596bb6319d237bb683136365584df2d134fc0a9e9584c9d946b47506
```

The boot image is exactly 100,663,296 bytes. `AP.tar.md5` contains exactly one
member, `boot.img.lz4`. The repacked kernel hash equals the known-booting Magisk
base kernel. The ramdisk replaces `/init` and adds only:

```text
/observer                    mode 0755
/observer/sec_log_buf.ko     mode 0600, size 76688
```

The embedded module was extracted from the final repacked boot and matched the
pinned input hash. The no-change MagiskBoot repack remained byte-identical to
the known-booting Magisk boot SHA256
`2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.

## Marker

The expected frame is bound to run, actual PID field, module, V3431 contract,
and non-circular build context:

```text
[[S22P1K1|012a|run=db4d3b66480bec29158c9ac9bfede880;phase=PID1_ENTER;seq=00000001;pid=00000001;module=b4751eb8243a2bce4cd2f7b5f157f8429b295798dc310e23e861648906d24b61;contract=686207c75d2530f90049de6b6945fbd3134019ca402f84cb97418c43804a4ca5;context=b44f060a596bb6319d237bb683136365584df2d134fc0a9e9584c9d946b47506|crc=732895ee]]
```

The runtime copies the pinned frame, rewrites its eight PID hexadecimal digits
from the raw `getpid` result, and requires the result to equal the exact expected
frame before the sole `/dev/kmsg` write. The run token appears in no failure
diagnostic. Every failed gate parks silently.

## Removed V3429 Variables

V3432 has no runtime osrelease read, module SHA implementation, `/proc/modules`
scan, driver-bind symlink wait, PRECHECK/FINAL current-ring readback, failure
diagnostic, USB/configfs work, reboot, panic, watchdog, persistent mount, or
block write. Exact live osrelease equality remains a host connected-preflight
gate for the future live helper.

## Validation

```text
V3432 focused tests                        11/11 PASS
QEMU state/marker selftest                 PASS
PID mismatch stop                          PASS
volatile setup failure stop                PASS
module failure stop                        PASS
observer-node failure stop                 PASS
short marker write stop                    PASS
exact happy path                           PASS
first _start syscall by disassembly        getpid
static AArch64, no PT_INTERP                PASS
undefined symbols                          0
forbidden runtime syscalls                 absent
independent full builds                     byte-identical
expected frame V3431 classification         PASS_PID1_EXECUTION_AND_OBSERVER_LOAD
```

Both independent builds matched for source, generated header, expected marker,
module, base boot, no-change repack, original Magisk init, compiled init,
ramdisks, kernel, boot image, LZ4 payload, AP tar, and AP.tar.md5.

## Boundary And Next

This host build does not authorize a flash. The next unit must create a fresh
one-shot helper and exact `AGENTS.md` exception pinned to the hashes above,
require connected Android/Magisk health plus exact live osrelease before any
write, and retain mandatory Magisk boot-only rollback. Only a later explicit
live invocation may consume that exception.
