# Samsung Galaxy S22+ FYG8

[English](S22PLUS.md) · **한국어**

## 기기 / SoC / kernel

- 기기: Samsung Galaxy S22+ (`SM-S906N`, `g0q`), exact firmware
  `S906NKSS7FYG8`.
- SoC: Qualcomm SM8450 / Snapdragon 8 Gen 1 (`taro`).
- Kernel: source-matched Samsung vendor Linux
  `5.10.226-android12-9-30958166-abS906NKSS7FYG8`.

## 역할

S22+는 source-matched rebuilt-kernel과 direct-native-PID1 연구 대상입니다.
Android userspace 없이 bounded native-PID1 USB 통신과 인증된 고정 명령 실행을
확립했습니다. 현재는 세션 안정성과 실패 관측을 개선합니다. 통신 기능의 증명과
USB/Max77705의 상세 원인 설명은 별도로 판정합니다.

## 증명된 capability

- **PROVED(증명됨) — reproducible source-matched kernel build.** Rebuilt
  Full-LTO kernel은 예상된 format과 identity를 가지며, bounded live candidate가
  clean rollback 전에 exact FYG8 Android userspace를 boot했습니다.
- **PROVED(증명됨) — rebuilt-kernel early Android witness.** 이후 guarded
  candidate가 예상된 early Android PID1 path에 도달했고, accepted acquisition
  channel을 통해 retained marker를 보존했습니다.
- **PROVED(증명됨) — direct native `/init` exec acceptance.** R4W1-D는 current가
  PID 1인 동안 `kernel_execve("/init")` 성공 이후 exact retained marker 하나를
  생성했습니다. 이는 kernel이 의도한 native executable을 PID 1로 받아들였음을
  증명합니다. 그 역사적 marker만으로 첫 userspace instruction은 증명되지
  않았으며, 아래의 후속 native-PID1 통신 결과가 runtime 실행을 확립했습니다.
- **PROVED(증명됨) — native-PID1 ACM 도달과 양방향 명령.** P3.25는 exact
  native banner를 보존했습니다. P3.26은 고정 양방향 교환과 BusyBox child 실행을,
  P3.27은 세 개의 framed 고정 명령과 정상 종료를 증명했습니다.
- **PROVED(증명됨) — 인증된 bounded session.** P3.30은 인증과 세 고정 명령을
  완료했습니다. P3.35는 한 run에서 인증된 세 세션을 증명했습니다. 두 세션은 같은
  tty descriptor, 세 번째는 계획된 host close/reopen 이후였으며, 명령 9회가 모두
  exit 0과 정상 세션 종료를 남겼습니다. 이 성공 run들은 exact rollback과 rooted
  FYG8 final health도 통과했습니다.
- **PROVED(증명됨) — recovery-safe experiment mechanics.** Process-v2 run은
  transfer, observation, rollback, final health를 구분하고 candidate no-replay를
  보존합니다. 이후 여러 USB experiment는 candidate success를 승격하지 않은 채
  no-proof 또는 refutation으로 안전하게 종료됐습니다.
- **PROVED(증명됨), host-side 한정 — 역사적 P3.19 USB plan static closure.** 해당
  plan은 73개 row, 누락된 declared dependency 0개, ordering violation 0개, 72개
  vendor row의 exact module byte, built-in DWC3/gadget core를 가집니다. 이는 static
  membership/order/ABI 결과에만 해당합니다.
- **PROVED(증명됨) — P3.19 recovered final health.** Exact candidate와 rollback이
  각각 한 번 전송됐고 journal이 닫혔으며 rooted FYG8 Android health가
  통과했습니다. Formal result는 USB 성공이 아닌 `NO_PROOF_OBSERVER`이며
  candidate는 replay 없이 소비됐습니다.

## 부분 증명 / 관측

