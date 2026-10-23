# P457: P456 기록의 반환 후 영속성 확인 준비

P456은 같은 실기 부팅에서 Debian 초기/설치된 PID1, 최소 초기화, runlevel 2,
120초 service 관측과 같은 boot의 SSH를 증명하고 Android로 건강하게 종료됐다.
그러나 shutdown 요청 수락과 USB departure는 clean filesystem shutdown이나
반환 후 파일 보존을 증명하지 않는다. P457의 목적은 다음 writable boot 전에
기존 mountless reader로 P456의 정확한 early/runtime 파일을 읽고 비교하는 것이다.
서버 작업은 종료했고 A90와 S20+는 이번 변경 범위 밖이다.

## 선택한 최소 단위

새 reader identity만 등록하고 기존 `autoboot-pair`의 두 경로와 권한/크기 제한을
유지한다. Native_data partition RO와 mountless library reader를 재사용한다.
파일시스템 mount, write, journal replay, repair, installed init 실행이나 일반
Debian reboot를 추가하지 않는다. 현재 superblock state, RECOVER와 orphan은
파일 내용과 별도로 보고하며, clean bit를 writable-root admission으로 해석하지
않는다. 원래 N 1회와 원본 A 1회, 최종 Android 건강 검사 경로를 유지한다.

현재 reader capability selector와 정책의 prospective pointer를 새 P457 검토로
옮긴다. 이전 review, consumed grant, artifact, raw capture 및 journal은 변경하지
않는다. 이 H0 단위의 완료 기준은 실제 이미지 재현성/패키지 검증, 새 reader의
ARM64 동작 확인, 독립 검토 및 실행 전의 구체적인 유한 제안이다. 실기는 별도
반환 승인과 물리 참석, 현재 target/health/recovery 검사를 요구한다.

## 비교 기준과 증거 한계

P456의 closed operation을 원래 consumer로 다시 검증하고, 실제 SSH raw capture를
물리 writer의 key/run/source identity로 인증했다. Early 10,972 bytes와 runtime
3,456 bytes를 private fixture로 보존했다. 두 채널의 boot/nonce join은 MATCH,
highest authenticated stage는 SERVICES_120S_COMPLETE다.

Early live 채널은 RAM mirror다. 이 fixture는 H0 reader의 parser와 전달 경로를
검증할 뿐 반환 후 저장장치의 파일 존재/내용을 증명하지 않는다. 나중의 보호된
실기 capture를 별도로 인증하고 각 파일의 전체 길이/해시/바이트를 live snapshot과
비교해야 한다. Runtime은 snapshot 뒤 정상적으로 늘어날 수도 있으므로 불일치를
곧바로 corruption이나 비실행으로 해석하지 않고 인증된 prefix/후속 records를
구분한다. Missing home-block 파일도 비실행 증거가 아니다.

## 검증과 실행 상태

실제 A/B 이미지가 바이트 단위로 일치하고, 패키지는 boot-only archive 및 원래
image consumer 검증을 통과했다. AP 크기는 32,266,281 bytes다. Init, child와 VM
reader는 ARM64 static ELF다. Reader runtime source 165개는 P455와 모두 동일해
기존 전체 negative corpus를 재사용했다. 새 ARM64 clean/missing-runtime 경우는
실제 P456 live 바이트를 regular-file disk에 넣어 실행했고, 두 경우 모두 전체
allocated disk가 byte-identical이며 mount/write가 없었다. 관련 테스트는 reader
18개, retrieval 9개, task 6개로 총 33개 통과했다.

독립 capability 검토는 PASS_GO, findings 없음이며 현재 원래 consumer가 host
source 141개와 runtime 165개를 확인했다. 새 candidate의 문자열 배치에 따른 두
library mode-pointer relocation도 같은 `a` 문자열을 가리키는 것으로 검증했다.
원래 offline preparation으로 단일 `root-evidence`, 1800초, budget 1, attended
task/proposal 및 source snapshot을 준비했고 READY_H0_PRELIVE_ONLY다. 실제
연결 건강 검사는 실행 직전 원래 runner가 수행한다.

별도 실제 task/entry 검토는 PASS_READY_H0_AND_UNEXECUTED_ENTRY, findings 없음이다.
원래 offline task consumer와 source snapshot, P456의 건강한 종료와 동일 target/A
binding, 일회용 진입점의 여섯 guard 경우를 확인했다. 진입점은 실제 반환 승인
기록을 요구하고 원래 grant opener와 참석 실행 CLI를 한 번씩 호출한다. 기존
일반 터미널 경로를 준비했으며 entry 자체는 실행하지 않았다.

검토/실행 identity는 기존 별도 변경을 포함한 frozen working-tree 바이트에 묶이며
commit만으로 전체 소스 동일성을 주장하지 않는다. Grant, operator approval,
preflight attempt, operation 및 실행 log는 없다. 이 결과는 H0 준비 완료이며
실제 파일 영속성, clean shutdown, 일반 Debian reboot나 새로운 device authority를
증명하지 않는다. 저장된 제안에 대한 실제 반환 승인과 물리 참석이 다음 조건이다.

Private H0 evidence는
`workspace/private/outputs/s22plus-autoboot-persistence-p457-h0-20261024-1/`에 있다.
원래 P456 실기와 healthy closure는
[P456 결과](S22PLUS_DEBIAN_MINIMAL_P456_RUN_2026-10-24.md)에 보존한다.
