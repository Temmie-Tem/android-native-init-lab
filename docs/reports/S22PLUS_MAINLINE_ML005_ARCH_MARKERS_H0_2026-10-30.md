# S22+ ML005: post-FDT and post-paging progress markers

Status: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.

ML005 prepares two later positive progress witnesses after
[ML004](S22PLUS_MAINLINE_ML004_RUN_2026-10-30.md) proved MMU-enabled early
`setup_arch` entry. The first new site follows `setup_machine_fdt`; the second
immediately follows `paging_init`. Both use the existing guarded temporary
Normal-NC writer within the same two 128-byte slots. No pre-MMU assembly or
pre-FDT C marker remains in this candidate. Only S22+ FYG8 is selected;
A90 and S20+ are untouched. No ML005 grant, control or partition transfer
exists here; only the named preapproval D0 reads have run.

Independent source/artifact review is **PASS_GO**, with no unresolved findings.
The production image/task consumers reopened the exact candidate, and the
unchanged ordinary-terminal worker selected backend v14. Current readiness
was rederived from complete raw Android health and its durable journal;
process exit alone was not accepted. Readiness remains a point-in-time fact
subject to the existing freshness and effect-time checks.

| Preparation receipt | SHA-256 |
| --- | --- |
| Independent review | `ea8ff92725879fad927db7531d976f36a6b17c86a62209874222cd756c744659` |
| Mainline capability | `eb8bc9b20a73f84ed6e03260c45d720602ad8c44662369eae7e63a6c1b48df64` |
| Backend v14 | `df8c750414ea5c4d318e6d9cbec322d1af8bf94e393b70901a945ff298f846f3` |
| Exact task | `f307e034bf60f4c02a333e6e06495d10aa3e2e5f6b67bab0e8c481aee915bbd4` |
| Current readiness | `b21ba793291d6a5a42c31f3e24ea7dc46b5a8676ece0c61855d43b7142c361b9` |
| Pre-experiment summary | `5463eab35d6f2812f8fa85536234b6c936749c8e29c4eaca1465c06b5e98b716` |

## Claude and Argon discussion

Claude Opus 5.5 and Gemini 4 Argon High each completed an initial critique and
a cross-model challenge using sanitized evidence and exact source excerpts.
No model tools or device actions were invoked. Both ultimately recommended
post-FDT and post-paging as the smallest useful next pair. Their advice is
separate from the required independent capability/artifact review.

The challenge corrected concrete overclaims before implementation:

- Missing markers never strictly locate a failure. A later positive with an
  absent earlier record is consistent with guard skips, overwrite or loss,
  and creates no new stop or gate.
- This exact ARM64 tree defines both late fixmap helpers. A generic fallback
  `BUG()` does not prove that post-reset mapping is unavailable on this target.
  The selected sites nevertheless stay before `early_ioremap_reset`.
- Removing ML004's old writer does not retroactively prove its return. A new
  post-paging positive can prove return from ML005's earlier helper call along
  its sequential path, even if that earlier call skipped recording.
- No demonstrated hazard justified disabling stack protection or PAC. The
  existing compiler protections remain enabled; KASAN and shadow call stack
  are disabled by the retained configuration.
- Forced command-line bytes contain no `earlycon=` and use `panic=0`. No
  unclocked-UART or automatic-panic-reboot explanation was established.
  Recurrent resets and historical NoC text still do not identify reset cause.

A cheap additional H0 fixture used the exact ML004 kernel and actual
loader-produced DTB. QEMU's own DTB first established its CPU/MMU environment;
only at the early-C boundary was the FDT argument replaced. Actual
`early_init_dt_scan` returned true and execution reached the post-FDT path.
ML005 repeated this call-stage check at `setup_arch` entry, including return
from its post-FDT writer. These checks establish software handling of the
actual DTBs, not physical DTB reads or full emulation of the g0q board.

The original DTB is 139,560 bytes; the loader-produced buffer is 500,000 bytes,
at the qualified aligned destination. Full-loader checks preserve its tree
and reservations except the exact initrd start/end additions. The log slice
has active no-map coverage. No missing secure carveout was identified.

## Implementation and evidence limits

V3 has distinct magic, integrity domain and stage IDs. The C template changes
only by substituting its fixed function/frame name and half-slot offset.
Header and CPU-state guards, byte stores, prefix-last commit, mapping bounds
and reverse unmapping are retained. V1/V2 decoding remains unchanged.

