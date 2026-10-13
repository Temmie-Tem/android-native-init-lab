# S22+ Debian 부팅 진행 상태와 실패 원인 종합

기준일은 2026년 10월 13일 KST이며 대상은 `SM-S906N/g0q/S906NKSS7FYG8`이다.
이 분석은 기존 실행 기록, 그 실행에 묶인 소스와 바이너리, 호스트 재현,
원문 기술 자료를 대조한 H0 작업이다. 새 기기 동작이나 실행 승인을 만들지 않았다.

**Debian이 이 기기에서 PID1로 실행될 수 있는지는 이미 해결했다. 아직 해결하지
못한 것은 실제 기기에서 서비스 시작과 네트워크 접속을 끝까지 이어 가는 것이다.**
P410과 P413은 설치된 Debian init의 실행을 증명했고, P413은 rcS 진입까지 증명했다.
이후 선택한 Debian 초기 부팅 경로는 하드웨어 준비를 다시 이식하는 별도 경로다.
이 새 경로의 실패가 앞선 설치된 PID1 증거를 지우지는 않는다.

가장 구체적인 새 발견은 **잘못된 로거 바인딩 이름을 검사하는 코드가 P418,
P423, P424에 공통으로 들어갔다는 것**이다. 실제 P418·P424 로그에는 `8.…`가
있는데 코드는 `soc:…`를 기대한다. 실제 보존 함수를 사용한 호스트·ARM64
12개 반례가 이 조건만으로도 정상 가정의 장치를 거부함을 재현했다. 다만
P419는 이 검사를 제거하고도 실패했으므로 모든 실패의 단일 원인은 아니다.

## 목표와 두 부팅 경로의 구분

목표는 전용 저장소의 Debian이 실제 호스트 PID1, 서비스, 장치, 네트워크,
로그와 종료를 소유하며 SSH와 보통의 패키지 서비스를 제공하는 것이다.
Android는 별도로 부팅하는 관리·복구 환경이다. chroot나 살아 있는 native
감독 프로세스 아래의 Debian 자식은 이 목표를 충족하지 않는다.

| 경로 | 부팅 순서 | 지금까지의 실기기 증거 |
| --- | --- | --- |
| P410·P413의 native 준비 후 인계 | FYG8 커널 → native 준비 → 기존 사용자 프로세스 정리 → root 전환 → 설치된 Debian init | 설치된 PID1, 동일 커널 부팅, 정확한 root와 실행 파일, P413 rcS 진입 |
| P417 이후의 Debian 초기 부팅 | FYG8 커널 → Debian initramfs의 shell PID1 → 고정 하드웨어 준비 헬퍼 → 이후 설치된 init으로 전환할 설계 | P418의 일부 초기 실행 기록만 확보; 완전한 준비·인계는 미증명 |

Debian이 처음부터 소유하는 방향은 유지할 수 있다. C로 된 짧은 장치 준비
헬퍼나 기존 vendor 커널 모듈을 쓰는 것은 이 방향과 모순되지 않는다. 제거할
대상은 독립적으로 남는 native PID1·서비스 관리 체계이며, 필요한 커널 지원과
일시적인 준비 코드를 언어 때문에 다시 만들 필요는 없다. 기존 native 경로는
하드웨어 준비의 검증된 비교 기준으로 활용한다.
[목표의 소유권 정의](../../GOAL.md),
[Debian 초기 부팅 설계](S22PLUS_DEBIAN_OWNED_EARLY_BOOT_FEASIBILITY_H0_2026-10-07.md).

## 이미 증명된 부분과 아직 남은 부분

여기서 실기기 성공은 해당 실행의 성공이다. 여러 실행이나 VM의 결과를 합쳐
한 번의 완전한 Debian 부팅에 성공했다고 판정하지 않는다.

