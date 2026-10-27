# S22+ 재빌드와 검증 및 독립 리뷰의 필요성 감사

Date: 2026-10-28 KST. Source checkpoint:
`17ed5b5ba9ea23524b254ffe18d2243d017c28af`.
Scope: P463 준비 과정, P459 cron 검증의 반례, 현재 mainline H0 절차에 적용할 결정.

**검사기만 고쳤는데 이미지를 재생성하고 전체 VM을 다시 돌리는 연결은 제거할
대상이다. 후보 데이터마다 별도 독립 진입 리뷰를 요구하는 단계도 검토된
템플릿과 기계적 결합 검사로 대체할 수 있다. 반면 새로운 권한·복구·증거
수용 의미를 검토하는 독립 리뷰는 구체적인 결함 발견 가치가 확인됐다.**

이번 감사는 [이전 비용 감사](S22PLUS_PROCEDURE_COST_AUDIT_H0_2026-10-27.md)를
이어 절차의 존재 이유와 제거 대안을 평가했다. 현행 계약에 요구된다는 사실을
필요성의 근거로 사용하지 않았다. 아래 처분은 향후 설계 권고이며, 현재
러너의 검사를 우회하거나 소비된 기록을 재발급하는 변경은 수행하지 않았다.

## 검토와 재현

Claude Opus 5.5 high에는 최소 절차와 제거 후보를, Gemini 4 Argon High에는
그 절차가 놓칠 구체적인 결함과 저렴한 대안 검사를 요청했다. 첫 답변을 받은
뒤 실제 코드·보존 증거의 재현 결과와 상대 모델의 답변을 제공해 각각 한 번
교차 검토했다. 모델별 2회이며 formal capability review나 PASS_GO는 아니다.

Private evidence:
`workspace/private/outputs/s22plus-procedure-necessity-audit-20261028-1/`.
동결 입력, 모델 원문, review inventory, 원본 해시, 두 재현 스크립트와
결과를 보존했다. 이전 감사의 374개 빌드 소스 스냅샷 대조를 재사용했다.
기기·네트워크·프로세스 실행을 차단한 raw 재해석에서 133개 입력 파일의
해시가 유지됐으며, 원래 결과 파일은 수정하지 않았다.

## 단계별 최종 처분

| 현재 단계 | 권고 | 남길 최소 기능과 이유 |
| --- | --- | --- |
| H0 판독기·fixture 수정 때 payload 재빌드 | **제거** | 실제 생성 입력이 불변이면 기존 artifact를 보존하고 새 validator 버전으로 재해석한다. 코드가 이미지에 설치되지 않는 것뿐 아니라 생성 결과에도 영향을 주지 않는지 확인한다. |
| 위 수정 때문에 새 run/key를 만들고 A/B를 반복 | **제거** | 보존된 H0 artifact와 비공개 키를 유지한다. 실제 레시피 변경이나 재현성 주장에 필요한 A/B는 조건부로 남긴다. |
| 변경 범위와 무관한 전체 VM 재실행 | **조건부 실행** | 완전한 기존 증거는 재소비하고, 실제 영향·미실행·증거 부족 사례만 실행한다. 판독만으로 원래 실행의 누락 증거를 만들지 않는다. |
| 동일 범위의 합성·물리 후보 전체 corpus를 항상 두 번 실행 | **통합 후보** | 하나를 정식 자격 경로로 삼고 달라진 baseline·identity·packaging의 영향만 추가 확인한다. 같은 사례명만으로 동등성을 인정하지 않는다. |
| 같은 이미지에 같은 cold admission을 부모와 리뷰어가 반복 | **통합** | 동일 image/consumer/관련 환경에 대한 cold 검증 한 번과 그 입력·출력 결합을 재사용한다. 독립 리뷰는 소비자 논리와 반례를 검토한다. |
| 후보별 독립 prepared-entry 리뷰 | **독립 리뷰 단계 제거, 기계 검사 유지** | 검토된 entry 템플릿·치환 슬롯·binding consumer 아래서 정확한 후보/target/이전 closure를 검사한다. 새 값 종류·제어 흐름·권한 의미가 생기면 delta review한다. |
| 새로운 effect/recovery/admission 의미의 독립 리뷰 | **유지, 범위 제한** | 권한 봉인, 복귀 순서, 잘못된 evidence 수용 등 기존 정상 테스트가 놓친 결함이 있다. 변경된 의미와 연결부를 한 번 검토한다. |
| 이미 잡은 오류의 값싼 negative fixture | **유지** | 단순 marker나 성공 경로로 대체하면 거짓 coverage가 재발할 수 있다. 실제로 6개 반례가 판독기의 잘못된 수용을 드러냈다. |
| 같은 daemon/revocation 동작의 긴 cron 관측 반복 | **조건부 실행** | 최초 동작 증거와 daemon·reload·revocation 변경 때는 필요하다. 관련 입력이 불변인 반복에서는 기존 증거를 재사용한다. |

