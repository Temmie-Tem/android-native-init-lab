# S22+ 진행 절차 비용과 검증 효율 감사

Date: 2026-10-27 KST. Scope: S22+ FYG8의 P448–P463 진행 과정과 현재
mainline RAM USB canary 준비에 적용할 개선안. 기준 커밋은
`32c38611df4989f69272de089491692b0af39807`이다.

**일부 절차는 기능 진전 대비 비용이 과하다. 가장 확실한 문제는 H0 검사 코드와
실행 이미지의 과도한 결합, 실제 입력을 놓치는 테스트, 긴 검증과 짧은 응답
제한시간의 결합이다.** 장치 식별·재실행 방지·복구 검증을 줄이는 것보다 이
결합을 풀고 검증 위치를 바꾸는 편이 근거가 강하다. 전체 작업시간 중 몇 퍼센트가
낭비인지는 현재 기록으로 산출할 수 없다.

이 문서는 분석과 제안이다. 계약, 러너, 승인, 소비된 기록은 변경하지 않았다.
기기 명령은 실행하지 않았으며 A90·S20+는 분석·변경 대상에 포함하지 않았다.
진행 중인 mainline 및 일시 중지된 boot-journal 작업의 파일도 수정하지 않았다.

## 조사 범위와 검증 방법

- P448–P463의 16개 번호, P458 후속 실행을 포함한 17개 실행 보고서를 조사했다.
  7월 [P264 빌드 지연 회고](S22PLUS_FYG8_P264_QUALIFICATION_LATENCY_POSTMORTEM_AND_IDENTITY_SPLIT_H0_2026-07-25.md)와
  9월 [비례성 감사](S22PLUS_VALIDATION_PROPORTIONALITY_AUDIT_2026-09-15.md)는
  재발 유형을 비교하는 자료로 사용했다. 당시 문제를 현재 미해결 문제로 간주하지 않았다.
- Claude Opus 5.5 high와 Gemini 4 Argon High에 동일한 동결 패킷을 주고
  각각 독립 분석을 받았다. 그 후 현재 코드·Git 이력·보존된 결과로 반박할
  내용을 모아 각각 한 차례 수정 검토를 받았다. 외부 모델의 의견은 실행 심사나
  `PASS_GO`가 아니다.
- P463 두 빌드의 원본 소스 스냅샷 각각 187개, 총 374개 해시를 확인했다.
  VM 결과·빌드 결과·과거 cold/warm 측정값도 원본 JSON과 로그에서 대조했다.
- 현재 코드의 검증 재사용, 시간 제한, UTF-8 외부 프로필 처리에 관련된
  기존 집중 테스트 20개가 0.098초에 통과했다. 첫 호출은 tests 디렉터리에서
  실행해 한 모듈의 import 경로 오류가 있었고, 저장소 루트에서
  `PYTHONPATH=tests`로 바로잡았다. 이를 제품 결함으로 집계하지 않았다.
- 커밋 간격, 파일 수정시각, grant 전체 구간을 엔지니어의 실제 작업시간으로
  환산하지 않았다. 병렬 VM의 개별 소요시간 합계도 전체 경과시간과 구분했다.

Private evidence:
`workspace/private/outputs/s22plus-procedure-cost-audit-20261027-1/`.
동결 패킷, 출처 해시, 두 모델의 원문과 수정 답변, 검증 코드 스냅샷,
`verified-measurements.json`, `frozen-source-verification.json`, 집중 테스트
로그를 보존했다. 원시 장치 식별자나 외부 모델 대화 원문은 공개 문서에 넣지 않았다.

## 실제로 얻은 진전과 반복된 비용

| 구간 | 얻은 사실과 기능 | 관측된 추가 비용 |
| --- | --- | --- |
| P448–P451 | 설치된 Debian PID1/rcS 진입의 부분 증거, early/runtime 파일 회수, journal 상태 정리 | P448 이후 reader → replay → reader의 3개 별도 실행 |
| P452–P455 | hostname 완료와 mountkernfs 진입 경계, 인증된 파일 쌍과 이후 루트 비교에 필요한 이력 | 다시 reader → replay → reader의 3개 별도 실행. 회수된 runtime 형식에는 per-script 패킷이 없어 정지 위치를 더 좁히지 못함 |
| P456–P458 후속 | live Debian 서비스·SSH, 복귀 후 파일 영속성, 일반 재부팅과 두 번의 Debian 부팅 | P458 첫 실행은 호스트 deadline 결함으로 N 전송 전에 중단. Download 제어는 이미 발생했음 |
| P459–P462 | 실제 cron 작업, 디스크 cron 설정의 재부팅 후 소비·은퇴, 자동 Download/A 복귀, hello 설치·실행·보존 | 후보 준비·VM·review 반복과 post-A 건강 관측 중단. 이 네 후보는 첫 물리 시도에서 각 기능을 입증함 |
| P463 | APT 기능은 NO_PROOF. 원래 A 복귀와 좁은 건강 재관측 경로는 입증 | N 전송 후 호스트 UTF-8 처리 실패. native_data는 이후 M=40/needs-recovery로 관측됨 |

