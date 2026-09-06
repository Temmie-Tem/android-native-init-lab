# P354 explicit noise disable: same corruption, rolled back

P353 produced the intended static pattern with visible corruption and was
rolled back healthy. P354 compares one specific software difference found in
the [exact Android firmware analysis](S22PLUS_FYG8_P353_ANDROID_DISPLAY_COMPARISON_H0_2026-09-07.md):
explicitly setting the selected CRTC's `noise_layer_v1=0` instead of omitting it.
The later approved P354 run reproduced similar visible corruption and returned
healthy through exact rollback. No visible improvement or causal repair was
established. H0 qualification and the separately approved live result follow.

## Bounded change

The renderer keeps the P353 red/blue/green/black-cross pattern, linear XRGB8888
WC buffer, full 30HS timing tuple, primary selection, privilege drop, inherited
plane handling and single blocking ALLOW_MODESET transaction. It resolves the
noise property by name and includes literal zero even if its cached value is
zero. CRTC property count increases from two to three; following array offsets
increase by one. Missing or duplicate property fails before the sole atomic
ioctl. There is no alternative property, raw register access, second commit,
mode fallback, retry or changed kernel module.

The exact driver source installs a volatile property and distinguishes omission
from NULL disable: the setter clears the enable flag and marks noise state dirty;
the apply path reaches the existing mixer noise clear operation. The retained
three source-function fixture cases were reused after both source hashes were
reverified. Synthetic registers and callbacks do not prove runtime hardware
state. Neither Android's actual guarded branch nor P353's live noise bits were
observed, so the corruption's cause remains unproved.

Fresh P354 run, command, Image identity, observer and receipt namespaces keep
the consumed P353 binding separate. A fixed namespace declaration verifies seven
sealed P353 sources; wrappers reuse their reviewed behavior. The builder includes
those original files in its source closure, including files read without Python
imports. Shared Process-v2 dispatch selection follows the registered workload,
and closure snapshot names follow the selected namespace. P353's existing receipt
format is preserved.

The one-way authenticated observer retains its pre-dispatch checks and separate
closure snapshot. It proves host request dispatch only and leaves visual output
UNPROVED. No display response, later command, redraw or automatic recovery is
introduced. The operator's screen observation and eventual exact rollback/final
health remain separate results. Source absence stops locally but is not itself
a demonstrated device recovery; ordinary attended physical Download is retained.

## Validation and artifacts

- Generated renderer fixture: full atomic object/count/property/value sequence,
  one buffer/one commit, every painted pixel including row padding, explicit
  disable with cached zero, inherited-plane pair offsets, missing/duplicate
  noise, bad mode/map/alpha/attachments, and commit error without retry.
- Actual generated authenticated C supervisor with host sockets/pipes: normal
  and error exits after host closure, and the existing 60-second child deadline
  under a scaled fixture clock. No post-dispatch tty I/O or next session occurs.
- Real prefix parser/immutable receipt replay: truncation, tampering, partial
  write without retry, closure-snapshot failure/hash binding, no visual claim
  promotion, and final-result projection. Supplemental Carrier remains noncausal.
- P354 focused tests: 21 passed. P353 regression: 21 passed. Common F1 live
  regression: 74 passed. Repository boundary and document links pass. Touched Python
  compiles. Userspace and renderer are static AArch64 ELFs; A/B userspace,
  renderer, boot and AP are byte-identical. The actual AP decompression joins
  the audited boot and the complete expected ramdisk inventory.
- Exact twelve display modules, module plan, prerequisite receipt, KMS contract
  and separate child artifact equal P353. The generated renderer diff contains
  only the noise property and necessary array/count adjustments.

