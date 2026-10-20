# S22+ P452: 단일 CPU에서 실제 rcS script 진행 관측

상태: **H0 설계; 구현·검토·qualification·기기 승인은 아직 없음**.
대상은 FYG8 S22+ 하나다. P448/P450/P451은 모두 소비·건강 종료됐으며 다시
실행하지 않는다. 이 문서는 구현 전에 기록한 선택과 완료 기준이다.

## 선택과 완료 기준

P448의 retained kernel/82 modules, `cpuidle.off=1 maxcpus=1`, revision-6
CPU/driver 상태 확인과 기존 Debian 서비스 목표를 유지한다. P451에서 인증된
P448 early/runtime 두 파일만 exact history에 추가한다. 기존 여덟 행에 두 행을
더하는 것으로, P450의 과거 complete-root 거부를 성공으로 바꾸지 않는다.
새 부팅의 두 차례 전체 clean protected admission이 각각 쓰기 전에 통과해야
한다. P445 runtime이나 미확인 파일은 여전히 허용하지 않는다.

P445에서 검증했던 RAM serial dispatcher와 anonymous nonblocking datagram
채널을 공용 코드로 분리한다. 새 선택은 proc watchdog sampling, tracefs,
kprobe, observer state handover를 사용하지 않는다. 설치된 rc/rcS bytes와
서비스 순서·반환 처리는 보존한다. 새 상주 프로세스나 native_data 파일은 없다.
동일한 rcS 부모와 즉시 fork child만 채널을 소유하며, service/helper에는 fd3와
shell이 보관한 복제 descriptor가 전달되지 않아야 한다.

관측 시작은 실제 rcS 진입이다. 최대 120000 ms의 상대 관측 창을 원래 절대
300000 ms BOOTTIME deadline으로 자른다. 새 VM 전용 timing offset은 없다.
부모의 기존 2000 ms logger 예산 안에 setup/read/record/close 비용을 포함한다.
최대 34개 packet은 dispatcher 진입 D, 고정 16개 script의 B/E·exit status,
dispatcher 종료 X다. 기존 wait loop에서 최대 8개의 드문 부모 진행 기록도
추가한다. 각 drain은 최대 8개, child reap 뒤 최종 drain은 최대 5회다.
기존 96 records/actor와 512 bytes/record 상한은 늘리지 않는다.

채널 setup 실패·포화·유실·예산 종료는 관측을 닫고 원래 workload를 계속한다.
재시도·새 관측 창·새 실행 권한은 생기지 않는다. 받은 packet은 기존 stock
RAM logger의 run/boot/actor/sequence 인증 envelope로 남긴다. packet의 시각은
부모 수신 시각이며 script 실행 시각이 아니다. B 이후 E가 없다는 사실은 해당
script의 정지, reset 시각 또는 원인을 증명하지 않는다. rcS child reap은
dispatcher process의 종료이고 개별 service process의 건강 증거가 아니다.

H0 완료 기준은 실제 producer/consumer와 ARM64의 정상 및 failure 경로에서
원래 script 순서·status, descriptor 격리, late start, bounded/loss semantics를
검증하고, 실제 A/B archive와 기존 서비스·SSH·shutdown qualification을 통과하는
것이다. 독립 검토는 변경된 공용 채널과 decoder, history, 정책 상호작용 및
실제 선택된 runtime을 포함한다. 기능 성공 기준은 그대로 설치 PID1, local
120초 서비스, 같은 boot/count의 두 SSH health(120초 간격), 고정 shutdown이다.
관측 기록만으로 기능 성공을 선언하지 않는다.

## Android와 driver 비교를 이번 작업에 연결하는 범위

입력은 retained root archive를 symlink/usr-merge까지 해석한
[P441 후속 감사](S22PLUS_P441_WATCHDOG_FOLLOWUP_H0_2026-10-20.md)와
[순정 첫 watchdog 감사](S22PLUS_FYG8_STOCK_FIRST_WATCHDOG_H0_2026-10-20.md)다.
선택 script bytes를 다시 읽어 아래 kernel-visible 작업을 대응시켰다. 표는
가능한 실행 경로를 정리하며 P448에서 실제 실행됐다고 주장하지 않는다.

