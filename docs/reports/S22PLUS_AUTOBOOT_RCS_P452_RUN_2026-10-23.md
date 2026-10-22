# S22+ P452 rcS 관측과 원본 A 복구

P452는 **소비됐고 ANDROID_CLOSED_HEALTHY로 종료됐다**. 승인된 N 전송과
원본 A 복구 전송은 각각 한 번이다. grant는 닫혔고 F1 owner는 남아 있지 않다.
실시간 서비스/SSH 판정은 **NO_PROOF**다. 별도 post-return 증거에서는 설치된
Debian PID1, rcS dispatcher 진입과 첫 script `S01hostname.sh`의 성공 종료를
인증했다. rcS 전체 완료, 120초 서비스, SSH와 clean shutdown은 증명하지 못했다.
A90와 S20+에는 작업하지 않았다.

후보와 독립 검토는 [H0 qualification](S22PLUS_AUTOBOOT_RCS_P452_H0_2026-10-21.md),
구현 commit `23744b4aba7ca2d96c116f01dcc397de5bbaa118`에 연결된다.
사용자가 정확한 1-operation/3600-second attended 승인을 반환한 뒤 일반 터미널의
원래 runner가 source/artifact/recovery 및 현재 Android 검사를 수행했다.
유일한 N 전송 후 원래 360초 관측 창이 끝났고 USB 표본 90개는 모두 선택 경로의
`ABSENT_USB`를 기록했다. NCM endpoint, 인증된 live envelope, SSH 건강 증거는
없으며 SSH shutdown도 실행하지 않았다. USB 부재는 Debian 비실행 증거가 아니다.

## 복구와 종료 검증

사용자가 물리 Download 진입 후 기존 recovery 명령을 실행했다. 원래 observer가
정확한 endpoint를 검증한 뒤 A를 한 번 전송했다. 첫 post-A 건강 bracket의
root-read가 `device not found`로 실패했다. 이 원시 증거를 남기고 기존 runner의
건강 읽기만 새 시도로 이어갔다. A 전송과 실험은 반복하지 않았다.

최종 changed-boot Android root, 원본 boot와 supporting partitions, GPT,
Android32 용량 검증이 통과했다. 424개 raw capture와 15행 journal을 원래
consumer로 재도출했고, 실패 capture는 위 읽기 하나다. H0 closure는 device/process
acquisition을 차단한 상태에서 원래 terminal과 journal이 그대로임을 검사했다.
원본 A 복구는 native_data의 변경을 되돌리거나 현재 파일시스템의 clean 상태를
입증하지 않는다.

시간은 최초 grant의 host BOOTTIME 시작부터의 초다.

| 사건 | 초 / 결과 |
| --- | ---: |
| Live session 시작 | 0.000 |
| Android Download 요청 | 67.237 |
| N 전송 시작 | 88.934 |
| N 전송 완료 | 92.459 |
| Candidate boot ready | Live criterion으로 미증명 |
| 관측 중단 | 452.479 |
| 원본 A 전송 시작 | 70317.415 |
| 원본 A 전송 완료 | 70318.830 |
| 원본 A 건강 검증 완료 | 70469.495 |
| H0 task closure | 70477.617 |

원본 A 복구는 연구 grant 만료 뒤 수행됐다. 기존 recovery 경로는 만료된 연구
예산을 갱신하지 않고, 소비된 effect에 대한 원본 복구와 건강 검증만 허용한다.
관측 종료와 물리 복귀 사이의 기기 활동 또는 정지는 증명되지 않았다.

## 회수된 rcS 증거

정상 Android 복구와 task closure 뒤 기존 fixed D0로 같은 복귀 boot의 `last_kmsg`를
한 번 읽었다. Before/after health를 포함한 16개 capture가 통과했고 raw log는
2,097,136 bytes다. 원래 strict collector는 한 boot의 transition 135개를
인증하고, 비정규 line 하나를 거부하며 충돌은 보고하지 않는다.

