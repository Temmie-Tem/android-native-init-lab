# S22+ FYG8 P3.17 CDC-ACM topology-drift correction

Date: 2026-08-14 KST
Target: Samsung Galaxy S22+ FYG8 only
Status: **H0 DESIGN PASS_GO V2; CANDIDATE-NOT-READY; NO LIVE AUTHORITY**

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
size    10589
sha256  fbaa41713b606c8d8757d59752bd4fd07ba221fdb0576b2b46265334af3dbe8a
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
invalid returns, but it returns no successful byte count to P3.17. Its deadline
is not an absolute attempt deadline: the `EINTR` branch loops before any clock
check, so an interrupt storm can extend the attempt without bound.

Consequently, the retained P3.17 data cannot distinguish a successful 49-byte
gadget write from timeout, errno, or partial delivery. Adding a stage after the
call cannot repair that: the Carrier is already closed.

The P3.18 design contract therefore requires this order:

```text
prove gadget and observer evaluability
-> initialize one five-second absolute monotonic deadline
-> make one banner attempt whose EINTR, EAGAIN, and short-write loops all use it
-> retain outcome, normalized error class, and bytes written
-> encode a new terminal envelope
-> publish the retained terminal for every outcome
-> park without a second banner attempt
```

The outcomes are `written`, `eagain_timeout`, `failure`, and `partial`.
`written` requires exactly 49 bytes; partial coverage includes both boundary
counts 1 and 48. Zero-byte `zero_write` and `invalid_short_write` returns map to
`failure`; the same causes after progress map to `partial`. The valid terminal
domain contains 344 rows and has no unclassified zero-byte state. The absolute
deadline is initialized once, checked before every write or retry, covers
`EINTR`, `EAGAIN`, and every short-write continuation, and caps sleeps to its
remaining duration. A written result proves only that the device accepted all
49 bytes into the gadget write path. It does not prove host selection, open,
or receipt. Failure of the banner attempt must not suppress the Max77705
terminal.

This requires a new envelope version. Reinterpreting reserved Envelope-v3
bytes is forbidden; the fixed 128-byte Carrier size remains unchanged. Before
any successor device use, every positive outcome and negative invariant must
pass the real encoder, Carrier, and host decoder, followed by packaging and an
independent changed-closure review.

Private receipt:

```text
banner-result-contract-20260814-01.json
size    14730
sha256  e14efb29cfaaeee7de35452033ce3c789391befaeefe88c2002ddba277308f2d
verdict CHANGES_REQUIRED_P318_HOST_EVENT_PRODUCER_NOT_IMPLEMENTED_H0
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
- Normal rollback accepts `rollback_bound_exact` when a fresh revalidation of
  the predeclared rollback binding is complete and the path is unchanged. It
  does not require a new independent recovery review.
- After drift, rollback accepts only `recovery_rebound_exact` under a fresh,
  independently reviewed recovery-only binding ID. It may name the same or a
  different current path. Every other state parks recovery without changing
  the retained experiment result.

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

The first design named `RESET`, `CONNECT_DONE`, and `SETUP` dispatch seams but
did not name any candidate component able to retain them. That was an
executability gap, so the earlier design `PASS_GO` is withdrawn.

The fixed source exposes a module-only route that does not require an Image
patch, kprobe, tracefs, or trace-clock synchronization. `dwc3_process_event_entry()`
calls `trace_dwc3_event(event->raw, dwc)` before endpoint or device dispatch;
`trace.c` exports `dwc3_event` with `EXPORT_TRACEPOINT_SYMBOL_GPL`; the fixed
`trace.h` callback ABI supplies both `u32 event` and `struct dwc3 *dwc` and
captures `dwc->ep0state`; the fixed
P3.10 Image config (`6adf58c7204695e6f5a8deaf0f5995bca91a79ce4cc5f7b74e7b247128e0673b`)
has `CONFIG_TRACING=y`; and `ktime_get()` is GPL-exported. A future
early custom latch module can therefore register the tracepoint, filter exact
`a600000.dwc3`, decode the first RESET/CONNECT_DONE/EP0-SETUP completion, and
sample `ktime_get_ns()` as the first actual host-caused device event. The late
Max77705 diagnostic must use the literal same
primitive for `pre`, `write`, `post1`, and `post2`.

This route is selected but not implemented. The latch module must load and
prove exact-target registration before configfs exposes the gadget; only then
may the 69 stock early-module plan, gadget activation, and late diagnostic
sequence proceed. That changes the future package shape to one early custom
latch plus the 69 stock early modules, followed by the inherited late
diagnostic. Release/acquire publication must prevent a torn event kind/time.

`pre` remains the zero origin, but the six samples are now latch-install,
pre, write, post1, post2, and first host event. Five signed 32-bit microsecond
deltas are required. Bit 5 authenticates the install sample. The only
causal masks are `0x2f` (armed latch, no host event) and `0x3f` (armed latch,
host event). Legacy `0x0f` means “host event not observable,” never “no host
event.” Even `0x2f` is legal only when registration/arming preceded gadget
exposure, latch-install is no later than pre, and the complete host receipt has
no endpoint. Endpoint-present plus `0x2f` is an observer contradiction. The
candidate decision path must execute this timing/host-receipt cross-check
before retaining any topology result. An incomplete receipt cannot authorize
the no-event reading. Conversely, `0x3f` plus a complete no-endpoint receipt
means the host reached DWC3 but no host endpoint survived the observation; it
is retained separately as `DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT`, never
collapsed into host-silent.

If the host-event delta precedes the write delta, host traffic existed before
the MUX write. If write precedes the event, the write preceded first host
traffic but causation is still not proved. Equality, missing install/event
authority, host-receipt contradiction, or clock-source mismatch permits no MUX
causal claim. The current 1,200-second guard fits the signed-delta range, but
the Python design constant is not execution authority. Successor qualification
must bind the actual Process-v2 guard and prove it does not exceed
2,147.483647 seconds.

Envelope-v3 has no generic free 44-byte region. Its fixed geometry is 128-byte
Carrier/envelope = 48-byte metadata + 76-byte payload + 4-byte CRC. Envelope-v4
reserves 22 payload bytes for the validity mask, host-event kind, and five
signed deltas, plus 3 bytes for banner outcome, byte count, and error class.
The prefix is therefore 25 bytes and the lossless PackBits poll capacity falls
from 76 to 51 bytes. The existing 44-byte overflow summary (SHA-256 32 + OR 4
+ poll0 4 + nonzero-count 4) occupies 69 bytes with the prefix and leaves 7
zero-reserved bytes. Overflow remains non-causal. The 51/52-byte boundary,
six timing samples, banner outcomes, and same-clock ordering must all
cross the real encoder, Carrier, and host decoder before any successor use.

The one-byte banner error field now has an explicit mapping. `EAGAIN` deadline,
`EPIPE`, and `ENODEV` are pairwise distinct; `ETIMEDOUT`, zero write, invalid
short write, and other errno have separate declared classes. The implementation
must source-bind `sizeof(p260_banner) - 1 == 49`, statically prove it is at most
`UINT8_MAX`, and reject rather than saturate an out-of-range byte count. The
absolute attempt deadline must be new implementation work; the inherited
helper's EAGAIN-only deadline is explicitly insufficient.

## Validation and remaining boundary

The corrected classifier has 240 input rows and 12 decision partitions after
input echoes are removed from the partition digest. Its independent
input-to-decision oracle is exercised by branch/output mutations rather than
only by mutating a policy dictionary. The mask/install/event/receipt audit
also covers 36,864 inputs and eight timing decisions, including receipt
completeness. Corrected focused tests
pass 46/46, the common Process-v2 regression passes 120/120, and
both changed private receipts were regenerated from the current sources. No
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
reproduced both private receipts byte-for-byte, and returned the now-withdrawn:

`PASS_GO — S22PLUS_FYG8_P318_TOPOLOGY_TIMING_DESIGN_H0_CAPABILITY_V1`

A later adversarial review found the missing event producer, the favorable
late-latch/no-event ambiguity, overloaded rollback authority, tautological
180-row uniqueness metric, and policy-copy “oracle.” Those findings are valid.
The first review of the resulting correction found three more gaps: host-event
plus endpoint-absent still collapsed into host-silent, the inherited helper's
EINTR path escaped the claimed five-second bound while zero/invalid zero-byte
returns had no terminal row, and `trace.h` was not a receipt input. This
revision separates the DWC3-event/no-endpoint result, adds receipt completeness
to the exhaustive cross-product, specifies a once-initialized absolute
deadline and a total 344-row banner domain, and binds the callback ABI and
`ep0state` through the exact `trace.h` bytes.

Fresh independent review of commit `4f54675d1a` regenerated both receipts,
rejected the host-event/endpoint and receipt-completeness counterexamples over
the 36,864-row audit, proved the valid 344-row banner domain plus 56 rejected
rows, and mutation-tested the exact `trace.h` ABI. Focused 46/46, Process-v2
120/120, and extended common 167/167 (one skip) passed. It returned:

`PASS_GO — S22PLUS_FYG8_P318_TOPOLOGY_TIMING_DESIGN_H0_CAPABILITY_V2`

P3.18 is not candidate-ready. No live selector transition is authorized, the
new banner/timing envelope encoder/decoder has not been implemented, and no
package or Process-v2 binding exists. The target-contract recovery-boundary
change and design are qualified only at the exact V2 H0 closure. The component
banner receipt deliberately remains `CHANGES_REQUIRED` until the producer,
absolute-deadline helper, real Envelope-v4 path, and package exist. This H0
PASS grants no D0, D1, F1, recovery, or live authority.
