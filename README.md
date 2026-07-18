# Android Native Init Lab

이 저장소는 단순 rooting, 보안 우회, 또는 exploit 실습 프로젝트가
아닙니다. 저장소 소유자가 소유·관리하는 Android 기기의 vendor
boot chain과 kernel 위에 custom static `/init`(PID 1)와 최소 Linux-style
runtime을 구성·검증하는 다기기 로컬 연구/문서화 작업 공간입니다.

현재 활성 대상은 Samsung Galaxy A90 5G와 Galaxy S22+이며, 공통 연구 축은
특정 모델이 아니라 **Android vendor kernel 기반의 custom native PID 1**입니다.
프로젝트는 해당 진입점을 안정화하고 반복 운용 가능한 임베디드 콘솔과
서버형 userspace로 확장합니다.

> **Note on repository name**
>
> This repository was originally named `A90_5G_rooting` when the Galaxy A90 5G
> was its only target. It was renamed to `android-native-init-lab` after the
> research expanded to the Galaxy S22+ and to a reusable, device-independent
> native PID 1 method. Historical paths and target-specific `a90_*` identifiers
> are retained where they remain technically or historically meaningful.

## Safety, Scope, and Ethics

이 작업은 저장소 소유자가 직접 소유하고 복구 경로를 관리하는 로컬 기기에서만
진행합니다. README와 관련 문서는 제3자 기기, 서비스, 계정, 네트워크를 대상으로 한
접근 방법이나 우회 절차로 해석하지 않습니다.

허용 범위는 다음으로 제한합니다.

- local device research
- documentation
- build troubleshooting
- native init/runtime development
- read-only diagnostics
- recovery-safe validation

금지/비목표 범위는 다음을 명확히 포함합니다.

- unauthorized access
- third-party targeting
- exploit deployment
- persistence
- malware
- credential theft
- stealth/evasion
- 타인 소유 기기 조작

실험 전에는 항상 해당 타깃의 검증된 recovery/Download 경로,
known-good boot/recovery/vbmeta, 로그 보존 경로를 확인하고, 복구 가능성을
해치거나 소유권이 불명확한 대상에는 적용하지 않습니다.

## Active Targets

- **Galaxy A90 5G (`SM-A908N`)**: custom native init, USB ACM/NCM, KMS/HUD,
  input, storage, network, and minimal userspace work has an established
  recovery-safe baseline. Detailed version history remains in
  `docs/overview/PROJECT_STATUS.md` and `CHANGELOG.md`.
- **Galaxy S22+ (`SM-S906N`, FYG8)**: source-matched vendor-kernel rebuild and
  retained PID 1 witness work is the active frontier. The current exact state,
  next host-only unit, and live authorization status are maintained at the top
  of `GOAL.md`.

Shared source lives under `workspace/public/src/`; target-specific source,
helpers, reports, rollback identities, and safety gates remain explicitly
separated. A result on one target never authorizes a device action on another.

## Current Objective

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

## What This Is

- Android vendor kernel과 기기 전용 driver를 활용하는 native userspace 실험
- boot ramdisk의 `/init`를 교체해 PID 1부터 직접 구성하는 작업
- USB serial, KMS display, input, battery/thermal sysfs를 사용하는 임베디드 콘솔
- 필요한 관측 능력을 추가하는 source-matched vendor-kernel rebuild 및 검증
- 장기적으로 BusyBox, USB network, dropbear SSH 같은 서버형 구성으로 확장할 수 있는 기반

## What This Is Not

- 일반 Debian/Ubuntu/Red Hat 배포판 포팅 완료 상태가 아님
- Android framework, 앱, SurfaceFlinger, Zygote를 복구하는 프로젝트가 아님
- 메인라인 커널 포팅 또는 범용 Android 커스텀 ROM 프로젝트가 아님
- 카메라, 모뎀, GPU 가속 등 vendor userspace 의존 기능을 즉시 지원하는 환경이 아님

## Near-Term Roadmap

현재 활성 프론티어는 S22+ FYG8 R4W1-B direct-PID1 acceptance의
호스트 소스/체커 구현이다. 정확한 상태와 다음 단계는 `GOAL.md`와
`docs/plans/S22PLUS_FYG8_R4W1B_DIRECT_PID1_EXEC_ACCEPTANCE_DESIGN_2026-07-13.md`를
기준으로 한다. 현재 live authorization은 없다.

A90은 이미 확보한 native-init/runtime 기반을 유지하는 안정화 대상이며,
기기별 다음 작업은 각각의 rollback identity와 `AGENTS.md` 승인 경계를
독립적으로 만족해야 한다.

## Repository Layout

- `docs/`
  현재 문서 인덱스, 프로젝트 상태, v39/v40/v41/v42 상태 보고서, 다음 작업 목록
