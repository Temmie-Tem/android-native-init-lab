# Samsung Galaxy A90 5G - 현재 문서 인덱스

이 문서 트리는 `2026-04-29` 기준으로 다시 정렬했습니다.

초기 `native Linux rechallenge`의 핵심 진입점 확보 단계는 통과했고,
현재 문서의 중심은 **stock Android kernel 위에서 custom static `/init`를 실행해
작은 native userspace/runtime을 만드는 작업**입니다.

상단 `docs/`는 이제 다음 흐름에 필요한 문서를 유지합니다.

1. native init 0.9.16 / v116 verified 기준 상태 고정
2. shell/HUD/log/menu 운영 안정화
3. 필요한 하드웨어/커널 경로만 역추적
4. BusyBox/network/SSH 같은 서버형 확장 가능성 검토

## 현재 기준점

- 디바이스: `SM-A908N`
- 빌드: `A908NKSU5EWA3`
- kernel: Samsung stock Android kernel `Linux 4.14.190`
- recovery: TWRP 사용 가능
- latest verified build: `A90 Linux init 0.9.16 (v116)`
- official version: `0.9.16`
- build tag: `v116`
- creator: `made by temmie0214`
- latest verified source: `stage3/linux_init/init_v116.c` + `stage3/linux_init/v116/*.inc.c` + `stage3/linux_init/helpers/a90_cpustress.c` + `stage3/linux_init/helpers/a90_rshell.c` + `stage3/linux_init/a90_config.h` + `stage3/linux_init/a90_util.c/h` + `stage3/linux_init/a90_log.c/h` + `stage3/linux_init/a90_timeline.c/h` + `stage3/linux_init/a90_console.c/h` + `stage3/linux_init/a90_cmdproto.c/h` + `stage3/linux_init/a90_run.c/h` + `stage3/linux_init/a90_service.c/h` + `stage3/linux_init/a90_kms.c/h` + `stage3/linux_init/a90_draw.c/h` + `stage3/linux_init/a90_input.c/h` + `stage3/linux_init/a90_hud.c/h` + `stage3/linux_init/a90_menu.c/h` + `stage3/linux_init/a90_metrics.c/h` + `stage3/linux_init/a90_shell.c/h` + `stage3/linux_init/a90_controller.c/h` + `stage3/linux_init/a90_storage.c/h` + `stage3/linux_init/a90_selftest.c/h` + `stage3/linux_init/a90_usb_gadget.c/h` + `stage3/linux_init/a90_netservice.c/h` + `stage3/linux_init/a90_runtime.c/h` + `stage3/linux_init/a90_helper.c/h` + `stage3/linux_init/a90_userland.c/h` + `stage3/linux_init/a90_diag.c/h` + `stage3/linux_init/a90_wifiinv.c/h` + `stage3/linux_init/a90_wififeas.c/h` + `stage3/linux_init/a90_app_about.c/h` + `stage3/linux_init/a90_app_displaytest.c/h` + `stage3/linux_init/a90_app_inputmon.c/h`
- latest verified boot image: `stage3/boot_linux_v116.img`
- previous verified source-layout baseline: `stage3/linux_init/init_v80.c` + `stage3/linux_init/v80/*.inc.c`
- known-good fallback: `stage3/boot_linux_v48.img`
- control channel: USB CDC ACM serial bridge
- display: custom boot splash 후 상태 HUD/menu 자동 전환
- input: VOL+/VOL-/POWER 단일/더블/롱/조합 입력 layout과 input monitor 확인
- logging: SD 정상 시 `/mnt/sdext/a90/logs/native-init.log`, fallback 시 `/cache/native-init.log`
- blocking cancel: q/Ctrl-C 취소 확인
- boot timeline: `timeline` 명령 확인
- boot selftest: `selftest`/`bootstatus`에서 non-destructive module smoke test `pass=11 warn=0 fail=0` 확인
- HUD boot summary: `BOOT OK shell` 표시 확인
- run cancel: `/bin/a90sleep` helper 확인
- storage: `/cache` safe write, ext4 SD workspace `/mnt/sdext/a90`, critical partitions do-not-touch
- screen menu: 자동 메뉴, 앱 폴더, CPU stress app, nonblocking `screenmenu`, serial `hide`/busy gate 확인
- USB map: ACM-only gadget `04e8:6861` / host `cdc_acm` 기준 문서화
- userland: static BusyBox 1.36.1 SD runtime 실행과 toybox 0.8.13 fallback 실행 확인
- remote shell: token-authenticated custom TCP shell `a90_rshell` over USB NCM `192.168.7.2:2326` 검증
- service manager: `service list/status/start/stop/enable/disable`로 autohud/tcpctl/adbd/rshell 공통 operator view 검증
- USB reattach: v48에서 ACM rebind 후 serial console 재연결 확인
- USB NCM: persistent composite, device `ncm0`, IPv4 ping, IPv6 link-local ping, host→device netcat 확인
- NCM ops: host interface 자동 탐지, ping, static TCP nettest 양방향 payload 검증 완료
- TCP control: NCM 위에서 `a90_tcpctl` ping/status/run/shutdown 검증 완료
- TCP wrapper/soak: `tcpctl_host.py smoke`와 5분/30사이클 `soak` 검증 완료
- physical USB reconnect: 실제 케이블 unplug/replug 후 ACM bridge, NCM ping, tcpctl 복구 확인
- serial noise: unsolicited `AT` modem probe line 무시 확인
- boot netservice: opt-in flag 기반 NCM/tcpctl 부팅 자동 시작과 rollback 검증 완료
- reconnect: v60 `netservice stop/start` software UDC 재열거 후 NCM/TCP 복구 확인
- HUD metrics: CPU/GPU 온도와 사용률 `%` 표시, CPU stress 검증 확인
- dev nodes: `/dev/null`/`/dev/zero` boot-time char device guard 확인
- app menu: APPS/MONITORING/TOOLS/LOGS/NETWORK/POWER 계층 메뉴, CPU stress, input monitor 확인
- boot splash: TEST 패턴 대신 `A90 NATIVE INIT` custom splash 표시 후 HUD 전환 확인
- splash layout: v65에서 긴 문구/footer 잘림 방지를 위해 안전 여백과 자동 축소 적용
- display test: v77에서 color/font/safe-area/layout preview 4페이지로 분리, `cutoutcal` 펀치홀 보정 추가
- SD workspace: `mountsd [status|ro|rw|off|init]`로 ext4 SD `/mnt/sdext/a90` 운영 검증
- about app: `APPS / ABOUT`에서 version, changelog 목록/상세, credits 표시
- log tail panel: HUD hidden 상태와 menu visible 상태에서 최근 native log 표시 확인
- serial reattach log: v75에서 idle-timeout 성공 로그를 억제해 LOG TAIL noise 감소
- serial noise: v76에서 짧은 `A`/`T`/`ATAT` fragment를 unknown command 없이 무시
- shell protocol: `cmdv1`/`A90P1` framed one-shot result와 `a90ctl.py` host wrapper 검증
- shell protocol: v74 `cmdv1x` length-prefixed argv encoding verified for whitespace args
- console module: v83에서 `a90_console.c/h`로 fd/attach/readline/cancel API 분리
- cmdproto module: v84에서 `a90_cmdproto.c/h`로 `cmdv1/cmdv1x` frame/decode API 분리
- run/service modules: v85에서 `a90_run.c/h`와 `a90_service.c/h`로 process/service lifecycle API 분리
- KMS/draw modules: v86에서 `a90_kms.c/h`와 `a90_draw.c/h`로 화면 저수준 API 분리
- input module: v87에서 `a90_input.c/h`로 물리 버튼/gesture API 분리와 실기 회귀 검증 완료
- HUD module: v88에서 `a90_hud.c/h`로 boot splash/status HUD/log tail 렌더러 분리와 실기 회귀 검증 완료
- menu module: v89에서 `a90_menu.c/h`로 menu model/state를 분리하고 `screenmenu`를 nonblocking background request로 전환
- metrics module: v90에서 `a90_metrics.c/h`로 배터리/CPU/GPU/MEM/전력 sysfs snapshot API 분리
- cpustress helper: v91에서 `/bin/a90_cpustress` static helper로 CPU stress worker를 PID1 밖으로 분리
- shell/controller modules: v92에서 `a90_shell.c/h`와 `a90_controller.c/h`로 shell metadata와 menu busy policy 분리
- storage module: v93에서 `a90_storage.c/h`로 boot storage state, SD probe, cache fallback, `storage`/`mountsd` API 분리
- selftest module: v94에서 `a90_selftest.c/h`로 boot-time non-destructive module smoke test와 `selftest` 명령 추가
- netservice/USB modules: v95에서 `a90_usb_gadget.c/h`와 `a90_netservice.c/h`로 USB configfs/UDC 및 NCM/tcpctl policy API 분리
- structure audit: v96에서 v95 모듈 경계 감사와 stale console klog marker 정리
- runtime module: v97에서 `a90_runtime.c/h`로 SD runtime root, cache fallback, runtime directory contract, `runtime` command 분리
- helper module: v98에서 `a90_helper.c/h`로 helper inventory, manifest path, preferred helper fallback, `helpers` command 분리
- userland module: v99에서 `a90_userland.c/h`로 BusyBox/toybox inventory, `userland`, `busybox`, `toybox` command 분리
- remote shell module: v100에서 `/bin/a90_rshell` custom TCP helper, token auth, `rshell_host.py` smoke 검증 완료
- service manager: v101에서 `a90_service.c/h` metadata/status API와 `service` command 검증 완료
- diagnostics: v102에서 `a90_diag.c/h`와 `diag_collect.py`로 read-only diagnostics/log bundle 검증 완료
- Wi-Fi inventory: v103에서 `a90_wifiinv.c/h`와 `wifi_inventory_collect.py`로 read-only WLAN/rfkill/firmware path 조사 완료
- Wi-Fi feasibility: v104에서 `a90_wififeas.c/h`와 `wififeas [summary|full|gate|paths]`로 read-only evidence 기반 bring-up gate 검증 완료
- soak RC: v105에서 `native_soak_validate.py` 10-cycle quick soak와 recovery-friendly baseline 검증 완료
- UI app split: v106 `a90_app_about.c/h`, v107 `a90_app_displaytest.c/h`, v108 `a90_app_inputmon.c/h` 분리 완료
- structure audit 2: v109에서 post-v108 구조 감사와 v110 cleanup boundary 기록 완료
- ADB: 보류

