# 프로젝트 연혁

[English](PROJECT_HISTORY.md) · **한국어**

> **이 문서는 서술이며 증거가 아닙니다.**
>
> 여기 적힌 어떤 문장도 device authority를 부여하지 않고, 어떤 claim의 정본도
> 아닙니다. 각 항목의 정본은 링크된 report, plan, campaign ledger이며, 현재
> 상태는 `AGENTS.md`의 binding target registry와 각 `GOAL*.md`가 기준입니다.
> 이 문서와 정본이 어긋나면 **정본이 이깁니다.**
>
> 증거 용어(PROVED / observed / designed / unproved)는
> [`../devices/README.ko.md`](../devices/README.ko.md)의 정의를 그대로 씁니다.
> 서로 다른 run의 결과를 합쳐 새로운 end-to-end 성공으로 읽지 마십시오.

이 문서는 2025-11-13 첫 커밋부터 현재까지 저장소가 지나온 길을 시대 단위로
정리합니다. 무엇이 언제 열리고 닫혔는지, 그리고 **왜 방향이 바뀌었는지**를
남기는 것이 목적입니다.

- 기간: 2025-11-13 ~ 2026-09-02
- 커밋: 5,754
- 활동일: 125일 (5개월 휴면 1회 포함)
- 대상 기기: Galaxy A90 5G → Galaxy S22+ → Galaxy S20+ 5G

일(day) 단위 상세는 이 문서가 아니라 `git log`가 정본입니다. 재생성 가능한
정보를 문서로 굳히지 않습니다.

---

## 한눈에 보기

| # | 시대 | 기간 | 커밋 | 이 시대가 남긴 것 |
| --- | --- | --- | ---: | --- |
| 1 | 씨앗과 휴면 | 2025-11-13 ~ 2026-04-22 | 4 | 타당성 조사만. 이후 5개월 정지 |
| 2 | PID 1 진입 | 2026-04-23 ~ 04-30 | 72 | 재개 당일 native `/init` PID 1 실증. 모듈 경계 확정 |
| 3 | 콘솔화 | 2026-05-02 ~ 05-08 | 114 | `0.9.0`~`0.9.59`. remote shell, 앱 계층, long soak, 하드닝 |
| 4 | 두 축 분리 | 2026-05-09 ~ 05-18 | 136 | flash축/연구축 분리. 호스트 하네스와 broker |
| 5 | Wi-Fi 대장정 | 2026-05-19 ~ 06-06 | 1,754 | native WLAN association·DHCP·IP 통신 도달. 최대 난관 |
| 6 | 계약 기반 운영 | 2026-06-07 ~ 06-13 | 319 | `AGENTS.md`·`GOAL.md`·`tests/` 도입. 운영 성격 전환 |
| 7 | 하드웨어 스택 | 2026-06-14 ~ 06-27 | 903 | 오디오 → 비디오 → 입력 → GPU 직접 렌더 |
| 8 | 커널 REPL과 Debian | 2026-06-28 ~ 07-05 | 608 | 런타임 커널 호출 증명, 자가 플래시, Debian PID 1/SSH |
| 9 | 두 번째 기기와 프로세스 | 2026-07-06 ~ 07-31 | 914 | S22+ 리빌드 커널 부팅, `/init` exec 수용, 위험등급 정식화 |
| 10 | 세 기기 병행과 공개 | 2026-08-01 ~ 09-02 | 930 | S20+ 합류, OSS 표면, USB 프론티어 심층 규명 |

---

## 제1기 — 씨앗과 휴면

**2025-11-13 ~ 2026-04-22 · 커밋 4**

저장소 이름은 `A90_5G_rooting`이었고, 대상은 Galaxy A90 5G 하나였습니다. 벤더
커널 위에 정적 `/init`를 올릴 수 있는지에 대한 문헌 조사와 문서화만
이루어졌습니다(Phase 0). 이후 **약 5개월간 커밋이 없습니다.**

이 공백은 프로젝트 서술에서 지워야 할 흠이 아니라, 재개 시점에 방향이 크게
정리되어 돌아온 이유이기도 합니다.

---

## 제2기 — PID 1 진입

**2026-04-23 ~ 04-30 · 커밋 72**

