# S22+ P452 rcS channel: H0 qualification

상태: **H0 준비 완료; 이후 실기 작업은 소비·정상 Android 복구 완료**.
[별도 실행 결과](S22PLUS_AUTOBOOT_RCS_P452_RUN_2026-10-23.md)를 참조한다.
아래는 실행 전 qualification이며 실기 기능 성공이나 재실행 권한을 선언하지 않는다.
[구현 전 설계](S22PLUS_AUTOBOOT_RCS_P452_DESIGN_2026-10-21.md)는
`5a04f253ce`에 먼저 기록했다. 대상은 FYG8 S22+ 하나이며 A90·S20+와 기존
46개 변경 경로는 이 작업의 root revision/pin 변경을 제외하고 보존한다.

## 구현

P448의 retained kernel/modules, single-CPU 설정, revision-6 상태 확인과
서비스/SSH/종료 조건을 유지했다. P451에서 인증된 P448 early/runtime의 정확한
두 행만 추가해 history 10개, immutable comparison 8,979개를 만든다.
과거 P450의 complete-root 실패를 변경하지 않으며, 새 부팅의 두 전체 clean
protected admissions가 각 쓰기에 앞서 통과해야 한다.

P445의 dispatcher transformer와 anonymous nonblocking channel/parser를 공용
코드로 분리했다. 새 선택은 proc sampling, tracefs/kprobe, 상태 handover를
실행하지 않는다. 설치된 rc/rcS 및 RAM dispatcher의 bytes는 이전과 같다.
기존 rcS 부모가 상대 120초 창을 절대 300초 deadline으로 제한한다. 관측은 기존
2초 logger 예산 중 최대 1.5초를 사용하고, cleanup도 같은 제한을 따라 후속 원래
기록에 0.5초를 남긴다. 막힌 syscall이나 descheduling의 초과 시간은 보장할 수
없다. 최대 34개 script packet과 8개 드문 부모 진행 기록은 독립 관측이다.
유실, setup 실패와 예산 종료는 관측을 닫으며 원래 workload의 실행을 막지 않는다.

stage 91–95의 decoder는 setup/child/packet/parent/summary를 구분한다.
script exit status, dispatcher child reap, 서비스 건강을 서로 대신하지 않는다.
받은 기록의 시각은 수신 시각이며, 없는 종료 기록은 stall/reset/원인 증거가 아니다.

## 실제 Android 초기화 파일과의 제한된 대조

기존 stock 추출 manifest의 해시를 다시 검사한 Android 파일 4개와, symlink 및
usr-merge를 해석한 rcS script 16개를 읽었다. 22개의 관련 정적 명령을 원래 block,
line과 함께 private crosswalk에 보존했다. 새로운 firmware 실행이나 기기 읽기는
없다. 이 대조는 실행 시각이나 실패 원인을 증명하지 않는다.

- 순정 system init의 `early-init`은 ueventd를 시작한다. Debian의 udev script는
  daemon 부재로 조기 종료하고, 그 뒤 별도 mdev background 실행 경로가 있다.
  두 환경의 장치 관리 순서를 같다고 가정하지 않는다.
- 순정은 `init` block에서 configfs를 `/config`, pstore를 `/sys/fs/pstore`에
  mount한다. Debian은 mountkernfs 및 mount-configfs에서 관련 가상 filesystem을
  확인한다. configfs 경로와 이후 gadget lifetime은 구분해야 한다.
- 순정 QTI `early-init`은 `vendor.modprobe`를 시작하고 `init`에서
  `vendor.all.modules.ready=1`을 기다린다. Debian의 고정 초기 82-module 준비와
  이후 rcS kmod는 별도 단계다. 새 script 경계가 kmod를 가리킬 때 실제 module
  요청과 driver dependencies를 좁게 비교한다.
