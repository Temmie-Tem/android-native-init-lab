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

S20+는 단계별 native-PID1과 recovery 연구 대상입니다. Onboarding, resident
Magisk, retained T2 TWRP recovery를 확립했습니다. Direct-PID1 boot candidate는
전송·rollback됐지만 native 실행은 미증명입니다. 현재는 ACM과 독립적인 초기
부팅 증거를 확보하는 방향을 연구합니다.

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

- **PROVED(증명됨) — retained T2 TWRP recovery.** Candidate 1회 전송으로 exact
  root-ADB marker와 `PROVED_T2_RECOVERY_RETAINED`를 얻었습니다. Rollback은
  0회이며 TWRP를 의도적으로 유지했습니다. 이는 recovery 증명으로, 프로젝트의
  custom native PID 1 증명은 아닙니다.
- **PROVED(증명됨) — P0 V3 전송과 정상 rollback.** Candidate와 resident Magisk
  rollback이 각각 한 번 전송됐고 exact rooted-Android final health가 통과했습니다.
  Native-PID1 결과는 여전히 `NO_PROOF`입니다.
- **PROVED(증명됨) — bounded classic-fastboot census.** 네 고정 read-only request로
  같은 기기의 endpoint를 식별하고 healthy Android로 복귀했습니다. Temporary boot
  support를 증명한 것은 아닙니다.

## 부분 증명 / 관측

- **observed(관측됨) — 첫 custom-boot transition은 factory reset이 필요할 수
  있습니다.** Patched transfer와 stock transfer 뒤에 같은 visible first-boot
  failure/recovery pattern이 발생했으므로 cause는 특정 image에 귀속되지 않고
  unclassified 상태입니다.
- **designed(설계됨), host-proved — N3-U0 ACM.** Static witness, owned configfs
  gadget, observer, attended journal, concrete backend, atomic evidence owner,
  execution integration에 focused hostile-test와 independent-review result가
  있습니다. 그 역사적 H0 closure는 `PASS_GO_NOT_ACTIVE`이며 현재 P0 결과가 아닙니다.
- **designed(설계됨), host-proved — autonomous research policy/coordinator/public
  health.** Policy state machine, dormant coordinator, six-command public-health
  parser는 각각 범위가 제한된 H0 `PASS_GO_NOT_ACTIVE` result를 가집니다. 이들이
  active connected session을 구성하지는 않습니다.
- **observed(관측됨) — payload-free Download return.** One-shot return command는
  `rc=0`이었고 operator가 normal Android를 관측했지만, endpoint behavior 때문에
  original contract에서 dispatch source를 증명하지 못했습니다. 따라서 recovery
  finalizer는 final health를 증명하면서도 `exit_dispatch_proven=false`를
  보존했습니다.

- **observed(관측됨) — P0 V3에서 exact ACM banner를 얻지 못했습니다.** 전체
  180초 관측에서 인정된 banner가 없었습니다. Candidate가 중간 stage receipt를
  보존하지 않았으므로 banner 부재만으로 실패 위치나 PID 1 실행 여부를 판정할 수 없습니다.
- **designed(설계됨) — 초기 부팅 pstore/PMSG 관측.** Host 분석은 stock overlay와
  retained T2 artifact의 ramoops geometry가 일치함을 확인했습니다. Live readability와
  marker retention은 미증명입니다.

## 아직 증명되지 않은 것

- S20+에서 global native `/init`가 PID 1로 실행되는 것.
- Candidate runtime의 N3-U0: SSUSB/UDC ownership, ACM enumeration, exact banner,
  mandatory rollback, terminal rooted health가 하나의 attended run에서 닫히는 것.
- Retained source/toolchain으로 reproducible stock-kernel byte identity를 만드는 것.
- Factory-reset-dependent boot behavior의 complete cause.
- Live pstore/PMSG readiness와 필요한 복귀 경로를 거치는 retention.
- Autonomous F1 또는 R1 operation. Exact reviewed root-health read는 attended
  D0 capability로 존재하지만 일반 root 권한이나 자율 권한이 아닙니다.

