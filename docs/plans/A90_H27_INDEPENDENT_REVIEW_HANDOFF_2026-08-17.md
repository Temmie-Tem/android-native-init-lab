# A90 H27 independent review handoff

Date: 2026-08-17
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 handoff specification
Device or live effect: none

This document tells an independent reviewer exactly what the H27 F1 runner will
accept, so a completed review produces artifacts the runner can actually
validate. It specifies **shape only**.

**It deliberately does not supply findings.** `validated_invariants` and the
verdict are the reviewer's own words and judgement. If this document contained
them, the review would be checking work against a script written by the author
of the thing under review, which is the failure this gate exists to prevent.

## What is under review

Two separate reviews are required, and neither transfers from H24
(`AGENTS.md:187-191` requires independent review when the runner, hazard, or
closure changes; H27 changes the kernel, the builder manifest, the candidate
hash, and the device's exploit-mitigation posture).

1. **Capability review** — is the H27 capability sound?
2. **Execution review** — is the H27 F1 runner sound for one attended flash?

Both must confront one fact that the H24 capability never had to: **the
candidate kernel has `CONFIG_RKP_CFP`, `CONFIG_RKP_CFP_JOPP`, and
`CONFIG_RKP_CFP_ROPP` disabled**, because Samsung's patched LLVM is not
distributed. That is a real reduction in kernel exploit mitigation on this unit
for as long as the candidate is resident. A reviewer unwilling to accept it
should return no-go on the capability, not on the artifact.

## Artifacts under review

| item | path |
|---|---|
| runner | `workspace/public/src/scripts/server-distro/a90_h27_ufs_f1_runner_v1.py` |
| builder version | `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h27/manifest.toml` |
| design | `docs/plans/A90_SELF_BUILT_KERNEL_F1_DESIGN_2026-08-16.md` |
| build report | `docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md` |
| candidate (private) | `workspace/private/outputs/a90-h27-selfbuilt-kernel-ab-20260816-01/` |

Prior review history worth reading first: this design was returned **no-go
three times**. The third found that the candidate carried `0.11.193`, which is
retired H25's identity (`GOAL_A90.md:86`, `A90_TARGET_CONTRACT.md:590`), and that
the runner still validated H18 as its starting resident rather than H24. The
candidate was rebuilt as H27 `0.11.194` and the predecessor bindings were
unbound rather than guessed. Earlier, Draft 1 was written without reading the binding target contract and
proposed a candidate that reused the resident's identity, which
`A90_TARGET_CONTRACT.md:320-324` forbids. Draft 2 fixed that but understated the
runner, review, and manifest gaps. Both reviews are in the session record.

## What the runner requires, exactly

### Capability review report

Path: `docs/reports/A90_H27_SELFBUILT_KERNEL_CAPABILITY_INDEPENDENT_REVIEW.json`

Fields the runner compares (`validate_host_capability_qualification`):

| field | required value |
|---|---|
| `schema` | `a90-h27-selfbuilt-kernel-independent-review-v1` |
| `capability` | `A90_H27_SELFBUILT_KERNEL_NOCFP_V1` |
| `status` | `PASS_GO` |
| `review_date` | the review's own date |
| `reviewer` | the reviewer's own identifier |
| `validated_invariants` | **the reviewer's findings** |
| `live_authority` | `false` |

### Capability qualification

Path: `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h27/capability-qualification.json`

| field | required value |
|---|---|
| `schema` | `a90-h27-selfbuilt-kernel-capability-qualification-v1` |
| `capability` | `A90_H27_SELFBUILT_KERNEL_NOCFP_V1` |
| `verdict` | `PASS_GO` |
| `execution_closure_sha256` | SHA256 over the `execution_hashes` set |
| `execution_hashes` | exactly **24** repository-relative files, each `{size, sha256}` |
| `native_init_closure_sha256` | `3d1514e3f266e5b77886bf4511a396c9328b487b0c614c3c79fd3df16d26ca52` |
| `native_init_closure_members` | `142` |
| `review_scope` | `h27-selfbuilt-kernel-nocfp-capability` |
| `incident_class` | the reviewer's classification |
| `new_hazard_or_incident` | `true` |
| `ordinal_requalification_required` | `false` |
| `f1_runner_qualified` | `false` |
| `d1_runner_qualified` | `false` |
| `review_report` | the capability report path above |
| `review_report_sha256` | that file's digest |
| `live_authority` | `false` |

The native-init closure values are given because they are **measured, not
judged**: H27's 142-member source closure is byte-identical to H24's, since
only build constants and the kernel changed.

### Execution review report

Path: `docs/reports/A90_H27_SELFBUILT_KERNEL_EXECUTION_INDEPENDENT_REVIEW.json`

| field | required value |
|---|---|
| `schema` | `a90-h27-ufs-f1-execution-independent-review-v1` |
| `capability` | `A90_H27_SELFBUILT_KERNEL_NOCFP_V1` |
| `verdict` | `PASS_GO` |
| `review_date` | same date as the capability review |
| `reviewer` | same reviewer identifier |
| `execution_closure_sha256` / `execution_file_count` | over `EXECUTION_SOURCE_RELS` |
| `review_scope` | `h27-selfbuilt-kernel-nocfp-boot-only-f1-execution-critical-closure` |
| `incident` | same as `incident_class` above |
| `findings` | `{"high": [], "medium": [], "low": []}` |
| `validated_invariants` | **the reviewer's findings** |
| `review_contacts` | as the runner computes them |
| `live_authority` | `false` |

### Execution qualification

Path: alongside the manifest, schema
`a90-h27-ufs-execution-qualification-v1`, capability
`A90_H27_SELFBUILT_KERNEL_NOCFP_V1`, `verdict` `PASS_GO`,
`predecessor_capability_closure_sha256` equal to the capability closure,
`f1_runner_qualified` `true`, `live_authority` `false`.

## After the review: filling the runner

The runner refuses to start while any binding is a `UNSET_PENDING_`
placeholder, and an empty invariant tuple is rejected rather than treated as
"nothing required". Filling these is a separate reviewed edit:

```
H27_REVIEW_DATE
HOST_CAPABILITY_CLOSURE_SHA256
HOST_CAPABILITY_REVIEWER
HOST_CAPABILITY_INCIDENT
HOST_CAPABILITY_REQUIRED_INVARIANTS
EXECUTION_REVIEWER
EXECUTION_REVIEW_INCIDENT
EXECUTION_REVIEW_REQUIRED_INVARIANTS
```

`tests/test_a90_h27_ufs_f1_runner_v1.py` asserts these stay unset and that the
named reports are absent. Those tests must be updated in the same change that
fills them, with the reports present.

## Open questions for the reviewer

These are scoping decisions the author deliberately did not settle.

1. **Predecessor terminal.** The runner's `CURRENT_*` and D1-evidence bindings
   are unset. H27's predecessor is H24 `0.11.192` (boot.img 58,372,096,
   `d8c280e4acee5d17d13270fdf25535b4ce05304e786bc22efa84ab16f6b82782`), whose D1
   evidence is at `workspace/private/runs/server-distro/a90-h24-ufs-f1-20260812-01`
   and closed `REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY`.
   The inherited check required a **D1 HEALTHY** predecessor.
   `A90_TARGET_CONTRACT.md:1276-1279` says a later refutation does not
   retroactively fail an installation. Does a refuted-but-healthy D1 satisfy this
   precondition, and what exactly should the rebound check require?