## 문서 읽는 순서

### 빠른 시작

1. `overview/PROJECT_STATUS.md` – 현재 상태와 다음 후보를 본다.
2. `operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md` – flash/bridge 조작 절차를 따른다.
3. `operations/DEVELOPMENT_LOOP_STANDARD.md` – 상태 확인부터 커밋까지 표준 개발 루프를 따른다.
4. `operations/CLAUDE_NATIVE_INIT_RUNBOOK.md` – 에이전트가 실수하지 않도록 운영 규칙을 확인한다.
5. `plans/NATIVE_INIT_TASK_QUEUE_2026-04-25.md` – 바로 이어서 할 작업 큐를 본다.
6. `plans/NATIVE_INIT_V109_V116_ROADMAP_2026-05-04.md` – v109 이후 장기 순서를 본다.
7. `plans/NATIVE_INIT_LONG_TERM_ROADMAP_2026-05-03.md` – v101 이후 장기 순서를 본다.

### 새 에이전트 인계

1. `operations/CLAUDE_HANDOFF_PROMPT.md`
2. `operations/DEVELOPMENT_LOOP_STANDARD.md`
3. `operations/CLAUDE_NATIVE_INIT_RUNBOOK.md`
4. `overview/PROJECT_STATUS.md`
5. `docs/README.md`

