# S22+ FYG8 P3.17 CDC-ACM topology-drift correction

Date: 2026-08-14 KST
Target: Samsung Galaxy S22+ FYG8 only
Status: **H0 DESIGN PASS_GO; NO LIVE AUTHORITY**

## Result first

The P3.17 candidate did enumerate on the host. The sealed sidecar proves one
high-speed USB device at `3-1.3`, under controller `0000:00:14.0`, with the
exact `04e8:6861` identity, the hash-bound candidate serial, `cdc_acm`, and
`ttyACM0`. The frozen candidate observer was bound to Download-era topology
`2-1.3`, under the different controller `0000:00:0d.0`. Both its exact match
and candidate-like match required that literal topology. It therefore selected
zero endpoints and never opened the TTY.

The operator now confirms that the cable/dock connection was physically moved
during the run. That statement explains the controller and path change but is
human evidence, not a fact manufactured from the sealed logs. The frozen
observer was therefore correct to refuse the new path. Its `endpoint-timeout`,
null endpoint identity, and zero-byte raw file mean “not selected,” not
“opened and read nothing.” For P3.17 only, the endpoint classification is
`exact-candidate-topology-drift`, and the effective proof class for that
experimental precondition is `NO_PROOF_EXPERIMENT_PRECONDITION`.
It does not reclassify earlier campaigns.

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

The host independently saw high-speed enumeration and CDC-ACM binding after
the physical topology changed. That proves that the candidate enumerated on
the later connection, but it is not a clean witness for the original
connection or for CONTROL1 causality. The two retained records are not
attributable to one boot, opcode `0x05` readback remains a register/firmware
observation rather than a direct switch-position witness, and physical
disconnect/reconnect is a competing cause. The MUX hypothesis is therefore not
resolved by host enumeration; the frozen physical-switch ceiling remains.

## Incident topology audit, not live selector authority

The H0 transition contract is implemented in
`workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_cdc_acm_endpoint_transition.py`.
It reopens the sealed P3.17 preparation, target, observer, sidecar, kernel,
udev, and frozen observer source. It derives one incident-specific drift:

```text
Download source: 2-1.3 / 0000:00:0d.0
Candidate target: 3-1.3 / 0000:00:14.0
```

The common suffix `1.3` is descriptive only. The controllers differ, so the
contract explicitly forbids inferring a generic companion relation from a
shared suffix or parent. The observed `3-1.3` path is incident evidence and
does not authorize selection. Only the original approved `2-1.3` path can
produce `selected-exact-approved-path` in the fixture model.

The positive fixture selects the exact identity only at the approved path.
The observed incident endpoint is classified as topology drift and is not
opened. Further negative fixtures reject:

1. the same suffix on another controller;
2. another Samsung device;
3. more than one exact candidate; and
4. a wrong identity occupying the approved path.

An exact candidate on any unapproved path is classified explicitly and is not
opened. This prevents the correction from turning a topology-precondition
failure into cross-device evidence contamination. The contract is a host-only
incident audit; it cannot qualify another host or run and supplies no live
selector transition.

Private receipt:

```text
endpoint-transition-20260814-01.json
size    9519
sha256  ce91779ce2f4aec95998fe982a21594092a4ca5d448d8082d565ce71f1118183
verdict PASS_P318_P317_PHYSICAL_TOPOLOGY_DRIFT_LOCALIZATION_H0
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
sha256  3911bd72177e32be10a78b50553436f96adcb418b69ed19a2cb88b350d0a280e
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
size    8386
sha256  81ed202b30c6513683354cb3054c30d093b64cb772a0da063a0058bfdbc92c9d
verdict PASS_P318_ENVELOPE_V4_TIMING_BANNER_BUDGET_DESIGN_H0_IMPLEMENTATION_REQUIRED
```

## Physical-topology continuity and rollback recovery

P3.17 proves that the Download-era endpoint binding is invalidated if the
operator moves the cable, dock, or host port before candidate observation
closes. The S22+ target contract now prohibits that movement from the initial
Download binding through rollback and verified final-health close. The named
gate is a permanent S22+ F1 boundary with no expiry; endpoint identity,
topology/controller capture, phase classification, recovery rebinding, or
selector changes trigger a new independent boundary review. It never widens
the live selector and the unapproved endpoint is not opened.

The same mismatch also invalidates the old rollback endpoint binding. It is
therefore not enough to say that rollback “continues.” Mandatory rollback
remains required, but the run must park without new effects until a
bounded, independently reviewed recovery-only path re-establishes one exact
current Download/rollback endpoint. Only then may the predeclared exact
rollback resume from the durable journal. The endpoint is carried by a new
immutable recovery binding ID and may differ from the start path; it is
recovery authority only and cannot reclassify the experiment result. Candidate
replay remains forbidden.

