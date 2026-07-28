# S22+ FYG8 P2.82 F1 None-Readback Boundary

Date: 2026-07-28 KST

Status:
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK; TRANSACTION_CLOSED`

## Scope

This report records one authorized P2.82 Process v2 candidate attempt, its
bounded observation, the mandatory exact Magisk rollback, and final health.
It does not authorize a replay or a successor F1.

Raw device and host evidence remains under `workspace/private/`. This report
contains no device serial, USB identity, PARTUUID, address, or raw log.

## Exact Transaction

- candidate contract:
  `s22plus-fyg8-p282-prebind-child-reinit-decision-v1`;
- candidate run ID: `5525fada87150ec7d94c208f7875b83f`;
- candidate boot-only AP SHA256:
  `23a9bdee16c122fb7217d1cbb15df6a55c13cce8b7fc7c50cc6030cf04681b3b`;
- exact Magisk rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- approval binding SHA256:
  `e19ce4f6d719333c8365d903f6fadb17aa4619565f6ccb12af6f1bba8a52418d`.

The candidate and rollback each completed exactly one boot-only Odin transfer.
The candidate was not replayed. The operator observed a successful candidate
boot with no boot loop.

## Retained Result

Two post-rollback reads are byte-identical and contain one exact P2.82 record:

```text
generation 86: stage 0x8d, outcome progress, detail 0
generation 87: stage 0x8e, outcome failure,  detail 0xc10
```

The generated contract decodes `0xc10` as
`none-readback-not-reached`.

The exact control flow establishes:

1. The unchanged P2.80 prefix again reached initial parent `peripheral` mode
   and exact `/sys/class/udc/a600000.dwc3` membership.
2. The bounded role helper completed its exact NONE-write operation without a
   helper receipt contradiction or synchronous errno.
3. The parent mode did not become exact `none\n` before the shared 30-second
   stop deadline.
4. The classifier stopped at that first failed boundary as designed.

This result does not establish whether the NONE state was rejected because of
a DP session, asynchronously reasserted by another role producer, or accepted
without the expected worker-visible state transition. It also does not reach
or test child suspend, DEVICE restart, child runtime resume, femto-HS
reinitialization, configfs UDC bind, final UDC state/speed, or host ACM receipt.

The candidate observer ran for its full 300-second bound and found no accepted
endpoint. That negative result is expected after the runtime stopped before
configfs UDC bind; it is not a separate physical-enumeration finding.

## Rollback And Health

The preauthorized rollback completed without candidate replay. Final checks
passed for:

- Android boot completion and stopped boot animation;
- FYG8 stock kernel identity;
- root access;
- exact boot rollback identity;
- recovery, vendor_boot, and DTBO supporting-partition identities; and
- absence of an Odin endpoint.

All eight canonical timeline events are present in order. The durable
transaction state is `CLOSED`, recovery is not required, and the final verdict
is `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.

## Disposition

P2.82 provided a useful earlier boundary rather than E3 proof. Do not repeat
the candidate and do not modify the later child-reinit classifier yet.

The next unit is host-only and focused on the exact parent NONE boundary:

```text
mode_store("none")
  -> dwc3_msm_set_role(USB_ROLE_NONE)
  -> vbus_active / DP-session condition
  -> dwc3_ext_event_notify()
  -> B_SESS_VLD clear
  -> dwc3_otg_sm_work()
```

It must distinguish synchronous acceptance, DP-session refusal, external role
reassertion, and worker scheduling from exact FYG8 source and the frozen
P2.82 implementation. A physical cable replug is not an accepted substitute:
the candidate had not reached gadget bind, and replug would add Type-C/VBUS
producers without proving the missing exact NONE transition.