## 문서 카테고리

### 1. Overview

- `overview/PROJECT_STATUS.md` – 현재 기준점, 성공/실패 조건, 다음 작업 링크
- `overview/PROGRESS_LOG.md` – 날짜순 진행 로그
- `overview/VERSIONING.md` – semantic version과 `vNN` build tag 규칙
- `../CHANGELOG.md` – 공식 버전별 업데이트 로그

### 2. Operations

- `operations/DEVELOPMENT_LOOP_STANDARD.md` – native init 작업 표준 개발 루프, gate, bypass mode 기준
- `operations/CLAUDE_NATIVE_INIT_RUNBOOK.md` – 에이전트용 bridge/TWRP/custom init 작업 런북
- `operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md` – 사람이 직접 따라 하는 flash/bridge 운영 절차서
- `operations/CLAUDE_HANDOFF_PROMPT.md` – Claude에게 그대로 붙여 넣는 안전 작업 프롬프트

### 3. Plans

- `plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md` – v42 이후 역추적/셸/HUD/로그/네트워크 작업 목록
- `plans/NATIVE_INIT_TASK_QUEUE_2026-04-25.md` – v47 이후 바로 실행할 작업 큐
- `plans/NATIVE_INIT_V84_SHELL_CMDPROTO_PLAN_2026-04-29.md` – v84 `a90_cmdproto.c/h` 분리 실행 계획
- `plans/NATIVE_INIT_V85_RUN_SERVICE_PLAN_2026-04-30.md` – v85 `a90_run.c/h`, `a90_service.c/h` 분리 실행 계획
- `plans/NATIVE_INIT_V86_KMS_DRAW_PLAN_2026-04-30.md` – v86 `a90_kms.c/h`, `a90_draw.c/h` 분리 실행 계획
- `plans/NATIVE_INIT_V87_INPUT_API_PLAN_2026-04-30.md` – v87 `a90_input.c/h` 분리 실행 계획
- `plans/NATIVE_INIT_V88_HUD_API_PLAN_2026-05-02.md` – v88 `a90_hud.c/h` 분리 실행 계획
- `plans/NATIVE_INIT_V99_BUSYBOX_USERLAND_PLAN_2026-05-03.md` – v99 BusyBox static userland evaluation 실행 계획
- `plans/NATIVE_INIT_V100_REMOTE_SHELL_PLAN_2026-05-03.md` – v100 custom TCP remote shell 실행 계획
- `plans/NATIVE_INIT_V101_SERVICE_MANAGER_PLAN_2026-05-03.md` – v101 minimal service manager 구현 계획
- `plans/NATIVE_INIT_V102_DIAGNOSTICS_PLAN_2026-05-03.md` – v102 diagnostics/log bundle 실행 계획
- `plans/NATIVE_INIT_V103_WIFI_INVENTORY_PLAN_2026-05-04.md` – v103 Wi-Fi read-only inventory 실행 계획
- `plans/NATIVE_INIT_V104_WIFI_FEASIBILITY_PLAN_2026-05-04.md` – v104 Wi-Fi enablement feasibility gate 실행 계획
- `plans/NATIVE_INIT_V572_BOOT_TIME_COMPANION_TIMING_PLAN_2026-05-21.md` – V571 이후 QRTR/modem readiness 타이밍 가설을 검증하기 위한 opt-in boot-time companion timing 계획
- `plans/MINIMAL_BOOT_ALLOWLIST_2026-04-22.txt` – 현재 최소 부팅 allowlist
- `plans/MINIMAL_BOOT_DELETE_CANDIDATES_2026-04-22.txt` – allowlist 기준 삭제 후보 스냅샷
- `plans/NATIVE_LINUX_RECHALLENGE_PLAN.md` – native init 진입점 확보 이전 로드맵, 보존 기록
- `plans/REVALIDATION_PLAN.md` – 부트체인 재검증 실행 체크리스트, 보존 기록

