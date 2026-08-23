# S22+ FYG8 P3.19 candidate requalification H0

Status: `P319_CANDIDATE_REQUALIFICATION_IMPLEMENTED_REVIEW_PENDING`.

This is a host-only requalification of the already-built exact 73-row P3.19
stock-witness candidate. It creates no ready manifest, run manifest, approval,
fresh baseline, device action, recovery invocation, replay, causal result, or
live authority. Independent changed-closure review remains required.

## Reason for requalification

The reviewed `candidate-qualification-v1-20260821-08` intent contained 436
source keys. The current pre-requalification closure contained 437 and differed
at exactly four execution-critical entries:

- `adapter`;
- `adapter_closure:s22plus_fyg8_p319_stock_process_v2_adapter.py`;
- newly present `adapter_closure:s22plus_fyg8_p319_result_contract_arming.py`;
  and
- `process_contract`.

Those changes are already separately reviewed H0 capability inputs. This unit
does not reinterpret them. It reruns the exact qualifier so the current intent,
candidate, executability and integration layers consume the same bytes.

## Final no-clobber qualification

The final intent is
`candidate-qualification-v1-20260821-10/intent.json`, 107,403 bytes, SHA-256
`5a6a24195d89743b7b71e3dbd8db2d8d263c129b774d4a1d6155704507cb3bb2`.
It binds 437 source keys. Their qualifier-canonical digest is
`f41bfd2d1a4cf62aa62500a636a22e2035f3d56f9151e806e80da86f6c9cdded`;
the integration auditor's newline-terminated canonical encoding gives
`62ff6ea059e0d6cf3e45efca0a26a2528ec7639fab1b356394224d0fd7edb18c`.
Pinned and current integration summaries are byte-for-byte equal with zero
mismatch keys.

The exact plan remains 73 rows with `eud.ko` at index 38 and one generic
overlay, `s22plus_dwc3_event_latch.ko`. Fresh Phase 1 and Phase 2 are:

- `stock-witness-runtime-v1-20260821-52/result.json`: 382,264 bytes,
  `982f903f7685f63e5b2fbadebc5a3bbef5d98f009207ac352bda80777b09e886`;
- `stock-witness-runtime-v1-20260821-53/result.json`: 392,886 bytes,
  `21beec5d2010ecb5804c09055c93a24f83f0fc4be0c9125d24a831908efeaa4a`;
- static reconstruction: 975 bytes,
  `ce271a46e4bef9510e409c92dd29aded83f39dbcb4cec289c16897f6007d10af`;
- qualification: 113,386 bytes,
  `72b39572318945a180dff396998c8f2d72babc89a0f8655557a0dfc000cc852d`;
  and
- private report: 16,229 bytes,
  `2f49b75230088c14e6f784e02e9297a94da6d4a47c6ebc8bcdbc9e9e0e5853f9`.

Every private receipt above is a direct regular file with mode `0400` and link
count 1. Explicit `audit_existing()` regeneration succeeds against the exact
`-52`/`-53`/`-10` paths.

The self-bound qualifier's no-argument defaults deliberately remain the
preserved `-50`/`-51`/`-09` bootstrap. The final `-52`/`-53`/`-10` authority is
always supplied through its explicit CLI paths. Editing a default after intent
creation would change `qualification_source` and immediately invalidate that
same intent; the stale default therefore fails closed rather than acting as an
implicit mutable current pointer.

## Candidate bytes did not change

The final Phase-2 artifacts are byte-identical to reviewed `-49`:

| artifact | size | SHA-256 |
|---|---:|---|
| `candidate-a/boot.img` | 100,663,296 | `2b492a71808a0483f62896eb804042da38ed9ba7867aea045c5de630c9a86cb1` |
| `candidate-a/boot.img.lz4` | 27,267,991 | `0491d50adecf485d10ec5e58ea4f58c2f62a874897564fb7151059348205c7e0` |
| `candidate-a/odin4/AP.tar.md5` | 27,279,401 | `db5666ac794dfbf6f64192d7ea341ed79ff330f03db74c57da5ef61f659032f6` |
| `userspace-a/init` | 80,080 | `f6e6ea932c6c5297e18a932197e2fe1a131fac93c9caff9416d8fb873b055acb` |
| `userspace-a/s22-e1-child` | 1,376 | `eb3c072b41ab4d4953fd1d862388d3be5ca5a40e9a07f074cb273f96a28557cf` |

