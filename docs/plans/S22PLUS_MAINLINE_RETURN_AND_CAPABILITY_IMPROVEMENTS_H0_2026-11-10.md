# S22+ deferred return and capability improvements

Status: **H0 PROPOSALS ONLY — NOT IMPLEMENTED OR ADOPTED**.

The operator requested that these improvements remain separate from the
[stage-two diagnostic implementation](../reports/S22PLUS_MAINLINE_STAGE2_DIAGNOSTICS_H0_2026-11-10.md).
Neither proposal changes authority, recovery, candidate admission or a consumed
record. Neither is a prerequisite for that bounded H0 unit. No new gate,
daemon, observer or device action is proposed merely to restate consent.

## A. Normal return after a proved pre-effect rejection

The current module-result failure stops both the guest and host normal-return
paths. A selected future profile could distinguish a narrowly proved rejection
before late UFS effects from an uncertain or partially executed operation.
Its benefit would be fewer physical Download interactions; no fixed time
saving is claimed before measuring the actual end-to-end path.

The implementation question is not just `stage == 0`. Overlay application,
rail registration and probe dispatch precede the assignment of stage 1.
Attempted, completed and uncertain preparation need distinct evidence before
any absence claim. Likewise `usb_released == false` can mean that coverage
already unwound internally or never acquired a reference. A new class must
prove all required references settled without equating that flag to leakage
or cleanup. Zero fixed RPMh records alone does not prove zero hardware work.

Any future change must join the module's exact terminal evidence, the guest
success-only gate in `ml030_module_result`, the host's result validator and
return-intent checks, and the existing result-bound Download transaction.
It must preserve original deadlines, one original A total, exact Download
arrival, same-owner fallback and final health. Partial results, unknown
effects or unresolved work do not enter the new class. Stage-two and later
failures remain excluded unless their reached-state cleanup is separately
proved; ML035 cannot be retroactively reclassified or replayed.

Acceptance would exercise the real guest/host producer and consumer for each
admitted and rejected state, and separately review the execution/recovery
implementation with its policy adoption. Measure physical interventions and
stop-to-A time using consistent anchors. This is not an invitation to bypass
the current success-only return condition.

## B. Separate reusable capability identity from candidate data

The current source list includes successive policy documents and historical
marker modules, and candidate adoption edits the `REVIEW` selector in code.
A prospective change should reduce unrelated invalidation while preserving
the selected reachable execution, recovery, artifact, schema and authority
dependencies. Imports alone are not a sufficient dependency definition.

Separate three identities: reviewed capability machinery, exact candidate
declaration/artifact qualification, and each finite grant/consumption/journal.
A manifest's review selector must bind the correct capability and effective
scope; merely moving the path out of a constant is not sufficient. Retained
artifacts keep their original source provenance. New keys still require
validation of the changed archive and loader bytes. A capability review may
be reused only while its relevant inputs and hazard assumptions remain valid.

Acceptance should demonstrate that permitted candidate-data changes preserve
an unchanged capability review, and that changes to execution, recovery,
authority or evidence acceptance invalidate the affected binding. Include
mixed/stale declarations and original-owner recovery in the focused tests.
Do not target an arbitrary source/file count or repin an old approval to
obtain PASS. The schema, runner and governing adoption need one coherent
independent review before any future activation.