### 4. Current Native Init Reports

- `reports/NATIVE_INIT_V582_MODEM_COMPANION_CLASSIFIER_2026-05-22.md` – `sysmon-qmi`/`service-notifier`/WLAN-PD gap을 missing userspace daemon이 아닌 kernel/QMI readiness path로 분류
- `reports/NATIVE_INIT_V581_ICNSS_ORDER_GAP_2026-05-22.md` – Android boot-complete와 최신 V580 native evidence를 비교해 native가 QRTR modem readiness/service-notifier/WLAN-PD/WLFW 단계에 진입하지 못함을 host-only로 분류
- `reports/NATIVE_INIT_V580_POSTFLIGHT_ICNSS_CLASSIFIER_2026-05-22.md` – V579 cleanup false를 delayed reaping으로 분리하고, 현재 blocker가 qcwlanstate `EINVAL` + ICNSS modules-not-initialized임을 read-only로 확정
- `reports/NATIVE_INIT_V579_V95_COMPANION_DRIVER_STATE_2026-05-22.md` – V95 companion stack과 `/dev/wlan` driver-state `ON`을 결합한 bounded proof; qcwlanstate는 여전히 `EINVAL`/ICNSS modules-not-initialized에서 막힘
- `reports/NATIVE_INIT_V578_COMBINED_GATE_CLASSIFIER_2026-05-21.md` – V513 qcwlanstate branch와 V577 V95 companion branch를 비교해 V579 combined bounded proof 필요성을 분류
- `reports/NATIVE_INIT_V577_V95_BROADER_IWIFI_RETRY_2026-05-21.md` – V95 init-root 계약으로 service-manager/dual-HAL/`IWifi.start()` broader window 재검증, 여전히 `ERROR_UNKNOWN/9` 및 QRTR socket 0
- `reports/NATIVE_INIT_V576_QRTR_NAMESPACE_SURFACE_2026-05-21.md` – V95 companion baseline 이후 read-only QRTR namespace surface 재분류, `QIPCRTR` protocol은 있으나 socket 0/`/proc/net/qrtr` 없음
- `reports/NATIVE_INIT_V575_COMPANION_INIT_ROOT_RETRY_2026-05-21.md` – V95에서 `rmt_storage`/`tftp_server`를 Android init-root start 계약으로 수정, companion window는 통과했지만 QRTR/QMI/BDF/FW marker는 아직 없음
- `reports/NATIVE_INIT_V574_BOOTPROBE_RESCUE_ONLY_2026-05-21.md` – V572 opt-in pre-ACM block 이후 stale bootprobe flags를 소비만 하는 rescue-only boot image local build
- `reports/NATIVE_INIT_V573_BOOTPROBE_FAIL_OPEN_RESCUE_2026-05-21.md` – V572 opt-in pre-ACM block 이후 one-shot/two-flag/fail-open rescue boot image local build
- `reports/NATIVE_INIT_V572_BOOT_TIME_COMPANION_BOOTPROBE_2026-05-21.md` – disabled-flag flash PASS, opt-in pre-ACM bootprobe blocked USB return and led to V573 rescue
- `reports/NATIVE_INIT_V571_QRTR_MODEM_READINESS_DELTA_2026-05-21.md` – read-only 비교 결과 native는 `QIPCRTR` protocol은 있으나 socket 0, QRTR/service-notifier/WLAN-PD/QMI readiness 미진입
- `reports/NATIVE_INIT_V570_RMT_TFTP_IDENTITY_2026-05-21.md` – `rmt_storage`/`tftp_server`를 Android 실측 UID/GID/groups/caps로 맞춘 helper v94 identity retry 결과
- `reports/NATIVE_INIT_V569_HAL_ERROR_UNKNOWN_DEPENDENCY_2026-05-21.md` – `IWifi.start()`는 `ERROR_UNKNOWN/9`, WLFW QRTR readback은 service event 없이 end-of-list, QIPCRTR socket 0
- `reports/NATIVE_INIT_V568_IWIFI_START_STATUS_2026-05-21.md` – raw `IWifi.start()` transport는 성공했지만 HAL `WifiStatus.ERROR_UNKNOWN/9`, QRTR/QMI/BDF/WLFW readiness 없음
- `reports/NATIVE_INIT_V567_HWBINDER_HANDLE_RETAIN_2026-05-21.md` – `IWifi/default` handle retain 후 raw hwbinder `IWifi.start()` transport 성공, Wi-Fi surface는 아직 없음
- `reports/NATIVE_INIT_V566_HWBINDER_TOKEN_COMPAT_2026-05-21.md` – legacy C-string interface token으로 raw `IServiceManager.get(IWifi/default)` handle 획득, 다음 blocker는 handle lifetime
- `reports/NATIVE_INIT_V562_LSHAL_THEN_IWIFI_START_2026-05-21.md` – 같은 dual-HAL 창에서 `lshal wait IWifi/default`는 성공하지만 raw hwbinder get은 service-null, raw parcel 계약 수리 필요
- `reports/NATIVE_INIT_V561_COMPANION_DUAL_HAL_WIFICOND_IWIFI_START_2026-05-21.md` – dual-HAL 등록 후 raw hwbinder `get(IWifi/default)`는 service-null, `IWifi.start()` 미실행
- `reports/NATIVE_INIT_V560_COMPANION_DUAL_HAL_WIFICOND_IWIFI_REGISTRATION_2026-05-21.md` – Android-like dual-HAL 창에서 AOSP `IWifi/default` 등록 관측, 다음은 bounded `IWifi.start()`
- `reports/NATIVE_INIT_V559_COMPANION_HAL_WIFICOND_IWIFI_REGISTRATION_2026-05-21.md` – Samsung `ISehWifi/default` 등록 후에도 AOSP `IWifi/default`는 Samsung-HAL-only 창에서 timeout, dual-HAL 필요
- `reports/NATIVE_INIT_V558_COMPANION_HAL_WIFICOND_REGISTRATION_2026-05-21.md` – V557 11-child window에서 Samsung Wi-Fi HAL `ISehWifi/default` 등록 관측, 아직 firmware/netdev marker 없음
- `reports/NATIVE_INIT_V557_COMPANION_HAL_WIFICOND_ORDER_2026-05-21.md` – service-manager/companion/HAL/`wificond`/CNSS 11-child start-only window cleanup-safe, WLFW/QMI/BDF는 여전히 없음
- `reports/NATIVE_INIT_V556_COMPANION_HAL_ORDER_2026-05-21.md` – service-manager/companion/HAL/CNSS 10-child start-only window cleanup-safe, WLFW/QMI/BDF는 여전히 없음
- `reports/NATIVE_INIT_V555_QMI_COMPANION_GAP_2026-05-21.md` – `qmiproxy`/`ssgqmigd`는 init 선언만 있고 startable binary가 없어 combined companion+HAL order proof로 전환
- `reports/NATIVE_INIT_V554_COMPANION_QRTR_WLFW_READBACK_2026-05-21.md` – companion window에서 WLFW QRTR readback end-of-list, Android modem/QRTR companion gap 확인 필요
- `reports/NATIVE_INIT_V553_FD_DETAIL_MAPPER_2026-05-21.md` – fdinfo/tcp6/udp6/raw/raw6 추가 후에도 13개 socket fd unmapped, QRTR-specific readback 필요
- `reports/NATIVE_INIT_V552_SOCKET_FAMILY_MAPPER_2026-05-21.md` – companion socket fd를 `unix`/`netlink`/unmapped으로 분류, QRTR 후보 fd 추가 확인 필요
- `reports/NATIVE_INIT_V551_QRTR_WINDOW_SNAPSHOT_2026-05-21.md` – companion window에서 `QIPCRTR` socket count 0 확인, socket family mapper 필요
- `reports/NATIVE_INIT_V550_VNDSERVICEMANAGER_COPYREAL_REPLAY_2026-05-21.md` – copy-real linkerconfig로 `vndservicemanager` 관측, binder gap 해소, QRTR/QMI blocker 전환
- `reports/NATIVE_INIT_V54_NCM_LINK_2026-04-25.md` – USB NCM persistent link, IPv4/IPv6 ping, host→device netcat 검증
- `reports/NATIVE_INIT_V55_NCM_OPS_2026-04-25.md` – NCM host setup helper와 양방향 TCP nettest helper 검증
- `reports/NATIVE_INIT_V56_TCPCTL_2026-04-26.md` – NCM 위의 작은 TCP command service helper 검증
- `reports/NATIVE_INIT_V57_TCPCTL_HOST_WRAPPER_2026-04-26.md` – TCP control host wrapper 검증
- `reports/NATIVE_INIT_V58_TCPCTL_SOAK_2026-04-26.md` – NCM + TCP control 5분 soak 검증
- `reports/NATIVE_INIT_V59_AT_NOISE_2026-04-26.md` – unsolicited `AT` serial noise filter 검증
- `reports/NATIVE_INIT_V60_NETSERVICE_2026-04-26.md` – opt-in boot-time NCM/tcpctl netservice 검증
- `reports/NATIVE_INIT_V60_RECONNECT_2026-04-26.md` – netservice stop/start UDC 재열거 복구 검증
- `reports/NATIVE_INIT_V61_CPU_GPU_USAGE_2026-04-26.md` – HUD/status CPU/GPU 사용률 `%` 표시 검증
- `reports/NATIVE_INIT_V62_CPUSTRESS_2026-04-26.md` – CPU stress 사용률 게이지와 `/dev/null`/`/dev/zero` guard 검증
- `reports/NATIVE_INIT_V63_APP_MENU_2026-04-26.md` – 계층형 앱 메뉴와 CPU stress screen app 검증
- `reports/NATIVE_INIT_V64_BOOT_SPLASH_2026-04-26.md` – TEST 화면을 custom boot splash로 교체한 검증
- `reports/NATIVE_INIT_V65_SPLASH_SAFE_LAYOUT_2026-04-26.md` – boot splash 잘림 방지 safe layout 검증
- `reports/NATIVE_INIT_V66_ABOUT_VERSIONING_2026-04-26.md` – ABOUT app, versioning, changelog, credits 검증
- `reports/NATIVE_INIT_V67_CHANGELOG_DETAILS_2026-04-26.md` – compact ABOUT typography와 version별 changelog detail 검증
- `reports/NATIVE_INIT_V69_INPUT_LAYOUT_2026-04-26.md` – physical-button gesture layout과 `inputlayout` 검증
- `reports/NATIVE_INIT_V70_INPUT_MONITOR_2026-04-26.md` – `TOOLS / INPUT MONITOR`와 `inputmonitor [events]` raw/gesture trace 검증
- `reports/NATIVE_INIT_V72_DISPLAY_TEST_2026-04-27.md` – display test screen과 framebuffer color fix 검증
- `reports/NATIVE_INIT_V73_CMDV1_PROTOCOL_2026-04-27.md` – `cmdv1`/`A90P1` shell protocol과 `a90ctl.py` wrapper 검증
- `reports/NATIVE_INIT_V74_CMDV1X_ARG_ENCODING_2026-04-27.md` – `cmdv1x` length-prefixed argv encoding 검증
- `reports/NATIVE_INIT_V75_QUIET_IDLE_REATTACH_2026-04-27.md` – idle-timeout serial reattach 성공 로그 억제 검증
- `reports/NATIVE_INIT_V76_AT_FRAGMENT_FILTER_2026-04-27.md` – 짧은 AT serial fragment filter 검증
- `reports/NATIVE_INIT_V77_DISPLAY_TEST_PAGES_2026-04-27.md` – display test와 cutout calibration 검증
- `reports/NATIVE_INIT_V78_SD_WORKSPACE_2026-04-29.md` – ext4 SD workspace와 `mountsd` 검증
- `reports/NATIVE_INIT_V79_BOOT_STORAGE_2026-04-29.md` – boot-time SD health check와 `/cache` fallback 검증
- `reports/NATIVE_INIT_V80_SOURCE_MODULES_2026-04-29.md` – PID1 source module split 검증 기록
- `reports/NATIVE_INIT_V81_CONFIG_UTIL_2026-04-29.md` – config/util true `.c/.h` base module extraction 검증 기록
- `reports/NATIVE_INIT_V82_LOG_TIMELINE_2026-04-29.md` – log/timeline true `.c/.h` API module extraction 검증 기록
- `reports/NATIVE_INIT_V83_CONSOLE_API_2026-04-29.md` – console fd/attach/readline/cancel API module extraction 검증 기록
- `reports/NATIVE_INIT_V84_CMDPROTO_API_2026-04-30.md` – cmdproto `cmdv1/cmdv1x` frame/decode API module extraction 검증 기록
- `reports/NATIVE_INIT_V85_RUN_SERVICE_API_2026-04-30.md` – run/service process lifecycle API module extraction 검증 기록
- `reports/NATIVE_INIT_V86_KMS_DRAW_API_2026-04-30.md` – KMS/draw API module extraction 검증 기록
- `reports/NATIVE_INIT_V87_INPUT_API_2026-04-30.md` – input API module extraction 실기 검증 기록
- `reports/NATIVE_INIT_V88_HUD_API_2026-05-02.md` – HUD API module extraction 실기 검증 기록
- `reports/NATIVE_INIT_V89_MENU_CONTROL_API_2026-05-02.md` – menu control API와 nonblocking screenmenu 실기 검증 기록
- `reports/NATIVE_INIT_V90_METRICS_API_2026-05-02.md` – metrics API module extraction 실기 검증 기록
- `reports/NATIVE_INIT_V91_CPUSTRESS_HELPER_2026-05-02.md` – CPU stress external helper 실기 검증 기록
- `reports/NATIVE_INIT_V92_SHELL_CONTROLLER_API_2026-05-02.md` – shell/controller API module extraction 실기 검증 기록
- `reports/NATIVE_INIT_V93_STORAGE_API_2026-05-02.md` – storage API module extraction 실기 검증 기록
- `reports/NATIVE_INIT_V94_BOOT_SELFTEST_API_2026-05-03.md` – boot selftest API 실기 검증 기록
- `reports/NATIVE_INIT_V95_NETSERVICE_USB_API_2026-05-03.md` – netservice/USB gadget API 실기 검증 기록
- `reports/NATIVE_INIT_V96_STRUCTURE_AUDIT_2026-05-03.md` – structure audit / refactor debt cleanup 실기 검증 기록
- `reports/NATIVE_INIT_V97_SD_RUNTIME_ROOT_2026-05-03.md` – SD runtime root 실기 검증 기록
- `reports/NATIVE_INIT_V98_HELPER_DEPLOY_2026-05-03.md` – helper deployment/package manifest 실기 검증 기록
- `reports/NATIVE_INIT_V99_BUSYBOX_USERLAND_2026-05-03.md` – BusyBox static userland 실기 검증 기록
- `reports/NATIVE_INIT_V100_REMOTE_SHELL_2026-05-03.md` – custom TCP remote shell over USB NCM 실기 검증 기록
- `reports/NATIVE_INIT_V101_SERVICE_MANAGER_2026-05-03.md` – service manager command/view 실기 검증 기록
- `reports/NATIVE_INIT_V102_DIAGNOSTICS_2026-05-03.md` – diagnostics/log bundle 실기 검증 기록
- `reports/NATIVE_INIT_V103_WIFI_INVENTORY_2026-05-04.md` – Wi-Fi read-only inventory 실기 검증 기록
- `reports/NATIVE_INIT_V83_CONSOLE_SHELL_CMDPROTO_DEPENDENCY_MAP_2026-04-29.md` – shell/cmdproto 분리 전 의존성 지도
- `reports/NATIVE_INIT_V74_PHYSICAL_USB_RECONNECT_2026-04-27.md` – 실제 USB 케이블 unplug/replug 후 ACM/NCM/tcpctl 복구 검증
- `reports/NATIVE_INIT_V53_MENU_BUSY_2026-04-25.md` – menu-active serial busy gate와 flash auto-hide 검증
- `reports/NATIVE_INIT_V48_USB_REATTACH_NCM_2026-04-25.md` – USB reattach와 NCM probe 실기 검증
- `reports/NATIVE_INIT_USERLAND_CANDIDATES_2026-04-25.md` – static userland/BusyBox/toybox 후보 보고서
- `reports/NATIVE_INIT_USB_GADGET_MAP_2026-04-25.md` – USB gadget/host descriptor/ADB·network 후보 지도
- `reports/NATIVE_INIT_STORAGE_MAP_2026-04-25.md` – 저장소/파티션 안전 등급 보고서
- `reports/NATIVE_INIT_V47_SCREEN_MENU_2026-04-25.md` – 화면 메뉴 초안 실기 검증
- `reports/NATIVE_INIT_V45_RUN_LOG_2026-04-25.md` – `run` cancel과 log preservation 검증
- `reports/NATIVE_INIT_V44_HUD_BOOT_2026-04-25.md` – HUD boot summary 검증
- `reports/NATIVE_INIT_V43_TIMELINE_2026-04-25.md` – boot readiness timeline 검증
- `reports/NATIVE_INIT_V42_CANCEL_2026-04-25.md` – blocking command 취소 정책 검증
- `reports/NATIVE_INIT_V41_LOGGING_2026-04-25.md` – `/cache/native-init.log` 검증
- `reports/NATIVE_INIT_V40_BUILD_2026-04-25.md` – shell return code 정밀화 검증
- `reports/NATIVE_INIT_V39_STATUS_2026-04-25.md` – native init 기준 상태 보고서