이 표는 일반적인 모든 검사를 없애는 목록이 아니다. **독립적인 판단과
동일 계산의 반복을 분리**하고, 같은 의미를 후보마다 다시 승인하는 단계를
줄이자는 결정이다. 정당한 H0 수정마다 새 승인이나 모델 검토를 붙이지 않는다.

## P463의 final4에서 final5까지 실제로 줄일 수 있는 일

두 빌드의 187개 소스 입력 중 변경은 `cron_vm_faults.py`와
`s22plus_debian_reboot_qualification_v1.py` 두 파일이었다. 네이티브 소스는
같았다. 수정은 강제 종료 후 mountless dump로 설정 보존을 입증하려던 잘못된
단언을 제거하고, 해당 실패 사례에서 사후 보존을 주장하지 않도록 한 것이다.

[autoboot.sources](../../workspace/public/src/debian/s22plus_initramfs_h0/autoboot.py)는
호스트 검증 코드를 포함한 넓은 집합을 동결했고, 새 빌드는 새 run/key와
payload를 만들었다. 기존 자격 소비자는 이를 정확한 build/source에 결합했다.
따라서 현재 규칙을 그대로 적용하면 전면 재생성이 필요했지만, 그러한 결합
자체가 필요한지는 별도로 평가할 수 있다.

### 원본에서 확인한 분류

| final4 증거 | 실제 상태 | 대안 처리 |
| --- | --- | --- |
| 정상 시나리오 1 + root 사례 51 + runtime 사례 17 | **69개 완료 result 보존** | 이미지·fixture·raw·종료·격리·시간·소스 결합이 맞으면 VM을 다시 실행하지 않고 재소비 |
| apt-download-changed | 선택된 실패 serial과 command는 있으나 사후 단언 예외로 result 미발행 | 누락된 종료·시간·격리 증거를 독립 보존 자료에서 복원할 수 있는지 확인. 부족하면 이 사례만 재실행 |
| apt-orphan-child | helper와 serial이 없고 실행되지 않음 | 해당 주장을 유지하려면 새 실행 증거 필요 |

### 실제로 수행한 재해석

동결된 final4/final5의 `validate_apt_serial`, `validate_config_serial`,
`rejection` 함수 AST가 동일함을 확인하고 원래 함수 본문을 그대로 실행했다.

- 런타임 실패 serial **18개**를 수용했다. 결과 미발행 download 사례도 포함한다.
- 일반 root 거부 serial **48개**를 수용했다.
- 보존된 허위 fault-coverage 반례 **6개**를 모두 거부했다.
- 해석과 관련 해시 재확인은 **0.09154초**였다. 새 빌드·VM·기기 효과는 0이다.

이는 66개 로그의 **부분 의미 확인**이다. 정상 두 부팅의 인증 체인, 특수 root
3건, 원래 프로세스 종료·시간, native 영역 밖의 격리, 전체 build/source
결합까지 이번 스크립트가 재검증한 것은 아니다. 특히 이 실험에 clock-owner나
H4 핸들 검사의 시간을 포함시키지 않는다.

