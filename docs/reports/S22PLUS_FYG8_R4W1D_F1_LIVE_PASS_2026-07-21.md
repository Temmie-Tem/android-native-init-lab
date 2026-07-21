# S22+ FYG8 R4W1-D direct PID1 live pass

Date: 2026-07-21 KST
Scope: one approved boot-only candidate and mandatory exact boot-only rollback
Status: PASS, transaction closed

## Verdict

`PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK`

The exact R4W1-D compact retained proof establishes that the rebuilt kernel
successfully executed the intended native `/init` as PID 1. The exact Magisk
boot-only rollback then returned the device to healthy FYG8 Android. The strict
result validator reopened the complete journal, transfer receipts, state,
timeline, final health, and both retained observers.

## Binding and artifacts

- manifest: `s22plus-fyg8-r4w1d-process-v2-ready-1`;
- bundle SHA256:
  `872da8ec972a230d928779cc78ba52cfc4d2a12f07013559baa7dae93614eb4e`;
- approval binding SHA256:
  `16640f551d082dd89e8de57da7572c42e235abd30d0733fa050c76aa46530392`;
- candidate AP SHA256:
  `e35cee4c81966f7b3955af60dfb4921edbb9a07f7a10336d6cc9fddfa915d649`;
- exact Magisk rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- private run:
  `workspace/private/runs/device-action-f1-live-v2/f1-2026-07-21T100308522934Z-1784628188522972001`.

Candidate and rollback each have exactly one transfer attempt. Both regular-path
Odin invocations returned rc=0 with empty stderr and
`classification=odin_transfer_completed`. The candidate receipt SHA256 is
`e6fdb93a30249ec384ea0938b7659e9f20930ff860e53c932b5992b79add516f`;
the rollback receipt SHA256 is
`af0d03d9fe251d7c94dd2a6127961b501271349815ce31712571cd78dcbb22b8`.

## Native PID1 proof

After more than 120 seconds of candidate dwell, the operator observed a stable
screen with no boot loop. Following rollback, two independent complete reads of
`/proc/last_kmsg` were byte-identical:

- size: 2,097,136 bytes each;
- SHA256:
  `ed4a24e7df05b86fc5f7e9d3b213175beab911cee468a82cf89053d9bd0aac5a`;
- exact marker count: one;
- marker family count: one;
- foreign, historical, delimiter-mismatch, partial-head, partial-tail, and
  unterminated counts: zero;
- classification: `EXACT_MARKER_PRESENT`;
- accepted: true.

The exact marker is:

`[[S22P1D|0e13f28e8558dde01ce3345f16408673]]`

Its kernel-side contract emits the marker only after successful
`kernel_execve("/init")` and `task_pid_nr(current) == 1`, using the exact pinned
carrier boot and watchdog init identities. The live marker therefore closes the
direct native-PID1 proof rung.

## Rollback and final health

Final verification proved:

- Android boot complete and boot animation stopped;
- Magisk root available;
- exact known Magisk boot SHA256
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- stock vendor_boot SHA256
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`;
- stock DTBO SHA256
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- stock recovery SHA256
  `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`;
- orange verified-boot state; and
- no Odin endpoint.

The canonical timeline contains exactly, in order:

`live_session_start`, `candidate_flash_start`, `candidate_flash_done`,
`candidate_boot_ready`, `rollback_flash_start`, `rollback_flash_done`,
`rollback_boot_ready`, `live_session_end`.

The strict final result is 4,944 bytes, SHA256
`28e4bcbf25644379f1f9c184fbcfcb34fdedcf2da74740237bba91a97c0da156`.
Journal state is `CLOSED`; `recovery_required=false`.

## Process incident

After each successful transfer, the completed Odin `--reboot` removed its
USBFS node. Endpoint-session teardown then raised
`Odin endpoint identity observation failed` for the departed path. In both
cases the transfer result had already been durably recorded as completed. The
first recovery call advanced candidate observation without a second candidate
attempt; the second recovery call recognized the durable rollback receipt and
performed no second rollback transfer. A final resume verified health and
closed the transaction.

This false post-transfer error did not weaken or create the PASS. The strict
validator independently requires both transfer receipts, exact marker evidence,
rollback completion, final health, and canonical timeline. The endpoint-session
teardown behavior remains a reusable Process v2 defect to fix before the next
candidate.
