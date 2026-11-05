# S22+ 메인라인 반복 속도 개정안 (초안)

Status: **DRAFT PROPOSAL — 규범 아님, 권한 없음.**
AGENTS.md에 따라 초안은 어떤 lane도 활성화하지 않는다. 채택하려면 운영자 결정,
해당 contract 문서 개정, 독립 리뷰, 기계적 활성화가 모두 필요하다.
작성: Claude Opus 5.5, 2026-11-05. 대상: SM-S906N / g0q / S906NKSS7FYG8.

## 배경

메인라인 lane([S22PLUS_MAINLINE_RAM_V1](../operations/S22PLUS_MAINLINE_RAM_V1.md))은
후보마다 **승인 1회 = 작업 1회 / 1800초**이고, 사람이 지켜보는 Download 복구가
필요하다. ML021~ML028 동안 기준선은 안정됐다. 남은 일은 이미 r0q 포트에서 동작이
확인된 하드웨어를 하나씩 켜는 기능 작업이다. 그런데 기능 하나마다 준비 → 승인 →
참석 → 전송 2회가 반복된다.

비교 대상인 r0q 포트는 TWRP를 recovery에 상주시키고 `dd`로 boot를 직접 써서
나흘에 40회 이상 반복했다. 그 속도를 이 저장소의 안전 원칙 안에서 얼마나
가져올 수 있는지 검토한 결과, **속도를 정하는 것은 전송 방식보다 승인 단위**였다.

## 현재 규칙과 각 변경안의 위치

| 변경 | 건드리는 규칙 | 등급 |
| --- | --- | --- |
| A. 메인라인 범위 승인 모드 | 메인라인 lane의 승인 단위(target/lane 규칙) | **영구 경계 변경 없음.** 독립 리뷰 1회 |
| B. TWRP recovery 상주 | 영구 경계 2(boot 외 파티션 금지) | 영구 경계 예외. 독립 안전 리뷰 + 기계적 활성화 |
| C. TWRP 안의 고정 boot 기록기 | 영구 경계 3(`dd`·블록 직접 쓰기 금지) | 영구 경계 예외. 독립 안전 리뷰 + 기계적 활성화 |

선례:
- A: 같은 기기의 [proportional research V1](../operations/S22PLUS_PROPORTIONAL_RESEARCH_V1.md)
  (vendor 커널 native baseline용 범위 승인)과
  [deferred physical recovery V1](../operations/S22PLUS_NATIVE_BASELINE_DEFERRED_RECOVERY_V1.md)
- B: S20+ F2-T0/T1/T2(Odin recovery 전용 전송, 정품 rollback, TWRP 상주)와
  [S20+ TWRP baseline](../operations/S20PLUS_TWRP_BASELINE_V1.md)
- C: A90의 고정 TWRP misc-BCB hook(검토된 코드, 고정 경로·크기·SHA, 호출자 인자 없음)

## 권장 순서

**A를 먼저 채택하고, B와 C는 보류한다.**

ML027과 ML028에서 메인라인 Debian이 명령으로 정상 Download에 진입하는 경로가
증명됐다. 따라서 `Android 확인 → Download → N → 시험 → (명령) Download → A →
Android 확인`의 정상 경로는 이미 기계가 처리할 수 있다. 사람이 필요한 것은
실패했을 때의 물리 복구와 현재의 USB 재연결뿐이다. A만으로도 반복 1회의 사람
비용 대부분이 사라진다. 반면 B와 C는 영구 경계 두 개를 바꾸면서도 추가로 줄이는
것은 Odin 전송 시간 정도다.

B는 마일스톤 5~6(Android를 대신할 독립 rescue 경로)이 실제 과제가 될 때 다시
평가한다. C는 B가 채택된 뒤에도 Odin 전송이 실제 병목으로 측정될 때만 평가한다.

## A. 메인라인 범위 승인 모드 (제안 내용)

proportional research V1의 구조를 메인라인 lane에 맞게 옮긴다. 부모(범위)가
정책과 예산을 고정하고, 자식(후보)은 각자 기계 검증을 받는다.

### 운영자가 한 번 반환하는 범위 승인에 들어갈 것

- 정확한 target, 원래 A(rollback)와 그 해시, 복구 방식(참석 또는 지연 물리 복구)
- **유한 예산:** 작업 횟수 상한(예: 8회), 전체 기한(예: 6시간, host suspend 포함,
  갱신 없음)
- **허용 기능 범위(선언형 목록):** 아래 "허용 후보 범위"에서 고른 항목
- **허용 runtime profile:** 기존 RAM PID1 / SSH / rc / Download 귀환 profile 중 선택

### 후보(자식)마다 기계가 확인하는 것

- 정확한 boot-only AP, uniLoader, 커널, DTB, initramfs의 해시와 출처
- 기존 메인라인 H0 검증 일체: loader 진입, VM, 예약 메모리 대조, USB 공급 결합
- **선언한 허용 범위를 벗어나지 않는다는 기계 검사**: 아래 "기계 검사 예시"
- 직전 작업의 닫힌 종료와 현재 Android 건강

