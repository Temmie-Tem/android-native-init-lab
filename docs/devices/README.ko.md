# 기기별 진행 상황 안내

[English](README.md) · **한국어**

이 디렉터리는 저장소의 세 기기를 외부 독자가 빠르게 이해할 수 있게 정리한
안내서입니다. Binding target contract, 현재 GOAL 파일, campaign ledger, run
report를 대체하지 않으며, 해당 기록이 계속 정본입니다.

## 증거 용어

- **PROVED(증명됨)** — 하나의 bounded run에서 명시된 evidence contract가
  받아들였거나, 명시된 범위에 대해 재현 가능한 host-side proof가 성립한 상태.
- **observed(관측됨)** — 직접 관측했지만 인접한 더 강한 claim을 뒷받침하기에는
  충분하지 않은 상태.
- **designed(설계됨)** — host-side에서 구현하거나 문서화했지만, 별도 명시가
  없으면 runtime에서 증명되지 않은 상태.
- **unproved(미증명)** — 해당 claim을 받아들일 수 있는 증거가 저장소에 없는 상태.

이 label은 각 claim의 범위 안에서만 유효합니다. 서로 다른 run의 증거를 합쳐
새로운 end-to-end 성공으로 만들지 않습니다.

## 한눈에 보기

2026-09-05 확인한 기록의 요약입니다. 이후 변동은 각 GOAL을 확인합니다.

| 기기 | SoC / kernel | 확립된 결과 | 현재 프론티어 | 핵심 미증명 경계 |
| --- | --- | --- | --- | --- |
| [Galaxy A90 5G](A90.ko.md) (`SM-A908N`)<br>[시각 증거](A90_VISUAL_EVIDENCE.ko.md) | Qualcomm SM8150 / vendor Linux 4.14.190 | **PROVED(증명됨):** native PID 1, ACM/NCM, native Wi-Fi/audio와 bounded Debian PID 1/SSH/display 결과 | H41 rollback/health 종결; isolated-Debian 서버 작업 일시 중지 | 선택한 isolated-Debian architecture를 통합한 persistent run; H41 playback과 복구 종결 |
| [Galaxy S22+](S22PLUS.ko.md) (`SM-S906N`, FYG8)<br>[디스플레이 시각 증거](S22PLUS_DISPLAY_VISUAL_EVIDENCE.ko.md) | Qualcomm SM8450 / vendor Linux 5.10.226 | **PROVED(증명됨):** rebuilt-kernel Android boot, native-PID1 ACM, 인증된 제한적 읽기 전용 셸, 120초 reopen과 healthy rollback (P348) | P349 RAM workspace와 실제 1시간 witness는 host 검증 완료; 두 전송 전 인증 중단 후 참석 대기 | 기기 RAM/1시간 검증, 무제한 root shell/persistent service, 상세 USB/Max77705 원인 |
| [Galaxy S20+ 5G](S20PLUS.ko.md) (`SM-G986N`) | Qualcomm SM8250 / vendor Linux 4.19.113 | **PROVED(증명됨):** onboarding, resident Magisk, retained T2 TWRP, P0 V3 전송/정상 rollback | P0 V3 NO_PROOF 이후 초기 부팅 pstore/PMSG 관측 | Custom native PID 1, live 초기 부팅 retention, autonomous F1 |

## 읽는 순서

먼저 위의 기기별 페이지를 읽습니다. 현재 상태는 각 GOAL 링크, 기기 authority는
target contract, 과거 결과는 ledger와 개별 report를 확인합니다. Host-side
`PASS_GO`는 명시된 capability만 qualification하며, live result나 standing device
authority의 증거가 아닙니다.