| 기능 | 실제 S22+ 증거 | H0 또는 VM 증거 | 현재 판단 |
| --- | --- | --- | --- |
| FYG8 커널과 기존 native 준비 | 여러 종료된 실행에서 USB·UFS·정확한 Android 복귀 확인 | 고정 소스·모듈·아카이브 검증 | 재사용할 기반 |
| 전용 저장소와 ext4 | Android 32 GiB와 native 약 191.46 GiB; 초기화와 새 부팅 후 witness 확인 | GPT·filesystem 소비자 검증 | 설치 기반은 확보 |
| 설치된 Debian root | P402의 설치 상태, P420의 checker 및 8969개 항목 일치 | 서명된 129개 패키지와 재현 가능한 rootfs | 재설치가 현재 해결책은 아님 |
| ARM64 Debian 사용자 프로그램 | P403 고정 설치 사용자 공간 작업 성공 | 동적 loader와 라이브러리, 명령 실행 | 일반적인 ABI 불가능 가설과 맞지 않음 |
| 실제 PID1 root 전환 | P409 RAM witness, P410·P413 설치된 init | 정상·거부 경로 검증 | 전환 가능성은 해결 |
| 기존 native 사용자 공간의 종료 | P413 인계 시 다른 사용자 공간과 상속 ACM/state fd 부재 확인 | 정리와 fd 거부 사례 | 그 인계 경계에서 증명 |
| rcS·runlevel·서비스 | P413 rcS **진입**만 확인 | rcS/rc2, init·cron·sshd 실행과 종료 성공 | 기기상의 완료·안정성은 미증명 |
| Debian NCM와 SSH | 같은 부팅의 NCM·인증 SSH 성공 없음 | 가상 네트워크의 SSH 성공 | 핵심 미완료 기능 |
| 패키지·보통 서비스·재부팅 후 지속성 | 통합 실기기 증거 없음 | apt 추가 패키지, cron, 서비스 재시작, 정상 reboot와 데이터 유지 | 기기로 이식·통합해야 함 |
| Debian shell이 소유하는 초기 준비 | P417·P419 USB 증거 없음; P418 일부 기록 | 실제 Debian `/init`, vendor+Debian 아카이브, 준비·인계 VM 성공 | 하드웨어 준비의 이식이 미완료 |
| 복귀 후 초기 기록 보존 | P418 기록 두 개, P424 PRE 한 개 인증 | 생산자·해석기와 오류 경로 | 제한된 보존 경로 확보, 완전한 단계 기록은 미완료 |
| 실패 후 Android 복구 | 열거한 실행들은 정상 Android 종료 기록 보유 | 일회성 복구·읽기 재관측 검사 | 물리 복구 확인이며 자동 복구 증명은 아님 |

근거는 [rootfs와 VM 생명주기](S22PLUS_DEBIAN_BOOTSTRAP_H0_2026-09-21.md),
[P403을 포함한 이전 목표 기록](../archive/roadmaps/GOAL_THROUGH_P410_CLOSED_2026-10-01.md),
[P409](S22PLUS_SWITCH_ROOT_P409_FIRST_RUN_2026-09-30.md),
[P413](S22PLUS_DEBIAN_HANDOFF_P413_FIRST_RUN_2026-10-03.md),
[P420](S22PLUS_NATIVE_DATA_P420_RUN_2026-10-13.md),
[Debian 초기 PID1 VM](S22PLUS_DEBIAN_OWNED_EARLY_BOOT_H0_2026-10-07.md)이다.

## 실험이 늘어난 과정

현재 소비 대장의 정확한 S22+ 후보 항목은 102개다. 이 중 첫 Debian 후보인
P401부터 P424까지는 **22개**, P417부터는 **8개**다. P414·P416 등 H0 작업의
번호까지 실기기 횟수로 세면 안 된다. 이 수치는 소비된 후보 수이며, 복구
전송·재사용 baseline 설치·읽기를 합친 전 프로젝트의 총 기기 동작 수가 아니다.

