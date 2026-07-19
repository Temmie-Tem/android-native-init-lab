# S22+ FYG8 R4W1-C Connected Policy Binding Host GO

Date: 2026-07-20 KST

Verdict: `PASS_R4W1C_CONNECTED_POLICY_BOUND_HOST_ONLY`

Scope: separate host-only activation of the reviewed R4W1-C connected
read-only policy. No device contact, USB enumeration, reboot, Download
transition, Odin transfer, flash, partition write, or candidate execution
occurred.

## Source Boundary

The connected helper, tests, inactive exception draft, exact binding-clause
document, source review report, and GOAL update were committed first as:

```text
64d317ab s22plus: prepare R4W1C connected qualification
```

The independent final delta review found no HIGH or MEDIUM issue and returned
both `Source commit: GO` and `Separate connected policy activation: GO`.

## Exact Binding

The complete fenced payload from
`docs/operations/S22PLUS_FYG8_R4W1C_CONNECTED_BINDING_CLAUSE_2026-07-20.md`
was inserted byte-for-byte into `AGENTS.md`. A direct host diff was empty. The
installed bounded block is:

```text
BEGIN_S22PLUS_FYG8_R4W1C_CONNECTED_POLICY_V1
...
END_S22PLUS_FYG8_R4W1C_CONNECTED_POLICY_V1
```

Its SHA256 is:

```text
35f1d2cf8b9a4b25bac108832fb3f9ec9fd37e05c1b03f9fa34eeb5367c17ffa
```

The block activates only
`S22PLUS_FYG8_R4W1C_CONNECTED_POLICY_STATE=ACTIVE`. It authorizes one
successful bounded read-only qualification after a fresh exact acknowledgement.
It does not authorize candidate execution, reboot, Download transition, Odin
transfer, flash, rollback, device write, cleanup, or any partition action.

## Post-Binding Validation

```text
R4W1-C connected focused tests and relevant cores   140 passed
git diff --check                                     PASS
full 9.68 GB offline artifact gate                   PASS
offline verdict                                      PASS_R4W1C_CONNECTED_GATE_OFFLINE_CHECK
policy.active                                        true
policy.policy_clause_sha256                          35f1d2cf...c17ffa
connected_pass_present                               false
device_contact/device_writes/reboot                  false/false/false
download_transition/odin_transfer/flash              false/false/false
```

The full offline rerun also reproduced every artifact and source pin and the
fresh static verdict
`PASS_R4W1C_WATCHDOG_CARRIER_TWO_REPRO_STATIC_CONTRACT`.

## Next Gate

The repository is ready for exactly one connected read-only qualification only
after the attending operator newly supplies:

```text
S22PLUS-FYG8-R4W1C-CONNECTED-READ-ONLY-DRY-RUN
```

Generic approval is insufficient. A connected PASS will be evidence for a
future separately implemented and independently reviewed live gate; it is not
live authority itself.
