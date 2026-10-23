# P456 최소 Debian 부팅 실기 결과

P456은 **PASS_DEBIAN_AUTOMATIC_INITIAL_PID1_TO_SSH**이며,
**ANDROID_CLOSED_HEALTHY**로 종료됐다. 같은 실기 부팅에서 Debian 초기 PID1,
설치된 SysVinit PID1, 최소 초기화와 runlevel 2 완료, init·cron·sshd의 120초
관측 및 NCM을 통한 인증된 SSH 접근을 증명했다. 서로 126.830초 떨어진 두 SSH
상태 응답은 같은 boot와 boot count를 가리킨다. N과 원본 A 전송은 각각 한 번이다.
Task가 닫혔고 F1 owner는 없다. A90와 S20+에는 작업하지 않았다.

[H0 준비](S22PLUS_DEBIAN_MINIMAL_P456_H0_2026-10-23.md)의 실제 A/B 패키지,
141개 host 및 159개 runtime/collector source와 정확한 반환 승인을 사용했다.
구현은 `60d825c040`, [연결 도구 보완](S22PLUS_APPROVED_TERMINAL_AUTOBOOT_H0_2026-10-23.md)은
`28c31c1526`이다. 실제 실행 소스는 기존 별도 변경을 포함한 frozen working-tree
바이트에 묶여 있으며 commit만으로 그 전체 동일성을 주장하지 않는다.

## 같은 부팅에서 검증된 기능

새 작업자의 검토 identity를 확인한 뒤 커넥터로 한 번 실행했다. 원래 runner가
현재 target, Android 건강, rollback, source와 artifact를 검사하고 N을 전송했다.
두 protected-root admission과 두 bounded writable lifetime 이후 Debian이
설치된 init과 packaged services를 실행했다. SSH 최초 상태 응답은 device uptime
23.700초, 마지막 응답은 150.530초다. 모두 원래 300초 device deadline과
N 완료 후 360초 host 관측 창 안에 있다.

| 증거 | 결과 |
| --- | --- |
| Debian 초기 PID1 | 같은 run/boot/source의 early envelope로 확인 |
| 설치된 Debian PID1 | root-transition witness와 runtime envelope로 확인 |
| 최소 초기화·runlevel 2 | 선택된 최소 sysinit 및 packaged rc2 완료 |
| init·cron·sshd | 120초 service window의 고정 표본 검증 통과 |
| 실제 SSH | 같은 boot/count의 두 상태 응답, 126.830초 간격 |
| 현재 실행 파일 | early 10,972 bytes / 14 records, runtime 3,456 bytes / 25 records |
| 종료 | 고정 SSH shutdown 요청 수락 및 원래 USB departure 확인 |
| Android 복귀 | 원본 A 1회 전송, changed-boot root/partition/GPT/Android32 건강 확인 |

최소 sysinit 완료는 생략한 원래 16개 rcS script 전체의 실행 증거가 아니다.
두 SSH 응답은 표본 간 접근을 증명하며 연속 접속을 뜻하지 않는다. Shutdown
수락과 departure만으로 clean filesystem shutdown을 주장하지 않는다. 현재
native_data 일관성, 다음 native boot의 persistence, 일반 Debian reboot,
watchdog pet 및 자동 복구는 별도 미검증 범위다.

## 물리 복귀와 최종 건강 검사

원래 owner가 `AWAITING_PHYSICAL_DOWNLOAD`를 기록한 뒤 사용자가 물리 Download
전환과 원래 CLI의 `continue --attended`를 한 번 수행했다. 커넥터에는 이
이어가기 기능이 없어 해당 host 명령은 직접 실행했다. 정확한 endpoint를 검사한
원래 runner가 A를 한 번 전송했다.

첫 post-A 건강 bracket에서 ADB가 `device not found`로 실패했다. 원시 capture와
`stopped` journal을 보존했다. 원래 A의 유일한 intent와 raw transfer completion,
retained owner 및 이전 CLI 종료를 확인한 뒤 원래 `recover --attended` 경로의
남은 D0 건강 검사만 이어갔다. 이 분기는 기존 A completion을 재도출하며 A를
다시 전송하지 않는다. 호스트 privilege 변경이나 새 grant는 없었다.

마지막 건강 확인과 task closure가 완료됐다. Terminal의 `recovered=true`는
이 건강 검사 continuation을 반영하며 추가 복구 전송을 뜻하지 않는다.
원래 소비된 후보, shutdown 및 전송을 다시 실행할 권한은 없다.

시간은 최초 grant의 host BOOTTIME 시작부터의 초다.

| 사건 | 초 |
| --- | ---: |
| Live session 시작 | 0.000 |
| Android Download 요청 | 67.854 |
| N 전송 시작 | 87.433 |
| N 전송 완료 | 90.979 |
| Candidate boot ready: 서비스와 SSH 검증 완료 | 253.832 |
| 원본 A 전송 시작 | 360.837 |
| 원본 A 전송 완료 | 364.265 |
| 최종 Android 건강 검증 완료 | 569.668 |
| H0 task closure | 634.422 |

## 보존과 검증

H0 closure는 process/device acquisition을 차단하고 원래 consumer로 346개
capture와 19행 journal을 재도출했다. Terminal과 journal은 바뀌지 않았다.
비영 exit 23개는 완성된 evidence를 기다리는 고정 read 19개, 이미 없는 host
network 설정에 대한 정리 관측 3개, 위 ADB 읽기 실패 1개다. 이들을 동일한
실행 실패로 합치지 않는다.

정상 closure 뒤 같은 반환 Android boot에서 승인된 fixed `last_kmsg` D0를
한 번 수행했다. Before/after 건강 검증과 strict collector는 통과했지만 P456의
인증된 retained transition은 없었다. 이 별도 채널의 부재는 이미 수신·검증한
live PID1/service/SSH envelope를 부정하거나 비실행을 증명하지 않는다.

Private evidence는
`workspace/private/outputs/s22plus-debian-minimal-p456-h0-20261023-1/`에 있다.
반환 승인, 커넥터 dispatch, grant, N/A raw transfer, live SSH envelope, 실패한
post-A bracket, 건강 continuation, frozen sources, canonical timeline 및
post-closure D0를 보존했다. 기능 판정은 같은 한 부팅의 live 증거에만 근거한다.
