# Samsung Galaxy S20+ 5G

**English** · [한국어](S20PLUS.ko.md)

## Device / SoC / kernel

- Device: Samsung Galaxy S20+ 5G (`SM-G986N`, `y2q`, `y2qksx`), exact build
  `G986NKSS8IYC2`.
- SoC: Qualcomm SM8250 (`kona`).
- Kernel: Samsung vendor Linux `4.19.113-27166950`; exact stock source and
  embedded configuration are retained, but a reproducible stock-identical
  kernel build is unproved.

## Role

The S20+ is a staged native-PID1 and recovery research target. Onboarding,
resident Magisk, and retained T2 TWRP recovery are established. A direct-PID1
boot candidate has been transferred and rolled back, but native execution
remains unproved. Current work seeks early-boot evidence independent of ACM.

## Proven capabilities

- **PROVED — exact onboarding and public health.** Bounded D0 runs identified
  one exact authorized target, recorded platform/build/kernel/SELinux/boot
  facts, and issued zero commands to the other devices.
- **PROVED — stock artifact/source acquisition.** The exact firmware, stock
  boot, Samsung kernel source, and embedded final kernel configuration were
  integrity-checked host-side. These artifacts do not themselves prove flash
  readiness or reproducible kernel identity.
- **PROVED — boot-only Magisk bootstrap and rollback.** One bounded candidate
  transferred once and produced healthy rooted Android; the exact stock boot
  rollback transferred once and ended in healthy root-absent Android. The run
  required recovery/factory-reset handling and was not promoted to a resident
  success.
- **PROVED — resident Magisk root.** A later distinct run transferred the
  resident candidate once; a read-only finalizer proved healthy exact-target
  Android with Magisk root and no rollback transfer.
- **PROVED within the N1 transaction history — native canary intent and
  recovery semantics.** The canary wrote its canonical intent but no canary
  result. The preauthorized recovery then disabled it and proved healthy rooted
  Android with replay forbidden. This is a data-only Magisk canary path, not
  native PID 1 or a canary execution PASS.
- **PROVED — stock USB substrate facts.** Bounded source/D0 evidence binds the
  live UDC to `a600000.dwc3` and confirms the required DWC3 MSM, configfs ACM,
  Type-C/PD, extcon, and Samsung notifier components in the exact stock kernel.

- **PROVED — retained T2 TWRP recovery.** One candidate transfer produced the
  exact root-ADB marker and `PROVED_T2_RECOVERY_RETAINED`, with zero rollback
  transfers and TWRP intentionally retained. This is recovery proof, not
  proof of the project's custom native PID 1.
- **PROVED — P0 V3 transfer and healthy rollback.** Candidate and resident
  Magisk rollback each transferred once, with exact rooted-Android final
  health. The native-PID1 result remains `NO_PROOF`.
- **PROVED — bounded classic-fastboot census.** Four fixed read-only requests
  identified the same-target endpoint, followed by healthy Android return.
  This does not prove temporary boot support.

## Partially proven / observed

- **observed — first custom-boot transitions can require factory reset.** The
  same visible first-boot failure/recovery pattern occurred after patched and
  stock transfers, so the cause remains unclassified rather than attributed
  to one image.
- **designed and host-proved — N3-U0 ACM.** The static witness, owned configfs
  gadget, observer, attended journal, concrete backend, atomic evidence owner,
  and execution integration have focused hostile-test and independent-review
  results. That historical H0 closure is `PASS_GO_NOT_ACTIVE`; it is not the
  current P0 result.
- **designed and host-proved — autonomous research policy/coordinator/public
  health.** The policy state machine, dormant coordinator, and six-command
  public-health parser each have scoped H0 `PASS_GO_NOT_ACTIVE` results. They
  do not form an active connected session.
- **observed — payload-free Download return.** A one-shot return command had
  `rc=0` and the operator saw normal Android, but endpoint behavior prevented
  proving the dispatch source in the original contract. The recovery finalizer
  therefore preserved `exit_dispatch_proven=false` while proving final health.

- **observed — P0 V3 had no exact ACM banner.** The full 180-second window
  yielded no accepted banner. The candidate did not retain intermediate stage
  receipts, so the missing banner does not locate a failure or disprove PID 1.
- **designed — early-boot pstore/PMSG observation.** Host analysis identified
  matching ramoops geometry in the stock overlays and retained T2 artifact.
  Live readability and marker retention remain unproved.

## Not yet proven

- Global native `/init` running as PID 1 on the S20+.
- N3-U0 at candidate runtime: SSUSB/UDC ownership, ACM enumeration, the exact
  banner, mandatory rollback, and terminal rooted health in one attended run.
