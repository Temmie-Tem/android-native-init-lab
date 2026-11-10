# S22+ ML037: same-read HCE and bounded HCI diagnostic preparation

Status: **H0 QUALIFIED / INDEPENDENT PASS_GO / ML037 CONSUMED WITH NO_PROOF**.

The operator requested implementation through the next attended physical
experiment after the ML036/Mythos cross-analysis. ML036 remains consumed,
NO_PROOF and Android-closed healthy. This unit preserves the original HCE
word and a small bounded set of additional status reads; it does not disable
HCE, move a reset or relax an admission condition. Completion is one qualified,
independently reviewed successor, exact attended admission, a separately
classified physical result and original-A healthy closure.

## Scope and evidence

The report-v5 module records the full value returned by the original stage-two
HCE read. The same value still decides the original nonzero refusal. Only
HCE 1/2/3 permits five added reads, in order: HCS, transfer doorbell, task
doorbell, interrupt enable and interrupt status. Each read checks remaining
time against the original absolute module deadline. A deadline ends the
captured prefix and preserves the original EBUSY refusal. Unknown HCE bits
admit no extra read. HCE zero and the later pre-link check retain their original
paths. All link, power, USB, five-minute witness and recovery guards remain.

The selected retained kernel's `ufshci.h` defines these offsets and HCE bits.
Its `ufshcd.c` reads HCS for presence/readiness, polls the doorbells, reads IE
before a conditional write, and reads IS before an explicit write-clear and
reread. This is direct software/ABI evidence for the fixed ordinary reads;
it is not a proof of every physical inherited state. The generic UFS driver
is disabled in the selected configuration and is a reference, not a newly
enabled consumer. No run/stop, AHIT, reset-pin, queue-pointer, PHY or UIC-error
read is added. The broader eight-register proposal was narrowed to this
source-supported five-read set before implementation.

Captured raw values are separate from the original evaluated/failed predicate
masks. They are sequential reads, not an atomic controller snapshot. An HCE
refusal still leaves every later predicate UNOBSERVED, even when a raw value
was captured. Missing HW-version reads decode to unavailable rather than a
zero value; an actually read zero remains zero. None of these values proves
the cause, another owner's absence, idle DMA, link completion or recovery.

The existing 256-byte authenticated envelope carries 30 decimal fields under
the explicit v5 tag: the original 23 fields, captured prefix mask and six raw
words. Capacity is checked for reachable shapes; no claim is made that 30
unconstrained 32-bit decimal words fit. Mixed modes and impossible captures
fail closed. Historical v1-v4 results retain their original meaning. Both
guest and host require zero new fields for the existing certified pre-overlay
normal-return class. Stage-two failure never gains normal-return permission.

## Reuse and validation

The ML035 Image, configuration, DTB, transport, PHY tables, original-A path,
owner timing and physical cue implementation are reused unchanged. Only the
module, observer and their derived RAM archive/loader/AP change. Shared V2
continues to separate reviewed capability from key-only candidate data; a
changed module needs its own reviewed capability, never reuse of ML036's
review or approval. The common boundary-3 scope, selected target and shared
policy name the exact added accesses together.

The actual ARM64 module built against an isolated copy of the retained Kbuild;
`file` identifies an ARM aarch64 relocatable object. Host and ARM64 fixtures
exercise actual HCI/stage/report functions, the bounded reader and guest/host
consumers. Defined and unknown HCE values, maximum raw values, every added-read
deadline boundary, unchanged HCE-zero/early-failure traces and the untouched
later check are covered. The actual socket collector retains the v5 raw result,
rederives its authentication and creates no Download intent on stage-two refusal.
Success and certified pre-effect return keep their existing behavior.

The focused suite passed **54 tests with no skips**, including two real v5
key candidates, their actual byte joins, mixed-artifact negatives, host and
ARM64 C cases and the actual socket collector. Both new loaders passed the
existing placement/exception-level qualification; each boot/AP pair reproduced
identically. The original ML036 authenticated v4 result also decodes to exactly
the old facts with the new decoder and gains no retrospective raw snapshot.
Touched Python compilation, diff and repository boundary checks passed.

Independent preliminary review identified the unobserved HW-version zero
presentation, which was corrected with explicit early/actual-zero cases. It
also checked the fixed read semantics and the distinction between sequential
captures, predicate evaluation and physical proof. Final independent review
returned PASS_GO with no remaining findings and independently passed all 54
tests. It checked 80 execution sources, 53 bridge sources, 83 evidence records
and both fresh artifact sets. These counts describe that review, not future
acceptance criteria.

The immutable reviewed capability is
`6407b1de7c9fef516abe95b98218ea1e05f8a02bf66b1e50a05f840847de41af`;
the independent owner review is
`d18fd990645674c8a7fa58139ee6d81add98210a0616b1d1047e28f541fc8b88`.
Both candidates then passed complete observer reproduction and fresh V2
qualification. Only ML037 has an exact prepared task; the peer remains H0.
The reviewed v41 backend was published under the existing locks with no F1
owner and without changing the stable worker. A fresh fixed foreground D0
completed current identity/root/partition-digest health and host checks with
zero control or transfer. No approval, grant or operation exists at this
preparation point; physical execution still requires the exact returned
1800-second one-operation approval, current attendance and usable Download.

The first candidate-build invocation stopped at an unavailable Unicorn import
before artifact creation. The existing retained Python dependency directory
was selected; the failure log remains. The first review freeze also refused an
empty compiler log as a nonempty-record pin. Its empty bytes were recorded
explicitly and the failed snapshot preserved before a fresh immutable freeze.
No assertion or device action was bypassed. Existing unrelated candidate-list
and attachment work is preserved.
A90 and S20+ have no action in this unit.

Checklist: ABI checks target offsets and actual ARM64 execution; WIRE joins
formatter/reader/authenticated collector and both consumers; SEMANTIC keeps
captured versus evaluated versus unavailable distinct; ARTIFACT binds fresh
module/observer/loader/AP provenance; ROUTE selects the reviewed fixed report
mode through existing V2; RETURN retains stage-two physical recovery and one
original A. Private evidence is under
`workspace/private/outputs/s22plus-ml037-hce-snapshot-h0-20261110-1`.

## Attended outcome

[ML037 ran once](S22PLUS_MAINLINE_ML037_RUN_2026-11-10.md). Its original
first-response window expired with all 88 selected USB censuses absent, before
any base request, five-minute witness or module permit. The diagnostic was not
exercised on hardware. The actual completion reply resolved the attach cue
before separate physical Download. Original A transferred once and the first
complete health bracket passed. The consumed run is NO_PROOF and
ANDROID_CLOSED_HEALTHY, with no F1 owner or created network profile.
The preparation evidence retains its original H0 meaning and grants no replay.