재개 당일에 근본 가정이 닫혔습니다. Stage 0 기준점 캡처 → Stage 1 → Stage 2 →
**Stage 3에서 native Linux `/init`가 PID 1로 진입**했습니다. 스톡 Samsung
Linux 4.14.190 벤더 커널 위에서입니다.

같은 주에 프로젝트 정체성이 바뀝니다. 04-25 커밋
`Reframe project around native init userspace` — 목표가 "루팅"에서 **"벤더 커널
위의 자체 native userspace"**로 재정의됩니다. 저장소 이름이 실제로 바뀌는 것은
이보다 3개월 뒤지만, 방향 전환은 여기입니다.

이 시대에 확립된 것:

- serial console과 host bridge, sysfs·input 프로브, 화면 없이 물리 버튼만으로
  조작하는 blind menu
- `cmdv1` / `cmdv1x` framed shell 프로토콜 — 이후 모든 호스트 툴링의 공통 채널
- HUD, KMS/draw, display 캘리브레이션
- `v80`~`v87` 모듈 분할로 **현재까지 유지되는 모듈 경계** 확정:
  `init_main` / `util`·`log`·`timeline`·`dev`·`storage` /
  `console`·`shell`·`cmdproto`·`run` / `metrics`·`kms`·`draw`·`hud`·`input`·`menu`

---

## 제3기 — 콘솔화

**2026-05-02 ~ 05-08 · 커밋 114**

`0.9.0`(v100) remote shell 프로토타입부터 `0.9.59`(v159)까지, **사이클과 실제
flash가 1:1로 움직인 유일한 시기**입니다. 진입점 확보가 끝났으니 이제 반복
운용 가능한 콘솔로 만드는 단계입니다.

- 서비스 매니저 뷰, 진단 번들, 앱 계층 분리(about / displaytest / inputmonitor /
  cpustress)
- BusyBox 1.36.1 정적 빌드와 toybox 폴백 — 단, native PID 1 셸은 BusyBox에
  의존하지 않도록 유지
- long soak 계층: 기반 → 상태 → 상관 → 슈퍼바이저 → 호스트 단절 분류기,
  전력·발열 추세
- 외부 보안 리뷰 지적을 받아 하드닝 배치 1~6 (`0.9.24`~`0.9.26`)
- 커널 능력 인벤토리, pstore·watchdog·tracefs 타당성

버전 두 축(실제 flash `0.9.x` vs 연구 사이클 `vNNN`)의 규칙은
[`../operations/VERSIONING_POLICY.md`](../operations/VERSIONING_POLICY.md)와
[`VERSIONING.md`](VERSIONING.md)를 따릅니다. 버전별 이력은
[`../../CHANGELOG.md`](../../CHANGELOG.md)가 정본입니다.

---

## 제4기 — 두 축 분리와 호스트 하네스

**2026-05-09 ~ 05-18 · 커밋 136**

`v159` 이후 **숫자 버전과 연구 사이클이 분리**됩니다. 실제 flash는 드물게,
연구 사이클은 독립적으로 진행하는 구조입니다. flash가 비싸고 위험한 동작이라는
인식이 운영에 반영된 첫 지점입니다.

- `v160`~`v169` 안정성 축: NCM TCP, 스토리지 IO, 프로세스 동시성, 스케줄러
  지연, USB 복구
- `v170`~`v177` 호스트 하네스: observer API, module runner, evidence bundle,
  long-run supervisor, safety gate
- `v185`~`v195` communication broker: 프로토콜, 백엔드, 감사, 인증 하드닝
- `v232`~`v241`에서 Android linker·property·namespace 재현 시도 → linker
  early-abort 호출지점 매핑

마지막 항목이 다음 시대의 진입로입니다. Wi-Fi를 켜려면 Android 런타임의 일부를
native 환경에서 흉내내야 한다는 사실이 여기서 드러납니다.

---

## 제5기 — Wi-Fi 대장정

**2026-05-19 ~ 06-06 · 커밋 1,754 (전체의 30%)**

프로젝트 최대 난관입니다. Qualcomm WLAN 스택은 커널 드라이버 하나로 끝나지
않고 CNSS ↔ QRTR ↔ WLFW ↔ ICNSS ↔ 모뎀/eSoC ↔ PMIC가 서로를 기다리는
구조인데, 이걸 Android 프레임워크 없이 손으로 재현해야 했습니다.

주요 경유지:

- private property namespace 증명, execns private Binder devnode, VNDK linker
  경로, VINTF Wi-Fi 선언 수집
- native Wi-Fi SELinux 핸드오프 증명, 정책 로드, scan-only 게이트
- 모뎀 서브시스템 hold/offlining, QRTR 등록, service-manager 순서 규명
- SSCTL boot proof (`0.9.65`~`0.9.67`), qrtr-ns boot hook (**`0.9.68` / v724,
  2026-05-24 — 현재까지 A90에 flash된 마지막 이미지**)
- peripheral manager 경계 추적, per-proxy 타이밍 단축(2159ms → 800ms),
  mdm_helper SELinux 컨텍스트 수리, eSoC 트리거 경로
- PMIC pinctrl·GPIO 재현, WLAN-PD DIAG 세션, macloader 게이트

**결과 (PROVED, run-scoped):** 서로 분리된 bounded experiment에서 내부
ICNSS/qcacld WLAN 경로가 association → DHCP → IP traffic까지 도달했습니다.
2026-06-05에 native `wlan0` link-up과 최소 스캔 게이트가 닫혔고, 06-06에 connect와
ping 검증이 활성화됐습니다.

- 호스트 분석: [`../reports/WLAN0_ASSOCIATION_REGULATORY_HOST_ANALYSIS_2026-06-05.md`](../reports/WLAN0_ASSOCIATION_REGULATORY_HOST_ANALYSIS_2026-06-05.md)
- 베이스라인 QA hold: [`../reports/NATIVE_INIT_WIFI_BASELINE_QA_HOLD_2026-06-06.md`](../reports/NATIVE_INIT_WIFI_BASELINE_QA_HOLD_2026-06-06.md)
- 이후 소유권 증거: [`../reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md`](../reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md)

이 시대가 남긴 방법론적 교훈은 A90 페이지에 남아 있습니다. 긴 우회(외부
SDX50M/eSoC/PCIe 추격) 끝에 실제 게이트는 **내부 모뎀 경로**였다는 것이고,
이 "잘못된 레이어를 한참 추격 → 진짜 게이트 발견 → 안전 체크포인트 남기고
닫음" 패턴은 이후 모든 에픽에서 반복됩니다.

---

## 제6기 — 계약 기반 운영 도입

**2026-06-07 ~ 06-13 · 커밋 319**

Wi-Fi가 닫힌 직후 워크스페이스를 재구성하고, transport 계층을 공통화하고,
Wi-Fi 자동연결과 HUD를 제품화합니다. 그리고 **2026-06-12에 프로젝트 성격이
바뀝니다.**

같은 날 `AGENTS.md`, `GOAL.md`, `tests/`가 함께 생깁니다. 이때부터:

- 작업은 `STATE → SELECT → DESIGN → IMPLEMENT → STATIC VALIDATE → DEVICE →
  REPORT → COMMIT` 사이클을 따릅니다
- 모든 claim에 증거 등급(PROVED / observed / designed / unproved)이 붙습니다
- 기기 작업은 binding target contract 없이는 열리지 않습니다
- 06-13에 회귀 테스트가 대량 투입되어 host-only 검증 층이 생깁니다

직전까지 커널 관측 능력의 한계를 분류하던 흐름(V2191, BPF, JOPP/ROPP slide,
kallsyms 심볼화)이 여기서 커널 내부 연구로 이어집니다.

**이 시점 이후의 모든 결과는 증거 계약 아래에서 생산됐습니다.** 그 이전 결과를
읽을 때는 이 차이를 감안해야 합니다.

---

## 제7기 — 하드웨어 스택

**2026-06-14 ~ 06-27 · 커밋 903**

휴면 상태의 벤더 하드웨어를 한 서브시스템씩 깨우는 시대입니다.

**USB 가젯 런타임 제어** — `usb status`, mass-storage expose/remove, identity
rodata 패치, multi-LUN. v2321이 롤백 체크포인트로 승격됩니다.
[`../reports/NATIVE_INIT_V2321_USB_CLEAN_IDENTITY_RODATA_LIVE_2026-06-14.md`](../reports/NATIVE_INIT_V2321_USB_CLEAN_IDENTITY_RODATA_LIVE_2026-06-14.md)