Candidate AP: `30965801B/bc48a71f0cd70cfb859f5b39a660b3e0464e8658169fe560a227b5d239b0e598`.
Its sole regular member is `boot.img.lz4`,
`30960599B/2df2dac56a110e2dbb540e6a01a41f7b7996b8edadf40cdf9c7aa5deba3a11b7`.
Renderer: `710032B/6a7f78de19035a3dafeeb9d915afcded04207a0b319da0441025840cd9115395`.
Image: `41490944B/776d2cf9e42295c636a46b17f52d0e540d8ee3014e5a37fee2d04e43e0c0e175`;
its inherited same-length transformation changes run identity only.
Exact Magisk rollback remains `23367721B/d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

Static qualification binds 109 source inputs and is
`47864B/fbb6a9b79d89ef4251a38753af3779b9acfc9b16d7bc1db9d43e1e7943f9b826`.
Private artifacts and checks are under
`workspace/private/outputs/s22plus_fyg8_p354/`; the A/B build is
`stock-candidate-build-v1-20260907-01/`. No raw logs, firmware or photograph is tracked.

Initial fixture execution exposed an absent new preparation wrapper and a test
that omitted its P354 session namespace. Both host-only integration omissions
were corrected before qualification; the original failed log is retained.
No candidate input changed during the A/B build.

## State

Independent review returned **PASS_GO**, with no blocking finding, for the exact
execution-critical closure and artifact/static joins. Its private receipt is
`independent-review.json`, SHA-256
`1d9af29948a3892ec7b0492ebbce8e651b8f7b1c9b5b1f5997166120f3324fd3`.
The actual offline promotion CLI and final-path bundle verification passed;
ready manifest is `4686B/0b86674afbcf19b171dff0b7dee8eab727c1b186acd0e2d9efbd2d604d389b28`,
bundle `0da5cc319545673b1244e98fa5db6ebbbd1d632511b231bc43ee831c3ba5b08e`.
All 72 construction and 109 static source inputs remained unchanged at closure.
The private H0 close record is `close.json`, SHA-256
`8cb0f93d22060ba31fff1457a560414d4dc529c4add01d14fee582ee4fbe181f`.

The H0 qualification above sent no device command and created no connected run
or returned F1 approval.
P353's consumed artifact, journal and result remain unchanged. A90/S20+ were
untouched. The next step after H0 closure is fresh exact connected preparation
and separately returned attended F1 approval, then one same-pattern visual
comparison and exact rollback. This report grants no device authority.


## Connected preparation after operator D0/D1 preapproval

The operator authorized exact S22+ D0/D1 through F1 code issuance, then confirmed
physical availability. This authorization does not include F1 execution.

First D0 in `p354-ready1-prepared-20260907-1` stopped at baseline classification
after initial exact FYG8/root/boot/supporting-health checks passed. The complete
`2097136B/d2abc5d47ca9ab81553e4f688fbdf2abab310ee643d73916d83a04895a2998f3`
observer was preserved. Its typed nonreusable stop is
`3252B/2151adb2d465a22b673f2ad6669594f0476eacb3c70497e8eec55104b9c3a388`;
actual stop-result reopening passed. No final continuity was claimed for that
stopped D0, and no transition was repeated from it.

The unchanged reviewed one-normal-reboot primitive ran once under fresh P354
metadata after physical availability was confirmed. The source/tool pins and
H0 primitive self-test passed. The result is
`PASS_P354_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH`,
`2963B/da843d9ecc0688408176528627dd12e61e4044a4125af015c2c4301143a0b57d`.
The boot ID changed, exact Android/rooted FYG8 health returned, and no other
target received a command. This is ordinary reboot return evidence, not proof
of automatic recovery from a blocked experimental kernel call.

Fresh D0 and preparation in `p354-ready1-prepared-20260907-2` pass.
D0 result is `3261B/88b2f8eb9911b71f38655a5a776bf4640eaeb239791fac5c07cfebed48e38be3`;
the complete observer is
`2097136B/c663aa6da69960b63f39f1a4a2205ca632550097b7157f95667b2826428e4e05`,
with a clean baseline. Prepared record is
`30321B/772e9786f2c36ddecb31dc9bc2a12c332d92a12ba9b00cdae2ea9111c3692079`.
Actual `load_prepared` reopening passed after preparation. The private
prepared record owns the exact approval token; no token or private
identifier is copied into this report. No Download request, Odin transfer,
native display dispatch or F1 execution has occurred. Android remains the
last verified healthy state. A separately returned F1 approval remains required.


## Approved F1 result

The operator returned the exact prepared approval. One original execute
invocation completed one candidate transfer and one exact Magisk rollback.
The authenticated parent prefix and full display-request write passed. Machine
verdict is `PASS_F1_V2_P354_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`; the session
remains deliberately unclosed and display execution/visible output remain
UNPROVED in that machine receipt. No follow-up display command was sent.

The operator reported “이전과 비슷하게 깨짐” and “똑같이 노이즈 패턴 보인다”, and supplied
a photo. The photo shows the intended red/blue upper blocks and green lower block
with black cross, horizontal speckles and extensive lower corruption. This is
**no observed improvement** under the explicit-noise-disable candidate. The two
photos were not measured pixel-for-pixel. The experiment does not directly prove
the property's setter or hardware clear ran; no post-dispatch execution telemetry
was collected. Do not convert this result into a hardware diagnosis, a complete
refutation of noise-related mechanisms, or proof of correct buffer visibility.
Photo and operator witness remain private in the run directory.

Supplemental Carrier classification is `AMBIGUOUS_INTEGRITY_FAILURE`, with
`NO_PROOF_OBSERVER`; it supplies no causal result. Its nonacceptance does not
change the narrower authenticated dispatch observation. Final rooted FYG8,
original boot/supporting hashes and absent Download all pass. The journal is
CLOSED with 19 records and `recovery_required=false`. Live result is
`22805B/ab4ff2f332604433424a23a11916a1c987e73c3d6cae8a99578c0018a4400883`.
Actual prepared/result reopening passed. There was no recover invocation or
candidate/rollback retransmission. Exactly one matching campaign closure row
was appended from this journal/result.

Canonical timeline, UTC:

| Event | Timestamp |
| --- | --- |
| `live_session_start` | `2026-09-06T19:40:18.684219Z` |
| `candidate_flash_start` | `2026-09-06T19:40:45.089196Z` |
| `candidate_flash_done` | `2026-09-06T19:40:46.739717Z` |
| `candidate_boot_ready` | `2026-09-06T19:41:11.063209Z` |
| `rollback_flash_start` | `2026-09-06T19:41:50.829169Z` |
| `rollback_flash_done` | `2026-09-06T19:41:52.364764Z` |
| `rollback_boot_ready` | `2026-09-06T19:42:37.500686Z` |
| `live_session_end` | `2026-09-06T19:42:37.522971Z` |

The run and its approval are consumed. No active shell or further device
authority remains; A90/S20+ were untouched. The previously assessed hardware
magenta solid-fill path is the next proposed H0 successor, to distinguish
buffer-fetch behavior from the remaining composition/output path. A clean
solid-fill result would still not alone prove a cache fault. No such successor
was built or run in this unit.
