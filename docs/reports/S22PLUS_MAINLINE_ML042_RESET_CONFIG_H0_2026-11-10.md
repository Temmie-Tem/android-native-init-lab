# ML042: dedicated UFS reset configuration and V7 preparation

## Bounded change

The operator requested Mythos analysis/discussion and the next attended physical
experiment after ML041. This unit replaces the ungrounded generic output-enable
interpretation at the four existing UFS reset-pin checks. V7 requires whole-word
CTL `0x0000000b` and keeps the existing IO bit-0 high-latch predicate. It adds no
CTL write, MMIO read, reset pulse, status clear, retry or timing extension.
The existing HCE stop, later UFS path and automatic Download attempt remain.
All artifact, policy and source changes are H0 until independent review, fresh
qualification, current health and the exact returned attended grant complete.
A90 and S20+ are outside this unit.

## Evidence and interpretation

[ML040](S22PLUS_MAINLINE_ML040_RUN_2026-11-10.md) observed CTL `0xb` after its
same-boot witness and refused before reading IO or stopping HCE. Its output-
enable test required bit 31 set. The exact retained SM8450 table declares
`oe_bit=-1`, `in_bit=-1`, `out_bit=0`; the unsigned five-bit C fields turn the
sentinels into 31. Generic direction/get paths use that value without a special
sentinel check. Reproducing this generic behavior does not establish hardware
direction semantics for the dedicated pad.

The separately hash-verified Samsung base archive has the same dedicated layout,
field widths and generic behavior. The FYG8 differential replaces none of the
five inspected pinctrl/UFS source files. The Samsung reset consumer uses a GPIO
descriptor and logical levels. This is source evidence, not a claim of an exact
shipped-binary MMIO readback. The previously reviewed FYG8 tree maps active-low
line 210 to the same CTL/IO addresses. The actual research DTB has TLMM and the
UFS host disabled and no reset-gpios property on that host; its module accesses
the fixed eight-byte window directly.

