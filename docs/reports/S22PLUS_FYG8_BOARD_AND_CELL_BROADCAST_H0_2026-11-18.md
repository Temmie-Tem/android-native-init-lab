# SM-S906N 실기 보드 식별과 재난문자 수신 상태

국내판 S22+의 기존 실기 기록을 FYG8 순정 기기 트리와 대조했다. 실기 기록은 AP 보드 리비전 16과 이 보드에 적용된 기기 트리를 식별한다. 모뎀이 선택한 RF 카드나 실장 트랜시버의 실리콘 리비전을 식별할 수 있는 값은 찾지 못했다.

## 실물과 펌웨어의 대응

| 관측 대상 | 대조 결과 |
| --- | --- |
| 실험 단말 | 7월 13일에 수집한 두 보고서가 모두 모델 `SM-S906N`, 제품 `g0q`, 부트로더 `S906NKSS7FYG8`, 베이스밴드 `S906NKSS7FYG1`을 기록했다. |
| AP 보드 | Android 속성 `ro.boot.revision`은 16이고 XBL의 하드웨어 리비전 기록은 `0x10`이다. 커널의 기기 트리 모델 표기는 두 보고서 모두 `Samsung G0Q PROJECT (board-id,12)`이다. |
| 순정 DTBO | 컨테이너의 11개 항목을 모두 해석했다. 항목 10(0부터 셈)의 모델이 실기 기록과 같으며, 시작·끝 리비전은 `0x0c`와 `0x20`이다. 리비전 16이 들어가는 항목은 이것 하나다. FYG8 공개 커널 소스의 `g0q_kor_singlex_w00_r12.dts`와도 일치한다. |
| 모뎀 RF 식별 | RIL이 보고한 값은 `ril.hw_ver=REV0.7`이다. 두 ZIP의 `dumpstate.txt`와 `dumpstate_board.txt`에서 이 값과 RF 카드 ID를 연결하는 기록, QLINK 번호와 실장 칩 리비전을 함께 식별하는 기록을 찾지 못했다. |

