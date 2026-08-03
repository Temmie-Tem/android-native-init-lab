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

Final direct validation passed 20 of 20 P2.98 tests. The whole
P2.82/P2.84/P2.86 boundary plus P2.98 focused closure passed 130 of 130. The
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

A second bounded Tier-2 repair preserves the inherited full-binary authority
validator while handling one compiler-generated false positive. The canonical
66,384-byte `init` at SHA-256
`e35e2a1d978d2c9f4af0d6b3ac254239324c6f503312107b1a5a89c91f702daa`
contains the printable bytes `/M9@`
across the boundary of one `ldrb` and one `cbz` instruction. The adapter first
runs the strict inherited validator, then permits an in-memory validation-copy
scrub only when the complete artifact hash and size, single occurrence at file
offset `0x5a51`, allocated `.text` bounds, aligned eight-byte instruction
window `e02f4d3940010034`, and unexpected-path set exactly `{/M9@}` all match.
It reruns the same inherited validator after the scrub. `/tmp`,
`/data/local/tmp/unauthorized`, path replacement, opcode mutation, another GCC
output, or another artifact hash still fail closed. No Tier-1 byte or candidate
intent changed.

Pre-Full-LTO qualification now passes on the qualified build PC before any
kernel build. The focused closure passes 130/130 and the exact shared
Process-v2 regression passes 110/110. The build host reports 33,662,164,992
bytes physical RAM, 12,884,893,696 bytes swap, and 37,085,384,704 bytes free
disk. A first attempt correctly failed closed because the inherited P2.84
ingestion receipt named a local GCC 15 path unavailable on the build PC. The
oracle was rerun host-only with the installed GCC 14 and exact pinned QEMU, then
qualification passed with 21 gates and SHA-256
`f3533d20ef3edc5c4feaf410296492820138dcd2c56861ee81be02fca78b89eb`.
The qualification still records `full_lto_started=false`.

The historical P2.96 Full-LTO A/B pair passes the new read-only six-function
audit with canonical disassembly digest
`0e889836181ffc156e34944880b329224c9c941408d5235b06b2ff5de41fe0bc`.
That is baseline evidence only.

Fresh P2.98 Full-LTO A/B construction now passes on the qualified build host.
The final clean pair used the content-identical relocated clang repository
under `workspace/private/work/toolchains`, inside the inherited debug-prefix
mapping. Build A and B respectively produced result receipts at SHA-256
`6f7c0900d656d187048af6993fff7a44fd400048b56a1c58bd9609240c037670`
and
`9012897753b95da8aece36885e10fa3acea2e1cd93f65702d8f53e1e2b4c7914`.
Both produced:

- 41,490,944-byte `Image`, SHA-256
  `689d71487788777e28efbdb48eb783462dde271f5af5a8ba0d2aa6348541ce87`;
- 476,979,440-byte `vmlinux`, SHA-256
  `3067680949754f7c5bd418136bc8c21cc9522f55aa8394a666fa0b21e1a2968d`;
- byte-identical `.config`, `System.map`, `vmlinux.symvers`, and `abi.xml`.

The A-before-B path gate found zero random private namespace occurrences and
zero absolute host clang-resource paths, with 138 mapped paths under
`/private-repo`. The final verifier returned
`PASS_P298_TWO_CLEAN_BUILD_REPRO_AND_LINKED_AUDIT_HOST_ONLY`. Its linked audit
proves the four probe targets remain out of line, both ordered EP0-enable calls
remain direct and checked, pullup overwrites the discarded gadget-start return
before direct run-stop, and resume immediately tests the signed return.

One earlier host-only A attempt failed closed before B because its invocation
omitted the already-required relocated `--clang-repo` and used the equal-byte
copy outside the mapped work-tree parent. The path gate detected the random
private namespace in clang-resource paths. That rejected result and its seven
evidence files remain marked `rejected-*` in private output; its reproducible
intermediate tree was removed. SOURCE_KEYS remained 136/136 with
`CHANGED_KEYS=[]`, no candidate was promoted, and the corrected clean pair used
the previously qualified layout.

## Independent review

A delegated independent reviewer found no Critical, High, Medium, or Low
execution-code finding and returned `PASS_GO` for the exact hash-bound Tier-2
repair. The review independently checked Tier-1 identity, the exact artifact
exception and mutation rejects, the 12-event
parser and same-run result contract, EP0 1/2-hit attribution, errno domain,
Tier-2 selector repair, linked call-shape audit, focused regressions, and the
boot-only/no-live-authority boundaries. The structured receipt names every
reviewed execution-critical byte. Its final current-policy and document hash
rebinding remains a pre-build gate.

This review, the passing pre-LTO receipt, and the completed fresh A/B closure
do not authorize packaging or device work. Capability reuse remains limited to
unchanged execution-critical and policy-context hashes with no new hazard or
incident.

This new host capability changes no partition boundary, recovery mechanism,
F1 runner, or target identity.
This report records completed host implementation and fresh Full-LTO closure,
not an F1-ready candidate. No promoted boot package or rollback binding exists
for P2.98. No device was contacted, no boot image was transferred, no live
authority was created, and the A90 target was untouched.
