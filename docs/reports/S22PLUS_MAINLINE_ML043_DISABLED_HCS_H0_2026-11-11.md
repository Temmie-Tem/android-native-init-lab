# ML043: disabled HCS readiness semantics and V8 preparation

## Bounded result

The operator requested Mythos analysis/discussion of ML042's post-stop HCS `0x8`,
then one next attended physical experiment. V8 removes UIC_COMMAND_READY only
from the three existing disabled-state predicates. It preserves every other
condition and the enabled command checks, and records the same-read readiness
sample in the existing report slot. The coherent capability is H0 until its
independent review, qualification, current health and exact attended grant.
A90 and S20+ are outside this task; ML042 remains consumed and healthy closed.

## What explains the rejection, and what remains unknown

[ML042](S22PLUS_MAINLINE_ML042_RUN_2026-11-11.md) observed full HCE zero after
one stop, then HCS `0x8` in one sample. The selected header calls bit 3
UIC_COMMAND_READY. The old disabled mask `0x39` rejected it even though its
DEVICE_PRESENT and existing host/device error bits were clear. Later post-stop
registers were not read. This proves why the program stopped; it does not
identify the bit's origin, persistence, clearing latency or electrical state.

The retained Linux `ufshcd_hba_stop()` and hash-verified Samsung base/FYG8 source
join both wait for HCE zero without waiting for UCRDY clear. No selected
ufshcd/ufshci/ufs-qcom file was replaced by the FYG8 differential. Their enabled
command path consumes readiness. The Samsung pre-enable callback contains
power/PHY/lane-clock/ICE work; that broader driver does not authorize those
excluded operations in this reduced module. Its source is a comparator, not
proof of exact shipped-binary behavior.

