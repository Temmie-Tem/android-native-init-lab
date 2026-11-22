# S22+ FYG8 uniLoader LOGM 실기 결과

**PASS_LOADER_FYG8_ANDROID · READBACK_AND_SNAPSHOT_OBSERVED · ANDROID_CLOSED_HEALTHY**

SM-S906N/g0q/FYG8에서 동일한 LA002 기록기와 새로운 후보 표식을 넣은
boot-only 이미지를 1회 실행했다. 운영자의 정확한 1,800초 입회 승인을
저장했다. 이전 사전 판독의 300초 유효 시간이 지나, 같은 요청의
original-A 상태를 지정된 읽기 전용 절차로 한 번 갱신했다. 현행 로더
검토와 백엔드 V52를 사용했다. [작업 절차](../operations/S22PLUS_LOADER_ANDROID_V1.md)

## 후보에서 관측한 결과

후보 Android의 부팅 완료, 숫자 UID 0, 예상 벤더 커널, boot 이미지와
지원 파티션 해시, uniLoader 표식을 확인했다. 한 후보 Android 부팅과
같은 USB 세대로 묶인 두 상태 확인 사이에 FDT 보고서와
`/proc/last_kmsg`를 수집했다. 후보 Download 전환 직전에도 동일한
부팅을 다시 확인했다.

| 항목 | 관측 |
| --- | --- |
| 로더 기록 시점 | 벤더 커널 인계 직전, EL1 |
| 쓰기 직후 128바이트 판독 | 불일치 0바이트 |
| 쓰기 전, 커밋 전, 커밋 후 LOGM 헤더 | 세 표본 동일 |
| Android에서 수집한 스냅샷 | 2,097,136바이트 |
| 후보 HMAC 프레임 | 온전한 표식 1개, 손상 및 외부 후보 0개 |

봉인된 원시 FDT와 스냅샷에서 후보 HMAC를 독립 계산해 실행 도구의
판독과 대조했다. FDT 보고서는 관측한 부팅의 로더 기록 결과를
보여준다. 정적 HMAC 프레임은 후보 이미지에 묶여 있으며, 해당
프레임을 쓴 단일 부팅 시도까지 식별할 수 없다. 수집은 후보
Android에서 이루어졌다. Download 또는 복구 후의 보존, 전원
단절 후 보존, 메인라인 SCM 관측은 미검증이다.
[이전 LA002 양성 대조](S22PLUS_LOADER_LOGM_LA002_RUN_2026-11-03.md)

## 복구와 종료

후보 Android에서 일반 Download로 돌아갔고, 같은 실행이 기존
original-A를 한 번 전송했다. 첫 최종 상태 판독의 고정 root 명령이
종료 코드 1과 `error: closed`를 반환했다. 그 시도의 원시는
보존했다. A 전송 완료 증거와 기존 소유자를 확인해 상태 판독만
한 번 이어갔다. 새 판독에서 원본 boot와 지원 파티션 해시, 숫자
UID 0, Android 부팅 완료와 중지된 부팅 애니메이션을 확인했다.
복구 후 Android의 부팅 ID는 확인된 후보 부팅과 달랐다. 첫
판독 실패의 원인 자체는 확인되지 않았다.

| 경과 시간 | 이벤트 |
| ---: | --- |
| 30.809초 | original-A에서 처음 Download 전환 요청 |
| 43.630 / 45.131초 | 후보 이미지 전송 요청 / 완료 |
| 150.437초 | 후보 Android와 LOGM 관측 완료 |
| 152.486초 | 후보에서 Download 전환 요청 |
| 165.483 / 167.030초 | original-A 전송 요청 / 완료 |
| 208.337초 | 첫 최종 상태 판독 실패와 정지 |
| 234.154 / 235.920초 | 기존 소유자의 상태 전용 이어가기 시작 / 최종 정상 상태 |

전송은 후보 1회와 original-A 1회였고, Download 전환은 2회였다.
후보 재실행이나 복구본 재전송 없이 종료했다. 원시 기록과 정본
타임라인은 `workspace/private/outputs/s22plus-loader-logm-refresh-h0-20261122-1/`의
`task-1/closed.json`에 연결돼 있다. `offline-audit.json`은 봉인된
원시 데이터로 재검증한 수치다. 실행 소스는 로더 검토 갱신
`e35ad93644`와 이 요청의 `source-snapshot.json`에 연결돼 있다.
