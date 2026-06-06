# Samsung Galaxy A90 5G Native Init Workspace

이 저장소는 단순 rooting, 보안 우회, 또는 exploit 실습 프로젝트가 아닙니다.
저장소 소유자가 소유·관리하는 `Samsung Galaxy A90 5G (SM-A908N)` 실기에서
stock Android Linux kernel 위에 custom static `/init`(PID 1)와 최소
Linux-style runtime을 구성·검증하는 로컬 연구/문서화 작업 공간입니다.

초기 목표였던 `native Linux rechallenge`의 핵심 진입점 확보 단계는 통과했고,
현재 프로젝트의 중심은 **Android kernel 기반 native init 환경을 안정화하고
서버형 임베디드 Linux 콘솔로 확장하는 것**입니다.

> **Note on repository name**
>
> This repository was originally named during an early rooting/recovery access
> phase for a Samsung Galaxy A90 5G device owned by the repository owner.
> The project direction has since changed. The current focus is not general
> rooting guidance, but local development and documentation of a custom native
> `/init` and minimal Linux-style runtime on top of the stock Android Linux
> kernel.

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

실험 전에는 항상 TWRP, known-good boot/recovery/vbmeta, 로그 보존 경로를 확인하고,
복구 가능성을 해치거나 소유권이 불명확한 대상에는 적용하지 않습니다.

## Current State

아래는 외부 심사자와 협업자가 빠르게 확인해야 하는 핵심 상태입니다.
긴 version/history 목록과 세부 검증 기록은 이 README 상단에서 반복하지 않고
`docs/overview/PROJECT_STATUS.md`와 `CHANGELOG.md`를 기준으로 확인합니다.

- device: `SM-A908N`
- build: `A908NKSU5EWA3`
- kernel: Samsung stock Android kernel `Linux 4.14.190`
- recovery: TWRP 사용 가능
- current device build (flashed): `A90 Linux init 0.9.246 (v726-wifi-lifecycle)`
- official version: `0.9.246`
- build tag: `v726-wifi-lifecycle`
- creator: `made by temmie0214`
- current source tree: modular native init under `stage3/linux_init/`, rooted at `init_v724.c` with the V726 Wi-Fi lifecycle builder
- current boot image: `stage3/boot_linux_v726_wifi_lifecycle.img`
- previous verified boot image: `stage3/boot_linux_v725_fasttransport.img`
- known-good fallback: `stage3/boot_linux_v48.img`
- active research: native Wi-Fi lifecycle baseline hardening; next promoted baseline should use the next global run/build identity (`V2169` / `0.9.247`) rather than helper numbering
- 버전별 검증 이력은 `docs/overview/PROJECT_STATUS.md` 말미의 "README 이관" 섹션을 참고
- control channel: USB CDC ACM serial (`/dev/ttyGS0` ↔ `/dev/ttyACM0`)
- host bridge: `scripts/revalidation/serial_tcp_bridge.py --port 54321`
- display/input: custom boot splash, status HUD/menu, and physical button gesture handling
- logging: SD log path first, `/cache/native-init.log` fallback, private `/tmp/a90-native/native-init.log` emergency fallback
- storage: `/cache` safe write, ext4 SD workspace `/mnt/sdext/a90`, critical partitions do-not-touch
- validation posture: non-destructive selftest, read-only inventory/diagnostics, and recovery-safe smoke/soak checks
- userland policy: toybox fallback is verified; SD BusyBox remains blocked until manifest SHA-256 validation
- network posture: USB ACM/NCM and token-authenticated local control are opt-in, local-device channels only

> 버전별 상세 검증 노트(v48–V1165 이력)는 README에서 분리되어
> `docs/overview/PROJECT_STATUS.md` 말미 "README 이관: 상세 검증 노트" 섹션으로 이동했습니다.

## Current Objective

현재 메인 목표는 `stock Android kernel 위의 자체 native userspace`를 만드는 것입니다.

구조는 다음과 같습니다.