- **observed(관측됨) — stock Android와 stock first-stage CDC ACM은
  functional합니다.** Bounded stock control이 framed exchange 128회를 완료했고,
  early Android boot service도 같은 결과를 반복했습니다. 어느 쪽도 native-PID1
  USB bring-up을 증명하지 않습니다.
- **observed(관측됨) — 과거 direct-native run에는 인정된 ACM receipt가 없었습니다.**
  항상 endpoint가 없었다는 뜻은 아닙니다. P3.23/P3.24는 이후 host selector와 tty
  property 결함을 국한했습니다. 소비된 no-proof 결과는 P3.25의 인정된 native
  banner와 구분합니다.
- **observed(관측됨) — 후속 세션 실패가 남아 있습니다.** P3.35의 늦은 idle action은
  인증·명령 실행 전에 uncertain으로 끝났습니다. P3.36–P3.39는 native banner를
  보존했지만 인증된 세션 성공은 없었습니다. P3.39에서는 host collector가 추가
  실패 diagnostic을 읽기 전에 멈추는 문제가 확인됐습니다.
- **designed(설계됨) — 초기 OPEN 실패 수집 successor.** P3.40 host 작업은 기존
  diagnostic stream을 대상으로 하며 새로운 live 성공이 아닙니다.
- **PROVED(증명됨), P3.15 내부에 한정 — restart-side functional witness가
  실행됐습니다.** 같은 run은 clean four-outer-work model을 refute했습니다. USB2
  connector pull-up, attachment, transport는 증명하지 않았습니다.
- **observed(관측됨) — stock recovery는 SSUSB mode에 `peripheral`을 쓰고
  `a600000.dwc3`를 기다릴 수 있습니다.** 이 positive control은 direct-role design
  shape를 뒷받침하지만 다른 runtime/Image를 사용하므로 candidate bind를
  증명하지 않습니다.

## 아직 증명되지 않은 것

- **unproved(미증명) —** bounded 성공 세션 범위를 넘는 안정적인 long-idle/reopen.
- 범용 interactive PTY/shell, caller-selected command, file transfer,
  persistent service, autonomous F1 operation.
- USB/Max77705 bring-up과 natural UCSI/PMIC-GLINK role path의 완전한 원인 설명.
  End-to-end 통신 성공이 모든 중간 driver event를 독립 측정하거나 supplemental
  Carrier 문제를 해결하지는 않습니다.
- 후속 초기 OPEN header rejection의 원인. 실패한 collector에 diagnostic byte가
  없다는 사실만으로 device가 보내지 않았다고 판정하지 않습니다.

## 현재 프론티어

2026-09-05 확인 기준으로 P3.35가 인정된 세 세션 reference이며, 이후 candidate의
성공을 보장하지는 않습니다. P3.39는 candidate·rollback 각 1회, healthy rooted
FYG8 복귀와 `NO_PROOF`로 닫혔습니다. Native banner와 header-validation 실패는
수집했지만, 원인을 설명하는 데 필요한 추가 word는 얻지 못했습니다.

P3.40은 그 초기 수집 경로를 다루는 host 작업입니다. 직접 목표는 확립된 ACM
채널에서 유용한 실패 증거와 반복 가능한 세션을 확보하는 것입니다. 정확한 현재
준비·검토 상태는 [GOAL.md](../../GOAL.md)와 target contract를 따릅니다.
이 페이지는 실행 권한이나 replay를 만들지 않습니다.

## 주요 milestone

1. Exact FYG8 source와 Full-LTO build closure가 Android를 boot하는 rebuilt
   kernel을 만들었습니다.
2. Retained-witness 작업이 reliable acquisition과 strict absence classification
   boundary를 확립했습니다.
3. R4W1-D가 PID 1에서 direct native `/init` exec acceptance를 증명했습니다.
4. 이후 USB run은 명시적 refutation과 no-proof terminal을 포함해 functional
   restart witness를 connector/transport claim과 분리했습니다.
