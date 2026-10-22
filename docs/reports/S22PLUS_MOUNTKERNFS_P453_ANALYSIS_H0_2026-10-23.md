# S22+ P453: mountkernfs 호출 경로 분석과 다음 읽기 후보 설계

상태: **분석 H0 완료; P453 mountless reader 구현·qualification 전 설계**.
대상은 FYG8 S22+ 하나다. P452는 소비·정상 Android 복구 완료 상태이며 다시
실행하지 않는다. 이 작업은 기기 읽기·쓰기·전송 권한을 요청하거나 사용하지 않는다.

## 현재 증거가 선택한 범위

[P452 결과](S22PLUS_AUTOBOOT_RCS_P452_RUN_2026-10-23.md)는 dispatcher 진입,
`S01hostname.sh`의 B/E/0, 별도로 인증한 `S01mountkernfs.sh` 호출 직전 B를
보존한다. B는 shell script의 첫 명령, 특정 syscall 또는 pstore 진입을 증명하지
않는다. 부모의 이후 진행 기록도 없으므로 해당 script 내부만 원인 후보로 단정할
수 없다. 사용자 조작으로 추가 부팅이 있었다는 관찰과 세 boot의 정확한 대응도
여전히 미확인이다.

Retained root archive를 hash 검증하고 symlink/usr-merge를 해석해 script,
source되는 함수, 설정과 도구 27개 항목을 선택했다. Archive에는 실행하지 않았다.
아래 ARM64 실행은 그 archive의 정확한 bytes를 별도 diskless VM에 넣은 H0다.
FYG8 OSRC base와 delta도 다시 hash 검증하고 common/msm 양쪽에서 관련 kernel
파일 20개를 선택했다. 이 열 파일 경로에는 FYG8 delta가 없다. pstore, securityfs,
proc/sysfs, shmem의 선택 bytes는 양쪽에서 같고 namespace/SELinux 파일은 다르다.
OSRC 호출 경로 분석은 물리 kernel의 실제 stack이나 실패 원인 증거가 아니다.

## 실제 호출 순서

`rcS -> RAM rc-observed -> /etc/rcS.d/S01mountkernfs.sh start`가 선택 경로다.
마지막 symlink는 `/etc/init.d/mountkernfs.sh`로 해석된다.

| 단계 | 실제 consumer와 동작 | 현재 판단 |
| --- | --- | --- |
| 1 | `/lib/init/vars.sh`: rcS 설정, cmdline 읽기 | hostname도 사용하는 공통 입력. 같은 호출의 완료 증거는 아님 |
| 2 | `/lib/init/tmpfs.sh`: 다섯 size 변수 계산 | 각 계산이 `vm_size`를 호출해 MemTotal/SwapTotal의 grep/sed pipeline을 실행함. 아직 mount 전 |
| 3 | `/lib/lsb/init-functions`와 hooks | `run-parts --list`; systemd redirect는 `/run/systemd/system`이 있을 때만 선택 |
| 4 | `/lib/init/mount-functions.sh` source | 함수 정의 후 `mount_filesystems mount_noupdate` 진입 |
| 5 | `mount_run -> read_fstab -> domount -> mountpoint` | 넘겨받은 `/run` mount를 재사용하며 RAM marker/directory를 준비 |
| 6 | `mount_lock -> domount` | 기본 RAMLOCK=yes. `/run/lock`에 별도 5 MiB tmpfs가 없으면 mount |
| 7 | proc, securityfs, sysfs | 이미 mounted인 proc/sysfs는 재사용. 지원되는 securityfs가 없으면 mount |
| 8 | pstore | directory가 있고 filesystem이 지원되며 아직 mount되지 않았으면 mount |
| 9 | efivarfs | EFI variable directory가 있을 때만 검사/mount |

선택된 `/etc/fstab`는 비어 있고 tmpfs/rcS 설정은 기본값을 바꾸지 않는다.
기존 witness는 `/run`을 executable tmpfs로 넘기고 `/proc`, `/sys`, `/dev`를
이동한다. `mount_noupdate`의 이미 mounted 분기는 재마운트하지 않으므로,
mount_run의 `noexec` 옵션 문자열만 보고 기존 `/run`의 실행 권한이 제거됐다고
해석할 수 없다. Default mountkernfs 경로에서 module-init, watchdog pet 제어,
native_data repair 또는 partition writer가 직접 호출되는 근거도 없다.

