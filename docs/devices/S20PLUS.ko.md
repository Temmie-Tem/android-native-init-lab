# Samsung Galaxy S20+ 5G

[English](S20PLUS.md) · **한국어**

## 기기 / SoC / kernel

- 기기: Samsung Galaxy S20+ 5G (`SM-G986N`, `y2q`, `y2qksx`), exact build
  `G986NKSS8IYC2`.
- SoC: Qualcomm SM8250 (`kona`).
- Kernel: Samsung vendor Linux `4.19.113-27166950`. Exact stock source와
  embedded configuration은 보존돼 있지만 reproducible stock-identical kernel
  build는 unproved(미증명)입니다.

## 역할

S20+는 controlled-onboarding과 staged native-canary 대상입니다. A90과 달리 stock
Android/Magisk에서 시작해, global native PID 1을 고려하기 전에 작고 recoverable한
data-only 또는 boot-overlay experiment를 거칩니다. 별도로 설계한 bounded
autonomous-research infrastructure도 있지만 live activation gate는 의도적으로
닫혀 있습니다.

## 증명된 capability

- **PROVED(증명됨) — exact onboarding과 public health.** Bounded D0 run이 exact
  authorized target 하나를 식별하고 platform/build/kernel/SELinux/boot fact를
  기록했으며 다른 기기에 보낸 command는 0개였습니다.
- **PROVED(증명됨) — stock artifact/source acquisition.** Exact firmware, stock
  boot, Samsung kernel source, embedded final kernel configuration을 host-side에서
  integrity-check했습니다. 이 artifact 자체는 flash readiness나 reproducible
  kernel identity를 증명하지 않습니다.
- **PROVED(증명됨) — boot-only Magisk bootstrap과 rollback.** 하나의 bounded
  candidate가 한 번 transfer돼 healthy rooted Android를 만들었고, exact stock
  boot rollback이 한 번 transfer돼 healthy root-absent Android로 끝났습니다. 이
  run은 recovery/factory-reset handling이 필요했으며 resident success로
  승격되지 않았습니다.
- **PROVED(증명됨) — resident Magisk root.** 이후 별도의 run에서 resident
  candidate가 한 번 transfer됐고, read-only finalizer가 rollback transfer 없이
  Magisk root가 동작하는 healthy exact-target Android를 증명했습니다.
- **PROVED(증명됨), N1 transaction history 내부에 한정 — native canary intent와
  recovery semantics.** Canary는 canonical intent를 썼지만 canary result는 쓰지
  못했습니다. Preauthorized recovery가 canary를 disable하고 replay가 금지된
  상태에서 healthy rooted Android를 증명했습니다. 이는 data-only Magisk canary
  path이며 native PID 1이나 canary execution PASS가 아닙니다.
- **PROVED(증명됨) — stock USB substrate fact.** Bounded source/D0 evidence는 live
  UDC identity가 `a600000.dwc3`임을 고정하고, 필요한 DWC3 MSM, configfs ACM,
  Type-C/PD, extcon, Samsung notifier component가 exact stock kernel에 있음을
  확인했습니다.

## 부분 증명 / 관측

- **observed(관측됨) — 첫 custom-boot transition은 factory reset이 필요할 수
  있습니다.** Patched transfer와 stock transfer 뒤에 같은 visible first-boot
  failure/recovery pattern이 발생했으므로 cause는 특정 image에 귀속되지 않고
  unclassified 상태입니다.
- **designed(설계됨), host-proved — N3-U0 ACM.** Static witness, owned configfs
  gadget, observer, attended journal, concrete backend, atomic evidence owner,
  execution integration에 focused hostile-test와 independent-review result가
  있습니다. Integrated closure는 `PASS_GO_NOT_ACTIVE`입니다.
- **designed(설계됨), host-proved — autonomous research policy/coordinator/public
  health.** Policy state machine, dormant coordinator, six-command public-health
  parser는 각각 범위가 제한된 H0 `PASS_GO_NOT_ACTIVE` result를 가집니다. 이들이
  active connected session을 구성하지는 않습니다.
- **observed(관측됨) — payload-free Download return.** One-shot return command는
  `rc=0`이었고 operator가 normal Android를 관측했지만, endpoint behavior 때문에
  original contract에서 dispatch source를 증명하지 못했습니다. 따라서 recovery
  finalizer는 final health를 증명하면서도 `exit_dispatch_proven=false`를
  보존했습니다.