**권고하는 대안:** 기존 이미지를 고정하고 69개 완료 기록을 완전 재소비한 뒤,
download 사례의 누락 증거만 조사하고 orphan 사례를 실행한다. download의
완전한 증거를 복원할 수 없다면 그 사례도 실행한다. 69개 중 추가 문제가
드러나면 해당 범위를 더 검증한다. 따라서 “항상 1–2개만 실행하면 충분”이나
“70개 재사용을 이미 입증했다”는 결론은 아니다.

이 대안을 적용하려면 artifact provenance와 validator provenance를 분리하는
검토된 소비자가 필요하다. 원래 result를 고치거나 새 false 플래그를 붙여
기존 qualification을 통과시키는 방식은 사용하지 않는다.

## 독립 리뷰는 어디서 가치가 있었고 어디서 중복됐는가

### 새로운 의미와 실패 경계에서는 추가 가치가 있었다

P463의 보존된 리뷰는 다음을 발견했다.

- root0400 metadata를 uid42 acquisition이 읽지 못하는 문제.
- 하위 archive만 봉인하고 uid42 소유 상위 cache를 남겨 디렉터리 교체가
  가능한 문제.
- 90초 복귀 창 안에서 cleanup 명령 8개를 동기 실행하는 순서 문제.
  232초는 실제 대기가 아니라 명령당 29초의 시뮬레이션 합계다.
- 의도한 fault 전에 네트워크가 실패해도 해당 fault 검증으로 통과하는 문제와
  다른 VM case의 clock 증거를 수용하는 문제.
- 만료된 0 deadline의 truthiness 처리, 늦은 projection 성공, guard 실패를
  재관측 가능한 read 실패로 잘못 분류하는 문제.

첫 번째 권한 읽기 문제는 실제 정상 경로 VM도 찾을 가능성이 높다. 그러나
상위 디렉터리 봉인, 복귀 순서, 잘못된 증거 결합을 정상 VM 하나가 모두
탐지한다고 볼 수는 없다. 리뷰 후 추가한 회귀 테스트가 지금 통과한다는 사실도
리뷰 전에 같은 탐지기가 있었다는 증거가 아니다.

[P459](S22PLUS_DEBIAN_CRON_P459_H0_2026-10-25.md)의 cached-cron 문제도
이 구분을 보여 준다. 보존된 수정 후 serial은 기존 daemon에서 **92,052ms** 동안
한 번만 호출되고 설정 크기/mtime이 0이며 추가 report가 없었음을 기록한다.
mtime이 0이라는 빠른 검사만으로 daemon의 내부 cache 폐기까지 증명할 수 없다.
다만 관련 구현이 그대로일 때 92초 관측을 매번 새로 수행할 필요는 별개다.

### 후보별 entry 심사는 반복적인 기계 판정이었다

P462와 P463의 실제 entry를 AST로 비교했다. 문자열을 제외한 제어 흐름과
상수는 동일했고, 보존된 리뷰에 기록된 **8개 문자열 변경**과 정확히 일치했다.
변경은 후보명·버전·이전 closure 경로/해시·안내 문구였다.

문자열이 일반적으로 무해하다는 뜻은 아니다. 명령·경로·승인 내용도 문자열이다.
정확히 이 슬롯들의 의미와 consumer를 한 번 검토하고, 이후에는 후보 데이터가
정해진 출처와 맞는지 기계적으로 검사해야 한다.

`prepared-entry-review.json`의 1.227초는 기록된 기계 검사 범위의 시간이지
리뷰어 전체 소요시간이 아니다. 이 단계에서 새 발견이 0이었다는 것만으로
삭제를 정당화하지 않는다. **판정 내용이 이미 검토 가능한 템플릿과 결정적
결합 조건으로 표현된다는 점**이 별도 독립 리뷰를 대체할 근거다.