- 순정은 init에서 cmdline/default properties, post-fs-data에서 entropy 파일을
  urandom에 공급한다. Debian은 기존 seed script를 사용한다. 해당 차이 자체가
  watchdog 실패 원인이라는 근거는 없다.
- 선택 QTI/qcom postboot 서비스는 `sys.boot_completed=1` 또는 charger trigger에
  연결된다. 따라서 기존 순정 첫 pet보다 늦은 서비스의 전체 설정을 Debian 초기
  선행 조건으로 복사하지 않는다. core_pattern의 순정 변경도 특정 debug property
  조건에 묶여 있다.

기존 watchdog/driver/firmware 감사는 입력이 같아 재사용한다. 새 기록이 특정
script나 호출 경로를 선택할 때 그 경로의 분석을 진행한다. 광범위한 firmware
해독이나 더 많은 proc 표본을 기능 후보의 새 선행 조건으로 만들지 않는다.

## 현재 검증과 수정

관련 단위 검사 123개와 변경 Python compilation이 통과했다. 명시적
`--script-channel --single-cpu --post-p447` CLI로 만든 현재 P452 physical
producer들은 ARM64로 cross-compile됐고 실제 생성 header/history 검증을 통과했다.
공용 코드를 쓰는 기존 phase 경로도 ARM64 A/B compile이 일치한다. P445·P448의
보존 producer validation과 P445의 생성 seal bytes는 그대로 통과한다.

기존 ARM64 dash fixture의 normal/full-queue/dead-peer/original 사례는 transformer
bytes가 일치함을 검사한 뒤 재사용한다. 16개 script 순서·nonzero status·서비스와
helper의 fd 격리를 검증한 증거다. 새 generic ARM64 구성요소 검사는 정상, gap,
잘못된 순서, zero/truncated packet, 포화, setup 실패, logger 예산 소진, 상대·절대
deadline, 실제 16초 뒤 시작, 부모 진행 및 logger loss를 검증했다. 500 ms로 짧게
바꾼 deadline fixture는 production decoder가 의도대로 거부한다. generic VM의
socket/clock 검증을 Samsung watchdog/hardware proof로 사용하지 않는다.

독립 초기 검토에서 optional child-channel 기록의 PID/PPID와 실제 fork 연결이
누락된 증거 판정 오류를 발견했다. mandatory stage 순서와 분리해 optional child도
fork/parent/causal/failure 검증에 포함했다. 잘못된 PID·부모, fork 전/reap 후 시각,
실패한 fork를 거부하고 올바른 연결은 유지함을 독립 재검증했다.

호스트 `NoNewPrivs=1` 때문에 original builder의 `newuidmap`이 실패한다. 단일
사용자 namespace는 원본 rootfs의 여러 소유자를 보존할 수 없으므로 그 대안은
채택하지 않았다. 기존 `--map-auto` 및 모든 build 검사를 유지한 H0 terminal
진입점은 독립 검토를 통과했다. 2026-10-22 일반 터미널 실행은 매핑 뒤
AppArmor `unprivileged_userns`의 rprivate mount 거부로 `inside` 진입 전에
실패했다. kernel audit의 거부 2행, 원본 namespace log와 request digest를
private에 보존했고 tree/archive/build result가 없음을 확인했다. 동일 명령은
재실행하지 않는다. 호스트 정책 변경 없이 별도 ARM64 VM에서 동일 `inside`
빌더와 다중 UID/GID 매핑을 실행하는 H0 대체 빌드 경로를 검토 중이다.
이 H0 대체 경로는 실제 ARM64 guest에서 import, UID/GID `0 → 1000:65536`,
tmpfs 및 `42:997` 소유자 설정을 확인했다. 별도 서명 검증한 Debian kernel과
Python 도구는 빌드용 guest에만 쓰고 원본 product root archive는 보존했다.
NIC/USB/passthrough 없이 새 regular-file ext4 disk 하나만 연결했다. 원본
`autoboot.build`의 단일 namespace 호출만 VM의 원본 `inside`로 넘긴 뒤 원래
A/B·payload·module metadata·source 검사를 모두 그대로 실행했다. guest 실행
188.897초에 A/B 10,692,344-byte initramfs가 일치했고 현재 producer도 통과했다.
각 실행의 실제 adapter source와 launch, 두 namespace map, bounded export의
사전 inode type/size 및 사후 digest 검사를 보존했다. 앞선 실패한 guest 준비와
호스트 실패를 성공으로 바꾸지 않는다. 통합 VM qualification도 아래의 전체 37개 사례를 통과했다.
실제 Opus 5.5 source 검토와 후속 재검토에서 남은 actionable finding은 없다.
budget reserve, noexec fallback, CLI 선택, 잘못된 sampler 증거의 conflict와 오류
label을 반영했다. 후속 검토가 직접 보지 못한 logger deadline, owner stage81/82,
현재 producer와 ARM64 fixture는 로컬 원본·결과로 확인했다. 독립 내부 재검토도
수정된 실행 의미와 virtual fault의 기능 검증 조건을 확인했다. 최종 artifact 및 통합 VM의 별도 독립 capability review도 `PASS_GO`,
open findings 0개로 완료됐다. [공개 바인딩](../../workspace/public/src/device-action/bindings/s22plus_debian_autoboot_p452_review.json)은
검토자가 승인한 정확한 bytes이며, host 140개 및 runtime 158개 입력에 묶인다.

