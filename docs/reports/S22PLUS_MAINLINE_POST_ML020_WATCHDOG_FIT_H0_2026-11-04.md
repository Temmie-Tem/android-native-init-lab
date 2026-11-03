# ML020 후속: guest watchdog 이식 타당성 확인

Status: **H0 검토 완료 / 새 기기 후보 미선정 / 기기 효과 없음**.

[ML020](S22PLUS_MAINLINE_ML020_RUN_2026-11-04.md)의 소비·건강한 Android 종료 뒤,
실제 RAM PID1·인증 USB 부팅을 돕는 누락 기능이 있는지 확인했다. 이번 한정
단위는 FYG8 guest watchdog의 배포 바이너리 ABI와 현재 메인라인 코어의
수용 조건을 연결해, 조건부 keepalive 이식의 근거를 판단하는 것이었다.

**현재 자료로는 그 이식을 채택하지 않는다.** 메인라인 인계 때 이미 켜진
guest watchdog과 그 타이머의 기한이 확인되지 않았다. 순정 커널이 직접
설정하는 값을 그 미확인 타이머에 적용할 근거도 없다. 이는 watchdog 원인을
배제했다는 결과나 새 실행 gate가 아니다. 기능에 필요한 근거가 생기면 다시
평가할 수 있으며, 전체 펌웨어 해명이나 새 관측 체계를 선행 조건으로 만들지 않는다.

## 확인한 동작

원본 vendor ramdisk에서 보존한 `gh_virt_wdt.ko`, `qcom_wdt_core.ko`와
원본 FYG8 `hypvm`의 해시를 검증했다. 선택한 firmware 명령어 153개와
core 명령어 45개를 실제 바이트에 대조하고, ARM64 명령어 일부를 호스트에서
실행하는 제한 fixture 15개를 통과했다. 실제 SMC, 펌웨어 잠금, 하드웨어
타이머, 전체 handler 실행이나 기기 호출은 하지 않았다.

- 순정 core는 9,360ms pet 주기와 11,000ms bark 값을 넣고, 초기화에서
  bark 및 bark+3,000ms의 bite 설정을 요청한 뒤 enable과 초기 pet을 호출한다.
  해당 초기화의 소스와 배포 명령어는 이 두 주기를 DT 속성으로 덮어쓰는
  경로를 보여주지 않는다. 이 값들은 **순정 드라이버의 설정 요청값**이며,
  실제 firmware 적용 성공이나 메인라인 인계 전 타이머의 값은 아니다.
- attached-object의 같은 enable 상태를 요청하면 내부 함수는 false를
  반환하고, 바깥 dispatcher는 이를 SMC 오류 1로 바꾼다. vendor wrapper는
  그 오류를 `-EINVAL`로 변환한다. core는 enable 오류에서 초기 pet 전에
  실패 경로로 나간다. 모든 오류가 같은 상태를 뜻한다는 역방향 추론은 안 된다.
  wrapper의 별도 software-enabled guard와 전체 실행 조건도 구분했다.
- STATUS는 enabled·expired 플래그와 마지막 pet 이후 경과 시간을 반환한다.
  확인한 경로의 시간 결과는 하위 16비트이며 bark/bite 기한을 반환하지 않는다.
  이 사실을 모든 firmware 인터페이스에 getter가 없다는 주장으로 확대하지 않는다.
- PET은 disabled 상태에서도 잠금과 객체 필드 갱신을 거쳐 성공을 반환할
  수 있다. 성공 코드만으로 실제 timer service를 증명하거나, 이 호출을
  상태 변화 없는 조회로 취급할 수 없다.
- 현재 Linux 7.2.11의 `___watchdog_register_device()`는 `.start`가 없으면
  등록을 거부한다. 따라서 제안된 `.ping`만 있는 드라이버는 그대로 등록되지
  않는다. stub 추가만으로 worker·사용자 공간·수명·기한 문제가 해결되지는 않는다.

