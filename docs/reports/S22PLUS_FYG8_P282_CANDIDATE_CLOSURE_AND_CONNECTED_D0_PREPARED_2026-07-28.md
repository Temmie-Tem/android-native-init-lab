# S22+ FYG8 P2.82 Candidate Closure And Connected D0 Prepared

Date: 2026-07-28 KST

Status:
`PASS_P282_CONNECTED_D0_PREPARED; F1_INACTIVE`

## Scope

This unit closes the host-only P2.82 build, package, static-closure, offline
Process v2 promotion, ready-manifest, and connected D0 preparation path. It
also records one initial read-only D0 stop and the exact approved baseline
rotation used before the successful D0.

No candidate boot, Download transition, Odin invocation, transfer, or
partition write occurred in this unit.

## Frozen Candidate

- source contract:
  `s22plus-fyg8-p282-prebind-child-reinit-decision-v1`;
- candidate run ID: `5525fada87150ec7d94c208f7875b83f`;
- Full-LTO Builds A/B are byte-identical across `.config`, `Image`,
  `System.map`, `abi.xml`, `vmlinux`, and `vmlinux.symvers`;
- exact `Image` SHA256:
  `ee824e5887da621da2a3340ab7c0defef0de9eac820a1de7087bd6ce1ed99257`;
- exact boot-only AP SHA256:
  `23a9bdee16c122fb7217d1cbb15df6a55c13cce8b7fc7c50cc6030cf04681b3b`;
- exact Magisk rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

GNU linked audit passed with all six linked artifacts equal. Candidate A/B
packages are byte-identical. The independent static result has SHA256
`df87772e5dd71c0d8d5f0f78a12dac5fef6f3e28ff5c43d66fb756ab308686b5`.

## Host Adapter Corrections

Two downstream version-inheritance omissions were found after the frozen
candidate had already passed its own source contract:

1. The canonical candidate static checker applied the dynamic executable
   entrypoint context only to P2.80. P2.82 inherits that P2.80 entrypoint
   adapter, so the checker now verifies the exact P2.82-to-P2.80 ownership
   chain and uses the derived P2.82 `/init` and child entrypoints.
2. Process v2 evidence promotion adapted the 60-row module closure to the
   historical 59-row generic-rootfs auditor only for P2.80. P2.82 inherits
   the same unchanged module plan, so the evidence adapter now verifies the
   P2.82-to-P2.80 ownership chain and reuses the existing P2.57/P2.53 legacy
   views.

Neither correction is in the candidate identity preimage or changes the
kernel, init payload, boot image, AP, run ID, decoder, or source contract.
Focused positive and missing-adapter tests pass.

Because `device_action_f1_evidence_v2.py` is an execution-critical Process v2
source, the already consumed P2.80 ready manifest now fails closed on source
preimage drift. Its regression test records that rejection instead of
pretending the old approval bundle remains reusable.

Offline promotion now passes:

- run-manifest SHA256:
  `14239beb7d49cb5a25115691f9b587d533df91316ee4f6ae456c2782a7595976`;
- static-check SHA256:
  `d9eedfabad1861bd833be4d40f4dd4c9b8d70cc683f040a46ad4eb76d371162b`;
- verdict: `PASS_P234_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION`.

The ready manifest is
`workspace/public/src/device-action/manifests/s22plus_fyg8_p282_process_v2_ready_1.json`.
It binds terminal stage `0x93`, the exact CDC-ACM observer, a 300-second
observation timeout, and the 360-second observer guard qualified by P2.82.
Common-runner host preflight passes with bundle SHA256
`eec2ad38a8447b4bc9ddb73f44b3b1b7b4aa3688bb481a56d022c7c68a887c07`.

## Parent PM Return-Value Check

The P2.83 stock trace produced a non-errno-looking return value from a
`dwc3_msm_runtime_resume` kretprobe. P2.82 does not consume that value.
Its parent-PM results are exact post-call kprobes in
`dwc3_otg_start_peripheral`, reading `x0:s32` after the two
`__pm_runtime_resume` calls at source-bound offsets. The linked audit verifies
those offsets and the intervening instructions do not overwrite `x0`.

The stock kretprobe anomaly therefore does not invert a P2.82 decision.

## Connected D0 And Baseline Rotation

The target was uniquely visible as healthy rooted Android and no Download
endpoint was present. The first D0 captured `/proc/last_kmsg` and found:

- one stale `S22E1L1|` related-family record;
- zero P2.82 exact run-ID occurrences.

The clean-baseline gate correctly stopped before `prepared.json`, approval
binding, Odin, Download transition, or any device write. This is retained
history contamination, not evidence that P2.82 ran.

The operator then gave one fresh exact D1 approval for one Android `adb reboot`.
The same model and build returned with `sys.boot_completed=1`, ADB, and root.
No Download or Odin action occurred. This rotation replaced the stale
last-boot history.

The second connected D0 against the unchanged manifest passed:

- bundle SHA256:
  `eec2ad38a8447b4bc9ddb73f44b3b1b7b4aa3688bb481a56d022c7c68a887c07`;
- D0 result SHA256:
  `49e8c31c5ee36ea392b3cd2166b0a48b21d4e6f8078dc77b72a4191312e0a67d`;
- approval binding SHA256:
  `e19ce4f6d719333c8365d903f6fadb17aa4619565f6ccb12af6f1bba8a52418d`;
- `device_writes=false`, `odin_invoked=false`, `partition_transfer=false`,
  `f1_authorized=false`, and `live_authorized=false`.

The prepared run and active approval token remain private. The next step is
the operator's fresh exact F1 approval. Until that token is returned and the
unchanged binding is reopened, no candidate or rollback transfer is
authorized.