P449–P451과 P453–P455는 합쳐서 **6개 실행과 12개 N/A 전송**이다. 이는
관측·복구 구조의 실제 비용이다. 그러나 확보한 초기 파일, journal 상태,
이후 정확한 루트 승인에 쓰인 이력까지 무가치한 작업으로 분류할 수는 없다.
P457의 영속성 확인 역시 독립된 제품 증거다.

P452의 grant부터 closure까지 약 19.5시간은 물리 복귀 지연을 포함한다.
이 구간을 전부 검증 시간이나 전부 운영자 부재 시간으로 분류할 근거는 없다.
17개 실행을 성공/낭비의 이분법으로 나누거나 커밋 간격으로 낭비율을 계산하지 않는다.

## 확인된 병목과 개선 우선순위

### 1. 검사 코드 수정이 실행 이미지와 전체 VM 재실행으로 번진다

가장 강한 사례는 [P463 준비](S22PLUS_DEBIAN_APT_P463_PREPARE_2026-10-27.md)의
`build-final-4` → `build-final-5`다. 두 빌드의 187개 입력을 대조하면 변경은
`cron_vm_faults.py`와 `s22plus_debian_reboot_qualification_v1.py` 두 파일뿐이다.
네이티브 소스는 같지만 새 run/key와 helper, hook, entry, writer, witness,
initramfs 해시가 모두 달라졌다. 앞선 로그에 69개 PASS 행이 있었는데도,
잘못된 H0 사후 보존 단언을 고친 뒤 71개 VM 사례 전체를 다시 실행했다.

원인은 [autoboot.py](../../workspace/public/src/debian/s22plus_initramfs_h0/autoboot.py)의
`sources()`가 디렉터리의 모든 `.py/.c/.h`와 호스트 검증기를 함께 수집하고,
`prepare()`가 기본적으로 새 UUID/key를 만들며, `build()`가 그 입력을
모두 동결하는 구조다. 이어서
[image_binding](../../workspace/public/src/scripts/revalidation/s22plus_debian_autoboot_qualification_v1.py)은
전체 build source와 `runtime_sources`, VM 결과와 정확한 build를 결합한다.
UUID가 소스 해시에서 계산되는 것은 아니다. 광범위한 입력 집합과 새 빌드
절차가 함께 이미지 정체성을 바꾸는 것이다.

P459도 합성 corpus와 물리 후보 corpus에 같은 이름의 45개 사례가 있다.
각각 시간 필드가 있는 12개 실패 사례의 합계는 719.806초와 715.185초다.
병렬 실행이므로 이 합계를 두 번의 직렬 대기시간으로 제시하지 않는다.
또한 run/key와 baseline이 달라졌으므로 이름이 같은 사례를 곧바로 재사용할
수 있다는 뜻도 아니다.

**개선안:** 앞으로 만들 mainline 빌더에서는 실제 payload를 바꾸는 입력,
산출물을 해석하는 검증기·fixture, 실행 권한·복구 입력을 처음부터 구분한다.
검증기만 바뀌었을 때 동일한 불변 산출물에 새 검증 결과를 붙일 수 있어야 한다.
과거 결과의 버전이나 해시를 바꿔 현재 검증인 것처럼 만들지 않는다.
기존 vendor 경로에 적용하려면 별도 검토된 변경이 필요하지만, 중지된 그
스택을 이 감사 때문에 다시 열 필요는 없다.

**검증 기준:** 순수 검증기/문서 수정이 payload 해시나 빌드를 불필요하게
바꾸지 않는지, 실제 payload 입력 수정은 반드시 산출물 검증을 무효화하는지
기존 빌더 검사에서 확인한다. 총 시간 절감률은 아직 미측정이다.