따라서 기기 트리 이름의 12를 모뎀 RF 카드 번호로 대입할 근거가 없다. 국내 모델의 n78 지원 자체는 제조사가 명시한다. 확인한 실기 기록에서는 n78 접속, 기지국 역할의 송신, 독립 수신기의 파형 관측을 입증할 수 없었다. [삼성전자 국내 모델 사양](https://www.samsung.com/sec/support/model/SM-S906NZEWKOO/)

국립전파연구원의 해당 모델 적합인증 원문에서도 장비 역할을 확인했다. 2022년 2월 11일 인증한 `R-C-SEC-SMS906`의 모델은 `SM-S906N`이며, 3.5 GHz 5G NR 장비의 분류는 ‘육상이동국의 송수신장치’다. 이 기록은 국내 모델의 이동국 송수신 용도를 뒷받침한다. 기지국 역할의 동작 여부를 판정할 시험 결과나 RF 부품 명세는 이 인증 조회표에 없다. [국립전파연구원 모델별 적합인증](https://www.rra.go.kr/ko/license/A_b_popup_keyno.do?key_no=R-C-SEC-SMS906)

## 재난문자 수신 구성요소의 변화

Android 수신 경로에서는 전화 프레임워크가 CellBroadcastService로 메시지를 넘기고, 수신 앱이 경보를 표시한다. 이 단말의 두 패키지는 `com.google.android.cellbroadcastservice`와 `com.google.android.cellbroadcastreceiver`이다. 패키지 목록, 실행 중 서비스 연결, 실제 경보 표시는 각각 다른 관측이다. [Android 수신 경로](https://source.android.com/docs/core/ota/modular-system/cellbroadcast)

| 시점과 자료 | 관측한 상태 |
| --- | --- |
| 7월 13일, 실기 bugreport 두 건 | 두 패키지의 APEX 경로가 등록되어 있었고, 각 패키지의 사용자 0 상태는 `installed=false`였다. 전화 프레임워크의 수신 서비스 관리자는 `mEnabled=true`, `mCellBroadcastServicePackage=null`이었다. 두 번째 보고서에는 서비스를 찾지 못해 연결에 실패한 기록도 있다. SIM 속성은 두 건 모두 `ABSENT`, 망 종류 속성은 `LTE`였다. |
| 9월 16일, P398 additional38 | 사용자 0의 시스템 패키지 목록에서 작업 전과 작업 후 모두 서비스와 수신 앱이 확인된다. 한국용 수신 설정 오버레이와 서비스 오버레이는 작업 전 목록에만 있다. 이 목록은 수신 기능 시험 결과를 담지 않는다. |
| 9월 16일, P398 checkpoint-full | 초기 사용자 0 목록에 두 패키지가 있었다. 저널 항목 125–128에서 각 패키지의 제거 의도·완료가 짝을 이루고, 두 원본 명령 결과가 모두 성공이다. 재부팅 전 목록과 이후 대조 목록에는 두 패키지가 없다. |

두 시점 사이에 설치 상태가 바뀌었으며, 7월의 미설치 원인이나 그 이후 복원 시점은 이 자료로 판별할 수 없다. 9월의 제거 작업에는 직접 증거가 있다. 이 기록으로 확인한 범위는 실험 단말의 사용자 0과 해당 수집 시점이다. 국내 출고 기본값, 현재 서비스 상태, 실제 공공 경보 수신 여부는 미확인이다.

## 근거와 검증

- 7월 자료는 `workspace/private/runs/` 아래의 `s22plus_fyg8_r4w1a_oracle_dry_run_20260713T095754Z`, `s22plus_fyg8_r4w1a_stream_candidate_live_20260713T142016Z`다. 각 ZIP의 SHA-256을 다시 계산해 해당 실행의 `oracle_capture.json`과 대조했다. 해시 접두사는 각각 `0935e3215ea3`, `b22cd16a40d8`이다.
- 보관된 순정 DTBO 두 사본의 전체 SHA-256이 기존 순정 해시와 일치했다. 각 DTBO 항목의 모델과 리비전 속성은 컴파일된 FDT에서 읽었다. [저장소의 순정 DTBO 해시](../operations/S22PLUS_FYG8_R4W1C_CONNECTED_BINDING_CLAUSE_2026-07-20.md)
- 9월 근거는 `workspace/private/runs/s22plus-android-minimal-v1/`의 `p398-additional38-20260916-1` 및 `p398-checkpoint-full-20260916-1`이다. 목록 생산자의 사용자 0 범위를 확인하고 보관된 출력과 캡처 해시를 대조했다. 제거 완료 두 건은 저널이 참조하는 캡처와 실제 명령 출력까지 대조했다.
- 11월 18일에는 호스트의 USB 열거 정보에서 확인한 삼성 단말 한 대가 두 과거 보고서의 비공개 식별값과 일치했다. 현재 부팅 상태나 패키지 상태를 보여 주는 값은 아니다. 기존 전경 연구용 D0 도구의 호스트 측 검증은 `reviewed source changed`를 반환했다. 저장된 검토 이후 원본 캡처 도구, 실행 레지스트리, 공통 계약 및 대상 계약의 해시가 달라졌다. 이 도구의 프로세스 목록만으로도 실제 경보 수신 여부를 판별할 수 없다. [전경 연구용 D0 도구의 범위](../operations/targets/S22PLUS_FYG8_GOAL_RESEARCH_V1.md)
- 새 단말 명령, 패키지 변경, 재부팅 또는 RF 송신은 수행하지 않았다. 실장 RF 부품을 확정하려면 해당 보드 리비전에 대응하는 부품표나 부품 마킹이 판독되는 사진이 필요하다. 실제 재난문자 수신·표시 여부는 같은 수신 건에 대해 무선 수신과 Android 표시 양쪽을 확인할 수 있는 증거가 필요하다.