| 구간 | 알아낸 것 | 남은 한계 |
| --- | --- | --- |
| P401–P403 | root 설치 상태와 설치 사용자 공간을 확인 | 완전한 부팅은 아님 |
| P404–P408 | 호스트 NCM 선택 오류 수정, 보호된 root와 준비 작업 확인 | 초기 무관측 실패와 하드웨어 USB는 별개 |
| P409–P410 | 실제 root 전환과 설치된 PID1 확인 | 서비스·접속 실패, 두 번째 gadget 결함 발견 |
| P411–P413 | dirty root를 거부·복구한 뒤 설치된 PID1와 rcS 진입 재확인 | 실제 USB 단절 이후 상태 불명 |
| P414 H0 | close/reopen 경계와 자식 상태 관측 구현·검증 | 완전한 실기기 후보나 실제 수리는 아님 |
| P417–P419 | Debian 초기 준비로 방향 전환, 일부 보존 기록 확보 | USB가 없을 때 준비 실패와 관측 실패를 분리하지 못함 |
| P420–P422 | root 정합성 복구, 파일 기록 시도, 별도 읽기 | 목표 파일이 없어 초기 실행의 정지 위치 불명 |
| P423–P424 | 로거만 축소한 시도 후, 검증된 native 환경에서 PRE 보존과 모듈 호출 반환 확인 | 바인딩 검사 결함과 새로운 cold 준비 경로의 미검증 부분 |

핵심적인 통합 진전은 P413의 rcS 진입까지이며, 그 뒤에는 관측 수단과 초기
준비를 다시 만드는 작업의 비중이 커졌다. 복구 성공과 H0 테스트 수가 많아져도
서비스·SSH의 완료 증거가 늘어나는 것은 아니다.

## 확인된 결함과 미확정 원인

### 로거 바인딩 이름의 불일치

P418의 `usb-first-prepare.c`, P423의 `stage-probe.c`, P424의
`s22plus_native_log_calibration_v1.c`는 다음 링크를 요구한다.

`/sys/bus/platform/drivers/samsung,kernel_log_buf/soc:samsung,kernel_log_buf`

P418과 P424의 보존 로그는 같은 드라이버가 `8.samsung,kernel_log_buf` 장치를
probe하는 것으로 기록한다. 보존된 g0q DT 소스의 `reg`와 커널의 장치 이름
생성 방식도 주소가 앞에 붙는 이름과 부합한다. DT 소스만으로 런타임 sysfs를
대신하지 않았으며, 기기 로그와 실제 소비자 코드를 별도로 확인했다.

각 소비된 이미지의 runtime 소스 핀, frozen 함수, 실제 helper 안의 경로
문자열을 연결했다. 그 함수 본문을 그대로 사용하고 lstat·대기만 대체한
fixture에서 모듈 디렉터리와 proc 노드는 정상으로 가정했다. 드라이버 링크가
관측된 `8.…`뿐이면 세 함수 모두 `ENODEV`를 반환하고, 기대한 `soc:…`이면
모두 성공한다. 호스트와 ARM64 각각 두 조건, 총 12개 사례가 통과했다.

이것은 **정상 가정에서도 실패할 수 있는 검사 결함**의 재현이다. 실제 세
부팅에서 어느 predicate가 실패했는지나 probe가 완결됐는지까지 재현한 것은
아니다. P424는 합성 바인딩 조건의 `ENODEV`만 보고했고 개별 조건을 남기지 않았다.

P418에서는 이 확인이 첫 `sec_log_buf` 삽입 직후, `MODULE_DONE`과 나머지
platform 모듈보다 앞에 있다. 따라서 이 실패만으로 후속 준비와 USB가 막힐 수
있다. P418에서 첫 BEGIN 뒤의 기록이 없다는 사실과 부합하지만, 물리 실행의
유일한 원인으로 확정하지 않는다. P423에도 같은 결함이 있지만, 기록이 전혀
없는 P423을 이 검사 지점까지 도달했다고 판정할 근거는 없다.

