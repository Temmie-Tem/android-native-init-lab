# S22+ FYG8 P3.17 CDC-ACM endpoint-selector correction

Date: 2026-08-14 KST
Target: Samsung Galaxy S22+ FYG8 only
Status: **H0 IMPLEMENTED; INDEPENDENT REVIEW PENDING; NO LIVE AUTHORITY**

## Result first

The P3.17 candidate did enumerate on the host. The sealed sidecar proves one
high-speed USB device at `3-1.3`, under controller `0000:00:14.0`, with the
exact `04e8:6861` identity, the hash-bound candidate serial, `cdc_acm`, and
`ttyACM0`. The frozen candidate observer was bound to Download-era topology
`2-1.3`, under the different controller `0000:00:0d.0`. Both its exact match
and candidate-like match required that literal topology. It therefore selected
zero endpoints and never opened the TTY.

The P3.17 `endpoint-timeout`, null endpoint identity, and zero-byte raw file do
not mean that the observer opened the candidate TTY and read no bytes. They
mean that the observer did not select or open the enumerated candidate at all.
For P3.17 only, the corrected host classification is
`exact-candidate-on-unrecognized-topology`.

This does not change the official campaign-level no-proof result. Two
byte-identical retained records still violate the frozen single-result
contract. The operator reports that a physical-button misoperation caused the
action to occur twice; that is consistent with two executions, but the
retained records lack a per-boot identity and do not independently prove their
origin. The original transfer counts, healthy recovery close, multiplicity
terminal, and no-replay rule remain unchanged.

## What the live run established

P3.17 crossed the P3.16 executability blocker:

- all three provider masks were bound before and after the diagnostic;
- `waiting_for_supplier` was present and zero;
- the diagnostic owned the exact parent and exactly one `0x25` client;
- `causal_ready=true`, probe entry was retained, and all four commands and
  responses were present;
- CONTROL1 was `0x3f` before the command, `0x09` after it, and `0x09` after the
  30-second retention boundary; and
- no post2 detection latch was retained.

The host independently saw high-speed enumeration and CDC-ACM binding. That
proves that the candidate's USB2 data path physically conducted well enough
for enumeration. It does not prove that the CONTROL1 command caused the
physical path to move: the two retained records are not attributable to one
boot, and opcode `0x05` readback remains a register/firmware observation rather
than a direct switch-position witness. The simple claim that the run was
silent because the MUX stayed open is no longer supported, but the frozen
physical-switch ceiling remains.

## Exact transition authority, not a generic companion rule

The H0 transition contract is implemented in
`workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_cdc_acm_endpoint_transition.py`.
It reopens the sealed P3.17 preparation, target, observer, sidecar, kernel,
udev, and frozen observer source. It derives one incident-specific transition:

```text
Download source: 2-1.3 / 0000:00:0d.0
Candidate target: 3-1.3 / 0000:00:14.0
```

The common suffix `1.3` is descriptive only. The controllers differ, so the
contract explicitly forbids inferring a generic companion relation from a
shared suffix or parent. Only the exact sealed P3.17 path pair and exact
candidate identity authorize selection in this replay audit.

The positive fixture selects exactly one candidate at the authorized target.
The negative fixtures reject:

1. the same suffix on another controller;
2. another Samsung device;
3. more than one exact candidate; and
4. a wrong identity occupying the authorized path.

An exact candidate on any unregistered path is classified explicitly and is
not opened. This prevents the repair from turning a timeout into cross-device
evidence contamination. The contract is a host-only incident replay; it is
not yet wired into the live observer and cannot qualify another host or run.

Private receipt:

```text
endpoint-transition-20260814-01.json
size    3998
sha256  8f0ff7c015dbc4c8ee27d81f497ae16bc38b73863785d8bd6fbb165b154e5f03
verdict PASS_P318_P317_ENDPOINT_SELECTOR_LOCALIZATION_H0
```

## CDC-ACM positive control

The positive control deliberately closes two real seams without claiming an
end-to-end environment that was not run:

1. the sealed QEMU receipt proves the exact 49-byte pre-bind banner traversed
   the Linux `dummy_hcd` / `u_serial` / `cdc_acm` path and arrived at
   `ttyACM0`; and
