# S22+ FYG8 과거 실패 기반 체크리스트

용도: 변경한 경로에서 이미 겪었던 실패가 반복되는지 확인한다.
대상은 S22+ FYG8의 네이티브 런타임과 호스트 관찰·저장 경로다.
[현재 목표](../../GOAL.md)와
[과거 실패 적용성 감사](../reports/S22PLUS_FYG8_P364_HISTORICAL_FAILURE_APPLICABILITY_AUDIT_2026-09-08.md)를
함께 본다. 상세 사고 이력은 각 항목의 보고서에 남긴다.

2026-09-10 갱신: P365~P381의 사고와 H0 발견 사항에 더해 P383의 USB
관측 중단, 화면의 인증 의존성, 복구 뒤 ADB 일시 불통을 기존 항목에 반영했다. 추가 근거의 `실행`은 준비·실행·복구에서 실제 발생한 문제이며,
기기 효과가 있었다는 뜻은 아니다. `H0`는 실기 투입 전에 발견한 결함,
`사후 분석`은 기록 해석의 정정을 뜻한다. 의도한 실패 조건 시험이나 단순한
미검증 범위를 사고로 추가하지 않는다.

후속 [host arrival H0 수정](../reports/S22PLUS_FYG8_RESTORATION_ARRIVAL_H0_2026-09-10.md)은
빈 child 이력에서 전송한 정확한 endpoint가 첫 inventory 도중 사라지는 경로와
남은 다른 node의 동일성 교체를 실제 measured observer로 검증했다. 고정 건강과
선택 HUD를 분리한 [1C 관찰기](../reports/S22PLUS_FYG8_LOCAL_DISPLAY_OBSERVER_1C_H0_2026-09-10.md)는
조기 실패의 raw 보존, 복귀 시간 확보, 실패 진단의 frame 오인을 검증했다.
둘 다 H0 PASS_GO이며 소비된 실행의 결과나 실기 권한을 바꾸지 않는다.