## 현재 프론티어

2026-09-05 확인 기준으로 P0 V3는 소비됐고 owner는 dormant입니다. Terminal은
`NO_PROOF_P0_RETURNED_RESIDENT_HEALTHY`로, candidate와 rollback 각 1회, replay
없음, healthy rooted Android 복귀를 남겼습니다. Retained T2 recovery는 별도로
확립된 capability입니다.

다음 선택 방향은 고정 read-only pstore/PMSG readiness profile입니다. Static
geometry만으로 live backend나 marker retention이 증명되지는 않습니다. 다음
direct-PID1 candidate가 의존하기 전에 관측 채널을 확보하는 것이 목표이며,
정확한 구현·검토·활성화 상태는 [GOAL_S20PLUS.md](../../GOAL_S20PLUS.md)를 따릅니다.

Classic-fastboot census는 성공했지만 별도 boot-support probe와 fastbootd census는
목표 runtime capability를 확립하지 못했습니다. 해당 시도들은 healthy return과 함께
소비됐습니다. N3-U0와 초기 autonomous policy/coordinator 보고서는 보존된 H0 작업이며
현재 live authority가 아닙니다. 각 connected action은 target contract를 따르고,
조건부 autonomous F1은 활성화되지 않았습니다.

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

8. T2가 retained TWRP/root-ADB recovery를 확립했고, classic-fastboot census가
   bounded endpoint fact와 healthy return을 증명했습니다.
9. P0 V3가 native PID1 증명 없이 전송·관측·정상 rollback을 완료했으며, 초기 부팅
   관측이 다음 연구 방향입니다.

## Architecture 요약

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

첫 흐름은 소비된 P0 실험 기록이며 native-PID1 성공이 아닙니다. 두 번째는 연구
방향을 설명하며 기기 권한을 부여하지 않습니다.

## 정본 증거 링크

- [Retained T2 recovery](../reports/S20PLUS_G986N_TWRP_T2_CONNECTED_OWNER_H0_2026-08-31.md)
- [P0 V3 terminal](../reports/S20PLUS_G986N_P0_PID1_ODIN_F1_OWNER_H0_2026-09-01.md)
- [Classic-fastboot census](../reports/S20PLUS_G986N_FASTBOOT_GETVAR_CENSUS_2026-09-03.md)
- [Boot-support probe 한계](../reports/S20PLUS_G986N_FASTBOOT_BOOT_SUPPORT_F1_H0_2026-09-03.md)
- [초기 부팅 관측 설계](../reports/S20PLUS_G986N_EARLY_BOOT_OBSERVATION_H0_2026-09-05.md)
- 현재 상태: [GOAL_S20PLUS.md](../../GOAL_S20PLUS.md)
- Binding target contract: [S20+ target contract](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md)
- Exact onboarding: [D0 onboarding report](../reports/S20PLUS_G986N_ONBOARDING_D0_H0_2026-08-12.md)
- Stock artifact/source: [artifact acquisition report](../reports/S20PLUS_G986N_STOCK_ARTIFACT_ACQUISITION_H0_2026-08-13.md)
- Native phased design: [S20+ native-init design](../plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md)
- N1 host closure: [native canary N1 report](../reports/S20PLUS_G986N_NATIVE_CANARY_N1_H0_2026-08-15.md)
- USB substrate: [native USB substrate H0/D0](../reports/S20PLUS_G986N_NATIVE_USB_SUBSTRATE_H0_D0_2026-08-16.md)
- N3-U0 construction: [ACM host build](../reports/S20PLUS_G986N_N3U0_ACM_HOST_BUILD_H0_2026-08-16.md)
- 역사적 N3-U0 dormant integration: [evidence/execution integration](../reports/S20PLUS_G986N_N3U0_EVIDENCE_EXECUTION_INTEGRATION_H0_2026-08-20.md)
- Autonomous policy state: [autonomous research session H0](../reports/S20PLUS_G986N_AUTONOMOUS_RESEARCH_SESSION_H0_2026-08-21.md)
