# S22+ ML036: first shared-V2 run identifies the HCE rejection

ML036 is **consumed** with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.
The shared V2 route selected the reviewed diagnostic/report-v4 module and fresh
key-derived candidate. USB admission and the five-minute same-boot witness
passed. The module stopped at stage 2 because the first HCI-quiescence
predicate observed a nonzero `REG_CONTROLLER_ENABLE` (HCE) value. All later
guard predicates were unobserved. No local UniPro or link command was issued.
One original-A transfer and a health-only continuation restored verified
Android health. No F1 owner remains and this candidate/grant cannot replay.

## Scope and actual application

[Reviewed V2 adoption and preparation](S22PLUS_MAINLINE_UFS_V2_ADOPTION_H0_2026-11-10.md)
were committed as `de098caf38`. The current common/target scope, selected
immutable capability/review and backend v40 governed this run. The stable
ordinary-terminal worker stayed connected. A fresh fixed foreground D0
verified target/root/partition-digest health with no control or transfer.
The operator then returned the exact one-operation 1800-second approval and
confirmed current attendance and usable physical Download recovery.

The fixed Image/module and original H0 evidence were reused; the new observer,
RAM archive, loader and AP had complete fresh qualification. No candidate-
specific policy or executable selector was introduced. The normal-return
extension was not exercised: this stage-two failure is explicitly excluded.
Existing guards and the 300-second witness were unchanged.

## Functional result

Times use the original N launch recorded by the owner.

| Event | N-relative result |
| --- | --- |
| N transfer completed | +2.245 s |
| One attach cue issued | +50.982 s |
| First selected USB census present | +93.964 s |
| First authenticated base sealed | +95.815 s, within 120 s |
| Actual operator completion reply resolved | +104.108 s |
| Same-boot witness | 300.334 s host interval; 300.452 s guest uptime advance |
| One module permit sent | +398.466 s |
| Authenticated module result sealed | +398.497 s |
| Owner stopped new commands | +399.731 s |
| Separate physical Download completion reported | +474.165 s |
| Original-A transfer completed | +479.786 s |
| Complete final health bracket | +583.371 s |

The authenticated base proved the selected mainline kernel/DT/observer,
packaged Debian PID 1 and zero block devices. The next witness used the same
boot and socket before the one-shot permit. The operator reported one USB
reconnection complete; actual physical timing is unmeasured. No observation
window or grant was extended.

The source-bound v4 result was:

- `operation_errno=16`, `stage=2`, `status=NO_PROOF`, `normal_return=false`.
- USB coverage passed on its first attempt, with no trylock failure and the
  held USB reference released: `usb_reason=OK`, `usb_detail=0`.
- `stage2_site=260`: component `HCI`, operation `QUIESCENT`.
- Evaluated mask `1` and failed mask `1`: `HCE=FAIL`; HCS, both doorbells,
  both run/stop conditions, interrupt enable/status, auto-hibernate and both
  reset-pin predicates are `UNOBSERVED`. No HCS value is claimed.
- Fixed RPMh records/claims/triggers/acknowledgments/reclaims and local UniPro
  commands are zero; `link_issued=false`.

The actual retained HCI source uses the nonzero value from its original
`readl(REG_CONTROLLER_ENABLE)` predicate and preserves short-circuit order.
This establishes the first refusing condition on ML036. The report records
no full HCE register value, its origin, a bootloader cause, electrical state
or ML035's historical predicate. Earlier runtime-PM/access-clock preparation
and ordinary boot-time BCM behavior occurred; zero later command counters
are not a claim of zero hardware activity.

## Recovery and evidence

After the closed attach cue and stopped original owner, the operator reported
physical Download. The original owner transferred exact original A once.
The first health bracket's `03-health` read returned 1 with empty stdout and
ADB reporting the selected device absent. Its raw failure remains separate.
Raw A completion was rederived before one existing health-only continuation;
that continuation passed a fresh complete seven-read bracket. No earlier
successful prefix was combined with it and A was not sent again.

The owned NetworkManager profile was removed once and later observed already
absent. H0 close and audit ran with acquisition, socket creation and process
creation blocked. They reopened all **558 indexed raw captures**, both sealed
cue captures, all 82 original/retained task source snapshot entries, exact
transfers, authenticated base/witness/permit/result, final health and cleanup.
The canonical timeline, structured close and no-owner state are retained.

The empty ACK capture is the finalizer's record after a known late module
rejection. No normal Download control was sent; its timeout flag is not a
timeout of a dispatched control. Expected profile-absence statuses and the
failed first health read are separately classified.

Before the first attach-caller spawn, host raw-capture allocation refused a
missing output directory. The directory was created locally, with no caller
spawn or cue before that correction. The caller then ran once, sealed its
output and issued the one timely cue. No device effect or physical instruction
was replayed; this setup failure did not change any source or guard.

Private evidence is under
`workspace/private/outputs/s22plus-ufs-v2-adoption-h0-20261110-1`.
The separate operator-directed boot-journal cleanup remains backed up with
exact-byte verification. The remaining unrelated candidate-list/attachment
work, previous closure/audit and old reviews are preserved. A90 and S20+
received no action.

The next functional question is how the qualified boot handoff and current
UFS initialization order relate to this nonzero HCE condition. That is a new
H0 investigation, not permission to clear HCE, relax the guard or replay ML036.
