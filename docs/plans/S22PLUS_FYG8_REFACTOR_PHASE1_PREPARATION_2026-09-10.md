# S22+ FYG8 구조 점검과 1차 리팩토링 준비

상태: **H0 구조 점검·범위 제안 완료. 리팩토링 구현·독립 리뷰·실기 검증 전.**
대상: SM-S906N / g0q / S906NKSS7FYG8.
점검 기준: 문서 커밋 `7dfe735cfe` 시점의 현재 소스와 소비된 P383 실행 증거.

## 판단과 범위

**1차 리팩토링 준비가 필요하다.** 현재 기능을 생성하는 코드의 진입점과
화면·콘솔의 실행 책임을 명확히 하는 것이 우선이다. 기존 코드에 기능을
추가했다는 사실이나 파일 크기만으로 결함을 판단하지 않는다. 이번에는
호스트 인증 실패가 기기 화면 시작까지 막는 실제 의존성이 확인됐고,
최신 생성 코드에 여러 세대의 변환이 겹쳐 그 관계를 파악하기 어려워졌다.

이 점검은 최신 S22+ native 생성·실행·관측·증거·복구 경로를 대상으로 한다.
전체 저장소나 모든 과거 후보를 전수 감사한 결과는 아니다. A90/S20+,
커널 메모리 변경, 새로운 장치 기능, 펌웨어·파티션 변경은 범위 밖이다.
P382/v0.1.2 성공과 P383 NO_PROOF/CLOSED/19 및 최종 Android 건강은 유지한다.
두 번째 커널/PID1 실행 단계와 일시적 ADB offline 원인은 계속 미확정이다.

## 현재 구조와 확인 근거

| 층 | 현재 책임과 진입점 | 구조적 판단 |
| --- | --- | --- |
| 후보 생성 | `s22plus_fyg8_p383_stock_candidate_build.py`, `s22plus_fyg8_p383_namespace.py`가 이전 소스를 해시 검증하고 변환·실행한다. | 과거 입력 보존에는 유용하지만 현재 동작을 읽기 위해 이전 세대의 변환과 전역 바인딩을 따라가야 한다. |
| native 초기화·인증 | 생성된 `p345_framed_console`이 OPEN/AUTH, BOOT_ID, return 준비, RAM 작업 영역을 거쳐 `rc1_console`에 들어간다. | 인증된 명령 경로와 로컬 표시 준비의 경계를 다시 나눌 필요가 있다. |
| 콘솔·출력 | `s22plus_root_console_v1.inc.c`에 P381의 `s22plus_root_console_output_v2.inc.c` 적용을 더한다. | 명령·취소·출력 한도·CONTROL 및 backpressure 수정은 유지할 기능이다. 최종 소스가 원본 파일 하나와 같지는 않다. |
| HUD·측정 | 콘솔 안에서 `hud1_start/tick/stop`을 호출한다. 현재 HUD는 별도 renderer·collector 자식과 bounded IPC를 사용한다. | 자식 격리는 이미 있다. 부족한 것은 프로세스 수가 아니라 시작·갱신·종료의 독립성이다. |
| 호스트 트랜잭션 | `device_action_f1_live_v2.py`가 준비·실행·후보 관측·복구·최종 결과를 조정하고 P383 복원은 `s22plus_native_roundtrip_owner_v1.py`에 위임한다. | 책임별 모듈은 일부 있지만 공통 조정기 안에 후보별 선택·상태 투영·검증이 함께 누적돼 있다. |
| 증거·분기 | `device_action_f1_evidence_v2.py`의 `SHELL_VARIANTS`와 관측 schema/reader, live의 return/console owner 표가 연결된다. | 기존 선언을 활용할 수 있다. 별도 플러그인 등록 체계보다 현재 중복 선언과 소비자의 관계를 명확히 하는 편이 작다. |
| 전송·저장·복구 | boot-only AP reader, Odin/usbfs 관측, raw capture, Journal, consumed registry, 최종 건강 모듈이 별도로 존재한다. | 1차 전면 재작성 대상이 아니다. 정확한 바인딩·효과 1회·증거 보존·복구 경계를 유지할 기반이다. |

현재 측정값은 문제 범위를 설명하는 시점별 관측이며 테스트의 고정 정답이 아니다.

- live 조정기: 19,902행, 최상위 함수 356개·클래스 37개.
- typed evidence: 23,042행. core F1: 4,087행. P383 roundtrip owner: 358행.
- P383 runtime import의 동적 실행을 추적하면 P382→P375의 8개 투영 층을
  지나간다. 하위 기반 코드까지 포함한 전체 의존성 깊이라는 뜻은 아니다.
- 생성된 helper **템플릿**은 68,846바이트·1,723행,
  SHA256 `2480436b9013fb4c2f59edc396f6a2f4788d7a04448eac2a1323473146b13920`.
  이는 실기 `/init` 바이너리나 최종 materialized helper의 동일성 증거가 아니다.
- 소비된 P383 준비에 묶인 실행 소스 86개는 현재도 크기·해시가 모두 같다.

