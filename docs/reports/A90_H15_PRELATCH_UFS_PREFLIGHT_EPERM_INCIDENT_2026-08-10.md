# A90 H15 pre-latch UFS preflight EPERM incident

Date: 2026-08-10
Target: Samsung Galaxy A90 5G only
Classification: attended D1 handoff refusal before latch

## Incident

The exact H15 D1 approval was consumed and one combined arm-plus-reboot command
was dispatched. The rebooted H15 resident proved the asynchronous Wi-Fi helper
in a private mount namespace and the shared network namespace, prepared NCM,
then refused the UFS read-only preflight with `rc=-1` before creating the
one-shot latch. The operator-visible status showed automatic-handoff error E1.

The durable journal contains exactly open, arm-reboot intent, dispatch result,
and observer records. Arm and reboot dispatch counts are one and are never
replayed. The device returned to exact H15 native health with self-test
`11/1/0`, but its durable state is `binding=1 enable=1 latch=0`. The target
contract classifies that state as recovery-pending.

## Evidence and containment

- Same-boot logs prove helper namespace readiness in 10 ms, NCM handoff
  preparation, then `userdata read-only preflight failed rc=-1` before latch.
- No H15 UFS qualification marker, latch, switch-root marker, payload,
  partition write, flash, SD staging, or userdata write was produced by D1.
- A later host parser read was contaminated by one stale serial fragment and
  failed before final-health publication. Read-only continuation then proved
  exact H15 identity, health, and `enable=1/latch=0`.
- Reboot, arm, and handoff replay are prohibited. The operator must not reboot
  until the exact enable marker is recovered.

## Recovery requirement

Recovery is limited to one reviewed attended primitive that proves the consumed
D1 prefix and exact H15 `1,0` state, preserves the byte-exact mode-0600 enable
record privately, durably records intent, removes only that enable file with a
fixed unlink-and-sync command, and closes only on `enable=0/latch=0` plus exact
H15 health. An uncertain response is reconciled read-only and never resent.

This incident invalidates reuse of the earlier H15 capability qualification for
another live candidate or D1 attempt. The root cause and an H16 replacement are
separate host-only work after exact recovery. S22+ received no command.
