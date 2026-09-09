# Android Native Init Lab — 한국어 상세 문서

[English](README.md) · **한국어**

> [`README.md`](README.md)가 이 저장소 공개 진입점의 **구조 정본**이다. 이 문서는
> 그 절 구조를 따르되 문장 단위 번역본은 아니며, 한국어 운영·연구 설명을 더 자세히
> 유지한다. 사실과 현재 상태의 권위는 각 GOAL·campaign ledger·리포트·계약에 있다.

이 저장소는 단순 rooting, 보안 우회, 또는 exploit 실습 프로젝트가
아닙니다. 저장소 소유자가 소유·관리하는 Android 기기의 vendor
boot chain과 kernel 위에 custom static `/init`(PID 1)와 최소 Linux-style
runtime을 구성·검증하는 다기기 로컬 연구/문서화 작업 공간입니다.

현재 활성 대상은 Samsung Galaxy A90 5G, Galaxy S22+, Galaxy S20+ 5G이며, 공통 연구 축은
특정 모델이 아니라 **Android vendor kernel 기반의 custom native PID 1**입니다.
프로젝트는 해당 진입점을 안정화하고 반복 운용 가능한 임베디드 콘솔과
서버형 userspace로 확장합니다.

<p align="center">
  <img src="docs/images/a90/01-debian-pid1-appliance.jpg" width="36%" alt="A90에서 PID 1으로 동작하는 Debian 12.14">
  <img src="docs/images/a90/boot-sequence.gif" width="41%" alt="스톡 Linux 4.14 벤더 커널에서 부팅하는 A90 네이티브 init">
</p>

<p align="center"><sub>
서로 다른 빌드의 서로 다른 두 A90 실행을 실제 기기에서 기록한 것.<br>
<b>왼쪽</b> — ext4 루트 위에서 <code>/usr/sbin/init</code>이 PID 1으로 도는 Debian 12.14.
로컬 USB-NCM 링크의 Dropbear SSH와, 아웃바운드 Cloudflare Quick Tunnel로도
접근된 루프백 HTTP 서비스.<br>
<b>오른쪽</b> — 스톡 삼성 Linux 4.14 벤더 커널 위의 네이티브 init 콜드 부팅.
삼성 스플래시부터 USB 시리얼 가젯이 올라오고 HUD가 뜨기까지.<br>
<a href="docs/devices/A90_VISUAL_EVIDENCE.ko.md">A90 시각 증거와 실행 리포트 더 보기 →</a>
</sub></p>

## 왜 이 접근인가

벤더 지원이 끝난 Android 기기는 소프트웨어 스택만 낡았을 뿐 하드웨어는 그대로
동작합니다. 문제는 그 하드웨어의 드라이버가 **vendor kernel 안에만** 존재한다는
점입니다. 선택지는 보통 셋인데 각각 비용이 다릅니다.

| 경로 | 하드웨어 지원 | 비용 |
| --- | --- | --- |
| stock Android 유지 | 좋음 | Android 프레임워크 전체가 따라옴 |
| 커스텀 ROM | 좋음 | 여전히 Android이고, 여전히 프레임워크 |
| 메인라인 Linux 포팅 | 초기엔 나쁨 | 모델별 GPU/디스플레이/USB/전원 bring-up |

이 프로젝트는 그 사이의 빈칸을 탐색합니다 — **vendor kernel + native Linux-style
userspace**. 벤더 드라이버는 계속 동작하고, Android 프레임워크는 사라지며,
제어는 PID 1부터 시작합니다.

## 이 기기들을 넘어 왜 의미가 있는가

기기에 의존하지 않는 산출물은 개별 기기 포팅이 아니라 **방법**입니다.

잠긴 하드웨어의 bring-up 작업은 대개 즉흥적이고, 기록이 남지 않으며, 때로는
파괴적입니다. 이 저장소는 그 작업을 감사 가능하고 반복 가능하게 만들려는
시도입니다.