- Reproducible stock-kernel byte identity from the retained source/toolchain.
- A complete cause for the factory-reset-dependent boot behavior.
- Live pstore/PMSG readiness and retention across the required return path.
- Autonomous F1 or R1 operation. Exact reviewed root-health reads exist as an
  attended D0 capability; they are not general root or autonomous authority.

## Current frontier

Snapshot checked on 2026-09-05: P0 V3 is consumed and the owner is dormant.
Its terminal is `NO_PROOF_P0_RETURNED_RESIDENT_HEALTHY`, with one candidate
and one rollback, no replay, and healthy rooted Android return. Retained T2
recovery remains a separate established capability.

The selected next direction is a fixed read-only pstore/PMSG readiness
profile. Static geometry alone does not prove a live backend or retained
markers. The goal is to establish an observation channel before another
direct-PID1 candidate depends on it; exact implementation, review, and
activation status belongs in [GOAL_S20PLUS.md](../../GOAL_S20PLUS.md).

The classic-fastboot census succeeded, but the separate boot-support probe
and fastbootd census did not establish their intended runtime capabilities.
They remain consumed with healthy return. N3-U0 and the early autonomous
policy/coordinator reports are retained H0 work, not current live authority.
The target contract governs each named connected action; conditional
autonomous F1 is not active.

## Major milestones

1. Exact D0 onboarding closed target identity and healthy stock-Android facts.
2. Exact firmware, boot, source, and embedded configuration were retained and
   audited host-side.
3. A boot-only Magisk bootstrap proved transient root and exact stock rollback.
4. A separate resident candidate established persistent healthy Magisk root.
5. The N1 data-only native canary and recovery-aware R1 machinery became an
   active attended capability with bounded historical outcomes.
6. Stock USB substrate evidence selected `a600000.dwc3` and motivated N3-U0.
7. N3-U0 execution/evidence integration and the autonomous policy stack
   reached independently reviewed but explicitly non-active H0 closure.

8. T2 established retained TWRP/root-ADB recovery; the classic-fastboot census
   established its bounded endpoint facts and healthy return.
9. P0 V3 completed transfer, observation, and healthy rollback without native
   PID1 proof; early-boot observation is the next research direction.

## Architecture summary

```text
Samsung Android + resident Magisk root
  + retained T2 TWRP recovery
  -> attended P0 boot-only candidate
    -> bounded ACM observation (no exact banner in V3)
  -> exact resident Magisk rollback + healthy Android

next observation direction (designed, not live-proved):
fixed read-only pstore/PMSG readiness
  -> separately qualified retention witness
  -> better-observed native-PID1 candidate
```

The first flow records the consumed P0 experiment, not native-PID1 success.
The second describes a research direction and grants no device authority.

## Authoritative evidence links

- [Retained T2 recovery](../reports/S20PLUS_G986N_TWRP_T2_CONNECTED_OWNER_H0_2026-08-31.md)
- [P0 V3 terminal](../reports/S20PLUS_G986N_P0_PID1_ODIN_F1_OWNER_H0_2026-09-01.md)
- [Classic-fastboot census](../reports/S20PLUS_G986N_FASTBOOT_GETVAR_CENSUS_2026-09-03.md)
- [Boot-support probe limits](../reports/S20PLUS_G986N_FASTBOOT_BOOT_SUPPORT_F1_H0_2026-09-03.md)
- [Early-boot observation design](../reports/S20PLUS_G986N_EARLY_BOOT_OBSERVATION_H0_2026-09-05.md)
- Current state: [GOAL_S20PLUS.md](../../GOAL_S20PLUS.md)
- Binding target contract: [S20+ target contract](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md)
- Exact onboarding: [D0 onboarding report](../reports/S20PLUS_G986N_ONBOARDING_D0_H0_2026-08-12.md)
- Stock artifacts/source: [artifact acquisition report](../reports/S20PLUS_G986N_STOCK_ARTIFACT_ACQUISITION_H0_2026-08-13.md)
- Native phased design: [S20+ native-init design](../plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md)
- N1 host closure: [native canary N1 report](../reports/S20PLUS_G986N_NATIVE_CANARY_N1_H0_2026-08-15.md)
- USB substrate: [native USB substrate H0/D0](../reports/S20PLUS_G986N_NATIVE_USB_SUBSTRATE_H0_D0_2026-08-16.md)
- N3-U0 construction: [ACM host build](../reports/S20PLUS_G986N_N3U0_ACM_HOST_BUILD_H0_2026-08-16.md)
- Historical N3-U0 dormant integration: [evidence/execution integration](../reports/S20PLUS_G986N_N3U0_EVIDENCE_EXECUTION_INTEGRATION_H0_2026-08-20.md)
- Autonomous policy state: [autonomous research session H0](../reports/S20PLUS_G986N_AUTONOMOUS_RESEARCH_SESSION_H0_2026-08-21.md)