이 단서는 P418의 기존 raw에 이미 있었다. P424 전에 기존 로그와 새 고정
경로를 대조했어야 했다. 장치 이름만 `8.…`로 전역 치환하기보다 정확한 대상
장치·driver 연결을 검증하고, 모듈 존재·링크·proc 노드의 실패를 구분해야 한다.
[P418](S22PLUS_DEBIAN_USB_FIRST_P418_RUN_2026-10-09.md),
[P424](S22PLUS_NATIVE_LOG_CALIBRATION_P424_RUN_2026-10-13.md),
[Linux 5.10 sysfs 규칙](https://docs.kernel.org/5.10/admin-guide/sysfs-rules.html).

### 모듈 호출 성공과 장치 준비 성공은 다르다

P424에서 `finit_module`은 0을 반환했고 PRE는 현재 커널 링과 복귀 후 로그에서
확인됐다. 그렇다고 module·driver link·현재 `/proc/ap_klog`의 모든 조건이
성공한 것은 아니다. stock logger의 init은 platform driver 등록을 호출하며,
장치의 매칭·probe·자원 준비는 별도 단계다. 따라서 호출 성공과 바인딩 확인
실패가 동시에 기록되는 것은 모순이 아니다.
[Linux 5.10 driver binding](https://docs.kernel.org/5.10/driver-api/driver-model/binding.html).

P424의 POST는 바인딩 거부 때문에 생성되지 않았다. POST가 복귀 과정에서
사라졌다고 해석하면 안 된다. PRE 한 개의 실제 보존은 유효한 진전이지만,
완전한 두 표식 교정이나 Debian 초기 PID1 실행의 증거는 아니다.

### P410의 두 번째 USB gadget 결함

P410의 정확한 커널 Image에는 Android configfs 코드가 첫 gadget의 전역
포인터를 계속 사용하는 동작이 있었다. 첫 `g1`을 unbind한 뒤 두 번째 gadget을
만들어 NCM을 붙이는 설계에서는 setup이 첫 객체의 unbind 상태에 막힌다.
기계어 확인과 실제 함수 재현으로 확인한 결함이며, 첫 `g1`을 유지·재구성하는
수정이 이후 V2 경로에 반영됐다.

이는 P410에서 의도한 NCM 설계가 작동할 수 없는 이유를 설명한다. 다만 실제
P410이 해당 서비스까지 도달했는지나 이후 native 재등장의 원인까지 설명하지
않는다. **P413은 USB release와 NCM 전환 전에 관측이 끊겼으므로 같은 결함을
그대로 P413 원인으로 재사용할 수 없다.**
[P410의 정확한 Image 분석](S22PLUS_DEBIAN_HANDOFF_P410_FIRST_RUN_2026-09-30.md),
[Linux 5.10 gadget 설정](https://docs.kernel.org/5.10/usb/gadget_configfs.html).

### P413은 호스트 파서 오류만으로 설명되지 않는다

P413은 설치된 init, 같은 부팅·root, START와 rcS 진입 기록을 남긴 뒤 EOF가
발생했다. 같은 사건에 호스트 USB core의 실제 장치 disconnect가 있고, 약
24.43초 뒤 물리 복구 요청보다 먼저 같은 USB 식별자가 재등장했다. USB 제거가
CDC ACM hangup, read 0과 ioctl EIO로 이어지는 인과관계는 확인됐다.

하지만 단절을 일으킨 원인은 아직 모른다. 커널 부팅 ID가 달라졌는지 확보하지
못했으므로 전체 재부팅과 같은 부팅의 UDC·PHY 재설정을 구분할 수 없다. P413은
첫 gadget을 아직 유지하는 단계였으므로 같은 USB 식별자의 재등장만으로
native 사용자 공간이 다시 실행됐다고 주장할 수도 없다.

기존 분석은 단순 idle/VMIN, CLOCAL 누락, 호스트의 조기 fd close, 미지원
`close_range`, native 사용자 프로세스 종료로 watchdog petting이 사라졌다는
설명을 반박했다. 선택된 watchdog은 커널 스레드가 pet한다. 다만 커널 정지,
UDC·PHY·Type-C 문제, 예외적인 PM/링크 문제는 원인으로 확정되거나 완전히
배제되지 않았다. 시간 간격이 watchdog·RCU 숫자와 비슷하다는 이유만으로
원인을 정하지 않는다.
[P413 인과 분석](S22PLUS_P413_CAUSAL_RESEARCH_H0_2026-10-03.md),
[Linux 5.10 USB PM](https://docs.kernel.org/5.10/driver-api/usb/power-management.html).

P414의 close/reopen·부모 관측 fd 유지·자식 wait 상태 기록은 이미 H0 구현과
ARM64 검증을 마쳤다. 새 관측 체계를 처음부터 만들 필요는 없다. 이 변경은
물리 USB를 고쳤다는 증거가 아니며 완전한 실기기 후보도 아니다.
[P414 구현과 한계](S22PLUS_DEBIAN_HANDOFF_P414_OBSERVER_H0_2026-10-03.md).

### 초기 부팅과 그 관측이 서로 의존했다

P417·P419의 RAM 기록은 USB가 성공해야 회수할 수 있었다. USB가 오지 않으면
초기 `/init`, 모듈, driver 준비, gadget 생성, 관측기 자체 중 어디서 실패했는지
남지 않는다. P421의 파일 기록은 73+8 모듈과 저장소 준비·root admission을
먼저 통과해야 시작된다. 그보다 앞선 실패를 파일로 설명할 수 없는 구조다.

P423은 로거만 남겼지만 최초 RAM 설정·target 확인·커널 링 쓰기·parent 측정이
로거 삽입보다 앞선다. 이 앞부분에서 실패하면 복귀 후 기록이 없을 수 있다.
P424는 먼저 입증된 native 실행 환경에서 생산자를 확인해 이 관측 문제의
일부를 분리했다. 다음에는 이 결과를 초기 경로에 활용해야 한다.

**P419는 로거 경로를 없앴는데도 USB가 나오지 않았다.** 따라서 로거 이름
수정이 필요하더라도 cold platform 준비와 gadget 관측 경로의 다른 차이는
여전히 남아 있다. 현 증거로 특정 모듈이나 firmware 실패를 지목할 수 없다.
[P419](S22PLUS_DEBIAN_USB_RAM_P419_RUN_2026-10-12.md),
[P421·P422](S22PLUS_DEBIAN_FILE_P422_RETRIEVAL_2026-10-13.md),
[P423](S22PLUS_DEBIAN_EARLY_STAGE_P423_RUN_2026-10-13.md).

## VM과 웹 자료가 답하는 범위

VM은 실제 ARM64 명령, Debian `/init`, vendor+Debian cpio 순서, shell hardlink,
loader, root 전환, 서비스·SSH, 프로토콜과 실패 처리를 실행했다. 이 부분은
유효한 검증이며 무의미한 성공이 아니다. 반면 Samsung module insertion,
driver binding, UFS 발견, UDC·PHY·Type-C, 전기적 USB, 보존 RAM의 실제 동작은
시험별로 대체했다. 이번 이름 결함을 포함해 그 대체 영역은 VM PASS로
증명되지 않는다. module CRC 3926개 일치는 링크 호환성이지 모든 probe의 완료가 아니다.
[FYG8 준비 검증](S22PLUS_DEBIAN_FYG8_PREPARATION_H0_2026-10-07.md).

현재 커널은 `DEVTMPFS`, `FHANDLE`, PID/user namespace와 SysV IPC가 꺼져 있고,
ext4, tmpfs, Unix98 PTY, configfs와 NCM은 들어 있다. 이는 이미 선택한
SysVinit·mdev와 tmpfs `/dev` 설계의 이유다. systemd v257의 요구사항에는
DEVTMPFS와 FHANDLE이 명시돼 있다. 지금 systemd나 다른 커널로 바꾸는 것은
입증된 부족분을 닫기보다 새로운 변수를 추가한다. PID namespace가 없다는
것은 실제 호스트 PID1 실행이 불가능하다는 뜻이 아니다.
[systemd v257 요구사항](https://github.com/systemd/systemd/blob/v257/README).

init이 실행됐다고 SysV의 sysinit·rcS·runlevel 작업까지 끝난 것은 아니다.
Debian의 정의에서도 이들은 별도 실행·대기 단계다. 이 때문에 P413의 설치된
PID1와 rcS 진입을 서비스 완료·SSH 성공으로 올릴 수 없다.
[Debian inittab](https://manpages.debian.org/trixie/sysvinit-core/inittab.5.en.html),
[Debian init](https://manpages.debian.org/trixie/sysvinit-core/init.8.en.html).

루트 전환은 이미 검증한 5.10용 `run-init`/`switch_root` 의미를 유지한다.
버전 없는 최신 kernel 문서에는 nullfs 기반의 다른 설명이 나타나므로 그대로
적용하면 안 된다. 이 작업의 기준은 5.10 문서와 실제 Image이다. 이미 성공한
root 전환을 새 `pivot_root` 실험으로 다시 열 이유가 없다.
[Linux 5.10 initramfs](https://docs.kernel.org/5.10/filesystems/ramfs-rootfs-initramfs.html),
[Debian initramfs 단계](https://manpages.debian.org/trixie/initramfs-tools-core/initramfs-tools.7.en.html).

## 지금 저장소 상태를 해석하는 방법

P415의 dirty 관측은 과거 사실이다. P420은 strict journal finalization 뒤
read-only checker와 8969개 root 항목 일치를 증명했다. P421의 파일 작업은
실행 위치가 불명확하고, 이후 P422는 `state=1/recover=0/orphan=0`인 clean
슈퍼블록과 목표 파일 부재를 확인했다. P423·P424는 native_data 작업을 선택하지 않았다.

현재 계획을 무조건 추가 복구·포맷·재설치부터 시작해서는 안 된다. 다음 실제
쓰기 전에 기존의 fresh protected root admission이 필요하며, 그것이 dirty나
불일치를 보일 때 해당 결과에 맞는 조치를 선택한다. P422의 clean 슈퍼블록은
전체 root 재검증이나 P421의 정상 unmount 증명으로 확대하지 않는다.
[P420](S22PLUS_NATIVE_DATA_P420_RUN_2026-10-13.md),
[P422](S22PLUS_DEBIAN_FILE_P422_RETRIEVAL_2026-10-13.md).

## 목표까지 남은 개발 경로

아래는 개발 우선순위이며 새 기기 권한이나 추가 안전 gate가 아니다.
소비된 후보는 그대로 종료 상태를 유지한다.

1. **H0에서 구체적인 잘못된 가정을 제거한다.** 로거의 장치 식별과 합성 오류를
   고치고 관측된 이름·부재·다른 driver·불완전 probe 조건을 시험한다. 기존
   native의 module 순서·매개변수·provider 확인·driver 대기·USB role·gadget
   설정을 Debian 초기 헬퍼의 실제 효과 순서와 대조한다. module 목록이 같다는
   것만으로 완전한 이식을 주장하지 않는다. 기존 P414 관측 코드는 필요한
   범위에서 재사용하고, 새로운 범용 observer나 native 감독자를 만들지 않는다.
2. **다음 후보의 기능 경로를 끝까지 연결한다.** Debian shell PID1 아래에서
   정확한 하드웨어 준비, 보호된 root admission, 설치된 SysVinit, rcS/rc2,
   Debian 소유 NCM와 SSH가 이어지는 하나의 설계를 만든다. USB 관측이 끊겨도
   시작 진행과 제한된 기기 내부 증거를 구분할 수 있게 한다. 저장소 사용 전의
   짧은 보존 기록과 admission 이후의 제한된 기록은 각자의 범위만 담당한다.
   초기부터 Debian이 gadget을 만들면 첫 객체를 유지하고, 이미 만들어진
   객체를 인수하는 구성이라면 검증된 same-g1 규칙을 지킨다.
3. **같은 부팅의 실제 기능으로 판정한다.** 초기 PID1와 설치된 init의 연결,
   정확한 root, old-root 사용자 공간 종료, rcS/rc2 완료, 필요한 서비스 liveness,
   NCM link와 pinned SSH 인증을 같은 부팅에서 확인한다. PRE·POST 교정이나
   부가 원인 분석은 이 기능 경로의 관측으로 포함할 수 있으며, 각각을 별도
   전체 실험의 성공 목표로 계속 분리할 필요는 없다. 새 효과·회복 의미가 있는
   통합은 그 정확한 범위로 검토·qualification한 뒤 유한한 실행 권한을 적용한다.
4. **접속이 확보된 뒤 사용성과 지속성을 검증한다.** 보통의 패키지 서비스,
   시작·정지·재시작, DNS·package access, 동기화된 데이터, 정상 Debian 종료와
   다음 Debian 부팅에서의 보존을 확인한다. 추가 패키지의 VM 성공은 기존
   immutable root의 모든 업데이트를 허용하는 제품 정책을 대신하지 않는다.

P410·P413의 경로를 재사용하는 빠른 기능 기준점과 Debian 초기 PID1 이식은
같은 과제로 위장하지 않는다. 이번 목표 방향은 후자이며, 전자의 성공한
하드웨어·인계 구현을 재사용할 수 있다. 초기부터 Debian이 소유하려는 요구를
조용히 포기하거나 독립 native 감독자를 남기는 설계로 바꾸지 않는다.

## 다음 결과가 달라질 때의 해석

| 다음 실행에서 확보한 마지막 증거 | 좁혀지는 작업 |
| --- | --- |
| 최초 표식도 없음 | `/init` 진입·초기 RAM 설정·기록 경로를 조사; Debian 서비스나 SSH를 원인으로 지목하지 않음 |
| module BEGIN과 반환·개별 binding 결과 | 정확한 모듈 또는 자원 준비 경계를 조사; 모든 준비를 다시 바꾸지 않음 |
| 준비 완료, root admission 거부 | 해당 root 조건을 해결; 무조건 포맷·재설치하지 않음 |
| 설치된 PID1, rcS 시작 뒤 USB 단절 | 기기 내부 단계와 P414 경계로 서비스 상태를 분리; 단절을 즉시 재부팅이라고 부르지 않음 |
| rcS/rc2·서비스 생존, NCM 없음 | gadget 객체·role·UDC·host interface에 집중 |
| NCM 정상, SSH 인증 실패 | 주소·계정·키·sshd 설정에 집중 |

각 후보는 이전 실패의 다른 가능한 원인을 실제로 구분하거나 남은 기능을
전진시켜야 한다. 단순 timeout을 같은 의미로 또 얻는 변경은 유용한 실험
설계가 아니다. 반대로 모든 과거 원인을 완벽히 밝혀야만 독립적으로 안전한
서비스 진전을 허용한다는 전제도 필요하지 않다. 남은 횟수는 보장할 수 없지만,
이미 증명한 기반과 추가 관측 자체를 계속 재실험하는 방식은 줄일 수 있다.

## 분석 근거와 보존

10개 주요 종료 작업의 task·grant·operation·terminal 연결과 N/A 1회씩의
기록을 H0로 확인했다. 소비 대장의 체인을 검증했고, P418·P424 raw 수집
receipt에서 로거 장치 이름을 다시 읽었다. P418·P423·P424의 이미지에 묶인
세 검사 함수와 helper를 확인해 12개 호스트·ARM64 반례를 실행했다. 이 반례의
sysfs는 fixture이며 실제 probe 성공을 주장하지 않는다. 기존 실행 기록은
바뀌지 않았고 기기 연결 명령은 없었다.

Exa 검색은 9개 질의의 45개 결과를 검토했고, 버전이 지정된 kernel·Debian·
systemd 원문 9페이지를 별도로 읽었다. 다른 Samsung 세대의 logger 구현,
최신 kernel의 바뀐 rootfs 의미, 일반적인 USB 장애 글은 이 기기의 원인 증거로
채택하지 않았다. 원문은 메커니즘의 근거이고 실제 기기 판정은 보존된 실행에 둔다.

Private evidence는
`workspace/private/outputs/s22plus-debian-state-synthesis-h0-20261013-1/`에 있다.
`binding_reproduction.py`, 각 `binding-p*/`, `binding-reproduction-result.json`,
`summarize_evidence.py`, `evidence-summary.json`과 `web-*.json`이 재현과 출처를
보존한다. 작업 시작 기준 커밋은 `d71d91e7a0520977b297c388a4202bef714b0680`이다.

| 근거 기록 | SHA-256 |
| --- | --- |
| 세 바인딩 검사 반례 결과 | `ce72aa4fdec1b371d9d0422abd4bd069bc586ff5dbb2b9989bbdfc6e10378013` |
| 종료 작업과 연구 근거 연결 | `8bc46346294f018e4dfa469e933541aef6e1d316fc040b1a7fe4d1be55648074` |

이 정리는 실행 기능을 바꾸거나 새 후보를 준비하지 않았다. 다음 H0 구현의
대상과 실기기에서 반드시 얻어야 할 기능 증거를 명확히 한 결과다.
