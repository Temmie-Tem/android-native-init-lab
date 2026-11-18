# S22+ mainline UFS V13: upstream link tolerance and version envelope (H0)

H0 only. No device action, grant, candidate or capability adoption. This
unit implements the operator-selected V13 from the
[upstream-tolerance audit](S22PLUS_MAINLINE_UFS_UPSTREAM_TOLERANCE_AUDIT_H0_2026-11-19.md)
and removes the per-version contract chain that every earlier module version
had to traverse. Its independent review is pending.

## Module change

V13 inherits V12 with three differences, specified in the
[V2 capability's Report-v13 section](../operations/S22PLUS_MAINLINE_UFS_CAPABILITY_V2.md):

1. During the issued DME_LINK_STARTUP only, UIC_ERROR is admitted with UCCS
   and ULSS and polling continues to completion or the existing 500 ms bound.
   Every other bit keeps the V12 refusal; local commands are unchanged.
2. The OR of all link-poll IS samples is recorded. After UIC_ERROR the five
   read-to-clear UIC error-code registers are read once within the original
   budget. UECPA and UECDL are reported raw; UECN/UECT/UECDME share one word.
3. The existing QUNIPRO_SEL reads and write move to the end of stage four,
   after PHY calibration and before lane clocks. Every check that preceded
   the write at stage six (rates, HCI quiescence, PCS ready, HCE zero, HCS)
   is re-evaluated first.

Report v13 has tag `0xd0000000` and 38 fields. With every unconstrained word
at ten digits, the issued-link line is 254 bytes, inside the 256-byte envelope.
Raw UEC words for all five layers did not fit, which is why three are packed.

## Process change

Report versions and compile modes now come from one declaration,
`report_modes.py`. The builder, guest observer compiler, candidate
reproduction and host decoder derive from it instead of repeating version
tuples or chained keyword checks.

The common details gain a version envelope. A later module version may be
adopted by a row in the capability's version table, its own section, fixed
artifacts and one independent review, without amending the root, details or
target contract. This applies only while every difference stays within
predicate changes on existing reads, bounded reads in the fixed windows,
relocation of an existing write, and a report layout inside 256 bytes. New
writes, clears, retries, waits, power effects or any return, recovery,
authority, attendance, health or evidence-acceptance change still require
amendment. AGENTS.md (revision 81), the details, target contract and RAM
policy now refer to the version table instead of enumerating v4–v12.

Before this change, V12 (a single scalar assignment) edited AGENTS.md,
the details, the target contract, the RAM policy and the capability policy.
Each contract edit also invalidates the terminal backend review that binds
those bytes. The terminal (v50) and UDC timer review receipts are now
outdated by this revision and need fresh review before the next device run.

## Verification

| Check | Result |
| --- | --- |
| Focused UFS suites (17 modules) | 178 tests pass, 6 skipped |
| V13 fixture branches (20 cases × 2 CFG1 states, host and ARM64/QEMU) | pass |
| V12 parity without UIC_ERROR (link-phase MMIO trace, first 33 fields) | identical |
| UIC_ERROR outcomes: complete, timeout, fatal follow-up, bad code, budget expiry | decoded as specified |
| Guest and host agreement on V13 success lines (17 variants) | identical decisions |
| Historical v3–v12 observer compile commands and Kbuild text | byte-identical |
| V12 module rebuilt from this source tree | `9176104a…`, byte-identical to ML047 |
| V13 ARM64 module against the real Kbuild | `5628f299…`, `BUILT_H0_COLD_LINK_COMPONENT` |
| Repository boundary check | pass |

Private build evidence is under
`workspace/private/outputs/s22plus-ufs-v13-upstream-link-h0-20261119-1/`.

## Review rounds

Round one (Codex Luna, max effort, read-only) returned BLOCKED with 13
findings: three on envelope wording, eight on tooling/decoder gaps (two of
them lines lost in the mode refactor), two minor. All were confirmed and
fixed. Round two confirmed all 13 resolved and raised five more: a moved
write could occur where V12 would not issue it, an impossible stage-six
`UNREACHED` accepted by the host, a guest/host disagreement on the terminal
sample, and v6–v12 ranges left in the recovery path and the legacy source
closure. Those are fixed here: the selection re-evaluates V12's stage-six
admission before writing, (c) states the one admitted difference, and the
guest checks the terminal sample against the observed union.
Round three confirmed those five resolved and raised two: the policy named
only the lane-clock stop although stage-six deadline and re-check stops are
also post-write paths, and the guest's success check omitted the completion
result and post-link HCS. The capability now enumerates every post-write
stop, (c) admits that class rather than a single path, and the guest checks
both fields (the V13 module bytes are unchanged).
Round four confirmed both resolved, found nothing new in a final pass over
`1d2d6ccba0^..ccf5ed1bd7`, and returned **PASS_GO**: envelope-admitted
effects stay inside the reviewed late-UFS scope, reachable V13 success
histories agree across producer, guest and host, and v1–v12 behaviour is
unchanged. Prompts and raw outputs of all four rounds, with SHA-256 sums,
are in the private evidence directory under `review/`.

## Capability, backend review and preparation

The first V13 candidate build exposed one more line the mode refactor had
deleted (`import build_evidence`); it was restored in `d3d313deaf` and the
full removed-line diff of the refactored builders was re-audited.

A fresh candidate (`candidate-final-v13a`) passed observer/archive build,
loader and entry (EL2 accept, EL3 reject) tests, packaging, complete
producer reproduction, real AP/boot/loader/kernel/DT/archive joins and
identity separation from ML048. The capability record `3532b540…` binds 84
mainline and 54 backend sources and 467 evidence items.

A separate Luna review (read-only, max effort) returned PASS_GO for the
capability record, the revision-81 terminal backend re-review (48 of 54 v50
pins unchanged; the six changed sources carry only the reviewed V13/envelope
changes) and the restored import. Its first answer flagged the null
pre-review draft fields; given the established order (receipt, then binding,
then `candidate.qualify`), the reviewer withdrew that as a sequencing false
positive. The backend selector now names
`s22plus_approved_terminal_persistent_v51_review.json`.

After the review, the capability-bound declaration passed `candidate.qualify`
and the exact task was prepared (`PASS_H0_V13_REVIEWED_PREPARATION`). No
grant or operation exists.

The capability policy is itself a bound source of the capability record, so
its version-table row stays as frozen (`H0; code/contract review PASS_GO …
pending`) until the next capability; this report and GOAL carry the adoption
state. Editing that row after freezing changed the bound bytes and made the
first readiness request fail closed (`record receipt changed`); the frozen
bytes were restored.

## Remaining before the physical run

Current foreground D0 health; the operator's separately returned exact
one-operation 1800-second attended approval; physical attendance with usable
Download recovery. The replug dependency of the USB first response recorded
in GOAL applies: reconnect the cable when the attach cue appears.
