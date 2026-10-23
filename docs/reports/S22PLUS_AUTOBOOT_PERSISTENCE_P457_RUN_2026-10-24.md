# P457: P456 기록의 Android 반환 후 영속성 확인

P457은 **PASS_P456_LIVE_PAIR_RETAINED_AFTER_ANDROID_RETURN**이며
**ANDROID_CLOSED_HEALTHY**로 종료됐다. P456의 early/runtime 파일을 partition RO,
mountless 방식으로 읽었고, 두 파일 모두 P456 실기 live snapshot과 길이·SHA-256·
전체 바이트가 일치한다. 원래 물리 writer의 source/key/run 인증과 원래 live boot/
nonce 비교도 모두 통과했다. N과 원본 A 전송은 각각 한 번이며 task는 소비·종료됐고
F1 owner는 없다. A90와 S20+에는 작업하지 않았다.

[P457 H0 준비](S22PLUS_AUTOBOOT_PERSISTENCE_P457_H0_2026-10-24.md)의 구현은
`584ff8a520`이다. 실제 실행은 반환된 1800초 / 1-operation 참석 승인, 검토된
일반 터미널 진입점과 원래 V3 runner를 사용했다. 141개 host 및 165개 runtime/
collector source는 frozen working-tree snapshot에 묶여 있다. 현재 연결된
작업자의 이전 CLI source pin은 변경하지 않았고 서버 작업도 재개하지 않았다.

## 보존된 파일과 현재 관측

| 항목 | 결과 |
| --- | --- |
| Early 파일 | 10,972 bytes / 14 authenticated records, live snapshot과 전체 일치 |
| Runtime 파일 | 3,456 bytes / 25 authenticated records, live snapshot과 전체 일치 |
| 원래 boot/nonce | 두 파일끼리 및 독립적인 P456 live envelope와 모두 일치 |
| 보존된 마지막 단계 | SERVICES_120S_COMPLETE, service observation 120,030 ms |
| 현재 superblock | state 1 / RECOVER 0 / orphan 0 |
| 읽기 보호 | Partition RO 유지, mount·journal replay·filesystem write 없음 |
| Android 복귀 | 원본 A 1회, changed-boot root/partition/GPT/Android32 최종 건강 통과 |

P456 early live 채널은 RAM mirror였지만, 이번에는 독립적인 새 reader 부팅에서
실제 파일의 전체 바이트를 읽어 그 mirror와 비교했다. 따라서 두 기록이 P456의
Android 복귀 이후에도 저장장치에 보존됐다는 증거다. 보존된 service records는
[원래 P456 한 부팅의 기능 증거](S22PLUS_DEBIAN_MINIMAL_P456_RUN_2026-10-24.md)와
연결되며 새로운 Debian service/SSH 실행을 뜻하지 않는다.

현재 clean home-block view는 clean shutdown의 실행 경로나 전체 root admission을
증명하지 않는다. P457은 전체 root tree를 비교하지 않았고 installed Debian init도
실행하지 않았다. 일반 Debian reboot, package/configuration 지속성, 자동 복구는
여전히 별도 범위다. 다음 writable boot는 이번 인증된 history를 자격화하고 원래
완전한 protected-root admission을 통과해야 한다. 이 read는 새 writer 권한을 주지
않으며 소비된 P456/P457을 재실행할 수 없다.

## Android 건강 검사 continuation

원래 native CONTROL/Download 복귀 뒤 원본 A가 한 번 전송됐다. 첫 post-A 건강
bracket의 첫 inventory에는 정확한 target이 있었지만, 두 번째 inventory는
정상 exit 0과 빈 기기 목록을 반환했다. 원래 selector가 이를 거부했고 journal에
`SessionError` stop이 기록됐다. 프로세스의 exit 0을 건강 성공으로 해석하지 않았다.

원래 runner의 복구 분기는 이미 완료된 A 전송을 raw evidence로 재도출하고
`recovery-health`만 수행했다. 추가 전송이나 CONTROL 재실행 없이 전체 최종 건강
검사와 terminal closure가 완료됐다. `recovered=true`는 이 health-only continuation을
뜻한다. Inventory에서 사라진 근본 원인은 이번 관측으로 확정하지 않는다.

H0 audit는 실패한 두 번째 inventory를 원래 selector에 다시 넣어 같은 거부를
재현했다. 648개 raw captures는 모두 producer exit 0이며 별도의 semantic 건강
실패가 한 번 있다. 이 차이와 원래 실패 bytes, 20행 journal을 그대로 보존했다.

## 시간과 보존

시간은 최초 grant의 BOOTTIME 시작부터의 초다.

| 사건 | 초 |
| --- | ---: |
| N 전송 시작 / 완료 | 15.448 / 16.953 |
| 인증된 native boot 및 고정 read 시작 | 42.189 |
| 고정 read 완료 | 46.630 |
| 원본 A 전송 시작 / 완료 | 54.920 / 56.480 |
| 최종 Android 건강 완료 | 103.920 |
| H0 task closure | 178.487 |

H0 closure와 파일 해석은 process/device acquisition을 차단하고 원래 consumer로
실행했다. 648개 captures, unique N/A claims, 현재 review와 source snapshot,
initial/final health 및 unchanged journal/terminal을 검증했다. 두 raw 파일을 먼저
보존한 뒤 인증·해석했고, P456의 실제 SSH envelope를 다시 인증해 비교 기준을
확인했다. Private evidence는
`workspace/private/outputs/s22plus-autoboot-persistence-p457-h0-20261024-1/`에 있다.
