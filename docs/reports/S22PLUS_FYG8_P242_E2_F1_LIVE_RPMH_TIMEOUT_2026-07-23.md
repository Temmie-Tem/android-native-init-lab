# S22+ FYG8 P2.42 E2 F1 live RPMh timeout

Date: 2026-07-23 KST
Tier: F1 boot-only candidate plus mandatory rollback
Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`
Final state: `CLOSED`
Live authority: consumed

## Result

One exact P2.42 E2 boot-only candidate and its preapproved exact Magisk
rollback were transferred once. The retained observer decoded one exact E2
terminal-failure record at stage `0x7e`, item index 3, detail 110. The source
contract maps that record to the `rpmh` bind gate and `ETIMEDOUT`.

The operator observed no candidate boot loop. Final Android, root, boot,
supporting partitions, and Odin absence passed. The private transaction closed
as `candidate_not_proven_rollback_verified`; its binding and approval cannot be
reused.

## Exact Failure Boundary

The two post-rollback retained reads were byte identical and complete. The
decoded profile-3 record had:

- one exact E2 record for the bound run identity;
- active generation 71 at failure stage `0x7e`, item index 3, detail 110;
- the preceding valid generation 70 slot at progress stage `0x7d`, item
  index 2;
- both A/B slots valid with no fallback;
- zero UNSAT, foreign, malformed, delimiter, partial, historical, or
  unterminated evidence; and
- no integrity issue.

The strict transition model and runtime map the retained stages as follows:

```text
0x40..0x7a  all 59 exact module insertions and prefix verifications passed
0x7b        hwspinlock bind gate passed
0x7c        smem bind gate passed
0x7d        cmd-db bind gate passed
0x7e        rpmh bind gate timed out after the shared 20-second deadline
```

The failed predicate was the exact driver-bind symlink:

```text
/sys/bus/platform/drivers/rpmh/af20000.rsc
```

Detail 110 is the positive retained form of `ETIMEDOUT`. The candidate did not
reach the `gcc-waipio`, `ssusb`, `dwc3-core`, or `udc` gates and did not publish
E2 terminal success.

## What This Proves

This run proves that the direct-PID1 runtime:

- completed the previously proven E1A local-runtime prefix;
- inserted and verified the exact ordered 59-module E2 prefix;
- observed exact hardware-spinlock, SMEM, and command-database driver binds;
  and
- executed the bounded E2 gate loop and recorded its first unresolved bind
  boundary.

It does not prove that `qcom_rpmh` bound to `af20000.rsc`, nor any downstream
clock, SSUSB, DWC3 child, UDC, USB enumeration, ACM bytes, NCM, shell, or
Debian state. Module registration alone remains insufficient evidence of
driver probe success.

## Transfer, Recovery, And Health

The candidate transfer completed once and the transaction reached observation.
The first recovery inventory check occurred before the operator's physical
Download endpoint was available and stopped without another candidate action.
After the exact endpoint appeared, the durable transaction resumed and
transferred the preapproved rollback once.

The first post-rollback endpoint-departure check raced the device transition
and stopped after the completed rollback transfer. A second `--recover` resume
used the durable state to perform final health only; it did not repeat either
transfer.

Final health verified:

- Android boot completion and stopped boot animation;
- the exact expected Magisk boot identity;
- root availability;
- the expected unlocked verified-boot state;
- exact pinned `vendor_boot`, DTBO, and recovery identities; and
- no Odin endpoint remaining.

The append-only journal closed with 19 records and all eight canonical timeline
events in order:

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

## Next Bounded Unit

Do not retry the E2 candidate unchanged. The next unit is H0-only and focused
on the `rpmh_rsc_probe()` prerequisites for the exact FYG8 DT and module:

1. bind stage `0x7d` to the command-database state available when the gate
   passed;
2. enumerate every later `rpmh_rsc_probe()` deferral or failure dependency,
   especially power-domain attachment and provider readiness;
3. compare those requirements against the 59-module direct-PID1 closure and
   stock runtime topology; and
4. design a bounded discriminator that distinguishes missing provider,
   permanent probe failure, and delayed probe without widening to downstream
   USB work.

Any later candidate requires a new H0 closure, clean connected D0 preparation,
and fresh exact approval.