5. P3.19는 static module/order/ABI 문제를 닫았지만 live 결과에서는 observer
   실패가 드러났으며 USB 성공은 얻지 못했습니다.
6. P3.25가 native-PID1 ACM 도달을 증명했고, P3.26/P3.27이 양방향 BusyBox 실행과
   framed 고정 명령을 추가했습니다.
7. P3.30이 인증을, P3.34/P3.35가 bounded 다중 세션과 healthy rollback을
   확립했습니다. 이후 idle/reopen 실패는 별도로 남아 있습니다.

## Architecture 요약

```text
bootloader
  -> source-matched Samsung 5.10.226 kernel
    -> custom static /init running as PID 1
      -> vendor USB bring-up and CDC ACM
      -> authenticated bounded session
        -> fixed BusyBox commands and framed results
      -> exact boot rollback and rooted Android health
```

이 bounded 흐름은 링크한 성공 run들이 뒷받침합니다. 범용 shell이나 계속 운영되는
서비스는 아니며 모든 내부 USB 원인 문제를 해결한 것도 아닙니다.

## 정본 증거 링크

- Native ACM 도달: [Native ACM 도달](../reports/S22PLUS_FYG8_P325_F1_ACM_PRIMARY_PASS_2026-09-02.md)
- 양방향 BusyBox 증명: [양방향 BusyBox 증명](../reports/S22PLUS_FYG8_P326_F1_BIDIRECTIONAL_USB_BUSYBOX_PASS_2026-09-02.md)
- Framed 고정 명령: [Framed 고정 명령](../reports/S22PLUS_FYG8_P327_F1_FRAMED_EXEC_FIXED_COMMANDS_PASS_2026-09-02.md)
- 인증된 명령: [인증된 명령](../reports/S22PLUS_FYG8_P330_F1_AUTHENTICATED_COMMAND_PASS_2026-09-03.md)
- 세 세션 증명: [세 세션 증명](../reports/S22PLUS_FYG8_P335_F1_ATTENDED_RESIDENT_PASS_2026-09-04.md)
- 초기 수집 실패: [초기 수집 실패](../reports/S22PLUS_FYG8_P339_INITIAL_CAPTURE_INCIDENT_2026-09-05.md)
- 현재 프론티어: [GOAL.md](../../GOAL.md)
- Binding target contract: [S22+ FYG8 target contract](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
- Historical run ledger: [S22+ campaign ledger](../operations/CAMPAIGN_LEDGER_S22PLUS.md)
- Epistemic experiment index: [native PID1/userspace evidence ledger](../reports/S22PLUS_FYG8_NATIVE_PID1_USERSPACE_EXPERIMENT_EVIDENCE_LEDGER_2026-07-22.md)
- Rebuilt-kernel Android proof: [R3C1 live result](../reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md)
- Direct PID1 boundary: [R4W1-D live pass](../reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md)
- Stock ACM positive control: [O0 stock USB control](../reports/NATIVE_INIT_V3403_S22PLUS_O0_STOCK_USB_CONTROL_LIVE_2026-07-10.md)
- 역사적 static USB closure: [P3.19 SSUSB/UDC plan closure](../reports/S22PLUS_FYG8_P319_SSUSB_UDC_PLAN_CLOSURE_H0_2026-08-24.md)
- 역사적 USB audit와 live interpretation: [P3.19 comprehensive USB audit](../reports/S22PLUS_FYG8_USB_COMPREHENSIVE_INVESTIGATION_AUDIT_H0_2026-08-30.md)
- Additive post-live decoder: [`s22plus_fyg8_p319_postlive_decoder.py`](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_postlive_decoder.py)
- 역사적 H0 kmsg prototype: [`s22plus_fyg8_p319_kmsg_record_envelope.py`](../../workspace/public/src/scripts/analysis/s22plus_fyg8_p319_kmsg_record_envelope.py)