### 5. Historical / Android Baseline Reports

- `reports/BOOTCHAIN_REVALIDATION_MATRIX_2026-04-23.md` – 기본 4조합, KG, fallback, Linux 후보 기록 시트
- `reports/STAGE3_EXPERIMENT_LOG_2026-04-23.md` – Stage 3 native init 진입 실험 로그
- `reports/NATIVE_INIT_SHELL_PROBE_2026-04-23.md` – 초기 USB ACM shell probe 기록
- `reports/ADB_FROM_LINUX_INIT_LOG_2026-04-23.md` – Linux init에서 ADB 시도 기록
- `reports/MINIMAL_BOOT_STATUS_2026-04-22.md` – 최소 부팅 상태와 남은 예외 패키지
- `reports/ADB_DEBLOAT_RESEARCH_2026-04-22.md` – 패키지별 제거 판단 근거
- `reports/ADB_DEBLOAT_2026-04-22.md` – debloat 적용 기록
- `reports/MINIMAL_BOOT_DELETE_RUN_2026-04-22.log` – 최소 부팅 삭제 실행 로그
- `reports/MINIMAL_BOOT_DELETE_RUN_AFTER_ROOT_2026-04-22.log` – root 이후 재실행 로그

### 6. Archive

- `archive/README.md` – 아카이브 인덱스
- `archive/legacy/` – 기존 2025 방향 문서 일괄 보관

