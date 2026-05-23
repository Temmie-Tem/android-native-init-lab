# A90 Native Init Development Loop Standard

Date: `2026-05-21`

이 문서는 A90 native init 작업의 표준 개발 루프다. Wi-Fi bring-up처럼 실기기 상태,
vendor 서비스, 보안 경계, rollback 가능성이 모두 중요한 작업은 이 루프를 기본값으로
따른다.

## 기본 원칙

- 현재 worktree와 실기기 상태를 먼저 확인하고, 기억이나 이전 대화만으로 진행하지 않는다.
- 목표와 성공/실패 기준을 먼저 적은 뒤 최소 구현으로 좁게 검증한다.
- 위험 작업은 `read-only`에서 `external ping`까지 gate를 나누고, 각 gate별 금지사항을 명시한다.
- 실환경 검증은 timeout, cleanup, evidence 경로를 항상 포함한다.
- 검증된 단위만 커밋하고, 다음 루프 후보를 남긴다.
- host-side 검증은 목적에 맞는 파일만 대상으로 삼고, firmware/archive/image/log 전체를
  읽는 broad scan을 금지한다.
- 작업 목표와 무관한 삭제, wipe, 파괴적 조작은 수행하지 않는다. 안전장치는 악의 방지가 아니라
  실수, 오판, 환경 차이로 인한 손상을 줄이기 위한 기본 통제다.

## 표준 루프

### 1. 상태 확인

`git`, worktree, host 환경, device 상태, bridge/NCM/server 상태를 확인한다.

필수 확인 항목:

- `git status --short`
- 현재 branch와 최근 commit
- serial bridge 또는 NCM reachability
- device boot mode: native init, TWRP, Android 중 어디인지
- 진행 중인 background server/helper/process 여부
- 이전 루프에서 남은 evidence, tmp output, cleanup 필요 여부

### 2. 목표/조사/기준 정의

작업 전에 목표, 범위, 금지사항, 참고 자료, 성공/실패 기준을 작성한다.

필수 포함 항목:

- cycle label: 예 `v527`
- 작업 목표와 non-goal
- 허용 gate: `read-only`, `deploy-only`, `start-only`, `bring-up`, `external ping`
- 금지사항: 예 `no daemon start`, `no Wi-Fi bring-up`, `no reboot`, `no boot partition write`
- 성공 기준과 실패 분류
- 필요 시 코드베이스 조사 결과와 웹 리서치 출처

### 3. 최소 구현

한 번에 큰 기능을 넣지 않고 관측성, 상태 분류, 안전장치, 기능 변경 순서로 작게 수정한다.

우선순위:

1. 관측성: 로그, manifest, summary, classifier
2. 상태 분류: pass/fail/blocked/needs-approval/needs-cleanup
3. 안전장치: timeout, private output, no-follow write, bounded start, cleanup
4. 기능 변경: helper, host script, native payload, boot artifact 순서

### 4. 정적 검증

실기기 실행 전에 가능한 로컬 검증을 수행한다.

예시:

- Python: `python3 -m py_compile ...`
- C helper: 해당 build command 또는 syntax/build smoke
- 문서: 경로, 명령, approval 문구, evidence 경로 오탈자 확인
- 보안: output permission, symlink-safe write, bounded cleanup 확인
- secret/resource guard: 변경 파일 중심 secret scan, 대형 artifact 제외, chunk 기반 검사 확인

정적 검증은 host 자원을 고갈시키면 안 된다. secret scan이나 로그 검색은
`operations/HOST_VALIDATION_RESOURCE_GUARDRAILS.md`를 따른다. 특히 `firmware/`,
`backups/`, `stage3/*.img`, `tmp/`, 대형 `.tar`/`.img`/`.log`를 기본 검사 범위에
넣지 않는다.

### 5. 실환경 검증

실기기, server, 통합 환경에서 timeout과 cleanup 조건이 있는 제한 테스트를 수행한다.

필수 조건:

- 실행 전 device/host reachability 확인
- command timeout 명시
- live process start 시 stop/cleanup 경로 명시
- evidence output directory 명시
- 위험 gate 상승 시 사용자 승인 문구와 금지사항 재확인

### 6. 결과 문서화

변경 내용, 검증 결과, 실패 분류, 증거, 남은 문제를 기록한다.

필수 기록:

