# S22+ 메인라인 Gunyah watchdog: ABI 일치와 등록 차단 지점 (H0)

2026-11-05 KST. 대상: SM-S906N / g0q / S906NKSS7FYG8.
Status: **H0 분석 / 기기 효과 없음 / 후보·승인 없음**.

Claude Opus 5.5가 Codex 메인라인 루프와 병행해 수행한 호스트 전용 조사다.
기존 [ML002 분석](S22PLUS_MAINLINE_ML002_BOOTLOOP_ANALYSIS_H0_2026-10-29.md),
[ML020 후속](S22PLUS_MAINLINE_POST_ML020_WATCHDOG_FIT_H0_2026-11-04.md),
[FYG8 순정 watchdog 분석](S22PLUS_FYG8_STOCK_FIRST_WATCHDOG_H0_2026-10-20.md)과
[P437 부팅 요구사항](S22PLUS_P437_BOOT_REQUIREMENTS_WATCHDOG_H0_2026-10-19.md)을
재사용했다. 기기 호출, 빌드, 실행 소스 변경은 하지 않았다.

## 결론

1. **메인라인 7.2.11의 `gunyah_wdt` 드라이버와 FYG8 하이퍼바이저의 SMC ABI는
   함수 번호, 인자 배치, 제어 값, 상태 반환 형식까지 일치한다.** 서버용
   watchdog을 새로 이식할 필요는 없어 보인다.
2. **유일한 차단 지점은 등록 단계의 UID 검사다.** `qcom_scm_gunyah_wdt_init()`는
   upstream Gunyah UID(`c1d58fcd-…`)를 요구하는데 FYG8 응답은 `bd54bd19-…`이다
   (ML002 분석). 그래서 `CONFIG_GUNYAH_WATCHDOG`를 켜도 장치가 등록되지 않는다.
3. **인계 시점에 guest watchdog이 켜져 있지 않을 가능성이 높다.** 아래 근거로
   보면 현재 메인라인 부팅을 죽이는 것은 guest watchdog이 아니다. 서버 과제는
   "꺼야 할 watchdog"이 아니라 "직접 켜야 할 watchdog"이다.

## 1. ABI 대조

순정 `gh_virt_wdt.ko`(P319 보존본, SHA-256 앞자리 `f030c5486a41b1fb`)의
기계어와 7.2.11 `drivers/watchdog/gunyah_wdt.c`를 비교했다. 하이퍼바이저 쪽
dispatch는 FYG8 분석에서 이미 원본 `hypvm` 바이트로 확인된 것이다.

| 기능 | 순정 `gh_virt_wdt` (기계어) | 메인라인 `gunyah_wdt` | 일치 |
| --- | --- | --- | --- |
| CONTROL | `0x86000005`, enable `x1=3`, disable `x1=2` | `0x0005`, `WDT_CTRL_ENABLE=BIT1\|BIT0`, `DISABLE=BIT1` | ✓ |
| STATUS | `0x86000006`, `x1=0`; 결과 `a1` bit0=enabled, bit31=expired, `a2`=마지막 pet 이후 ms | `0x0006`; `a2/1000`을 경과 초로 사용 | ✓ |
| PING | `0x86000007`, `x1=0` | `0x0007`, `(0, 0)` | ✓ |
| SET_TIME | `0x86000008`, `x1=bark_ms`, `x2=bite_ms`, 바꾸지 않는 쪽은 `0xffff` | `0x0008`, `(timeout_ms, timeout_ms)`, 최대 32초(0x8000 이상 예약) | ✓ (아래 미확인 1) |
| 호출 규약 | fast, SMC32, owner VENDOR_HYP, `smc #0` | `ARM_SMCCC_CALL_VAL(FAST, SMC_32, VENDOR_HYP, id)` | ✓ |

ML020 후속에서 확인한 FYG8 동작과의 상호작용:

- **같은 상태로 CONTROL을 보내면 거부된다**(오류 1 → 메인라인 `-EINVAL`).
  메인라인 probe는 `gunyah_wdt_stop()`의 반환을 무시한다. `start`는 첫 disable
  실패를 `watchdog_active()`일 때만 오류로 본다. 따라서 이미 꺼진 상태에서의
  거부는 등록과 첫 시작을 막지 않는다.
- PET은 disabled 상태에서도 성공할 수 있다. 메인라인은 PET의 성공을 상태
  조회로 쓰지 않는다.
- `.start`가 있어 7.2.11 watchdog core 등록 조건(ML020에서 지적된 `.start` 필수)을
  충족한다.

## 2. 등록 차단과 우회 방식

`qcom_scm_gunyah_wdt_init()`는 UID가 같고 DT에 `qcom,kpss-wdt` 또는
`arm,sbsa-gwdt` 노드가 없을 때만 `platform_device_register_simple("gunyah-wdt")`를
호출한다. 7.2.11 `sm8450.dtsi`에는 두 노드가 모두 없으므로 UID만 막고 있다.
드라이버는 DT 없이 이름으로 바인딩한다.

UID 검사는 Gunyah가 아닌 하이퍼바이저(KVM 등)에서 vendor-hyp 함수 5~8이
다른 의미일 때를 막기 위한 것이다. 이 펌웨어에서는 같은 번호가 watchdog
dispatch라는 바이트 근거가 있다. 따라서 **이 기기에 한정해 등록을 허용하는 것은
근거 있는 우회**다. 검사를 일반적으로 완화하는 것과는 다르다.

| 방식 | 내용 | 장점 | 단점 |
| --- | --- | --- | --- |
| A. 로컬 패치 | `qcom_scm_gunyah_wdt_init()`의 허용 UID에 FYG8 값 추가 | 한 줄, upstream 흐름 그대로 | 코어 패치. SCM probe 시점에 바로 등록 |
| B. 등록 전용 작은 모듈 | `platform_device_register_simple("gunyah-wdt", -1, NULL, 0)`만 수행 | 코어 무변경. 로드 시점과 여부를 userspace가 결정 | 별도 모듈 관리 |

첫 검증에는 **B를 권장한다.** 모듈을 로드하지 않으면 기존 후보와 동작이 같아서
변수 하나만 바꾸는 실험이 된다.

## 3. 인계 시점의 guest watchdog 상태

- 순정 커널은 `gh_virt_wdt`가 **스스로** bark 11,000ms / bite 14,000ms를 설정하고
  enable한다(ML020 후속). 이 값은 커널 드라이버의 요청값이다.
- P437(벤더 커널)에서는 첫 pet이 실패하자 약 12.74초에 bark/bite와 warm reset이
  기록됐고, 같은 후보가 다시 부팅했다. 드라이버가 켠 watchdog이 실제로 리셋을
  수행한 사례다.
- ML021~ML028 메인라인 커널은 `CONFIG_GUNYAH_WATCHDOG` 미설정이라 아무도 pet하지
  않는다. 그런데도 인증된 응답에 기록된 같은 부팅의 가동 시간이 51~67초다.