The fixed Image remains 41,490,944 bytes,
`71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8`.
No candidate identity, candidate run ID, rollback artifact, transfer count, or
consumed-candidate record changed.

## Bounded Rule-7 repair

The first corrected integration execution stopped before any device or
transfer session because the permanent raw-first auditor still held the old
exact identity for the host-only non-acquiring candidate qualifier. The
intermediate `-50`/`-51`/`-09` qualification is preserved. Its integration
receipt is 50,490 bytes,
`caf04f34a6a8f985e73bb2acc5f79a7fd350f8cd3d9433cb368cc1dd5eef45e0`,
and records the fail-closed prerequisite error rather than hiding it.

One bounded H0 repair re-registered only the final qualifier's exact 47,599
bytes and SHA-256
`2618c9c9ad0723ce456fcf718af0f456e02e020acc52c27864b501a0fd42ace4`.
The semantic audit still requires the same two approved `exec` sites, the same
single `getattr` site, no device transport, and every H0-only false-authority
field. The final raw-first auditor is 62,642 bytes,
`e67513b28c563f83d0b34b3df0c52d84a91a93102340150ed261938f337acbfd`;
its 11,012-byte mode-`0400`, link-count-1 receipt is
`ac3876c078062098ce240ae78c102ae19d2fe1b47eba257d374131cbaffc193e`.
The pre-final raw receipt `ab698ffb...` and independently reviewed
request-cut receipt `d8448713...` remain unmodified.

The corrected execution is the only post-repair qualification run. This is
the bounded Rule-7 repair, not a retry-until-pass loop.

## Integration state

Current host-only successors are:

- executability: 96,194 bytes,
  `636cb0cd551254c32120e31af8765b692f964256ca7e380f69b79c170df5b542`;
- prerequisite: 12,537 bytes,
  `ee6a1e79dfcd155f5bcdec95fbea61eea0c0645a8cd3ea2c7d30a04b59d7837c`;
  and
- integration: 61,388 bytes,
  `745814926e44763214ed15d3eeb10d2a4c4e8bb591d3b92d96685aa4cf4aff88`.

The integration verdict remains
`BLOCKED_P319_PROCESS_V2_INTEGRATION_H0`, now with exactly one machine
blocker: `FRESH_BASELINE_MISSING`. Source closure passes, the global consumed-
candidate registry is present and runner-consumed, Download-request-cut
recovery is closed, and runtime classification remains pending the future
candidate. `runner_ready`, ready/run/approval manifests, D0/D1/F1/replay,
causal result, candidate success, device contact, and live authority are all
false.

Topic 33's independent FYD9/FYG8 source-delta review remains separate and
unresolved. This unit opens topic 34 only. It does not authorize the fresh
baseline; that remains a separate attended exact-target action after this
changed closure receives independent review.

## Validation

- candidate requalification: 8/8;
- campaign-ledger taxonomy: 39/39;
- integration documentation: 7/7;
- candidate qualification, executability, prerequisite, integration and
  raw-first documentation core: 62/62;
- permanent raw-first hostile suite: 20/20 in 584.973 seconds;
- common Process-v2 four-module selection: 142/142; and
- full P3.19 discovery: 554 tests in 277.596 seconds, 553 passed, zero failed,
  and one error. The only error is the already-recorded unavailable
  `/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko` input to the
  independent temporary materialization test.

After the topic-34 ledger row was appended, both `build_receipt()` for the
prerequisite and `build_result()` for integration regenerated exactly equal to
their stored current JSON objects. The append-only bookkeeping row therefore
does not silently stale either machine result.

The first new requalification-test run was 7 passed plus one test-harness
import error because the direct module loader did not reproduce the script
directory on `sys.path`; the production CLI audit had already passed. Only the
test harness was corrected, after which the suite passed 8/8. The first full
raw-first run was 19 passed plus one stale expected inventory-digest assertion
(`a859...` instead of the newly generated `341e...`); the exact failing test
then passed 1/1 and the full suite passed 20/20. Neither correction changed a
candidate byte, private receipt, raw-first policy, or execution source.