## 아직 증명되지 않은 것

- S20+에서 global native `/init`가 PID 1로 실행되는 것.
- Candidate runtime의 N3-U0: SSUSB/UDC ownership, ACM enumeration, exact banner,
  mandatory rollback, terminal rooted health가 하나의 attended run에서 닫히는 것.
- Retained source/toolchain으로 reproducible stock-kernel byte identity를 만드는 것.
- Factory-reset-dependent boot behavior의 complete cause.
- 모든 autonomous connected authority. `RESEARCH_ACTIVE`, live authority,
  mechanical activation, durable-evidence integration은 false 상태입니다.
- Autonomous root profile, F1, R1. 제안된 autonomous lane은 이를 authorize하지
  않으며 F1과 R1은 attended 상태를 유지합니다.

## 현재 프론티어

Native-runtime 프론티어는 N3-U0입니다. 하나의 rc file, static AArch64 ACM
witness, owned configfs gadget, finite versioned banner를 포함하는 temporary
resident-Magisk boot overlay입니다. Host construction과 multi-layer dormant
execution/evidence stack은 independent review를 받았지만 모든 activation boolean은
false 상태입니다. Physical-entry integration, target-contract activation, fresh
preparation, fresh attended approval, live ACM observation, rollback, final health가
여전히 필요합니다.

병렬로 autonomous-research 프론티어는 authority가 아니라 infrastructure입니다.
Policy, coordinator, public-health parser는 `PASS_GO_NOT_ACTIVE`입니다. Strict
evidence owner, accounting integration, live action wiring, 추가 review, attended
campaign opening, mechanical activation이 남아 있습니다. 이를 “autonomous research
active”라고 설명하면 부정확합니다.

## 주요 milestone

1. Exact D0 onboarding이 target identity와 healthy stock-Android fact를 닫았습니다.
2. Exact firmware, boot, source, embedded configuration을 retain하고 host-side에서
   audit했습니다.
3. Boot-only Magisk bootstrap이 transient root와 exact stock rollback을
   증명했습니다.
4. 별도의 resident candidate가 persistent healthy Magisk root를 확립했습니다.
5. N1 data-only native canary와 recovery-aware R1 machinery가 bounded historical
   outcome을 가진 active attended capability가 됐습니다.
6. Stock USB substrate evidence가 `a600000.dwc3`를 선택하고 N3-U0에 근거를
   제공했습니다.
7. N3-U0 execution/evidence integration과 autonomous policy stack이 independent
   review를 받은 명시적 non-active H0 closure에 도달했습니다.

## Architecture 요약

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

두 번째 lane은 F1과 R1 전에 멈추도록 designed(설계됨)됐으며 현재 dormant입니다.

## 정본 증거 링크

- 현재 상태: [GOAL_S20PLUS.md](../../GOAL_S20PLUS.md)
- Binding target contract: [S20+ target contract](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md)
- Exact onboarding: [D0 onboarding report](../reports/S20PLUS_G986N_ONBOARDING_D0_H0_2026-08-12.md)
- Stock artifact/source: [artifact acquisition report](../reports/S20PLUS_G986N_STOCK_ARTIFACT_ACQUISITION_H0_2026-08-13.md)
- Native phased design: [S20+ native-init design](../plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md)
- N1 host closure: [native canary N1 report](../reports/S20PLUS_G986N_NATIVE_CANARY_N1_H0_2026-08-15.md)
- USB substrate: [native USB substrate H0/D0](../reports/S20PLUS_G986N_NATIVE_USB_SUBSTRATE_H0_D0_2026-08-16.md)
- N3-U0 construction: [ACM host build](../reports/S20PLUS_G986N_N3U0_ACM_HOST_BUILD_H0_2026-08-16.md)
- N3-U0 current dormant integration: [evidence/execution integration](../reports/S20PLUS_G986N_N3U0_EVIDENCE_EXECUTION_INTEGRATION_H0_2026-08-20.md)
- Autonomous policy state: [autonomous research session H0](../reports/S20PLUS_G986N_AUTONOMOUS_RESEARCH_SESSION_H0_2026-08-21.md)