A successor records three path boundaries: approved Download start,
candidate-observer end, and fresh rollback Download. Each includes the
endpoint identity, topology, controller/device-path digests, match count, and
an immutable raw-snapshot size/hash made from the same bytes that are parsed.
Each record carries its binding ID, comparison binding ID, relationship to the
start path, and authority state. Classification is phase-specific:

- Download-start non-exact/absent/ambiguous is a pre-session stop with no
  consumed-run proof class; unreadable evidence is a pre-session observer
  failure.
- Candidate-end drift or ambiguity is experiment-precondition no-proof. An
  exact complete same-path window with no host endpoint and a causal-ready
  device terminal remains an evaluable host-silent device result. Other absent
  or unavailable cases are observer no-proof.
- Rollback Download accepts only `reestablished_exact` under the fresh recovery
  binding ID. Every other state parks recovery without changing the retained
  experiment result. Relationship to the start path is evidence only.

A path mismatch can prove drift, but it cannot manufacture proof that a person
physically moved the cable.

## Timing correction and Envelope-v4 budget

The host sidecar's `armed.json` is not the candidate-internal “sidecar arm
proof” in the runtime ordering. It was published before the candidate flash
completed. Candidate enumeration occurred about 53.2 seconds after flash
completion, but boot, the 69-module early load, gadget setup, diagnostic load,
and the 30-second dwell all fit inside that interval. The retained host events
cannot distinguish gadget-ready enumeration from post-CONTROL1 enumeration.

Extending the existing sidecar window is not sufficient. Its sealed result
shows that kernel and udev capture continued until `17:08:53Z`, roughly 250
seconds after the candidate enumerated, while the kernel log contains no later
USB event. Absence of a later event supplies no post1 or post2 timestamp.
Gadget readiness is also not a host anchor: the host may enumerate an
arbitrary time later.

The successor instead latches the first actual host-caused device event —
`RESET`, `CONNECT_DONE`, or `SETUP` — on the same device monotonic clock as
`pre`, `write`, `post1`, and `post2`. No host/device wall-clock synchronization
is needed. `pre` is the zero origin and four signed 32-bit microsecond deltas
represent all five samples. A validity mask distinguishes a missing host event
from a zero delta. If the host-event delta precedes the write delta, host
traffic existed before the MUX write. If write precedes the event, the write
preceded first host traffic but causation is still not proved. Equality,
missing data, or clock-source mismatch permits no MUX causal claim.
The four device samples are mandatory and ordered
`pre <= write <= post1 < post2`; only validity masks `0x0f` (no host event) and
`0x1f` (one latched host event) are legal. A clock read failure is an observer
failure, not a device result.
The current 1,200-second guard fits the signed-delta range, but the Python
design constant is not execution authority. Successor qualification must bind
the actual Process-v2 guard and prove it does not exceed 2,147.483647 seconds.

Envelope-v3 has no generic free 44-byte region. Its fixed geometry is 128-byte
Carrier/envelope = 48-byte metadata + 76-byte payload + 4-byte CRC. Envelope-v4
reserves 18 payload bytes for the validity mask, host-event kind, and four
signed deltas, plus 3 bytes for banner outcome, byte count, and error class.
The prefix is therefore 21 bytes and the lossless PackBits poll capacity falls
from 76 to 55 bytes. The existing 44-byte overflow summary (SHA-256 32 + OR 4
+ poll0 4 + nonzero-count 4) occupies 65 bytes with the prefix and leaves 11
zero-reserved bytes. Overflow remains non-causal. The 55/56-byte boundary,
five timing samples, banner outcomes, and same-clock ordering must all
cross the real encoder, Carrier, and host decoder before any successor use.

## Validation and remaining boundary

The three focused P3.18 modules pass 32/32 and the documentation/receipt
binding module passes 6/6, for a 38/38 unit total after the Envelope-v4 and
topology-continuity receipts are regenerated. Python compilation passes. No
device command, USB open, reboot,
Odin invocation, payload, partition transfer, candidate replay, recovery
action, A90 action, or S20+ action occurred.

Independent review first returned `CHANGES_REQUIRED`: the topology gate lacked
permanent-boundary metadata, one phase-insensitive state table collapsed
device results and recovery states, recovery lacked a fresh binding identity,
and the table was descriptive rather than executable. The corrected closure
uses a total 180-row classifier over phase, relationship, authority, snapshot
completeness, and causal-terminal readiness. Independent re-review found zero
oracle mismatches, rejected all three policy mutations, independently
reproduced both private receipts byte-for-byte, and returned:

`PASS_GO — S22PLUS_FYG8_P318_TOPOLOGY_TIMING_DESIGN_H0_CAPABILITY_V1`

P3.18 is not candidate-ready. No live selector transition is authorized, the
new banner/timing envelope encoder/decoder has not been implemented, and no
package or Process-v2 binding exists. The target-contract recovery-boundary
change has passed independent review. This H0 design capability grants no D0,
D1, F1, recovery, or live authority.