현재 [Controller.bundle](../../workspace/public/src/scripts/host_tools/s22plus_approved_terminal_tasks_v1.py)은
후보별 독립 review 객체를 요구한다. 향후 구현은 재사용할 template/capability
review와 기계 생성 candidate-binding을 명시적으로 구분해야 한다. 기계 결과에
기존 independent-review 라벨만 붙이는 변경은 적절하지 않다.

### 동일한 전체 admission의 두 번째 실행은 통합할 대상이다

P463 부모 cold admission **148.365초**와 독립 final admission **144.333초**는
정확히 같은 image receipt를 결합하며 둘 다 격리 Python과 준비된 import path가
없는 조건이었다. 독립 측은 원래 `image_valid(artifact_bytes=True)`를 사용했다.

동일 알고리즘을 한 번 더 실행하는 것은 그 알고리즘의 논리 오류에 대한
독립 탐지기가 아니다. 한 번의 cold 실행 결과와 입력 해시·consumer 버전·환경을
재사용하고, 독립 검토자는 소비자의 논리나 반례를 살피도록 **통합을 권고한다**.
입력·환경·consumer가 달라졌거나 실제로 다른 독립 알고리즘을 쓰면 별도 검증의
가치가 생긴다. 효과 직전 현재 바인딩 확인은 계속 필요하다.

144.333초는 이번 표본의 두 번째 계산에 기록된 비용이다. 전체 리뷰 지연이나
프로젝트 전체 절감률은 아니다. review JSON 파일 수 역시 리뷰 호출 수가
아니며, probe와 부분 결과가 같은 리뷰어에게서 나오는 경우가 있다.

## 독립 리뷰를 새로 열 조건

향후 기준은 **변경의 의미**다.

- 새 target/effect/privilege/owner 또는 복구·건강 판정 의미.
- 실제 실행 허가나 결과의 안전성을 결정하는 evidence admission 조건 변경.
- 실행할 코드 선택, timeout, 실패 분류, recovery 동작을 바꿀 수 있는 변경.
- 최초 템플릿·입력 분리·binding consumer처럼 여러 후보가 재사용할 기반 변경.

이 경우 변경된 코드와 실제 연결부를 한 번 독립 검토한다. 수정 후에는 해당
발견과 수정 범위의 delta만 확인한다. 변경되지 않은 전체 이력을 다시 심사하지 않는다.

새 독립 리뷰가 필요하지 않은 예는 순수 설명·표시·진단 수정, admission을
바꾸지 않는 regression fixture 추가, 검토된 슬롯 안의 후보 데이터 치환,
관련 입력이 같은 검사의 재소비다. “모든 Python 수정”, “모든 tightening”,
“모든 import 수정”처럼 확장자나 수정 방향으로 일괄 분류하지 않는다.

P463 final4→5는 실패 후 보존이라는 unsupported claim을 내리는 변경이다.
이 주장이 물리 qualification에서 어떻게 쓰이는지를 좁게 검토할 가치는 있다.
이를 이유로 정상 runtime 전체를 다시 리뷰하거나, 주장하지 않기로 한 보존을
증명하려고 새 journal replay 연구를 의무화할 필요는 없다.

## 현재 mainline 작업에 적용할 순서

1. **현재 빌더의 이미 분리된 부분을 유지한다.**
   [mainline build_initramfs](../../workspace/public/src/mainline/s22plus_canary_h0/build_initramfs.py)의
   명시적 입력 목록에는 `verify.py`와 `vm.py`가 없다.
   [최근 H0 보고서](S22PLUS_MAINLINE_RAM_CANARY_H0_2026-10-27.md)는 같은 config의
   kernel을 실제로 재사용한 사례도 기록한다. vendor의 전체 closure 개편을
   현재 canary의 선행 과제로 만들지 않는다.
2. **검증기 수정은 보존된 artifact부터 재소비한다.**
   실제 바이트 생성 입력이 바뀌었을 때만 필요한 member를 재빌드하고 downstream을
   확인한다. 비용이 큰 새 dependency graph보다 명시적 입력 목록과 현재 builder
   경계를 우선 사용한다.
