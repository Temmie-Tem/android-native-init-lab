# S22+ v0.1.2-rc.4 output delivery and memory observation preparation

P381 implements the [rc.4 design](../plans/S22PLUS_FYG8_V012_RC4_DESIGN_2026-09-10.md)
for SM-S906N/g0q/S906NKSS7FYG8 after P380 lost1536 output bytes. v0.1.1 remains
the functional version. P380 is consumed and remains NO_PROOF with exact
rollback/final health complete. This report does not claim rc.4 target success.
The [capability definition](../operations/S22PLUS_FYG8_OUTPUT_MEMORY_RC4_V1.md)
preserves the target's fresh review, preparation and attended approval rules.

## Implemented behavior

The generated PID1 reads stdout/stderr only when an OUTPUT queue credit is
available and rotates streams after successful forwarding. Receive, exec status,
reap, deadlines, cancellation, HUD and CONTROL remain outside that admission
check. Partial writes retain their queue entry. Output limits still cause
explicit truncation/drain; finite cleanup and CONTROL can still produce an
incomplete terminal even with zero dropped bytes. No wire or timer is expanded.
The actual command limit is767bytes; the older rc.3 prose's1023-byte figure was
too loose, although its640-byte command fitted the real bound.

Six fixed qualifications precede the optional memory plan. The sixth now emits
gauge/HUD output only. A short renderer mode supplies bounded early/late memory
records as separate commands, each at most4096bytes. It branches before DRM and
module operations. The fixed369-file metadata manifest is derived from sealed
vendor/initial-module-plan inputs; module contents are never opened on the device.
The memory mode does not modify device files, allocator state or RBIN/CMA
reservations; kernel measurement code remains unchanged.

The output distinguishes missing sources, logical file bytes, allocation
metadata, nominal slab estimates, renderer-owned GEM handles and unavailable
physical/reclaimability proof. Up to32 GEM records use the existing HUD log pipe.
The new observer excludes only optional HUD_MEM diagnostic records from the
inherited functional predicate and preserves the complete raw log identity.
Other HUD errors, global size and newline guards remain binding.

## Host checks and corrections

Thirty real-pipe/supervisor cases passed on x86 and static ARM64 under QEMU,
including dual64KiB binary bursts with a paused host, byte-budget exhaustion,
one-credit fairness, short wire writes, CONTROL and inherited lifecycle tests.
The actual target UAPI constants and representative ARM64 open/stat/pipe behavior
were checked; these tests do not prove physical USB or actual target recovery.
Both modes of an exact executable copy of the final ARM64 renderer also passed
under QEMU with the host kernel/procfs, producing959/957bytes and no stderr.
The sealed build artifact remains mode0400; its initial non-executable invocation
returned1 with empty streams, retained separately. Only the H0 copy gained execute
permission. No candidate bytes were changed or target data observed by this check.

Twenty-two snapshot cases passed on x86/ARM64 with real tmpfs, sparse-file and
no-follow operations. Fixtures explicitly adapt fixed paths/procfs identity and
test-user ownership. They cover missing/oversized/malformed/duplicate input,
numeric overflow, wrong filesystems/metadata, nominal slab ranking, stale GEM
records and terminal/parser failures. Generated renderer/evidence tests cover
successful retirement, retirement failures and unchanged gauge/HUD guards.

An independent review found that the initial meminfo parser accepted malformed
number/unit separators. Requiring a space or tab and testing those cases fixed
that issue. Combined integration then found that the inherited HUD_ guard rejected
the new HUD_MEM records; the diagnostic-only projection above fixed this without
altering gauge requirements or raw evidence. Both findings were H0-only.

The generated PID1/collector/renderer integration passed, including collector
failure/control and authenticated replay. The prospective three-command plan
ran only after all six qualifications, then produced two valid bounded snapshot
records separated by at least two seconds. A20-second test fixture correctly
skipped the plan under the existing command-plus-return reserve; the plan test
uses60seconds and changes no production deadline. Four shared live-receipt
invariants passed, including changed plan/HUD claim rejection and budget-stop
handling. Host fixture DRM, credentials and memory are not device observations.