**오디오 / ADSP** — 이 시대의 최대 난관. tinyalsa 인벤토리에서 시작해 ACDB
(오디오 캘리브레이션 DB) 재현으로 들어갑니다. cal12 mem-handle 블로커,
send-v5 데드락 역공학, AFE 토폴로지 게이트를 거쳐 SET-cal 캡처·리플레이
경로가 완성됩니다.

> **PROVED (run-scoped):** bounded live run에서 SM8150 audio card를
> materialize하고, 필요한 calibration과 route를 replay하고, 내장 스피커로 PCM
> write/drain을 수행한 뒤 route를 cleanup하고 exact rollback 경로로
> 복귀했습니다.
> [`../reports/NATIVE_INIT_V2814_AUDIO_CORE_PROMOTION_CANDIDATE_MARKER_LOSS_TOLERANT_LIVE_2026-06-19.md`](../reports/NATIVE_INIT_V2814_AUDIO_CORE_PROMOTION_CANDIDATE_MARKER_LOSS_TOLERANT_LIVE_2026-06-19.md)

**비디오와 입력** — 프레임 스트리밍, A/V 싱크, 압축 스트림 포맷. 이어서
doomgeneric 이식과 시리얼 기반 입력 브리지, DRM plane·pageflip 케이던스
최적화. 화면·입력·오디오가 동시에 도는 상태가 여기서 처음 만들어집니다.

**GPU** — Adreno 직접 제어. 셰이더 출력, 캐시 무효화, 클립 가드밴드를 거쳐
KMS 위 삼각형 렌더와 compute 셰이더, 2D 텍스처까지 도달합니다.

**커널 보안 트랙 개시** — 06-27에 PROCA/FIVE UAF 후보가 기록되고 Tier-0에서
실증 트리거가 확인됩니다(비치명, 기기 생존). 수동 UAF 재사용 제어성은
**NEGATIVE**로 닫힙니다.
[`../reports/KERNEL_SECURITY_TIER2_KASAN_LITE_RECLAIM_DUMP_2026-06-28.md`](../reports/KERNEL_SECURITY_TIER2_KASAN_LITE_RECLAIM_DUMP_2026-06-28.md)

---

## 제8기 — 커널 REPL과 Debian

**2026-06-28 ~ 07-05 · 커밋 608**

06-28에 **RKP 하에서 정적 커널 `.text` 패치가 부팅됨(VIABLE)**이 기록되고,
목표가 Tier-2 런타임 커널 REPL로 재차터됩니다. kallsyms 추출기의 ULEB128 루트
디코드를 고친 뒤 커널 함수를 런타임에 호출하고 계약을 증명하는 체계가
만들어집니다(`filp_open`, `kernel_read`, `memchr`, `kmemdup` 등 다수).

이 시대에는 오퍼레이터 정정이 여러 번 기록됩니다 — "블로커는 할당자 ABI가
아니라 MAP 오라벨", "맵 감사가 UNSOUND하니 그걸로 디코더를 재작성하지 말 것",
"resident-session은 1-타깃이 아니라 세션을 PACK해야 함". **틀린 방향을 문서에
남기고 되돌리는 방식**이 이때 자리잡습니다.

병행해서 self-dd 자가 플래시가 fail-closed 가드와 폴트 주입 테스트를 갖추고
호스트 자가 플래시 라이브 PASS에 도달합니다.

그리고 server-distro 에픽이 열립니다:

- D0 Debian rootfs 빌더와 호스트 스테이징 → **D1 chroot MVP** → **D2 chroot 내
  SSH** → D4C userdata 포맷·채우기
- WSTA 시리즈: Debian STA Wi-Fi, 패킷 필터 컨트롤 플레인, 아웃바운드 터널,
  seccomp 로더, durable HUD presenter, 콜드부팅 지속성
- [`../reports/A90_PHASE3_DEBIAN_NETWORK_SSH_OWNERSHIP_H0_2026-08-03.md`](../reports/A90_PHASE3_DEBIAN_NETWORK_SSH_OWNERSHIP_H0_2026-08-03.md)

Debian PID 1 자체의 증명은 이후 7월 말에 확정됩니다:
[`../reports/A90_V3404_D3_WORK_COPY_POSTMORTEM_DEBIAN_PID1_PROVEN_2026-07-31.md`](../reports/A90_V3404_D3_WORK_COPY_POSTMORTEM_DEBIAN_PID1_PROVEN_2026-07-31.md)