## 현재 우선순위

1. shell return code 정밀화 — v40 완료
2. `/cache/native-init.log` 추가 — v41 완료
3. blocking command 취소 정책 통일 — v42 완료
4. boot readiness timeline 자동 기록 — v43 완료
5. HUD boot progress/error 표시 — v44 완료
6. recovery log preservation + `run` cancel helper — v45 완료
7. safe storage/partition map 문서화 — v46 완료
8. on-screen menu 초안 — v47 완료
9. USB gadget/device/sysfs map 문서화 — 완료
10. Toybox/static userland build + device validation — 완료
11. USB ACM reattach + NCM probe — v48 완료
12. v49 HUD image 격리 — boot prefix readback은 맞지만 Android userspace로 진입
13. 상태 HUD/menu TUI 개선 — v52 실기 표시 확인
14. menu-active serial busy gate + flash auto-hide — v53 완료
15. USB NCM persistent link + IPv4/IPv6 ping + host→device netcat 검증 — 완료
16. NCM host setup helper + TCP nettest helper — 완료
17. NCM TCP control helper — 완료
18. TCP control host wrapper — 완료
19. NCM + TCP control 5분 soak — 완료
20. unsolicited `AT` serial noise filter — v59 완료
21. opt-in boot-time NCM/tcpctl netservice — v60 완료
22. netservice stop/start UDC reconnect recovery — v60 완료
23. HUD CPU/GPU usage percent 표시 — v61 완료
24. CPU stress usage gauge + `/dev/null`/`/dev/zero` guard — v62 완료
25. 계층형 앱 메뉴 + CPU stress screen app — v63 완료
26. TEST 부팅 화면을 custom boot splash로 교체 — v64 완료
27. boot splash 잘림 방지 safe layout — v65 완료
28. semantic version + ABOUT/changelog/credits app — v66 완료
29. compact ABOUT typography + version별 changelog detail — v67 완료
30. HUD log tail + expanded changelog history — v68 완료
31. physical-button input gesture layout — v69 완료
32. input monitor app + raw/gesture trace — v70 완료
33. HUD/menu live log tail panel — v71 완료
34. display test screen + framebuffer color fix — v72 완료
35. shell protocol v1 + host wrapper — v73 완료
36. cmdv1x argument encoding — v74 완료
37. idle serial reattach log quieting — v75 완료
38. AT fragment serial noise hardening — v76 완료
39. display test multi-page app + cutout calibration — v77 완료
40. ext4 SD workspace + `mountsd` storage manager — v78 완료
41. boot-time SD health check + `/cache` fallback — v79 완료
42. PID1 source layout split into include modules — v80 완료
43. Config/util true `.c/.h` base module extraction — v81 완료
44. Log/timeline true `.c/.h` API module extraction — v82 완료
45. Console true `.c/.h` API module extraction — v83 완료
46. Cmdproto true `.c/.h` API module extraction — v84 완료
47. Run/service lifecycle `.c/.h` API module extraction — v85 완료
48. KMS/draw true `.c/.h` API module extraction — v86 완료
49. Input true `.c/.h` API module extraction — v87 완료
50. HUD true `.c/.h` API module extraction — v88 완료
51. Menu control true `.c/.h` API module extraction + nonblocking `screenmenu` — v89 완료
52. Metrics true `.c/.h` API module extraction — v90 완료
53. CPU stress external helper process separation — v91 완료
54. Shell/controller metadata and busy policy API extraction — v92 완료
55. Storage state, SD probe, cache fallback API extraction — v93 완료
56. Boot selftest non-destructive module smoke test API — v94 완료
57. Netservice/USB gadget API extraction — v95 완료
58. Structure audit / refactor debt cleanup — v96 완료
59. SD runtime root promotion — v97 완료
60. Helper deployment / package manifest — v98 완료
61. BusyBox static userland evaluation — v99 완료
62. Custom token TCP remote shell over USB NCM — v100 완료
63. Minimal service manager command/view — v101 완료
64. Diagnostics/log bundle command and host collector — v102 완료
65. Wi-Fi read-only inventory — v103 완료
66. Wi-Fi enablement feasibility gate — v104 완료
67. Long-run soak/recovery RC — v105 완료
68. UI app split and controller/runtime hardening — v106-v114 완료
69. Remote shell hardening audit and invalid-token smoke — v115 완료
70. Diagnostics bundle 2 evidence closure — v116 완료

패키지 최소화와 Android userspace 복구는 보조 실험으로만 다루고,
메인 목표는 **Android kernel 위에 반복 운용 가능한 native init 기반 최소 Linux 콘솔을 만드는 것**입니다.
