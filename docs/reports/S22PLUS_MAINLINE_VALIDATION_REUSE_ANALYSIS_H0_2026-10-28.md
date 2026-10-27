# S22+ mainline 후보 변경과 검증·리뷰 재사용 분석

Date: 2026-10-28 KST. Base HEAD: `78e1a2e076` plus the explicitly frozen,
concurrently developed mainline draft. **H0 analysis and successor proposal;
not capability qualification, activation or device authority.**

**지금 추가 캐시나 후보 승인 체계를 구현할 근거는 부족하다.** 측정한 이미지
결합 검사는 기존 캐시로 반복 비용이 작았고, 첫 후보의 정확한 리뷰 결합은 그
후보에 유효하다. 실제 후속 후보가 필요할 때 검토된 생성·검증 방식과 허용된
데이터 슬롯을 재사용하도록 분리하는 것이 다음 변경의 범위다.

이 분석은 [절차 필요성 감사](S22PLUS_PROCEDURE_NECESSITY_AUDIT_H0_2026-10-28.md)
이후의 작업이다. 분석 시점의 mainline 실행/복구 owner는 작성 중인 미활성 초안이었다.
현재 생산 코드, 정책, 승인과 다른 작업의 파일을 수정하지 않았다. 이미지 빌드·패키징·VM·연결 장치 작업은 없다. A90·S20+도 다루지 않았다.

## 실제 측정과 반례

공개 소스 16개를 동결하고 실제 `s22plus_mainline_profile_v1.image_binding`을
기존 완성된 private qualification에 적용했다. 계측된 함수와 그 실제 기록
판독기·캐시를 사용했으며, subprocess/socket/device-file 접근과 연구 디렉터리
밖의 쓰기는 차단했다. 금지된 시도는 없었다.

| 호출 | 시간 | records.read_bytes를 통과한 바이트 |
| --- | ---: | ---: |
| 프로세스 검증 캐시가 빈 첫 호출 | 0.111028초 | 90,546,875 |
| 같은 프로세스 반복 1 | 0.002073초 | 907,509 |
| 같은 프로세스 반복 2 | 0.001914초 | 907,509 |
| 같은 프로세스 반복 3 | 0.001917초 | 907,509 |
| 캐시 유지 + AP envelope 확인 | 0.142448초 | 907,509 + 별도 AP 읽기 |

시간에는 읽기 집계와 추가 무결성 해시 계측 비용이 포함된다. 마지막 행의 AP
transport 읽기 바이트는 위 카운터에 포함되지 않는다. OS 저장장치 캐시가 빈
측정이나 전체 qualification·세션·물리 부팅 비용이 아니다. 이 결과는 해당
반복 경로에 새 캐시를 추가할 근거가 없다는 판단에만 사용한다.

기록 결합의 실제 반례는 다음과 같다.

- 바이트 동일 qualification JSON을 새 private 경로에 복사하고 그 바깥 receipt를
  맞추면 수용된다. 내부 artifact 결합은 계속 검사된다.
- 바이트 동일 package result JSON을 새 경로에 복사하고 새 qualification에서
  참조하면 `candidate evidence was not covered by retained entry review`로 거부된다.
  런타임 산출물과 기존 리뷰는 바꾸지 않았다.

두 번째 결과는 첫 리뷰가 path/size/hash를 정확히 결합한다는 증거다. 우회나
현재 제품 결함으로 분류하지 않는다. 관측한 원본 기록 13개와 새 fixture 3개의
내용을 확인했다. 원시 계측 JSON의 `protected_original_records=16`은 이 합계로,
원본만 16개라는 뜻이 아님을 `interpretation.json`에 명시했다.

## 실제 코드에서 확인한 재사용 경계

분석 시점의 profile은 loader/package/init manifest와 loader/entry 시험 receipt가
retained entry review의 정확한 artifact 목록에 있어야 한다. `qualify()`에도 첫
리뷰와 시험 디렉터리 이름이 지정돼 있다. 이것은 첫 후보의 닫힌 범위이며,
일반적인 리뷰 재사용 지침이 이 기계 검사를 해제하지 않는다.