2. the current real Python observer is executed against a kernel PTY after the
   same exact 49 bytes are queued before observer open; it selects, opens,
   reads, validates, persists, and reopens those bytes.

The source-derived banner SHA-256 is
`e9e1fed41d67f018747299177d7e6b9c919ceae124e00b38508769f9496a55f7`
at both seams. This is a transitive two-seam control, not the Python observer
running inside QEMU, and its synthetic healthy guard is not the real root
udev/ModemManager guard.

A fresh QEMU attempt was also made host-only. It stopped before guest start
because the pinned QEMU binary tried to load incompatible host GUI/audio
modules. That failed attempt is private evidence only and is not cited as the
positive result. The accepted positive control reopens the earlier sealed QEMU
PASS and verifies that its runtime and C-harness hashes still equal the current
sources before joining it to the freshly executed Python-observer seam.

Private receipt:

```text
cdc-acm-positive-control-20260814-01.json
size    2387
sha256  8aefa209527611fe7644ea6589598d9e6752af968bac744334eb9d7ebcc6a61c
verdict PASS_P318_CDC_ACM_TWO_SEAM_POSITIVE_CONTROL_H0
```

The DTR explanation is rejected. Fixed `f_acm.c` stores the handshake bits but
does not enforce DTR before data flow, and fixed `u_serial.c` queues bytes and
starts TX whenever the USB port is present. DTR must not be carried forward as
the P3.17 explanation.

## Banner-result blind spot and successor contract

The active materialized path is
`p290_e3_run -> p317_run -> p317_publish`. In `p317_publish`, the retained
terminal is committed first, then `p260_write_banner(tty_fd)` is called with a
discarded return value, then the runtime parks. There are three discarded
banner calls in the complete materialized file, including the one active P3.17
publisher call. The inherited `p260_write_all()` retries `EINTR`, bounds
`EAGAIN` with a deadline, handles short writes, and rejects nonpositive or
invalid returns, but it returns no successful byte count to P3.17.

Consequently, the retained P3.17 data cannot distinguish a successful 49-byte
gadget write from timeout, errno, or partial delivery. Adding a stage after the
call cannot repair that: the Carrier is already closed.

The P3.18 design contract therefore requires this order:

```text
prove gadget and observer evaluability
-> make one five-second bounded banner attempt
-> retain outcome, normalized error class, and bytes written
-> encode a new terminal envelope
-> publish the retained terminal for every outcome
-> park without a second banner attempt
```

The outcomes are `written`, `eagain_timeout`, `errno`, and `partial`.
`written` requires exactly 49 bytes; partial coverage includes both boundary
counts 1 and 48. A written result proves only that the device accepted all 49
bytes into the gadget write path. It does not prove host selection, open, or
receipt. Failure of the banner attempt must not suppress the Max77705 terminal.

This requires a new envelope version. Reinterpreting reserved Envelope-v3
bytes is forbidden; the fixed 128-byte Carrier size remains unchanged. Before
any successor device use, every positive outcome and negative invariant must
pass the real encoder, Carrier, and host decoder, followed by packaging and an
independent changed-closure review.

Private receipt:

```text
banner-result-contract-20260814-01.json
size    4194
sha256  e15af9b96dc7109297babd482ddd4ca4e1cb6f435f6c27a9a7e3903fbc36b57a
verdict PASS_P318_BANNER_RESULT_DESIGN_H0_IMPLEMENTATION_REQUIRED
```

## Validation and remaining boundary

The three new focused modules pass 22/22, including the three requested
selector negatives, source-seam mutations, and banner ordering/write-helper
mutations. A separate documentation/receipt binding module passes 5/5, for a
27/27 P3.18 unit total. Python compilation passes. No device command, USB open, reboot,
Odin invocation, payload, partition transfer, candidate replay, recovery
action, A90 action, or S20+ action occurred.

P3.18 is not candidate-ready. The live selector has not been changed, the new
banner envelope/encoder/decoder has not been implemented, and no package or
Process-v2 binding exists. Independent review is still required. This H0 unit
grants no D0, D1, F1, recovery, or live authority.
