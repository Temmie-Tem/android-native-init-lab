# P418 Debian USB-first preparation

Date: 2026-10-08 KST. Target: S22+ `SM-S906N/g0q/S906NKSS7FYG8` only.
Status: **PASS_GO; CONNECTED_PREPARATION_PASS; AWAITING_RETURNED_ATTENDED_GRANT**.
No candidate transfer, device write/control, new grant or consumption occurred
during this preparation. A90 and S20+ were not contacted.

## Bounded result

The operator selected a minimum Debian early-PID1/USB successor after P417's
missing USB proof. P418 `v0.5.0-rc.2` implements
[USB-first V1](../operations/S22PLUS_DEBIAN_USB_FIRST_V1.md): Debian shell stays
PID1; stock `sec_log_buf` loads first, followed by the retained 73 platform
modules and a fixed authenticated ACM observer. The eight UFS modules and
all block/storage preparation are excluded from its fixed child path.

Retained P399 source inspection found the functional USB sequence: full
descriptor/readback set, `max_speed=high-speed`, raw tty before publication,
one role transition from `none` to `peripheral`, and one UDC bind. Trace,
QSCRATCH and exposure-latch code observes that sequence rather than adding
another USB adjustment. The small Debian child adopts the functional steps;
it does not copy the old native PID1/service runtime. These differences do
not diagnose P417's unobserved internal stage or prove its failure cause.

The stock logger has 71 imported symbol CRCs, all matching the fixed Image.
Exact module disassembly and pinned Samsung source agree that DT strategy 3
uses vendor printk hooks. Driver-bound evidence is required immediately after
insertion; module presence alone is insufficient. No kernel rebuild, DT edit,
direct reserved-memory writer, logging-policy change or filesystem writer was
needed. Current kernel-ring acceptance and post-return retention remain
different claims.

## Evidence production and return

Each fixed stage marker binds run, kernel boot, sequence and HMAC. One bounded
`/dev/kmsg` write is followed by exact ring readback within 64 KiB/500 ms;
other ring messages are discarded in RAM. A failure stops later preparation
without reissuing the write or module insertion. The 64 KiB RAM log remains
the authenticated USB snapshot's preparation evidence. USB proof measures
the actual PID1 executable/command line, `/init` and helper bytes, and boot.

The dedicated protocol domain prevents the USB-only result from being read as
the older protected-metadata result. The existing V3 `debian-early` owner,
one-operation 1800-second attended grant, global consumption and physical
original-A recovery are reused. No shell/control request, native admission,
NCM/SSH, installed init or automatic recovery is added.

After original Android closes healthy, a fixed D0 reader requires that exact
returned Android boot, reads only bounded `/proc/last_kmsg`, brackets it with
root/boot/supporting-health and shell-v2 checks, preserves raw bytes first and
accepts only authenticated selected-run markers. When USB proof exists, its
candidate boot hash must match the returned records. With no USB proof,
standalone authenticated partial records remain possible. Missing records
never prove non-execution. Hardware retention is still **UNPROVED**.

## Actual artifacts and validation

Private evidence root:
`workspace/private/outputs/s22plus-debian-usb-first-p418-h0-20261008-1/`.
The source snapshot identifies the actual working-tree inputs over base
`12aac6e7312c7d4f476bc127edd9fbc757cf7e2b`; the base commit alone does not
describe inherited uncommitted dependencies. Historical P417 source bindings
and consumed records are not repinned.
The scoped commit excludes unrelated dirty work; its tree alone is not a fresh
live-source qualification. Actual live qualification uses the frozen working
tree, including its reviewed complete policy bytes.

| Artifact | SHA-256 |
| --- | --- |
| `build-3` A/B initramfs, 7,299,496 bytes | `297b639b258b78f2374c5366f90adf94f4762ed8dd70cae804d86fdd633dde0c` |
| `package-1` boot, 100,663,296 bytes | `2b63bd0b9c0f86ba2e5b38dcf1775087c8f1447557e9b6c3b4543a6e19d9697b` |
| `package-1` AP, 34,129,961 bytes | `3a07a6dcb1d3a23909d29b2d1331ead5efaa5479bc0e5ef7762c87290dfc3075` |
| Qualified image record | `27f9ecf3969d0ac11cb13b69f2d9f558df68813be73bc0aea3ec14666f5dc7d7` |

Both actual boot/AP constructions are identical and preserve the retained
kernel, boot signature and trailer bytes, with only the declared ramdisk and
derived offsets changed. The existing unlocked research carrier's old AVB
payload descriptor is not a signature for the new ramdisk. Combined stock
vendor/Debian archive extraction retains Debian's working dynamic-loader path.

`vm-2` passed four real ARM64 cases: normal authenticated PID1/USB snapshot,
valid-CRC wrong-HMAC rejection, logger-off preparation rejection, and insertion
failure rejection. Normal output contains all 153 preparation and seven USB
stage markers with valid HMACs. Every sentinel disk is unchanged. Board
identity, module insertion/probe and physical gadget operations are explicit
substitutions; real Samsung USB, logger retention and recovery are not VM
claims. A separate ARM64 harness executes the actual retained-record helper
against seven syscall failures/bounds, including a late matching record,
silent drop, short write, uneven remaining-byte budget and backwards clock.

Focused Python checks passed: early protocol/owner 12, USB protocol/scope 8,
V3 session 21, handoff owner 13, root-inspection scope 11 and boundary 11
(76 total). Fourteen touched Python files passed compilation; repository
boundary and diff checks passed. Independent final review returned `PASS_GO`
with no unresolved findings, bound to the frozen 105-file host closure
`555a07e30afbf38f87227232aca5d5f4e049c068e70d76cc052b013847121b04`,
142 build-source rows and 168 VM-source rows. The distinct capability binding
is `workspace/public/src/device-action/bindings/s22plus_debian_usb_first_v1_review.json`.
An isolated export of the scoped index also passed 54 portable tests; its
projected common-policy digest matches the projected root pin. That commit
projection received a separate H0 semantic check without changing live bytes.

The fixed connected preparation then passed in `connected-1`: exact rooted
original-A/supporting health before/after, shell-v2, GPT and Android32 capacity.
The concrete one-operation task hash is
`28edefbce472c08fa18441ca730af6c131267c733b321e1c589ed19fce938499`.
No grant is open and no image has been transferred. Only the returned finite
approval and current physical attendance remain before candidate execution.

The first logger-off VM fixture used a bare `off` sysctl write, which the
inspected kernel rejects without the expected newline. Its unexpected USB
publication is preserved as a fixture failure. The corrected fixture reads
back `off` before expecting rejection; it does not weaken the producer or
reinterpret the earlier failure. Initial compiler diagnostics and all prior
build/VM artifacts are retained privately.
