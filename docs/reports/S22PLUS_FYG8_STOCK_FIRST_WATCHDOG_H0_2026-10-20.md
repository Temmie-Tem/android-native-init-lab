# FYG8 순정 Android의 첫 watchdog 갱신 조건과 Debian 경로의 차이

날짜: 2026-10-20 KST. 대상: `SM-S906N/g0q/S906NKSS7FYG8`만.
범위: 원본 펌웨어·소스·실제 모듈 및 이미 보존된 기록의 **H0 분석**.
완료 기준은 첫 주기 갱신의 실행 경로, 순정의 선행 설정, 현재 후보의 차이와
반증을 원본에 연결하는 것이다. 새 부팅·접속·기기 읽기·쓰기·후보 빌드는 없다.

## 확인된 결론

**가장 구체적인 차이는 초기 CPU idle 정책이다.** 순정은 초기 모듈 로딩에서
`qcom_lpm` governor를 선택하며, 배포 바이너리의 `sleep_disabled` 초기값은 1이다.
이 값이 유지되는 동안 해당 governor는 가장 얕은 state 0/WFI를 선택한다.
P437은 이 모듈을 포함하지 않고 초기 로그에서 `menu` governor를 선택한다.
순정의 IPI pending 시 깊은 idle 진입을 억제하는 hook도 이 모듈에 있다.

그러나 **이 차이가 P437 reset의 원인이라고 확정할 수는 없다.** P430은 P437과
실제 커널 바이트 및 82개 모듈의 해시·인자가 같은데도 준비·파일 작업 후 약
368.889초까지 생존했다. 빠진 모듈이 있으면 항상 첫 pet에 실패한다는 설명은
이 반례와 맞지 않는다. 현재 우선 가설은 설치된 Debian 시작 때 달라지는
부하·idle 전환·CPU 응답의 상호작용이며, 실제 idle 상태와 ping 대기 지점은 미관측이다.

또한 순정의 첫 주기 pet은 약 **10.24초**, `sys.boot_completed` 후 설정 서비스는
**16초 이후**다. 그 늦은 스크립트나 Android watchdog daemon을 추가해야 첫
갱신이 된다는 설명은 확인한 실행 순서와 맞지 않는다. 현재의 kernel watchdog,
PSCI와 기본 interrupt 초기화 자체가 통째로 빠진 상태도 아니다.

## 원본과 실제 실행물의 구분

원본 FYG8 배포 ZIP의 AP 전체를 읽어 CRC와 해시를 확인하고, sparse super의
geometry/table을 검사한 뒤 vendor·system을 호스트 파일로 추출했다. 마운트하지
않고 선택한 init/config/script 200개를 읽었다. 기존 보존본과 비교 가능한
161개는 바이트가 같았고, system init도 별도로 일치했다.

FYG8 공개 소스는 독립된 전체 트리가 아니라 FYD9 기반에 적용하는 delta다.
기반 `Kernel.tar.gz`와 FYG8 delta를 함께 사용하고, 선택한 파일 99개의 출처와
override를 기록했다. GKI core는 `kernel_platform/common`, vendor module은
`msm-kernel`로 구분했다. 대조한 core 9개 중 8개는 양쪽이 동일하고, timer는
msm 쪽의 추가 tracepoint export 두 줄만 달랐다. 이는 선택한 소스 비교이며
배포 커널 전체와의 재현 빌드 일치 증명이 아니다.

원본 vendor ramdisk에서 실제 모듈 9개와 load/dep/blocklist를 다시 추출했다.
watchdog, CPU hook, LPM, CPUfreq, WALT, GIC routing, Samsung pet 기록의
소스 설명을 실제 ELF symbol·data·relocation·disassembly와 대조했다.
`vendor_dlkm`도 원본 super에서 다시 추출하고 기존 corpus의 image 해시와
대조했다. 그 안의 실제 `qcom_lpm.ko`는 분석한 ramdisk 사본과 바이트가 같다.

