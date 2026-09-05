# S20+ early-boot observation through sec_log `/proc/last_kmsg`

Date: 2026-09-05. Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`.
Status: **H0 DESIGN ONLY - NO RUNNER ACTIVE, NO DEVICE AUTHORITY**.

## Why this replaces the PMSG marker route

Three P0 native-PID1 F1 candidates are consumed. Every one completed its full
180-second ACM observation window and emitted no banner, so "PID1 never ran"
and "PID1 ran and nothing reached the host" stayed indistinguishable. The lane
does not lack candidates; it lacks an out-of-band channel.

It also lacks an in-band record. The USB observer already distinguishes exact,
pending and conflicting identities (`s20plus_g986n_p0_pid1_usb_observer.py:112`,
`:242`), so partial enumeration is a first-class concept in the design. But the
consumed V3 run published only the observer *baseline*, with every array empty
(`p0-usb-baseline.json`), and a terminal `candidate-observation.json` carrying
`claim_verdict` plus a `reason_sha256` digest and `transport_authorized: false`.
The observer's terminal inventory was never published, so whether the candidate
appeared on USB at all - even partially - is unrecoverable from three consumed
F1 transactions. The absence of a banner is recorded; the absence of
enumeration is not.

The PMSG warm-reboot marker D1 was built to supply one. It writes a marker,
reboots, and reads `/sys/fs/pstore/pmsg-ramoops-0`. Two independent reviews of
its corrected V2 have now returned findings, its V1 trial consumed an action
without writing a byte, and it proves only that one byte survived.

Recorded readiness D0 evidence plus the stock kernel configuration show a
channel that is already present and strictly more informative:

| Node | Recorded state |
|---|---|
| `/sys/fs/pstore/console-ramoops-0` | unavailable |
| `/sys/fs/pstore/dmesg-ramoops-0` | unavailable |
| `/sys/fs/pstore/pmsg-ramoops-0` | unavailable |
| `/proc/last_kmsg` | regular, readable, 2,097,136 bytes, content not read |

`CONFIG_SEC_LOG_BUF=y`, `CONFIG_SEC_LOG_LAST_KMSG=y` and
`CONFIG_SEC_LOG_STORE_LAST_KMSG=y` identify the mechanism, and
2,097,136 = 2 MiB - 16 identifies a 2 MiB Samsung sec_log reserved buffer with a
16-byte header. The kernel's own printk ring is `CONFIG_LOG_BUF_SHIFT=17`
(128 KiB) and separate.

The previous boot's kernel log is therefore already retained and root-readable,
populated automatically on every boot, with no write action of any kind.

## Two units, in order

### Unit 1 - `last_kmsg` observation D0 (instrument)

A fixed, reviewed, read-only D0 that establishes what the channel actually
carries, before any further F1 is spent. Deliberately small so it can be
reviewed quickly. It consumes no marker action, performs no write, and causes
no reboot or mode transition.

It must answer exactly three questions:

1. is the content a kernel log at all - does it carry the fixed boot markers a
   Linux 4.19.113 boot always emits;
2. is it the *previous* boot rather than the current one - compare the boot id
   it reports against the live `/proc/sys/kernel/random/boot_id`;
3. does userspace-originated output reach it - does it contain `init:` records,
   which is what makes a PID1 banner viable.

Bounds and privacy. The content is a raw device log and may contain serials,
MAC/BSSID values, paths and KASLR slides. The journal publishes only digests
and matched predicates, never log text. The raw capture is retained under
`workspace/private/` at mode 0600 and is never committed. The read is bounded by
an explicit maximum above the 2,097,136-byte observed size, and a larger file
fails closed rather than truncating silently.

Ordering. The health guard, source binding, shared routine-actions guard,
no-replay rule and durable-intent-before-effect model are inherited unchanged
from the readiness D0 sibling. Predicate evaluation happens on the device so
that only bounded results cross the boundary; the digest of the whole file is
taken on the device and re-verified on the host against the retained capture.

### Unit 2 - P0 PID1 F1 V4 (the proof)

Only after unit 1 reports what the channel carries. The candidate's native PID1
writes one exact fixed banner to `/dev/kmsg` as its first action, so the banner
enters the printk path and therefore the sec_log buffer, with no USB, gadget,
ACM or networking dependency. The boot is expected to fail; that is acceptable,
because the F1 is boot-only with mandatory rollback already authorized.

Unit 2 also publishes the USB observer's terminal inventory - exact, pending and
conflicting identity counts - alongside its verdict. That is host-side journal
work with no additional device action, and it separates "enumerated with an
unexpected identity" from "never appeared", which the three consumed runs cannot
answer. The two instruments cross-check: an out-of-band log and an in-band
enumeration record.

After the authorized stock rollback and a healthy return, unit 1's instrument
reads `/proc/last_kmsg` and looks for the exact banner:

- banner present - native PID1 execution is proved directly, for the first time;
- banner absent but the log is a well-formed candidate-boot kernel log - PID1 did
  not reach its first instruction, which is a far sharper result than the three
  existing `NO_PROOF` outcomes;
- log absent or not the candidate boot - the channel did not survive the
  Odin/Download transition, and unit 2 has still cost no more than the F1 that
  the lane was going to spend anyway.

Every branch is informative. That is the property the previous three candidates
lacked.

## What is deliberately not claimed

The content of `/proc/last_kmsg` has never been read on this device. That it is
the previous boot's log is the standard sec_log semantic and is consistent with
the observed size, but it is unverified - which is precisely what unit 1 exists
to settle before unit 2 spends an F1.

Whether the buffer survives an Odin/Download transition is a different question
from surviving a warm reboot and is not settled by anything currently recorded.
Unit 2 tests it as a by-product; unit 1 cannot.

Enabling a real UART console is not an alternative. `CONFIG_SERIAL_MSM_GENI=y`
and `CONFIG_MUIC_SUPPORT_UART_SEL=y` are set, but
`# CONFIG_SERIAL_MSM_GENI_CONSOLE is not set`, `CONFIG_SEC_LOG_BUF_NO_CONSOLE=y`
and `CONFIG_CMDLINE=""` mean no console is attached to that UART. Changing it
requires a kernel rebuild that `GOAL_S20PLUS.md` records as unproven and whose
source is not staged.

## Disposition of the PMSG warm-reboot marker D1

Shelved dormant, not activated. Its second independent review returned blocking
findings on test fidelity and PATH-guard durability; closing them costs another
implementation and review cycle and still yields a channel that carries one
marker byte rather than a boot log. Its three documentation errors are corrected
separately as plain fact corrections, because they are wrong regardless of which
route the lane takes.