| ID / script | Debian의 관련 작업 | Android/driver와 대조할 지점 |
| --- | --- | --- |
| 1 hostname | hostname 설정 | UTS 설정; watchdog pet의 선행 조건 근거 없음 |
| 2 mountkernfs | proc/sysfs/securityfs/pstore 및 RAM mount 확인 | Android early-init의 mount 순서와 이미 옮겨진 mount의 재사용 |
| 3 udev | 선택 archive에서 daemon 부재로 조기 종료 | Android ueventd와 동등한 장치 관리가 실행됐다는 뜻이 아님 |
| 4 mdev | background `busybox mdev -df` 시작 | uevent/netlink와 장치 node 처리; 이후 script와 병행 가능 |
| 5 mountdevsubfs | shm/devpts mount 확인 | terminal/pty 및 RAM mount; 새 하드웨어 초기화와 구분 |
| 6 kmod | 고정 config에 따른 modprobe | 기존 82개 모듈·Android modules.load와 실제 요청된 module만 비교 |
| 7 mount-configfs | configfs가 없으면 mount | 이후 고정 gadget 준비와 mount 공유; 이 script 자체는 NCM 증거 아님 |
| 8 mountall | fstab local mount와 RAM directory 준비 | 기존 native_data root 및 retained fstab; 일반 Android fstab을 적용하지 않음 |
| 9 mountall-bootclean | 정해진 임시 directory 정리 | RAM/허용 root 경로의 기존 동작과 실제 mount 상태 |
| 10 brightness | 선택된 ACPI/Intel backlight knob 검사 | FYG8 panel driver와 이름/경로가 다름; 실제 존재·접근 경계만 후속 조사 |
| 11 procps | 선택 sysctl 적용 | core_pattern/pid_max 등 실제 설정; 현재 config에 RT/user-pet/cpuidle 변경 없음 |
| 12 urandom | seed 읽기·갱신, urandom 접근 | 기존 root mutable lifetime과 random driver; 새 증거 파일 추가 아님 |
| 13 networking | ifup와 hotplug config | 기존 interface 설정 및 별도 NCM lifetime; 반환만으로 외부 접근 증명 불가 |
| 14 mountnfs | 선택 fstab의 network mount 처리/대기 | retained fstab과 실제 branch; 일반적인 NFS 지연을 원인으로 가정하지 않음 |
| 15 mountnfs-bootclean | 임시 directory 정리 | 9번과 같은 실제 mount/경로 확인 |
| 16 bootmisc | 초기 임시 marker 정리 | rcS dispatcher 종료와 이후 runlevel 진입을 구분 |

순정 첫 pet은 약 10.24초이며, 뒤의 약 16초 postboot userspace 서비스가 먼저
필요하다는 가설은 기존 자료가 지지하지 않는다. 선택 kernel의 WALT/cpufreq/
idle 차이와 GH SMC/firmware queue·lock 분석은 입력이 같아 재사용한다.
rcS 경계가 새로 특정한 작업을 가리키면 그 작업의 실제 Android init 명령과
driver 호출 경로를 좁게 비교한다. 현재 누락된 실패 시점의 pet/CPU/PC는 광범위한
firmware 재해독으로 복원되지 않는다. 새로운 직접 근거가 있을 때 그 분석을 연다.

## 권한과 복구

새 `post-autoboot-p451-v1` 선택은 common details, target와 automatic-boot
policy에 함께 명시하고 독립 검토한다. 기존 300000 ms/360초, 두 RW lifetimes,
한 NCM 시도, 현재 Android32 health 및 물리 Download/original-A 복구를 유지한다.
상대 관측 창은 원래 실행 deadline을 연장하지 않는다. 자동복구는 주장하지 않는다.
실기 실행에는 현재 lane의 별도 returned attended 1-operation/3600-second grant가
필요하다. host `NoNewPrivs`가 계속 census를 막으면 원래 runner/check를 보존한
검토된 operator-terminal 진입을 사용한다. A90·S20+와 기존 다른 작업은 보존한다.