### 2. 많은 검증보다 실제 입력을 먼저 통과시키는 것이 중요하다

[P463 실행](S22PLUS_DEBIAN_APT_P463_RUN_2026-10-27.md)은 71개 ARM64 사례와
독립 리뷰를 통과했지만 첫 호스트 네트워크 조사에서 중단됐다. 외부 Ethernet
프로필의 한글 이름을 포함한 네 필드를 모두 ASCII로 해석했기 때문이다.

실행 전 커밋 `cdb988b64b`의 `SharedNetwork` fixture를 확인하면 inventory는
자기 프로필 또는 빈 목록만 반환한다. 실제
[configure_network](../../workspace/public/src/scripts/revalidation/s22plus_debian_apt_access_v1.py)의
외부 프로필 검사 분기는 그 fixture에서 다뤄지지 않았다. 이는 ARM64 검사
71개의 무용성을 뜻하지 않고, 다른 입력 계층 하나가 빠졌다는 증거다.

현재 코드는 라벨만 UTF-8로 해석하고 interface/MAC/address는 엄격하게
유지한다. 외부 프로필·인코딩·충돌 거부 테스트도 이미 추가돼 이번에 통과했다.
같은 테스트를 다시 만들 필요는 없다.

**개선안:** 새 기능의 실제 producer 출력과 실제 consumer를 비용이 큰
빌드·기기 실행 전에 연결한다. 예를 들어 기존 호스트 프로필 목록의 파싱은
장치 NCM 생성 없이도 확인할 수 있다. 실제 endpoint의 현재 소유권과 상태는
효과 시점에 다시 확인한다. mock 응답을 production의 기대값 생성기로만
만들면 양쪽이 같은 가정을 공유할 수 있으므로, 보존된 실제 출력과 독립적인
동작 조건을 함께 사용한다.

P459의 cold ordinary-entry 검사도 빌드 드라이버가 가려 주던 module path
문제를 잡았다. 이 유형의 검사는 검증 목록의 끝보다 앞에 둘 가치가 있다.

### 3. 검증 캐시는 개선됐지만 새 프로세스와 8초 응답 창은 따로 봐야 한다

[P458 수정](S22PLUS_P458_DEADLINE_RECOVERY_H0_2026-10-25.md)의 보존된
최종 reconciliation은 다음을 기록한다. 결과 동등성과 누락 없는 2,071개
의존성 확인까지 통과한 기록이며, 초기 pending 결과와 구분했다.

| 경로 | 측정 시간 |
| --- | ---: |
| 기존 전체 qualification | 15.859초 |
| 최초 ticket 생성 | 16.559초 |
| 같은 owner의 ticket 재사용 | 0.045846초 |
| P462의 별도 cold image admission | 93.888초 |
| P463의 별도 cold image admission | 148.365초 |

현재 [Qualification](../../workspace/public/src/scripts/revalidation/s22plus_native_qualification_v1.py)과
[ReadSet](../../workspace/public/src/scripts/revalidation/device_action_read_dependencies_v1.py)은
이 재사용을 구현하고 있다. 변경된 입력을 거부하며 장치·권한·grant·journal
검사를 캐시하지 않는다. 따라서 “모든 frame에서 전체 검사를 다시 한다”는
주장은 틀리다.

한편 [persistent Gateway](../../workspace/public/src/scripts/host_tools/s22plus_approved_terminal_persistent_v1.py)의
`response_line()` 기본값은 8초이고 요청마다 새 Python backend를 만든다.
[continue_task](../../workspace/public/src/scripts/host_tools/s22plus_approved_terminal_tasks_v1.py)는
bundle과 continuation binding을 확인한 뒤 intent·spawn·response를 낸다.
일반 autoboot 복귀 continuation의 새 Adapter는 cold qualification을 받을 수
있다. recovery/health-only 경로는 별도로 일부 qualification을 생략하므로
모든 RPC에 148초가 걸린다고 일반화할 수 없다.

P458 후속·P459·P460의 응답 불확실성은 실제 기록이다. 위 admission 시간은
그 호출들의 pre-dispatch 지연을 직접 계측한 값은 아니다. 구조상 불일치와
증상은 확인됐지만 당시 지연의 정확한 분해는 남아 있다.