직접 확인한 주요 소비자·검증 경로:
[namespace 실행](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_p383_namespace.py),
[HUD 삽입](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_p376_research_shell_runtime.py),
[HUD/collector 수명](../../workspace/public/src/native-init/s22plus_boot_hud_v2.inc.c),
[roundtrip owner](../../workspace/public/src/scripts/revalidation/s22plus_native_roundtrip_owner_v1.py),
[Download 관측](../../workspace/public/src/scripts/revalidation/s22plus_odin_transition_core.py),
[현재 lifecycle fixture](../../tests/test_s22plus_fyg8_p383_lifecycle.py).

## 이번 실패가 드러낸 경계

### 화면은 콘솔의 자식 기능에서 부팅 상태 표시로 역할이 넓어졌다

[P376 원래 범위](../operations/S22PLUS_FYG8_BOOT_HUD_V1.md#scope-and-ownership)는
인증된 콘솔의 상태 화면이다. 현재 화면은 시스템·게이지 상태까지 표시하지만
수명은 계속 콘솔 안에 있다. 따라서 호스트가 인증 전에 멈추면 화면도
시작하지 않는다. 화면 자식은 인증 키나 USB 콘솔 FD를 받지 않으므로,
인증은 렌더링 자체의 필수 조건이 아니다.

`hud1_start` 호출만 앞으로 옮기는 변경으로는 충분하지 않다.
`/s22-root-work/hud.log`가 사용하는 RAM 작업 영역도 인증 후 생성되고,
HUD 갱신·수거·정리와 시간 제한은 콘솔의 실행 흐름에 연결돼 있다.
초기화 순서, 필요한 장치/모듈, 진단 저장, 시각 원점, 자식 수명까지
확인해야 한다. 원래 return 준비 전체를 무조건 인증 앞으로 옮기지 않는다.

### 두 번째 관측은 새 디렉터리에서 시작한다

P383 owner의 `finish`는 N 복원 전송 후 새 child `odin-endpoints`를 만들고
`observe_candidate`를 호출한다. 그 함수는 인증 관찰기보다 먼저 Download
부재 관측을 수행한다. `wait_for_no_live_endpoint`는 해당 디렉터리의 마지막
live snapshot 또는 새로 얻은 live snapshot에서 expected departure를 정한다.

실패한 child에는 snapshot receipt가 0개이고, 첫 USB evidence 수집에서
membership 변경 진단이 남았다. 따라서 **부모 전송 endpoint와 새 관측 세션의
출발점 연결**은 구체적인 조사 대상이다. 아직 이 상태를 재현해 원인을 확정한
것은 아니며, 단순 재시도 추가나 부모 receipt 복사로 고칠 수 있다고 결론내리지
않는다. 동일 대상·부팅·lease·시각·전송 역할을 검증하는 연결이어야 한다.

### 기존 통합 검증의 유효 범위

P383 lifecycle 검증은 실제 owner·writer·USB/Download 소비 경로와 native
생산자를 연결한다. 다만 복원 fixture는 `source_mode('absent')`로 전환한 뒤
관측하므로 첫 snapshot 수집 중 목록이 바뀌는 이번 타이밍을 그 성공 사례가
대표하지 않는다. 기존 HUD 통합 검증도 인증 후 콘솔/HUD의 동작과 격리를
검증한다. 호스트가 없는 상태의 독립적인 화면을 검증한 것으로 읽으면 안 된다.
이는 기존 PASS 전체의 무효화가 아니라 추가할 정확한 회귀 사례의 범위다.

## 1차 구현을 위한 분할안

### 1A — 현재 native 구현을 직접 읽을 수 있는 기준 소스로 정리

최신 native 생성 경로에 한정해 기능 소스와 후보 식별자 주입을 분리한다.
공개 C 템플릿·현재 include 조합을 명시적인 공통 구현으로 옮기고, 새 후보는
그 구현과 명시적 식별자 설정을 선택하게 한다. 과거 wrapper·pin·artifact는
역사 재현을 위해 보존한다. 실기 `/init`이나 키가 들어간 private 생성물을
공개 기준 소스로 복사하지 않는다. 깊은 다른 공통 계층까지 동시에 옮기지 않는다.

이 단계에서는 **행동을 바꾸지 않는다**. 동일한 고정 H0 입력에서 기존 생성기와
새 생성기의 materialized C·renderer·모듈 계획·관측 스펙을 비교하고, 패키지와
최종 ELF의 동일성 또는 차이의 정확한 원인을 확인한다. 템플릿 해시 하나만으로
최종 동등성을 주장하지 않는다. 후보 ID 주입은 선언된 필드에만 허용한다.
새 경로가 정리되기 전에 또 다른 후보별 문자열 치환 층을 추가하지 않는다.

### 1B — native 생명주기와 인증 콘솔의 책임 분리

1A의 읽을 수 있는 기준 위에서 별도의 **행동 변경**으로 설계·검증한다.
PID1이 local display와 authenticated console을 각각 관리한다. 로컬 화면은
필요한 초기화 뒤 시작하며 인증 대기·활성·실패를 구분해 표시한다. EXEC와
CONTROL의 인증, 한 번의 Download 요청, 출력·취소·시간 제한은 그대로 유지한다.

화면 프로세스 격리와 기존 nonblocking IPC·DRM 버퍼 수명 규칙은 재사용한다.
새 daemon/proxy, 화면으로 명령 권한을 부여하는 경로, 무제한 listener/재연결은
추가하지 않는다. 로컬 표시 시간과 콘솔 시간은 명시적으로 정의하며, 인증을
기다리다 멈춰도 유한한 정리 정책이 있어야 한다. 화면의 성공은 인증된 PID1
증명이나 자동 복구 증명이 아니다. stale 화면을 현재 건강으로 표시하지 않는다.

완료 기준은 호스트 없음·지연·잘못된 인증에서 로컬 상태 표시가 동작하고,
정상 인증에서는 기존 명령/출력/CONTROL이 유지되며, HUD·collector 고장이나
느린 DRM이 콘솔 제어를 막지 않는 것이다. 전후 각 상태의 종료·정리도 포함한다.

### 별도 소규모 수정 — 호스트 arrival 경계

화면 분리와 USB 타이밍 수정을 한 diff에 섞지 않는다. 먼저 빈 child 관측 이력과
snapshot 수집 중 정확한 Download 이탈을 기존 실제 관측기 경로로 재현한다.
이후 필요한 경우 전송 결과와 관측 시작을 연결하는 작은 명시적 context를
기존 owner/backend 경계에서 정의한다. 실제 동일성·증거 바인딩 없이 전역
inventory 오류를 무시하거나 효과를 재실행하는 해결책은 배제한다.

잘못된/추가된 endpoint, 오래된 receipt, 불일치한 lease/역할, 불완전한 raw
증거는 계속 거부해야 한다. 검증 가능한 정상 이탈과 중단해야 할 모호함을
구분하는 수정이어야 한다. ADB offline 원인 분석은 별도이며 이 수정의 원인으로
합치지 않는다.

## 1차에서 유지하고 뒤로 미룰 것

- F1 상태 머신·저널·consumed registry·AP reader·기존 A 복구 경로를 전면
  분할하거나 재설계하지 않는다. 필요한 작은 호출 경계만 별도 검토한다.
- 모든 과거 후보의 namespace나 공통 live/evidence 파일을 일괄 변환하지 않는다.
  최신 경로의 책임 정리 후 실제 변경 비용을 보고 다음 분할 범위를 고른다.
- 커널·DRM 알고리즘·게이지·메모리 절감과 새 native baseline 채택을 섞지 않는다.
- 소비된 P383 실행·승인·예외 예산을 재사용하거나 과거 증거를 새 구조에 맞게
  수정하지 않는다. 이 준비 단계에서는 새 후보/버전/실기 실행을 할당하지 않는다.

## 검증·리뷰·완료 조건

| 변경 | 재사용할 검증과 추가할 행동 사례 |
| --- | --- |
| 1A 생성 경로 정리 | 현재 P383 native health, P381 출력/HUD 통합, 기존 A/B·정적 source closure 검증을 활용한다. 실제 생성물 동등성과 선언 외 치환 부재를 추가 확인한다. |
| 1B 수명 분리 | 실제 생성된 C의 PID1/콘솔/renderer join으로 호스트 없음·지연·인증 거부, HUD/collector stall, CONTROL과 종료, stdout/stderr backpressure를 확인한다. 로컬 테스트와 실제 ARM64 ABI/DRM 증거의 범위를 구분한다. |
| arrival 수정 | `test_s22plus_odin_transition_core.py`, `test_s22plus_odin_usbfs_identity.py`, P383 lifecycle의 실제 관측 경로에 empty-child/도중 이탈/외부 endpoint/불완전 증거 사례를 연결한다. 기존 publication cut·역할별 1회·복구 최종화를 유지한다. |

이 표는 필요한 변경에 대한 검증 계획이며 이번 준비에서 테스트를 새로 수행한
결과가 아니다. Python/C 실행 코드를 바꿀 때 기존 계약의 py_compile·실제
repository toolchain 교차 컴파일·대표 생산자/소비자 검증을 적용한다. 의미 없는
과거 수치 고정이나 mock이 생성해 준 receipt를 실제 경계 검증으로 대체하지 않는다.

구현 후에는 변경된 실행-critical closure와 상위 계약의 상호작용에 대한 기존
독립 리뷰가 필요하다. 1B는 기존 인증 후 HUD 범위의 행동 변경이므로 해당 계약
변경도 함께 검토한다. 새 코드에 과거 PASS_GO를 그대로 적용하지 않는다.
새로운 승인 의식이나 별도 영구 게이트를 만드는 제안은 아니다.

이번 준비의 완료 기준은 구조·의존성·증거 한계·1차 경계·검증 방법을 현재 소스로
확인해 기록하는 것이다. 이 기준은 충족했다. 구현·qualification·실기 검증은
완료되지 않았으며, P383의 두 번째 부팅을 성공으로 승격하지 않는다.
