# P437 실기기 부팅 요구사항 대조: 첫 watchdog 갱신과 자동 재부팅

2026-10-19 KST. 대상은 `SM-S906N/g0q/S906NKSS7FYG8`만이다.
이 작업은 보존 자료·현재 코드·실제 설치 파일·외부 원자료를 대조한 H0 조사다.
새 장치 명령, 부팅, 이미지 빌드, 승인, 정책 변경은 수행하지 않았다.

## 결론과 변경된 우선순위

**P437의 첫 실험 부팅은 약 12.74초에 Qualcomm watchdog bark/bite를 기록하고
warm reset으로 이어졌다.** 이후 같은 후보의 두 번째 커널 부팅이 별도의
인증된 boot identity로 구분된다. 호스트 N 전송은 여전히 한 번이다.
첫 부팅에서 설치된 Debian PID1과 rcS fork/exec 시도/첫 wait·sleep까지
인증됐다는 [기존 결과](S22PLUS_P437_RCS_OBSERVATION_RUN_2026-10-19.md)는 유효하다.
watchdog를 갱신하지 못한 근본 원인과 rcS의 실제 완료 여부는 아직 모른다.

이 발견은 마지막 단계 표식만으로 원인을 좁힌 이전 분석보다 강한
실기기 실패 근거다. 기존 `NO_PROOF / ANDROID_CLOSED_HEALTHY` 터미널과
소비된 journal·승인·후보를 변경하지 않는다. Android 복구 완료는 유효하지만,
두 번째 후보 부팅의 파일 쓰기 여부나 안전한 거부, native_data의 현재
일관성까지 증명하지 않는다.

다음 작업의 우선순위는 **첫 watchdog 갱신의 timer → kernel thread →
CPU 응답 확인 → hypervisor pet 경계를 구분하는 최소 관측**이다.
Debian 패키지 추가, rcS 순서 변경, watchdog 비활성화, RT 예산 변경을
정당화하는 결함은 이번 조사에서 발견하지 못했다.

## 원시 자료에서 새로 확인한 부팅 구간

기존 같은-returned-boot D0의 원시 파일과 receipt를 다시 해시 검증했다.
소비된 소스의 실제 decoder와 key/domain을 사용하여 각 연속 커널 구간을
따로 해석했다. 서로 다른 부팅의 레코드를 합쳐 하나의 실행으로 만들지 않았다.

| 구간 | 인증된 관측 | 해석의 한계 |
| --- | --- | --- |
| 첫 후보 부팅 | 초기 준비 158개, 진단 4개, transition 132개; 설치된 PID1 및 rcS 초기 경계 | 아래 watchdog 문장은 주변 커널 로그이며 개별 MAC 인증 레코드는 아니다. 동일 원시 구간과 reset 순서로 연결한다. |
| 두 번째 후보 부팅 | 다른 boot identity; 초기 준비 156개와 helper START 진단 1개 | 마지막 인증된 준비 단계는 UFS 모듈 BEGIN이다. 나머지 표식 일부는 오래된 Android 문자열에 덮여 인증되지 않는다. 쓰기·완료·안전한 거부를 추론하지 않는다. |

첫 후보 부팅의 구체적 순서는 다음과 같다. 커널 메시지는 보존 로그의
관측이며, 메시지 시각을 호스트 grant 시각과 직접 빼서 지연을 계산하지 않는다.

| 해당 부팅의 시각 | 관측 |
| --- | --- |
| 약 0.739초 | watchdog 초기화 시 마지막 pet 시각; 나중의 bark가 이 값을 보고함 |
| 약 6.145초 | 설치된 Debian PID1 확인 완료 |
| 약 6.173초 | rcS 자식의 exec 시도 |
| 약 6.185초 | 부모의 첫 10ms sleep 정상 반환 |
| 약 11.988초 | CPU 7의 `gh-watchdog` 문맥에서 RT throttling 경고 |
| 약 12.739초 | watchdog bark, 초기화 이후 갱신되지 않은 last-pet 값, CPU alive mask 0, bite 요청과 만료 상태 |
| 그 뒤 | warm-reset bootloader 출력, 이어서 다른 인증된 후보 boot identity |