---

## 제9기 — 두 번째 기기와 프로세스 정식화

**2026-07-06 ~ 07-31 · 커밋 914**

07-06에 **Galaxy S22+ (`SM-S906N`, FYG8)**가 합류합니다. 방법론이 기기에
종속되지 않는지 검증하는 것이 목적입니다. 시작은 순탄하지 않았습니다 —
recovery loop, disabled vbmeta 블로커, 공장초기화 복구를 거칩니다.

**M 시리즈 (부팅 증거 채널 확보)** — Magisk 부팅 캡처, pstore/ramoops 시도,
그리고 호스트 발견: *진짜 지속성은 mainline ramoops가 아니라 삼성
`sec_debug`(debug_level)*. EUD는 TZ 게이트(rc:-22)로 닫히고 DTS-exact QMP-PHY
전력 기질로 피벗합니다.

**O 시리즈 (양성 대조군)** — 스톡 ACM이 실제로 동작함을 먼저 증명해 관측
장비 자체를 검증합니다.
[`../reports/NATIVE_INIT_V3403_S22PLUS_O0_STOCK_USB_CONTROL_LIVE_2026-07-10.md`](../reports/NATIVE_INIT_V3403_S22PLUS_O0_STOCK_USB_CONTROL_LIVE_2026-07-10.md)

**R 시리즈 (커널 리빌드)** — Full-LTO R1, static R2를 닫고:

> **PROVED:** source-matched 리빌드 커널이 실제 기기에서 Android를
> 부팅했습니다.
> [`../reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md`](../reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md)

> **PROVED:** direct native candidate가 현재 PID 1 상태에서 수용된 `/init`
> exec에 도달했습니다.
> [`../reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md`](../reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md)

**같은 시기에 안전 체계가 정식화됩니다.** 07-21에
[`../operations/DEVICE_ACTION_RISK_TIERS.md`](../operations/DEVICE_ACTION_RISK_TIERS.md)와
[`../operations/DEVICE_ACTION_PROCESS_V2.md`](../operations/DEVICE_ACTION_PROCESS_V2.md)가
생기면서 D0/D1/F1 위험 등급과 boot-only F1 절차, 재사용 가능한 F1 어댑터가
공통 계층이 됩니다. 재개 가능한 Odin transition core, one-shot 라이브 정책,
소비된 후보의 영구 폐기 규칙도 이때 자리잡습니다.

07-19에 저장소 이름이 `A90_5G_rooting`에서 **`android-native-init-lab`**으로
바뀝니다. 단일 기기 프로젝트의 종료입니다.
[`../reports/REPOSITORY_RENAME_ANDROID_NATIVE_INIT_LAB_2026-07-19.md`](../reports/REPOSITORY_RENAME_ANDROID_NATIVE_INIT_LAB_2026-07-19.md)

07-24부터 **P 시리즈 USB 프론티어**가 시작됩니다. SSUSB 타임아웃이 처음
프론티어로 기록되고, 이것이 현재까지 이어집니다. UCSI 레이스, PMIC GLINK 활성화
경로, kprobe 기반 전기적 경계 측정이 이 시기에 닫힙니다.

증거 색인:
[`../reports/S22PLUS_FYG8_NATIVE_PID1_USERSPACE_EXPERIMENT_EVIDENCE_LEDGER_2026-07-22.md`](../reports/S22PLUS_FYG8_NATIVE_PID1_USERSPACE_EXPERIMENT_EVIDENCE_LEDGER_2026-07-22.md)

---

## 제10기 — 세 기기 병행과 공개

**2026-08-01 ~ 2026-09-02 · 커밋 930**

세 갈래가 동시에 굴러가는 현재 구조입니다.

### A90 — self-built kernel 트랙

resident install과 reviewed D1 fast loop가 활성화되고, switch_root가 반복
증명됩니다. 08-10에 **H15~H17이 read-only UFS 직접 handoff를 검증**하면서 이전의
수 GB SD work-copy 의존이 제거됩니다.

08-12의 devtmpfs 노출 사고를 계기로 이전 공유 네임스페이스 설계가 폐기되고,
더 작은 **isolated Debian** 아키텍처가 선택됩니다:
[`../plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`](../plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md)