`post-fdt` proves that candidate's post-FDT recording point. `post-paging`
proves its post-`paging_init` point and return from the earlier helper call;
that earlier call may have skipped its write. Neither static record proves
its own later cleanup/return, a shared boot, last attempt, reset cause, PID1
or USB. Missing records remain unknown. The original-A recovery graph,
120-second USB observation, one-shot consumption and finite attended approval
are unchanged.

The source tree differs from the retained unmarked base only in `setup.c`
and the generated C header; `head.S`, config and g0q DTB are unchanged.
The standard full kernel producer was used. No consumed build tree was edited,
no mutable hardlinks were introduced, and no Kbuild command rewriting or
manual linker replay was used to save a build.

## Validation

| Check | Result |
| --- | --- |
| Actual linked C writers | 318 cases passed across both stages, including interrupted stores, mapping failures, both slot page crossings, guard rejection and header changes |
| Actual instruction placement | FDT scan and read-only remap precede the first call; the second call directly follows `paging_init`; superseded marker symbols are absent |
| Exact Image, real EL1/EL2 and mappings | 13 QEMU cases passed; both writers return, temporary fixmap PTEs clear, mapping-pressure and mutation cases preserve bounds |
| Post-paging alias qualification | Actual stage-1 page-table walks find no translation for all 512 log pages; adjacent RAM translates correctly and its sentinels are readable |
| Earlier guard skip, later positive | Qualified without treating the missing first marker as a contradiction |
| Actual loader-produced DTB | Exact new kernel accepts it and returns from the post-FDT writer in the bounded call-stage fixture |
| Exact kernel with VM-specific RAM PID1 | Authenticated observer passed with the QEMU-shaped no-map DTB; complete raw evidence rechecked offline |
| Retained ML004 C artifact | 159 cases passed with the new checker, without rebuilding or repinning old artifacts |
| Retained ML004 raw projection | Production rederivation agrees; original consumed proof and journal bytes unchanged, device/process acquisition blocked |
| Loader and outer package | Complete loader cases, actual EL1/EL2 entry and EL3 refusal passed; two boot/AP packages are identical |
| Focused Python suite | 70 tests passed; touched Python compiled; content/link/diff checks apply to documentation |

The first new QEMU-DTB generator attempted an anonymous 36-GiB allocation and
failed before emulation. It now uses the existing sparse, unreserved backing
method. The failed log is retained; the kernel was not changed or rebuilt for
this fixture repair. QEMU's shaped DTB models the no-map hole and its own RAM;
it is not the physical g0q DTB and proves no physical cache coherency.

Past-failure checklist applicability: ABI covers real EL/PAC/canary and mapping
paths; WIRE/SEMANTIC preserve positive-only evidence; ROUTE/PERSIST cover exact
format selection, raw capture and historical decoder support; ARTIFACT joins
actual calls, frames, kernel and package; HOST covers emulator resource setup
and the existing terminal route; RETURN keeps original-A and no-replay rules.
No transport IO or display implementation changed. Unchanged checks and
historical evidence are reused without transferring their authority.

## External-model accounting and private evidence

Four calls completed with no failed, refused or fallback attempt. Thinking is
a subset of output tokens in this table.

| Provider | Input tokens | Output including thinking | Thinking subset | Other accounting |
| --- | ---: | ---: | ---: | --- |
| Claude Opus 5.5 | 4 uncached + 23,171 cache creation | 18,910 | 12,085 | CLI list-price equivalent USD 0.563584; actual subscription charge unavailable |
| Gemini 4 Argon High | 41,264 | 13,768 | 8,826 | 55,032 provider total tokens; cost unavailable |

Claude's account-wide five-hour utilization moved from 10% to 13%; Argon's
weekly remaining meter moved from 79.24% to 77.23%. These are account snapshots,
not exact per-call quota attribution. An unchanged intermediate Argon reading
is preserved as possible reporting lag, not zero token use. Before/after records are
append-only in the private external-model usage ledger; credentials are absent.

Discussion evidence is under
`workspace/private/outputs/s22plus-mainline-ml004-next-discussion-20261030-1/`.
Fresh build and qualification evidence is under
`workspace/private/outputs/s22plus-mainline-ml005-h0-20261030-1/`.
Existing consumed ML003/ML004 artifacts, grants, reviews and journals remain
intact. Independent final review, exact task admission and current readiness
are complete. The exact returned finite approval and actual attendance remain
required before the experiment; no operator-approval record or grant is open.
