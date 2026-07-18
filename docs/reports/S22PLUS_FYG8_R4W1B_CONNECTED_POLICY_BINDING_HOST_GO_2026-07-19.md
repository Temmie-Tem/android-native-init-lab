# S22+ FYG8 R4W1-B Connected Policy Binding Host GO

Date: 2026-07-19 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Scope: host-only independent review, connected-only policy binding, and
post-binding static/offline requalification. No device was contacted or
enumerated. No ADB, reboot, Download transition, Odin transfer, flash,
connected PASS, or consumed state was created.

## Result

The connected read-only policy is bound and ready for one fresh attended
qualification:

`PASS_R4W1B_CONNECTED_ONLY_POLICY_BOUND_HOST_ONLY`

The one-shot live policy remains inactive. This result authorizes no connected
execution by itself and no live or rollback action.

## Independent Reviews

Claude Opus 4.8 high-effort review used conversation
`c7d10391-7bb6-4274-9e49-076007945b03`.

1. The exact `c744abb3` source delta returned
   `GO_TO_SEPARATE_CONNECTED_POLICY_BINDING_REVIEW` with no finding.
2. The exact connected clause draft SHA256
   `c4a0f30cffaa1b8ae9730667b38f2f9fbe9f8b156dde18b2358a6e503b968048`
   returned `GO_TO_BIND_CONNECTED_ONLY_POLICY_COMMIT` with no HIGH, MEDIUM,
   or blocking LOW finding.

The second review confirmed that the connected sentinel appears exactly once,
the live sentinel is absent as both a standalone line and substring, all
source/artifact/baseline/observer pins match the committed helper, and the
clause authorizes only host-side evidence output plus one exclusive connected
PASS record.

## Bound Scope

`AGENTS.md` now contains exactly one standalone connected sentinel:

`S22PLUS_FYG8_R4W1B_CONNECTED_POLICY_STATE=ACTIVE`

It contains no R4W1-B live sentinel. The bound stage permits only one exact
connected read-only qualification after the fresh acknowledgement:

`S22PLUS-FYG8-R4W1B-CONNECTED-READ-ONLY-DRY-RUN`

It explicitly forbids candidate execution, consumed-state creation, reboot,
Download transition, Odin transfer, rollback, flash, partition writes, RDX,
and device cleanup. Live activation remains a separate future policy commit
that requires the exact connected PASS and another independent review.

## Post-Binding Validation

```text
focused core + helper tests              38 passed
all R4W1-B regression tests              100 passed, 3 skipped
py_compile                               PASS
git diff --check                         PASS
connected clause content                 exact, plus one separator blank line
complete offline artifact gate           PASS
connected policy                         active
live policy                              inactive
connected PASS                           absent
candidate consumed state                 absent
device contact/write/flash               false/false/false
```

The complete offline gate reopened the 9.68 GB stock firmware, candidate and
rollback APs, Odin, source pins, and fresh deterministic static result. It
returned `PASS_R4W1B_LIVE_GATE_OFFLINE_CHECK` with
`connected_active=true`, `live_active=false`,
`connected_pass_present=false`, and `candidate_consumed=false`.

## Next Gate

Stop before device contact until the attending operator supplies the exact
fresh connected acknowledgement. On connected PASS, pin the exclusive PASS
record and result identity, independently review the live binding clause, and
activate live only in a separate commit. A generic approval does not satisfy
the exact acknowledgement.