**개선안:** 이 경로를 다음 작업에서 실제 사용할 때 기존 로그에 bundle,
binding, intent, spawn, response 시각을 붙여 먼저 확인한다. 필요한 경우
원래 owner에 귀속되는 접수 상태와 장시간 admission 완료를 구분한다.
접수 응답은 장치 실행 허가가 아니며, 효과 전 전체 필수 검사는 그대로 수행한다.
상주 backend 전환이나 무조건 긴 timeout은 별도의 비용·상태 위험이 있다.

P458의 “명령 전에 이미 만료된 departure 창”은 수정됐고 현재 집중 테스트도
통과했다. 이를 다시 미해결 문제로 제시하지 않는다. 이미 발행한 intent 뒤에
시간 창을 새로 시작하거나, 응답이 늦었다고 같은 제어를 재전송해서도 안 된다.

### 4. 변경 범위보다 넓은 리뷰 무효화와 후보별 진입 리뷰가 강제된다

[source_paths](../../workspace/public/src/scripts/revalidation/s22plus_native_task_v3.py)는
선택 operation을 인자로 받지 않는다. 모든 literal import를 분기 안까지
탐색하고 여러 profile의 정책·artifact 경로를 추가한다. `capability(profile=...)`는
review 파일을 선택하지만 요구하는 source path 집합은 공통이다. 선택 경로
밖의 변경이 자격에 영향을 줄 수 있는 결합은 코드에서 확인된다.

또한 Controller의 `bundle()`은 후보별 `prepared-entry-review.json`과
`PASS_READY_H0_AND_UNEXECUTED_ENTRY`를 요구한다. 루트 계약의
“변하지 않은 capability review 재사용” 원칙만 읽고 이 검사를 생략할 수 없다.
현재 기계가 요구하는 조건과 미래에 줄일 수 있는 조건을 구분해야 한다.

**개선안:** 새 경로를 설계할 때 변경된 실행·복구 의미에 대한 독립 리뷰와
후보 데이터의 기계적 자격 확인을 분리한다. 기존 경로를 바꾼다면 실제 도달
가능한 코드, 공통 상위 정책, 동적 선택까지 포함하는 범위를 입증하고 한 번
리뷰한다. 파일 수만 보고 hash를 삭제하거나 기존 review를 자동 repin하지 않는다.

어느 리뷰가 몇 분을 소모했고 어떤 결함을 찾았는지 완전한 집계는 없다.
“세 겹의 리뷰이므로 두 겹은 낭비”라는 숫자 기반 결론은 채택하지 않는다.

### 5. 비용을 줄이라는 개발 규칙이 초기 전달본에서 빠져 있었다

현재 루트 [AGENTS.md](../../AGENTS.md)는 427줄, **38,491바이트**다.
이 대화에 처음 제공된 AGENTS 본문은 `routine in-s`에서 끝났고, 실제 파일의
첫 **32,768바이트**가 정확히 그 문자열로 끝난다. `Development and Commit
Discipline`은 byte offset **33,862**부터 시작한다.

따라서 초기 전달본에는 다음 개발 규칙이 빠져 있었다: 작은 변경 우선,
동일 입력의 성공한 검증 재사용, 문서 변경에 image build 금지, 완료 기준
통과 후 확장 중단. 이번 감사에서는 파일을 직접 읽어 보완했다. 이는 이
세션에서 관측한 전달 상태이며 모든 Codex 환경의 설정값을 단정하는 것은 아니다.

**개선안:** 일상적인 자율 작업·검증 재사용·완료 기준을 루트 앞부분으로
옮기고, 이미 SHA로 결합된 공통 세부 문서와 중복되는 예외 설명을 줄인다.
새로운 “과잉 방어 금지” 문장을 맨 뒤에 덧붙이는 것만으로 해결하지 않는다.
공통 계약 재배치는 경계 의미를 보존하는 독립 리뷰를 한 번 거쳐야 한다.
기존 소비된 binding은 그대로 보존한다.

### 6. 관측과 상태 복구 구조가 연구 비용을 키운다

더티 ext4의 checkpointed home-block view에는 journal에만 있는 최신 파일이
보이지 않을 수 있다. P449–P451과 P453–P455의 3단계 실행이 이를 드러낸다.
그러나 dirty 상태에서도 early 파일은 회수됐고, replay 및 이후 파일
회수는 다음 루트 승인에 필요한 증거를 제공했다.