3. **향후 실행 owner를 준비할 때 entry 템플릿과 기계 binding을 구분한다.**
   변경된 authority/recovery 의미를 검토하고, 후보마다 같은 독립 review를
   재생성하는 설계를 그대로 복제하지 않는다.
4. **최종 cold admission을 한 경로로 모은다.**
   구현자와 리뷰어가 동일 계산을 반복하는 대신 한 검증 산출물을 공유하고,
   리뷰는 새 실패 경계와 반례에 집중한다.

현재 mainline의 unresolved loader 문제나 첫 물리 qualification을 이 감사로
통과시킨 것은 아니다. A90·S20+는 다루지 않았고, 현재 장치 관측·명령은 없다.
위 감사 단계에서는 계약·production 코드와 다른 작업의 dirty 파일을 수정하지 않았다.
이후 승인된 첫 구현은 아래에 별도로 기록한다.

## 모델 의견에서 기각한 부분

- 공개 source hash에서 HMAC 비밀키를 만들자는 Argon 제안은 기각했다.
  비공개 secret 보존/생성과 공개 identity는 별개의 문제다.
- case ID 하나로 clock-owner 오결합을 100% 막거나, H4를 악의적 same-UID 방어로
  단정하는 주장도 기각했다. 평범한 stale record·잘못된 handle·배선 오류가 있다.
- fault marker 하나로 잘못된 원인과 종료 결과에 관한 negative fixture를
  대체하지 않는다. 싼 테스트를 지우려고 새 인증 프로토콜을 만들 필요가 없다.
- 0.09초 재해석을 완전한 71-case admission으로 부르거나, VM 1–2개만으로
  항상 충분하다고 말하지 않는다. 추가 reconsumption 실패가 범위를 넓힐 수 있다.
- 모든 payload 변경에 무조건 전체 리뷰를 요구하거나, 모든 tightening/refactor를
  리뷰 면제로 만드는 양쪽의 과잉 일반화를 채택하지 않는다.

두 모델은 후보별 의례 제거와 재빌드 결합 분리에는 수렴했다. cold admission
통합의 독립성 수준에는 강조점 차이가 남았다. 최종 권고는 모델 투표가 아니라
같은 artifact·같은 consumer의 중복 계산이라는 실제 대조에 근거한다.

## 이번 외부 모델 사용량

| 모델 | 완료 호출 | 입력 토큰 | 출력 토큰 | 호출 경과시간 합계 |
| --- | ---: | --- | ---: | ---: |
| Opus 5.5 high | 2 | 일반 4 + cache 생성 26,612; cache read 0 | 16,922 | 181.540초 |
| Argon High | 2 | 42,017; cache read 0 | 17,750 | 222.352초 |

출력에는 보고된 thinking이 포함된다. 모델별 tokenizer가 다르며 호출 시간
합계는 전체 감사 경과시간이 아니다. Opus 가격표 환산은 USD 0.551352이며
실제 구독 청구액이 아니다. Argon은 금액을 보고하지 않았다.
계정별 호출 전후 quota와 토큰 원본은 private 사용량 장부에 별도로 남겼다.

Argon의 주간 잔량은 95.53→94.43→93.79%로 관측됐으며 합산 감소는 1.74%p다.
Opus 계정 5시간 사용률은 첫 호출 0→5%, 수정 호출 7→7%였다. 계정 전체
수치에는 다른 사용·반올림·갱신 지연이 섞일 수 있으므로 토큰 사용과 구분한다.


## 승인 후 첫 적용: mainline VM 증거 재사용

현재 사용하는 RAM canary 경로에 `vm.py --recheck-run`을 추가했다. 커널·initramfs를
다시 만들거나 VM을 띄우지 않고, 완료된 실행의 원시 응답을 현재 검사기로
재검증한다. 기존 validator의 판정 의미와 장치 실행 경로는 변경하지 않았다.

