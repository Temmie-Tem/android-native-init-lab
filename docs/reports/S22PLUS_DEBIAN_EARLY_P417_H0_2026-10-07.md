# S22+ P417 Debian-owned early boot preparation

Date: 2026-10-07 KST. Target: `SM-S906N/g0q/S906NKSS7FYG8` only.
Scope: one prospective `debian-early` operation, `p417 v0.5.0-rc.1`.

This report records preparation. The subsequent
[2026-10-08 physical run](S22PLUS_DEBIAN_EARLY_P417_FIRST_RUN_2026-10-08.md)
consumed the candidate with **NO_PROOF** and recovered original Android healthy.

## Result and boundary

The operator requested continuation through a physical experiment. This unit
packages Debian initramfs-tools' shell `/init` as the initial PID1, the retained
73 platform plus eight UFS modules, a protected metadata child and a separate
authenticated evidence child. It uses the existing FYG8 kernel unchanged.
The [reviewed operation](../operations/S22PLUS_DEBIAN_EARLY_BOOT_V1.md) requires
one concrete attended grant and one original-A return with Android32 health.
Preparation and H0 qualification alone do not open that grant.

The reviewed capability and actual candidate qualified with independent
`PASS_GO`. Fixed foreground Android preparation subsequently passed boot and
supporting-partition hashes, root, shell-v2, exact GPT, 34,357,624,832-byte
Android32 capacity and same-boot health brackets. At preparation completion no
grant was open and no candidate had been transferred. Physical qualification
then required the exact returned grant and actual attendance. The most recent
experimental result at that point remained P415's dirty
native_data observation and healthy original Android closure. A90 and S20+
are untouched.

The trial stops at authenticated early-PID1 and GPT/superblock evidence. It
does not mount native_data, replay its journal, clear partition RO, execute
installed Debian init, install a root filesystem or start SSH. Clean metadata
would not establish full root admission. Dirty metadata is an expected result.

## Execution and recovery

Debian's packaged shell remains PID1 while its children run sequentially.
The preparation child checks every exact module before insertion, preserves
the established order and parameters, records one attempt per module, and
verifies exact UFS/GPT identity before setting only native_data's RAM RO flag.
It reads the primary ext4 superblock and repeats GPT/superblock/RO checks;
owned block aliases are removed without clearing RO.

The evidence child measures its parent, the actual PID1 executable, `/init`,
the preparation executable and current boot identity. It creates one fixed
ACM gadget, opens and normalizes its tty before publishing the UDC, accepts one
authenticated challenge, exports the bounded RAM record and exits. The shell
parks. There is no native console, CONTROL or automatic recovery command.
The ordinary V3 owner consumes automatic preparation with the candidate
transfer intent and pauses for physical Download before one original-A transfer.

The original native thermal workers are absent. The existing kernel/platform
modules are retained, but this is not a native-health, watchdog-petting or
automatic-recovery claim. Physical attendance and the demonstrated Download
route remain necessary. A userspace timeout cannot recover a stalled kernel.
RAM evidence may disappear on reset; missing records do not prove non-execution.
No persistent evidence writer is authorized by this operation.

## Validation

The actual archive audit joins the Debian `/init`, BusyBox shell hardlink,
compiled preparation/evidence children and all 81 module files to their input
bytes. The vendor ramdisk's real `/lib/modules` directory is preserved while
Debian's dynamic-library paths remain reachable through explicit links.

ARM64 VM tests combine the retained vendor archive with the new Debian archive.
They run the actual PID1, file measurements, block ioctls, GPT/superblock reader
and authenticated frame producer/consumer. Board identity, module insertion,
UFS discovery and USB hardware are explicitly substituted. Clean and RECOVER
dirty cases prove partition RO while disk/userdata remain writable in RAM;
whole sparse disk fingerprints remain unchanged. A request with a valid frame
CRC and an invalid HMAC receives no evidence and exits unsuccessfully.

Twelve focused tests exercise authenticated semantic mutations, bad HMAC,
truncated/repeated frames, cleanup grammar, exact task scope, physical pause,
uncertain N/evidence/A handling, health-only recovery and raw retention when
close-record publication fails. Forty-five existing handoff/session/boundary
tests also pass. Python compilation and shell syntax checks pass.

Boot packaging uses the pinned retained boot carrier and existing tools.
Kernel, fixed header fields, boot signature and partition-size image are
unchanged; the exact new ramdisk is independently decompressed and compared.
The SEANDROID marker and vbmeta move with the larger ramdisk. Signed vbmeta
bytes remain identical, with exact footer/alignment/zero-padding checks.
This does not sign the new ramdisk or write the vbmeta partition.

Independent review covers the new policy adoption, archive/gadget/protocol,
host owner, no-replay behavior and physical recovery. Final `PASS_GO` binds the
102-file host closure, 137-file runtime/build closure and actual boot/AP
qualification. The dedicated source-bound review is published; every older
capability review retains its original meaning.

## Private provenance and preserved failures

Evidence is under
`workspace/private/outputs/s22plus-debian-early-p417-h0-20261007-1/`.
The final artifact uses `build-8`, `vm-5` and `package-2`. A/B initramfs size is
7,446,273 bytes, SHA-256
`4f241a8aa8b9b337c92d8c5941f8b306050b4ca607676e11080c6c958d0c5cad`.
The boot-only AP is 34,314,281 bytes, SHA-256
`d4cae2e0c01ede3674f23ea8d450f7af426c2ce72e0f3fa03b253c709dacc2be`.
The 100,663,296-byte boot image retains the fixed FYG8 Image; its SHA-256 is
`f1a24124634cb9fab473279940e93f9286ef07e43c4f38f2119eb185e4066bb9`.
The fixed connected preparation is `connected-2`, with 19 bounded raw captures
and a concrete 1800-second/one-operation attended proposal. The first read in
`connected-1` stopped on ADB's host-daemon startup stderr. Its raw evidence was
preserved; the reviewed pure-read reobservation used a fresh directory and
passed without weakening the stderr predicate or performing a control action.

Source snapshots and generated private seals are retained with each build and
VM suite. Keys, target identifiers, raw records and executable artifacts remain
private. The prior H0 FYG8 preparation inventory is reused unchanged.

Intermediate H0 failures remain intact: compiler warnings, the initial wrong
shell/hardlink assumption, too-small artifact pin bound, VM serial setup, a
source-change stop during a build, and an overstrict opaque-trailer comparison.
The older malformed-request VM case tested CRC rejection; only the later
valid-CRC bad-HMAC cases establish authentication rejection. None was a device
effect, and no failed result was relabelled as success.
