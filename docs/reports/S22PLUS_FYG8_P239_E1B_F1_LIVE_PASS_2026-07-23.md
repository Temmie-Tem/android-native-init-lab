# S22+ FYG8 P2.39 E1B F1 live pass

Date: 2026-07-23 KST
Tier: F1 boot-only candidate plus mandatory rollback
Status: `PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK`
Final state: `CLOSED`
Live authority: consumed

## Result

One exact P2.39 E1B boot-only candidate and its preapproved exact Magisk
rollback were transferred once. The retained observer accepted one exact E1B
terminal-success record. Final Android, root, boot, supporting partitions, and
Odin absence passed. The operator observed no candidate boot loop.

The private transaction closed as `candidate_proven_rollback_verified`. It
cannot be reused for another candidate or approval.

## Candidate Transfer And Observation

The reusable Process v2 runner revalidated the prepared binding and clean
baseline before the candidate action. Odin accepted the regular AP path,
transferred only `boot.img.lz4`, reached 100 percent, and closed the connection.
The durable journal recorded candidate transfer start and completion before the
bounded native observation window.

At the end of that window the transaction reached `OBSERVED`. The first
recovery inventory check occurred before the operator's physical Download
endpoint was available and stopped without a rollback transfer. It did not
retry the candidate. Once one exact Odin endpoint appeared, the same durable
transaction resumed through `--recover` and transferred only the preapproved
Magisk rollback.

## E1B Proof

Two post-rollback `/proc/last_kmsg` reads were byte identical and complete.
Their decoded result was `E1B_SUCCESS_ONE_OR_MORE_BOOTS` with:

- exactly one E1B long record and one success;
- active generation 15 at terminal stage `0x3f` with zero detail;
- the preceding valid generation 14 slot at stage `0x35`,
  `WDT_MODULES_VERIFIED`;
- both A/B slots valid with no torn-update fallback;
- zero UNSAT, failure, foreign, historical, malformed, delimiter, partial, or
  unterminated evidence; and
- a minimum of one candidate boot.

The H0 source and artifact closure binds the ordered transitions before stage
`0x35` to successful `finit_module()` calls for the exact FYG8 stock modules:

```text
smem
minidump
qcom_scm
qcom_wdt_core
gh_virt_wdt
```

It then binds stage `0x35` to exact `/proc/modules` visibility and stage `0x3f`
to E1B terminal success. This proves the bounded module-load runtime rung. It
does not prove driver or platform bind.

## Rollback And Final Health

The rollback transfer completed once. Android returned with:

- boot completion and stopped boot animation;
- the exact expected Magisk boot identity;
- root available;
- the expected unlocked verified-boot state;
- exact pinned `vendor_boot`, DTBO, and recovery identities; and
- no Odin endpoint remaining.

The journal contains all eight canonical timeline events in order:

```text
live_session_start
candidate_flash_start
candidate_flash_done
candidate_boot_ready
rollback_flash_start
rollback_flash_done
rollback_boot_ready
live_session_end
```

The final result records the candidate and rollback as completed, retained
evidence accepted, final health verified, recovery no longer required, and the
state closed.

## Boundary And Next Rung

This pass proves custom PID 1 local runtime plus insertion and visibility of the
five exact watchdog-chain modules. It does not prove probe success, watchdog
registration or ownership, platform-device bind, DWC3/UDC readiness, ACM host
bytes, NCM, shell, or Debian.

The next bounded rung is E2: prove platform bind and UDC state without inferring
them from module presence. Any new candidate requires a new H0 closure, fresh
clean connected D0 binding, and fresh exact F1 approval.
