# S22+ Debian USB-first V1

Status: **REVIEW_GATED_CAPABILITY**

This sibling of [Debian-owned early boot V1](S22PLUS_DEBIAN_EARLY_BOOT_V1.md)
uses the same V3 `debian-early` operation and physical-original-A recovery
owner, with the distinct `debian-usb-first-v1` runtime profile and source-bound
review. Only `SM-S906N/g0q/S906NKSS7FYG8` and the retained Android32 target are
selected. P417/P418 and every historical grant remain consumed; this definition
opens no grant. The original profile's metadata predicate is unchanged.

## Finite operation and recovery

One fresh boot-only candidate, current exact target/healthy original A,
qualified artifact/source closure, key and demonstrated physical Download
route require one returned attended 1800-second, one-operation V3 grant.
The candidate-transfer intent consumes every automatic preparation effect.
There is no native admission, E, repeated candidate, reconnect, shell request,
CONTROL, network configuration, SSH, shutdown or automatic recovery claim.

The graph remains healthy A, Download, candidate, one authenticated observation,
attended physical Download, one original A and full Android32 health. Endpoint
and evidence deadlines remain 90 and 60 seconds; the evidence child retains
its 300-second BOOTTIME bound. Physical return is bounded by the earlier of
600 seconds and the original grant deadline. Uncertain effects never repeat.
Expired work retains only the original recovery owner. Proved A followed by
failed health permits health-only continuation, never another transfer.
Attendance and usable physical recovery remain mandatory throughout. No old
native thermal service, watchdog-petting result or safe-quiescence assertion
is inherited. A kernel/module syscall can outlive a userspace deadline.

## USB before storage

Debian's packaged shell `/init` remains PID1 and starts two fixed children
sequentially. The artifact fixes its logging mode at build time; this is not a
runtime fallback or a relaxed interpretation of a failed retained log.
The `ram-only` mode, first selected by P419, verifies and loads exactly the
retained 73-module platform order. It excludes the added `sec_log_buf` module,
logger binding and every `/dev/kmsg` write/readback from both children. Checked
bounded RAM preparation records remain mandatory, and the complete log must
authenticate through USB. USB stage printk diagnostics are absent in this mode.
It makes no post-return retention claim and selects no post-return `last_kmsg`
capture. Losing USB can leave no retrievable stage evidence after physical
return; that limitation is accepted for this bounded dependency-isolation step.

The separately declared `retained` mode preserves P418's exact stock
`sec_log_buf` first insertion and matching driver binding before the same 73
platform modules. Historical builds without a mode field mean `retained` only.
Neither mode permits skipping a platform module or its checks after failure.
Every insertion has one checked intent and
completion record; EEXIST/error stops without retry/unload. The eight UFS
modules are absent from the candidate's fixed module directory. There is no
UFS initialization, block alias, GPT/superblock read, BLKROSET, root admission,
block-backed/root filesystem mount, journal replay, repair, installed init or
persistent filesystem write. Fixed configfs and Debian's RAM filesystem setup
are retained. The vendor ramdisk is unchanged; no ambient module loader runs.

The evidence child requires the complete platform result. It uses the retained
12 driver/UDC readiness paths and fixed `g1`/ACM configuration, including
high-speed, bcdUSB 0x0200, bcdDevice 0x0003, bmAttributes 0x80 and MaxPower 500,
with attribute and topology readbacks. The tty is raw before one role write
from `none` to `peripheral` and one UDC bind. Trace/QSCRATCH/exposure-latch
diagnostic orchestration is not copied. Actual authenticated USB response is
the channel proof. Target-specific role/bind failure never retries.

The existing research VID/PID and `S22E3` plus fresh run identity preserve the
reviewed host endpoint/holder checks. The protocol uses the distinct
`S22PLUS-FYG8-DEBIAN-USB-FIRST-v1` HMAC domain. Actual parent executable,
command line, `/init`, helper and kernel boot identity must match the built
archive and complete RAM log, including the selected mode's exact completion
record. `PASS_DEBIAN_USB_FIRST_OBSERVED` establishes
Debian early PID1/platform/USB evidence only. It says nothing about native_data
state or installed Debian, and is not a reboot-retention verdict.

## Bounded retained stage evidence

This section applies only to a build declared `retained`; the post-return
reader rejects a `ram-only` candidate before any connected read.

The stock logger uses its existing reserved-memory region and strategy 3
vendor printk hooks; there is no new physical-memory writer, mapping, region,
DT edit or persistent-storage writer. The candidate writes only fixed,
run/boot/sequence-bound HMAC stage lines through `/dev/kmsg`, at most 256 lines
of at most 768 bytes. It never writes a panic trigger, sysctl or logging-policy
setting. One checked open/write/close emits each record. Because write length
can conceal a dropped record, a read cursor established before the write must
find the exact current record within 64 KiB and 500 ms. Other messages are
discarded in RAM. A failed readback stops later preparation effects; no write
or module action is repeated. Ring acceptance is separate from retention.

Logger probe snapshots the previous boot into `last_kmsg` before importing
current early messages. Its current-boot `last_kmsg` is therefore not current
stage proof. After the operation closes healthy in original Android, the
foreground task may perform the fixed root-health/shell-v2-bracketed D0 read
of `/proc/last_kmsg` (at most 4 MiB), with no reboot, clear, mount or write.
Before/after health must bind the exact target and the same returned Android
boot. Raw bytes are preserved privately before interpretation. A pure read
failure may use the target's reviewed read-only reobservation rule; it does
not reopen the consumed operation or renew any effect.

The reader accepts only candidate-key-authenticated markers for the selected
run, one kernel boot and increasing nonduplicated sequence numbers. Complete
or partial stage records are reported separately from USB proof and Android
health. Missing, overwritten or truncated records never prove non-execution.
Only actual post-return retrieval can establish retention across the tested
physical return. No native-return candidate is selected by this profile.

## Qualification

Independent review covers the selected mode, changed reachable producer/consumer,
actual combined
vendor/Debian archive, USB sequence, existing V3 no-replay/recovery integration
and evidence scope. Retained mode additionally covers stock logger ABI/probe,
bounded printk readback and fixed post-return D0. ARM64 VM cases execute actual
Debian PID1, RAM logs and HMAC frames with board/module/gadget substitutions
disclosed. Both modes require normal, invalid-HMAC, logger-off and failed-insertion
cases. For `ram-only`, logger-off must still produce authenticated complete
platform/PID1 evidence without a `/dev/kmsg` node, and a missing RAM log must
prevent USB publication. For `retained`, logger-off must stop preparation.
H0 results do not prove Samsung hardware, retention or recovery.

Actual A/B boot/AP qualification and a current source-bound capability review
precede the existing foreground fixed Android health/shell-v2/GPT/statfs
preparation. Those read-only preparation checks neither load a candidate nor
open the finite grant. A fresh concrete returned grant and actual attendance
are still required for the experiment.
