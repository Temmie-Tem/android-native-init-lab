# 문서 인덱스

[English](README.md) · **한국어**

`docs/`에 무엇이 있는지, 그리고 더 중요하게는 **어떤 파일이 무엇에 대한 정본인지**를
보여주는 지도입니다. 이 인덱스는 현재 상태를 의도적으로 담지 않습니다. latest
build, 현재 unit이나 P 번호, 기능 버전 같은 것은 넣지 않습니다. 그것들은 움직이고,
여기 사본을 하나 더 두면 며칠 안에 틀린 값이 됩니다. 아래의 모든 포인터는 답을
소유한 파일을 가리킵니다.

그런 상태를 담고 있던 이전 한국어 인덱스는
[`archive/documentation/DOCS_README_KO_LEGACY_2026-09-09.md`](archive/documentation/DOCS_README_KO_LEGACY_2026-09-09.md)에
byte 단위로 동일하게 보존되어 있습니다.

## 현재 상태의 정본

| 질문 | 정본 |
| --- | --- |
| 특정 대상의 현재 frontier, 활성 bounded unit, 기능 버전은? | [`GOAL.md`](../GOAL.md) (S22+), [`GOAL_A90.md`](../GOAL_A90.md), [`GOAL_S20PLUS.md`](../GOAL_S20PLUS.md) |
| 기기에 무엇이 허용되며, 어떤 승인 아래인가? | [`AGENTS.md`](../AGENTS.md)와 [타겟 계약](operations/targets/) |
| 어떤 한 번의 실행이 실제로 무엇을 성립시켰나? | [`reports/`](reports/)의 해당 런 리포트 |
| 한 대상이 전체적으로 무엇을 확립했고 무엇이 미증명인가? | [`devices/README.ko.md`](devices/README.ko.md)와 기기별 페이지 |
| 버전·후보·실행의 명명 규칙과 버전↔산출물 대응은? | [`operations/S22PLUS_FYG8_VERSIONING.md`](operations/S22PLUS_FYG8_VERSIONING.md), [`operations/VERSIONING_POLICY.md`](operations/VERSIONING_POLICY.md) |
| 공개 트리에 무엇이 들어갈 수 있나? | [`operations/PUBLIC_TREE_SANITIZATION_POLICY.md`](operations/PUBLIC_TREE_SANITIZATION_POLICY.md) |

요약 페이지가 위 정본을 덮어쓰는 일은 없습니다. 롤링 요약과 GOAL·계약이 어긋나면
GOAL·계약이 옳고 요약이 낡은 것입니다.

## 읽는 순서

**처음 보는 경우.** 루트 [`README.ko.md`](../README.ko.md)에서 프로젝트가 무엇인지
확인하고, [`devices/README.ko.md`](devices/README.ko.md)에서 각 대상이 공통 증거
어휘 아래 무엇을 확립했는지 비교한 다음, 읽는 대신 보고 싶다면 시각 증거 페이지로
갑니다: [A90](devices/A90_VISUAL_EVIDENCE.ko.md),
[S22+ 디스플레이](devices/S22PLUS_DISPLAY_VISUAL_EVIDENCE.ko.md),
[S22+ 부팅 HUD](devices/S22PLUS_BOOT_HUD_VISUAL_EVIDENCE.ko.md).

**기기를 건드리거나 그런 작업을 검토하기 전.** [`AGENTS.md`](../AGENTS.md)가
먼저이고, 그다음
[`operations/DEVICE_ACTION_RISK_TIERS.md`](operations/DEVICE_ACTION_RISK_TIERS.md),
[`operations/DEVICE_ACTION_PROCESS_V2.md`](operations/DEVICE_ACTION_PROCESS_V2.md),
그리고 선택한 [타겟 계약](operations/targets/)입니다. 해당 `GOAL*.md`는 현재 unit이
무엇인지 알려줄 뿐, 그 자체로는 어떤 권한도 부여하지 않습니다.

**진행 중인 작업을 이어받는 경우.** 대상의 `GOAL*.md`, 그다음
[`operations/`](operations/)의 campaign ledger, 그다음 해당 대상의 최신 리포트입니다.

**엔지니어링 관행.**
[`operations/ENGINEERING_INVARIANTS.md`](operations/ENGINEERING_INVARIANTS.md)가
대상 공통 빌드·주소지정·기록 불변식이고,
[`operations/DEVELOPMENT_LOOP_STANDARD.md`](operations/DEVELOPMENT_LOOP_STANDARD.md)는
A90 전용 루프입니다.

## 문서 컬렉션

