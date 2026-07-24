# S22+ FYG8 P2.55 connected D0 prepared pass

Date: 2026-07-24 KST
Tier: D0, preceded by one bounded D1 normal reboot
Status: `PASS_P255_CONNECTED_D0_PREPARED_F1_INACTIVE`
F1 authority: none

## Result

The P2.55 typed-evidence verifier fix left the P2.54 kernel, userspace,
boot-only candidate, rollback, and candidate identity unchanged. Exact
host-ready validation passed without a kernel rebuild.

The first connected read-only preparation stopped because the retained
baseline contained a historical related family. It created no prepared
binding, transaction, Odin session, Download request, or transfer.

One operator-preapproved normal Android reboot then ran exactly once without a
payload or Download request. The target disconnected and the same target
reconnected. The D1 recorder immediately requested the full strict property
set; an empty early-boot `sys.boot_completed` value was rejected as malformed,
so that recorder did not close its timeline. No second reboot was requested.
A private incident record preserves the incomplete recorder result instead of
repeating the transition.

Read-only polling subsequently observed completed boot and stopped boot
animation. A fresh connected D0 then passed:

- exact target and FYG8 identity;
- Android boot, Magisk root, kernel, boot, and supporting-partition health;
- exact candidate and rollback boot-only AP identity;
- a complete retained read with zero related family and exact-marker counts;
- Odin endpoint absence; and
- the current execution-critical source closure.

The new private prepared binding was reopened through the production
`load_prepared()` path after documentation-only follow-up work. Candidate,
rollback, D0 evidence, private target binding, and execution closure all
revalidated. No transaction directory exists.

## Safety State

The prepared result reports:

```text
device_contact=true
device_writes=false
reboot_requested=false
odin_invoked=false
partition_transfer=false
f1_authorized=false
live_authorized=false
```

The earlier D1 transition did execute one normal reboot; the values above are
the separate D0 prepared record and correctly show that preparation itself was
read-only. The incomplete D1 timeline is a reporting deviation, not evidence
of a second reboot or a device failure. Final health is independently bound by
the passing D0 result.

## Next Gate

The standing operator approval explicitly excludes flashing a new build. The
prepared record grants no F1 authority. One candidate attempt and its
mandatory rollback may start only after the operator sends the exact fresh
approval token emitted by this unconsumed binding. The token remains outside
tracked files.
