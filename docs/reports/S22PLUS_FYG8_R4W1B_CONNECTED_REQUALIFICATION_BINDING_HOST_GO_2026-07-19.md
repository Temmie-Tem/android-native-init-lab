# S22+ FYG8 R4W1-B Connected Requalification Binding Host GO

Date: 2026-07-19 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Scope: retire the original connected-only qualification, preserve its evidence,
and bind one hardened connected read-only requalification. No device contact,
reboot, Download transition, Odin transfer, flash, consumed-state creation, or
partition write occurred.

## Source And Evidence

```text
hardened source commit  0524f206
helper SHA256           3b42a52b406b7c0073fc13b1df957b165193f20a75a9b6010c96131013baec61
helper test SHA256      0016da20c765583e1adf15af105078ebefaf49ebf792fda328e25e4ba310680a
clause draft SHA256     50a1e19f558507706bdc83d3603c0b13ba4211c5704c889d97ba1ad10e677112
AGENTS SHA256           da397d7f98fae660d1054bb158cd5592e32999075ad6e62aaf164bf302c7e200
old PASS SHA256         dea447026c4aad259559c100698ee9463345026467b3cfccd90dfdcb466c067e
```

The old canonical PASS path is absent. Its exact 760-byte content is retained at
`workspace/private/state/s22plus_fyg8_r4w1b_connected_read_only_pass_invalidated_20260719T064318Z.json`.
The candidate consumed state is absent.

## Independent Review

The first binding review returned `NO_GO` because appending the new block would
leave two standalone connected ACTIVE sentinels. The draft was changed into an
atomic replacement payload containing both the old-run RETIRED summary and the
new connected-only ACTIVE clause.

The follow-up simulated replacement of the exact old R4W1-B clause and found no
blocking issue. It verified exactly one connected ACTIVE sentinel, zero live
ACTIVE sentinels, all production `policy_required_values`, exact old evidence,
and no authority for reboot, Download, transfer, flash, or device/partition
write. Verdict:

`GO_TO_BIND_CONNECTED_REQUALIFICATION`

The installed AGENTS section equals the reviewed fenced payload plus one final
separator newline before the following R4W1-A clause; all payload bytes are
otherwise identical.

## Validation

```text
connected ACTIVE lines  1
live ACTIVE lines       0
connected policy_active true
live policy_active      false
focused tests           39 passed
all R4W1-B tests        113 passed, 3 skipped
offline artifact gate  PASS_R4W1B_LIVE_GATE_OFFLINE_CHECK
connected PASS present false
git diff --check        PASS
device contact          false
candidate consumed      false
```

## Verdict

`PASS_R4W1B_HARDENED_CONNECTED_REQUALIFICATION_POLICY_BOUND_HOST_ONLY`

This verdict authorizes no automatic device contact. The next connected run
requires a fresh exact operator acknowledgement:

`S22PLUS-FYG8-R4W1B-CONNECTED-READ-ONLY-DRY-RUN`