- SET_TIME 필드는 16비트 ms이고 0x8000 이상은 예약이다(순정은 0xffff를 "변경
  안 함"으로 사용). 따라서 설정 가능한 최대 기한은 약 32.8초다.

이 네 가지를 합치면 **인계 시점에 guest watchdog이 켜져 있었다면, pet 없이
67초를 넘길 수 없다.** 따라서 꺼져 있었거나, 만료가 리셋으로 이어지지 않는
구성이다. 같은 펌웨어와 ABL을 쓰는 ML002의 8~9초 루프도 guest watchdog bite로는
설명되지 않는다. ML002도 이 드라이버가 미설정이었다. 다른 원인이 그 루프를
일으켰을 것이다. 이것은 추론이며, 인계 시점의 STATUS를 직접 읽은 증거는 아니다.

## 4. 단계별 검증 제안 (각각 별도 후보와 승인 필요)

1. **W1 (등록만):** `GUNYAH_WATCHDOG=m` + 등록 모듈. probe의 STATUS와 stop만
   실행된다. `/dev/watchdog0` 생성, STATUS 결과(`CTL` bit0=0 예상), 기존 RAM
   PID1/SSH/Download 복귀가 유지되는지 본다. **3절의 추론을 직접 확인하는 단계**다.
2. **W2 (켜고 pet하고 끄기):** 32초(또는 더 짧게) 기한으로 연 뒤 일정 주기로
   ping하고, magic close로 정지한다. 기간 중 리셋 없음과 정지 후 STATUS를 확인한다.
3. **W3 (의도적 만료):** 켠 뒤 ping을 멈춘다. 기한 안에 warm reset이 일어나는지,
   그리고 Samsung upload/ramdump 화면이 아니라 일반 재부팅으로 이어지는지 본다.
   리셋 뒤에는 같은 boot_a(메인라인)로 다시 부팅하므로, 그 부팅의 식별과 Download
   복귀를 사전에 설계해야 한다. P437은 벤더 커널에서 warm reset 후 재부팅을
   보였다. 메인라인의 SCM download-mode 설정에서도 같은지는 별도로 확인해야 한다.

## 5. 서버 구성 메모 (현재 ML028 설정 기준)

- `panic=0`, `CONFIG_PANIC_TIMEOUT=0`: panic 시 영구 정지한다. watchdog을 켜면
  pet이 멈춰 bite로 복구되지만, `panic=10` 같은 값도 함께 검토할 만하다.
- `SOFTLOCKUP_DETECTOR`, `HARDLOCKUP_DETECTOR`, `DETECT_HUNG_TASK`가 모두 꺼져 있다.
  하이퍼바이저 watchdog이 최종 안전망이 되고, 이들은 원인 기록용으로 유용하다.
- 메인라인 드라이버는 probe에서 watchdog을 끄고, 커널이 자동 pet하지 않는다.
  사용자 공간(SysVinit이면 Debian `watchdog` 패키지 등)이 `/dev/watchdog`을 열어야
  보호가 시작된다. 이 방식은 커널 정지와 사용자 공간 정지를 모두 덮는다.
- `CONFIG_PM8916_WATCHDOG=m`(PMIC PON watchdog)은 대안 후보다. 다만 SPMI 접근
  권한과 PMK8350 호환이 미확인이라 우선순위가 낮다.

## 미확인

1. bark와 bite를 같은 값으로 주는 SET_TIME을 FYG8이 허용하는지. 공개 Gunyah
   `watchdog.c`는 bite ≤ bark이면 bite를 바로 큐에 넣는다. 그러나 순정은 이 조합을
   쓰지 않았고, 공개 소스는 FYG8의 정확한 소스가 아니다. W2에서 SET_TIME
   반환값으로 확인된다.
2. 인계 시점 STATUS의 실제 값(W1).
3. 메인라인에서 bite 이후의 경로(일반 재부팅인지, upload 모드인지)(W3).
4. FYG8 UID `bd54bd19-…`의 공개 출처. 웹 검색과 표준 이름공간 UUIDv3/v5 대조에서는
   찾지 못했다. 우회의 근거는 출처가 아니라 바이트 수준 ABI 일치다.

## 자료

- 순정 모듈: `workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-24/module-bytes/gh_virt_wdt.ko`
- 메인라인 소스: `workspace/private/outputs/s22plus-mainline-canary-h0-20261027-1/linux-7.2.11/`
  (`drivers/watchdog/gunyah_wdt.c`, `drivers/firmware/qcom/qcom_scm.c`)
- ML028 설정: `workspace/private/outputs/s22plus-mainline-ml028-rc-ssh-cycle-h0-20261105-1/review/final-review-1/embedded.config`
- upstream 시리즈: [PATCH v8 Gunyah Watchdog](https://lkml.org/lkml/2025/11/18/736),
  [RESEND v8](https://ratatoskr.run/linux-watchdog/2026/03/3452402/t)
- 공개 Gunyah: [quic/gunyah-hypervisor](https://github.com/quic/gunyah-hypervisor)
