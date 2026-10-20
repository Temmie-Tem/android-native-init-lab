# S22+ P441 watchdog 후속 분석: 관측의 의미와 남은 원인 분기

상태: **H0 분석 완료; 실패 원인 미확정**.
[P441 원본 실행](S22PLUS_AUTOBOOT_WATCHDOG_P441_RUN_2026-10-20.md)은
CONSUMED / ANDROID_CLOSED_HEALTHY이며 live access는 NO_PROOF다.
이번 작업은 이미 보존한 자료만 읽었다. 기기 명령, 새 빌드·전송, parser 변경,
소비된 결과 수정은 없다. A90와 S20+는 대상이 아니다.

목표는 P441이 추가한 증거로 가설을 최대한 구분하고, 적대적 반례까지 확인한 뒤
남은 질문에 필요한 정보를 명시하는 것이다. 현재 자료로 판별 가능한 후속
검사는 완료했다. 원인을 확정하거나 가능한 모든 커널 결함을 배제했다는 뜻은
아니다. Debian rcS 완료·서비스·SSH, clean shutdown과 현재 native_data 일관성은
여전히 증명되지 않았다.

## 1. 거부된 마지막 줄에는 완전한 인증 프레임이 있다

원본 strict decoder는 **141개 기록 / watchdog 관측 기록 9개 / malformed 1개**를
그대로 반환한다. 마지막 450-byte 후보의 앞 416 bytes는 원시 capture 안에
연속으로 존재하는 완전한 프레임이며, 뒤에 34 bytes의 다른 텍스트가 붙어 있다.
원시 바이트를 수정·추정·재조립하지 않고 그 연속 구간만 분리하면 원래 key,
run, boot, producer, actor, sequence로 MAC 검증과 기존 decoder를 통과한다.
뒤 텍스트의 출처나 시간 관계는 MAC이 증명하지 않는다.

별도 forensic projection은 **142개 인증 기록 / watchdog 관측 기록 10개**다.
이는 열 번의 측정이 아니라 다섯 TASK/WCHAN 쌍이다. 추가된 기록은 기존
12.006초 TASK와 같은 slot의 `WATCHDOG_WCHAN=0`이다. 179 CPU ticks는 이미
strict 결과에 있었고, 새로운 CPU 표본이나 기능 성공 증거가 생긴 것은 아니다.

독립 검토는 원본 framing 거부를 재현하고, 길이 부족·suffix 추가·body/MAC
변조·잘못된 key/run/boot/producer·중복 sequence를 포함한 열 가지 반례를
확인했다. 원본 capture, projection, journal, terminal과 source pin은 보존했다.
이 결과로 production parser의 framing을 완화하지 않는다.

## 2. 99 ticks는 무엇을 의미하는가

실제 P441 Image의 열 개 함수와 embedded config, 선택된 Samsung 소스의
procfs·scheduler·ARM64 경로를 대조했다. `nsec_to_clock_t`의 실제 ARM64
곱셈/shift는 모든 unsigned 64-bit 입력에서 `floor(ns / 10,000,000)`과 같다.
따라서 procfs CPU 시간 단위는 **USER_HZ=100**이다. 커널의 **HZ=250**과 다르다.

| 획득 시각 | state | 누적 CPU ticks | 마지막 CPU | wchan |
| --- | --- | ---: | ---: | --- |
| 6.539초 | S | 0 | 2 | `qcom_wdt_kthread` |
| 9.006초 | S | 0 | 2 | `qcom_wdt_kthread` |
| 10.003초 | S | 0 | 2 | `qcom_wdt_kthread` |
| 11.009초 | R | 80 | 7 | 0 |
| 12.006초 | R | 179 | 7 | 0 — 별도 forensic frame |

관측기는 `/proc/PID/stat`의 utime/stime만 합한다. child 시간 필드는 포함하지
않으며, 단일 kernel task의 신원을 전후 읽기로 확인한다. 997ms 간격에 99 ticks
증가는 약 **0.99초의 Linux scheduler 집계 시간**이다. 별도의 정수 버림,
비원자적 읽기와 집계 지연 때문에 정확한 99.3% 물리 CPU 사용률, 계속 같은
명령을 실행했다는 증거 또는 정확한 wake 시각으로 사용할 수 없다.

실제 `update_curr_rt`는 runqueue task clock 차이를 실행 시간에 더한다.
선택 config에는 IRQ 시간 집계가 있고 paravirtual steal 시간 집계는 없다.
task가 계속 current인 동안의 WFE 또는 firmware/EL2 체류가 집계에 포함되는
경우와 유용한 명령 실행을 이 숫자만으로 구분하지 못한다. 어떤 대기가 실제로
일어났다는 증거도 아니다.