| 비교 대상 | 확인한 정체성 | 해석 범위 |
| --- | --- | --- |
| 순정 배포 Image | SHA-256 `027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d` | 순정 Android의 커널 |
| P430/P437의 실제 boot payload Image | SHA-256 `d510a3f83a6d48392649df325223e9847f85e2ee35989f32db0fb6abff371a3d` | 보존된 FYG8 진단 carrier; 순정 Image와 바이트가 다름 |
| P430 대 P437 | 실제 kernel 동일, 82개 module 행과 인자 동일 | 준비/park와 installed-init 경로의 비교에 유효; 전체 userspace/실행 시각 동일을 뜻하지 않음 |
| 순정 대 후보 config | lab E1 설정과 빌드 경로 차이; 두 쪽 모두 `CONFIG_RT_GROUP_SCHED=n` | config 유사성은 core 기계어 동일성의 대용이 아님 |

따라서 아래의 모듈 기계어 확인과 공개 core 소스 설명은 증거 종류가 다르다.
옛 vmlinux를 현재 Image의 symbol oracle로 쓰지 않았고, 모든 core 함수의
순정/후보 바이트 동일성을 주장하지 않는다.

## 첫 주기 갱신이 실제로 요구하는 경로

선택된 구현은 `qcom_wdt_core.ko` + `gh_virt_wdt.ko`다. 두 모듈은 P437에
이미 포함되어 있다. 소스와 배포 모듈에서 확인한 순서는 다음과 같다.

1. 초기 등록에서 watchdog를 설정·enable하고 초기 reset을 호출한다.
   `last_pet`을 기록하고 9,360ms 주기의 kernel timer를 건다.
2. timer callback이 만료 상태를 설정하고 `gh-watchdog`를 깨운다.
   thread는 `SCHED_FIFO`, 우선순위 99를 요청한다.
3. IPI 확인이 활성화된 경로에서 online CPU를 순회한다. `CPU_PM_ENTER`로
   idle power-collapse 상태라고 기록된 CPU는 건너뛰고, 나머지에는
   `smp_call_function_single(..., wait=1)`을 호출한다. 필요한 호출들이
   반환해야 다음 단계로 간다. 이 코드는 반환 errno를 따로 검사하지 않으므로
   뒤의 pet 기록만으로 모든 CPU의 개별 응답을 증명할 수는 없다.
4. 사용자 pet 조건을 확인한다. 초기값은 `user_pet_enabled=false`,
   `user_pet_complete=true`이므로 기본 경로에는 Android 사용자 공간 pet이 필요 없다.
5. `gh_reset_wdt()`가 hypervisor에 `SMC 0x86000007`을 보낸다.
   반환 후 core가 `last_pet`을 갱신하고 pet notifier를 호출한 뒤 다음 timer를 건다.

배포 watchdog 모듈에는 CPU_PM notifier 등록도 있다. 따라서 “모든 online
CPU는 idle 상태와 무관하게 반드시 ping된다”거나 “PSCI idle 지원이 없다”는
설명은 이 구현에 맞지 않는다. 실제 실패 순간의 CPU_PM 상태·IPI 응답은 별도다.

두 기록의 의미도 구분해야 한다. Samsung `sec_qc_summary`는 pet notifier에서
현재 시각과 자신이 저장한 이전 시각을 출력한다. 그 저장값은 0으로 초기화된다.
순정 첫 주기 기록의 이전 시각 0은 watchdog 초기 reset이 없었다는 뜻이 아니다.
반면 P437 bark의 마지막 pet은 watchdog core의 값이다.

또한 core는 `reset_wdt()`의 반환값을 검사하지 않고 `last_pet`을 갱신한다.
**pet notifier는 reset 함수의 반환과 기록 경로 진입을 증명하지만, 그 한 줄만으로
SMC 성공을 증명하지 않는다.** 오래 지속되는 정상 동작과 오류 유무를 함께 봐야 한다.

## 순정의 실제 선행 순서

원본 `init.qti.kernel.rc`는 early-init에서 모듈 서비스를 시작하고 init 단계에서
ready property를 기다린다. 첫 module은 동기식으로, 나머지는 각각 background
modprobe로 실행한 뒤 `wait`한다. script의 ready property/exit 0은 모든 개별
driver probe 성공을 보증하지 않는다. 실제 governor 선택 로그를 따로 대조했다.

