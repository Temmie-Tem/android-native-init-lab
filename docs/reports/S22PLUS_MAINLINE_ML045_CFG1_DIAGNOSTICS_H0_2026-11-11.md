# ML045: distinguish the first CFG1 readback and budget failures

## Outcome and scope

The operator requested Argon analysis/discussion of ML044's HCI_CFG1 EIO,
then one next physical experiment, and correction of the reconnect caller's
invocation error before that run. Two bounded Gemini 4 Argon High discussions
completed. The V10 candidate records which original CFG1 branch is taken and
preserves its two reads, one write, short-circuited clock check and errno.
The capture CLI fixes the host-side API mismatch and is exercised before N.

ML044 remains consumed and closed healthy. Its retained authenticated result
is decoded with the changed checker and every field agrees with the stored
V9 result; interpreting those bytes as V10 fails. A90, S20+, the unrelated
candidate-manifest edit and attachment directory remain outside this unit.
The completion criterion is one reviewed V10 candidate, one separately
approved attended run, original-A healthy closure and an evidence-based report.
H0 success and review alone do not grant that physical operation.

## Source analysis and discussion

ML044 returned stage 6, PCS ready, HCE-started 1, EIO, zero local commands and
no link command. The exact retained source places that tuple at the first
`HCI_CFG1=0xdc` bit-0 readback-or-budget branch. Earlier exits precede the
HCE-started flag; later EIO sites follow at least one local-command increment.
The flag itself precedes the actual HCE-one write, so it is not enabled-state
proof. The 1.923-second host permit-to-result interval strongly favors a
readback failure, but does not establish the kernel's clock comparison.

The selected mainline and FYG8 Samsung headers both define `QUNIPRO_SEL` as
bit 0 at CFG1 offset 0xdc. Their mode-selection write has no immediate bit
readback assertion, and their surrounding initialization order differs from
this bounded module. Definition parity therefore does not prove our immediate
readback assumption is a hardware requirement. Conversely, the available raw
result does not justify deleting the check or diagnosing a broken aperture.
Cross-reset clearing, clock/gating and posted-write explanations remain
hypotheses. Source versions and supplied excerpts are retained by hash.

Argon's first response agreed on the source localization and proposed the
three-field diagnostic. A second challenge preserved original errno and
short-circuit evaluation, checked source-derived outcome constraints and
reviewed the fixed capture caller. Corrections rejected its inaccurate
36-field count (the actual change is 30+3=33), retry-oriented initialization,
zero-perturbation wording and a proposed additional waiting mechanism.
Static board initialization and existing single-probe/HCE latches suffice;
no retry is introduced. The final design promises unchanged MMIO/clock access
order and count, not instruction count or timing identity. Raw pre/post values
cannot prove write causality, electrical state or ML044's historical branch.

## Implementation

`G0Q_CFG1_DIAGNOSTICS` requires the complete V9 mode chain. The first pre-read
is stored, exactly that word OR bit 0 is written once, and the existing post-read
is stored. Bit 0 clear records outcome 1 and returns EIO without a clock read.
Otherwise the original clock check records outcome 2 and EIO on expiry, or
outcome 3 before the unchanged later HCE-one path. Zero-initialized outcome 0
means that this branch was not reached. The scalar fields are never reset to
make another attempt admissible.

The unsigned tag is `0xa0000000U`. Exactly three u32 decimal words follow the
existing 30 fields inside the same 256-byte authenticated envelope. The host
rejects mixed tags/counts, ranges and contradictory stage/PCS/HCE/guard/local/
link/result/errno histories. Outcome 1 leaves budget unavailable; outcome 2
means evaluated and expired; outcome 3 means that check passed, not successful
HCE enable or link completion. The guest's successful-link path requires the
matching outcome and set bit. A pre-effect certificate needs all extra words
zero. Original V1–V9 schemas and retained artifacts keep their provenance.

The existing reconnect CLI now accepts a prepared capture directory for a
fixed self-invocation. It uses the actual raw API's `stdout_maximum` and
`stderr_maximum` parameters, seals both streams/status before interpretation,
and never automatically retries or overwrites an existing capture. A final
capture-side deadline check suppresses actionable text if the original window
has 60 seconds or less left. It does not delete a cue or resolve its interlock.
Before N, a separate `capture-help` invocation exercises the same API and real
storage. Issue/resolution have distinct prepared directories and fixed argument
arrays; actual operator completion/cancellation remains required.