## 최종 H0 결과와 다음 실행 경계

실제 source-selected ARM64 VM의 정상·거부·관측 고장 37개 사례와 원본 전체
consumer 검증이 통과했다. 정상 사례는 initial/installed Debian PID1, 120초
서비스, 같은 부팅의 120.570초 간격 SSH 건강, 고정 shutdown 및 clean ext4를
증명한다. rcS 채널은 setup 14.431초, 종료 수신 16.001초로 34개 packet을 모두
증명했다. parent 기록은 2개, 관측 summary 예산은 22 ms였다. 이는 VM 증거이며
Samsung watchdog pet 또는 실기 성공을 증명하지 않는다.

두 channel fault 사례는 setup 실패와 packet gap을 실제로 일으켰다. 완전한
channel 증거는 거부되지만 120초 서비스·SSH·정상 종료는 유지된다. 나머지
실패 사례의 원본 기록과 disk/outside-native 상태도 독립 재검증했다. 별도 task
경계 6개 및 P452를 포함하는 두 retention consumer routing 검사 4개가 통과했다.

원본 packager의 boot/AP A/B가 일치한다. boot-only AP는 38,010,921 bytes이며
actual kernel/header/signature/CPIO 및 전체 qualification이 통과했다. 새 후보는
기존 autoboot 경로와 같이 artifact에서 identity를 유도하며 native research
catalog를 수정하지 않는다.

기존 `prepare_offline`으로 `READY_H0_PRELIVE_ONLY` 제안서를 생성하고 source
snapshot을 보존했다. 이는 fresh connected health 또는 native_data admission
증거가 아니다. 정확한 1-operation/3600-second attended 반환 승인 뒤에만
기존 `open_grant`가 source/task/recovery와 host census를 검사하고, 원래
`execute`가 첫 mode-changing intent 전에 live lane과 fresh Android health를
검사한다. agent의 `NoNewPrivs=1` 때문에 검토된 실행 진입점은 일반 사용자
터미널에서 실행한다. 호스트 보안 설정이나 원래 검사는 변경하지 않는다.
현재 grant·operation·image transfer는 없으며, A90·S20+는 건드리지 않았다.

private evidence base:
`workspace/private/outputs/s22plus-autoboot-rcs-p452-h0-20261021-1/`.
실패한 fixture 준비와 거부된 projection도 원본으로 보존한다. 현재 새 기기 효과는
0이며 기존 F1 승인·소비·복구 상태를 변경하지 않았다.