### 허용 후보 범위 (운영자가 고르는 선언형 목록)

| 등급 | 예시 | 조건 |
| --- | --- | --- |
| R0 관측 | thermal 센서, cpufreq 읽기, SMP(`maxcpus` 제거), TLMM 활성화, watchdog **등록만**(W1) | 하드웨어 설정을 바꾸지 않거나, 정품 FYG8 live FDT 범위 안의 값만 사용 |
| R1 제어 가능 | watchdog 켜기·pet·끄기(W2), cpuidle 활성화, USB Type-C(MAX77705 CCIC) 역할 처리 | 정품 범위 안. 리셋이 일어나는 시험(W3)은 제외 |
| 별도 범위 | UFS(읽기 전용 → 쓰기), 충전기 설정, Wi‑Fi(PCIe/펌웨어), 레귤레이터 전압을 바꾸는 변경, 의도적 리셋(W3) | 이 모드의 범위로 묶지 않음. 각자의 정책과 승인 필요 |

### 기계 검사 예시

- DT의 모든 활성 레귤레이터의 min/max 전압이 정품 FYG8 live FDT의 같은 레일 범위
  안에 있다.
- 활성 노드 집합이 선언한 허용 범위의 합집합을 넘지 않는다. 예를 들어 범위에
  UFS가 없으면 `ufs_mem_hc`가 `disabled`여야 한다.
- `CONFIG_` 차이가 선언 목록 안에 있다.
- 커널 패치가 사전 검토된 패치 집합의 부분집합이다.

### 그대로 유지하는 것

- 후보 intent와 소비는 재실행하지 않는다. 불확실한 전송이나 제어는 replay하지 않는다.
- 실패한 작업의 F1 owner와 원래 A 복구는 그대로 남는다. 다음 후보는 닫힌 종료와
  건강이 확인돼야 시작한다.
- boot 외 파티션 금지, `dd` 금지 등 영구 경계는 변경 없음.
- 같은 능력의 독립 `PASS_GO`는 실행 핵심 해시가 같은 동안 재사용한다(AGENTS Review
  Rules).

### 남는 사람의 역할

1. 범위 승인 1회
2. 실패 시 물리 복구(지연 물리 복구 모드를 선택하면 운영자가 올 때까지 대기)
3. **USB 재연결**. ML021~ML028은 매번 폰 쪽 재연결이 필요했다. 범위 모드의 실익을
   최대로 하려면 R1의 MAX77705 Type-C 처리(r0q attempt 23)를 이 모드의 첫 후보로
   두는 것이 좋다.

## B. TWRP recovery 상주 (보류, 요점만)

- S20+ T0→T1→T2 순서를 따른다. 정확한 g0q TWRP AP 하나와 정품 recovery rollback
  AP 하나(각각 `recovery.img.lz4` 한 멤버)를 SHA로 고정하고, pinned `odin4`로
  recovery 전용 전송만 한다.
- 전송 전에 기기에서 정품 recovery digest를 새로 읽는다. 정품 rollback 경로를
  증명한다. KOR 펌웨어에서 키 조합 recovery 진입에는 USB 데이터 케이블이 필요하다
  (ABL 분석 `0x4b8d8`).
- TWRP 건강 판정은 S20+ baseline처럼 고정 identity 수집기로 한다. TWRP UI 설치,
  백업, 복원, mount, format, 임의 root 명령은 제외한다.
- 메인라인에서 recovery로 재부팅하는 경로(PON reboot-mode)는 별도로 증명한다.

## C. TWRP 안의 고정 boot 기록기 (보류, 요점만)

- 범용 `dd`가 아니라 검토된 고정 프로그램이다. 대상은 `by-name/boot` 하나로
  고정하고, 쓰기 전에 대상 경로와 크기를 확인한다. 정확한 이미지 SHA만 받고,
  쓴 뒤에 전체를 다시 읽어 대조한다. 호출자가 경로, 오프셋, 길이를 줄 수 없다.
- 원래 A 복구는 지금처럼 Download로 유지한다. C는 개발용 빠른 경로일 뿐이고
  최후 복구 수단이 아니다.

## 결정이 필요한 것 (운영자)

1. A 채택 여부와 기본 예산(작업 횟수, 기한)
2. 기본 복구 방식: 참석 또는 지연 물리 복구
3. A의 첫 범위에 넣을 허용 항목. 제안: R0 전체 + R1의 Type-C·watchdog W2
4. B와 C를 지금 보류하는 것에 대한 동의

## 정정 기록

작성자는 이 초안 직전의 대화에서 "현재 contract는 standing approval을 명시적으로
배제한다"고 말했다. 정확하지 않았다. 같은 기기의 proportional research V1에는
유한한 범위 승인으로 여러 후보를 실행하는 제도가 이미 있다. 다만 메인라인 lane은
아직 그 제도를 쓰지 않고, 작업 1회 승인을 사용한다.