| 디렉터리 | 내용 | 진입점 |
| --- | --- | --- |
| [`devices/`](devices/) | 기기별 페이지와 시각 증거, 영어·한국어 | [`devices/README.ko.md`](devices/README.ko.md) |
| [`operations/`](operations/) | 계약, 위험 등급, device-action 프로세스, 타겟 계약, capability 명세, campaign ledger, 런북 | 아래 목록 |
| [`operations/targets/`](operations/targets/) | 결속력 있는 대상별 계약 | 대상당 하나 |
| [`reports/`](reports/) | 실행·사이클별 불변 증거, 수천 개 | 파일명 규칙 참고 |
| [`plans/`](plans/) | unit 실행 전에 작성한 설계와 인계 문서 | 파일명 |
| [`module-map/`](module-map/) | 서브시스템 연구 맵 | [`module-map/s22plus-fyg8/README.md`](module-map/s22plus-fyg8/README.md) |
| [`overview/`](overview/) | 프로젝트 연혁과 버전 서술 | [`overview/PROJECT_HISTORY.ko.md`](overview/PROJECT_HISTORY.ko.md) |
| [`security/`](security/) | 리뷰 findings, hardening 노트, batch | [`security/README.md`](security/README.md) |
| [`artifacts/`](artifacts/) | 생성된 인벤토리와 frontier 후보 데이터 | [`artifacts/README.md`](artifacts/README.md) |
| [`images/`](images/) | 시각 증거 페이지가 참조하는 공개 사진·클립 | 그 페이지들 |
| [`archive/`](archive/) | 대체된 문서, 폐기된 계약 텍스트, 역사적 스냅샷 | [`archive/README.md`](archive/README.md) |

`reports/`와 `plans/`는 여기에 목록화하지 않습니다. unit마다 늘어나므로, 손으로
관리하는 목록은 쓸모 있어지기 전에 낡습니다.

### 자주 여는 operations 문서

- [`operations/DEVICE_ACTION_RISK_TIERS.md`](operations/DEVICE_ACTION_RISK_TIERS.md) — 동작에 비례하는 검증 강도
- [`operations/DEVICE_ACTION_PROCESS_V2.md`](operations/DEVICE_ACTION_PROCESS_V2.md) — 재사용 가능한 boot-only 프로세스
- [`operations/DEVICE_ACTION_CONTRACT_DETAILS.md`](operations/DEVICE_ACTION_CONTRACT_DETAILS.md) — 영구 기기 안전 경계
- [`operations/ENGINEERING_INVARIANTS.md`](operations/ENGINEERING_INVARIANTS.md) — 대상 공통 엔지니어링 불변식
- [`operations/PUBLIC_TREE_SANITIZATION_POLICY.md`](operations/PUBLIC_TREE_SANITIZATION_POLICY.md) — 식별자 경계와 boundary check
- [`operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md`](operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md) — flash/bridge 절차
- [`operations/CLAUDE_NATIVE_INIT_RUNBOOK.md`](operations/CLAUDE_NATIVE_INIT_RUNBOOK.md) — 운영 런북

## 목록 없이 리포트 찾기

리포트 파일명이 소속을 인코딩합니다. 즉 grep이 인덱스입니다.

```text
<대상 또는 계열>_<unit>_<주제>_<날짜>.md

S22PLUS_FYG8_P376_BOOT_HUD_H0_2026-09-09.md
NATIVE_INIT_V3043_DOOMGENERIC_LATENCY_COLOR_LIVE_2026-06-22.md
```

사용 중인 대상·계열 접두어에는 `S22PLUS`, `A90`, `S20PLUS`, `NATIVE_INIT`,
`KERNEL`, `SERVER`가 있습니다. 끝의 날짜는 둘이 다를 경우 실행 날짜가 아니라 리포트
작성 날짜입니다.

## 아카이브

[`archive/`](archive/) 아래의 어떤 것도 기기 승인의 활성 근거가 아닙니다. 그 안의
역사적 `ACTIVE` 문자열, 승인 토큰, 상태 주장은 비활성 증거입니다. 폐기된 계약
텍스트, 2026년 이전 세대 문서, 그리고 대체된 문서의 byte 단위 동일 스냅샷을
보관하며, 각각의 SHA-256이 [`archive/README.md`](archive/README.md)에 기록되어
있습니다.

## 언어

기기 페이지, 루트 README, 이 인덱스는 영어와 한국어로 관리합니다. 각 쌍에서
구조 정본은 영어 파일이며, 한국어판은 그 절 구조를 따르되 지역 상세를 더 담을 수
있습니다. operations 문서, 리포트, plans는 단일 언어입니다.