첫 retained kernel fragment에는 header가 없다. 그 fragment의 authenticated
preparation은 `STORAGE_READY`와 두 helper의 성공 종료까지 이어진다.
Transition은 첫 file lifetime의 unmount/partition RO at 8.632 seconds,
clean-superblock observation at 8.633, installed actual-init check at 15.400,
rcS fork at 15.462와 첫 sleep의 성공 반환 at 15.475 seconds를 기록한다.
현재 native_data 상태를 과거 clean 관측으로 대체하지 않는다.

rcS-relative channel setup은 15.461 seconds, window end는 135.461 seconds로
인증됐다. 원래 collector의 script packets는 연속 1–3이다.

| Packet | 인증된 경계 |
| --- | --- |
| 1 / D | 변환된 dispatcher 실행 진입 |
| 2 / B | `S01hostname.sh` 호출 직전 |
| 3 / E / status 0 | `S01hostname.sh` 성공 반환 |

세 packet의 부모 수집 시각은 15.567 seconds다. 이 값은 각각의 script 실행
시각이나 소요 시간이 아니다. Legacy `rcs_child_exec_proved` 필드는 전체 rcS
완료에 묶여 false로 남는다. 별도 script-channel의 `dispatcher_exec_proved=true`
양성 사실을 사용하며 원래 필드나 live terminal을 다시 분류하지 않는다.

비정규 line에는 완전한 MAC-valid frame과 firmware-text suffix가 함께 있다.
별도 H0 extent 감사는 이 frame을 원래 boot/source/parent와 연속 actor sequence,
packet sequence로 연결했다. 내용은 packet 4 / `S01mountkernfs.sh` B다.
이는 호출 직전 경계이며 script 반환이나 내부 mount syscall 진입 증거가 아니다.
Strict projection과 그 rejected count는 수정하지 않았다.
이후 E/다음 packet/부모 진행 기록이 없는 것은 정지 위치나 실패 원인을 증명하지 않는다.

## 여러 부팅과 사용자 관찰

회수 범위에는 서로 다른 인증된 candidate boot 세 개가 있다. 첫 번째는 header가
잘린 fragment이고, 뒤의 두 kernel span은 `cpuidle.off=1 maxcpus=1` 및 한 processor
활성화를 각각 기록한다. 이 두 startup 관측을 첫 fragment의 현재 CPU 상태나
연속적인 CPU 상태의 증거로 전용하지 않는다.

첫 fragment의 마지막 kernel timestamp는 15.601371이다. 다음 span은 preparation
`STORAGE_READY`와 helper 2 START를 남기지만 그 helper의 종료는 입증하지 않는다.
그 span의 마지막 timestamp 값은 79220.095411이다. 마지막 span은
`MODULE_BEGIN ordinal=3 name=qcom_hwspinlock`까지 인증하고 마지막 timestamp 값은
1.277631이다. 각 span 뒤에 warm-reset firmware header가 있다. 이 timestamp들은
보존된 로그 값이며 정확한 reset 시각 또는 host 시간과의 대응을 뜻하지 않는다.

사용자는 Download 모드 진입을 시도하다 실수로 한 번 더 부팅했다고 별도로
알렸다. 이 관찰은 private 원문으로 보존했다. 어느 retained span이 그 조작에
해당하는지, 다른 reset이 언제 왜 일어났는지는 특정하지 못한다.
선택된 kernel 범위에는 watchdog bark/bite, panic, Oops 기록이 없지만, 누락 가능한
로그로 그 사건의 실제 부재를 증명할 수 없다. Watchdog pet/실패 원인은 미증명이다.

## 남은 범위

현재 P452 early/runtime 파일은 회수하지 않았고 native_data의 현재 일관성도
미확인이다. 다음 H0 분석은 실제 인증된 두 번째 경계의 retained mountkernfs script와
callee를 좁게 확인할 수 있다. 새로운 쓰기 후보는 별도 현재 파일 qualification과
새로운 complete protected admission이 필요하다. 이 결과는 P452 재실행, filesystem
repair 또는 journal replay를 허용하지 않는다.

Private evidence base는
`workspace/private/outputs/s22plus-autoboot-rcs-p452-h0-20261021-1/`이다.
원래 approval/grant/source snapshot, raw journal/terminal, closure audit,
retention capture와 strict projection, fragment-aware extent audit, 해석 및 사용자
복귀 관찰을 보존했다. H0 audit/interpretation은 device/process acquisition을 차단한다.
