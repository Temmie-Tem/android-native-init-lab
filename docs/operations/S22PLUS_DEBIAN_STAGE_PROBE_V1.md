# S22+ Debian logger-only early stage probe V1

Status: **REVIEW_GATED_CAPABILITY**

This narrow sibling of the Debian USB-first profile selects only
`SM-S906N/g0q/S906NKSS7FYG8` and V3's existing `debian-early` operation under
`debian-stage-probe-v1`. It establishes a pre-storage observation boundary.
It neither inherits USB success nor changes any consumed result or grant.

## One operation and original-A owner

One qualified fresh boot-only candidate, current exact original-A health,
source-bound independent review and usable physical Download recovery require
one returned attended 1800-second, one-operation grant. The N-transfer intent
consumes the entire automatic probe, including uncertain insertion or logging.
There is no native admission, E, reconnect, shell command, USB gadget, CONTROL,
network, installed init, ordinary reboot or automatic-recovery claim.

The existing owner performs fresh healthy A, Download and N transfer, then a
fixed 90-second host opportunity window anchored to that transfer's original
completion. The window reports `AWAITING_RETAINED_STAGE_RECORDS`, with device
activity unknown and no execution proof. It sends no device query. Attended
physical Download and one original A follow within the earlier of the existing
600-second return deadline and original grant deadline, then full original
boot/root, changed-boot and Android32 GPT/capacity health. Transfer preparation
reserves the same bounded 240-second transfer allowance, window and physical
return allowance before the original N effect. No deadline renews.

Uncertain effects never repeat. A module syscall can outlive any userspace
limit. Lost physical recovery or other common stop ends new effects; only the
existing journal-bound original-A recovery remains. Proved A followed by failed
health permits health-only continuation. An absent record grants no replay.

## Fixed logger-only child

Debian's packaged shell `/init` remains PID1. The existing fixed tmpfs/dev/proc/
sys setup precedes one root child. The child validates the exact kernel/model
and its RAM workspace, then emits bounded stage records. It verifies actual
parent executable path, exact `/bin/sh` `/init` command line, shell and `/init`
hashes, and measures its own executable bytes. Parent evidence does not depend
on a completed preparation log or a later evidence child.

The sole declared module is the exact retained `sec_log_buf.ko`, with 71
kernel-matched symbol CRCs. There are zero platform-prefix and zero UFS modules.
The child checks absence, pins/rehashes the exact module file, emits a pre-call
record, checks the original 60-second kernel BOOTTIME bound and absence again,
and calls `finit_module` once. It never unloads or reinserts. A return record is
separate from success; EEXIST and all other errors stop. Bounded read-only
readiness checks, at most 200 ten-millisecond waits, require the module,
matching platform-driver link and `last_kmsg` node before binding completion.

There is no block-node creation, partition ioctl, storage discovery, GPT or
superblock access, root mount, native_data write, repair or installed execution.
The vendor ramdisk, kernel and DT are unchanged. The stock logger alone owns
its already allocated retained RAM and vendor printk hooks; there is no direct
physical-memory mapping/writer, new region, sysctl/logging-policy write, panic
or new kernel component. After success or failure the child returns to Debian
PID1's existing park loop. No thermal service or safe-quiescence guarantee is
inherited from native init.

## Short records and post-return evidence

At most nine independently authenticated records use a distinct stage-probe
HMAC domain. Each fixed frame has 108 binary bytes encoded into 144 canonical
Base64 characters inside `S22STG1[...]`: 153 marker bytes, plus the printk
priority and newline. Run, kernel boot, sequence, event/value and one 32-byte
measurement are authenticated. Records distinguish child entry, parent shell,
init image, helper image, next module call, module return, logger binding and
completion; a separate rejection event never constitutes completion.

Each record has one checked write and exact nonblocking current-ring readback
within 64 KiB and 500 ms. A logging failure stops later effects and does not
retry that record. Record emission and new module effects require kernel
BOOTTIME below 60 seconds. Current-ring acceptance is not post-return retention.

After the original operation closes healthy, the foreground task may use the
same fixed root-health/shell-v2-bracketed D0 `last_kmsg` acquisition, at most
4 MiB, bound to the exact returned Android boot and rederived consumed owner.
No reboot, mount, clear or write is added. Raw bytes are preserved before
interpretation. Bounded pure-read reobservation follows the existing target
rule, without reopening the original grant or repeating an effect.

The new decoder examines only exact contiguous fixed-size envelopes, retaining
raw offsets and malformed-candidate diagnostics. It reconstructs no bytes.
Foreign runs are ignored; mixed authenticated boots, duplicate or reversed
sequences reject the projection. A complete result requires all eight expected
records, matching measured archive hashes, successful insertion/binding and
no damaged candidate. An authenticated rejection, incomplete valid subset and
no authenticated record are separate results. The last surviving record is
not a stopping-point diagnosis. P418's old parser and verdict remain unchanged.

Complete evidence proves only this early Debian-parent/logger boundary through
the tested return and emission of the terminal milestone. It does not prove
the final marker's readback/close, helper return or parking. It does not prove
platform/UFS progress, P421 execution,
file creation, unmount, native_data health, installed Debian or USB/SSH. No
record cannot distinguish failure before RAM setup from lost later evidence.

## Qualification and scope lifetime

Actual A/B boot/AP and combined vendor/Debian archive inspection must show the
sole selected helper/module workload. ARM64 cases exercise real Debian PID1,
measurement, short-frame producer and ring readback, with board/module/probe
substitutions disclosed. Require normal, actual parent-image mismatch,
insertion error, missing binding, disabled ring publication and expired device
time cases, plus parser damage/gap/foreign-run/duplicate/mixed-boot negatives.
Whole VM sentinel disks remain unchanged. VM evidence proves neither physical
retention nor Samsung module readiness or recovery.

The one-module restriction defines this probe's scope, not a new global gate.
The review trigger is any change to its module/effect set, evidence meaning,
parent measurement, return owner or decoder framing. A prospective extension
can be considered after the current result is closed; it must declare its own
scope rather than silently carrying this diagnostic restriction forward.
Offline preparation uses retained exact target/recovery bindings and claims no
fresh connected health. This policy activates no run by itself.
