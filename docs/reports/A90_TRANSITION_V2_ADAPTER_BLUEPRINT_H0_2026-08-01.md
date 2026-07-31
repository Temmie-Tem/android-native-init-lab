# A90 transition-v2 adapter blueprint H0 closure

Date: 2026-08-01

## Result

`PASS_HOST_DESIGN_ONLY_LIVE_BLOCKED`

This unit maps the reviewed transition-v2 state model to existing A90 source
owners. It is H0 only. No device was contacted, no live target was bound, no
manifest or approval was published, and no flash, reboot, handoff, or cleanup
was attempted.

## Ownership decision

The resident F1 path delegates the whole transaction to
`a90_resident_promotion_v1.py`. Its existing base orchestrator remains the sole
owner of approval consumption, durable journal, candidate transfer, and exact
rollback. The new adapter owns no F1 phase and therefore does not duplicate or
partially bypass the reviewed F1 state machine.

The ordinary D1 path is an explicit route map over existing primitives:

- static predecessor-release and successor-acquisition gate;
- resident-native health primitive for a future composite preflight;
- transient A90-only ModemManager guard;
- one switch-root dispatch;
- central framed Debian/display classification;
- changed-USB-epoch native return;
- NCM binding by returned USB parent;
- exact work-copy cleanup; and
- final resident health.

No D1 phase contains flash, payload transfer, or a partition write.

## Deliberate blockers

The blueprint cannot become live under this schema. It fixes
`live_ready=false`, `device_authority=false`, and
`approval_preparation=false`, leaves the exact target unbound, and records:

- `REAL_EFFECTS_BACKEND_UNIMPLEMENTED`;
- `IMMUTABLE_SOURCE_BINDING_DEFERRED_TO_ACTIVATION_MANIFEST`;
- `CONNECTED_IMMUTABLE_MANIFEST_ABSENT`;
- `FRESH_F1_APPROVAL_ABSENT`;
- `D1_DURABLE_JOURNAL_OWNER_ABSENT`;
- `D1_ONE_SHOT_APPROVAL_CONSUMER_ABSENT`; and
- `D1_CLEANUP_APPROVAL_SCOPE_MISMATCH`; and
- `D1_CLEANUP_BASELINE_IDENTITY_MISMATCH`.

The cleanup mismatch is material. The existing retained-work cleanup helper
requires its own legacy approval and checks exact V2321 health. That approval
cannot be reinterpreted as the future D1 approval binding one handoff and
same-run exact cleanup, and V2321 is not the resident candidate identity.
Activation therefore requires a new D1 journal/approval/cleanup owner rather
than a wrapper that silently calls the old helper.

## Static closure

`a90_transition_manifest_v2.py` is a small flat route contract with no
inheritance or import of live execution modules.
`a90_transition_adapter_blueprint_v2.py` confines every named path to a real,
non-symlink repository hierarchy, parses source with AST, rejects duplicate
top-level definitions, and inventories required callables without importing
legacy runners.

The inventory names six source roles: transition contract and engine, resident
promotion owner, F1 orchestrator, central observation pipeline, and legacy
cleanup primitive. Symbol presence is not semantic proof and current-source
hashes are not generated as a false trust anchor. The audit output is generated
in memory, explicitly reports `source_identity_bound=false`, and is printed to
stdout only.

## Fault validation

Focused tests reject:

- a missing required callable without importing the affected module;
- duplicate top-level callable shadowing;
- an intermediate repository-path symlink;
- unknown schema keys or any readiness flip;
- F1 phase ownership by the adapter;
- a D1 flash, payload, or partition-write effect;
- reinterpretation of the legacy cleanup approval;
- claimed D1 journal/approval owners; and
- removal of a live blocker.

The two new modules also import successfully in a read-only disposable
bubblewrap namespace with no private tree and no write surface.

The expanded route, transition-engine, ModemManager guard, resident-promotion,
manifest-builder, and retained-cleanup regression passes `124/124`.
`py_compile` and `git diff --check` also pass.

Independent safety review returned PASS with no remaining Critical, High,
Medium, or Low finding. Its initial review rejected the larger dynamic-hash
self-audit as both an invalid trust anchor and excessive H0 structure. The
final implementation removes that claim, explicitly defers immutable binding
to activation, and retains only the route contract and honest symbol
inventory.

## Next bounded unit

The next H0 implementation may add the missing durable D1 journal, atomic
one-shot approval consumer, and same-approval exact cleanup effect. It must not
activate live execution in the same unit. A separate independent review and a
fresh connected manifest are required before any later D1 or F1 authority is
requested.
