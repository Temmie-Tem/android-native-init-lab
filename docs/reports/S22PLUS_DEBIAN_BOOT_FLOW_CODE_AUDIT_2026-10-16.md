# S22+ Debian 부팅 순서·대기 조건·기존 경로 결합 감사

기준: 2026-10-16 KST, `ecb813e6c712957069b2f37aec6f0e5bcdf0de1b`를 기준으로 한
현재 작업트리 소스와 해시로 고정된 설치 Debian 아카이브. 대상은 S22+ FYG8만이다.
상태: **H0_CODE_AUDIT_COMPLETE**. 실행 코드·정책 변경이나 기기 명령은 없다.

현재 사용자 공간의 주 부팅 경로는 대부분 순차적이다. 직접 확인된 장애 후보는
여러 단계의 호스트/USB 의존, 시험용 종료점, 이전 파일 상태를 가정한 루트 검사,
그리고 두 경로를 그대로 연결할 때 생기는 중복 초기화·기록 파일 충돌이다.
이것들은 다음 후보의 구성에서 해결해야 할 사항이다. 과거 기기 실패의 원인을
이번 정적 분석만으로 확정하지 않으며, P430/P431의 성공·소비·정상 복귀는 유지한다.

## 1. 실제로 실행되는 두 경로

[P430의 물리 증거](S22PLUS_DEBIAN_P430_P431_PERSISTED_EARLY_PID1_RUN_2026-10-16.md)는
다음 시험 경로에 해당한다.

```text
Debian /init: PID1, RAM root
  -> fyg8-prepare supervisor -> worker: 76개 모듈, 결과 수집
  -> file-log supervisor -> worker:
       보호된 루트 검사 -> native_data RW -> 기록 -> 나머지 6개 모듈
       -> 마지막 파일 기록 -> close/unmount/보호 복원 시도
  -> fyg8_stop: 계속 대기
```

