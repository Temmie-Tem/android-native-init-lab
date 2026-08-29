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

| 기기 | SoC / kernel | 확립된 결과 | 현재 프론티어 | 핵심 미증명 경계 |
| --- | --- | --- | --- | --- |
| [Galaxy A90 5G](A90.ko.md) (`SM-A908N`) | Qualcomm SM8150 / vendor Linux 4.14.190 | **PROVED(증명됨):** custom native PID 1, ACM/NCM, native Wi-Fi, internal-speaker 경로와 Debian PID 1/SSH/display를 각각 증명한 bounded run | public MPGen/RTIC metadata를 포함하는 stock-shaped self-built kernel을 재현하고, 향후 canary를 별도로 qualification | PID 1, final Wi-Fi, authenticated SSH, minimal `/dev`, isolation, terminal health를 동시에 닫는 하나의 persistent isolated-Debian run |
| [Galaxy S22+](S22PLUS.ko.md) (`SM-S906N`, FYG8) | Qualcomm SM8450 / vendor Linux 5.10.226 | **PROVED(증명됨):** source-matched rebuilt kernel이 Android를 boot했으며, direct native candidate가 current PID 1 상태에서 받아들여진 `/init` exec에 도달 | USB chain: SSUSB parent → DWC3 child → UDC → transport. 이후 live qualification 전에 누락된 fresh baseline 확보 | 첫 native userspace instruction과 candidate-runtime SSUSB/DWC3/UDC/host transport |
| [Galaxy S20+ 5G](S20PLUS.ko.md) (`SM-G986N`) | Qualcomm SM8250 / vendor Linux 4.19.113 | **PROVED(증명됨):** exact onboarding, boot-only Magisk bootstrap/rollback, persistent rooted Android, bounded native-canary transaction/recovery 결과 | review 이후에만 N3-U0 ACM 경로와 별도의 dormant autonomous-research infrastructure를 integration·activation | Native PID 1과 N3-U0 runtime. autonomous connected authority는 활성화되지 않음 |

## 읽는 순서

먼저 위의 기기별 페이지를 읽습니다. 현재 상태는 각 GOAL 링크, 기기 authority는
target contract, 과거 결과는 ledger와 개별 report를 확인합니다. Host-side
`PASS_GO`는 명시된 capability만 qualification하며, live result나 standing device
authority의 증거가 아닙니다.