부모의 첫 heartbeat는 fork 기록 뒤부터 10초가 지나야 하므로 약 16.175초에
도달할 예정이었다. **관측된 reset은 그보다 약 3.44초 빠르다.** 따라서 첫
heartbeat와 300초 STOP이 없는 것을 별도 부모 고장으로 해석할 필요가 없다.
관측된 actor의 순번·기록 비용도 96개/2,000ms 한도에 도달하지 않았다.

조사 중 잠정적으로 언급한 약 317초까지의 thermal/workqueue 메시지는
**두 번째 후보 부팅**에 속한다. 이를 첫 rcS 부팅의 생존 증거로 사용하지 않는다.
오래된 Android 로그가 섞여 있다는 사실 때문에 전체 raw를 하나의 시간축으로
정렬하거나, 마지막 커널 timestamp만으로 실험 수명을 판단해서도 안 된다.

## 정확한 watchdog 구현과 가능한 원인

P437에 포함된 `qcom_wdt_core.ko`와 `gh_virt_wdt.ko`는
[P413 당시 분석](S22PLUS_P413_CAUSAL_RESEARCH_H0_2026-10-03.md)에 사용한
모듈과 바이트 단위로 같다. 따라서 그 모듈의 disassembly와 보존된 Samsung
소스 분석을 재사용했다. P413과 P437의 전체 kernel Image는 다르므로,
모듈의 동일성을 전체 커널·실행 상태의 동일성으로 확대하지 않았다.

선택된 구현은 Android daemon이 아니라 kernel thread가 watchdog를 갱신한다.
thread는 `SCHED_FIFO` 우선순위 99를 설정하고, timer가 깨운 뒤 온라인 CPU의
응답을 동기식 `smp_call_function_single(..., wait=1)`로 확인한 다음,
hypervisor pet과 last-pet 갱신을 수행한다. 사용자 공간 pet은 기본적으로
비활성이다. 선택된 module의 pet 주기는 9,360ms다.

초기 last-pet 시각에 이 주기를 적용하면 첫 갱신 예정 구간은 약 10.10초다.
따라서 last-pet이 초기 값이라는 사실만으로 Debian 인계 전부터 정지했다고
말할 수 없다. 갱신 실패가 드러난 시점은 인계 이후이며, 정확한 시작점은 미상이다.