| 기록 | 부팅 후 시각 | 확인한 사건 |
| --- | ---: | --- |
| 보존된 순정 HIGH-debug 부팅의 초기 구간 | 3.513–3.712초 | `qcom_lpm` 로딩 및 3.665초의 `qcom-cpu-lpm` governor 선택 |
| 일반 순정 baseline | 4.051초 전후 | module ready 대기 종료; 일부 뒤따른 uclamp 설정은 권한 오류 |
| 일반 순정 baseline | 10.238645초 | 첫 주기 pet notifier가 기록한 pet 시각 |
| 같은 baseline | 16.278–16.290초 | qcom-post-boot, kernel-boot, kernel-post-boot 시작 |
| 같은 baseline | 19.714601초 | 두 번째 주기 pet 시각 |
| 같은 baseline | 21.998초 | post-boot script가 `sleep_disabled=N` 설정을 보고함 |
| HIGH-debug 초기 구간 | 10.239082 / 19.711099초 | 같은 초기 governor 선택 뒤 첫 두 주기 pet 기록 |

일반 baseline은 원래의 exact-target connected-preflight receipt와 원시 파일
해시로 묶었다. HIGH-debug 자료는 나중에 operator가 panic을 유도한 과거 실험이다.
여기서는 **20초 이전 순정 초기화 구간만** 썼으며, 후반 panic이나 복귀를 정상
부팅 대조군의 건강 증거로 합치지 않았다. 여러 위치의 동일 원시 파일도 독립
표본으로 세지 않았다. 두 부팅의 시각을 하나의 부팅처럼 합친 표가 아니다.

원본 `init.kernel.post_boot-taro.sh`에는 SoC revision·충전 분기가 있다.
rev 1.0의 sleep 유지 및 watchdog wakeup 설정을 다른 분기에 일반화하면 안 된다.
선택한 일반 baseline에서는 N 설정 메시지가 첫 두 pet 뒤에 나타난다.
다만 초기 `sleep_disabled`의 실제 readback은 없다. 배포 기본값, 빈 module 인자,
governor 선택, 늦은 해제 script가 초기 얕은 idle 정책을 지지하는 증거이며,
모든 순간의 실제 flag 값과 CPU state를 측정한 결과는 아니다.

## Debian에서 빠진 부분과 우선순위

| 항목 | 순정에서의 역할·근거 | P437 및 판단 |
| --- | --- | --- |
| `qcom_lpm` | 배포 `.data`의 `sleep_disabled=1`; 기본 분기는 state 0/WFI. rating 50으로 초기 `menu`보다 우선하며 IPI pending 시 깊은 idle을 억제 | 선택된 82개에 없음. 초기 `menu` 선택은 로그로 확인. 첫 갱신과 직접 관련된 가장 구체적인 정책 차이이나 실제 stall 원인은 미확인 |
| `sched-walt`, `qcom-cpufreq-hw` | first-stage load 목록에 있으며 LPM의 dependency closure에 연결 | 둘 다 없음. 부하·주파수·idle 예측의 차이. LPM 하나를 무조건 추가하는 방식은 의존성과 부작용을 생략함 |
| `qcom_cpu_vendor_hooks` | first-stage 모듈; timer bucket 계산에서 expiry를 1 jiffy 줄이는 hook, CPU 진단 등 | 없음. timer 배치 차이는 존재하나 watchdog 실패를 직접 증명하지 않음. 모듈 전체는 이 hook만의 변경이 아님 |
| `qcom_gic_intr_routing` | first-stage 모듈; 주로 SPI routing 조정 | 없음. watchdog CPU ping의 SGI/IPI와 구분해야 함. 기본 GIC 초기화 누락이라고 해석할 수 없음 |
| `sec_qc_summary` | pet notifier의 순정 주기 기록을 생성 | 없음. 동일한 순정 pet 문장이 P437에서 안 보이는 것은 관측 차이도 포함함 |
| kernel watchdog·CPU_PM·PSCI/GIC 기반 | watchdog thread와 hypervisor ops, CPU power/interrupt 기반 | watchdog 모듈 포함, PSCI v1.1·8 CPU online·GIC redistributor·PSCI cpuidle 초기화가 첫 P437 부팅에 기록됨. 이후 응답 정상성까지 증명하지는 않음 |
| Android post-boot script·irqbalance | boot-completed 분기의 후반 튜닝 | 확인한 순정 첫 pet보다 늦게 시작. 첫 pet의 필수 선행 daemon으로 보기 어려움 |
| RT budget 설정 | 선택한 순정 파일 200개에서 global RT period/runtime 변경을 찾지 못함 | foreground-boost의 `cpu.rt_runtime_us` 문장은 global sysctl과 다름. 두 커널의 RT group scheduling도 꺼져 있음. 예산 무제한 변경의 근거가 되지 않음 |