- 모든 동작을 위험 등급으로 분류하는 결속 안전 계약 [`AGENTS.md`](AGENTS.md) —
  host 전용, 연결된 읽기 전용, 일시적 제어, boot 전용 전송
- 사전 선언된 롤백, no-replay 규칙, 대상 격리. 실패한 실험이 조용히 기기를
  벽돌로 만들거나 다른 대상을 오염시킬 수 없습니다
- 재현 가능한 candidate identity, 증거 원장, 그리고 기기에 손대기 전에 반드시
  통과해야 하는 host 측 검증

[`docs/operations/DEVICE_ACTION_RISK_TIERS.md`](docs/operations/DEVICE_ACTION_RISK_TIERS.md)와
[`docs/operations/DEVICE_ACTION_PROCESS_V2.md`](docs/operations/DEVICE_ACTION_PROCESS_V2.md)를
참고하십시오.

## 현재 범위

[기기별 진행 상황](docs/devices/README.ko.md)에서 세 기기의 성과, 현재
프론티어, 미증명 경계를 같은 증거 taxonomy로 비교할 수 있습니다.

- **Galaxy A90 5G (`SM-A908N`)**: custom native PID 1, ACM/NCM, native Wi-Fi와
  audio, 그리고 bounded Debian PID 1/SSH/display 결과가 있습니다. 현재 작업은
  H41 rollback/health 종결이며 isolated-Debian 서버 작업은 일시 중지돼 있습니다.
- **Galaxy S22+ (`SM-S906N`, FYG8)**: 인증된 native-PID1 USB 경로는 P348까지
  제한된 읽기 전용 셸 작업을 뒷받침합니다. 이어진 P353~P361 디스플레이 시리즈는
  cached 버퍼의 반복 framebuffer 선택에 도달했고, 깨끗한 출력은 운영자가 관측하고
  사진·클립이 보강했습니다. 인증된 dispatch와 정확한 rollback은 그 시각 관측과
  분리해 증명됩니다. P363과 P364는 네이티브 Download 제어에 닿기 전에
  `NO_PROOF_OBSERVER`로 닫혔습니다. P365는 ARM64 준비 경로 결함을 고친 뒤 더 멀리
  나아가, 인증된 진단이 수락된 Download CONTROL에 도달했고 운영자는 화면이 꺼진 뒤
  물리 개입 없이 Download 모드에 도달하는 것을 관측했습니다. 다만 그 제어가 해당
  진입을 유발하거나 완료했다는 bounded machine proof는 여전히 미증명입니다. 이어진
  P375와 P376은 성공으로 닫혔고, 인증된 루트 명령 콘솔과 네이티브 PID 1이 직접 그리는
  최소 부팅 HUD를 더했습니다. 운영자는 패널에서 그 텍스트와 증가하는 uptime을
  관측했으며, 기계적 픽셀 증명은 주장하지 않습니다. 완료된 그 범위에는 기능 버전
  **v0.1.0**이라는 이름을 붙였고 변경되지 않은 P376 산출물에 대응시켰습니다. 검증된
  한정 범위의 이름일 뿐, 상주 설치나 반복 부팅·장시간 운용의 주장이 아닙니다. P349의
  RAM 작업공간·1시간 witness 단위는 host 검증된 상태로 보류돼 있습니다.
- **Galaxy S20+ 5G (`SM-G986N`)**: exact onboarding, resident Magisk root,
  retained T2 TWRP recovery가 확립됐습니다. P0 V3 native-PID1 시도에서는 exact
  ACM banner를 얻지 못했고 정상 Magisk rollback으로 종료했습니다. Native PID 1은
  미증명이며 현재는 초기 부팅 관측 경로를 연구합니다.

이 요약의 S22+ 항목은 2026-09-09, 다른 대상은 2026-09-05 확인한 기록 기준입니다. 기기별 페이지에서 인정된 결과의
근거를 확인하고, 바뀌는 프론티어와 실행 요건은 각 GOAL과 target contract를 따릅니다.

