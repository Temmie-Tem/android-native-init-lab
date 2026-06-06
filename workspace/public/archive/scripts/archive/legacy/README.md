# Legacy Scripts

이 문서는 `2026-04-23` 리셋 이전 스크립트 인덱스입니다.
현재 기준 스크립트는 상단 [scripts/README.md](/home/temmie/dev/A90_5G_rooting/scripts/README.md:1)를 따릅니다.

# A90_5G Rooting Scripts

도구 스크립트, 빌드 파이프라인, Magisk 모듈 템플릿을 한곳에 정리했습니다. 모든 스크립트는 Bash 기반이며 `adb`, `fastboot`, `python3` 등 기본 도구가 설치되어 있다고 가정합니다.

## 디렉토리 구조

| 경로 | 설명 | 주요 사용법 |
|------|------|-------------|
| `aosp_build/` | AOSP 미니멀 빌드 7단계 파이프라인. 소스 다운로드 → 디바이스 트리 구성 → 최소 설정 → 빌드/플래시 | `cd aosp_build && ./01_setup_environment.sh` 부터 순차 실행 |
| `headless_android/` | GUI/서비스 비활성화 자동화 스크립트와 복구 도구. 최적화 버전(`*_optimized.sh`)은 최신 패키지 스캔 결과에 맞춰짐 | `scan_packages.sh`로 목록 생성 → 단계별 `disable_*.sh` 실행 → `restore_all.sh`로 복구 |
| `magisk_module/` | `systemless_chroot` 템플릿과 `headless_boot_v2` 모듈 소스. 완성된 ZIP은 `magisk_module/releases/`(gitignore)로 분리 | 모듈 수정 후 `zip -r`로 패키징, 릴리스 파일은 `releases/`에 보관 |
| `utils/` | 루트fs 생성/검증, 환경 점검, Magisk 디버깅 등 공용 스크립트 | `utils/check_env.sh` 실행 후 `create_rootfs.sh`, `verify_rootfs.sh` 순으로 사용 |
| 최상위 `*.sh` | 커널 빌드 및 최적화 엔트리포인트 (`build_kernel_simple.sh`, `build_optimized_kernel.sh`, `kernel_optimize.sh`) | 지정된 툴체인/구성에 맞춰 실행 (`--help` 옵션 제공) |

## 릴리스 아티팩트

Magisk 모듈 ZIP과 기타 대용량 결과물은 `magisk_module/releases/` 폴더에 보관하며 `.gitignore` 처리되어 있습니다. 소스 변경 사항만 커밋하고, 배포 파일은 필요 시 GitHub Release나 외부 스토리지에 업로드하세요.

## 권장 워크플로우

1. `utils/check_env.sh`로 의존성 점검 → `create_rootfs.sh`/`verify_rootfs.sh`로 Debian rootfs 준비  
2. `magisk_module/systemless_chroot` 수정 후 디바이스에 배포 → `headless_android/` 스크립트로 RAM 최적화  
3. 고급 실험 시 `aosp_build/` 파이프라인 또는 커널 빌드 스크립트를 사용해 맞춤 이미지 생성

각 스크립트는 헤더 주석에 필요한 환경 변수와 실행 예제가 있으니, 실행 전 반드시 내용을 확인하세요.
