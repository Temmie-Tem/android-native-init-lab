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

The S20+ is the controlled-onboarding and staged native-canary target. Unlike
the A90, it starts from stock Android/Magisk and advances through small,
recoverable data-only or boot-overlay experiments before considering global
native PID 1. It also hosts a separately designed bounded autonomous-research
infrastructure whose live activation gates remain intentionally closed.

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

## Partially proven / observed

- **observed — first custom-boot transitions can require factory reset.** The
  same visible first-boot failure/recovery pattern occurred after patched and
  stock transfers, so the cause remains unclassified rather than attributed
  to one image.
- **designed and host-proved — N3-U0 ACM.** The static witness, owned configfs
  gadget, observer, attended journal, concrete backend, atomic evidence owner,
  and execution integration have focused hostile-test and independent-review
  results. The integrated closure is `PASS_GO_NOT_ACTIVE`.
- **designed and host-proved — autonomous research policy/coordinator/public
  health.** The policy state machine, dormant coordinator, and six-command
  public-health parser each have scoped H0 `PASS_GO_NOT_ACTIVE` results. They
  do not form an active connected session.
- **observed — payload-free Download return.** A one-shot return command had
  `rc=0` and the operator saw normal Android, but endpoint behavior prevented
  proving the dispatch source in the original contract. The recovery finalizer
  therefore preserved `exit_dispatch_proven=false` while proving final health.

## Not yet proven

- Global native `/init` running as PID 1 on the S20+.
- N3-U0 at candidate runtime: SSUSB/UDC ownership, ACM enumeration, the exact
  banner, mandatory rollback, and terminal rooted health in one attended run.
- Reproducible stock-kernel byte identity from the retained source/toolchain.
- A complete cause for the factory-reset-dependent boot behavior.
- Any autonomous connected authority. `RESEARCH_ACTIVE`, live authority,
  mechanical activation, and durable-evidence integration remain false.
- Autonomous root profiles, F1, or R1. The proposed autonomous lane does not
  authorize them; F1 and R1 remain attended.

## Current frontier

The native-runtime frontier is N3-U0: a temporary resident-Magisk boot overlay
with one rc file, one static AArch64 ACM witness, one owned configfs gadget,
and a finite versioned banner. Host construction and the multi-layer dormant
execution/evidence stack are independently reviewed, but all activation
booleans remain false. Physical-entry integration, target-contract activation,
fresh preparation, fresh attended approval, live ACM observation, rollback,
and final health are still required.

In parallel, the autonomous-research frontier is infrastructure rather than
authority. The policy, coordinator, and public-health parser are
`PASS_GO_NOT_ACTIVE`. A strict evidence owner, accounting integration, live
action wiring, another review, an attended campaign opening, and mechanical
activation remain ahead. Describing this as “autonomous research active” would
be incorrect.

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

## Architecture summary

```text
stock Samsung Android + resident Magisk root
  -> attended data-only native canary (N1)
  -> temporary boot overlay + owned configfs ACM witness (N3-U0, not active)
  -> retained pre-userspace witness
  -> eventual global native PID 1 (unproved)

separate lane:
attended campaign opening
  -> bounded autonomous public reads / control state machine
  -> READY_FOR_ATTENDED_F1 terminal
```

The second lane is designed to stop before F1 and R1. It is currently dormant.

## Authoritative evidence links

- Current state: [GOAL_S20PLUS.md](../../GOAL_S20PLUS.md)
- Binding target contract: [S20+ target contract](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md)
- Exact onboarding: [D0 onboarding report](../reports/S20PLUS_G986N_ONBOARDING_D0_H0_2026-08-12.md)
- Stock artifacts/source: [artifact acquisition report](../reports/S20PLUS_G986N_STOCK_ARTIFACT_ACQUISITION_H0_2026-08-13.md)
- Native phased design: [S20+ native-init design](../plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md)
- N1 host closure: [native canary N1 report](../reports/S20PLUS_G986N_NATIVE_CANARY_N1_H0_2026-08-15.md)
- USB substrate: [native USB substrate H0/D0](../reports/S20PLUS_G986N_NATIVE_USB_SUBSTRATE_H0_D0_2026-08-16.md)
- N3-U0 construction: [ACM host build](../reports/S20PLUS_G986N_N3U0_ACM_HOST_BUILD_H0_2026-08-16.md)
- N3-U0 current dormant integration: [evidence/execution integration](../reports/S20PLUS_G986N_N3U0_EVIDENCE_EXECUTION_INTEGRATION_H0_2026-08-20.md)
- Autonomous policy state: [autonomous research session H0](../reports/S20PLUS_G986N_AUTONOMOUS_RESEARCH_SESSION_H0_2026-08-21.md)