P384 후속 준비에서는 실제 prepared JSON의 들여쓰기를 포함한 크기 검증이
빠져 D0 뒤 64 KiB 초과를 발견했다. [수정과 실제 재개 검증](../reports/S22PLUS_FYG8_NATIVE_ROUNDTRIP_FOLLOWUP_V2_H0_2026-09-10.md#second-d0-and-preparation-publication-repair)은
기존 한도를 유지한 compact 저장으로 완료했다. [11개 ID 대조](../reports/S22PLUS_FYG8_NATIVE_ROUNDTRIP_FOLLOWUP_V2_H0_2026-09-10.md#past-failure-checklist-reconciliation)는
이 사전 누락과 아직 실행하지 않은 guard·네이티브 왕복·물리 화면 확인을 구분한다.

이 문서는 기존 계약·검증을 돕는 참고표다. 새 승인 단계나 독립적인 실행
게이트를 만들지 않으며, D0/D1/F1 권한을 부여하지 않는다. 실제 권한과
중단·복구 조건은 [AGENTS.md](../../AGENTS.md)와
[S22+ 계약](targets/S22PLUS_FYG8_TARGET_CONTRACT.md)을 따른다.

## 사용 방법

1. 이번 변경과 실제로 도달하는 코드에 해당하는 항목을 고른다.
2. 선택한 항목을 기존 H0 검증·리뷰에 포함한다. 관련 입력이 같은 검증은
   재사용하고, 해당하지 않는 오래된 사고를 새 작업의 일괄 차단 조건으로 삼지 않는다.
3. 결과는 기존 보고서나 변경 설명에 `ID — 확인 / 미확인 / 해당 없음 — 근거`
   형식으로 짧게 남긴다. 체크 표시만으로 확인을 대신하지 않는다.
4. 새 실패가 나오면 같은 원인의 항목과 근거를 갱신한다. 다른 원인일 때만
   항목을 추가하고, 수정 뒤에는 작은 회귀 검증으로 재발을 잡는다.

## 변경 범위별 확인표

| ID | 해당하는 변경 | 확인할 내용 | 과거 사고 / 근거 |
| --- | --- | --- | --- |
| ABI | syscall, 숫자 플래그, 구조체, ioctl, 대상 커널 API | 정확한 대상 UAPI와 값·레이아웃·필드 의미를 대조한다. 필요한 호출을 실제 대상 아키텍처에서 재현한다. 교차 컴파일과 x86 모의 테스트가 무엇을 확인하지 못하는지 구분한다. OF 노드 필드가 이름인지 전체 경로인지도 실제 커널 구현과 맞춘다. | [P364 ARM64 플래그](../reports/S22PLUS_FYG8_P364_PREPARATION_DIAGNOSTICS_2026-09-08.md#post-run-h0-diagnosis-arm64-open-flag-abi-mismatch), [H0 — P378 OF 노드 필드 오해](../reports/S22PLUS_FYG8_GAUGE_HUD_V012_RC1_H0_2026-09-09.md#evidence-and-correction) |
| IO | pipe, 자식 출력, 시간 제한, syscall 필터 | 자식 출력의 backpressure, 부분 입출력·EAGAIN, 출력 한도 안의 정확한 수신 바이트 수, 실제 대기 시간과 정리를 확인한다. 총량이 한도 이내여도 순간적인 큐 포화로 유실될 수 있다. 읽기 전 수용 공간과 stdout/stderr 동시 burst·느린 소비자를 시험한다. | [P346 출력 유실·sleep](../reports/S22PLUS_FYG8_P346_ADJACENT_FAILURE_AUDIT_2026-09-06.md), [P347 수정](../reports/S22PLUS_FYG8_P347_OUTPUT_TIMING_PREPARED_2026-09-06.md), [실행 — P380 출력 유실](../reports/S22PLUS_FYG8_GAUGE_MODEL_MEMORY_RC3_H0_2026-09-10.md#p380-live-close-and-output-loss-incident), [P381 수정·검증](../reports/S22PLUS_FYG8_OUTPUT_MEMORY_RC4_H0_2026-09-10.md) |
| SEMANTIC | 명령 결과·신원·성공 판정·측정값의 나이 | 숫자 UID/GID와 필요한 생산자의 상태·출력을 검증한다. exit 0, 마지막 shell 명령 성공, ioctl 반환, CONTROL ACK의 증명 범위를 명시한다. 모듈 삽입·probe·binding·실제 읽기를 구분하고 대상 신원 조건을 실제 관측값과 맞춘다. N/A가 원인을 지우지 않도록 기존 증거에 실패 단계·오류를 남긴다. 비동기 측정값의 시각은 각각 검증하며 정상적인 늦은 읽기와 오래된 캐시를 구분한다. | [P345 신원·투영](../reports/S22PLUS_FYG8_P345_SHELL_QUALIFICATION_NO_PROOF_2026-09-06.md), [P346 false success](../reports/S22PLUS_FYG8_P346_ADJACENT_FAILURE_AUDIT_2026-09-06.md), [실행 — P378 원인 미상 N/A / H0 — 시각 관계 오류](../reports/S22PLUS_FYG8_GAUGE_HUD_V012_RC1_H0_2026-09-09.md), [실행 — P379 모델 검사 거부](../reports/S22PLUS_FYG8_GAUGE_DIAGNOSTICS_RC2_H0_2026-09-10.md) |
| WIRE | 프로토콜, 관찰기, 진단 프레임 | 실제 C 생산자부터 실시간 수집기·원시 저장·재파싱까지 잇는다. 조기 거부 때문에 필요한 실패 증거가 사라지지 않는지, OPEN/raw 설정 순서와 부분 프레임 처리가 맞는지 확인한다. | [P339 수집 중단](../reports/S22PLUS_FYG8_P339_INITIAL_CAPTURE_INCIDENT_2026-09-05.md), [P341 OPEN 순서](../reports/S22PLUS_FYG8_P341_HOST_FIRST_OPEN_PREPARATION_2026-09-05.md) |
| PERSIST | 증거 필드, 세션 수, 준비·journal·상태·결과 JSON, 복구 시 저장 | 성공과 후반 실패의 실제 생산자 출력을 실제 writer로 저장하고 reader로 다시 연다. 중간 journal을 포함해 중첩 bytes·자료형·들여쓰기·envelope와 단계별 한도를 확인한다. 원본 증거와 해시 참조를 보존하면서 불필요한 본문 중복을 피한다. 정상 close→rollback→결과와 기록 전후 중단·복구를 시험하고 대표 크기 시험과 구분한다. 새 프로세스의 번호 할당은 기존·부분 기록을 포함해 이어가며 덮어쓰지 않는다. | [P310 JSON](../reports/S22PLUS_FYG8_P310_CARRIER_V2_JSON_SERIALIZATION_INCIDENT_2026-08-09.md), [P364 상태 용량](../reports/S22PLUS_FYG8_P364_HISTORICAL_FAILURE_APPLICABILITY_AUDIT_2026-09-08.md#1-success-evidence-can-exceed-the-current-state-writers-bound), [실행 — P366 복구 시 번호 충돌](../reports/S22PLUS_FYG8_POST_P366_HOST_REPAIR_2026-09-08.md#changes), [실행 — P381 journal 초과·H0 수정 검증](../reports/S22PLUS_FYG8_OBSERVED_JOURNAL_H0_2026-09-10.md), [실행 — P384 준비 JSON 서식 초과·수정 후 실제 reopen](../reports/S22PLUS_FYG8_NATIVE_ROUNDTRIP_FOLLOWUP_V2_H0_2026-09-10.md#second-d0-and-preparation-publication-repair) |
| ROUTE | 새 후보·스키마 등록, 공통 실행기, backend 증거 연결 | 실제 prepare/reopen, 성공·NO_PROOF·CLOSED 결과 경로가 올바른 namespace와 reader를 선택하는지 확인한다. 소비자가 요구하는 phase·파일·중첩 경로를 실제 backend가 생성하는지 잇는다. 테스트가 누락된 생산자 기록을 대신 만들어 연결 결함을 가리지 않게 한다. 공유 필드 예외는 정확한 이름과 소유자에 묶고 다른 후보 입력은 거부한다. | [P339 잘못된 분기](../reports/S22PLUS_FYG8_P339_INITIAL_CAPTURE_INCIDENT_2026-09-05.md), [P364 결과 저장 오류](../reports/S22PLUS_FYG8_P364_PREPARATION_DIAGNOSTICS_2026-09-08.md#host-terminal-publication-incident-and-repair), [실행 — P366 미생성 phase 요구 / H0 — 실제 receipt 경로 검증](../reports/S22PLUS_FYG8_POST_P366_HOST_REPAIR_2026-09-08.md) |
| ARTIFACT | 빌드 변환·패키징·승계 | 실제 AP를 풀어 Image의 raw/embedded-config 식별자, init, 모듈, 관찰 계약을 맞춘다. AP 추가 모듈 목록과 vendor_boot에서 승계한 전체 런타임을 구분하고 실제 소비한 파일까지 연결한다. 소비된 입력과 승인 pin은 보존한다. | [P320→P321 혼합 식별자 수정](../reports/S22PLUS_FYG8_P321_IDENTITY_USB_RACE_H0_2026-08-31.md), [H0 — P378 승계 모듈 해석·패키징 목록 누락](../reports/S22PLUS_FYG8_GAUGE_HUD_V012_RC1_H0_2026-09-09.md#evidence-and-correction) |
| AUDIT | 읽기 전용 검사·결과 복구 도구·원인 분석 | 읽기와 인덱스 복구를 구분하고 helper의 쓰기 동작까지 확인한다. 무변경 범위가 내용인지 inode·시간·모드까지인지 명시하고 scratch에서 검증한다. 원인 분석은 실행 단계·시각·원본 출처를 맞춘다. 앞선 snapshot 오류나 파일 시각만으로 뒤의 내부 syscall 실패를 단정하지 않으며 기록되지 않은 원인은 미확인으로 남긴다. | [P325 Journal.reopen](../reports/S22PLUS_FYG8_P325_CLOSED_RESULT_FINALIZER_INDEPENDENT_REVIEW_2026-09-02.md), [P364 적용성 감사](../reports/S22PLUS_FYG8_P364_HISTORICAL_FAILURE_APPLICABILITY_AUDIT_2026-09-08.md#2-journal-reopen-is-a-repairing-operation-not-a-pure-read), [사후 분석 — P365 원인 귀속 정정](../reports/S22PLUS_FYG8_P365_ARM64_AND_PERSISTENCE_PREPARATION_2026-09-08.md#post-run-provenance-correction) |
| HOST | 관찰기 시작·권한 helper·호스트 서비스·실행 환경 | 소스·파일 모드와 실제 프로세스 권한을 구분한다. polkit 인증 대기와 guard 완료, NoNewPrivs, ADB 최초 기동의 stdout/stderr를 현재 실행 환경에서 확인한다. 준비 단계 실패와 candidate 효과 발생을 구분하고, 원본 출력을 보존한 채 기존 중단 규칙을 따른다. 통과시키기 위해 권한 경로나 parser를 우회하지 않는다. 재부팅 전후 USB 목록이 바뀌는 실제 경로를 포함해 관측 시작을 검증하고, snapshot 수집 중단과 기기 부팅 실패를 구분한다. | [실행 — P367 인증 대기 중 guard 시작 실패](../reports/S22PLUS_FYG8_P367_HOST_PATH_PREPARATION_2026-09-08.md#approved-invocation-pre-candidate-observer-arm-abort), [실행 — P371 권한 환경·cold ADB 준비 실패](../reports/S22PLUS_FYG8_P371_FIXED_STATUS_PREPARATION_2026-09-09.md), [실행 — P383 재부팅 전후 USB 목록 변경·관측 중단](../reports/S22PLUS_FYG8_NATIVE_BASELINE_ROUNDTRIP_H0_2026-09-10.md#attended-attempt-and-final-android-health) |
| DISPLAY | DRM 초기 상태·버퍼·표시 경로·화면 수명 | 실제 vendor 드라이버 이름·초기 plane 상태·포맷·메모리 경로와 맞춘다. 기존 성공 렌더러를 유지할 수 있으면 재사용한다. 호스트 픽셀, ioctl 수락, 실제 표시 증거를 구분한다. 기능의 목적이 확장되면 시작·갱신·종료가 기존 호스트 연결·인증·콘솔에 종속되는지 확인한다. 부팅 상태 표시 목적이라면 호스트 부재·인증 실패 때 무엇을 표시할지 검증한다. 화면 부재만으로 커널/PID1 미도달을 단정하지 않는다. | [P352 초기 상태](../reports/S22PLUS_FYG8_P352_SOURCE_BOUND_DISPLAY_H0_2026-09-07.md), [P358 캐시 경로](../reports/S22PLUS_FYG8_P358_CACHED_FRAMEBUFFER_PREPARATION_2026-09-07.md), [사후 분석 — P383 인증 뒤 HUD 시작과 부팅 상태 표시의 한계](../reports/S22PLUS_FYG8_NATIVE_BASELINE_ROUNDTRIP_H0_2026-09-10.md#structural-coupling-and-follow-up-scope) |
| RETURN | 종료·재부팅·복구·보고 순서 | 실제로 증명한 복구 범위와 물리적 복구 필요성을 유지한다. 종료 직전 호스트 저장 실패도 Download 관측 시간창을 놓치게 할 수 있다. 효과 뒤 보고 오류는 보존된 저널에서 복구하며 candidate·CONTROL·rollback을 재전송하지 않는다. 나중의 복구 성공이나 복구 기록 게시 시각이 당시의 적시 복귀·기능 성공 증거를 대신하지 않게 한다. Android 화면 복귀, ADB online, 정확한 기기의 최종 건강을 별도로 확인한다. offline 뒤 연결이 회복되면 기존 저널에서 허용된 건강 검증만 이어가고 복구 전송을 반복하지 않는다. | [P318 후반 보고 오류](../reports/S22PLUS_FYG8_P318_POSTROLLBACK_FINALIZATION_INCIDENT_H0_2026-08-17.md), [P362 native 복귀 범위](../reports/S22PLUS_FYG8_P362_REBOOT_DOWNLOAD_PATH_ANALYSIS_2026-09-07.md), [실행 — P381 journal 오류 후 복구·놓친 관측 시간창](../reports/S22PLUS_FYG8_OUTPUT_MEMORY_RC4_H0_2026-09-10.md), [실행 — P383 ADB offline 시간 초과·추가 전송 없는 최종화](../reports/S22PLUS_FYG8_NATIVE_BASELINE_ROUNDTRIP_H0_2026-09-10.md#attended-attempt-and-final-android-health), [실행 — P384 일반 재부팅 조기 속성값 거부·후속 정상성 확인](../reports/S22PLUS_FYG8_NATIVE_ROUNDTRIP_FOLLOWUP_V2_H0_2026-09-10.md#one-attended-ordinary-reboot-and-later-health) |

## 짧은 기록 예시

아래는 기록 형식의 예시이며 실제 검증 결과가 아니다.

```text
이번 변경: 새 네이티브 준비 함수와 진단 결과 저장
선택 항목: ABI, WIRE, PERSIST, ROUTE, ARTIFACT
ABI — 확인 — 대상 헤더 및 ARM64 실제 호출 시험 <근거>
PERSIST — 미확인 — 성공 경로의 전체 상태/결과 roundtrip 필요
DISPLAY — 해당 없음 — 기존 렌더러 바이트 유지, 기존 검증 참조 <근거>
```

현재 미해결 문제와 다음 수정 범위는 GOAL과 최신 감사 보고서에서 관리한다.
이 참고표에 과거 PASS 상태를 복사해 새 후보의 PASS로 사용하지 않는다.