`build_initramfs.py`는 빌드마다 새 32바이트 키를 만들고 ID·MAC·serial을 파생한다.
키만 달라도 init, initramfs, loader, AP가 달라질 수 있다. 따라서 향후 새 키를
허용한 후보는 단순 문서 변경이 아니며 실제 새 바이트를 자격 검증해야 한다.

토론 중 생성된 `s22plus_mainline_task_v1.py`도 별도로 동결했다. 그 draft는 명시적
MODULES와 문서/스크립트 목록을 사용하며 mainline capability에 vendor 전체
`source_paths()`를 호출하지 않는다. 공유 파일의 전체 pin은 남지만, 그 때문에
실제로 반복 리뷰가 얼마나 발생하는지는 측정하지 않았다. 이를 이유로 범용
closure 분석기나 함수별 분리 작업을 추가하지 않는다.

공유 task 파일은 다른 작업에서 계속 변경됐다. 측정에 사용한 `image_binding`과
`unchanged` 함수 AST가 최종 확인 시에도 같은 것은 확인했지만, 이 분석이 최신
전체 owner를 검증했다는 뜻은 아니다.

## 변경별 필요한 작업

아래 표는 향후 작업 분류를 위한 분석이며 현행 계약·러너를 대체하지 않는다.

| 변경 | 재빌드 | 검증 재사용과 새 확인 | 독립 리뷰 |
| --- | --- | --- | --- |
| 문서·표시만 변경 | 이미지 없음 | 내용·링크·diff; 실제 표시 코드면 해당 문법·동작 확인 | AGENTS의 좁은 면제 조건을 충족할 때 생략. 기계 파싱 필드 변경은 별도 분류 |
| 오프라인 검사기, 수용 의미 불변 | 이미지 없음 | 불변 artifact/raw 재사용, 해당 fixture와 Python 문법 확인 | 실제 도달하는 실행 핵심 변경 여부를 현행 규칙으로 판단; 문서 면제가 코드 refactor에 자동 적용되지는 않음 |
| 검사기의 증거 수용 의미 변경 | 검사기만이면 이미지 없음 | 보존 증거 재해석과 바뀐 수용 경계의 양성·음성 사례. 증거가 부족한 사례만 추가 실행 | 변경된 수용 의미와 연결부를 검토 |
| 별도로 검토된 후속 키 슬롯 | init→initramfs→loader→AP; 고정 kernel/DTB 재사용 | 변경된 실제 blob의 배치·내부 멤버·새 해시에 묶인 시험. 무관한 host 시험 재사용 | machinery와 허용 슬롯이 그대로면 리뷰 재사용 가능. 현재 첫 후보에는 아직 없는 경로 |
| loader/kernel/init 실행 코드 | 실제 생성 입력이 바뀐 계층과 downstream | 달라진 실행 바이트·동작을 검증하고 무관한 시험은 재사용 | 현재 첫 범위 밖의 변경은 검토 필요. 모든 코드 변경에 전체 VM/전체 리뷰를 강제하는 일반 규칙은 아님 |
| 권한·전송·복구·건강 의미 | 이미지에 영향이 있을 때만 | 관련 상태 머신, 실패·정리·no-replay 검증 | 해당 권한·실행·복구 범위를 검토 |

H0 재해석은 device grant가 필요 없고 소비된 grant를 수정하지 않는다. 실제 효과
시에는 정확한 target/boot/artifact, 건강, authority, 복구 경로, 원래 deadline과
남은 예산 및 one-shot journal 상태를 확인한다. 향후 **실제로 활성화된** 유한
범위가 후보 변경을 이미 허용한다면 해시마다 사람 승인을 다시 받지 않는다.
현재 첫 후보의 한 작업·정확한 이미지 grant가 그 범위를 암묵적으로 얻지는 않는다.

A/B 패키징 2→1은 archive/qualification/evidence-acceptance의 생성기·소비자
변경이다. 실제로 바뀌지 않은 장치 권한·복구 의미까지 자동 확대하지 않는다.
현재 소비자는 두 copies를 요구하므로 producer만 고칠 수 없으며, 변경은 계속
보류한다. 다음에 필요한 포장 작업에서 비용을 기록하면 충분하다.

