# S22+ FYG8 R4W1-C No-Serial Physical-Continuity Source Host GO

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `SOURCE_GO_TO_NEW_LIVE_BINDING_PACKET`

Scope: host-only source correction, tests, static validation, full artifact
reopening, and independent read-only review after the serial-bound live gate
proved that normal FYG8 Download exposes no sysfs serial. No device was
enumerated or contacted during this correction. No ADB action, reboot, Download
transition, Odin transfer, flash, partition write, candidate consumption, or
live-policy activation occurred.

## Evidence Boundary

The prior live attempt proved exact topology `2-1.3`, Samsung Download product
`04e8:685d`, product string `SAMSUNG USB`, manufacturer `Samsung`, and direct
node `/dev/bus/usb/002/017`, with no sysfs `serial` attribute. It stopped before
candidate consumption and transfer. Exact FYG8 Android and Magisk health then
returned.

Without a Download-mode per-handset identifier, host software cannot
intrinsically distinguish a same-model substitute inserted at the same physical
port. The replacement therefore does not claim topology is device identity.
It binds every machine-observable property and explicitly retains one residual
trust assumption: the attending operator confirms that the same physical
handset, cable, hub path, and host port remain continuous.

## Replacement Contract

The source now enforces:

- exact Android ADB serial, `adb get-serialno`, Android sysfs serial, serial
  SHA256, and `adb get-devpath` agreement before reboot;
- exact Download topology, `04e8:685d`, `SAMSUNG USB`, and `Samsung`;
- mandatory Download sysfs serial absence, with serial presence fatal;
- stable arrival generation and complete direct-node tuple;
- usbfs pathname `/dev/bus/usb/<busnum>/<devnum>`, character major 189, and
  computed minor `(busnum - 1) * 128 + (devnum - 1)`;
- hardened Odin ticket equality and complete node snapshots before and after
  final sysfs reads at every transfer launch;
- recomputation of the Android serial digest at candidate consumption and
  recovery-state reopen;
- fresh physical-continuity confirmations for the candidate run, recovery,
  every rollback transfer, stock cleanup, ambiguous retry, and final exact
  Android return.

The consumed-state schema is
`s22plus_fyg8_r4w1c_consumed_v3` and records the physical-continuity basis.

## Stock Cleanup Boundary

Stock cleanup is not another branch of the Magisk confirmation. It requires a
separate fresh token after a definite Magisk `OdinCommandFailed`, then creates
an exclusive durable `rollback-stock-cleanup-intent.json` before stock launch.

Once that intent exists:

- the transaction is permanently non-PASS;
- built-in recovery stops before endpoint discovery or Odin launch;
- `_finish()` converts any attempted PASS into
  `FAIL_R4W1C_STOCK_CLEANUP_TAINTED`;
- direct intent and zero-or-one stock transfer log are hashed into transaction
  evidence; and
- a crash at or after intent requires a separately designed and reviewed
  recovery path.

This closes the window where an interrupted stock cleanup could later be
misclassified as an ambiguous Magisk transfer and recover to PASS.

## Exact Source Snapshot

```text
live helper
  size    100429
  SHA256  ce39196e58c6e7be83e8e8bcf7b56cb46e0e4ef22c05c1251f58b3310aae57ff

live focused test
  size    82033
  SHA256  b0e8112ffb926505d625f1feb9d5343d316d9d158386bee98cba641dc5ef0987

inactive live template
  size    12390
  SHA256  4bdba3b3cd2e08dd51f255c2a63bd6c160ee52235073686f150fdb375c47a3ca

binding packet generator
  size    11596
  SHA256  3d66c98423cbf5e3a7f5b6084a1f6c6f46d9f115e5692c57a935f16021e28381

binding packet focused test
  size    7111
  SHA256  8c8a4edc01fa1814946c2e1a424bef501cb87bad152e9a39084877011305ffbd

shared Odin core, unchanged
  SHA256  ab418aac5ce4c854f433e2132bd9536a610991384ec82c50dc0ba063f1888a9b

shared live core, unchanged
  SHA256  9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725
```

The generator pins the exact helper and focused-test identities. The template
identity is pinned by the helper and inherited by the generator.

## Independent Review

The existing `gpt-5.6-sol` xhigh read-only session
`019f7bc7-da2c-78c2-b172-2436e6a945d3` reviewed successive source snapshots.
It found and closed these blockers:

1. same-port substitution was overclaimed, usbfs identity was incomplete, and
   the Android serial digest was not recomputed at consumption;
2. physical-continuity confirmation ended at candidate transfer instead of
   spanning rollback and final Android return;
3. stock cleanup reused the Magisk confirmation instead of requiring separate
   authority; and
4. a crash after durable stock intent could enter ambiguous Magisk recovery and
   later reach PASS.

The final review found no HIGH, MEDIUM, or LOW finding and returned
`SOURCE_GO`. It specifically confirmed that pre-intent crashes grant no stock
authority, stock intent precedes launch and blocks built-in recovery before
Odin, completed stock transfer remains tainted, and uninterrupted stock cleanup
cannot produce PASS.

## Validation

```text
focused live test                         57 passed
binding packet focused test                7 passed
exact six-file relevant regression set   189 passed
ResourceWarning treated as error          PASS
py_compile                                PASS
git diff --check                          PASS
full 9.68 GB offline artifact gate        PASS
offline verdict                           PASS_R4W1C_LIVE_GATE_OFFLINE_CHECK
connected policy                          active
connected PASS                            present
live policy                               inactive/retired
candidate consumed                        false
device contact/write/reboot/flash         false/false/false/false
```

The exact six-file set is the R4W1-C live gate, R4W1-C binding packet,
R4W1-C connected gate, shared Odin transition core, shared boot-only live core,
and R4W1-B live regression. The count increased from 181 to 189 solely through
eight new R4W1-C focused tests.

The full gate reopened the exact candidate, Magisk rollback, stock cleanup,
Odin4, source pins, and FYG8 firmware ZIP SHA256
`f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`.

## Decision

Commit this host-only source checkpoint. While the live policy remains RETIRED,
the pinned generator may emit one new deterministic private binding packet from
the retained connected PASS. That exact packet and rendered clause require
independent review. Activation, post-activation qualification, and a fresh exact
operator acknowledgement remain separate later gates. This report grants no
device contact or live authority.
