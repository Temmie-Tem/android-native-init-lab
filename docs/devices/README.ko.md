# 기기별 진행 상황 안내

[English](README.md) · **한국어**

이 디렉터리는 저장소의 세 기기를 외부 독자가 빠르게 이해할 수 있게 정리한
안내서입니다. Binding target contract, 현재 GOAL 파일, campaign ledger, run
report를 대체하지 않으며, 해당 기록이 계속 정본입니다.

## 증거 용어

- **PROVED(증명됨)** — 하나의 bounded run에서 명시된 evidence contract가
  받아들였거나, 명시된 범위에 대해 재현 가능한 host-side proof가 성립한 상태.
- **OBSERVED(관측됨)** — PROVED로 올라가지 않은 직접 관측. 등급 라벨로 쓸 때는
  대문자 토큰을 쓰고, 일반 문장에서는 "observed"를 문법에 맞게 씁니다.
- **designed(설계됨)** — host-side에서 구현하거나 문서화했지만, 별도 명시가
  없으면 runtime에서 증명되지 않은 상태.
- **unproved(미증명)** — 해당 claim을 받아들일 수 있는 증거가 저장소에 없는 상태.

이 label은 각 claim의 범위 안에서만 유효합니다. 서로 다른 run의 증거를 합쳐
새로운 end-to-end 성공으로 만들지 않습니다.

## 한눈에 보기

S22+ 행은 2026-09-09 기준이며, 나머지 행은 2026-09-05 시점 요약을 유지합니다. 이후 변동은 각 GOAL을 확인합니다.

| 기기 | SoC / kernel | 확립된 결과 | 현재 프론티어 | 핵심 미증명 경계 |
| --- | --- | --- | --- | --- |
| [Galaxy A90 5G](A90.ko.md) (`SM-A908N`)<br>[시각 증거](A90_VISUAL_EVIDENCE.ko.md) | Qualcomm SM8150 / vendor Linux 4.14.190 | **PROVED(증명됨):** native PID 1, ACM/NCM, native Wi-Fi/audio와 bounded Debian PID 1/SSH/display 결과 | 마지막 추적 상태는 H41 Native에 주차; exact V2321 rollback/health 종결이 아직 남아 있으며 isolated-Debian 서버 작업은 일시 중지 | 선택한 isolated-Debian architecture를 통합한 persistent run; H41 playback과 복구 종결 |
| [Galaxy S22+](S22PLUS.ko.md) (`SM-S906N`, FYG8)<br>[디스플레이 시각 증거](S22PLUS_DISPLAY_VISUAL_EVIDENCE.ko.md)<br>[부팅 HUD 시각 증거](S22PLUS_BOOT_HUD_VISUAL_EVIDENCE.ko.md) | Qualcomm SM8450 / vendor Linux 5.10.226 | **PROVED(증명됨):** rebuilt-kernel Android boot, native-PID1 ACM, 인증된 제한적 읽기 전용 셸과 healthy rollback (P348까지); P353~P361은 display dispatch/rollback을 **PROVED**, 반복 framebuffer 선택을 포함한 깨끗한 cached-buffer 출력을 **OBSERVED(관측)**; P375 이후 작업은 인증된 루트 명령 콘솔과 uptime·콘솔 상태·메모리·CPU·배터리 항목을 싣는 네이티브 PID1 상태 HUD를 **PROVED**, 패널 위 출력을 **OBSERVED(관측)** | 완료된 각 범위는 정확한 롤백과 최종 건강 확인으로 닫히고 native 세션·재실행 권한을 남기지 않음; 정확한 현재 기능 버전과 다음 bounded unit은 `GOAL.md`가 정본 | 기기에서 뒷받침된 P349 1시간 witness, 상주·무제한 root shell, pixel readback, WC/CACHED 깨짐 원인, 네이티브 정상 reboot, 기계로 증명된 Download 도착, 무인 운용, PID1/커널 정지 복구 |
| [Galaxy S20+ 5G](S20PLUS.ko.md) (`SM-G986N`) | Qualcomm SM8250 / vendor Linux 4.19.113 | **PROVED(증명됨):** onboarding, resident Magisk, retained T2 TWRP, P0 V3 전송/정상 rollback | P0 V3 NO_PROOF 이후 초기 부팅 pstore/PMSG 관측 | Custom native PID 1, live 초기 부팅 retention, autonomous F1 |

## 읽는 순서

먼저 위의 기기별 페이지를 읽습니다. 현재 상태는 각 GOAL 링크, 기기 authority는
target contract, 과거 결과는 ledger와 개별 report를 확인합니다. Host-side
`PASS_GO`는 명시된 capability만 qualification하며, live result나 standing device
authority의 증거가 아닙니다.