새 VM 실행은 커널·initramfs·init·manifest·key의 정확한 입력 해시, 요청·응답,
nonce, 명령·serial·stderr와 수집 소스 사본을 남긴다. 완전한 응답 수신과 QEMU
종료 후 capture를 저장하고 그 뒤 의미를 판정한다. 따라서 판독기 예외가 나도
완료된 수집을 재사용할 수 있다. 재검증은 입력·증거의 변경이나 누락을 거부하고
현재 HMAC·신원·PID1·상태·FDT 검사를 수행하며, 별도의 새 출력에 검사기 출처를
기록한다. 원래 source provenance와 결과 파일은 그대로 보존한다.

기존 capture receipt가 없는 실행과 wrong-key negative 실행은 새 재검증 경로에
소급 등록하지 않는다. 재검증은 역사적 VM 관찰에 한정하며 변경된 runtime,
수집기나 VM 환경을 새로 검증했다는 뜻이 아니다. 물리 USB·로더·진입 qualification과
후보별 device binding은 여전히 각 경로가 담당한다. vendor runner를 개편하거나
현재 runner의 필수 검사를 해제하지 않았다.

| 실제 확인 | 결과 |
| --- | --- |
| 기존 kernel/initramfs로 정상 VM 수집 한 번 | PASS, 2.002초 |
| 같은 수집의 새 검사 결과 두 번 | PASS, 0.052633초 / 0.050922초 |
| 두 재검증의 프로세스·socket 호출 | 각각 0회; 호출 시 실패하도록 차단하고 CLI 경로 실행 |
| 원본 capture·source·runtime 입력 | 19개 파일의 내용 해시 유지 |
| 실제 wrong-key VM | 거부 PASS, 1.748초 |
| 집중 시험 | 10개 PASS; 실제 ARM64 protocol fixture, 입력/증거 13종 거부, 새 판독기의 잘못된 health 거부 포함 |
| 저장소 경계 검사 | clean, 관련 시험 12개 PASS |
| 이번 적용의 이미지 재빌드 / 기기 효과 | 0 / 0 |

실행 시간은 이 작은 mainline VM에 대한 측정이며 P463의 전체 qualification
절감 시간으로 확대하지 않는다. 이번 검증에는 정상·wrong-key VM을 각각 한 번
실행했으며, 이후 두 재검증에서는 추가 실행이 없었다.

AGENTS revision 63은 Review/Development 규칙을 긴 대상 표 앞에 이동하고,
검사기 변경 시 불변 산출물·완전한 raw를 재사용한다는 네 줄을 명확히 했다.
기존 capability review 재사용·후보 데이터의 기계 검사·완료 후 범위 확장 중단
규칙이 앞에서 읽힌다. 영구 경계, 대상 권한, 복구·no-replay 규칙과 details pin은
변경하지 않았고 기존 승인·activation을 repin하지 않았다.

Private evidence:
`workspace/private/outputs/s22plus-mainline-vm-reuse-h0-20261028-1/`.
체크리스트 적용: WIRE/SEMANTIC — 실제 응답의 현재 parser 검증과 HMAC/health
거부 확인; PERSIST/AUDIT — 수집과 판정 분리, 원본 보존 및 새 출력 확인;
ARTIFACT — 같은 kernel/initramfs/init 해시 결합 확인. RETURN — 기기 효과 및
복구 경로 변경이 없어 해당 없음. A90·S20+는 건드리지 않았다.

한 번의 독립 검토는 **PASS_GO, findings 0**이다. 정확한 AGENTS·수집/재검증
코드·시험 해시와 README의 재사용 절을 `independent-review.json`에 결합했다.
리뷰어는 동일 VM을 반복하지 않고 기존 결과를 재사용했으며, 부분 수신·프로세스
미종료·수집 중 입력 변경의 receipt 부재와 완전한 수집 뒤 parser 실패의 증거
보존을 네 가지 추가 반례로 확인했다. 이 검토는 H0 기능에 한정되며 device
capability activation이나 실행 승인을 발행하지 않는다.
