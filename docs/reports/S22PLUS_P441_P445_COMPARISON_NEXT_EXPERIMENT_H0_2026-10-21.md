# P441/P445 비교와 다음 실험 선택

상태: **H0 비교 완료; 단일 CPU 후보 방향 선택; 구현·빌드·기기 실행 없음**.
대상은 S22+ FYG8만이다.
[P441](S22PLUS_AUTOBOOT_WATCHDOG_P441_RUN_2026-10-20.md)과
[P445](S22PLUS_AUTOBOOT_PHASE_P445_RUN_2026-10-21.md)는 모두 소비·종료된
실행이며 재사용할 승인이 아니다. 이번 작업에서 A90·S20+를 포함해 기기
명령은 없었다.

**다음 기능 변수는 `maxcpus=1`로 선택한다.** P441의 기존 Debian 시작 경로와
가벼운 proc 관측을 출발점으로 삼고, P445의 phase kprobe/dispatcher 계측은
다음 후보에 넣지 않는다. 필요한 현재 이력·run binding은 새로 맞춘다.
이것은 watchdog의 다중 CPU 응답 대기 가설을 시험하는 제한된 후보이며,
단일 CPU 부팅의 실기 가능성이나 원인이 증명됐다는 뜻은 아니다.

## 비교에서 확인한 사실

소비된 task → artifact → build를 다시 연결하고 고정 source snapshot,
생성 입력, 실제 ELF, 기존 원시 capture와 receipt를 읽었다. 이전 분석의
해석만 비교하거나 현재 checkout을 당시 실행 소스로 대체하지 않았다.

| 비교 항목 | P441 | P445 | 판단 |
| --- | --- | --- | --- |
| 같은 부팅의 두 번째 admission 시작 | 3.356초 | 3.468초 — 별도 인증한 완전 프레임 | 시작 차이는 112ms |
| 다음 `ROOT_ELIGIBLE` 진입 | 6.363초 | 보존 기록 없음 | P441의 두 지점 간격은 3.007초. P445가 그 사이 어디서 끝났는지는 모름 |
| 설치된 PID1 / rcS 부모 진행 | PID1 6.508초, proc 표본 12.006초까지 | 보존 기록 없음 | P441은 단계 도달 경로이지 완성된 Debian 기준선은 아님 |
| 마지막에 남은 커널 텍스트 시각 | 첫 span 12.034912초; 별도 두 번째 span도 있음 | 3.497081초 | 실제 reset 시각이나 마지막 실행 지점이 아님 |
| 뒤따르는 firmware 문맥 | 첫 span 뒤 non-secure WDT fatal | PMIC abnormal reset / check rpm or kernel | 같은 reset 원인으로 합치지 않음. 후속 물리 복귀와의 관계도 한정됨 |
| 실제 kernel / 모듈 / shell / init | 동일 | 동일 | 82개 module row와 인자, 시작 script, idle 옵션, 절대 deadline도 동일 |
| 고정 runtime source | 147개 | 150개 | 공통 136개 동일, 11개 변경, phase 관련 3개 추가 |
| 루트 비교 표 | 8,974행 | 8,976행 | 기존 행은 전부 byte 동일. P444가 인증한 P441 파일 두 행만 추가 |

P445의 비교 표는 225 bytes 늘었으며 추가 파일은 early 10,972 bytes,
runtime 1,024 bytes다. 표·이력 header·실행 파일을 함께 확인했다.
새 이력이 임의의 예외나 약화된 admission으로 들어간 흔적은 찾지 못했다.
이 두 파일도 현재 부팅의 실제 내용과 다시 비교해야 한다.

초기 entry, file worker와 preparation 소스는 동일하다. 실제 preparation
ELF는 함수 기계어가 같고 run 관련 read-only data가 다르다. checker ELF는
전체 byte가 같다. entry/file worker ELF 전체는 같지 않다.

초기 경로의 `main`, `ri_run`, `at_emit` 여섯 구간을 실제 ARM64 disassembly로
대조했다. 함수별 명령 수·배치와 branch 명령 bytes는 같다. 바뀐 명령은
데이터 참조 ADD와 새 표 크기·행 수에 대응하는 MOV였다. 새 공통 logging
deadline 변수는 이 초기 경로에서 기존 값으로 컴파일돼 있다. installed hook은
phase 구현으로 실제 코드가 바뀌지만 두 번째 admission 뒤에 실행하는 경로다.