The pinned [EDK2 stop implementation](https://github.com/tianocore/edk2/blob/6bee033c69e2c4050cb65c378d282b8f23ca0a36/MdeModulePkg/Bus/Ufs/UfsPassThruDxe/UfsPassThruHci.c#L2178)
also observes HCE for stop completion and checks UCRDY before UIC submission.
The pinned [QEMU HCE model](https://github.com/qemu/qemu/blob/723622bedb0b423de7d1c61ebbe6e7a71934949c/hw/ufs/ufs.c#L1152)
zeroes HCS when disabling HCE. It therefore cannot explain or prove this board's
retained ready bit. Persistent, delayed, clock-dependent or separate-UIC-state
explanations remain hypotheses. Correcting the unused readiness predicate does
not require choosing one of those hypotheses.

## Exact change and interpretation

- Stage-two cold/post-handoff and stage-six quiescence change HCS mask
  `0x39` to `0x31`. The distinct final pre-enable check changes `0x9` to `0x1`.
  A shared compile-time readiness mask changes only that bit's membership;
  no extra error check is added to the narrower last site.
- Full HCE-zero prerequisites, short-circuit order, all doorbell/RUN/interrupt/
  auto-hibernate/pin guards and the existing reset release remain. No added
  MMIO read, poll, delay, status write, retry or effect slot is present.
- V8 retains `raw & 0x39` from the initial existing HCS read in bits 22–27 of
  the diagnostic word; failure independently uses `raw & 0x31`. A passing
  sample can thus contain bit 3. This is a masked sample, not the full HCS word
  or a claim about a later stage. No new field is added: tag `0x80000000U`,
  30 fields and the 256-byte envelope separate V8 from V1–V7.
- UCRDY already high means the later enable poll no longer supplies a clear-
  before-enable/0-to-1 readiness observation. The existing final HCE check,
  one start write, one-ms delay, 50-ms HCE/readiness poll, enabled command
  predicate and first exact local result remain. Sampled levels do not prove
  all internal initialization events. Stage-six bare EBUSY stays unattributed.

The fixed kernel, DTB, configuration, overlay, six-local/one-link scope and
120/300/540/15-second research bounds are unchanged. The same single-child
ordinary Download attempt, 555/570-second guest schedule and N+660-second
host cap remain. Completed negative results may return automatically; a hung
probe/kernel can still defeat ordinary reboot. Attendance and usable physical
Download remain required; conditional unattended F1 is inactive.

## Discussion, validation and review

Two tool-disabled Mythos 5.2 xhigh calls supported the correction while
challenging the actual implementation. The second accepted preserving the
three sites' differing original masks and withdrew a proposed per-outcome
review gate. It identified missing final-HCE-drift and stuck-enable tests and
a guest mask type that depended on the parser's 32-bit limit. Those were
repaired: actual second-read drift and HCE 0/2 after enable now refuse before
UIC, and the guest mask uses `long long`. No guard was weakened to pass a test.
The first model's proposed stage/error interpretation table is not adopted as
proof beyond the actual source and encoded evidence.

The complete focused suite passed **113 tests with no skips**, including six
real-artifact cases. Actual C functions run on host and ARM64, covering cold
and stopped HCS 0/8, retained sampled readiness, error/presence refusal, both
later disabled reads, final HCE drift, failed HCE enable, lost UCRDY and enabled
command admission. V7 and V8 have identical modeled read/write/timing traces
on their admitted later path. Real producer/reader/guest tests cover the
unsigned tag, malformed words and a maximum-width accepted 159-byte report.
Actual sockets exercise V8 result/return and fault paths. The ML042 raw result
redecodes field-for-field identically as V7 and is rejected as V8.

The final component was cross-compiled and identified as AArch64 ELF; its two
actual object commands select the same V8 mode. A rebuild after the guest-mask
correction produced identical module bytes, while the fresh final observer,
loader, key and AP were rebuilt and fully qualified. Actual loader/EL tests,
canonical package/CPIO checks, complete observer reproduction and AP/boot/
loader/kernel/DT/archive joins passed. The unselected first H0 candidate is
retained and never consumed. Artifact provenance is separate from checker
provenance and old VM evidence retains its original inputs.

The first H0 test attempt lacked a GENMASK fixture stub and revealed that cold
injection was overwritten by fixture setup. Both harness defects were corrected
and the failed log preserved. One evidence-index script named a nonexistent
source observer file; it was corrected to the actual generated observer path.
No device effect occurred during these H0 failures. The independent review
completed with **PASS_GO and no open findings**, bound to final packet2 and
capability2. It independently passed 60 focused checks, verified 1,368 immutable
pins, reproduced the actual observer and artifact joins, and re-opened all 537
prior ML042 raw captures. Its one omitted recovery-test import path was repaired
by rerunning only that missing module, preserving the failed harness log.

The reviewer identified an exclusive root-summary phrase, "V7 alone", that
conflicted with V8's inherited reset predicates. The final packet corrects it
to "V7/V8"; code, artifacts and successful tests were unchanged. The review
qualifies exact new capability/v44 publication and H0 preparation, plus reuse
of the unchanged paged finalizer after an actual healthy owner-free closure.
It grants no device authority. Before the physical run, the fresh candidate
and task were prepared, and v44 was selected without changing or restarting
the stable terminal worker. The subsequent exact attended grant, consumed
experiment and healthy original-A closure are recorded in the
[ML043 run report](S22PLUS_MAINLINE_ML043_RUN_2026-11-11.md).

## Physical completion criteria

One fresh attended run may establish a V8 HCS sample after cold entry or timely
handoff, then a later attributed refusal or deeper fixed initialization.
Expected negative results remain NO_PROOF and cannot silently relax the next
condition. Full link success retains every existing criterion. Report the
sample, reached stages/commands, selected return, exact original-A completion
and final health separately. A new HCS sample does not establish persistence,
reset causality or hang recovery. Finish after this one run's validated closure.

## External-model accounting and evidence

The two successful calls used 103,554 input tokens including cache creation and
50,949 output tokens including 42,990 thinking tokens. CLI API-equivalent cost
was USD 3.694792, distinct from subscription billing. CLI usage moved from
session 20% to 51% to 79%, weekly 16% to 17% to 19%, and Fable 31% to 34% to 37%.
These are account-wide rounded observations. Credits stayed off; no inference
retry or fallback was used. Before/after records and raw terminal captures are
retained in the private append-only ledger and task evidence.

Private evidence:
`workspace/private/outputs/s22plus-ml043-hcs-ready-h0-20261111-1/`, including
both exact prompts/responses and supplied source snapshots, retained-V7 raw
parity, final component/candidate/reproduction, test logs and review packet.