공용 소스는 `workspace/public/src/` 아래에 둡니다. 대상 전용 소스, 헬퍼,
리포트, rollback identity, 안전 게이트는 명시적으로 분리합니다. 한 대상의
결과가 다른 대상의 기기 작업을 승인하는 일은 없습니다.

### 만들고 있는 것

현재 메인 목표는 `Android vendor kernel 위의 자체 native userspace`를
반복 가능한 방법으로 만드는 것입니다.

구조는 다음과 같습니다.

```text
vendor bootloader
  -> stock or source-matched rebuilt Android vendor kernel
    -> custom static /init (PID 1)
      -> serial shell
      -> display HUD
      -> input/button handling
      -> sensor/sysfs reader
      -> logging/runtime layer
      -> optional BusyBox/network/SSH layer
```

즉 이 프로젝트는 더 이상 단순히 “Linux 진입이 가능한가?”를 확인하는 단계가 아니라,
확보한 진입점을 기반으로 **반복 운용 가능한 최소 Linux 콘솔/서버 환경**을 만드는 단계입니다.

장기 모듈 경계는 아래처럼 잡습니다.

- `init_main`: PID 1 부팅 흐름만 담당
- `util/log/timeline/dev/storage`: boot/runtime 기반 계층
- `console/shell/cmdproto/run`: serial 제어와 명령 실행 계층
- `metrics/kms/draw/hud/input/menu`: 센서 snapshot, 화면, 버튼 입력, device UI 계층
- `usb_gadget/netservice`: USB ACM/NCM, TCP control, 서버형 접근 계층

- Android vendor kernel과 기기 전용 driver를 활용하는 native userspace 실험
- boot ramdisk의 `/init`를 교체해 PID 1부터 직접 구성하는 작업
- USB serial, KMS display, input, battery/thermal sysfs를 사용하는 임베디드 콘솔
- 필요한 관측 능력을 추가하는 source-matched vendor-kernel rebuild 및 검증
- 장기적으로 BusyBox, USB network, dropbear SSH 같은 서버형 구성으로 확장할 수 있는 기반

### 현재 frontier의 정본

이 README는 확립된 결과와 기능 버전만 요약합니다. **자주 바뀌는 정확한 현재
frontier, 다음 bounded unit, live authorization 여부는 각 GOAL 문서가 정본이며**
이 문서에 복제하지 않습니다.

- [`GOAL.md`](GOAL.md) — S22+ 현재 상태와 다음 bounded unit
- [`GOAL_A90.md`](GOAL_A90.md) — A90 현재 상태와 다음 bounded unit
- [`GOAL_S20PLUS.md`](GOAL_S20PLUS.md) — S20+ 현재 상태와 다음 bounded unit

기기별 진행 상황의 읽기 쉬운 요약은
[`docs/devices/README.ko.md`](docs/devices/README.ko.md)에 있습니다. 기기별 다음
작업은 각각의 rollback identity와 [`AGENTS.md`](AGENTS.md)의 승인 경계를
독립적으로 만족해야 하며, 공용 F1 구조는 Device Action Process v2입니다.

## 이 프로젝트가 아닌 것

- 일반 Debian/Ubuntu/Red Hat 배포판 포팅 완료 상태가 아님
- Android framework, 앱, SurfaceFlinger, Zygote를 복구하는 프로젝트가 아님
- 메인라인 커널 포팅 또는 범용 Android 커스텀 ROM 프로젝트가 아님
- 카메라, 모뎀, GPU 가속 등 vendor userspace 의존 기능을 즉시 지원하는 환경이 아님
- rooting, 우회, exploit 실습 프로젝트가 아님. 여기 있는 어떤 것도 타인의 기기,
  서비스, 계정, 네트워크에 접근하는 방법이 아님

## 작업 검증 방식

