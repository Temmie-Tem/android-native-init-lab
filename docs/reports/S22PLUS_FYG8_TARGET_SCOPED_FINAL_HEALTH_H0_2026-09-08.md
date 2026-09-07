# S22+ target-scoped final health after rollback — H0

A foreign Download device previously blocked both final Odin absence and the
final Android-health loop after S22+ rollback had already completed. This
change allows the selected S22+ to finish final health while retaining the
foreign endpoint as separate evidence. It performs no connected run.

## Scope and prerequisites

Only native-return prepared source closures containing `final_target_health`
select the new path. The final observer first requires `ROLLBACK_FLASHED`, a
completed rollback state, matching attempt start/checkpoint, validated exact
rollback AP transfer evidence and the journal's rollback-completion event.
Result validation also accepts the subsequent health-verified/closed states
while requiring the same durable completion evidence.

Preflight/D0, Download acquisition, candidate and rollback transfers retain
their existing global uniqueness rules. Legacy prepared closures retain global
final validation. The new target contract clause changes only final observation
and gives no new run, transfer, recovery rebind or replay authority.

## Observation and evidence

The observer retains exact selected ADB serial/topology, completed Android
boot, root and original boot/supporting partition hashes. It revalidates the
prepared Type-C source/companion mapping around each census, checks the current
Android sysfs serial/source/controller, and rechecks boot identity after the
two existing EOF observer reads.

The fixed private `final-target-health/` context retains bounded typed census
captures before and after EOF collection. Each includes the complete Download
inventory and both Android identity reads, including partial values/errors.
These observations are sealed before identity comparison. No foreign device
is opened or commanded. A Download endpoint on either bound source/companion
lane, incomplete census, wrong Android identity, changed mapping/boot or failed
partition health cannot pass. Binding/census faults stop that observation;
they are not treated as ordinary Android-arrival polling.

The consumer reopens the raw captures and reconstructs the projection. It
requires explicit before/after phases and distinct increasing sequence numbers.
It never filters, resets or rewrites the existing Odin tracker. Capture names
continue above previous complete/partial observations in the fixed context.

| Field | Meaning |
| --- | --- |
| `health.odin_endpoint_absent` | Global absence across the retained before/after censuses; false if either contains foreign Download endpoints. |
| `health.target_odin_endpoint_absent` | No Download on the bound target lanes, with exact Android health. |
| `target_download_absence` | Versioned scope, ordered raw receipt identities and separate foreign endpoint summaries. |

Newly bound closures require the scoped evidence. Removing it and falling back
to an old global-success shape is rejected. Historical records are not relabeled.
Foreign endpoint details remain private; the structured summary uses digests.
A different final physical mapping still needs reviewed binding rather than
silently broadening target selection.

## Validation

Eight focused tests exercise real generic F1 journal/transfer-receipt production,
actual ADB raw-capture execution against a fixture program, temporary USB and
Type-C sysfs, the actual census producer and final-result consumer. The generic
marker fixture explicitly selects the new final branch; a separate real native
bundle test checks source-capability routing and historical exclusion.

Coverage includes foreign-present and globally-empty success, durable-rollback
rejection before any ADB creation, bound companion Download, incomplete census,
wrong Android serial with both failed observations retained, wrong partition
hash, duplicate/swapped before/after receipts, false global-success projection
and schema downgrade. Existing Odin-core regressions preserve two-live-endpoint
rejection and strict pre-transfer generation checks. Existing legacy/P366
lifecycle tests retain their historical source-capability input.

The final combined batch passes **207 tests**, including all eight focused
methods and their negative subcases. Changed Python files pass `py_compile`;
content/link/diff checks pass. Independent review returned `PASS_GO` for the
frozen runner, census helper, test and target-contract hashes. Review receipt
SHA-256: `0650797264bb7b58d1c1e4287cac75ef25022a6ab330a9e7d719058f13710ff9`.

Private validation and review records are under
`workspace/private/outputs/s22plus_fyg8_p366/`:
`target-final-regressions-final.log`,
`target-scoped-final-health-design-review.json`, and
`target-scoped-final-health-independent-review.json`.

This is a fresh source capability only. P366's consumed journal, prepared
source pins, raw evidence and report-only disposition remain unchanged. No
image build, candidate preparation, device command or additional flash occurred.
A90/S20+ work and source changes are excluded from this unit.