`fyg8.py:file_script()`는 file-log의 반환값을 저장한 뒤 성공 여부와 관계없이
`fyg8_stop`으로 간다. 따라서 마지막 줄을 지나도 설치된 init을 실행하지 않는다.
실기기 파일은 마지막 pre-unmount 기록까지 증명하며, 두 번째 worker의 반환이나
unmount 성공은 별도 미증명이다. 이 종료점은 파일 시험의 의도된 범위다.
[생성 스크립트](../../workspace/public/src/debian/s22plus_initramfs_h0/fyg8.py#L232),
[대기 함수](../../workspace/public/src/debian/s22plus_initramfs_h0/fyg8-dev#L2).

기존 P425 계열의 현재 통합 소스는 다른 순서를 가진다.

```text
Debian /init -> platform 74개 -> 부모 측정 -> exec integrated-init(PID1)
  -> ACM gadget/descriptor -> 호스트 integrated-start 수신
  -> 초기 증거 전송 -> UFS 8개 -> 증거 전송
  -> 보호된 루트 검사 -> RW 활성화 -> RAM witness로 루트 전환
  -> 호스트 CONTINUE -> 설치된 SysVinit
  -> 첫 sysinit hook: init 증거 -> 호스트 START
  -> rcS wrapper -> rc2 wrapper -> init/cron/sshd 120초 관찰
  -> 호스트 RELEASE 및 ACK -> ACM unbind -> 같은 g1을 NCM으로 전환
  -> 호스트 SSH health -> 고정 shutdown -> 물리 original-A 복귀
```

이 경로에는 별도 상주 native 서비스 관리자가 없다. 단, 부팅의 여러 전진 조건을
호스트 관찰 프로토콜이 소유한다. Debian 초기 PID1을 이미 확보했다는 사실만으로
이 조건들이 자동으로 없어지지 않는다.
[초기 생성기](../../workspace/public/src/debian/s22plus_initramfs_h0/integrated.py#L39),
[실제 PID1 진입점](../../workspace/public/src/debian/s22plus_initramfs_h0/integrated-init.c#L114),
[호스트 요청 소비자](../../workspace/public/src/scripts/revalidation/s22plus_debian_integrated_observation_v1.py#L14).

## 2. 진행을 막거나 지연하는 구체적 조건

| 조건 | 실제 동작과 영향 | 다음 구현에서의 처리 |
| --- | --- | --- |
| P430의 마지막 `fyg8_stop` | 성공한 파일 시험도 설치된 init으로 진행하지 않는다. | 새 후보의 정상 Debian 부팅 continuation으로 교체한다. 소비된 후보는 변경하지 않는다. |
| UFS 이전 USB 요청 | `integrated-init`은 gadget·tty·바인딩·`request(3)`와 초기 증거 송신을 모두 마친 뒤 UFS child를 실행한다. USB 부재/호스트 부재/전송 오류가 저장소 준비까지 막는다. | P430의 storage-first 순서를 채택하고 부팅을 관찰 연결과 분리한다. |
| 설치된 init 이전 CONTINUE | 루트 전환 witness의 `dh_exec_init()` 첫 동작이 인증된 CONTINUE 대기다. | 새 자동 부팅 범위에서는 앞서 승인된 실행 소유권에 따라 로컬로 진행하도록 설계한다. |
| rcS 이전 START | 첫 동기 sysinit hook이 init proof 송신·START 수신·durable START를 완료해야 반환한다. | init 증거 기록을 유지하며 서비스 시작을 외부 연결과 분리한다. |
| NCM 이전 관찰·RELEASE | 원래 `/etc/init.d/lab-usb`는 RAM overlay로 무동작 처리된다. rc2와 120초 관찰 후 RELEASE/ACK가 있어야 NCM이 시작된다. | 서비스와 접속을 먼저 제공하고 관찰을 후속 판정으로 배치하는 새 흐름을 검토한다. 같은 gadget의 단일 소유권은 유지한다. |
| 보고 중단 뒤 로컬 완료 | durable START 이후의 일부 보고 I/O 오류만 `de.off`로 전환된다. 서비스 관찰은 계속될 수 있지만 완료 후 영구 대기하여 NCM으로 가지 않는다. | 로컬 완료와 네트워크 시작의 관계를 명시적으로 다시 설계한다. |
| 공유 300초 기기 시한 | USB 대기·root 검사·서비스 시작·관찰이 한 시한을 쓴다. 관찰 직전 130초 미만이 남으면 즉시 거부한다. | 기능 시작과 측정 시간을 구분해 실제 필요한 유한 예산을 정한다. 기존 시한을 임의로 갱신하지 않는다. |

근거:
[USB 앞단](../../workspace/public/src/debian/s22plus_initramfs_h0/integrated-init.c#L117),
[CONTINUE](../../workspace/public/src/native-init/s22plus_debian_handoff_witness_v1.inc.c#L44),
[START](../../workspace/public/src/native-init/s22plus_debian_handoff_hook_v1.c#L168),
[USB 무동작 overlay](../../workspace/public/src/scripts/revalidation/s22plus_debian_handoff_profile_v1.py#L91),
[120초·보고 중단·RELEASE](../../workspace/public/src/native-init/s22plus_debian_handoff_observer_v2.inc.c#L143).

현재 V1의 네 요청은 실행 권한과 검증을 함께 담당한다. 새 흐름은 관련 효과를
부팅 전의 정확한 후보·유한 승인·원샷 소유권에 묶어야 한다. 기존 프로토콜에서
인증 대기만 삭제하거나 결과를 성공으로 바꾸는 변경은 적절하지 않다.
[현재 통합 범위](../operations/S22PLUS_DEBIAN_INTEGRATED_V1.md)는 이 네트워크 선행
조건과 순서를 포함하므로, 자동 진행으로 바꾸는 구현과 채택 범위는 함께 검토해야 한다.

## 3. 현재 저장소 상태가 만드는 실제 다음-run 충돌

### P430의 정상 증거 파일이 기존 root admission에 없다

현재 `MUTABLE`은 lab 디렉터리, boot-count, 제한된 로그·seed만 열거한다.
`var/lib/lab/s22-evidence-<run>`은 없다. 루트 검사는 전체 entry 수를
`archive table + 4 + 허용된 추가 항목`과 정확히 비교한다.
P431이 읽은 P430 파일은 실제로 존재하는 추가 항목이므로, 같은 루트의 다른
검사 항목이 모두 맞더라도 현재 통합 admission을 그대로 재사용하면 통과할 수 없다.
이는 파일시스템 손상 판정이 아니라 허용된 산출물과 다음-run 입력 규칙의 불일치다.

[mutable 선언](../../workspace/public/src/scripts/revalidation/s22plus_debian_handoff_profile_v1.py#L29),
[추가 항목 검사](../../workspace/public/src/native-init/s22plus_debian_handoff_root_v2.inc.c#L18),
[전체 개수 비교](../../workspace/public/src/native-init/s22plus_switch_root_v1.c#L101).
파일 파일럿과 journal-recovery의 clean-root 비교도 같은 추가 항목 검사와 개수
조건을 사용한다. 고정 mountless reader는 다른 경로이며 P431의 성공은 유지된다.

현재 C 함수들을 그대로 포함한 좁은 host/ARM64 harness에서 다음을 재현했다.

| 입력 | 전체 entry | 허용된 extra | 실제 판정 |
| --- | ---: | ---: | --- |
| 나머지 비교가 일치하는 작은 기준 fixture | 8 | 1 | 0 |
| 같은 fixture에 정상 형태의 evidence 파일 하나 추가 | 9 | 1 | `EPROTO`(71) |
| 별도 mutable 검사에 mode-0644 `boot-count=2` | 해당 없음 | 해당 없음 | `EPROTO`(71) |

이 harness는 실제 경로 탐색·mutable·admission C를 사용한다. immutable 비교는
일치하는 fixture 값이며 lost+found 경로만 private fixture로 치환한다. GPT,
파일시스템 checker나 기기 binding 전체를 시뮬레이션한 결과는 아니다.
초기 harness의 공유 directory cursor로 두 번째 entry 수가 0이 되는 결함을
발견해 그 결과는 폐기했다. 수정본은 독립 descriptor, 반복 개수 동일성 및
정확한 +1 증가를 확인한 뒤 위 결과를 얻었다. 원본·수정본 출력은 모두 보존했다.

`boot-count`도 현재 두 바이트 `1\n`만 허용한다. P430 때문에 발생한 새 오류는
아니지만, 일반적인 후속 Debian 부팅을 구성할 때 계속 사용할 수 있는 상태 모델은
아니다. 증거 파일과 카운터의 정상 생명주기를 정확히 선언해야 하며, 이전 파일을
지우거나 전체 root 비교를 완화해 통과시켜서는 안 된다.

### 초기 기록기와 설치된 기록기를 단순 연결하면 파일명이 충돌한다

초기 파일 기록기와 설치된 Debian의 `de_begin()` 모두 같은 run에서
`var/lib/lab/s22-evidence-<run>`을 `O_CREAT|O_EXCL`로 생성한다. 초기 파일은
version-3 pilot 형식이고 설치된 기록기는 별도의 durable 형식이다. 앞의 파일을
보존한 채 뒤의 기록기를 그대로 호출하면 `EEXIST`로 시작하지 못한다.
설치된 기록기의 실패는 첫 sysinit hook의 영구 대기로 이어진다.
[초기 파일 생성](../../workspace/public/src/debian/s22plus_initramfs_h0/file-log.c#L176),
[설치된 파일 이름](../../workspace/public/src/scripts/revalidation/s22plus_debian_evidence_v1.py#L18),
[설치된 파일 생성](../../workspace/public/src/native-init/s22plus_debian_evidence_v1.inc.c#L171).

두 생산자의 실제 이름 규칙이 같은 것을 대조하고, private 일반 파일에서 배타적
생성이 `EEXIST`를 반환하며 이전 바이트를 보존하는 것도 확인했다. 다음 후보는
한 부팅에서 단계별로 구분되는 bounded 기록이나 하나의 명확한 소유 기록 형식을
선택해야 한다. 기존 파일에 임의로 이어 쓰는 방식은 현재 형식과 검증을 만족하지 않는다.

## 4. 병렬성·작업 종료·반복 초기화

P430의 shell은 첫 supervisor 반환을 기다린 뒤 두 번째 supervisor를 실행한다.
각 supervisor에는 worker가 하나 있다. worker 미수집·시한·wait 오류에서는
supervisor가 대기하여 shell이 다음 helper로 넘어가지 않는다. 저장소 checker도
정확한 자식을 수집하기 전에는 RW 단계로 진행하지 않는다.
[supervisor](../../workspace/public/src/debian/s22plus_initramfs_h0/failure-observer.h#L37),
[checker 종료](../../workspace/public/src/debian/s22plus_initramfs_h0/file-log.c#L58).
커널 내부 probe나 실제 blocking syscall의 활동까지 직렬임을 주장하지 않는다.

통합 경로도 platform, 측정, UFS, checker, rcS, rc2를 차례로 기다린다. 설치된
실제 아카이브의 `.legacy-bootordering`은 `/lib/init/rc`의 `CONCURRENCY=none`을
선택한다. marker가 있는 실제 조건과 없는 반대 조건을 추출한 shell 결정문으로
실행해 각각 `none`과 `makefile`을 확인했다. 오래된 `.depend.*`에는 lab-network와
이미 제외된 서비스가 남아 있으므로 marker를 무작정 제거해 병렬화를 켜지 않는다.
[이미지 구성 이유](../../workspace/public/src/debian/s22plus_v1/device/prepare.py#L145).

rcS/rc2 내부에는 정상적인 daemon 시작이 있다. 예를 들어 mdev는 background로
시작하고 cron·sshd는 계속 살아 있어야 한다. 이는 이전 부팅 helper가 정리되지
않은 상태와 구분된다. retained rc는 개별 script 실패를 전부 실패 exit로 합산하지
않고 마지막에 0으로 끝나므로, rc 반환만으로 성공을 선언하면 안 된다. 현재
init·cron·sshd의 실행 파일·PID·root·생존 검사는 이 차이를 확인하는 유효한 검사다.

다음 사항은 단순한 병렬화나 함수 연결로 해결되지 않는다.

- `sw_no_children`과 `sw_userspace`는 루트 전환 전에 다른 사용자 프로세스를
  거부한다. 임의의 background USB/로그 daemon을 먼저 시작하면 `ECHILD`/`EBUSY`
  조건에 걸린다. 필요한 준비 자식을 종료·수집한 뒤 PID1이 진행해야 한다.
- P430은 76개 storage prefix 뒤 6개 client를 로드한다. 통합 코드는 74개 platform
  뒤 USB, 그 뒤 8개 UFS이다. P430 완료 후 기존 platform/UFS loader를 재호출하면
  이미 존재하는 모듈을 거부한다. 모듈 집합·순서·로그 parser를 한 선언으로 맞춰야 한다.
- P430은 supervised `STORAGE_READY` 로그, 통합 consumer는 직접 자식의
  `PLATFORM_READY`와 별도 UFS 로그를 기대한다. 부모 관계·로그 형식·해시를
  함께 바꾸지 않고 결과만 재사용할 수 없다.

[사용자 공간/자식 검사](../../workspace/public/src/native-init/s22plus_switch_root_common_v1.inc.c#L149),
[통합 로더](../../workspace/public/src/debian/s22plus_initramfs_h0/integrated-prepare.c#L62),
[storage-first 선언](../../workspace/public/src/scripts/revalidation/s22plus_debian_file_first_plan_v1.py),
[통합 consumer](../../workspace/public/src/scripts/revalidation/s22plus_debian_integrated_protocol_v1.py#L35).

반대로 과거 native의 `sw_workers()`/`three-workers-reaped` 경로는
`S22_SWITCH_ROOT_LIBRARY`에서 기존 main이 제외되므로 통합 entry에서는 호출되지
않는다. 현재 entry는 `early-children-settled`를 사용한다. 이 코드를 현재 blocker로
잘못 지목하지 않는다. 초기 PID1의 FYG8 argv 허용도 이미 수정·P430 검증된 상태다.

## 5. 다음 구현의 좁은 범위와 유지할 조건

다음 구현은 P430의 준비 순서를 기준으로, Debian 초기 PID1이 보호된 storage
admission을 거쳐 저장소 root와 설치된 init·서비스로 계속 진행하는 한 경로다.
호스트 관찰 응답이 UFS·init·서비스·네트워크의 시작을 각각 막는 구조를 바꾸고,
진행 상태는 USB가 없어도 회수할 수 있는 파일에 남긴다. 서비스 관찰 때문에
네트워크 자체를 늦추는 순서도 재검토한다.

먼저 정상 기존 evidence 파일과 후속 boot-count의 정확한 admission 규칙,
초기/설치된 기록기의 소유권·이름·형식, 중복 없는 모듈 구성과 child 정리를
정리해야 한다. 새 자동 부팅의 효과 소유권과 유한 시한은 기존 승인·복구 체계에
명시적으로 연결한다. 현재 V1을 우회하거나 소비된 후보를 재사용하는 변경은 없다.

타깃/GPT/root 신원, clean-only 검사, immutable 파일 검증, 제한된 mutable
surface, 자식 종료 확인, 단일 gadget 소유권, 실제 서비스 생존, 원샷·복구 규칙은
필요한 조건으로 유지한다. 현재 첫 기기 결과에 없는 실패 원인을 더 조사하는 일을
이 기능 구현의 추가 선행 조건으로 만들지 않는다.

검증 자료는 private `s22plus-debian-boot-flow-audit-20261016-1/`에 있다.
45개 소스 snapshot, retained root script index, 실제 생성 overlay, host/ARM64
C 판정 재현, 파일명 충돌과 rc 선택 재현을 보존했다. 분석은 기기 I/O 없이 완료했고
원래 46개 작업 항목은 유지했다. 이 감사는 설계 근거이며 새로운 기기 권한은 아니다.
