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
- creator: `made by Temmie`
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
- `operations/HOST_VALIDATION_RESOURCE_GUARDRAILS.md` – host-side 검증/secret scan/log 검색의 OOM 방지 기준
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
- `plans/NATIVE_INIT_V689_PERIPHERAL_PROPERTY_SHIM_CLASSIFIER_PLAN_2026-05-24.md` – V688 provider property-service blocker를 host-only로 분류해 V690 private shim exact-ack 후보를 좁히는 V689 계획
- `plans/NATIVE_INIT_V688_PERIPHERAL_MANAGER_SELINUX_CONTEXT_REPAIR_PLAN_2026-05-24.md` – V687에서 확인된 invalid `u:r:per_mgr:s0` 강제 context를 제거하고 helper v114로 provider/CNSS retry를 재검증하는 V688 계획
- `plans/NATIVE_INIT_V687_PERIPHERAL_MANAGER_LIVE_PROOF_PLAN_2026-05-24.md` – V686 helper v113 provider mode를 배포하고 service `74` gated `pm-service`/`pm-proxy` + CNSS retry live proof로 연결하는 V687 계획
- `plans/NATIVE_INIT_V686_PERIPHERAL_MANAGER_HELPER_MODE_PLAN_2026-05-24.md` – V685가 확정한 `vendor.per_mgr`/`vendor.per_proxy` provider gap을 helper v113 start-only mode로 구현하기 위한 V686 계획
- `plans/NATIVE_INIT_V685_PERIPHERAL_MANAGER_PROVIDER_PLAN_2026-05-24.md` – V684가 좁힌 `vendor.qcom.PeripheralManager`의 A90 provider가 `vendor.per_mgr`/`pm-service`와 `vendor.per_proxy`인지 확인하고 helper start-order gap을 분류하는 V685 계획
- `plans/NATIVE_INIT_V684_CNSS_DAEMON_VNDBINDER_TARGET_PLAN_2026-05-24.md` – V683 이후 `cnss-daemon` vndbinder `-22`의 정적/기존 live target 후보를 `vendor.qcom.PeripheralManager`로 좁히는 V684 host-only 계획
- `plans/NATIVE_INIT_V683_CNSS2_QMI_TRIGGER_ISOLATION_PLAN_2026-05-24.md` – V682/V651/V654/V669 증거로 pre-WLFW cnss2/QMI trigger가 direct QCA power 문제가 아니라 `cnss-daemon` vndbinder continuation 문제인지 host-only 분류하는 V683 계획
- `plans/NATIVE_INIT_V682_CNSS2_WLFW_PROGRESSION_OBSERVER_PLAN_2026-05-24.md` – helper v112/V679 live arm을 재사용해 Binder debugfs가 아닌 cnss2/WLFW progression 기준으로 현재 부팅 상태를 관찰하는 V682 계획
- `plans/NATIVE_INIT_V681_CNSS2_CAUSAL_CHAIN_REBASE_PLAN_2026-05-24.md` – V667~V680 증거와 cnss2/WLFW 의존성 모델을 재정렬해 다음 게이트를 Binder debugfs가 아닌 cnss2/WLFW progression observer로 라우팅하는 V681 계획
- `plans/NATIVE_INIT_V680_BINDER_DEBUGFS_GAP_PLAN_2026-05-24.md` – V679 registry snapshot은 실행됐지만 `/sys/kernel/debug/binder*`가 ENOENT인 원인을 host-only로 분류해 Binder debugfs/대체 transaction 관찰 후보를 정하는 V680 계획
- `plans/NATIVE_INIT_V679_BINDER_REGISTRY_SNAPSHOT_PLAN_2026-05-24.md` – V678이 좁힌 Binder transaction blocker를 같은 V535 Android userspace-order 실패 창에서 helper v112 registry/debug snapshot으로 캡처하는 V679 계획
- `plans/NATIVE_INIT_V678_BINDER_FAILURE_TARGET_CLASSIFIER_PLAN_2026-05-24.md` – V677 이후 property denial 0 상태에서 남은 Binder `-22` actor/code/FD surface를 host-only로 분류해 V679 registry/debug capture gate를 정하는 V678 계획
- `plans/NATIVE_INIT_V677_V676_RESIDUAL_PROPERTY_PLAN_2026-05-24.md` – V676 잔여 20개 property denial을 V535 private property root에 delta로 반영해 property blocker 제거 여부를 검증하는 V677 계획
- `plans/NATIVE_INIT_V676_V535_PROPERTY_ANDROID_ORDER_PLAN_2026-05-24.md` – V535 private property root로 V671 Android userspace-order path를 재생해 V675 property target 개선 효과와 남은 blocker를 검증하는 V676 계획
- `plans/NATIVE_INIT_V675_PROPERTY_BINDER_TARGET_CLASSIFIER_PLAN_2026-05-24.md` – V674 post-HAL property/Binder gap을 Android getprop/property_context와 비교해 다음 private property_info/seed 및 Binder capture 대상을 정하는 V675 계획
- `plans/NATIVE_INIT_V674_POST_HAL_WIFICOND_CLASSIFIER_PLAN_2026-05-24.md` – V673 post-HAL evidence를 기반으로 Wi-Fi HAL/`wificond` 이후 WLFW/BDF/`wlan0` 미진입 원인을 property/binder runtime gap으로 분류하는 V674 계획
- `plans/NATIVE_INIT_V673_SAME_HELPER_REPLAY_PLAN_2026-05-24.md` – V672가 좁힌 service `74/180` regression을 helper v111 same-helper replay matrix로 재검증하는 V673 계획
- `plans/NATIVE_INIT_V672_SERVICE74_REGRESSION_CLASSIFIER_PLAN_2026-05-24.md` – V671 service `74/180` timeout을 V668 service74-positive 증거와 비교해 Wi-Fi HAL/`wificond` 이전 lower service-notifier 재현성 문제인지 분류하는 V672 계획
- `plans/NATIVE_INIT_V671_SERVICE74_ANDROID_USERSPACE_ORDER_PLAN_2026-05-24.md` – V670 service-order delta 이후 service `74` positive path에 Wi-Fi HAL legacy/ext와 `wificond` start-only를 결합한 V671 계획
- `plans/NATIVE_INIT_V670_ANDROID_SERVICE_ORDER_DELTA_PLAN_2026-05-24.md` – V669 runtime gap 이후 Android Wi-Fi HAL/wificond/CNSS service order와 V668 native order를 비교해 다음 start-only gate를 정하는 V670 계획
- `plans/NATIVE_INIT_V669_ANDROID_CNSS2_RUNTIME_DELTA_PLAN_2026-05-24.md` – V668 focused capture 이후 Android 성공 경로와 native service `74` window를 비교해 다음 runtime/order gate를 정하는 V669 host-only 계획
- `plans/NATIVE_INIT_V668_CNSS2_FOCUSED_CAPTURE_PLAN_2026-05-24.md` – V667이 좁힌 service `74` 이후 cnss2/QCA6390/WLFW gap을 helper v110 focused sysfs capture로 service74-open/window 안에서 관찰하는 V668 계획
- `plans/NATIVE_INIT_V667_CNSS2_PD_NOTIFIER_CLASSIFIER_PLAN_2026-05-24.md` – V666의 service-notifier `180/74` 이후 WLFW service `69` 전 갭을 cnss2/WLAN-PD `pd_notifier` progression 관점에서 host-only/read-only로 분류하는 V667 계획
- `plans/NATIVE_INIT_V666_REPAIRED_PRIVATE_CNSS_RETRY_PLAN_2026-05-24.md` – V665 repaired private property/runtime surface를 V660/V655 fresh `cnss-daemon` retry 경로에 결합하는 V666 계획
- `plans/NATIVE_INIT_V665_PRIVATE_REGISTRY_SNAPSHOT_PATH_REPAIR_PLAN_2026-05-23.md` – V664에서 드러난 host/global `/dev` snapshot 오판을 helper private temp-root path capture로 고치는 V665 계획
- `plans/NATIVE_INIT_V664_PRIVATE_RUNTIME_MATERIALIZATION_PLAN_2026-05-23.md` – V663 이후 V317 private property root를 V662 service `74` snapshot 경로에 결합해 private `/dev/__properties__`와 `/dev/socket/property_service` materialization을 검증하는 계획
- `plans/NATIVE_INIT_V663_SNAPSHOT_ZERO_COUNT_CLASSIFIER_PLAN_2026-05-23.md` – V662 registry/context snapshot zero-count가 helper 실패인지 private runtime surface 부재인지 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V662_REGISTRY_CONTEXT_SNAPSHOT_PLAN_2026-05-23.md` – V661이 좁힌 dynamic binder registration/property context gap을 service `74`/`vndservicemanager_ready` 뒤 read-only snapshot으로 관찰하는 V662 계획
- `plans/NATIVE_INIT_V661_BINDER_REGISTRATION_CONTEXT_CLASSIFIER_PLAN_2026-05-23.md` – V660 fresh CNSS retry가 proven `vndservicemanager` readiness 뒤에도 binder transaction `-22`로 멈춘 원인을 service registration/property context gap으로 host-only 분류하는 계획
- `plans/NATIVE_INIT_V660_READY_CNSS_RETRY_PLAN_2026-05-23.md` – V659 readiness pass 이후 같은 gate에서 fresh `cnss-daemon` retry tail만 추가해 WLFW/WLAN-PD/QMI/BDF/`wlan0` 진전 여부를 검증하는 계획
- `plans/NATIVE_INIT_V659_VNDSERVICEMANAGER_READINESS_ONLY_PLAN_2026-05-23.md` – V658 이후 service `74` gate 뒤 `vndservicemanager` readiness만 분리 검증하고 CNSS retry tail은 보류하는 계획
- `plans/NATIVE_INIT_V658_VNDBINDER_SURFACE_CLASSIFIER_PLAN_2026-05-23.md` – V657 이후 V653/V657/V655 binder surface를 host-only로 비교해 V659 readiness-only gate를 정하는 계획
- `plans/NATIVE_INIT_V657_SERVICE74_V106_REPLAY_PLAN_2026-05-23.md` – V656 이후 helper v106으로 V653 exact service `74` gate를 재현해 V655 retry tail 전 blocker를 분리하는 계획
- `plans/NATIVE_INIT_V656_SERVICE74_REGRESSION_CLASSIFIER_PLAN_2026-05-23.md` – V655 service `74` gate timeout을 V644/V653 positive와 host-only로 비교해 다음 V657 exact replay gate를 정하는 계획
- `plans/NATIVE_INIT_V655_VNDSERVICEMANAGER_CNSS_RETRY_PLAN_2026-05-23.md` – V654가 좁힌 `cnss-daemon` vndbinder transaction blocker를 vndservicemanager readiness 후 fresh retry로 검증하는 V655 계획
- `plans/NATIVE_INIT_V654_BINDER_RUNTIME_MISMATCH_CLASSIFIER_PLAN_2026-05-23.md` – V653 service `74` gate 이후 남은 `cnss-daemon` vndbinder transaction `-22`를 host-only로 분류하는 V654 계획
- `plans/NATIVE_INIT_V653_SERVICE74_GATED_SERVICE_MANAGER_PLAN_2026-05-23.md` – V652 fixed-delay service-manager regression 이후 fresh service `74` kernel marker가 관찰될 때만 service-manager trio를 시작하는 V653 계획
- `plans/NATIVE_INIT_V652_SERVICE74_BINDER_PARITY_PLAN_2026-05-23.md` – V651 이후 V644 service `74` positive 경로에 V601/V603 service-manager binder surface를 결합해 WLFW 진입 여부만 검증하는 V652 계획
- `plans/NATIVE_INIT_V651_CNSS_WLFW_CONTINUATION_PLAN_2026-05-23.md` – V650 이후 Android/native CNSS netlink와 WLFW continuation 차이를 비교해 native `cnss-daemon` binder `-22` blocker를 분류하는 V651 계획
- `plans/NATIVE_INIT_V650_POST_WARNING_CONTINUATION_PLAN_2026-05-23.md` – Android V649와 native V644의 ASoC warning 이후 WLFW/WLAN-PD/QMI/BDF/`wlan0` continuation 차이를 비교하는 V650 계획
- `plans/NATIVE_INIT_V649_ANDROID_FULL_AUDIO_WIFI_RECAPTURE_PLAN_2026-05-23.md` – Android same-boot audio/ASoC + Wi-Fi lower-surface full dmesg reference를 수집하는 V649 계획
- `plans/NATIVE_INIT_V648_AUDIO_ASOC_PARITY_GUARD_PLAN_2026-05-23.md` – V647 이후 current native idle audio surface와 V644/Android evidence를 비교해 ASoC warning guard를 정하는 V648 계획
- `plans/NATIVE_INIT_V647_WARNING_SOURCE_CLASSIFIER_PLAN_2026-05-23.md` – V644 service `74` 직후 warning이 Wi-Fi QMI/HAL이 아니라 ASoC duplicate `pm_qos` 경로인지 host-only로 분류하는 V647 계획
- `plans/NATIVE_INIT_V646_ANDROID_POST74_TIMING_PLAN_2026-05-23.md` – Android 정상 service `74` 이후 WLAN-PD/WLFW timing과 V644 service `74` 이후 warning timing을 비교하는 V646 host-only 계획
- `plans/NATIVE_INIT_V645_V644_WARNING_ATTRIBUTION_PLAN_2026-05-23.md` – V644가 service `74` 직후 `pm_qos` warning을 낸 원인을 V619/V627/V642와 host-only로 비교해 다음 안전 gate를 고르는 V645 계획
- `plans/NATIVE_INIT_V644_CLEAN_DSP_CNSS_WLFW_READBACK_PLAN_2026-05-23.md` – V641 clean-DSP 상태에서 V598-class CNSS-including WLFW readback을 재생해 service `180` 재현과 service `74`/WLAN-PD 진전 여부를 검증하는 V644 계획
- `plans/NATIVE_INIT_V643_V642_PUBLISHER_GAP_CLASSIFIER_PLAN_2026-05-23.md` – V642 no-CNSS clean-DSP 결과와 V598/V625/V627 CNSS-including partial-positive를 비교해 service-notifier publisher gap을 분류하는 V643 계획
- `plans/NATIVE_INIT_V642_CLEAN_DSP_LOWER_COMPANION_PLAN_2026-05-23.md` – V641 clean-DSP 상태를 재사용해 direct DSP boot-node 재시도 없이 lower modem/QRTR companion publication을 관찰하는 V642 계획
- `plans/NATIVE_INIT_V641_FIRMWARE_BACKED_BOOT_WINDOW_PLAN_2026-05-23.md` – V640 이후 service `74`를 향한 유일한 남은 mutation 후보인 rollback-ready firmware-backed early boot-window sibling trigger proof 계획
- `plans/NATIVE_INIT_V640_SAFE_SIBLING_TRIGGER_RECLASSIFICATION_PLAN_2026-05-23.md` – V639 이후 late direct all-sibling write를 제외하고 service `74`로 이어지는 안전한 sibling SSCTL trigger 후보를 host-only로 재분류하는 V640 계획
- `plans/NATIVE_INIT_V639_SIBLING_WARNING_ATTRIBUTION_PLAN_2026-05-23.md` – V638 `pm_qos` warning 재발을 V619/V635/V636과 비교해 direct all-sibling write retry 가능 여부를 host-only로 분류하는 V639 계획
- `plans/NATIVE_INIT_V638_FIRMWARE_SIBLING_SSCTL_COMPOSITE_PLAN_2026-05-23.md` – V637 이후 firmware-backed ADSP/CDSP/SLPI per-node sibling SSCTL write가 Android-like sibling `sysmon-qmi`/service `74`를 만드는지 검증하는 V638 bounded live 계획
- `plans/NATIVE_INIT_V637_SERVICE74_POST_CDSP_CLASSIFIER_PLAN_2026-05-23.md` – V636 CDSP-online + V598 composite가 service `180`까지만 재현한 뒤 service `74` blocker가 CDSP power가 아닌 sibling SSCTL sysmon 계층인지 host-only로 분류하는 V637 계획
- `plans/NATIVE_INIT_V636_CDSP_V598_COMPOSITE_PLAN_2026-05-23.md` – V635 CDSP-online proof와 V625/V627 V598-class partial-positive를 같은 boot에서 결합해 service `74`/WLAN-PD/WLFW 진전 여부를 확인하는 V636 계획
- `plans/NATIVE_INIT_V635_FIRMWARE_CDSP_ONLY_PROOF_PLAN_2026-05-23.md` – V634 firmware mount parity에 CDSP-only bounded boot-node write를 더해 service `74`/WLAN-PD 진입 여부를 확인하는 V635 계획
- `plans/NATIVE_INIT_V634_FIRMWARE_MOUNT_PARITY_PLAN_2026-05-23.md` – V633 firmware surface missing 이후 `apnhlos`/`modem` read-only mount parity와 cleanup을 검증하는 V634 계획
- `plans/NATIVE_INIT_V633_CDSP_SURFACE_READONLY_PLAN_2026-05-23.md` – V632 이후 native v319에서 CDSP boot-node/subsys/firmware/dmesg surface를 read-only로 수집하는 V633 계획
- `plans/NATIVE_INIT_V632_CDSP_BLOCKER_CLASSIFIER_PLAN_2026-05-23.md` – V631이 CDSP timeout을 격리한 뒤 CDSP loader/firmware/readiness prerequisite을 host-only로 분류하는 V632 계획
- `plans/NATIVE_INIT_V631_PER_NODE_SIBLING_SSCTL_PROOF_PLAN_2026-05-23.md` – V630의 ADSP 이후 timeout을 좁히기 위해 ADSP/CDSP/SLPI를 per-node child/timeout으로 분리하는 V631 계획
- `plans/NATIVE_INIT_V630_SIBLING_SSCTL_BOOT_WINDOW_PROOF_PLAN_2026-05-23.md` – V629가 선정한 ADSP/CDSP/SLPI sibling SSCTL trigger를 post-ACM one-shot boot window에서 검증하는 V630 계획
- `plans/NATIVE_INIT_V629_SIBLING_SSCTL_TRIGGER_CLASSIFIER_PLAN_2026-05-23.md` – V628 이후 Android의 early-boot ADSP/CDSP/SLPI sibling SSCTL trigger와 native v319 누락을 host-only로 분류하는 V629 계획
- `plans/NATIVE_INIT_V628_SERVICE74_PUBLISHER_CLASSIFIER_PLAN_2026-05-23.md` – V627 이후 native service-locator/`180`은 재현됐지만 Android의 sibling `sysmon-qmi`/service `74`와의 차이를 host-only로 분류하는 V628 계획
- `plans/NATIVE_INIT_V627_POST_180_OBSERVER_PLAN_2026-05-23.md` – V626이 좁힌 native `service-notifier 180` 이후 `74`/WLAN-PD/WLFW service `69` publication을 V598/v100 경로로 bounded 관찰하는 V627 계획
- `plans/NATIVE_INIT_V626_POST_180_PUBLICATION_CLASSIFIER_PLAN_2026-05-23.md` – V625의 native `service-notifier 180` 이후 Android `74`/WLAN-PD와의 timing gap을 host-only로 분류하는 V626 계획
- `plans/NATIVE_INIT_V625_FRESH_V598_REPLAY_PLAN_2026-05-23.md` – V624가 선정한 safe partial positive를 fresh native boot에서 재현해 다음 lower-QMI blocker를 좁히는 V625 계획
- `plans/NATIVE_INIT_V624_SAFE_POSITIVE_REGRESSION_PLAN_2026-05-23.md` – V598 safe partial positive와 이후 negative replay/unsafe DSP path를 비교해 다음 안전 live gate를 고르는 V624 계획
- `plans/NATIVE_INIT_V623_LOWER_QMI_PUBLICATION_GAP_PLAN_2026-05-23.md` – V622 이후 `qmiproxy`와 lower QMI publication gap을 host-only로 비교 분류하는 V623 계획
- `plans/NATIVE_INIT_V622_ANDROID_MDM_HELPER_TIMING_RECAPTURE_PLAN_2026-05-23.md` – V621의 cross-boot `mdm_helper`/service-notifier 타이밍 갭을 Android same-boot read-only capture로 닫는 V622 계획
- `plans/NATIVE_INIT_V621_MDM_HELPER_CONTRACT_CLASSIFIER_PLAN_2026-05-23.md` – V620 이후 `vendor.mdm_helper`/`vendor.mdm_launcher` Android init 계약과 같은 부팅 타이밍 필요성을 host-only로 분류하는 V621 계획
- `plans/NATIVE_INIT_V620_DSP_MDM3_SAFETY_CLASSIFIER_PLAN_2026-05-23.md` – V619 이후 direct DSP boot-node warning, `mdm3=OFFLINING`, `sysmon_esoc0`, `mdm_helper` 경로를 host-only로 분류하는 V620 계획
- `plans/NATIVE_INIT_V619_ANDROID_ORDER_POST_SYSMON_OBSERVER_PLAN_2026-05-23.md` – V618이 좁힌 `pd_mapper` order delta를 no-CNSS/no-HAL Android-order observer로 검증하는 V619 계획
- `plans/NATIVE_INIT_V618_RFS_ALIAS_ORDER_CLASSIFIER_PLAN_2026-05-23.md` – V617의 `rfs_access` 후보를 alias/domain 힌트인지 확인하고 Android companion order delta를 분류하는 V618 계획
- `plans/NATIVE_INIT_V617_ANDROID_INIT_QMI_TRIGGER_CANDIDATE_PLAN_2026-05-23.md` – V616 이후 Android init/QMI service-registration 후보를 host-only로 분류하는 V617 계획
- `plans/NATIVE_INIT_V616_POST_SIBLING_SYSMON_SERVICE_NOTIFIER_CLASSIFIER_PLAN_2026-05-23.md` – V615 이후 sibling `sysmon-qmi`는 재현됐지만 service-notifier `180/74`가 없는 갭을 host-only로 분류하는 V616 계획
- `plans/NATIVE_INIT_V615_DSP_BOOT_NODE_OBSERVER_PLAN_2026-05-23.md` – V614가 좁힌 ADSP/CDSP/SLPI boot-node delta를 no-CNSS companion window로 검증하는 V615 live observer 계획
- `plans/NATIVE_INIT_V613_MDM3_ESOC_TARGETED_OBSERVER_PLAN_2026-05-23.md` – V612 이후 `mdm3`/`esoc0` lower publication delta를 native에서 no-close/reboot-cleanup으로 검증하는 계획
- `plans/NATIVE_INIT_V611_ANDROID_LOWER_SURFACE_RECAPTURE_PLAN_2026-05-23.md` – V610의 Android evidence limit을 닫기 위한 lower-surface read-only recapture 계획
- `plans/NATIVE_INIT_V610_QMI_PUBLICATION_PRECONDITION_PLAN_2026-05-23.md` – V609 이후 Android/native lower QMI publication precondition을 host-only로 비교하는 계획
- `plans/NATIVE_INIT_V609_POST_SYSMON_OBSERVER_PLAN_2026-05-23.md` – V608 이후 CNSS 없이 QRTR/sysmon 이후 service-notifier publication을 관찰하는 bounded observer 계획
- `plans/NATIVE_INIT_V608_HELPER_V100_BASELINE_REPLAY_PLAN_2026-05-23.md` – V607의 helper-version delta를 검증하기 위해 helper v100으로 V598 no-service-manager baseline을 재생하는 bounded live 계획
- `plans/NATIVE_INIT_V607_QMI_SERVICE_PUBLICATION_DELTA_PLAN_2026-05-23.md` – V598-positive/V606-negative 증거를 host-only로 비교해 `sysmon-qmi` 이후 QMI service publication 갭을 분류하는 계획
- `plans/NATIVE_INIT_V604_CNSS_FIRST_SERVICE_MANAGER_PROOF_PLAN_2026-05-22.md` – V603 이후 CNSS를 service-manager보다 먼저 시작해 service-notifier `180` 보존과 binder clean을 함께 검증하는 계획
- `plans/NATIVE_INIT_V603_QRTR_FIRST_SERVICE_MANAGER_PROOF_PLAN_2026-05-22.md` – V602 ordering gap을 검증하기 위해 QRTR/modem companion을 먼저 시작하고 service-manager를 뒤에 붙이는 helper v101 계획
- `plans/NATIVE_INIT_V602_SERVICE_MANAGER_ORDERING_GAP_PLAN_2026-05-22.md` – V598/V601을 비교해 service-manager ordering/timing gap을 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V601_SERVICE_MANAGER_BINDER_PROOF_PLAN_2026-05-22.md` – V600 이후 `cnss-daemon` binder/runtime gap을 service-manager 포함 modem-holder companion window로 검증하는 계획
- `plans/NATIVE_INIT_V600_REGISTRY_CNSS_MATRIX_PLAN_2026-05-22.md` – V598/V599 증거에서 service-registry와 CNSS runtime gap을 host-only matrix로 분류하는 계획
- `plans/NATIVE_INIT_V599_SERVICE_NOTIFIER_INSTANCE_GAP_PLAN_2026-05-22.md` – V598 이후 service-notifier `180`만 보이고 `74`/WLAN-PD/WLFW service `69`가 없는 갭을 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V590_ANDROID_SUBSYS_STATE_SAMPLE_PLAN_2026-05-22.md` – Android ADB 상태에서 modem/esoc subsystem 값을 read-only로 수집하는 V590 계획
- `plans/NATIVE_INIT_V589_ANDROID_SUBSYS_STATE_GAP_PLAN_2026-05-22.md` – Android QRTR/sysmon/service-notifier readiness timeline과 V588 native modem/esoc subsystem 값을 비교하는 host-only 계획
- `plans/NATIVE_INIT_V588_MODEM_SUBSYS_WINDOW_VALUES_PLAN_2026-05-22.md` – V587 이후 companion window 내부 modem/esoc subsystem 값을 helper v99로 캡처하는 계획
- `plans/NATIVE_INIT_V587_QRTR_MODEM_WINDOW_SURFACE_PLAN_2026-05-22.md` – V586 이후 companion window 내부 QRTR/modem sysfs surface를 helper v98로 캡처하는 계획
- `plans/NATIVE_INIT_V586_QRTR_COMPANION_BLOCKER_PLAN_2026-05-22.md` – V585 이후 QRTR/control-plane blocker를 boot-time 재시도 없이 read-only로 분류하는 계획
- `plans/NATIVE_INIT_V572_BOOT_TIME_COMPANION_TIMING_PLAN_2026-05-21.md` – V571 이후 QRTR/modem readiness 타이밍 가설을 검증하기 위한 opt-in boot-time companion timing 계획
- `plans/MINIMAL_BOOT_ALLOWLIST_2026-04-22.txt` – 현재 최소 부팅 allowlist
- `plans/MINIMAL_BOOT_DELETE_CANDIDATES_2026-04-22.txt` – allowlist 기준 삭제 후보 스냅샷
- `plans/NATIVE_LINUX_RECHALLENGE_PLAN.md` – native init 진입점 확보 이전 로드맵, 보존 기록
- `plans/REVALIDATION_PLAN.md` – 부트체인 재검증 실행 체크리스트, 보존 기록

### 4. Current Native Init Reports

- `reports/NATIVE_INIT_V689_PERIPHERAL_PROPERTY_SHIM_CLASSIFIER_2026-05-24.md` – V689 host-only 결과 V688의 property-service blocker는 exact private shim ack 후보 `vendor.peripheral.SDX50M.state=OFFLINE`와 `vendor.peripheral.modem.state=OFFLINE`로 좁혀져 다음은 helper v115
- `reports/NATIVE_INIT_V688_PERIPHERAL_MANAGER_SELINUX_CONTEXT_REPAIR_2026-05-24.md` – V688 live 결과 helper v114에서 `pm-service`/`pm-proxy`의 invalid `u:r:per_mgr:s0` `setexeccon`은 제거됐고 다음 blocker는 provider property service 접근/registration runtime gap
- `reports/NATIVE_INIT_V687_PERIPHERAL_MANAGER_LIVE_PROOF_2026-05-24.md` – V687 live 결과 helper v113 배포와 service `74` gated provider/CNSS retry는 실행됐지만 `pm-service`/`pm-proxy`의 강제 `u:r:per_mgr:s0` `setexeccon`이 `EINVAL`로 실패해 다음은 provider SELinux context mapping 수리
- `reports/NATIVE_INIT_V686_PERIPHERAL_MANAGER_HELPER_MODE_BUILD_2026-05-24.md` – V686 build 결과 helper v113에 service `74` gated `per_mgr`/`per_proxy` provider mode가 추가되어 다음은 V687 deploy/live start-only proof
- `reports/NATIVE_INIT_V685_PERIPHERAL_MANAGER_PROVIDER_LIVE_2026-05-24.md` – V685 live read-only 결과 A90 provider는 `vendor.per_mgr`/`pm-service`와 `vendor.per_proxy`이며 현재 helper가 이를 materialize/start 하지 않아 다음은 V686 helper start-only 지원
- `reports/NATIVE_INIT_V684_CNSS_DAEMON_VNDBINDER_TARGET_2026-05-24.md` – V684 host-only 결과 `cnss-daemon`이 `libperipheral_client.so`를 통해 `vendor.qcom.PeripheralManager` over vndbinder를 사용할 가능성이 높고 다음은 V685 live availability/start-order proof
- `reports/NATIVE_INIT_V683_CNSS2_QMI_TRIGGER_ISOLATION_2026-05-24.md` – V683 host-only 결과 Android는 CNSS→WLFW로 계속되지만 native는 `cnss-daemon` vndbinder transaction 뒤 WLFW 전 정지하므로 다음은 V684 transaction target capture/repair
- `reports/NATIVE_INIT_V682_CNSS2_WLFW_PROGRESSION_OBSERVER_LIVE_2026-05-24.md` – V682 live 결과 service `74`, CNSS retry, focused ICNSS/QCA6390 sysfs, Android userspace start-only는 통과했지만 WLFW/BDF/`wlan0`는 0이라 다음은 cnss2/QMI trigger isolation
- `reports/NATIVE_INIT_V681_CNSS2_CAUSAL_CHAIN_REBASE_2026-05-24.md` – V681 host-only 결과 service `74` positive와 Binder debugfs gap은 이미 확인됐지만 Android/native 차이는 cnss2/WLFW progression 전환점에 있어 다음은 V682 bounded cnss2/WLFW observer
- `reports/NATIVE_INIT_V680_BINDER_DEBUGFS_GAP_2026-05-24.md` – V680 host-only 결과 V679 snapshot phase는 실행됐지만 Binder debug path blocks 20개가 모두 비어 있고 `/sys/kernel/debug/binder*` ENOENT가 반복되어 Binder debugfs는 secondary observability gap으로 유지
- `reports/NATIVE_INIT_V679_BINDER_REGISTRY_SNAPSHOT_LIVE_2026-05-24.md` – V679 live 결과 helper v112 Binder registry snapshot phases는 모두 실행됐고 property denial은 0으로 유지됐지만 Binder debug files/per-child proc는 캡처되지 않아 다음은 V680 Binder debugfs/대체 transaction observability 분류
- `reports/NATIVE_INIT_V678_BINDER_FAILURE_TARGET_CLASSIFIER_2026-05-24.md` – V678 host-only 결과 V677 property denial 0 상태에서 Binder failure 5개를 `servicemanager`/`hwservicemanager`/`wificond` ioctl noise와 `cnss-daemon` vndbinder transaction blocker로 분류했고 다음은 V679 Binder registry/debug snapshot
- `reports/NATIVE_INIT_V677_V676_RESIDUAL_PROPERTY_LIVE_2026-05-24.md` – V677 live 결과 V676 잔여 property denial 370개/20키를 private property root delta로 제거해 property denial이 0이 되었고, 남은 blocker는 Binder `-22` registration/transaction 경로로 좁혀짐
- `reports/NATIVE_INIT_V676_V535_PROPERTY_ANDROID_ORDER_LIVE_2026-05-24.md` – V676 live 결과 V535 property root가 V675 denial set을 크게 줄였지만 service-manager/HAL/wificond/SKU/libvintf 관련 370개 property denial과 Binder failure가 남아 WLFW/BDF/`wlan0`는 아직 미진입
- `reports/NATIVE_INIT_V675_PROPERTY_BINDER_TARGET_CLASSIFIER_2026-05-24.md` – V675 host-only 결과 V674의 `24`개 property lookup failure는 모두 Android property_context에 매핑되고 runtime-required 값도 Android getprop에서 확인되어 다음은 private property_info/seed 확장과 bounded Binder registration capture
- `reports/NATIVE_INIT_V674_POST_HAL_WIFICOND_CLASSIFIER_2026-05-24.md` – V674 host-only 결과 V673 V671-arm은 HAL/`wificond`/fresh CNSS 시작과 UID/GID/cap/SELinux/Binder FD surface는 통과했지만 WLFW/BDF/`wlan0`는 없고 property-context 및 binder runtime gap이 남아 다음은 V675 targeted property/binder repair/capture
- `reports/NATIVE_INIT_V673_SAME_HELPER_REPLAY_LIVE_2026-05-24.md` – V673 live 결과 helper v111 same-helper matrix에서 V668-compatible/V671 둘 다 service `74/180`을 재현했고 V671은 Wi-Fi HAL/`wificond`/fresh CNSS retry까지 cleanup-safe로 실행했지만 WLFW/BDF/`wlan0`는 0이라 다음은 post-HAL/wificond runtime classifier
- `reports/NATIVE_INIT_V672_SERVICE74_REGRESSION_CLASSIFIER_2026-05-24.md` – V672 host-only 결과 V668과 V671 모두 QRTR RX/TX와 `sysmon-qmi` 및 firmware/modem surface는 같지만 V671에서만 service `74/180`이 사라져 다음은 helper v111 same-helper replay matrix
- `reports/NATIVE_INIT_V671_SERVICE74_ANDROID_USERSPACE_ORDER_LIVE_2026-05-24.md` – V671 live 결과 QRTR RX/TX와 `sysmon-qmi`는 재현됐지만 service `74/180` gate가 timeout되어 Wi-Fi HAL/`wificond` child start는 withheld됐고 다음은 V668-positive 대비 lower service-notifier regression classifier
- `reports/NATIVE_INIT_V670_ANDROID_SERVICE_ORDER_DELTA_2026-05-24.md` – V670 host-only 결과 Android는 Wi-Fi HAL legacy/ext, `cnss_diag`, `wificond`가 `cnss-daemon`보다 먼저 running이고 V668 native order에는 HAL/wificond가 없어 다음은 service74-gated Android userspace-order start-only proof
- `reports/NATIVE_INIT_V669_ANDROID_CNSS2_RUNTIME_DELTA_2026-05-24.md` – V669 host-only 결과 Android는 WLFW/BDF/firmware-ready/ICNSS `wlan0`까지 진행하지만 V668 native는 icnss/QCA6390 device만 보이고 WLFW 전 binder/`pm_qos` blocker에 남아 다음은 Android init/service-order 분류
- `reports/NATIVE_INIT_V668_CNSS2_FOCUSED_CAPTURE_LIVE_2026-05-24.md` – V668 live 결과 service `74` open/window 모두에서 icnss/QCA6390 sysfs focused capture는 준비됐지만 WLFW/BDF/`wlan0`는 여전히 0이라 다음은 Android/native cnss2 runtime delta 분류
- `reports/NATIVE_INIT_V667_CNSS2_PD_NOTIFIER_CLASSIFIER_2026-05-24.md` – V667 결과 V666의 service-notifier `180/74` 이후 cnss2 `pd_notifier`/QCA6390 power/WLFW/BDF/`wlan0` progression marker가 모두 없어 다음은 binder retry가 아니라 cnss2/WLAN-PD kernel progression gate
- `reports/NATIVE_INIT_V666_REPAIRED_PRIVATE_CNSS_RETRY_LIVE_2026-05-24.md` – V666 live 결과 private property/runtime surface와 service `74`/`vndservicemanager`/fresh CNSS retry는 통과했지만 WLFW service `69`/BDF/`wlan0`는 여전히 없어 다음은 cnss2/WLAN-PD `pd_notifier` progression classifier
- `reports/NATIVE_INIT_V666_REPAIRED_PRIVATE_CNSS_RETRY_PREP_2026-05-24.md` – helper v109와 V317 private property root를 fresh `cnss-daemon` retry 경로에 결합하는 V666 prep 기록
- `reports/NATIVE_INIT_V665_PRIVATE_REGISTRY_SNAPSHOT_PATH_REPAIR_2026-05-23.md` – helper v109로 registry snapshot이 private `dev/__properties__`와 `dev/socket` 경로를 캡처함을 live proof로 검증했고 다음은 repaired surface 기반 fresh CNSS retry
- `reports/NATIVE_INIT_V664_PRIVATE_RUNTIME_MATERIALIZATION_PREP_2026-05-23.md` – V664 prep으로 helper v108/V662 mode에 V317 private property root를 추가하는 no-CNSS-retry materialization runner를 준비
- `reports/NATIVE_INIT_V663_SNAPSHOT_ZERO_COUNT_CLASSIFIER_2026-05-23.md` – V663 host-only 결과 V662 zero-count는 snapshot 실패가 아니라 private Binder debugfs/property/socket runtime surface 부재로 분류되며, 다음은 V664 private property/runtime materialization proof
- `reports/NATIVE_INIT_V662_REGISTRY_CONTEXT_SNAPSHOT_LIVE_2026-05-23.md` – V662 live 결과 service `74`/`vndservicemanager_ready` 뒤 registry/context snapshot begin/end를 캡처했고 CNSS retry는 비활성으로 유지했으며, 다음은 snapshot zero-count 원인과 private Binder/property/service-registration surface 분류
- `reports/NATIVE_INIT_V662_REGISTRY_CONTEXT_SNAPSHOT_PREP_2026-05-23.md` – V662 prep 결과 helper v108에 service `74` gated registry/context snapshot mode를 추가하고 정적 ARM64 빌드와 runner/deploy wrapper 준비를 완료
- `reports/NATIVE_INIT_V661_BINDER_REGISTRATION_CONTEXT_CLASSIFIER_2026-05-23.md` – V661 host-only 결과 V660이 readiness/order/devnode/context-file 원인을 낮췄고, 남은 blocker를 dynamic vendor binder registration/property namespace gap으로 좁혀 다음은 bounded registry/context snapshot gate
- `reports/NATIVE_INIT_V660_READY_CNSS_RETRY_LIVE_2026-05-23.md` – V660 live 결과 V659-proven readiness 뒤 fresh `cnss_daemon_retry`가 실행됐지만 binder transaction `-22`가 지속되어 다음은 vendor binder registration/context classifier
- `reports/NATIVE_INIT_V659_VNDSERVICEMANAGER_READINESS_ONLY_LIVE_2026-05-23.md` – V659 live 결과 helper v107이 service `74` gate 뒤 `vndservicemanager` readiness를 증명했고 CNSS retry tail은 실행하지 않아, 다음은 proven readiness 이후 fresh `cnss-daemon` binder attempt gate
- `reports/NATIVE_INIT_V658_VNDBINDER_SURFACE_CLASSIFIER_2026-05-23.md` – V658 host-only 결과 helper v106 exact mode는 service `74`를 재현하지만 V653/V657 모두 `cnss-daemon` vndbinder transaction 전 WLFW에서 멈춰 다음은 V659 `vndservicemanager` readiness-only gate
- `reports/NATIVE_INIT_V657_SERVICE74_V106_REPLAY_LIVE_2026-05-23.md` – V657 live 결과 helper v106이 V653 exact mode에서 service `74` gate를 재현해 V655 timeout이 helper v106 일반 실패가 아님을 확인했고, 남은 blocker는 service-manager 이후 `cnss-daemon` binder surface
- `reports/NATIVE_INIT_V656_SERVICE74_REGRESSION_CLASSIFIER_2026-05-23.md` – V656 host-only 결과 V655는 QRTR/sysmon/V490은 V653과 같았지만 service `74`만 회귀했고 service-manager는 시작 전이라 다음은 helper v106으로 V653 exact mode replay
- `reports/NATIVE_INIT_V655_VNDSERVICEMANAGER_CNSS_RETRY_LIVE_2026-05-23.md` – V655 live 결과 helper v106/V641/V490 전제조건은 통과했지만 fresh service `74` gate가 timeout되어 service-manager/vndservicemanager/CNSS retry는 의도대로 보류됐고 다음은 V653 대비 service `74` 회귀 분류
- `reports/NATIVE_INIT_V655_VNDSERVICEMANAGER_CNSS_RETRY_PREP_2026-05-23.md` – V655 prep 결과 helper v106, runner, deploy wrapper가 빌드/plan/serial preflight를 통과했고 현재는 helper v106 deploy 후 bounded live proof가 다음 단계
- `reports/NATIVE_INIT_V654_BINDER_RUNTIME_MISMATCH_CLASSIFIER_2026-05-23.md` – V654 host-only 결과 binder devnode/SELinux/generic binder ioctl은 root cause 가능성이 낮고, `cnss-daemon`이 `vndservicemanager` readiness 증거 전 vndbinder transaction `-22`로 멈춰 다음은 vndservicemanager-ready + fresh `cnss-daemon` binder attempt proof
- `reports/NATIVE_INIT_V653_SERVICE74_GATED_SERVICE_MANAGER_LIVE_2026-05-23.md` – V653 live 결과 fresh service `74` gate 후 service-manager trio를 시작하면 service `180/74`는 보존되지만 `cnss-daemon` binder `-22`가 남아 다음은 binder/runtime mismatch classifier
- `reports/NATIVE_INIT_V653_SERVICE74_GATED_SERVICE_MANAGER_PREP_2026-05-23.md` – V653 prep/deploy 결과 helper v105가 service `74` gate 후 service-manager를 시작하는 새 모드로 배포됐고, live proof는 V641 clean-DSP와 V490 refresh가 다음 prerequisite
- `reports/NATIVE_INIT_V652_SERVICE74_BINDER_PARITY_LIVE_2026-05-23.md` – V652 live 결과 clean-DSP/V401/V490 전제조건에서 helper v104 CNSS-first delayed service-manager mode는 cleanup-safe였지만 service `180/74` publication을 회귀시켜, 다음은 service `74` 관찰 후 service-manager를 붙이는 explicit gated helper mode
- `reports/NATIVE_INIT_V652_SERVICE74_BINDER_PARITY_PREFLIGHT_2026-05-23.md` – V652 preflight 결과 helper v104와 real linkerconfig/APEX config는 준비됐지만 current boot의 V490 policy-load 증거와 V641 clean-DSP/RPMSG 상태가 없어, 다음은 V641 one-shot 재무장·재부팅 후 V490 refresh
- `reports/NATIVE_INIT_V651_CNSS_WLFW_CONTINUATION_2026-05-23.md` – V651 host-only 결과 Android는 CNSS genl failure 후 WLFW/WLAN-PD/QMI/BDF/`wlan0`까지 진행하지만 native V644는 CNSS netlink/`cld80211` 뒤 binder `-22` 반복으로 WLFW 전에서 멈춰 다음 gate는 bounded service-manager/binder-runtime parity proof
- `reports/NATIVE_INIT_V650_POST_WARNING_CONTINUATION_2026-05-23.md` – V650 host-only 결과 Android/native 모두 ASoC warning 후 sound-card까지 진행하지만 native만 WLFW/WLAN-PD/QMI/BDF/`wlan0`가 없어 다음 gate는 CNSS/WLFW continuation guard
- `reports/NATIVE_INIT_V649_ANDROID_FULL_AUDIO_WIFI_RECAPTURE_LIVE_2026-05-23.md` – V649 live/replay 결과 Android도 service `74` 직후 ASoC duplicate `pm_qos` warning을 내지만 WLFW/WLAN-PD/QMI/BDF/`wlan0`까지 계속 진행하므로 다음 gate는 post-warning continuation gap 비교
- `reports/NATIVE_INIT_V649_ANDROID_FULL_AUDIO_WIFI_RECAPTURE_PREP_2026-05-23.md` – V649 prep 결과 Android full audio/Wi-Fi collector와 v641 rollback handoff가 plan/dry-run 통과했고 다음은 live handoff recapture
- `reports/NATIVE_INIT_V648_AUDIO_ASOC_PARITY_GUARD_LIVE_2026-05-23.md` – V648 read-only 결과 current native v641 idle은 ASoC probe/duplicate `pm_qos`가 없고 V644 service `74` 경로에서만 warning이 나타나므로 다음 gate는 Android full audio/Wi-Fi dmesg recapture
- `reports/NATIVE_INIT_V647_WARNING_SOURCE_CLASSIFIER_2026-05-23.md` – V647 host-only 결과 V644 warning은 `msm_asoc_machine_probe` duplicate `pm_qos_add_request` 경로이며 V619/V638이 service `74` 없이 같은 warning을 재현하므로 다음 gate는 audio/ASoC parity guard
- `reports/NATIVE_INIT_V646_ANDROID_POST74_TIMING_2026-05-23.md` – V646 host-only 결과 Android는 service `74` 후 WLAN-PD까지 약 2.421초를 기다리지만 V644는 11.789ms 만에 warning을 내므로 다음 gate는 warning-source classifier
- `reports/NATIVE_INIT_V645_V644_WARNING_ATTRIBUTION_2026-05-23.md` – V645 host-only 결과 clean-DSP 단독/V627 service `180` 단독은 warning-free이고 V644 service `74` 후 11.789ms에 warning이 발생해 V646 Android post-service74 timing 비교가 다음 gate
- `reports/NATIVE_INIT_V644_CLEAN_DSP_CNSS_WLFW_READBACK_LIVE_2026-05-23.md` – V644 live 결과 V641 clean-DSP + CNSS-including companion에서 service `180`과 `74`가 처음 함께 재현됐지만 직후 `pm_qos_add_request` warning이 발생해 fail-safe로 중단하고 V645 warning attribution이 다음 gate
- `reports/NATIVE_INIT_V643_V642_PUBLISHER_GAP_CLASSIFIER_2026-05-23.md` – V643 host-only 결과 V642 no-CNSS clean-DSP 경로는 QRTR TX/`sysmon-qmi`까지만 가고, V598/V625/V627 CNSS-including 경로만 service `180`을 재현하므로 다음은 clean-DSP CNSS/WLFW readback replay
- `reports/NATIVE_INIT_V642_CLEAN_DSP_LOWER_COMPANION_LIVE_2026-05-23.md` – V642 live 결과 V641 clean-DSP 상태에서 Android-order lower companion이 QRTR TX와 `sysmon-qmi`까지 재현했지만 `service-notifier`/WLAN-PD/WLFW/`wlan0`는 없어 다음은 post-sysmon publisher gap classifier
- `reports/NATIVE_INIT_V641_FIRMWARE_BACKED_BOOT_WINDOW_ARMED_LIVE_2026-05-23.md` – V641 armed live 결과 firmware-backed ADSP/CDSP/SLPI writes는 모두 `rc=0`과 DSP PIL ready까지 진행했지만 `sysmon-qmi`/service `74`/WLAN-PD/WLFW/`wlan0`는 없어 다음은 clean DSP-PIL 상태의 lower companion observer
- `reports/NATIVE_INIT_V641_FIRMWARE_BACKED_BOOT_WINDOW_DISABLED_SMOKE_LIVE_2026-05-23.md` – V641 disabled-smoke live 결과 arm flag 없이 v641이 shell까지 부팅하고 proof log/flag/timeline marker 및 `pm_qos` proof marker가 없어 다음은 one-shot armed proof
- `reports/NATIVE_INIT_V641_FIRMWARE_BACKED_BOOT_WINDOW_PREP_2026-05-23.md` – V641 prep 결과 firmware-backed sibling SSCTL boot-window image가 로컬 빌드/marker/diff 검증을 통과했으며 다음 gate는 disabled-smoke 후 one-shot armed live proof
- `reports/NATIVE_INIT_V640_SAFE_SIBLING_TRIGGER_RECLASSIFICATION_2026-05-23.md` – V640 host-only 결과 service `74` 이전 미검증 non-write daemon 후보는 없고 late all-sibling write는 차단되어 다음은 rollback-ready firmware-backed early-boot sibling trigger proof로 분류
- `reports/NATIVE_INIT_V639_SIBLING_WARNING_ATTRIBUTION_2026-05-23.md` – V639 host-only 결과 V638 `pm_qos` warnings는 late all-sibling ADSP/CDSP/SLPI direct write sequence에 묶이고 CDSP-only/V636 service-180 path는 warning-free라 direct all-sibling retry를 중단
- `reports/NATIVE_INIT_V638_FIRMWARE_SIBLING_SSCTL_COMPOSITE_LIVE_2026-05-23.md` – V638 live 결과 firmware-backed ADSP/CDSP/SLPI child writes는 모두 반환됐지만 sibling `sysmon-qmi`/service `74`/WLAN-PD/WLFW/`wlan0`는 진전 없고 `pm_qos` kernel warning이 발생해 direct all-sibling write path를 중단
- `reports/NATIVE_INIT_V638_FIRMWARE_SIBLING_SSCTL_COMPOSITE_PREP_2026-05-23.md` – V638 prep 결과 firmware-backed ADSP/CDSP/SLPI per-node sibling SSCTL composite runner가 preflight-ready이며 live는 child timeout/reap, marker capture, mount cleanup, reboot cleanup으로 제한
- `reports/NATIVE_INIT_V637_SERVICE74_POST_CDSP_CLASSIFIER_2026-05-23.md` – V637 host-only 결과 CDSP power/ONLINE은 Android CDSP SSCTL `sysmon-qmi`와 다르며 V636이 service `180`까지만 재현했으므로 다음은 firmware-backed per-node sibling SSCTL composite observer 계획
- `reports/NATIVE_INIT_V636_CDSP_V598_COMPOSITE_LIVE_2026-05-23.md` – V636 live 결과 CDSP-online + V598-class modem-holder/readback 조합에서도 service `180`만 재현되고 service `74`/WLAN-PD/WLFW/BDF/`wlan0`는 없어 lower service `74` publisher dependency가 다음 blocker
- `reports/NATIVE_INIT_V636_CDSP_V598_COMPOSITE_PREP_2026-05-23.md` – V636 prep 결과 V635 CDSP-online proof와 V598/V625/V627 modem-holder partial-positive를 결합하는 runner가 plan/pass 상태이며, fresh V490 후 preflight/live가 다음 gate
- `reports/NATIVE_INIT_V635_FIRMWARE_CDSP_ONLY_PROOF_LIVE_2026-05-23.md` – V635 live 결과 firmware mount 상태에서 CDSP write는 timeout 없이 반환되고 CDSP PIL/reset/power-clock까지 진행했지만 `sysmon_cdsp`/service `74`/WLAN-PD/WLFW는 없어 post-CDSP-online gap이 다음 blocker
- `reports/NATIVE_INIT_V634_FIRMWARE_MOUNT_PARITY_LIVE_2026-05-23.md` – V634 live 결과 `apnhlos -> /vendor/firmware_mnt`, `modem -> /vendor/firmware-modem` read-only mount와 cleanup은 PASS, mount-only QRTR delta는 없어 V635 CDSP-only bounded proof가 다음 gate
- `reports/NATIVE_INIT_V633_CDSP_SURFACE_READONLY_LIVE_2026-05-23.md` – V633 live read-only 결과 `firmware_class.path=/vendor/firmware_mnt/image`이지만 native v319에 matching firmware mount/dir가 없어 CDSP write 전 firmware surface mount/verify가 다음 gate
- `reports/NATIVE_INIT_V632_CDSP_BLOCKER_CLASSIFIER_2026-05-23.md` – V632 host-only 결과 V631의 CDSP-only timeout과 Android V622 CDSP/service `74` timing을 묶어 다음 gate를 read-only native CDSP surface collector로 분류
- `reports/NATIVE_INIT_V631_PER_NODE_SIBLING_SSCTL_PROOF_LIVE_2026-05-23.md` – V631 live 결과 ADSP/SLPI boot-node write는 성공했지만 CDSP write가 timeout 후 reaped되어 service `74` 이전 active blocking node를 CDSP로 분류하고 v319 rollback 완료
- `reports/NATIVE_INIT_V631_PER_NODE_SIBLING_SSCTL_PROOF_PREP_2026-05-23.md` – V631 prep 결과 ADSP/CDSP/SLPI를 per-node child/timeout으로 나눈 `A90 Linux init 0.9.66 (v631)` boot image 로컬 빌드와 marker 검증 통과
- `reports/NATIVE_INIT_V630_SIBLING_SSCTL_BOOT_WINDOW_PROOF_LIVE_2026-05-23.md` – V630 live 결과 disabled-smoke와 rollback은 PASS, armed proof는 ADSP write 성공 후 child timeout으로 CDSP/SLPI 전 중단되어 V631 per-node bounded proof가 다음 gate
- `reports/NATIVE_INIT_V630_SIBLING_SSCTL_BOOT_WINDOW_PROOF_PREP_2026-05-23.md` – V630 prep 결과 `A90 Linux init 0.9.65 (v630)` boot image를 로컬 빌드했고 post-ACM one-shot sibling SSCTL proof marker 검증 통과, live disabled-smoke/armed proof/rollback이 다음 단계
- `reports/NATIVE_INIT_V629_SIBLING_SSCTL_TRIGGER_CLASSIFIER_2026-05-23.md` – V629 host-only 결과 Android visible trigger는 early-boot ADSP/CDSP/SLPI boot-node writes이고 native v319에는 equivalent path가 없어 V630 rollback-ready boot-time one-shot proof를 다음 gate로 선정
- `reports/NATIVE_INIT_V628_SERVICE74_PUBLISHER_CLASSIFIER_2026-05-23.md` – V628 host-only 결과 native V627은 service-locator/`180`까지 도달했지만 Android의 SLPI/CDSP/ADSP sibling `sysmon-qmi`와 service `74`가 없어 V629 safe sibling-SSCTL trigger 분석을 다음 gate로 선정
- `reports/NATIVE_INIT_V627_POST_180_OBSERVER_LIVE_2026-05-23.md` – V627 live 결과 V598/v100 경로가 `service-notifier 180`을 재현했지만 31.65초 post-180 window에서도 `74`/WLAN-PD/WLFW service `69`가 없어 lower service `74` publisher dependency를 다음 blocker로 분류
- `reports/NATIVE_INIT_V626_POST_180_PUBLICATION_CLASSIFIER_2026-05-23.md` – V626 host-only 결과 native V625는 warning-free `service-notifier 180`을 재현했지만 Android가 6.561ms 뒤 publish하는 `74`/WLAN-PD/WLFW service `69`가 없어 V627 post-180 lower observer가 다음 gate
- `reports/NATIVE_INIT_V625_FRESH_V598_REPLAY_LIVE_2026-05-23.md` – V625 live 결과 fresh boot에서 QRTR RX/TX, modem `sysmon-qmi`, service-notifier `180`이 warning 없이 재현됐지만 WLFW service `69`는 end-of-list라 `74`/WLAN-PD publication gap이 다음 blocker
- `reports/NATIVE_INIT_V624_SAFE_POSITIVE_REGRESSION_2026-05-23.md` – V624 host-only 분류 결과 V598은 warning-free partial positive지만 V606/V608에서 재현되지 않아, 다음은 새 daemon 추가가 아니라 fresh-boot V598-class replay/observer
- `reports/NATIVE_INIT_V623_LOWER_QMI_PUBLICATION_GAP_2026-05-23.md` – V623 host-only 분류 결과 `qmiproxy`는 disabled/static 후보일 뿐 Android running 증거가 없어 blind live target에서 제외하고, 다음은 direct DSP boot-node 없이 lower QMI publication을 재현할 안전 경로 분류
- `reports/NATIVE_INIT_V622_ANDROID_MDM_HELPER_TIMING_RECAPTURE_LIVE_2026-05-23.md` – V622 live same-boot Android capture 결과 `service-notifier 180`이 `mdm_launcher`/`mdm_helper`/`cnss_diag`보다 먼저 나타나므로 `mdm_helper` first-trigger 후보를 배제하고 V623 `qmiproxy`/lower QMI publication 분류로 이동
- `reports/NATIVE_INIT_V622_ANDROID_MDM_HELPER_TIMING_RECAPTURE_PREP_2026-05-23.md` – V622 same-boot Android read-only collector와 rollback handoff wrapper를 추가했고 plan/dry-run은 통과, 현재 native 상태에서는 Android ADB가 없어 live handoff가 다음 단계
- `reports/NATIVE_INIT_V621_MDM_HELPER_CONTRACT_CLASSIFIER_2026-05-23.md` – V621 host-only 분류 결과 `vendor.mdm_helper`는 실제 Android 서비스 후보지만 현재 boottime과 service-notifier dmesg가 서로 다른 부팅 증거라 V622 same-boot read-only recapture가 필요함
- `reports/NATIVE_INIT_V620_DSP_MDM3_SAFETY_CLASSIFIER_2026-05-23.md` – V620 host-only 재분류 결과 Android `sysmon_esoc0`은 service-notifier 뒤에 나타나 선행조건 가설을 배제하고, vendor init에 raw `esoc0`/`ioctl` 경로가 보이지 않아 `mdm_helper`/launcher 계약 분석으로 좁힘
- `reports/NATIVE_INIT_V619_ANDROID_ORDER_POST_SYSMON_OBSERVER_LIVE_2026-05-23.md` – V619 live에서 Android-order lower companion contract는 통과했지만 service-notifier는 0이고 `pm_qos_add_request` kernel warning이 재발해 direct DSP boot-node 반복을 중단
- `reports/NATIVE_INIT_V619_ANDROID_ORDER_POST_SYSMON_OBSERVER_PREP_2026-05-23.md` – helper v104에 `qrtr_ns,pd_mapper,rmt_storage,tftp_server` no-CNSS/no-HAL observer mode를 추가하고 현재 live preflight 환경 블로커를 기록
- `reports/NATIVE_INIT_V618_RFS_ALIAS_ORDER_CLASSIFIER_2026-05-23.md` – V618 host-only 분류 결과 `rfs_access`는 별도 live daemon 후보가 아니며 Android의 `qrtr_ns,pd_mapper,rmt_storage,tftp_server` 순서가 다음 bounded observer 후보로 좁혀짐
- `reports/NATIVE_INIT_V617_ANDROID_INIT_QMI_TRIGGER_CANDIDATE_CLASSIFIER_2026-05-23.md` – V617 host-only 분류 결과 Android는 `sysmon-qmi` 뒤 즉시 service-notifier `180/74`를 publish하지만 native V615는 core companion replay 후에도 notifier가 없고 `rfs_access`가 unreplayed 후보로 남음
- `reports/NATIVE_INIT_V616_POST_SIBLING_SYSMON_SERVICE_NOTIFIER_CLASSIFIER_2026-05-23.md` – V616 host-only 분류 결과 V615는 sibling `sysmon-qmi`와 service-locator까지 재현했지만 service-notifier `180/74`는 없고 `pm_qos_add_request` warning 23개로 direct boot-node retry가 차단됨
- `reports/NATIVE_INIT_V615_DSP_BOOT_NODE_OBSERVER_LIVE_2026-05-23.md` – V615 live에서 ADSP/CDSP/SLPI boot node write로 sibling `sysmon-qmi`까지 진전했지만 service-notifier `180/74`/WLAN-PD는 없고 `pm_qos_add_request` kernel warning이 발생해 direct boot-node retry를 중단
- `reports/NATIVE_INIT_V615_DSP_BOOT_NODE_OBSERVER_PREP_2026-05-23.md` – V614 다음 gate인 ADSP/CDSP/SLPI boot-node observer runner를 추가하고 plan 통과/current preflight는 V490 freshness로 차단됨을 기록
- `reports/NATIVE_INIT_V614_MDM3_TRIGGER_PATH_CLASSIFIER_2026-05-23.md` – V611/V613/vendor init 비교로 Android는 ADSP/CDSP/SLPI PIL 이후 sibling sysmon/service-notifier에 도달하지만 native V613은 MSS만 부팅함을 분류하고 V615 DSP boot-node observer를 다음 gate로 선정
- `reports/NATIVE_INIT_V613_MDM3_ESOC_TARGETED_OBSERVER_LIVE_2026-05-23.md` – V613 live에서 `mss=ONLINE`, QRTR `RX/TX`, modem `sysmon-qmi`, `rmt_storage`까지 재현했지만 raw `subsys_esoc0` open은 반환되지 않고 `mdm3=OFFLINING`/service-notifier 없음으로 끝나 다음 블로커를 `mdm3/esoc0` trigger path로 좁힘
- `reports/NATIVE_INIT_V613_MDM3_ESOC_TARGETED_OBSERVER_PREP_2026-05-23.md` – V612에서 좁힌 `mdm3/esoc0` delta를 native no-close holder + reboot cleanup으로 검증하는 V613 runner를 추가했고 current preflight는 V490 freshness만 차단
- `reports/NATIVE_INIT_V612_ANDROID_LOWER_SURFACE_HANDOFF_LIVE_2026-05-23.md` – Android handoff로 V611 lower-surface recapture를 실행해 `mdm3=ONLINE`, sibling sysmon, service-notifier `180/74`, QIPCRTR/rpmsg/service-locator를 확보하고 native v319 rollback 검증 완료
- `reports/NATIVE_INIT_V612_ANDROID_LOWER_SURFACE_HANDOFF_PREP_2026-05-23.md` – V611 Android lower-surface collector를 Android boot handoff/rollback 경로에 연결하는 wrapper를 추가하고 plan/dry-run 검증 완료
- `reports/NATIVE_INIT_V611_ANDROID_LOWER_SURFACE_RECAPTURE_PREP_2026-05-23.md` – V610의 Android evidence limit을 닫기 위한 lower-surface Android read-only collector를 추가했고 현재 native 상태에서는 ADB 없음으로 preflight가 차단됨
- `reports/NATIVE_INIT_V610_QMI_PUBLICATION_PRECONDITION_2026-05-23.md` – Android는 `mss/mdm3` ONLINE과 sibling sysmon/service-notifier를 갖지만 native V609는 `mss`만 ONLINE이고 `mdm3=OFFLINING`이라 lower publication surface gap으로 분류
- `reports/NATIVE_INIT_V609_POST_SYSMON_OBSERVER_LIVE_2026-05-23.md` – CNSS 없는 post-sysmon observer에서 QRTR TX/`sysmon-qmi`까지 도달했지만 `service-notifier`/WLFW service `69`는 미등록이라 lower QMI publication precondition 갭으로 분류
- `reports/NATIVE_INIT_V609_POST_SYSMON_OBSERVER_PREP_2026-05-23.md` – helper v103에 CNSS 없는 post-sysmon observer mode를 추가하고 runner/deploy preflight를 검증해 V609 live 준비 완료
- `reports/NATIVE_INIT_V608_HELPER_V100_BASELINE_REPLAY_2026-05-23.md` – helper v100 재배포 후 V598 baseline을 재생해도 `service-notifier` `180`이 복구되지 않아 lower modem QMI publication 안정성/전제조건 갭으로 재분류
- `reports/NATIVE_INIT_V607_QMI_SERVICE_PUBLICATION_DELTA_2026-05-23.md` – V598/V606 비교에서 lower readiness/order/readback/timing은 같고 helper marker만 v100→v102로 바뀐 상태에서 `service-notifier` `180`이 소실되어 helper v100 replay를 다음 gate로 선정
- `reports/NATIVE_INIT_V606_V102_BASELINE_REPLAY_2026-05-23.md` – current helper v102로 V598 no-service-manager baseline을 재생했지만 `service-notifier` `180`이 재현되지 않아 lower QMI service-publication 갭으로 분류
- `reports/NATIVE_INIT_V605_SERVICE_NOTIFIER_TIMING_CLASSIFIER_2026-05-22.md` – V598의 service-notifier `180`은 CNSS보다 먼저 떴고 V604b는 더 긴 pre-CNSS window에도 안 떠서 다음 후보를 v102 no-service-manager baseline replay로 좁힘
- `reports/NATIVE_INIT_V604_CNSS_FIRST_SERVICE_MANAGER_LIVE_2026-05-22.md` – CNSS-first delayed service-manager live proof에서도 service-notifier `180`은 없고 binder transaction failure 3회가 확인되어 V598/V604 timing classifier가 다음 후보로 분류됨
- `reports/NATIVE_INIT_V604_CNSS_FIRST_SERVICE_MANAGER_PREP_2026-05-22.md` – helper v102에 CNSS-first delayed service-manager 모드를 추가하고 deploy/live runner plan-only 검증을 완료
- `reports/NATIVE_INIT_V603_QRTR_FIRST_SERVICE_MANAGER_LIVE_2026-05-22.md` – QRTR-first service-manager live proof에서 binder failure는 0으로 유지됐지만 service-notifier `180`이 재소실되어 delayed-CNSS/order 조정이 다음 후보로 분류됨
- `reports/NATIVE_INIT_V603_QRTR_FIRST_SERVICE_MANAGER_PREP_2026-05-22.md` – helper v101에 `wifi-companion-qrtr-first-vnd-service-manager-start-only` 모드를 추가해 service-notifier `180` 보존과 binder clean을 함께 검증할 준비를 완료
- `reports/NATIVE_INIT_V602_SERVICE_MANAGER_ORDERING_GAP_2026-05-22.md` – V598은 service-notifier `180`까지 도달하지만 binder transaction failure가 있고, V601은 binder failure를 해소하지만 service-notifier `180`을 잃어 다음 live gate를 qrtr-first/delayed service-manager로 좁힘
- `reports/NATIVE_INIT_V601_SERVICE_MANAGER_BINDER_PROOF_2026-05-22.md` – service-manager 포함 modem-holder companion window에서 binder transaction failure는 해소됐지만 WLFW service `69`/service-notifier `74`/WLAN-PD는 여전히 미등록
- `reports/NATIVE_INIT_V600_REGISTRY_CNSS_MATRIX_2026-05-22.md` – native는 QRTR TX/`sysmon-qmi`/service-notifier `180`/CNSS netlink까지 도달하지만 `cnss-daemon` binder `-22` 반복으로 `wlfw_start` 전에 멈춤
- `reports/NATIVE_INIT_V599_SERVICE_NOTIFIER_INSTANCE_GAP_2026-05-22.md` – V598 native는 `sysmon-qmi` modem과 service-notifier `180`까지만 도달했고 Android의 `74`/WLAN-PD/WLFW service `69` 등록은 아직 없음
- `reports/NATIVE_INIT_V598_MODEM_HOLDER_WLFW_READBACK_2026-05-22.md` – V596 holder window에 WLFW QRTR nameservice readback을 추가해 service-notifier `180`까지는 진입했지만 WLFW service `69`는 end-of-list로 미등록임을 확인
- `reports/NATIVE_INIT_V597_POST_SYSMON_GAP_2026-05-22.md` – Android reference에서 `sysmon-qmi` 이후 약 22ms 만에 service-notifier가 뜨고, native V596은 QRTR TX/sysmon까지만 도달해 post-sysmon service-notifier gap임을 host-only로 분류
- `reports/NATIVE_INIT_V596_MODEM_HOLDER_COMPANION_2026-05-22.md` – global firmware mounts + `subsys_modem` holder + companion start-only로 QRTR RX 이후 QRTR TX와 `sysmon-qmi`까지 진입, WLFW/BDF/`wlan0`는 아직 없음
- `reports/NATIVE_INIT_V594_V595_GLOBAL_FIRMWARE_MODEM_READINESS_2026-05-22.md` – native global namespace에 `/vendor/firmware_mnt`와 `/vendor/firmware-modem`을 마운트하면 modem PIL/QRTR RX까지 진행함을 확인하고 raw close reference mismatch 위험을 분류
- `reports/NATIVE_INIT_V593_SUBSYS_OFFLINING_CLASSIFIER_2026-05-22.md` – native modem/esoc OFFLINING 원인을 firmware/PIL readiness gap으로 좁히기 위한 classifier 결과
- `reports/NATIVE_INIT_V592_SUBSYS_HOLD_OPEN_2026-05-22.md` – modem/esoc subsystem hold-open 실험으로 lower modem readiness trigger 가능성을 확인
- `reports/NATIVE_INIT_V591_ANDROID_SUBSYS_STATE_HANDOFF_2026-05-22.md` – Android handoff 기반 subsystem state 비교 자료
- `reports/NATIVE_INIT_V590_ANDROID_SUBSYS_STATE_SAMPLE_2026-05-22.md` – Android-side read-only modem/esoc state collector를 추가했고 현재 native 상태에서는 Android ADB가 없어 handoff 후 실행해야 함을 기록
- `reports/NATIVE_INIT_V589_ANDROID_SUBSYS_STATE_GAP_2026-05-22.md` – Android readiness timeline은 있으나 direct Android modem/esoc state sample이 없어 V590 Android read-only state capture가 필요함을 분류
- `reports/NATIVE_INIT_V588_MODEM_SUBSYS_WINDOW_VALUES_2026-05-22.md` – helper v99로 companion window 내부 `modem`/`esoc0` subsystem 값이 둘 다 `OFFLINING`임을 캡처하고 QRTR/QMI/WLFW/BDF/FW-ready marker 부재를 분류
- `reports/NATIVE_INIT_V587_QRTR_MODEM_WINDOW_SURFACE_2026-05-22.md` – helper v98로 companion window 내부 `/proc/net/qrtr`, `/dev`, `msm_subsys`, `rpmsg`, modem sysfs surface를 캡처했지만 QRTR/QMI/WLFW/BDF/FW-ready marker는 여전히 없음을 분류
- `reports/NATIVE_INIT_V586_QRTR_COMPANION_BLOCKER_2026-05-22.md` – V585 private firmware mount + companion window 이후에도 QRTR proc table 부재, `QIPCRTR` socket 0, Android-only QRTR/QMI/WLAN-PD/WLFW marker 부재를 read-only로 분류
- `reports/NATIVE_INIT_V585_COMPANION_FIRMWARE_MOUNT_LIVE_2026-05-22.md` – helper-private `apnhlos`/`modem` mount와 companion start-only window는 통과했지만 QRTR/QMI/WLFW/BDF/FW-ready marker가 없음을 확인
- `reports/NATIVE_INIT_V584_FIRMWARE_MODEM_MOUNT_PROOF_2026-05-22.md` – native에서 Android firmware/modem mount parity를 read-only mount/cleanup proof로 재현했지만 readiness delta는 없음을 확인
- `reports/NATIVE_INIT_V583_FIRMWARE_MOUNT_PARITY_2026-05-22.md` – Android가 QRTR modem readiness 전에 `/vendor/firmware_mnt`와 `/vendor/firmware-modem`을 마운트하지만 native global namespace에는 해당 parity가 없음을 read-only로 분류
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
