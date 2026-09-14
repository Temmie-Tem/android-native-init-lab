# S22+ native session V3 live qualification

P393 bootstrap and P394 physical USB reconnect N/E/N completed under the
actual returned attended grant for `SM-S906N/g0q/S906NKSS7FYG8`. The retained
device is P393 N, with a fresh final health/DETACH and terminal state
**`NATIVE_CLOSED_HEALTHY`**. P393 received V3 admission. The selected actual
USB reconnect passed. Android recovery was unnecessary and was not exercised.

The execution used source commit `d6525774c9ba9a0f24ab07175bc013f55fe2edc2`
and the reviewed current-working capability, SHA-256
`b8d67aa38b107349c19ab941e89c87d236eac8f1e226561aafcef5ceae47a0a8`.
Its exact 42 execution source files are preserved privately, including the
reviewed working contract variant. The unchanged 144-file native source
closure and P393/P394 artifact qualification are recorded in the
[H0 report](S22PLUS_NATIVE_SESSION_V3_H0_2026-09-15.md). No execution source
changed during this grant.

## Functional result

| Operation | Boot image transfers | Authenticated health observations | Result |
| --- | --- | ---: | --- |
| P393 bootstrap | P393 twice | 4 | Both installed boots qualified; N admitted |
| P394 N/E/N | P394 once, P393 once | 4 | Actual E USB reconnect, same-boot reentry, final N health/DETACH |

Initial Android health, exact artifacts, current host readiness and physical
lane binding passed before the first effect. The bootstrap's authenticated
ordinals were 1/2 on each of two distinct boots. The N/E/N starting observation
used ordinal 3 of the retained second N boot. E used ordinals 1 and 2; restored
N began a new boot at ordinal 1. All eight required health observations passed.

After E's first health/DETACH, the operator disconnected and reconnected only
the bound S22+ cable. The observer measured departure 24.310 seconds after
opening its fixed window and a different USB generation at 27.691 seconds,
both within 120 seconds. Fresh acquisition, exclusive descriptor and holder
checks passed. E's second authentication retained its kernel boot identity,
used a new nonce and advanced authenticated elapsed time from 903 to 30,416
milliseconds. The following CONTROL, measured Download arrival, P393 transfer
and final N health/DETACH completed.

The experiment terminal's `native_admitted: false` means that operation did
not create a new admission. P393's bootstrap admission remains verified and
its latest tail is the experiment's healthy N terminal. P394 remains consumed.

## Timeline and closure

Times below are seconds from the original grant's BOOTTIME opening, derived
from the immutable journals. Transfer rows describe completed transfers.

| Grant elapsed | Event |
| ---: | --- |
| 40.485 | Initial Android-to-Download transition completed |
| 54.720 | First P393 transfer completed |
| 82.180 | First N boot's health/DETACH and fresh health/CONTROL completed |
| 92.198 | Second P393 transfer completed |
| 108.677 | Second N boot's two health/DETACH observations completed |
| 174.927 | N/E/N starting-N health/CONTROL completed |
| 183.379 | P394 transfer completed |
| 203.022 | First E health/DETACH completed; cable window followed |
| 233.106 | Physical reconnect and fresh E health/CONTROL completed |
| 243.224 | P393 restoration completed |
| 260.033 | Final N health/DETACH completed |
| 372.869 | Evidence rederived and parent grant closed |

There are four boot-only transfers, four mode-change intents and no stopped
journal event. N installations followed the approved reuse sequence; P394 was
installed once and no uncertain request was replayed. Both complete
sequences, terminal records, original N admission and final N tail rederive
from their private raw evidence. Actual descriptor closure is retained.
No original-A transfer or Android-exit operation occurred.

Two of the three authorized operations were consumed. The remaining operation
was retired by the immutable parent close at 2026-09-15 02:58:27 KST, well
before the original 3600-second deadline. The F1 owner is absent. Closure
does not authorize another observation or effect. The five-file PC holder
census/polkit/udev configuration remains installed and verified external
configuration; it is not a released temporary guard.

## Evidence and remaining limits

The private run is
`workspace/private/runs/s22plus-native-session-v3/task-20260915-1/`.
Each operation retains its exact request, append-only journal, transfer raw
files and native open/close/RX/TX records. The parent retains the original
grant, source snapshot, close and derived completion summary.

| Record | SHA-256 |
| --- | --- |
| Bootstrap terminal | `c07352e12e63adbab07a023a433872ec910e7ad87700fd39a6dc2d0b87dd3349` |
| P393 admission | `b388b58212042d60bb4bc4df09be2981d85b9a75c01bbbe6717c97aa5ac94d7c` |
| N/E/N terminal | `50d35deffb5ba790ec96e13dd2d6f7b4685a335310a8528d18aa30f7dbac7cc5` |
| Final N health/DETACH | `e32382a01156d96a4d213218b9a87cc06706e31e4f47c267bbd8d8be01bd8e5a` |
| Parent close | `a29702715683eb8d5ef1aa08d1d36fb44c5422694d01d7e6d151c6e8cc2b41d8` |
| Completion summary | `5bbd60703dbc56e234772ad24ebc7ac3fc3f0304e5db6f33ddf1c4e6a9c38fc0` |

This proves the selected real reconnect and N/E/N return. It does not prove
long-duration USB reliability or automatic recovery from an unresponsive
native runtime. HUD acquisition was omitted as selected; no HUD proof is
claimed. The operator reported that the version display lacks the `rc.1`
suffix. Both qualified images display `v0.2.1`; this presentation detail is
recorded without changing consumed artifacts.

Raw device identifiers and protocol bytes remain private. A90 and S20+
received no commands or device effects.