08-21~23에 self-built kernel 트랙이 진전합니다. exact Snapdragon LLVM 10.0.7을
확보해 변경되지 않은 CFP/JOPP/ROPP 구성을 재현하고, H34에서 `rtic_mp`가 누락된
채 stale stock RTIC DTB가 유지된 아티팩트 불일치를 규명하고, public MPGen
locator를 수리해 deterministic 재현에 도달합니다.

- [`../reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H28_H0_2026-08-21.md`](../reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H28_H0_2026-08-21.md)
- [`../reports/A90_H34_RTIC_MP_STALE_DTB_HOST_CAUSAL_ANALYSIS_H0_2026-08-22.md`](../reports/A90_H34_RTIC_MP_STALE_DTB_HOST_CAUSAL_ANALYSIS_H0_2026-08-22.md)
- [`../reports/A90_RTIC_LOCATOR_REPAIRED_DETERMINISTIC_REBUILD_H0_2026-08-23.md`](../reports/A90_RTIC_LOCATOR_REPAIRED_DETERMINISTIC_REBUILD_H0_2026-08-23.md)

**이는 host-side 구조적 일치(PROVED)이며 boot result가 아닙니다.** H35 패키지는
bounded canary로 리뷰됐지만 live transaction이 candidate write 이전에 실패해
**unproved**이며 replay할 수 없습니다:
[`../reports/A90_H35_NATIVE_RECOVERY_COMMAND_PREWRITE_FAILURE_2026-08-23.md`](../reports/A90_H35_NATIVE_RECOVERY_COMMAND_PREWRITE_FAILURE_2026-08-23.md)

### S22+ — USB 프론티어 심층 규명

P3.xx가 이어집니다. 이 시대의 두 발견이 프론티어를 옮겼습니다.

**첫째, 08-11에 의심이 이동합니다.** in-kernel 경로가 refute된 뒤 Max77705
D+/D− mux가 후보로 올라오고, 08-17~20에 집중 규명이 이루어집니다: mux는
modprobe로 전환된다, 부트로더가 COM_OPEN을 쓰므로 상속 전제는 refuted,
CONTROL1 다섯 값의 의미, RDX 브링업은 5회 호출이고 실패한 MUIC 프로브는
조용하다, NoAutoIBUS는 재부팅을 생존한다.

**둘째, 08-21에 관측 기반 자체의 결함이 드러납니다** — *감사하던 vmlinux가
실제로 flash된 Image의 것이 아니었습니다.* 후보 런타임은 materialized
sources에서 읽어야 한다는 규율이 여기서 나옵니다.

현재 정적 폐쇄와 종합 감사:

- [`../reports/S22PLUS_FYG8_P319_SSUSB_UDC_PLAN_CLOSURE_H0_2026-08-24.md`](../reports/S22PLUS_FYG8_P319_SSUSB_UDC_PLAN_CLOSURE_H0_2026-08-24.md)
- [`../reports/S22PLUS_FYG8_USB_COMPREHENSIVE_INVESTIGATION_AUDIT_H0_2026-08-30.md`](../reports/S22PLUS_FYG8_USB_COMPREHENSIVE_INVESTIGATION_AUDIT_H0_2026-08-30.md)

08-29에는 S22+에 한정된 **비례적 pre-F1 자율 레인**이 정의됩니다. 이 권한은
다른 타깃으로 이전되지 않습니다.

### S20+ — 세 번째 기기

08-12에 **Galaxy S20+ 5G (`SM-G986N`)**가 격리된 D0 온보딩 대상으로
합류합니다. A90·S22+와 달리 처음부터 계약·위험등급 체계 아래에서 시작한
유일한 기기입니다.