## 후속 구현의 최소 제안과 종료 기준

구현 트리거는 실제 두 번째 후보가 필요하고 첫 실행 owner/closure의 검토된
경계가 정해졌을 때다. 그 전까지 아래 제안은 H0 설계 노트로 남긴다.

1. 최초 허용 데이터는 **고정 길이 키와 고정 형식의 파생 ID·MAC·serial**로
   한정한다. network tuple, kernel, config, DTB, cmdline, protocol, UDC/port,
   loader 배치, recipe와 toolchain은 고정한다. network 변화는 별도 검토된
   확장으로 다루며 `is_private`만으로 허용하지 않는다.
2. 기존 리뷰 기록은 검토한 생성·검증 machinery와 허용 슬롯을, qualification은
   실제 후보의 정확한 출력과 시험 증거를 결합하도록 후속 소비자를 설계한다.
   새 일반 인증서·cache·daemon 계층은 만들지 않는다. 첫 후보의 exact 경로와
   과거 리뷰·소비 기록은 유지하고, 기존 기록을 새 의미로 relabel하지 않는다.
3. 후속 자격에는 실제 AP 내부 member, key/ID 파생 관계, 크기·배치, 비슬롯 입력,
   검토된 시험 harness와 해당 새 loader 해시의 결합을 요구한다. 경로 이동을
   허용하더라도 private 경로/파일/내용 검사를 유지하며 path 검사만 삭제하지 않는다.
4. 향후 시험은 첫 exact 후보 유지와 허용된 새 키/기록 이동의 양성을 포함한다.
   비슬롯 소스·kernel/config/DTB/network 변화, `vm=True`, key/파생값 불일치,
   다른 blob 또는 미검토 harness의 시험 결과, AP 내부 member/A-B 불일치와
   미해결 review findings를 거부한다. 소비·불확실한 효과·예산 소진을 새로운
   키나 run ID로 해제할 수 없어야 한다. **이 후속 경로와 그 시험은 아직 미구현이다.**

이번 단위의 완료물은 위 분류표·측정·반례·후속 경계다. 내용·출처·diff 확인 후
종료하며 현재 first-candidate 코드 수정이나 추가 VM/벤치마크를 붙이지 않는다.

## 모델 토론과 사용량

Claude Opus 5.5 high와 Gemini 4 Argon High에 각각 1차 분석과 상대 답변/새 코드/
반례를 포함한 교차 검토를 요청했다. 모델별 2회이며 formal safety review가 아니다.
전체 성능을 작다고 일반화한 주장, 검사기 변경 시 grant 갱신, 모든 실행 코드
변경의 전체 재시험, A/B 변경을 곧바로 장치 권한 변경으로 분류한 주장은 교정했다.

| 모델 | 입력 토큰 | 출력 토큰(보고된 thinking 포함) | 계정 관측 |
| --- | ---: | ---: | --- |
| Opus | 일반 4 + cache 생성 30,576; cache read 0 | 10,975 | 5시간 사용률 11→12%, 다음 호출 13→13% |
| Argon | 45,587; cache read 0 | 13,096 | 주간 잔량 92.42→91.46→90.94% |

Opus의 CLI 가격표 환산은 USD 0.464124이며 실제 구독 청구액이 아니다. Argon은
금액을 보고하지 않았다. 계정 수치에는 동시 사용·반올림·갱신 지연이 섞일 수 있다.
Argon 첫 응답은 SUCCESS로 완성됐으나 CLI가 종료하지 않아 출력 보존 후 그
격리 프로세스만 종료했다. 모델 요청을 재실행하지 않았고 토큰·모델 완료 시간과
CLI 정리 시간을 분리 기록했다. 두 번째 호출은 정상 종료했다.

Private evidence:
`workspace/private/outputs/s22plus-mainline-reuse-design-h0-20261028-1/`.
동결 소스와 후속 snapshot, 계측 스크립트/결과, fixture, 모델 원문, 사용량 및
해석상의 한계는 각각 source manifest, `measurements.json`, `interpretation.json`,
모델별 `run.json`, `usage-summary.json`에 보존했다.
