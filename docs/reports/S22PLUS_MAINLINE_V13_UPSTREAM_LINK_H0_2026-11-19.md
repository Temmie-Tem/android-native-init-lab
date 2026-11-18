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
   after PHY calibration and before lane clocks.

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
| Focused UFS suites (17 modules) | 177 tests pass, 6 skipped |
| V13 fixture branches (20 cases × 2 CFG1 states, host and ARM64/QEMU) | pass |
| V12 parity without UIC_ERROR (link-phase MMIO trace, first 33 fields) | identical |
| UIC_ERROR outcomes: complete, timeout, fatal follow-up, bad code, budget expiry | decoded as specified |
| Guest and host agreement on V13 success lines (11 variants) | identical decisions |
| Historical v3–v12 observer compile commands and Kbuild text | byte-identical |
| V12 module rebuilt from this source tree | `9176104a…`, byte-identical to ML047 |
| V13 ARM64 module against the real Kbuild | `00ad0b93…`, `BUILT_H0_COLD_LINK_COMPONENT` |
| Repository boundary check | pass |

Private build evidence is under
`workspace/private/outputs/s22plus-ufs-v13-upstream-link-h0-20261119-1/`.

## Remaining before any physical run

Independent review of the code and contract change; a V13 capability
record and its review; fresh terminal-backend review under contract revision
81; fresh candidate qualification; current D0 health; and a separately
returned one-operation attended grant. The replug dependency of the USB first
response recorded in GOAL still applies to that run.
