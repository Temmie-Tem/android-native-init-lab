# S22+ FYG8 과거 실패 기반 체크리스트

용도: 변경한 경로에서 이미 겪었던 실패가 반복되는지 확인한다.
대상은 S22+ FYG8의 네이티브 런타임과 호스트 관찰·저장 경로다.
[현재 목표](../../GOAL.md)와
[과거 실패 적용성 감사](../reports/S22PLUS_FYG8_P364_HISTORICAL_FAILURE_APPLICABILITY_AUDIT_2026-09-08.md)를
함께 본다. 상세 사고 이력은 각 항목의 보고서에 남긴다.

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
| ABI | syscall, 숫자 플래그, 구조체, ioctl | 정확한 대상 UAPI와 값·레이아웃을 대조한다. 필요한 호출을 실제 대상 아키텍처에서 재현한다. 교차 컴파일과 x86 모의 테스트가 무엇을 확인하지 못하는지 구분한다. | [P364 ARM64 플래그](../reports/S22PLUS_FYG8_P364_PREPARATION_DIAGNOSTICS_2026-09-08.md#post-run-h0-diagnosis-arm64-open-flag-abi-mismatch) |
| IO | pipe, 자식 출력, 시간 제한, syscall 필터 | 자식 출력의 backpressure, 부분 입출력·EAGAIN, 출력 한도 안의 정확한 바이트 수, 실제 대기 시간과 정리를 확인한다. | [P346 출력 유실·sleep](../reports/S22PLUS_FYG8_P346_ADJACENT_FAILURE_AUDIT_2026-09-06.md), [P347 수정](../reports/S22PLUS_FYG8_P347_OUTPUT_TIMING_PREPARED_2026-09-06.md) |
| SEMANTIC | 명령 결과·신원·성공 판정 | 숫자 UID/GID와 필요한 생산자의 상태·출력을 검증한다. exit 0, 마지막 shell 명령 성공, ioctl 반환, CONTROL ACK가 각각 무엇을 증명하는지 명시한다. | [P345 신원·투영](../reports/S22PLUS_FYG8_P345_SHELL_QUALIFICATION_NO_PROOF_2026-09-06.md), [P346 false success](../reports/S22PLUS_FYG8_P346_ADJACENT_FAILURE_AUDIT_2026-09-06.md) |
| WIRE | 프로토콜, 관찰기, 진단 프레임 | 실제 C 생산자부터 실시간 수집기·원시 저장·재파싱까지 잇는다. 조기 거부 때문에 필요한 실패 증거가 사라지지 않는지, OPEN/raw 설정 순서와 부분 프레임 처리가 맞는지 확인한다. | [P339 수집 중단](../reports/S22PLUS_FYG8_P339_INITIAL_CAPTURE_INCIDENT_2026-09-05.md), [P341 OPEN 순서](../reports/S22PLUS_FYG8_P341_HOST_FIRST_OPEN_PREPARATION_2026-09-05.md) |
| PERSIST | 증거 필드, 세션 수, 준비·상태·결과 JSON | 성공과 후반 실패의 실제 생산자 출력을 실제 writer로 저장하고 reader로 다시 연다. 중첩 bytes·자료형·들여쓰기까지 포함한 크기와 단계별 한도를 확인한다. 대표 크기 시험과 완전한 경로 시험은 구분한다. | [P310 JSON](../reports/S22PLUS_FYG8_P310_CARRIER_V2_JSON_SERIALIZATION_INCIDENT_2026-08-09.md), [P364 상태 용량](../reports/S22PLUS_FYG8_P364_HISTORICAL_FAILURE_APPLICABILITY_AUDIT_2026-09-08.md#1-success-evidence-can-exceed-the-current-state-writers-bound) |
| ROUTE | 새 후보·스키마 등록, 공통 실행기 | 실제 prepare/reopen, 성공·NO_PROOF·CLOSED 결과 경로가 올바른 namespace와 reader를 선택하는지 확인한다. 공유 필드 예외는 정확한 이름과 소유자에 묶고 다른 후보 입력은 거부한다. | [P339 잘못된 분기](../reports/S22PLUS_FYG8_P339_INITIAL_CAPTURE_INCIDENT_2026-09-05.md), [P364 결과 저장 오류](../reports/S22PLUS_FYG8_P364_PREPARATION_DIAGNOSTICS_2026-09-08.md#host-terminal-publication-incident-and-repair) |
| ARTIFACT | 빌드 변환·패키징·승계 | 실제 AP를 풀어 Image의 raw/embedded-config 식별자, init, 모듈, 관찰 계약을 맞춘다. 의도한 소스와 실제 사용한 파일을 연결한다. 소비된 입력과 승인 pin은 보존한다. | [P320→P321 혼합 식별자 수정](../reports/S22PLUS_FYG8_P321_IDENTITY_USB_RACE_H0_2026-08-31.md) |
| AUDIT | 읽기 전용 검사·결과 복구 도구 | 읽기와 인덱스 복구를 구분한다. 호출하는 helper까지 쓰기 동작을 확인한다. 무변경을 주장하는 범위가 내용인지 inode·시간·모드까지인지 명시하고 scratch에서 검증한다. | [P325 Journal.reopen](../reports/S22PLUS_FYG8_P325_CLOSED_RESULT_FINALIZER_INDEPENDENT_REVIEW_2026-09-02.md), [P364 적용성 감사](../reports/S22PLUS_FYG8_P364_HISTORICAL_FAILURE_APPLICABILITY_AUDIT_2026-09-08.md#2-journal-reopen-is-a-repairing-operation-not-a-pure-read) |
| DISPLAY | DRM 초기 상태·버퍼·표시 경로 | 실제 vendor 드라이버 이름·초기 plane 상태·포맷·메모리 경로와 맞춘다. 기존 성공 렌더러를 유지할 수 있으면 재사용한다. 호스트 픽셀, ioctl 수락, 실제 표시 증거를 구분한다. | [P352 초기 상태](../reports/S22PLUS_FYG8_P352_SOURCE_BOUND_DISPLAY_H0_2026-09-07.md), [P358 캐시 경로](../reports/S22PLUS_FYG8_P358_CACHED_FRAMEBUFFER_PREPARATION_2026-09-07.md) |
| RETURN | 종료·재부팅·복구·보고 순서 | 실제로 증명한 복구 범위와 물리적 복구 필요성을 유지한다. 성공적인 롤백을 기능 성공으로 바꾸지 않는다. 효과 뒤 보고 오류는 보존된 저널에 따라 처리하며 효과를 반복하지 않는다. | [P318 후반 보고 오류](../reports/S22PLUS_FYG8_P318_POSTROLLBACK_FINALIZATION_INCIDENT_H0_2026-08-17.md), [P362 native 복귀 범위](../reports/S22PLUS_FYG8_P362_REBOOT_DOWNLOAD_PATH_ANALYSIS_2026-09-07.md) |

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