고정 Android superblock D0 구현은 Git 이력상 2026-10-25에 추가됐다.
10월 23일 P453에서 그 도구를 먼저 썼어야 한다고 평가하는 것은 시점 오류다.
`RECOVER=1`만으로 read의 무가치함이나 replay 권한을 추론할 수도 없다.

**개선안:** 현재 [mainline 목표](../../GOAL.md)가 선택한 RAM PID1/USB canary처럼
첫 부팅 증거를 writable root와 분리한다. 이후 protected storage 단계에서
실패 관측·journal 상태·루트 승인 단위를 함께 설계한다. 기존 read와 replay를
한 owner로 합치는 것은 새로운 효과·복구 설계이므로 단순 최적화가 아니다.
일시 중지된 vendor boot-journal을 현재 canary의 선행 과제로 되살리지 않는다.

post-A 건강 read의 반복 중단도 실제 운영 비용이다. P462의 readiness 수정은
뒤의 privileged read를 다루지 못했고, P463의 좁은 교체 bracket은 한 실제
사례에서 작동했다. 해당 호스트 경로를 다시 쓸 때 검토된 재관측을 재사용하되,
모든 읽기 오류를 retry하거나 전송·제어 재실행으로 확대하지 않는다.

## 유지할 검증과 축소를 검토할 검증

| 처분 | 대상 | 판단 근거 |
| --- | --- | --- |
| 유지 | 효과 직전 target/artifact/rollback, owner·intent·no-replay, 최종 건강 | 잘못된 장치, 중복 효과, 미완료 복구를 막는 실제 경계 |
| 유지하고 앞당김 | 실제 producer/consumer, ordinary-entry cold import, 변경된 실패 경로 | P463 입력 누락과 P459 import 결함처럼 비싼 후반 실패를 앞에서 찾을 수 있음 |
| 재사용 | 동일 owner의 immutable qualification, 관련 입력이 같은 성공 검사, 범위가 같은 capability review | 이미 구현된 cache와 루트 계약에 근거함 |
| 검토 후 분리 | 검증기/fixture 변경과 payload identity, profile 공통 closure, 준비 데이터별 독립 리뷰 | 반복 비용은 확인됐지만 현재 강제 검사를 삭제할 권한은 아님 |
| 보류 | RAM canary와 무관한 vendor journal, 원인 규명 전체, 일반 package 정책 재설계 | 현재 성공 기준에 필요하지 않음 |

검증이 실제로 유효했던 반례도 유지한다. P459 리뷰는 cron의 초 단위 캐시로
인한 재실행 위험을 찾았고, VM은 daemon 준비 경합을 드러냈다. cold import는
정상 실행 진입점의 모듈 누락을 잡았다. P463의 negative corpus는 목표 fault에
도달하지 않은 거짓 coverage와 journal에만 남은 데이터를 잘못 해석한 단언을
드러냈다. 이런 검증을 줄이는 대신 검사 자체의 변경 때문에 다른 계층 전체를
재생성하는 일을 줄여야 한다.

## 다음 세 작업에서 평가할 최소 변경안

1. **계약 전달 정리:** 개발·완료 규칙을 앞에 배치하고 중복 설명을 정리하는
   문서 변경을 하나의 단위로 검토한다. 내용·링크·경계 의미를 확인하면 된다.
   이 문서 변경을 이유로 kernel/image를 다시 빌드하지 않는다. 현재 binding의
   무효화 영향은 명시하고, 소비된 기록을 재발급하지 않는다.
2. **mainline H0 준비:** 실제 payload 입력과 검증 입력을 분리하고, 실제
   호스트 입력 및 cold entry를 먼저 검사한다. 불변 산출물의 재해석은 기존
   결과에 검증기 버전을 덧붙인 새 결과로 기록한다. 관련 없는 vendor 전체
   corpus를 mainline 완료 조건으로 가져오지 않는다.
3. **선택된 실행 경로 확인:** 사용할 connector의 admission/response 구간을
   H0 fixture에서 계측하고, 필요한 변경만 검토한다. 이후 별도로 승인된
   기기 실행이 있을 때 기존 timeline에 검증·대기 구간을 구분해 기록한다.
   이 감사를 검증하기 위한 추가 기기 실행은 만들지 않는다.

평가 지표는 기존 build/result/change description에 필요한 만큼만 남긴다:
payload와 무관한 재빌드 수, 같은 입력의 검사 재실행 수, 새 결함을 발견한 단계,
cold admission과 응답 지연, 실제 승인/물리 대기 구간. 새 대시보드·데몬·승인
계층이나 모든 수정마다 작성하는 별도 보고서는 필요하지 않다.