작업은 완료 기준이 명시된 bounded unit 단위로 진행합니다. 확보한 증거와 집중된
host 검사에서 시작하고, 변경되지 않은 빌드·검증 결과는 재사용합니다. 독립 검토는
[`AGENTS.md`](AGENTS.md#development-and-commit-discipline)가 지정한 계약·실행·안전
변경에 적용합니다. 기기 검증은 질문이 그것을 요구할 때, 선택된 대상의 복구·승인
규칙 아래에서만 사용합니다. 결과와 근거는 `docs/operations/`의 대상별 원장에
기록합니다.

Codex를 포함한 AI 코딩 에이전트는 같은 경계 안에서 구현과 분석에 사용합니다.
권위는 에이전트가 아니라 계약에 있습니다.

테스트 스위트는 host 전용이며 기기에 접촉하지 않습니다. 변경된 영역부터 실행하고
변경이나 실패가 요구하면 범위를 넓힙니다. 문서만 수정한 경우에는 보통 내용·링크·diff
검사로 충분합니다.

지속적으로 도는 검사는 하나뿐입니다. **Repository boundary** 배지는 공개 트리가
[`docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md`](docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md)의
식별자 경계를 만족한다는 것만 주장합니다. 테스트 스위트 상태가 아닙니다 — 전체
스위트는 소유자 비공개 픽스처에 의존하며 CI에서 실행되지 않습니다.

기기 안전 경계(`/efs`·modem·RPMB·keymaster·keystore·bootloader 계열 쓰기 금지 등)는
[`AGENTS.md`](AGENTS.md)와
[기기 작업 계약 details](docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md)가 정본입니다.

그 계약에 더해, 대상을 가리지 않고 지키는 빌드·주소지정·기록 관행 다섯 가지는
[대상 공통 엔지니어링 불변식](docs/operations/ENGINEERING_INVARIANTS.md)이 정본입니다.
known-good 이미지와 검증된 복구 경로 유지, 인과를 규명해야 하는 런에서의 변수 격리,
새 boot image의 provenance 기록, 파티션 by-name 주소지정, 그리고 원본 증거는 private
공개 요약만 public이라는 원칙입니다.

## 저장소 구조

- `docs/`
  현재 문서 인덱스, 프로젝트 상태, 사이클별 리포트(`docs/reports/`), 다음 작업 목록
- `workspace/public/src/native-init/`
  현재 native init 소스 클로저
- `workspace/public/src/scripts/revalidation/`
  현재 serial bridge, 콘솔, 재검증, 빌드 헬퍼 엔트리포인트
- `workspace/public/archive/`
  루트 경로에서 옮겨온 과거 스크립트와 native-init provenance
- `workspace/private/`
  git에서 제외되는 private 입력, boot image, 빌드 산출물, raw 로그, 시크릿
- `workspace/public/src/third_party/mkbootimg/`
  boot/recovery/vendor_boot 분석과 repack에 쓰는 도구 (AOSP, Apache-2.0)

## 주요 문서

전체 문서 목록과 읽는 순서, 사이클별 리포트는 `docs/README.md`를 정식
인덱스로 한다. 여기서는 자주 여는 진입점만 추린다.

현재 상태 / 연구:

- `GOAL.md` — S22+ frontier와 다음 bounded unit
- `GOAL_A90.md` — A90 frontier와 다음 bounded unit
- `GOAL_S20PLUS.md` — S20+ frontier와 다음 bounded unit
- `AGENTS.md` / `CLAUDE.md` — 기기 작업 절대 안전 경계와 운영 계약
- `docs/module-map/s22plus-fyg8/subsystem-usb.md` — S22+ USB 서브시스템 연구 맵과
  단계별 근거 (현재 frontier·다음 unit 자체는 `GOAL.md` 기준)
- `docs/devices/README.ko.md` — 기기별 진행 상황, 확립된 결과, 미증명 경계
- `docs/overview/PROJECT_HISTORY.ko.md` — 첫 커밋부터 현재까지의 연혁 (서술이며 증거 아님)

운영 / 빌드:

- `docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md` — flash/bridge 절차
- `docs/operations/CLAUDE_NATIVE_INIT_RUNBOOK.md` — 운영 런북
- `docs/operations/VERSIONING_POLICY.md` / `docs/overview/VERSIONING.md` — Run ID, native init version, build tag, helper version, SHA 축 분리 규칙
- `docs/operations/ENGINEERING_INVARIANTS.md` — 대상 공통 빌드·주소지정·기록 불변식
- `docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md` — 공개 트리 식별자 정리 규칙과 boundary check

이력 / 인덱스:

- `CHANGELOG.md` — A90 native-init / boot image의 역사적 이력. 현재 다기기 상태 기록이 아님
- `docs/README.md` — 전체 문서·리포트 인덱스

`docs/plans/NATIVE_LINUX_RECHALLENGE_PLAN.md`와 `docs/plans/REVALIDATION_PLAN.md`는
진입점 확보 이전의 부트체인 재검증 기록으로 보존한다.

## 안전, 범위, 윤리

이 작업은 저장소 소유자가 직접 소유하고 복구 경로를 관리하는 로컬 기기에서만
진행합니다. README와 관련 문서는 제3자 기기, 서비스, 계정, 네트워크를 대상으로 한
접근 방법이나 우회 절차로 해석하지 않습니다.

허용 범위는 다음으로 제한합니다.

- 로컬 기기 연구
- 문서화
- 빌드 문제 해결
- native init/runtime 개발
- 읽기 전용 진단
- 복구 안전성 검증

금지/비목표 범위는 다음을 명확히 포함합니다.

- 무단 접근
- 제3자 대상 공격
- exploit 배포
- 지속성 확보(persistence)
- 악성코드
- 자격 증명 탈취
- 은닉 및 탐지 회피
- 타인 소유 기기 조작

실험 전에는 항상 해당 타깃의 검증된 recovery/Download 경로,
known-good boot/recovery/vbmeta, 로그 보존 경로를 확인하고, 복구 가능성을
해치거나 소유권이 불명확한 대상에는 적용하지 않습니다.

이 저장소에는 실제 플래시 대상 바이너리와 Samsung 전용 이미지가 포함될 수 있습니다.
실험 전에는 항상 현재 boot/recovery/vbmeta 상태와 복구 가능한 known-good 이미지를
확인한 뒤 진행합니다.

## 기여

이 프로젝트에서 쓸모 있는 작업의 대부분은 **기기 없이** 할 수 있습니다 —
분석기, 검증기, 테스트, 문서는 전부 host-only(H0)입니다. 기여 방법과
기기가 필요한 작업의 경계는 [`CONTRIBUTING.md`](CONTRIBUTING.md)를,
보안 관련 제보는 [`SECURITY.md`](SECURITY.md)를 참고하세요.

## 라이선스

이 저장소의 **문서와 스크립트**는 MIT License를 따른다 (루트 `LICENSE` 참고).

단, **Samsung 전용 펌웨어·커널 소스·patched AP/TWRP 이미지 등 proprietary 구성요소는
MIT 적용 대상이 아니며**, 각자의 라이선스를 따르고 정당한 권한 없이 재배포하지 않는다
(루트 `NOTICE` 참고). `workspace/private/inputs/firmware/`,
`workspace/private/backups/`, `workspace/private/inputs/boot_images/*.img` 등에 포함된
벤더 바이너리는 저장소 소유자가 소유·관리하는 로컬 기기 복구/연구 용도로만 보관한다.

공개 트리에 포함된 서드파티 구성요소(AOSP `mkbootimg` 등)는 각자의 라이선스를
따릅니다. 전체 목록은 루트 `NOTICE`에 있습니다.

## 저장소 이름에 관하여

이 저장소는 Galaxy A90 5G가 유일한 대상이던 시절 `A90_5G_rooting`이라는
이름이었다. 연구 범위가 Galaxy S22+와, 기기에 의존하지 않는 재사용 가능한
native PID 1 방법론으로 확장되면서 `android-native-init-lab`으로 이름을 바꿨다.
과거 경로와 대상 전용 `a90_*` 식별자는 기술적·역사적으로 의미가 남아 있는
곳에 한해 그대로 둔다.