실제 ARM64 `get_wchan`은 TASK_RUNNING이면 stack unwind 전에 0을 반환한다.
`R`은 running/runnable이고 TASK와 WCHAN 읽기는 원자적이지 않다. 따라서
`wchan=0`은 CSD/IPI 대기, SMC, 특정 PC나 실패한 CPU를 가리키지 않는다.
마지막 CPU 7도 ping 대상 CPU라는 뜻이 아니다.

“proc 읽기가 원격 watchdog의 실행 시간 갱신과 RT throttle을 직접 일으켰다”는
반례도 확인했다. 이 경로는 `proc_tgid_stat`의 group 집계를 사용하고,
`task_sched_runtime(current)`는 읽는 task와 대상이 같은 thread group일 때만
호출한다. rcS 관측 부모와 watchdog는 다르므로 그 분기는 선택되지 않는다.
다만 읽기의 lock/cache/스케줄링 간섭까지 없다는 뜻은 아니다.

RT warning은 runqueue에 누적된 RT 시간과 한 번만 출력하는 진단이다.
그 한 줄만으로 이 task 하나가 예산 전체를 썼다거나, throttle 시작·해제 시각과
지속 시간을 복원할 수 없다. warning 뒤의 R 표본도 throttle이 없었다는 뜻은
아니다. preemption이 막힌 대기와 지연된 reschedule도 가능한 경로다.

## 3. 첫 갱신 경로를 어디까지 좁힐 수 있는가

선택된 watchdog 경로는 timer wait → CPU ping → user-pet wait → pet SMC →
last_pet 갱신 → notifier → freeze lock/timer 재등록 → 다음 주기 순서다.
배포 모듈과 소스를 함께 확인했다.

중요한 반례는 **core가 `reset_wdt`의 반환값을 검사하지 않는다는 점**이다.
GH 구현은 pet SMC 오류를 errno로 반환할 수 있지만, core는 호출이 돌아오면
그 값과 무관하게 `last_pet`을 갱신한다. 그러므로 future `last_pet` 관측도
그 자체로 hardware pet 성공을 증명하지 않는다. P441에는 실패 주기의 bark,
status, last_pet 기록 자체가 없다. P437의 더 좁은 증거를 전이할 수 없다.

notifier 분기도 구체적으로 한정했다. 해시가 일치하는 선택 모듈 82개의 ELF
import에는 pet/bark notifier 등록 함수가 없고, Android pet 기록을 설명하는
`sec_qc_summary`도 선택되지 않았다. 컴파일된 notifier 호출은 있지만 실제
callback 등록의 근거는 없다. 다른 미관측 등록 경로까지 없다는 증명은 아니며,
등록된 Android callback에서 정지했다는 설명은 현재 선택 자료가 지지하지 않는다.

| 가설 / 반례 | 현재 판정과 이유 |
| --- | --- |
| watchdog task가 전혀 깨어나거나 집계 시간을 얻지 못했다 | 11–12초의 같은 task CPU 시간 증가와 맞지 않음. 정확한 timer callback 실행 시각은 미관측 |
| 10초 전 S 상태가 이미 실패였다 | 정상 timer wait와도 양립함. wchan은 함수 수준이며 특정 wait 구문을 구분하지 못함 |
| 특정 CPU의 동기 CSD/IPI 응답을 기다렸다 | 실제 경로가 있고 R/시간 증가와 양립함. 요청 대상·callback 완료·실패 PC가 없어 확정 불가 |
| pet SMC/하이퍼바이저 내부에서 지연됐다 | 양립함. Linux 집계 시간과 wchan 0으로 배제 불가. P441에는 pet 진입/반환 기록 없음 |
| pet이 오류로 반환됐거나 실제 갱신 없이 진행됐다 | core의 반환값 미검사 때문에 남는 분기. 해당 오류 문자열 부재는 로그 완전성이나 성공을 증명하지 않음 |
| pet 뒤 notifier/freeze lock/timer 재등록 또는 후속 주기 문제 | P441의 직접 pet/bark 기록 부재로 배제 불가. reset reason만으로 첫 pet 이전에 멈췄다고 고정할 수 없음 |
| 일반 userspace signal 때문에 interruptible wait가 EINTR spin을 했다 | kthreadd의 `ignore_signals` 승계와 watchdog의 `allow_signal` 부재 때문에 선택된 정상 경로의 설명으로 지지되지 않음. 커널 강제 signal/메모리 손상까지 배제한 것은 아님 |
| userspace watchdog daemon을 먼저 띄워야 했다 | 선택된 기본 user-pet 설정과 순정 첫 pet 순서가 지지하지 않음. 실패 당시 모든 mutable 상태를 직접 읽은 것은 아님 |
| cpuidle 비활성화가 문제를 해결했다 | 실제 옵션·driver 거부·실패가 함께 관측되어 이 실행에서는 해결되지 않음. 모든 idle/WFI/firmware 상호작용을 배제하지는 않음 |
| 새로운 관측기만이 실패의 필수 원인이다 | 관측기 없는 P437도 실패하므로 일반적인 필수 원인 설명은 성립하지 않음. P441에 대한 시간 교란 가능성은 남음 |