변경 영향이 불명확하면 관련 producer와 consumer부터 확인한다. 모든
미분류 변경에 전체 저장소 build와 모든 검사를 요구하는 새 일반 규칙은 만들지
않는다. 실제 경계·복구 의미가 달라질 때 필요한 리뷰는 유지한다.

## 외부 모델 의견의 채택과 기각

두 모델 모두 빌드/검증 결합과 실제 호스트 입력 coverage의 불균형을 주요
문제로 지적했다. 원본 소스와 산출물 대조 후 두 지적은 더 강한 근거를 얻었다.

반면 다음 초기 의견은 수정 라운드에서 철회됐거나 최종 판단에서 제외했다.

- 전체 시간에서 H0 또는 장치 시간이 지배적이라는 단정, 50–75% 절감 예상.
- 17개 실행 중 기능 추가가 아닌 관측·복구를 모두 낭비로 분류하는 계산.
- 나중에 생긴 D0를 과거 작업에 소급 적용하거나 dirty면 자동 replay하라는 제안.
- N이 없던 P458을 무효과로 분류하거나 N이 전송된 P463을 pre-effect로 분류해
  소비된 grant 재사용을 암시하는 해석.
- 현재 강제되는 prepared-entry 리뷰·corpus를 즉시 삭제하는 제안.
- 패킷에 실제 포함된 P450/P454/P458 후속 보고서가 없다는 Argon의 주장.
- 새 기능에 이전 테스트 전체를 무조건 요구하거나, 이미 고친 UTF-8 테스트를
  다시 추가하거나, RAM canary에 별도 storage D0를 추가하는 제안.

최종 mainline 구현은 [현재 기술 평가](S22PLUS_MAINLINE_SERVER_ASSESSMENT_H0_2026-10-27.md)를
따른다. 이번 비용 감사가 kernel config, watchdog, firmware, USB, 메모리
예약 또는 복구 방식에 대한 새로운 기술 결정을 대신하지 않는다.

이번 리뷰 자체도 비용의 사례다. 긴 동일 패킷을 읽은 두 모델이 모두 잘못된
일반화를 했고, 원본 증거에 기반한 짧은 수정 라운드가 이를 바로잡았다.
앞으로 routine delta 리뷰에는 변경 함수, 관련 실패 원본, 기존 결론과 달라진
입력을 우선 전달하고, 긴 이력은 필요한 쟁점에만 추가하는 편이 낫다.
모델 둘의 동의만으로 지적을 확정하지 않는다.

## 모델 사용량

| 모델 | 완료 호출 | 입력 토큰 | 출력 토큰 | 호출 경과시간 합계 |
| --- | ---: | --- | ---: | ---: |
| Claude Opus 5.5 high | 2 | 일반 입력 4 + cache 생성 95,338; cache read 0 | 31,700 | 346.400초 |
| Gemini 4 Argon High | 2 | 83,317; cache read 0 | 47,175 | 581.353초 |

출력 토큰에는 보고된 thinking이 포함된다. 두 모델의 토큰 수는 서로 다른
tokenizer 기준이다. 호출 시간은 각각의 합이며 병렬 진행된 전체 감사 시간과
같지 않다. Claude CLI의 합산 list-price 환산은 USD 1.39672이며 실제 구독
청구액이 아니다. Argon은 금액을 보고하지 않았다.

Claude 계정의 5시간 사용률은 첫 호출 5→9%, 수정 호출 15→21%였고 주간은
7→8%, 8→8%였다. 동시 사용과 반올림·갱신 지연이 있어 이 증분 전체를 이
감사에 귀속하지 않는다. Argon 첫 호출의 주간 잔량은 99.77→96.03%였다.
수정 호출은 96.03→95.52%였으며, 두 완료 호출 구간의 합산 감소는 4.25%p다.
이 역시 계정 전체 관측값이다. 모든 호출별 원본 수치를 private 사용량 장부에 보존한다.

Argon 사용량 UI 진입 중 자동완성으로 의도하지 않은 짧은 분석이 시작되어
즉시 중단한 1건도 별도 기록했다. 해당 호출의 사전 quota와 토큰 수는 확보하지
못했으며 0으로 처리하지 않았다. 그 응답은 감사 결론에 사용하지 않았다.
