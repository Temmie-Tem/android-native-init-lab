# Scripts Index

`2026-04-23` 기준으로 `scripts/`는
`native Linux rechallenge`를 위한 최소 구조만 유지합니다.

## Current

- `revalidation/`
  현재 rooted baseline 점검, `boot/recovery/vbmeta` 캡처,
  4조합 재검증, 실험 기록 보조용 공간입니다.
  새 스크립트는 이 경로 아래에만 추가합니다.

## Archive

- `archive/README.md`
  스크립트 아카이브 인덱스
- `archive/legacy/`
  기존 2025 방향 스크립트 일괄 보관
  - AOSP minimal build
  - headless Android automation
  - Magisk module templates
  - kernel build / optimize helpers
  - Debian rootfs utilities

## Rule

- 현재 실험과 직접 관계없는 스크립트는 `archive/legacy/`에 둡니다.
- 현재 메인 목표는 rooted baseline 유지, 보안 경계 재검증,
  그리고 native Linux 진입 후보 재도전입니다.
- 부트체인 실험 중에는 추가 debloat 자동화를 넣지 않습니다.
- `firmware/`와 `mkbootimg/`는 스크립트 아카이브 대상이 아닙니다.