따라서 **현재 비교에서는 초기 경로의 새로운 제어 흐름 결함을 특정하지
못했다.** 이것은 전체 프로그램 동등성, layout/timing 영향의 부재, 두 번째
admission 성공 또는 phase 코드의 미실행 증명이 아니다.

## 보존 기록으로 더 좁힐 수 없는 부분

두 원시 `last_kmsg` 파일은 각각 2,097,136 bytes이고 기존 capture receipt의
크기·해시와 일치한다. 선택된 logger 소스는 retained payload를 index 기준으로
회전·복사한 뒤 proc 파일로 내보낸다. header/index 자체는 이 export에 없다.
따라서 export 안의 firmware 시작 offset을 물리 ring cursor로 바꾸거나,
덮인 bytes에서 사라진 몇 초를 계산할 수 없다. 새 RAM 읽기나 firmware
역공학을 이 비교의 후속 조건으로 추가하지 않는다.

P445의 후보 span 중간에는 이전 Android의 13,542초대 시각과 Wi-Fi 문장이
현재 문장에 섞인 깨진 줄 네 개도 있다. 문자열의 최대 timestamp를 후보의
수명으로 쓰면 잘못된 결론이 된다. 마지막 intact frame에 firmware suffix가
붙은 현상과 함께, 이 채널을 완전하고 단일 부팅에 속하는 텍스트로 취급할 수
없다는 추가 증거다. 인증된 run/boot frame은 별도로 유지한다.

다만 이 손상이 P445의 모든 후반 기록 부재를 설명한다는 증거도 없다.
P445 뒤에는 P441 첫 span의 WDT fatal과 다른 firmware 문맥이 남는다.
보존 손실, 더 이른 실패, 후속 reset의 영향은 현재 자료에서 완전히 분리되지
않는다. **Opus 5.5의 보존 손실 우선 가설을 확인된 원인 순위로 채택하지 않는다.**
정적 차이가 원인을 설명하지 못했다는 이유로 환경 문제라고 결론 내리지도 않는다.

원본 strict projection, 별도 forensic frame, journal, terminal은 수정하지 않았다.
P445 early-file cleanup은 그 시점의 사실이며 현재 native_data 일관성이나
후반 미실행의 증거가 아니다.

## 선택: P441 계열의 시작 경로에 `maxcpus=1`

이 선택의 근거는 P441의 watchdog 단서와 실제 실행 경로다.
[P441 후속 분석](S22PLUS_P441_WATCHDOG_FOLLOWUP_H0_2026-10-20.md)의 watchdog
task는 11–12초에 running/runnable 상태와 CPU 집계 시간 증가를 보였고,
선택된 모듈은 online CPU를 순회하며 동기 응답을 기다린 뒤 pet을 호출한다.
현재 커널에도 그 동기 대기 경로가 있다는
[기존 실제 Image 분석](S22PLUS_FYG8_STOCK_FIRST_WATCHDOG_H0_2026-10-20.md)을
재사용했다. P441의 `cpuidle.off=1`은 이미 문제를 해결하지 못했다.

`maxcpus=1`은 부팅 때 활성화할 CPU 수를 하나로 제한한다. 실제 P441/P445
Image에서 `maxcpus` early parameter, 처리 함수와 변수 연결을 확인했다.
컴파일된 기본 한도 32와 기존 실기에서 관측한 online CPU 8개는 구분했다.
선택 소스의 same-CPU `smp_call_function_single` 경로는 원격 응답을 기다리지
않고 callback을 실행한다. 한 CPU만 online이면 watchdog의 다른 CPU 응답
대기 경로를 사용하지 않게 되므로 가설을 시험할 수 있다.

후보에서 유지할 것은 다음과 같다.

- 같은 vendor kernel·82개 모듈, `cpuidle.off=1`, 초기 Debian PID1과 installed
  SysVinit/rcS/services/NCM/SSH 경로.
- 두 차례의 완전한 protected-root admission, clean 조건, 쓰기·deadline
  한도와 실제 watchdog enable/pet/bark 경로.
- P441 수준의 기존 bounded progress/proc 기록. P445 phase kprobe와 RAM
  dispatcher 대체는 넣지 않고 새로운 상주 관측기도 추가하지 않음.