timer 차이는 좁게 계산할 수 있다. `CONFIG_HZ=250`에서 9,360ms는 2,340 jiffies다.
base clock과의 delta가 이 값인 배치 모델은 level 2, 64-jiffy bucket에 해당한다.
실패 순간의 실제 base clock을 측정한 것은 아니다. 실제 hook의 1-jiffy
감산을 64개 expiry 나머지에 적용하면 bucket 차이는 0 또는 64 jiffies(256ms)다.
이는 **bucket 산술만의 차이**이며 thread scheduling·IRQ·IPI·SMC 지연의 상한이
아니다. 이 hook의 부재만으로 수초 뒤 bark까지 갱신되지 않은 현상을 설명했다고
할 수 없다.

CPU idle driver와 governor는 별개다. 현재 PSCI driver가 있다는 사실과 순정
Qualcomm governor가 없다는 사실은 양립한다. 이 구분은
[Linux 5.10 CPUIdle 설명](https://www.kernel.org/doc/html/v5.10/admin-guide/pm/cpuidle.html)과
해당 FYG8의 실제 governor 등록·선택 코드에서 함께 확인했다. 모듈 목록·의존성·
삽입과 장치별 동작을 나누는 기준은
[AOSP kernel module 설명](https://source.android.com/docs/core/architecture/kernel/kernel-module-support)도 참고했다.

## 펌웨어 경계에서 확인한 것과 남은 것

원본 BL member 전체의 CRC·해시 및 32개 압축 image member의 해시를 남겼다.
여기에는 `hypvm`, `tz`, `aop`, `cpucp`, `xbl` 계열이 포함된다. 파일의 존재나
이름으로 해당 runtime 내부 동작이 정상이라고 판정하지 않았다.

선택한 8개 실제 모듈의 import table에는 직접적인 `request_firmware` 계열
호출이 없다. 특히 `gh_virt_wdt`의 pet은 배포 기계어에서도 위 SMC를 직접
실행한다. Android에서 firmware 파일을 복사해 주는 사용자 공간 daemon이 이
pet의 직접 호출 경로에 있는 구조는 아니다. 다만 간접 dependency와 부트로더가
준비한 firmware는 여전히 필요할 수 있으므로 “firmware가 전혀 필요 없다”는
결론은 아니다.

원본 vendor DTB 네 blob에는 PSCI·CPU idle state·local-timer-stop 및 CPU hook
관련 노드가 있다. 이것은 bootloader가 선택·수정한 최종 live DT와 같다는 증명이
아니다. 배포 DTB에서 GH 노드를 찾지 못한 것을 실제 watchdog 미존재의 증거로
쓰지 않았다. P437의 실제 초기화 및 bark/status 기록이 별도로 존재한다.

이 H0는 secure/hypervisor firmware 내부를 의미적으로 역공학하거나 P437의
실패 시점 SMC 반환값을 얻은 작업은 아니다. 현재 자료로 “firmware blob 누락”을
원인으로 확정할 근거는 없으며, CPU idle 복귀·IPI 및 SMC 내부의 실제 원인은 남아 있다.

## P437에 적용할 수 있는 해석

[기존 boot-requirements 분석](S22PLUS_P437_BOOT_REQUIREMENTS_WATCHDOG_H0_2026-10-19.md)의
첫 실험 부팅은 초기 last-pet 약 0.739초, `gh-watchdog` 문맥의 RT throttling 약
11.988초, bark/bite 약 12.739초다. watchdog 경로가 첫 갱신을 마치지 못했다는
관찰은 유지한다. 현재 문맥의 RT 경고는 다른 Debian RT task가 예산을 소모했다는
증거가 아니며, 동기 CPU 호출의 대기 자체가 CPU를 소비할 가능성과도 구분해야 한다.

P430의 동일 kernel/module 대조 때문에 일반적인 파일 누락 하나로 모든 실패를
설명할 수 없다. 반대로 P430의 생존은 installed-init 부하에서의 idle/IRQ 문제를
배제하지 않는다. 현재 우선 가설을 시험하려면 다음 차이를 구분해야 한다.

- 첫 pet 전후의 governor/idle 사용과 CPU 상태가 실제로 어떻게 달라지는가.
- timer가 thread를 깨웠는가, thread가 CPU 응답을 기다리는가, pet 호출까지 갔는가.
- 작은 idle 정책 차이만으로 installed-init 경로가 첫 갱신을 넘고 계속 실행하는가.

이미 준비된 [비활성 watchdog 관측 H0](S22PLUS_WATCHDOG_OBSERVER_H0_2026-10-19.md)는
기존 parent에서 thread 상태·CPU 시간·wait symbol을 제한적으로 샘플링한다.
이를 재사용하되 표본 사이의 짧은 경계나 firmware 내부까지 자동으로 증명한다고
하지 않는다. 다음 유용한 H0는 **초기 idle 정책을 하나의 변수로 비교할 수 있는
최소 설계와 의존성 확인**이다. Android 모듈 전체 추가, watchdog 해제, RT 예산
무제한 변경이나 새 상주 daemon을 정답으로 채택할 증거는 없다.

별도로 [P438](S22PLUS_AUTOBOOT_EVIDENCE_P438_RUN_2026-10-20.md)은 dirty native_data
view와 runtime file 부재를 관측했다. 다음 writable boot의 root admission/필요한
고정 journal recovery 검토는 그대로 남는다. 파일 복구를 watchdog 원인 증명으로
대체하지 않는다. 이 보고서는 새 gate·활성화·후보·grant 또는 기기 동작을 만들지 않는다.

## 재현 자료와 검증

private 작업 위치는
`workspace/private/outputs/s22plus-stock-watchdog-conditions-h0-20261020-1/`다.

| 자료 | 보존 내용 |
| --- | --- |
| `stock/extraction.json`, `stock/partition-extraction.json` | 원본 ZIP/AP/super 및 vendor/system의 해시, 추출 출처 |
| `stock/files.json`, `stock/inline-files-v2.json` | 선택한 원본 200개 파일과 기존 보존본 비교 |
| `kernel/source-selection.json`, `kernel/source-supplement.json` | FYD9 기반+FYG8 delta의 선택 소스 99개와 해시 |
| `kernel/module-extraction.json`, `kernel/disassembly/` | 원본 vendor ramdisk, 실제 module 바이트와 symbol/import/명령어 대조 |
| `records/`, `kernel/dtb/` | 원시 receipt·offset·해시로 묶인 순정/P437 구간과 DTB 결과 |
| `synthesis/evidence-audit.json` | 파일·소스·모듈 검증, P430/P437 실제 payload join, 순정 시각 관계와 한계 |
| `synthesis/interface-audit.json` | BL 32-member inventory, 8개 import table, pet SMC와 64-case timer 산술 |
| `synthesis/vendor-dlkm-lpm-identity.json` | 원본 super의 vendor_dlkm 해시, 실제 LPM과 ramdisk 사본의 바이트 일치 |

호스트 F2FS 도구의 inline 추출은 extra-isize를 잘못 취급해 앞쪽 36바이트를
삽입하고 끝을 잘랐다. 이 실패 출력을 보존하고, exact inode layout의 extra
영역과 reserved word를 반영한 읽기로 수정했다. 기존 보존본의 byte equality도
확인했다. 성공 코드만으로 잘린 script를 원본으로 채택하지 않았다.

실제 producer/consumer 검증 결과: 200개 파일·99개 선택 소스·9개 모듈 pin,
P430/P437 kernel 및 82개 module row equality, 초기 LPM data byte, 실제 timer
감산 명령어, 순정 receipt와 첫 pet/후반 service 시각 관계가 통과했다.
추출한 super/vendor/system/vendor_dlkm의 읽기 후 해시는 그대로다. private Python은
`py_compile`하고 실제 원본 경로로 실행했다. 새 C·runtime·runner 변경은 없어
교차 빌드나 F1 capability 재검토를 만들지 않았다.

체크리스트: **AUDIT 확인** — 원본 해시·부팅별 구간·reader 오류를 구분했다.
**SEMANTIC 확인** — module-ready/exit 0, notifier, SMC 반환 및 실제 기능의 증명
범위를 구분했다. **ABI 확인 범위 제한** — 실제 AArch64 module 명령어와 선택
FYG8 source를 대조했으며 core 전체의 기계어 일치나 device 실행 성공은 주장하지 않는다.
후보 실행·전송·복구 변경 항목은 해당 없음이다. 모든 raw 로그·image·식별자는
private에 보존했다. A90·S20+ 및 사전 존재하던 다른 작업은 변경하지 않았다.