2. **Proof axis semantics.** `EXPERIMENT_PROOF_BY_STATUS` is new, unreviewed
   code. It maps recovery-path and pre-release aborts to `NO_PROOF_OBSERVER` and
   health failures to `REFUTED`, on the reading that only device-attributable
   evidence may burn an ordinal (`:102-121`). Is that mapping right?
3. **Is the kernel deviation acceptable at all?** Disabling RKP CFP cannot be
   undone by rebuilding; it requires Samsung's compiler. The remedy, if the
   posture proves unacceptable later, is returning to the stock kernel blob.
4. **Terminal semantics.** Booting proves booting. The design states that boot
   success is not functional equivalence for WLAN, display, GPU, audio, or USB,
   and that no observation set for those exists. Is `PROVED` the right
   experiment terminal for so narrow a claim?

## What remains after a PASS_GO

A passing review does not authorize a flash. Still required: `GOAL_A90.md`
recording the successor objective (it cannot grant authority —
`AGENTS.md:47`), one fresh `A90_F1_RESIDENT_INSTALL_V1` binding, an H27 F1
manifest, a fresh connected D0, an empty durable journal, proven physical
recovery, exact attended F1 approval, and the operator physically present.

## Boundary

Produced host-only from repository documents and staged artifacts. Device,
`/dev`, USB, S22+, and S20+ contacts are zero. No ordinal, identity, candidate,
qualification, approval, manifest, or command is created, and no D0, D1, or F1
authority is granted or implied.