첫 kernel span부터 다음 kernel 시작 전까지 원시 바이트를 제한해서 다시
검색했다. RT warning과 watchdog reset reason은 있으나, 보존된 해당 범위에
failed-reset 진단, bark/pet 기록, CSD 위치 또는 6초 이후 failure-time stack/PC는
없다. 초기 경고의 stack은 이 실패의 stack이 아니다. 검색 결과 부재를
실행 부재나 다른 저장소에 context가 없다는 증거로 사용하지 않는다.

기존 [순정/커널/firmware 분석](S22PLUS_FYG8_STOCK_FIRST_WATCHDOG_H0_2026-10-20.md)의
349개 선택 명령 차이, alternative/static-key table, timer bucket, hypervisor
dispatch와 lock 분석은 입력이 같아 재사용했다. 공개
[preemption 재활성화 수정](https://kernel.googlesource.com/pub/scm/linux/kernel/git/xiang/erofs/+/cdf0ba15c0898a04f55ca396d119b97bbcd801bc)은
동기 CSD 대기 전 preemption을 허용해 비선점 구간을 줄인다. P441의 양상과
관련해 검토할 이유는 있으나, 실제 CSD 대기나 누락된 응답을 증명하거나 현재
실패의 수정을 보장하지 않는다. backport 또는 RT 예산 변경을 해결책으로
승격하지 않는다. 공개 검색은 모든 관련 결함을 망라한 증명이 아니다.

## 4. rcS와 비교 실험의 교란 요인

retained root archive의 절대 symlink와 usr-merge를 해석해 실제 script를
읽었다. 최초 단순 경로 조회의 부재 표시는 잘못된 경로 해석이므로 사용하지
않고 그 시도와 수정된 추출 결과를 함께 보존했다.

`/etc/init.d/rcS`는 `rc S`로 이어진다. `.legacy-bootordering`이 있으므로
**serial rcS**가 선택된다. dependency 파일이 있어도 startpar 병렬 실행의
근거가 되지 않는다. `udev` script는 대상 daemon 실행 파일이 없어 devtmpfs
검사나 trigger 전에 종료하는 경로다. 이를 “udev가 실행되어 막혔다”는 설명의
근거로 삼을 수 없다.

정적 순서는 hostname/mountkernfs, udev, mdev/mountdevsubfs, kmod,
mount-configfs/mountall, bootclean, brightness/procps/urandom, networking,
mountnfs/bootclean, bootmisc다. mdev는 background 방식이므로 serial script가
전체 시스템의 병렬성 부재를 뜻하지 않는다. 확인한 module/sysctl 설정에는
watchdog user-pet·RT 예산·cpuidle 변경 항목이 없다. 이는 archive 검사이며
실패 당시 실행된 모든 명령이나 동적 상태의 증거는 아니다.

P441의 다섯 관측은 rcS 부모의 wait loop가 12.006초까지 진행했음을 추가로
보여준다. child exec 성공이나 그 child가 어느 script에 도달했는지는 여전히
알 수 없다. 첫 heartbeat는 fork-record 이후 약 10초에 예정되므로, 그
부재만으로 부모가 첫 sleep에서 멈췄다고 할 수 없다. P441의 정확한 reset
시각도 없으므로 P437의 12.739초를 대입하지 않는다.

| 비교 | 통제된 것 | 통제되지 않은 것 / 허용되는 결론 |
| --- | --- | --- |
| P437 ↔ P441 | consumed task→artifact→build를 재연결. 같은 Image, 82개 module row, installed init, 초기 startup script, inittab/crontab/USB assets | idle 옵션, watchdog observer, admitted history, run seal과 mutable boot 상태가 다름. 한 변수의 물리 A/B 시험이 아님 |
| P441 H0의 기본 idle ↔ cpuidle.off archive | 같은 payload에서 command-line field 외 byte 동일이라는 기존 검증 | 기본 idle 쪽의 새 실기 실행은 없음. 동일 관측기로 된 물리 대조군이 아님 |
| P430 ↔ installed-init 계열 | 기존 감사의 동일 kernel/module와 장시간 생존 반례 | 후반 userspace 경로가 달라 어떤 rcS 작업이 원인인지 선택하지 못함 |

P437/P441 runtime source diff에서 새 observer 호출과 runlevel 관측 선택을
확인했다. qualifier의 차이는 run별 파일 이름이다. source 목록의 모든 변경을
보존했으며, hash가 다른 두 실행을 동일한 프로그램이라고 부르지 않는다.

## 5. 조사 종료 기준과 다음에 필요한 정보

여섯 질문 FRAME, ACCOUNTING, PATH, COUNTERFACTUAL, RCS, FRONTIER를
원시 자료·현재 소비자·선택 소스·실제 binary·독립 검토에 연결했다.
현재 보존 자료로 추가 가설을 판별할 수 있는 미완료 H0 검사는 발견되지 않았다.
남은 원인들은 아래 정보가 없는 한 같은 관측 결과를 만들 수 있다.

| 남은 구분 | 필요한 정보 |
| --- | --- |
| timer/thread 재개와 CPU ping 중 어디까지 갔는가 | 같은 부팅의 첫 timer/thread 경계와 CPU별 ping 시작/완료 |
| Linux 대기와 SMC/EL2 지연 또는 오류 반환 | pet 호출 전후와 반환값, 필요하면 해당 시점의 유효한 PC/stack |
| pet 이후 문제 또는 후속 주기인가 | notifier, 재등록과 다음 주기의 경계; 실제 갱신을 확인하는 독립적인 증거 |
| 어떤 rcS 작업과 겹쳤는가 | child exec 이후 script 진행 경계와 watchdog 경계의 같은-boot 연결 |
| P441 저장 결과/다음 boot의 root 상태는 무엇인가 | 별도로 승인·검증된 제한적 retrieval/admission. Android 건강으로 대신할 수 없음 |

같은 proc 표본을 더 자주 읽거나 `wchan=0`을 반복 수집해도 누락된 PC와 pet
반환값은 생기지 않는다. 원인 위치를 고르기 전에 무관한 firmware 전체를 더
해독하는 작업도 현재 가설을 구분하지 못한다. 새로운 자료가 특정 경로를
가리키면 해당 분석을 다시 연다.

다음 H0 설계의 유용한 질문은 **기존 Debian 서비스 목표를 유지하면서 최소한의
실제 watchdog 경계와 rcS child 진행을 어떻게 보존할 것인가**다. 기존 proc
관측의 한계를 반복하는 장치나 별도 상주 supervisor를 추가하는 것은 답이 아니다.
아직 새 kernel/module 계측 구현, capability review, artifact qualification
또는 기기 실행 권한을 완료했다는 뜻은 아니다. 소비된 P441을 재실행하지 않는다.

## 검증과 보존

private evidence base:
`workspace/private/outputs/s22plus-p441-watchdog-followup-h0-20261020-1/`.
`review/`는 독립 framing 검증과 열 가지 반례, `accounting-audit.json`은
실제 Image·열 개 함수·정수 변환 증명·config·소스 대조,
`comparison-audit.json`은 소비된 두 build와 rcS 분기,
`raw-frontier-audit.json`은 정확한 검색 범위·query·원시 offset을 보존한다.
`review-path/`는 독립 accounting/path/rcS 검토를 보존한다.
독립 결론은 `PASS_BOUNDED_CLAIMS_WITH_EXPLICIT_LIMITS`이며 세 가지 해석상
지적을 반영한 뒤 남은 actionable finding은 없다. 분석용 Python 8개 compile,
산출물 재개방, public diff/link/privacy/boundary 검사와 기존 변경 46개 보존을
확인했다. 런타임 코드가 바뀌지 않아 새 image/VM build는 하지 않았다.

기존 체크리스트에서 ABI — 확인: USER_HZ/HZ와 실제 ARM64 함수;
WIRE — 확인: strict/forensic 분리와 MAC 반례; SEMANTIC/AUDIT — 확인:
집계 시간, 반환값과 실제 pet, 같은-boot 원인 범위; ARTIFACT/ROUTE/PERSIST —
확인: consumed build/source/raw 연결과 원본 보존이다. HOST/RETURN은 기존
P441 closure 증거를 재사용하고, DISPLAY는 해당 없다. IO의 실기 timing 영향과
기능 미검증은 미확인으로 유지한다. 새 gate, 승인 단계나 권한은 추가하지 않는다.