이전의 [firmware/클라이언트 연결 근거](S22PLUS_FYG8_STOCK_FIRST_WATCHDOG_H0_2026-10-20.md)와
guest 기본값, HYP 자체 timer, TZ/HYP hardware bank의 구분은 재사용했다.
별도 bank나 전체 부트로더 호출자를 다시 조사하지 않았다. 특정 vendor
초기화의 성공이 관측됐다는 전제도 그 시점·그 부팅에만 적용되며, ML020의
인계 상태나 과거 리셋 원인으로 전이되지 않는다.

## 두 차례 교차 검토와 USB 후속 확인

Claude Opus 5.5 High와 Gemini 4 Argon High가 각각 1차 제안과 2차 상호
반박을 수행했다. 실제 바이너리·소스 결과를 전달한 뒤 두 모델 모두 현재
이식안 미채택에 동의했다. 다음 제안은 근거 부족 또는 실제 소비기 불일치로
채택하지 않았다.

- 순정 초기화와 constructor만으로 메인라인 진입 시 disabled 또는
  keepalive의 확정적인 무효 동작을 선언하기.
- 순정 설정값을 미확인 prearmed watchdog의 기한으로 사용하기.
- `.start` 없이 watchdog core에 등록하기.
- 미래 USB 성공을 ML020 watchdog 원인의 증명으로, 미래 기록 부재를
  driver 미진입 또는 disabled 상태의 증명으로 해석하기.

이는 자문 토론이며 독립 실행 검토 `PASS_GO`가 아니다. 실행 소스·정책·스키마·
기기 후보를 변경하지 않아 새로운 실행 검토나 capability adoption은 만들지 않았다.

2차에서 제안된 USB 질문도 기존 ML020 산출물로 좁게 확인했다. 보존된
`prepared.json`의 해시와 일치하는 DTB·config에는 활성 USB2 PHY와 고정
`dr_mode = "peripheral"`이 있다. 해당 DWC3 Qualcomm 소스는 이 분기에서
software VBUS-valid를 설정한 다음 core probe를 호출한다. 남아 있는
`usb-role-switch` 속성은 이 고정 분기보다 뒤의 대안 분기에서 검사된다.
확인한 USB·PHY·GCC·RPMh·regulator·interconnect·SMMU 설정 11개는 모두
built-in이다. 여기서는 VBUS 처리 누락이나 선택한 driver 설정 누락을 찾지 못했다.

이 USB 확인은 선택한 소스·DT·config 관계에 한정된다. 전체 transitive
supplier의 실제 bind, vmlinux 전체 matching, PHY 전기 상태 또는 물리
probe 도달을 증명하지 않는다. 새 toggle이나 같은 후보의 반복 실행을
정당화하지 않으며, 기존 RAM PID1·USB 미증명 상태도 바꾸지 않는다.

## 검증과 종료

한정 ABI fixture와 USB 소비 경로 확인, 변경한 두 private Python 스크립트의
`py_compile`, 입력 해시·문서 링크·개인 식별자·diff 검사를 완료했다.
기존 실패 체크리스트의 ABI·SEMANTIC·AUDIT는 실제 바이트, 반환값 의미와
출처 구분으로 확인했다. 기기 transfer·recovery·PERSIST는 이번 H0에
해당하지 않는다. 새 이미지나 VM을 만들지 않았다.

ML020의 원본 task·grant·journal·종료·회수 증거와 실행 소스는 그대로다.
이번 단위는 새 D0 건강 측정을 하지 않았으므로, 마지막의 건강한 종료를
현재 시점의 새 건강 증거로 주장하지 않는다. ML020은 계속 소비된 상태이며
새 후보·승인·F1 owner는 없다. A90과 S20+는 건드리지 않았다.

private 근거는 `workspace/private/outputs/s22plus-ml020-next-discussion-20261104-1/`의
`guest-watchdog-audit.json`, `usb-followup.json`, 두 모델의 각 두 응답과
원시 stream, `usage-summary.json`, `final-check.json`에 있다. 외부 모델의
호출 전후 사용량과 실패 여부는 private append-only 사용량 기록에도 남겼다.