An independent implementation clarifies the sentinel convention: the pinned
[U-Boot special-pin GPIO consumer](https://github.com/u-boot/u-boot/blob/ecdcf9e365df6249a57cd8cc946e7026804ff4ae/drivers/gpio/msm_gpio.c#L97)
writes the output register and skips direction control when the OE field is
sentinel-valued; its get-function branch explicitly treats that as no OE
register. This supports the table-format interpretation. It is not an SM8450
register specification or electrical measurement for this board.

V7 therefore binds the complete **ML040-observed configuration**, not an inferred
firmware origin, measured current, output direction or pad voltage. Any CTL
drift, including `0x8000000b`, refuses. IO upper bits are unspecified and remain
preserved by the existing pulse RMW. A passed check proves a sampled high latch
bit, not whole IO equal to 1 or a physically high reset line. A failed latch
check proves only failure of that admission condition.

## Implementation and proof boundaries

`reset-pin.h` supplies one predicate definition to both kernel translation units.
Their actual compile-command receipts show identical V7/handoff/return defines.
Preprocessor checks reject an incomplete mode combination; the artifact build
receipts separately establish consistency across objects. The four call sites
retain their individual read order, short-circuiting and budget checks: HCE
pre-admission, stage-two cold/post-stop, and stage three before/after GCC reset.
No generic TLMM device or pin configuration writer is enabled.

The report remains 30 fields within 256 bytes, with tag `0x70000000`. V7 alone
names indices 10/11 RESET_CONFIG/RESET_LATCH_HIGH. A successful latch predicate
requires the captured prefix and progression, not a flag alone. Existing refusal
fields already preserve failed raw values, so no extra telemetry field or
whole-IO acceptance restriction is needed. V6 decoding and retained physical
results keep their original meaning; exact ML040 raw decoding was compared
field-for-field, and the V7 decoder rejects its old tag.

The kernel, DTB, configuration and late overlay are unchanged. One-stage HCE
stop, original reset ordering and pulse release, 120/300/540/15-second research
bounds and 555/570/660-second automatic recovery bounds remain. The existing
V6-named recovery identifier describes the shared mechanism, not the report
schema. Stage-three EBUSY still does not identify which side of the GCC reset
refused. Newly reached HCE/reset/PHY/link behavior and automatic return after
partial execution remain physical questions. Conditional unattended F1 stays
inactive and usable attended physical Download remains required.

## H0 validation and review

The actual C producer, bounded reader, guest return parser and authenticated
host decoder are tested on host and ARM64 for both V6 and V7. The V7 matrix
covers exact/mismatched CTL values, low/high latches and unknown upper IO bits,
both before and after HCE stop. The exact production stage-three function is
also exercised: pre-GCC refusal, post-GCC drift, exactly two IO stores, preserved
upper bits, mandatory release after failed low readback, reset-call failures and
budget expiry. Actual sockets cover V7 arm/liveness, complete negative returns,
malformed/partial results, ACK failure and unchanged deadlines. Original-owner
fixtures retain new-generation arrival, original-window and uncertain-A
non-replay checks.

The fresh candidate has actual observer reproduction, canonical package/CPIO
checks, ARM64 loader/exception-level tests and AP-to-boot-to-loader-to-kernel/
DT/archive byte joins. The earlier child/timer VM evidence is reused only for
its unchanged logic with original source provenance; it is not relabeled as a
new V7 physical or current-build VM result. The six real artifact checks use
this one fresh candidate and an actual old loader as a rejected mixed input.
The complete focused suite passed **102 tests with no skips**, including all
six current real-artifact cases. Touched Python compiled; scoped privacy, local
link and diff checks passed. The coherent independent review completed with
**PASS_GO and no findings**, binding the final capability and source packet.
The reviewer independently repeated all 102 tests without skips, verified the
actual artifact and retained V6 decoding, and confirmed the unchanged paged
H0 finalizer remains reusable after a proven healthy owner-free closure.

Fresh candidate qualification and exact task preparation completed. The
reviewed v43 backend was selected with its stable ordinary-terminal worker
unchanged. The fixed foreground D0 completed with current healthy Android;
no grant, operation, control or partition transfer was created. The next step
requires the generated exact approval, current attendance and usable physical
Download, as required by the selected mainline policy. Preparation and review
do not authorize the physical run.

H0 corrections preserved their failed logs: the first test parameterization had
an import/bytes-decoder typo; the reset fixture initially used a word pointer
where production uses byte-addressed `void __iomem *`; the first candidate
script lacked the existing private Unicorn dependency path before any build;
and one combined test driver omitted the repository root import path. These
were host harness repairs, not device effects or guard relaxation.

Past-failure checklist: ABI/SEMANTIC are confirmed by actual typed C/ARM64 and
sentinel/consumer evidence, with electrical state explicitly unproved.
WIRE/ROUTE cover version separation and actual guest/host/recovery branches.
ARTIFACT/AUDIT/PERSIST cover exact builds, raw historical parity and separate
source provenance. RETURN retains the reviewed original owner and finite
physical fallback. DISPLAY and media-backed filesystem persistence are outside
this RAM-only unit. No separate temporary execution gate was created.

## Mythos discussion and accounting

Two tool-disabled `claude-mythos-5-2` xhigh calls analyzed the original source
and then challenged the proposed V7 code with Samsung/U-Boot evidence. The
second response accepted retaining the 30-field report and withdrew optional
extra-IO telemetry. It identified cross-object mode consistency and actual
stage-three pulse testing, both addressed above. Its overstatements about
future boots, inherited configuration and latch/electrical implications were
corrected. Advisory conclusions are not independent PASS_GO or run authority.

Provider totals are 82,620 input tokens including cache creation and 40,153
output tokens including 33,597 thinking tokens. CLI API-equivalent cost totals
USD 2.928008; this is not verified subscription billing. CLI `/usage` showed
session 81% to 100%, then a reset and 0% to 20%; weekly usage moved 13% to 16%
and Fable 25% to 31%. These are account-wide, rounded readings across two
windows, not a single-call token conversion. Credits remained off. Before/after
records and both successful calls are in the private append-only usage ledger;
there was no inference retry or fallback.

Private evidence is under
`workspace/private/outputs/s22plus-ml042-reset-pin-h0-20261110-1/`. The next
physical outcome must separately state HCE stop issuance/completion, reached
post-conditions, local/link commands, return route and original-A final health.