[Linux 5.10의 동기 IPI 구현](https://github.com/torvalds/linux/blob/v5.10/kernel/smp.c)과
[RT scheduler 구현](https://github.com/torvalds/linux/blob/v5.10/kernel/sched/rt.c)은
해석에 필요한 반례를 제공한다. 다른 CPU의 callback 완료를 기다리는 thread가
CPU를 소비할 수 있으므로, `gh-watchdog` 문맥의 RT 경고만으로 별도의 Debian
프로세스가 RT 예산을 소진했다고 단정할 수 없다. 경고는 현재 실행 문맥이며
전체 원인 추적 기록이 아니다. 주기적인 RT 예산 보충과 interrupt 문맥의 응답도
있으므로, 경고 한 줄이 갱신 실패의 모든 시간을 설명하지 않는다.

CPU alive mask 0도 초기 상태와 새 ping round에서 모두 가능하다. 이 값만으로
어느 CPU가 응답하지 않았는지, timer가 언제 발화했는지, thread가 어느 함수에서
기다렸는지 결정할 수 없다. **CPU 응답 대기, timer/thread 지연, hypervisor pet
경로는 구분할 후보이며, 특정 원인으로 확정되지 않았다.**

watchdog를 끄거나 RT budget을 무제한으로 바꾸면 실패 표식을 없애거나
FIFO 대기를 더 길게 만들 수 있다. 현재 관측은 그런 변경의 근거가 아니다.

## 실제 Debian 시작 경로: 요구사항과 충족 상태

P437의 immutable-root 기준인 보존 P401 tar를 다시 해시 검증하고 필요한
파일만 읽었다. 설치된 버전은 SysVinit/sysv-rc/initscripts 3.14-4,
dash 0.5.12-12, BusyBox-static 1.37.0-6+b9, libc6 2.41-12+deb13u4다.
설치된 `/bin/sh`는 초기 initramfs의 BusyBox shell과 달리 dash다.

| 필요한 조건 또는 가설 | 실제 선택된 경로와 근거 | 현재 판단 |
| --- | --- | --- |
| root·init·인터프리터·loader | exact-root admission 뒤 설치된 init 실행; dash와 같은 dynamic loader/libc가 존재하며 정상 VM 파일과 동일 | 누락 결함이 발견되지 않음. 실제 rcS exec 완료는 별도 미증명 |
| proc/sys/dev/run·devpts·shm·ptmx | witness가 순서대로 준비·검사한 뒤 설치된 init을 실행 | 설치된 PID1 증거 이전에 통과한 조건; 추가 마운트 제안 불필요 |
| rcS 실행 순서 | rcS → `rc S`; `.legacy-bootordering`이 `CONCURRENCY=none`을 선택 | 순차 실행. 설치된 startpar와 `.depend.boot`는 이 경로에서 실행되지 않음 |
| udev·devtmpfs 요구 | 실제 udev init script는 daemon 부재 검사에서 종료; mdev가 선택된 장치 관리자 | udev의 devtmpfs 경로를 현재 실패 원인으로 삼을 근거 없음 |
| mdev 초기 스캔 | background `mdev -df`가 sysfs를 스캔할 수 있으며 뒤의 순차 script와 겹칠 수 있음 | 실기기와 VM의 실제 차이. 실행·원인 여부는 미증명 |
| kernel module·sysctl 추가 변경 | kmod의 활성 목록 없음; procps의 활성 설정은 core_pattern과 pid_max | rcS의 직접 RT budget/우선순위 변경이 발견되지 않음 |
| 콘솔과 표준 출력 | 초기 자동 owner는 null stdio; SysVinit은 console 실패 시 null fallback; rc의 stty 실패는 비치명적 | VM의 ttyAMA0와 관측 차이. 일반 script stderr가 printk에 남는다고 기대하지 않음 |

실제 rcS 링크는 hostname/mountkernfs → udev → mdev/mountdevsubfs → kmod →
configfs/mountall → bootclean → brightness/procps/urandom → networking →
mountnfs/bootclean → bootmisc 순이다. checkroot/checkfs/hwclock는 패키지 파일로
존재하지만 선택된 rcS 링크에는 없다. 파일 이름이나 dependency 파일의 항목만으로
그 코드가 실행됐다고 판단하지 않았다.

[Debian inittab](https://manpages.debian.org/trixie/sysvinit-core/inittab.5.en.html)과
[startpar 문서](https://manpages.debian.org/trixie/startpar/startpar.1.en.html)는
일반 동작을 설명한다. 이번에는 실제 선택 분기를 확인하여 startpar 관련
가설의 적용성을 제외했다. 이 결과는 이전의 “startpar를 사용할 수 있다”는
가능성 수준의 설명을 구체화한다.

## 과거 실기기와 VM에서 재사용할 근거

| 비교 대상 | 재사용할 사실 | 이번에 확대하지 않은 주장 |
| --- | --- | --- |
| [P430/P431](S22PLUS_DEBIAN_P430_P431_PERSISTED_EARLY_PID1_RUN_2026-10-16.md) | 같은 watchdog/logger 모듈과 빈 module 인자로 준비·파일 작업 후 park; 해당 후보 구간의 커널 출력이 약 368.889초까지 이어지고 bark/RT 경고를 찾지 못함 | 모든 미래 부팅의 watchdog 정상 보장 또는 차이를 rcS 하나로 특정 |
| [P410](S22PLUS_DEBIAN_HANDOFF_P410_FIRST_RUN_2026-09-30.md) | exact Image의 첫 gadget 객체 제약을 발견하여 후속 설계에 반영 | P437의 rcS 이전 USB 부재를 같은 결함으로 진단 |
| [P413](S22PLUS_P413_CAUSAL_RESEARCH_H0_2026-10-03.md) | kernel watchdog 소유자와 동기 CPU ping, 실제 USB disconnect 분석 | P437의 watchdog 발견을 당시의 미확인 재시작 원인으로 소급 확정 |
| [P319](S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md) | 순정 firmware의 module 인자·gadget 구성 순서를 실제 분기와 대조하는 방법 | 순정 Android service 전체가 Debian에 필요하다는 주장 |
| 기존 P437 ARM64 VM | 같은 rcS/rc/legacy marker/mdev/dash/loader/libc 7개 파일 일치; rcS·120초 서비스·SSH 성공 | Samsung watchdog, CPU wakeup/IRQ, 실제 sysfs·USB·UFS 동작의 성공 |

실제 target Image와 보존 VM Image의 embedded config를 각각 추출해 저장된
config와 일치함을 확인했다. 둘 다 DEVTMPFS/FHANDLE/SYSVIPC/PID·user namespace가
없고 UNIX98 PTY와 SELinux를 포함한다. 따라서 이 일반적인 기능 부재 자체로
기존 정상 VM과 실기기의 차이를 설명할 수 없다. 실제 watchdog·firmware loader·
IRQ/CPU-PM 환경과 virtual hardware 대체는 별도 차이다.

[Android vendor-module 지침](https://source.android.com/docs/core/architecture/kernel/vendor-module-guidelines)은
module 등록과 실제 probe/binding, firmware 준비를 구분한다. 외부의 실제
[Snapdragon S22 초기 지원 패치](https://lkml.rescloud.iu.edu/2508.3/05455.html)는
SM-S901E/r0q의 SimpleFB·USB 사례다. 정확한 g0q/FYG8 Debian 서비스 증거로
사용하지 않았다. Exynos g0s 자료 역시 target이 달라 직접 적용하지 않았다.

## 선택한 다음 최소 단위와 종료 기준

다음 개발 단위는 **첫 watchdog 갱신 전후의 제한된 kernel-thread/CPU 응답
관측을 기존 부팅 경로에 결합하는 설계와 H0 검증**으로 한정하는 것이 타당하다.

1. 실제 FYG8의 timer wakeup, FIFO thread, 동기 CPU ping, pet 반환 경계를
   기준으로 기존 proc/sysfs·보존 진단이 제공하는 정보를 대응시킨다. 내부 상태를
   읽을 수 없는 부분은 그대로 미확인으로 남기며, 일반 Linux source를 실제
   crash stack으로 대체하지 않는다.
2. P430의 준비 후 park와 P437의 이후 root admission/transition/installed-init
   경로 사이에서 필요한 관측만 고른다. 약 10초의 첫 갱신과 12.74초 reset보다
   늦은 heartbeat를 더 기다리는 설계는 피한다. 별도 상주 관리자를 만들지 않는다.
3. 결과가 timer/thread 미진입, CPU 응답 대기, pet 경로 오류 중 무엇을 구분하는지
   먼저 정하고, 그 소비자와 실패 처리를 H0에서 검증한다. 기존 정상 VM과
   41-case 증거는 관련 입력이 같으면 재사용한다. 대상 하드웨어를 모사하지 않는
   VM 반복만으로 watchdog 문제를 닫지 않는다.

현재 native_data 파일을 읽으면 첫 부팅의 rcS·서비스 진행을 더 얻을 수 있지만,
이미 확인된 watchdog reset의 이유는 파일 읽기만으로 결정되지 않는다.
dirty home-block에서 파일이 보이지 않는 경우도 비실행 증거가 아니다.
따라서 추가 reader·journal replay를 이번 조사에 붙이지 않았으며, 향후 reader는
기존 고정 프로필과 별도의 현재 바인딩으로 다뤄야 한다.

완료 기준은 원인 전체의 완벽한 규명이 아니라 **첫 갱신 실패의 어느 경계를
다음 최소 시험으로 구분할지와 그 판정 한계를 정하는 것**이다. 이번 H0 조사는
그 우선순위를 정했으며, 새 부팅 후보나 실행 승인을 준비한 것은 아니다.

## 검증·자료 위치

Private bundle:
`workspace/private/outputs/s22plus-p437-boot-requirements-h0-20261019-1/`.

- `entry/`: exact rootfs/startup 경로, 7개 실제 VM root 파일 비교, 요구조건 판정.
- `retention/`: 원본 receipt, offset·hash를 가진 watchdog 구간, 부팅별 실제
  decoder 재실행과 P430 비교. 인증 boot/run 값과 raw kernel 출력은 private 유지.
- `external/`: 외부 원자료, 버전·target·적용성·제외 근거와 검색 기록.
- `synthesis/`: 146개 소비된 runtime source의 frozen/current 일치, 실제 boot
  payload kernel과 inventory의 일치, 두 Image의 embedded config, watchdog
  module 동일성, 기존 41개 VM case의 참조 무결성 검사.

변경한 private Python은 py_compile 및 실제 read-only 실행으로 확인했다.
공개 변경은 이 보고서와 GOAL의 현재 상태 및 기존 실행 보고서의 후속 분석 링크다.
기존 장치 기록·산출물과 사전 존재한 46개 dirty/untracked 경로는 보존한다.
A90/S20+에는 명령이나 변경을 수행하지 않았다.