## Final A/B and static qualification

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| AP, identical A/B | 31,150,121 | `c6ee76b7f6eab3310b28686ebfdd92762b9a4ccba0133ebf088675a421a18658` |
| Image | 41,490,944 | `b1929bfdda66251fac191f6c238dbf73ae65672151820479a6c3171df4b11172` |
| init | 149,448 | `c13b9f27c8e0da406f6e1535b5b2ad667351c55bdc56c97f7d355cb989cf9d12` |
| renderer/collector/snapshot mode | 778,904 | `109dec43378f2def5e34fc0428113ef79c01ba395790e3cd18ddf86864a5576d` |

The build binds322 source inputs and preserves the consumed ancestors. Generated
userspace is static ARM64. The kernel uses only the existing same-length
candidate run-identity transform; the qualified gauge provider is unchanged.
The official static result is40,178bytes, SHA-256
`028403aad70d75748c67f30c8a119e81ab11374c7408df57c1ec7bfd63891201`,
`PASS_P381_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY`.

Private build/static evidence is retained under
`workspace/private/outputs/s22plus-fyg8-v0.1.2-rc.4/` and
`workspace/private/outputs/s22plus_fyg8_p381/`. No firmware, raw target logs or
private identifiers are published. Review/publication/preparation status is
recorded below when completed; none is a substitute for fresh F1 approval.

## Independent review and READY publication

Final independent review returned PASS_GO with no remaining findings. It
verified the322 build inputs,50 static sources, actual A/B artifacts and
generated C, all21 provider import CRCs, exact official-static regeneration
and the real offline promotion. Thirty-seven final combined tests passed
independently, in addition to the earlier37 snapshot/renderer/evidence cases.
Conservative lifetime HUD/gauge/GEM record bounds total236,884bytes, leaving
25,260bytes for startup records under the unchanged262,144-byte log cap.

The private review is90,416bytes, SHA-256
`79feb43d30b221b295bdb954ebff7f12082d59995428b7555720cbe142867a02`.
It covers only the existing foreground capability's f1_owner and target source
refresh. The prior receipt is retained; all eight actions and the other seven
source roles are unchanged. No grant is opened or renewed by that refresh.

The published READY manifest is9,088bytes, SHA-256
`e1ed783cbf30e5f5a7dc167361aff8be4d1fcb8a0362497b9fffa6cef782d98b`.
Publication verified the actual final bundle
`9c3ab1aed319a2899726709a2c5c872a3ce64c1393fc251ff2046dbfe09c1334`.
This is host-only readiness, not a candidate transfer or live authority.

## Connected preparation

One generic `--prepare` completed in `p381-ready1-prepared-20260910-1` with
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. It checked the exact current
S22+ identity, firmware, rooted health and original hashes through the existing
bounded raw-first reader. No A90 or S20+ command was sent. Device writes, reboot,
Odin, partition transfer, F1 authority and live authority are all false.

| Preparation record | Bytes | SHA-256 |
| --- | ---: | --- |
| D0 result | 3,261 | `ae15414c9cba1de1477791002b0d1187ab398243d85134bb306f4ea545f6d553` |
| Prepared record | 39,735 | `a7e3bfceaa7d6ef5983853ed60ce3e871ccdb0689a7c023671e78f6aef0e35a5` |
| Sealed three-command plan | 521 | `529f26995809dc33cd2734051020871c8f4c01815809aee64d11f8d1ebdb40ad` |

The actual prepared-record consumer reopened this run and the existing owner
sealed the root/RAM-directory check plus exact early/late snapshot commands.
All three use15-second command limits. The late command includes a two-second
sleep. They remain unexecuted until the fresh attended approval is supplied;
P380's consumed token is not reused. Preparation proves neither native memory
attribution nor physical gauge pixels, and creates no F1 ledger row or lease.

Touched Python compilation, focused tests, scoped content/link/diff checks and
the repository boundary check passed. Unrelated S20+, AGENTS and old P345 work
remain outside this unit. No push or HUD image publication was performed.
