# S22+ P453: P452 파일 읽기 후보 H0 qualification

상태: **H0 준비 완료 — READY_H0_PRELIVE_ONLY**.
기기 명령이나 grant 소비는 없다. [분석과 설계](S22PLUS_MOUNTKERNFS_P453_ANALYSIS_H0_2026-10-23.md)는
구현 전에 `73c4006324`에 기록했다.

## 선택

P453 `v0.16.0-rc.2`는 기존 `root-evidence` / `autoboot-pair` reader의 새 선언이다.
정상 Android 복구로 닫힌 P452의 정확한 early/runtime 두 파일만 선택한다.
기존 raw capture와 N/A 소유권, changed-boot Android32 health, P452의 실제
artifact/run/source를 H0에서 재도출해 새 reader와 결합했다.

두 파일의 전체 허용 크기는 각각 16,384/15,616 bytes다. 기존 metadata 검사,
partition-only RAM RO, mountless home-block view와 별도 원본 A 복구를 유지한다.
새 mount, journal replay, filesystem write, repair, installed Debian 실행 또는
writable-history admission은 없다. 파일이 없거나 dirty view이면 그 상태를 남기며
P452가 실행되지 않았다고 결론 내리지 않는다. 내용이 읽혀도 각 파일 인증과
boot/nonce 결합이 별도로 통과해야 한다.

## 검증

- P451 대비 reader runtime source 165개의 bytes가 모두 같다. 새 run identity와
  exact P452 경로 선언만 바뀌었다. 기존 consumed source/review는 변경하지 않았다.
- 실제 전체 A/B build가 byte-identical이며 원래 artifact qualifier와
  `image_valid(..., artifact_bytes=True)`가 통과했다. Boot-only AP는 32,266,281 bytes다.
- 별도 virtual A/B helper도 동일하고 ARM64 static ELF로 확인했다. 새 reader가
  실제 P452 정상 ARM64 VM producer의 인증된 early/runtime bytes를 읽는 clean 및
  missing-runtime 두 case가 통과했다. 이 fixture는 물리 P452 파일이 아니다.
- 두 case 모두 전체 검증 범위의 disk evidence가 전후 동일하다. Partition RO,
  파일별 bytes/status 및 mount/write 부재를 실제 producer/consumer가 검사했다.
- Reader 18개, retrieval 9개, task boundary 6개, 합계 33개 검사가 통과했다.
  변경 Python과 private H0 helper의 compilation도 통과했다.

변경은 선언·현재 capability routing과 문서에 한정한다. Root-evidence policy는
prospective P453와 consumed P451을 구분하고 P452 두 경로의 기존 의미를 유지한다.
Common details, target contract, reader/runtime/recovery 구현은 변경하지 않았다.

## 준비와 남은 실행 조건

독립 capability 검토는 현재 host source 140개와 unchanged runtime source 165개,
원래 artifact consumer, 전체 build/package, P452 closure 및 실제 VM 증거를
확인해 `PASS_GO`, findings 없음으로 완료됐다. 별도 좁은 검토도 구체적인 offline
task, 모든 source snapshot과 미실행 ordinary-terminal entry를 통과시켰다.

원래 `prepare_offline`을 command acquisition이 차단된 H0 환경에서 실행했다.
정확한 P452 pair의 root-evidence 1회 / 1800초 attended proposal과 host/runtime
snapshot이 결합됐다. Entry는 기존 사용자, 정상 터미널의 권한 조건, 이전 P452
closure, 현재 task/review/source 및 실제 반환 승인을 검사한 뒤 원래 V3 CLI만
호출한다. Entry는 실행하지 않았고 operator-approval, grant, operation, 실행 로그
또는 F1 owner는 없다.

Offline proposal은 retained target/recovery 정보만 사용하며 현재 건강 상태를
증명하지 않는다. 후속 실기는 자신의 정확한 반환 승인과 현장 attendance,
사용 가능한 Download 복구 및 원래 runner의 새 lane/host/Android 검사가 필요하다.
이번 H0에는 실행 승인을 반환하거나 grant를 여는 단계가 없다.

Private evidence base:
`workspace/private/outputs/s22plus-mountkernfs-p453-h0-20261023-1/`.
`inputs.json`은 script 분석 입력, `reader-inputs.json`은 새 reader 선언이다.
원시 build/VM 기록, source/consumer 검증과 분석 fixture를 보존한다.
A90·S20+와 기존 46개 다른 변경 경로는 그대로 유지한다.