- fresh run·현재 인증 이력·artifact binding과 기존 attended original-A
  복귀/건강 확인. P441/P445 image나 grant를 재실행하지 않음.

의도한 기능 변화는 CPU 부팅 수 하나다. mandatory history와 새 run seal은
이 변수와 구분한다. 이전 P441과 새 후보는 같은 시점의 물리 A/B 쌍이 아니므로
결과를 CPU 수 하나의 완전한 인과 증명이라고 부르지 않는다.

단일 CPU는 병렬성·IRQ affinity·부하·부팅 시간도 바꾼다. 또 `maxcpus`는 부팅
한도이며 영구적인 hotplug 금지 설정이 아니다. 후속 구현은 같은 부팅의
admission 및 SSH 관측에서 실제 online 상태를 확인하고, 추가 CPU를 켜는
동작을 넣지 않아야 한다. 인자 문자열 하나만으로 적용 성공을 주장하지 않는다.

watchdog disable, CPU ping 코드 우회, SMC 교체, RT 예산 무제한, 새 커널
backport와 root 비교 축소는 선택하지 않았다. 현재 근거로 원인을 특정하지
못한 채 더 큰 변경을 묶는 것보다 이 한 후보의 정보 가치가 높다고 판단했다.

## 성공·실패가 다음 결정을 어떻게 바꾸는가

주요 성공 기준은 **같은 부팅의 실제 Debian PID1·서비스·인증된 SSH가
120초 동안 유지되고 고정 종료가 완료되는 것**이다. NCM 열거만으로 기능
성공을 선언하지 않는다. 기존 제한 내의 관측과 shutdown을 재사용하며,
호스트의 USB 침묵을 30초 이상 생존했다는 증거로 바꾸지 않는다.

| 결과 | 다음 판단 |
| --- | --- |
| 한 CPU 적용을 확인하고 sustained services/SSH·종료 성공 | 제한된 단일 CPU Debian 기능을 확보. 다중 CPU 의존성은 우선 조사 대상이 되지만 특정 IPI/CPU가 원인이라고 확정하지 않음 |
| 한 CPU 적용과 admission은 확인됐지만 같은 watchdog 실패가 인증됨 | 원격 CPU 응답 대기만으로 충분히 설명하는 가설은 약해짐. 새 관측 체계 대신 남은 pet/SMC·주기 경로를 다음 선택 대상으로 좁힘 |
| admission 이전 실패 또는 endpoint·후반 증거 모두 없음 | NO_PROOF/inconclusive로 종료. 같은 후보 반복이나 보존 손실 확정을 허용하지 않음 |
| 실제 online 조건이 다르거나 새 hazard가 확인됨 | 가설 시험으로 인정하지 않고 해당 후보를 종료. 기존 복귀와 건강 확인을 수행할 범위는 원래 owner가 결정 |

이 문서는 후보 선택으로 끝난다. 이 조합의 부팅 인자 whitelist와 phase 없는
현재 history 선택은 runner에 구현돼 있지 않으며, 실제 변경에는 해당
capability의 검토·정적 qualification과 fresh applicable grant가 필요하다.
이는 새 승인 체계를
추가한 것이 아니라 현재 contract의 기존 조건이다.

P445 후 native_data 상태와 이력 파일은 아직 확인되지 않았다. 다음 writable
후보를 만들 때 필요한 protected read/recovery/history admission은 기존
정확한 경로로 해결해야 하며, 건강한 Android 복귀로 대신하지 않는다.

## 검증과 분석 종료

private 산출물:
`workspace/private/outputs/s22plus-p441-p445-decision-h0-20261021-1/`.
`artifact-comparison.json`, `retention-comparison.json`,
`selected-code-audit.json`에 원본 pins, 소스/표/ELF 차이, 정확한 raw 범위와
명령 비교를 보존했다. 두 분석 Python의 compile, 실제 산출물 재개방,
문서 diff/link/privacy 검사와 기존 46개 변경 보존을 확인했다.

이번 범위에서 결정에 필요한 비교는 끝났다. 새 보존 체계, 전체 firmware
분석, 원인 완전 해명 또는 전체 프로그램 동등성 증명을 다음 후보 선택의
추가 조건으로 만들지 않는다. 외부 모델 추가 호출, image/VM 빌드, 정책·runner
변경이나 기기 효과는 없었다.
