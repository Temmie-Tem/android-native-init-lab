# S22+ FYG8 P2.98 gadget-start and event attribution (H0)

Date: 2026-08-03

## Outcome

P2.98 implements the closed successor contract
`s22plus-fyg8-p298-gadget-start-event-attribution-v1` without changing any
P2.96 `SOURCE_KEY`. It extends the inherited isolated bind observer from seven
to 12 events:

- `__dwc3_gadget_start` entry and signed return;
- entry-only `__dwc3_gadget_ep_enable`;
- `dwc3_gadget_reset_interrupt` entry; and
- `dwc3_gadget_conndone_interrupt` entry.

Adding the EP-enable entry is a bounded marginal change to the existing trace
descriptor, parser counter, and exact profile comparison. It removes the
otherwise likely follow-up F1 needed to distinguish the two EP0 command edges:
one hit before a negative return means EP0-OUT failed, while two mean EP0-IN
failed. The exact source proves two ordered calls through `err0` and `err1`,
and restricts the expected negative return domain to `-EINVAL`, `-EAGAIN`, and
`-ETIMEDOUT`.

## Same-run result contract

| Observation | Retained meaning |
|---|---|
| setup control unavailable | `0xf60` |
| event registration unavailable | `0xf61` |
| setup cleanup unverified | `0xf62` |
| bind snapshot read failed | `0xf63` |
| gadget-start not reached / no return / positive return | `0xf64` / `0xf65` / `0xf66` |
| EP-enable hit contradiction | `0xf67` |
| EP0-OUT expected errno | `0xf68` through `0xf6a` |
| EP0-IN expected errno | `0xf6b` through `0xf6d` |
| unexpected negative errno / trace-source contradiction | `0xf6e` / `0xf6f` |
| final readback / cleanup / profile mismatch | `0xf70` / `0xf71` / `0xf72` |
| successful A event/link family | `0xd00` through `0xd3f` |
| successful B terminal family | `0xe00` and above, including `0xe50` through `0xe53` configured/high |

The observer remains active through the bounded final wait. RESET and
CONNECT_DONE events are attributed to the exact `dwc` pointer captured at
gadget-start entry. Before any successful A/B pair is published, the runtime
disables and reads the instance, verifies cleanup, parses the final trace, and
requires exact equality with every profile hit counter. Therefore the final
A/B family itself implies `probe_armed == 1`, `start_rc == 0`, exactly two
EP-enable hits, exact trace/profile agreement, and verified cleanup. This is
required because the two retained slots overwrite earlier setup checkpoints.

P2.96 is explicitly adopted as the historical no-probe behavioral baseline.
A dedicated control F1 is not planned. That decision reopens only for
unexplained prefix or tuple drift, a probe-provenance contradiction, a new
device-health anomaly, or a new hazard class. Probe registration proves
installation, not absence of observer effect.

## Host and linked closure

The generated-C host harness executes the real parser and classifier across
zero, OUT-negative, IN-negative, RESET/CONNECT_DONE, missing return, wrong
controller, duplicate, wrong-PID, counter-order, and profile-mismatch cases.
The broader closure exhausts 32,256 raw final-state inputs and 112
gadget-start result inputs against the Python source of truth. The generated
userspace links twice as the same static AArch64 binary.

The linked audit is no longer symbol-presence-only. For both actual Full-LTO
images it requires:

- out-of-line copies of all four probe targets;
- exactly two direct EP-enable calls from gadget-start, with the first failure
  skipping the second and both returns checked;
- exactly one direct pullup call whose `w0` is overwritten before direct
  run-stop; and
- exactly one direct resume call whose signed return is tested immediately.

Synthetic fixtures reject missing/inlined calls, LLVM clones, tail calls,
return-consuming pullup code, a one-call EP chain, and A/B divergence. A
read-only replay over the historical P2.96 Full-LTO pair confirms that the
source-level call shapes survive in the available linked baseline; the fresh
P2.98 pair remains subject to the same mandatory audit.

## Validation and authority

Final focused validation passed 18 of 18 P2.98 tests. The inherited
P2.82/P2.84/P2.86 boundary plus P2.98 tests passed 128 of 128. The
implementation closure reports 136 Tier-1 source keys, 13 generated artifacts,
a 45-byte two-slot ABI, 107 positions, 12 bind events, and a reproducible
static AArch64 userspace executable. The pre-intent and post-repair freezes both
report `CHANGED_KEYS=[]`.

One bounded Tier-2 repair was required after intent derivation. The inherited
selector used by downstream candidate checks did not recognize the new P2.98
contract even though intent creation had registered it in its own process. The
P2.98 candidate-contract adapter now installs the exact selector mapping for
each downstream process. No Tier-1 byte changed, candidate identity stayed
fixed, the corrected candidate contract passed, and two userspace builds
reproduced the same static AArch64 outputs: 66,384-byte `/init` at SHA-256
`e35e2a1d978d2c9f4af0d6b3ac254239324c6f503312107b1a5a89c91f702daa`
and 720-byte child at SHA-256
`9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639`.

Pre-Full-LTO qualification stopped before a kernel build. The exact shared
historical suite passed 108 of 110; the two failures are stale A90-only
documentation expectations, while the S22+ P2.98 documentation assertion
passes. Target isolation forbids repairing A90 state as part of this unit. The
authoritative resource predicate also reports 16,317,992,960 bytes physical
RAM against 32,212,254,720 required. Swap (17,179,865,088 bytes) and free disk
(41,104,457,728 bytes) pass. The resource gate was not bypassed and Full-LTO
was not started.

The historical P2.96 Full-LTO A/B pair passes the new read-only six-function
audit with canonical disassembly digest
`0e889836181ffc156e34944880b329224c9c941408d5235b06b2ff5de41fe0bc`.
That is baseline evidence only. Fresh P2.98 Full-LTO A/B construction and its
postbuild audit remain mandatory on a qualified host after the shared
regression gate is current.

## Independent review

A delegated independent reviewer found no Critical, High, Medium, or Low
finding and returned `PASS_GO` for the exact hash-bound P2.98 H0 host
capability. The review independently checked Tier-1 identity, the 12-event
parser and same-run result contract, EP0 1/2-hit attribution, errno domain,
Tier-2 selector repair, linked call-shape audit, focused regressions, and the
boot-only/no-live-authority boundaries. The structured receipt names every
reviewed execution-critical byte and the higher-precedence policy context.

This review does not convert the 108/110 shared regression result into PASS,
waive the physical-RAM gate, substitute the historical A/B replay for fresh
P2.98 Full-LTO images, or authorize packaging or device work. It is reusable
only while its named hashes and hazard assumptions remain unchanged.

This new host capability changes no partition boundary, recovery mechanism,
F1 runner, or target identity.
This report records a host implementation parked before mandatory fresh
Full-LTO closure, not an F1-ready candidate. No device was contacted, no boot
image was packaged or transferred, no live authority was created, and the A90
target was untouched.
