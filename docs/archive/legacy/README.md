# Samsung Galaxy A90 5G - 문서 인덱스

> **아카이브 · 권위 없음 · 2025 세대 문서**
>
> 이 인덱스는 A90 한 대만 대상이던 **2025년 방향**의 문서 트리(Headless
> Android / AOSP 최소 빌드 / Custom Kernel)를 설명합니다. 여기 적힌 Phase 0의
> "네이티브 부팅 불가" 판단은 **이후 반증됐습니다** — 2026-04-23에 native
> `/init`가 PID 1로 진입했습니다.
>
> 본문이 가리키는 `overview/PROJECT_STATUS.md`와 `overview/PROGRESS_LOG.md`는
> 이 디렉터리 아래 2025 세대 사본이며 갱신되지 않습니다. 2026 재도전기의 동명
> 후속 문서는 별도로 [`../overview/`](../overview/)에 보관합니다.
>
> - 현재 문서 인덱스: [`../../README.md`](../../README.md)
> - 프로젝트 연혁: [`../../overview/PROJECT_HISTORY.ko.md`](../../overview/PROJECT_HISTORY.ko.md)
> - 기기별 현재 상태: [`../../devices/README.ko.md`](../../devices/README.ko.md)
> - 기기 작업 권한: `AGENTS.md`와 선택된 binding target contract
>
> 본문은 당시 기록 그대로 보존하며 수정하지 않습니다.


최신 Phase 1(완료) / Phase 2(Headless Android + 커널 최적화) 결과물을 빠르게 찾기 위한 문서 인덱스입니다.  
프로젝트 전반 개요와 현재 상태는 `overview/PROJECT_STATUS.md`에서 최신으로 유지합니다.

## 현재 진행 상태
- ✅ **Phase 0**: 네이티브 부팅 불가 근거 확보, 대안 전략 수립
- ✅ **Phase 1**: Magisk Systemless Chroot + Debian 12 ARM64 환경 완성
- ✅ **Phase 2**: Android Headless 모드 + 커스텀 커널 최적화 (RAM 절감 235MB + α)
- 🚧 **Phase 3 이후**: AOSP 최소 빌드/Termux 대안, 하드웨어 교체 옵션 등 확장 단계는 준비 완료 상태

## 문서 카테고리

### 1. Overview
- `overview/PROJECT_STATUS.md` – Phase별 결과, 마일스톤, 다음 단계 옵션
- `overview/PROGRESS_LOG.md` – 모든 실험 로그, 명령어, 시간 기록

### 2. Plans
- `plans/NATIVE_LINUX_BOOT_PLAN.md` – Phase 0~5 네이티브 부팅 로드맵
- `plans/HEADLESS_ANDROID_PLAN.md` – Android GUI 제거 전략
- `plans/CUSTOM_KERNEL_PLAN.md` – 최적화 커널 로드맵
- `plans/ALTERNATIVE_PLAN.md` – Termux/다른 디바이스 등 대안 시나리오

### 3. Guides
- `guides/MAGISK_SYSTEMLESS_GUIDE.md` – Phase 1 전체 구현 가이드 (1,900+ 줄)
- `guides/HEADLESS_ANDROID_IMPLEMENTATION.md` – Headless 모드 적용 절차
- `guides/AOSP_MINIMAL_BUILD_GUIDE.md` – AOSP 최소 빌드 파이프라인 문서

### 4. Reports
- `reports/HEADLESS_BOOT_V2_SUMMARY.md` – Headless v2 결과 요약
- `reports/CUSTOM_KERNEL_OPTIMIZATION_REPORT.md` – 커널 최적화 상세 보고서
- `reports/PERFORMANCE_RESULTS.md` – 측정 지표 집계
- `reports/CLEANUP_SUMMARY.md` / `reports/FINAL_CLEANUP_REPORT.md` – 문서 정리 기록

## 활용 가이드
1. **상태 확인**: 새로운 작업을 시작하기 전에 `overview/PROJECT_STATUS.md`를 먼저 업데이트/확인합니다.
2. **세부 계획 → 실행**: `plans/` 문서로 로드맵을 잡고, `guides/`의 절차서를 따라 실행합니다.
3. **결과 기록**: 실험/측정 결과는 `reports/`에 요약하고, 상세 로그는 `overview/PROGRESS_LOG.md`에 누적합니다.

문서 추가 시 위 카테고리 중 하나에 위치시키고, 새 파일을 `docs/README.md`에도 링크하여 탐색성을 유지하세요.
