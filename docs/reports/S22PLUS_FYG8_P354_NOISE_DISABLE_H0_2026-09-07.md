# P354 explicit noise disable: H0 candidate

P353 produced the intended static pattern with visible corruption and was
rolled back healthy. P354 compares one specific software difference found in
the [exact Android firmware analysis](S22PLUS_FYG8_P353_ANDROID_DISPLAY_COMPARISON_H0_2026-09-07.md):
explicitly setting the selected CRTC's `noise_layer_v1=0` instead of omitting it.
This report records host qualification, not a demonstrated repair or device run.

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

This unit has sent no device command and created no connected run or returned F1 approval.
P353's consumed artifact, journal and result remain unchanged. A90/S20+ were
untouched. The next step after H0 closure is fresh exact connected preparation
and separately returned attended F1 approval, then one same-pattern visual
comparison and exact rollback. This report grants no device authority.