- exact 온보딩: [`../reports/S20PLUS_G986N_ONBOARDING_D0_H0_2026-08-12.md`](../reports/S20PLUS_G986N_ONBOARDING_D0_H0_2026-08-12.md)
- 스톡 아티팩트: [`../reports/S20PLUS_G986N_STOCK_ARTIFACT_ACQUISITION_H0_2026-08-13.md`](../reports/S20PLUS_G986N_STOCK_ARTIFACT_ACQUISITION_H0_2026-08-13.md)
- 단계 설계: [`../plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md`](../plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md)
- native canary N1: [`../reports/S20PLUS_G986N_NATIVE_CANARY_N1_H0_2026-08-15.md`](../reports/S20PLUS_G986N_NATIVE_CANARY_N1_H0_2026-08-15.md)
- USB substrate: [`../reports/S20PLUS_G986N_NATIVE_USB_SUBSTRATE_H0_D0_2026-08-16.md`](../reports/S20PLUS_G986N_NATIVE_USB_SUBSTRATE_H0_D0_2026-08-16.md)
- N3-U0 (dormant): [`../reports/S20PLUS_G986N_N3U0_EVIDENCE_EXECUTION_INTEGRATION_H0_2026-08-20.md`](../reports/S20PLUS_G986N_N3U0_EVIDENCE_EXECUTION_INTEGRATION_H0_2026-08-20.md)
- 자율 연구 인프라 (비활성): [`../reports/S20PLUS_G986N_AUTONOMOUS_RESEARCH_SESSION_H0_2026-08-21.md`](../reports/S20PLUS_G986N_AUTONOMOUS_RESEARCH_SESSION_H0_2026-08-21.md)

08-31에 boot recovery canary F1과 TWRP T2 recovery owner가 활성화되고, 09-01에
TWRP boot identity D0가 증명됩니다. **N3-U0 ACM 경로와 자율 연구 인프라는
host-qualified 상태이지만 의도적으로 활성화되지 않았습니다.**

### 공개 표면

08-07에 OSS 표면이 정리됩니다 — NOTICE 서드파티 목록 정정과 mkbootimg 라이선스
동봉, `.github` 구성, 공개 트리 식별자 정리 정책. 08-09에는 host 테스트
스위트의 베이스라인과 실패 분류 체계가 기록되고, 08-10에 한국어 README가
완성됩니다.

---

## 기기 합류 지점

| 기기 | 합류 | 합류 시점의 저장소 상태 |
| --- | --- | --- |
| Galaxy A90 5G (`SM-A908N`) | 2025-11-13 | 저장소 자체가 이 기기로 시작 |
| Galaxy S22+ (`SM-S906N`) | 2026-07-06 | 계약 체계 도입 후, 위험등급 정식화 직전 |
| Galaxy S20+ 5G (`SM-G986N`) | 2026-08-12 | 계약·위험등급·Process v2가 모두 갖춰진 뒤 |

세 기기는 서로에게 authority를 넘기지 않습니다. 한 기기의 결과가 다른 기기의
device 작업을 승인하는 일은 없습니다 (`AGENTS.md`).

기기별 현재 상태와 프론티어는 [`../devices/README.ko.md`](../devices/README.ko.md)를
보십시오.

---

## 이 문서가 하지 않는 것

- **현재 상태를 말하지 않습니다.** 현재 프론티어와 다음 bounded unit은
  `GOAL.md`(S22+), `GOAL_A90.md`, `GOAL_S20PLUS.md`가 기준입니다.
- **device authority를 부여하지 않습니다.** 어떤 기기 작업도 이 문서를 근거로
  열리지 않습니다. `AGENTS.md`와 선택된 binding target contract만이 권한을
  만듭니다.
- **run 결과를 합치지 않습니다.** 위의 PROVED 표기는 각각 해당 run의 범위
  안에서만 유효합니다.
- **일 단위 이력을 담지 않습니다.** `git log`가 정본입니다.

## 관련 문서

- [`../devices/README.ko.md`](../devices/README.ko.md) — 기기별 진행 상황과 증거 taxonomy
- [`../../CHANGELOG.md`](../../CHANGELOG.md) — native init / boot image 버전 이력
- [`../operations/CAMPAIGN_LEDGER_A90.md`](../operations/CAMPAIGN_LEDGER_A90.md) ·
  [`../operations/CAMPAIGN_LEDGER_S22PLUS.md`](../operations/CAMPAIGN_LEDGER_S22PLUS.md) — run 결과 원장
- [`VERSIONING.md`](VERSIONING.md) — 버전 축 분리 규칙
- 종료된 선행 문서: [`../archive/overview/PROGRESS_LOG_2026-04-23_2026-05-02.md`](../archive/overview/PROGRESS_LOG_2026-04-23_2026-05-02.md) ·
  [`../archive/overview/PROJECT_STATUS_A90_THROUGH_2026-06-19.md`](../archive/overview/PROJECT_STATUS_A90_THROUGH_2026-06-19.md)
