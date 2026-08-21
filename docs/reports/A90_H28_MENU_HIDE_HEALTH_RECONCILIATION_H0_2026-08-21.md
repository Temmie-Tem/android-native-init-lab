# A90 H28 menu-hide health reconciliation — H0 implementation record

Date: 2026-08-21

## Scope

This record describes host-only implementation of
`A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_V1`. It records no device contact,
USB enumeration, serial bridge use, durable private-run state, approval,
observation, guard removal, or live authority. The existing S22+/S20+ working
tree changes are outside this A90 scope.

## Binding and boundary

The implementation is a fresh namespace after the consumed slow-health
capability. It binds the immutable H28 manifest, terminal, physical-return
intent `19377bc18714c7b2b698665a8c9ff96573d3c1fdfb028efba5b86f6b2def9f66`,
first Native-observation intent
`8f401590bca71575258a2e3d45e1bee6c55fd4e8eeff4c22012fc25f559d05be`, and
consumed slow-health intent
`63c26238f332a7bc1bad37a3950d5dc05f383c50a4a09ecfe57e2a119a390ac4`.
Its execution closure includes the exact `EXECUTION_SOURCE_RELS` declared by
the physical-return reconciler as well as the fixed owner and new capability
sources; physical-reconciler source/design drift therefore changes the
closure and invalidates the review/token.
The exact twelve prior slow-health receipt names, sizes, and digests are
declared in the fixed source from the public incident facts; no private input
was opened while producing this record.

The sole intended session ordering is durable intent, exact USB inventory,
managed bridge preflight, one raw `hide` line with an explicit `hide requested`
receipt, the fixed 3.0-second asynchronous-menu settle inherited from
`native_init_flash.py`, then slow-input boot ID first, `version`, `selftest`,
`status`, and `boot-id-final`, with a final unchanged USB inventory. Exactly
two boot-ID reads are required; `sameBoot` is derived from equality of the two
receipts. Changed/missing/invalid final boot ID parks without recovery closure.
Prompt-only or `[done]`-only hide output is rejected; settle
interruption/failure parks without a boot-ID request.
Failure consumes the new intent and retains both guards. Success can publish
the original recovery terminal and remove only the active guard after exact
readback. No candidate, rollback, reboot, image, partition, physical, ADB,
TWRP, service-control, or arbitrary-command path exists.

## Static validation

The fixed source and focused hostile corpus pass `py_compile`, 21/21 focused
tests, and `git diff --check` at this H0 checkpoint. An independent full review
is still required before `prepare`; a PASS would qualify capability bytes only
and would not authorize a live session.