Securityfs의 선택 source는 `get_tree_single -> simple_fill_super`다.
Pstore는 `pstore_mount -> pstore_fill_super -> pstore_get_records ->
pstore_get_backend_records`에서 backend read mutex와 callback, optional
decompression, RAM inode 생성으로 이어진다. Ramoops callback은 보존 영역을
읽으며 유효하지 않은 DMESG header를 정리하는 분기도 있다. 따라서 pstore mount를
단순한 빈 directory 생성으로 취급할 수는 없다. P452의 실제 backend 등록 상태,
이 경로의 진입/반환 및 잠금 대기는 이번 증거로 확정하지 못한다.

## ARM64 실행으로 확인한 것

기존 서명 검증된 Debian generic kernel/module과 exact archive의 shell/helpers를
사용했다. VM은 CPU 하나, RAM root, block/USB/network 장치 없는 별도 fixture다.
초기 `/run`, proc, sysfs, configfs, devpts, shm mount를 모델링했다. Guest가 출력한
script/helper/sh의 SHA-256과 kernel/module의 서명 package 연결을 다시 검사했다.
FYG8 driver, pstore backend/보존 내용, 물리 scheduler 상태는 이 VM에 없다.

- 첫 실제 호출은 `/run/lock`, securityfs, pstore 세 mount를 만들었고 여섯 대상의
  mountpoint 검증이 통과했다. `/run`의 sentinel도 보존됐다.
- 두 번째 호출은 같은 mount를 재사용해 새 mount 명령 없이 성공했다.
  첫 fixture의 guest 관측 시간은 각각 약 1.00/0.88초이며 기기 timing 추정치가 아니다.
- 별도 fixture에서 pstore mount만 오류 32를 반환하도록 RAM shim을 넣었다.
  원본 mountkernfs script는 **여전히 exit 0**이었고 pstore mountpoint는 없었다.
  Script에는 전체 mount 성공을 집계하는 반환 계약이 없다. 따라서 미래 E/0도
  개별 mount 성공이나 서비스 준비 완료를 대신할 수 없다.

호스트 script 내용만 보는 것보다 분기를 좁혔지만, 현재 원인은 미확정이다.
남은 구분은 source 단계/프로세스 실행·스케줄링, 새 virtual mount/backend 경로,
관측 부모·logger 유실 또는 별도의 reset이다. pstore를 원인으로 지정하거나
script를 건너뛰는 기능 변경을 이 결과만으로 선택하지 않는다.

## 다음 실험의 H0 완료 기준

P452가 이미 만든 bounded early/runtime 파일이 진행 여부를 더 알려줄 수 있고,
다음 writable candidate의 exact history에도 필요하다. 먼저 **P453**을 기존
`root-evidence` / `autoboot-pair`의 새 선언 데이터로 준비한다. P452의 정확한 run
파일 두 개만 partition RO 아래 mountless로 읽으며 journal replay, mount,
filesystem write 또는 Debian 실행은 추가하지 않는다. Runtime source와 reader
형식은 기존 P451과 같다. P452의 closure/raw provenance를 먼저 재도출해 결합한다.

완료 기준은 새 식별자와 두 경로의 정확한 결합, 실제 A/B build와 boot-only package,
현재 ARM64 producer bytes를 쓰는 정상/누락 peer VM 검증, 관련 reader/retrieval/task
검사, 변경된 host closure에 대한 독립 검토, source snapshot 및 offline proposal이다.
준비 중에는 grant를 열거나 기기에 명령하지 않는다. 실기는 후속 returned attended
grant와 현재 lane/health/Download recovery 검증이 필요한 별도 단계다.

Reader가 얻을 결과에 따라 다음 기능 후보를 정한다. Runtime이 rcS 이후 진행을
증명하면 그 지점부터 분석한다. 같은 경계까지만 입증되고 현재 파일/metadata를
정확히 수용할 수 있다면, 기존 RAM 채널의 제한 안에서 source 및 실제 mount 호출
전후를 구분하는 관측을 설계한다. 누락·dirty view는 비실행이나 자동 repair 권한이
아니며, 이번 H0에서 미확인 P452 파일을 임의 history로 넣지 않는다.

Private base:
`workspace/private/outputs/s22plus-mountkernfs-p453-h0-20261023-1/`.
선택된 입력/원시 VM trace/실패 주입/검증 manifest를 보존한다. 초기 H0 fixture의
크기 상한 및 BusyBox basename 수정은 기기 동작과 관계없는 host/VM 준비 오류다.
A90·S20+와 기존 46개 변경 경로는 보존한다.