The shared policy, common details and selected target adopt the exact V10
artifact and capture behavior under one coherent review. No hardware access,
write, delay, barrier, predicate relaxation or new deadline is added. Kernel,
DT/configuration, overlay, rails/reset/PHY/UIC scope, 120/300/540/15 research
bounds, 555/570/660 automatic-return bounds, one N/original A and attended
physical fallback remain. Conditional unattended F1 remains inactive.

## Validation and review

Actual production HCI functions run on host and ARM64/QEMU with every MMIO and
clock access traced. V9 and V10 traces match for bit-clear, expired-budget,
passed-check and later HCE/command refusal cases; bit-clear skips the clock.
The same output passes the actual production formatter and authenticated host
consumer. A second invocation remains refused without reads/writes. Typed
negative tests cover inconsistent outcome/stage/PCS/latch/errno/word histories,
legacy tags and counts, signs and overrange words. Existing early HCE/ack
failure paths produce unobserved CFG1 diagnostics.

The real formatter, bounded reader and ARM64 guest accept the reachable
maximum-width successful record in 185 bytes with 33 fields. Real socket tests
cover all three CFG1 outcomes, early acknowledgement failures, pre-effect
refusal, successful link, load/read errors, malformed/partial packets and
expired/missing recovery controls. Existing one-A and health-only owner tests
cover V10 selection. The final capture CLI passes actual help/refusal, malformed
child JSON, timeout, overflow, spawn failure, late display and no-overwrite tests.
The actual final help probe completed in its prepared private directory.

The actual ARM64 module, observer, initramfs, loader and AP/boot envelopes were
built and qualified with the retained kernel/DT/configuration. Complete
producer reproduction and byte joins establish the fresh key-derived identity
and separation from consumed ML044. Module command records and disassembly
retain the intended mode and ordered accesses. No device transition is needed
to validate these host/build facts.

An initial H0 decoder test exposed an unbounded seven-field handoff unpack;
its slice now ends at the existing field 30 so V10's appended fields remain
separate. A test-edit script assertion and an incorrect test class invocation
were corrected with original failure logs preserved. No safety assertion or
device result was weakened. The artifact-check log's inherited ML044 print
label is cosmetic: its structured record and all joins bind the fresh ML045
candidate and V10 module.

The aggregate suite passed 159 tests without skips, including six actual
artifact cases. Fourteen touched Python files passed py_compile. Scoped
privacy/link checks, common-details digest and git diff checks passed. The
independent preliminary run passed 97 tests. A final policy reread found the
RAM policy's automatic-recovery successor list omitted V10; that one-line
routing addition is retained in packet 2, with unchanged executable, artifact
and test inputs. Final independent review returned PASS_GO with no findings
on packet `70a2166308f68cba5f7374fb1ed58ae185d200bcd8f1cad74094784e52e7ff8b`
and capability `ba99d891702c5cb6078fd99c03c9ab0c2043eb2d9156fbddb1be98e9ad77770f`.
The receipt is `3d66648c67c1bc8c5339f68f09e7d087b7c2f8655d3915cbc7878e2479375654`.
It independently verified 97 tests, 1,357 pin checks, complete artifact joins,
cue preflight and retained V9 parity. The v46 backend binding was published
with the stable worker unchanged and connected. Fresh exact ML045 qualification
and task preparation completed without a grant or operation. Fixed foreground
D0 passed all seven raw health reads with zero controls/transfers, no grant
and no operation. The exact returned approval and current physical attendance
with usable Download recovery are still required before dispatch.

## Evidence and external-model usage

Private evidence is under
`workspace/private/outputs/s22plus-ml045-cfg1-h0-20261111-1/`, including both
Argon prompts/responses/source pins, supplied source snapshots, usage captures,
discussion dispositions, module/build/artifact checks, old-raw parity, capture
preflight and test logs. Both calls selected `gemini-4-argon-high` with strict
permissions and no tool use. Provider totals are 50,730 input tokens, 17,837
output tokens (including 12,116 thinking tokens), and zero cache-read tokens.
The live weekly remaining meter moved from 91.05% to 89.66% to 89.18%.
These are account-level percentage points, not a per-call billing conversion.
Provider cost and subscription billing were not reported. Before/after quota
and token records were appended privately; no fallback model was used.

Past-failure applicability: ABI, SEMANTIC and WIRE are checked by exact source
mapping, actual ARM64 behavior and typed producer/consumer traces. IO, HOST,
ROUTE and PERSIST are checked by real self-capture and failure/raw preservation,
producer reproduction and byte joins. ARTIFACT and AUDIT retain the actual
old/new source versions and consumed V9 bytes. Rendering/display work is
inapplicable; notification is only a prompt, never completion or authority.
Physical readback branch and recovery remain unobserved until the separately
approved run. No new gate or evidence layer is created.