```text
Samsung bootloader
  -> stock Android Linux kernel
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

- Android kernel과 Samsung vendor driver를 그대로 활용하는 native userspace 실험
- boot ramdisk의 `/init`를 교체해 PID 1부터 직접 구성하는 작업
- USB serial, KMS display, input, battery/thermal sysfs를 사용하는 임베디드 콘솔
- 장기적으로 BusyBox, USB network, dropbear SSH 같은 서버형 구성으로 확장할 수 있는 기반

## What This Is Not

- 일반 Debian/Ubuntu/Red Hat 배포판 포팅 완료 상태가 아님
- Android framework, 앱, SurfaceFlinger, Zygote를 복구하는 프로젝트가 아님
- 커널 교체나 커널 드라이버 개발이 현재 목표가 아님
- 카메라, 모뎀, GPU 가속 등 vendor userspace 의존 기능을 즉시 지원하는 환경이 아님

## Near-Term Roadmap

현재 활성 작업은 native Wi-Fi lifecycle baseline hardening이다. 상세 사이클 계획과
안전 경계는 `CLAUDE.md`, `docs/reports/`, `docs/operations/VERSIONING_POLICY.md`를
기준으로 한다.

- verified baseline: `A90 Linux init 0.9.246 (v726-wifi-lifecycle)`,
  `stage3/boot_linux_v726_wifi_lifecycle.img`
- versioning cleanup: 다음 승격은 helper 번호와 혼동하지 않도록
  `V2169` run ID / `0.9.247` native init / `v2169-wifi-lifecycle-baseline`
  build tag 형태로 잡는다.
- artifact cleanup: 새 산출물은 `tmp/wifi/{runs,builds,cache,bench,scratch,archive}`
  구조로 저장하고, 공개 가능한 redacted summary만 `docs/artifacts`에 둔다.

v40–v116까지 완료된 native init 안정화 로드맵 체크리스트는 README에서 분리되어
`docs/overview/PROJECT_STATUS.md` 말미 "README 이관: 완료된 Near-Term Roadmap"
섹션으로 이동했다.

## Repository Layout

- `docs/`
  현재 문서 인덱스, 프로젝트 상태, v39/v40/v41/v42 상태 보고서, 다음 작업 목록
- `stage3/`
  native init 소스, 빌드 산출물, boot image 실험 파일
- `scripts/`
  serial bridge, console, revalidation helper
- `firmware/`
  stock firmware, patched AP, TWRP 이미지
- `mkbootimg/`
  boot/recovery/vendor_boot 분석과 repack에 쓰는 도구
- `backups/`
  known-good boot/recovery/vbmeta 등 복구 기준점

## Active Documents

전체 문서 목록과 읽는 순서, 사이클별 리포트(v40–V2168+)는 `docs/README.md`를
정식 인덱스로 한다. 여기서는 자주 여는 진입점만 추린다.

현재 상태 / 연구:

- `CLAUDE.md` — 현재 native Wi-Fi 연구 기준(사이클 상태·안전 경계)
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

- known-good boot image와 TWRP recovery 복구 경로를 항상 유지한다.
- 한 번에 하나의 boot/init 변수만 바꾼다.
- 새 boot image는 version, source path, SHA256, 실기 관찰 결과를 기록한다.
- 로컬 stage3 산출물은 v726 최신 verified, v725 fasttransport, v724 rollback, v48 known-good fallback만 기본 보존하고 나머지는 `scripts/revalidation/cleanup_stage3_artifacts.py`로 정리한다.
- USB ACM serial bridge를 기준 제어 채널로 사용한다.
- `/efs`, modem, RPMB, keymaster, keystore, bootloader 계열에는 쓰기 작업을 하지 않는다.
- `/data` 암호화 영역은 명확한 목적과 복구 계획 없이는 건드리지 않는다.
- 파티션은 by-name과 `/sys/class/block/<name>/dev` 기준으로 식별하고 major/minor를 hardcode하지 않는다.
- 원본 로그와 실험 산출물은 `/cache`와 `tmp/wifi/{runs,builds,cache,bench,scratch,archive}`에 남기고, 공개 가능한 redacted 요약만 `docs/reports` 또는 `docs/artifacts`에 남긴다.
- ADB 안정화는 후순위로 두고, serial/HUD/log/menu 안정화를 먼저 진행한다.

## Safety Note

이 저장소에는 실제 플래시 대상 바이너리와 Samsung 전용 이미지가 포함될 수 있습니다.
실험 전에는 항상 현재 boot/recovery/vbmeta 상태와 복구 가능한 known-good 이미지를
확인한 뒤 진행합니다.

## License

이 저장소의 **문서와 스크립트**는 MIT License를 따른다 (루트 `LICENSE` 참고).

단, **Samsung 전용 펌웨어·커널 소스·patched AP/TWRP 이미지 등 proprietary 구성요소는
MIT 적용 대상이 아니며**, 각자의 라이선스를 따르고 정당한 권한 없이 재배포하지 않는다
(`LICENSE`의 NOTICE 절). `firmware/`, `backups/`, `stage3/boot_linux_*.img` 등에 포함된
벤더 바이너리는 저장소 소유자가 소유·관리하는 로컬 기기 복구/연구 용도로만 보관한다.