- 실행한 명령
- 결과 label
- evidence 경로
- device 상태 변화
- cleanup 결과
- 다음 판단: 계속 진행, 우회, 중단, rollback, 추가 조사

### 7. 커밋

검증된 단위만 커밋한다.

커밋 전 확인:

- 의도하지 않은 dirty file이 섞이지 않았는지 확인
- Wi-Fi 실험 산출물과 문서/도구 변경을 구분
- secret, SSID password, private token, raw credential이 들어가지 않았는지 확인
- secret 확인은 변경 파일과 staged 파일로 제한하고, repository 전체 `read_bytes()` scan은
  실행하지 않는다.
- commit message에 cycle label과 실제 성격을 반영

### 8. 다음 후보 선정

다음 루프에서 처리할 후보를 정한다.

후보 선정 기준:

- 현재 최종 목표에 가장 가까운 blocker
- read-only로 먼저 줄일 수 있는 불확실성
- cleanup/rollback 없이 반복 가능한 smoke
- 보안 스캔 또는 실기기 안정성에 직접 영향을 주는 항목

## Gate 정의

### `read-only`

상태 수집만 수행한다. 파일 배포, daemon start, service start, Wi-Fi scan/connect를 하지 않는다.

### `deploy-only`

helper나 script만 배포한다. 배포된 helper 실행은 preflight 또는 version check 수준으로 제한한다.

### `start-only`

daemon/service를 짧게 시작해 linker/runtime/registration/crash 여부만 본 뒤 즉시 정리한다.
Wi-Fi scan, connect, link-up, external ping은 하지 않는다.

### `bring-up`

Wi-Fi radio/HAL/service를 실제로 올리고 scan/connect/link-up을 시도한다. 이 단계부터 SSID,
credential, RF 상태, route/DNS, rollback 영향까지 별도 기록한다.

### `external ping`

native init에서 Wi-Fi 연결 후 외부 인터넷 ping을 수행하는 최종 검증 gate다. 성공 시 IP,
route, DNS 여부, ping target, packet loss, cleanup 상태를 evidence로 남긴다.

## Wi-Fi 목표에 적용하는 순서

현재 최종 목표는 native init에서 Wi-Fi 연결 후 외부 인터넷 ping을 통과하는 것이다.

권장 진행 순서:

1. Android/TWRP/native 상태 차이와 vendor service contract 확인
2. SELinux, property, linker namespace, binder/hwbinder, QRTR, firmware path를 read-only로 분류
3. companion service를 순서대로 bounded start-only 검증
4. service-manager/HAL registration start-only 검증
5. scan-only 검증
6. SSID connect/link-up 검증
7. DHCP 또는 static route 검증
8. external ping 검증
9. cleanup/rollback과 재부팅 후 상태 확인

## 승인 문구 원칙

위험 gate는 승인 문구가 작업 범위를 명확히 제한해야 한다.

예시:

```text
approve v527 companion start-only proof only; no service-manager, no Wi-Fi HAL start,
no scan/connect/link-up and no external ping
```

```text
approve vXXX Wi-Fi connect proof to <SSID> only; bounded timeout, cleanup required,
external ping allowed, no boot partition write
```

## Bypass Mode

사용자가 명시적으로 `bypass mode`, `bypass 모드`, 또는 이에 준하는 표현으로 승인하면,
현재 active goal 범위 안의 반복 승인 문구는 이미 받은 것으로 간주한다.
이는 검증 가능한 실험을 빠르게 진행하기 위한 운영 규칙이며, 파괴적 삭제나 목적 밖의
상태 변경을 허용한다는 의미가 아니다.

Bypass mode는 신뢰 기반의 무제한 권한이 아니라 아래 allowlist와 hard stop으로 제한되는
작업 모드다. 명시적으로 허용되지 않은 위험 작업은 bypass mode에서도 허용되지 않는다.
사용자의 bypass 승인은 반복되는 승인 문구를 줄이기 위한 운영 승인으로 해석하며, 작업 목표와
무관한 삭제나 문제 유발 행동까지 승인한 것으로 해석하지 않는다.

신뢰 경계는 다음처럼 해석한다:

- 작업자는 목표 달성에 필요한 조작만 수행한다.
- 악의적 삭제, 고의적 장애 유발, 증거 은폐, 복구 경로 훼손은 어떤 모드에서도 허용되지 않는다.
- bypass mode는 “반복 승인을 생략한다”는 의미이지 “목표 밖 작업까지 맡긴다”는 의미가 아니다.
- 복구 가능한 boot image 교체라도 artifact, target, rollback 경로가 확인되지 않으면 진행하지 않는다.
- 실수 가능성을 줄이기 위해 destructive-looking command는 목적, 대상, rollback 가능성을 기준으로 한 번 더
  자체 점검한다.

운영 기준은 다음처럼 고정한다:

- patch upload, 배포 후 검증, boot image 변경, reboot, rollback 확인은 TWRP/recovery로 복구 가능한
  범위라면 bypass mode에서 승인된 루틴으로 본다.
- 이 승인은 malicious delete, 고의 장애 유발, 불명확한 partition write, 사용자 데이터 삭제까지
  확장되지 않는다.
- boot image 관련 작업은 산출물, SHA256, target partition, known-good rollback image가 확인된 경우에만
  진행한다.

Bypass mode에서 별도 승인 없이 진행할 수 있는 작업:

- `sudo`가 필요한 host reachability, NCM, bridge, deploy 보조 작업
- helper/script 배포와 version/preflight 실행
- bounded `start-only` smoke와 즉시 cleanup
- Wi-Fi `bring-up`, scan, connect, link-up, external ping 검증
- 검증된 native init boot image를 known boot partition에 flash하고 재부팅 후 검증하는 작업
- 위 작업을 위한 제한적 patch upload와 실기기 검증
- TWRP로 복구 가능한 범위의 boot image 변경, 재부팅, rollback 검증
- cleanup, rollback 검증, evidence 수집

Bypass mode에서도 반드시 지킬 조건:

- 모든 live action은 timeout을 둔다.
- daemon/service start는 bounded 실행과 cleanup 경로를 포함한다.
- patch upload, boot image update, reboot은 복구 가능한 범위에서만 수행한다.
- 실행 명령, 결과 label, evidence 경로를 남긴다.
- 작업 결과에는 “bypass 승인으로 수행”했음을 기록한다.
- 실패 시 같은 위험 작업을 무한 반복하지 않고 실패 분류를 남긴다.

Bypass mode의 controlled patch upload 조건:

- repo에서 빌드했거나 SHA256으로 식별한 helper, script, native payload, boot artifact만 올린다.
- destination은 `/cache/bin`, `/cache/tmp`, 명시된 evidence 경로, known boot partition처럼
  현재 루프에서 필요한 경로로 제한한다.
- upload 전후 artifact path, destination, SHA256, version 또는 smoke 결과를 기록한다.
- 기존 파일을 덮어쓸 때는 대상이 이전 루프 산출물인지 확인한다.
- broad delete, recursive wipe, 불명확한 cleanup은 하지 않는다.

Bypass mode의 controlled boot image update 조건:

- artifact path와 SHA256을 기록한다.
- target partition이 known boot partition인지 확인한다.
- rollback boot image와 TWRP/recovery path를 확인한다.
- flash 후 native init, serial bridge 또는 NCM reachability를 검증한다.
- 실패하면 새 실험을 이어가지 않고 rollback 또는 recovery 진입 가능성을 먼저 확인한다.

Bypass mode에서도 별도 확인이 필요한 hard stop:

- `userdata` format 또는 대규모 사용자 데이터 삭제
- 알 수 없거나 검증되지 않은 partition write
- 검증되지 않은 boot image flash
- recovery/vbmeta/efs/sec_efs/modem/persist/key 계열 write
- credential, token, private key, Wi-Fi password의 dump 또는 문서화
- 외부 네트워크로 broad exposure를 여는 변경
- timeout 없는 daemon 장시간 실행
- rollback 불가능하거나 복구 경로가 없는 변경

## 완료 판단

루프 완료는 “작업을 했다”가 아니라 “증거로 확인됐다”를 의미한다.

완료 조건:

- 목표 범위의 성공/실패 기준이 evidence로 판정됐다.
- cleanup 또는 rollback 상태가 확인됐다.
- 남은 문제와 다음 후보가 기록됐다.
- 커밋 가능한 변경만 남았다.

최종 목표 완료 조건:

- native init 상태에서 Wi-Fi 연결 성공
- 지정 SSID 연결 또는 명시된 테스트 AP 연결 성공
- device IP와 route 확보
- 외부 인터넷 ping 성공
- evidence 문서와 재실행 명령 기록
- cleanup/rollback 경로 확인