- `workspace/public/src/native-init/`
  current native init source closure
- `workspace/public/src/scripts/revalidation/`
  current serial bridge, console, revalidation, build helper entrypoints
- `workspace/public/archive/`
  historical script and native-init provenance moved out of root paths
- `workspace/private/`
  ignored private inputs, boot images, build outputs, raw logs, and secrets
- `workspace/public/src/third_party/mkbootimg/`
  boot/recovery/vendor_boot 분석과 repack에 쓰는 도구

## Active Documents

전체 문서 목록과 읽는 순서, 사이클별 리포트(v40–V2168+)는 `docs/README.md`를
정식 인덱스로 한다. 여기서는 자주 여는 진입점만 추린다.

현재 상태 / 연구:

- `GOAL.md` — 현재 활성 타깃, frontier, 다음 bounded unit
- `AGENTS.md` / `CLAUDE.md` — 기기 작업 절대 안전 경계와 운영 계약
- `docs/plans/S22PLUS_FYG8_R4W1B_DIRECT_PID1_EXEC_ACCEPTANCE_DESIGN_2026-07-13.md`
  — S22+ 현재 frontier 설계
- `docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md` — 다음 작업 큐
- `docs/overview/PROJECT_STATUS.md` — 디바이스 상태 + 버전별 검증 이력
- `docs/overview/PROGRESS_LOG.md` — 진행 로그

운영 / 빌드:

- `docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md` — flash/bridge 절차
- `docs/operations/CLAUDE_NATIVE_INIT_RUNBOOK.md` — 운영 런북
- `docs/operations/VERSIONING_POLICY.md` / `docs/overview/VERSIONING.md` — Run ID, native init version, build tag, helper version, SHA 축 분리 규칙

이력 / 인덱스:

- `CHANGELOG.md` — native init / boot image 버전 이력
- `docs/README.md` — 전체 문서·리포트 인덱스

`docs/plans/NATIVE_LINUX_RECHALLENGE_PLAN.md`와 `docs/plans/REVALIDATION_PLAN.md`는
진입점 확보 이전의 부트체인 재검증 기록으로 보존한다.

## Working Rules

- 각 타깃의 known-good boot image와 검증된 복구 경로를 항상 유지한다.
- 한 번에 하나의 boot/init 변수만 바꾼다.
- 새 boot image는 version, source path, SHA256, 실기 관찰 결과를 기록한다.
- boot image와 native-init 빌드 산출물은 `workspace/private/inputs/boot_images/`와 `workspace/private/builds/native-init/`에 보존하고, historical source provenance는 `workspace/public/archive/stage3/`에 둔다.
- 루트 `firmware/`, `kernel_build/`, `toolchains/`, `external_tools/`, `backups/`, `out/`에는 신규 payload를 두지 않는다. 외부 입력과 결과물은 `workspace/private/` 아래에 둔다.
- 제어·관측 채널은 타깃별로 검증된 계약을 사용한다. A90의 기준
  채널은 USB ACM serial이며 S22+의 gate를 자동으로 대체하지 않는다.
- `/efs`, modem, RPMB, keymaster, keystore, bootloader 계열에는 쓰기 작업을 하지 않는다.
- `/data` 암호화 영역은 명확한 목적과 복구 계획 없이는 건드리지 않는다.
- 파티션은 by-name과 `/sys/class/block/<name>/dev` 기준으로 식별하고 major/minor를 hardcode하지 않는다.
- 원본 로그와 실험 산출물은 `/cache`, `tmp/wifi/{runs,cache,bench,scratch,archive}`, `workspace/private/`에 남기고, 공개 가능한 redacted 요약만 `docs/reports`, `docs/artifacts`, `workspace/public/`에 남긴다.
- ADB 안정화는 후순위로 두고, serial/HUD/log/menu 안정화를 먼저 진행한다.

## Safety Note

이 저장소에는 실제 플래시 대상 바이너리와 Samsung 전용 이미지가 포함될 수 있습니다.
실험 전에는 항상 현재 boot/recovery/vbmeta 상태와 복구 가능한 known-good 이미지를
확인한 뒤 진행합니다.

## License

이 저장소의 **문서와 스크립트**는 MIT License를 따른다 (루트 `LICENSE` 참고).

단, **Samsung 전용 펌웨어·커널 소스·patched AP/TWRP 이미지 등 proprietary 구성요소는
MIT 적용 대상이 아니며**, 각자의 라이선스를 따르고 정당한 권한 없이 재배포하지 않는다
(`LICENSE`의 NOTICE 절). `workspace/private/inputs/firmware/`,
`workspace/private/backups/`, `workspace/private/inputs/boot_images/*.img` 등에 포함된
벤더 바이너리는 저장소 소유자가 소유·관리하는 로컬 기기 복구/연구 용도로만 보관한다.
