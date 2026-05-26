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

- `plans/NATIVE_INIT_V1004_SERVICE_WINDOW_SUBSYS_TRIGGER_LIVE_PLAN_2026-05-26.md` – helper `v170`으로 current-boot SELinux refresh 후 Android service-window scoped `/dev/subsys_esoc0` trigger capture를 수행하는 V1004 live 계획
- `plans/NATIVE_INIT_V1005_V1004_FD_GAP_CLASSIFIER_PLAN_2026-05-26.md` – V1000 Android dmesg/process, V911 native `mdm_helper` fd, V1004 service-window fd-gate 실패를 host-only로 비교해 다음 gate를 고르는 V1005 계획
- `plans/NATIVE_INIT_V1006_SERVICE_WINDOW_FD_POLL_SUPPORT_PLAN_2026-05-26.md` – V1005가 선택한 helper `v171` service-window `mdm_helper` `/dev/esoc-0` repeated fd-poll support source/build 계획
- `plans/NATIVE_INIT_V1007_HELPER_V171_DEPLOY_PLAN_2026-05-26.md` – helper `v171`을 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 remote sha/contract parity를 확인하는 V1007 계획
- `plans/NATIVE_INIT_V1008_SERVICE_WINDOW_FD_POLL_LIVE_PLAN_2026-05-26.md` – helper `v171`으로 current-boot SELinux refresh 후 Android service-window fd-poll/subsystem-trigger live gate를 실행하는 V1008 계획
- `plans/NATIVE_INIT_V1009_V911_V1008_CONTRACT_COMPARATOR_PLAN_2026-05-26.md` – V911 reduced runtime-contract fd-positive 경로와 V1008 full service-window fd-negative 경로를 host-only로 비교해 V1010 격리 gate를 고르는 계획
- `plans/NATIVE_INIT_V1010_MDM_HELPER_RUNTIME_SERVICE_DEFAULTS_PLAN_2026-05-26.md` – reduced V911 `mdm_helper` runtime-contract 순서에 service-defaults SELinux를 강제해 V911 양성 경로의 domain 의존성을 격리하는 V1010 계획
- `plans/NATIVE_INIT_V1011_V1008_V1010_ACTOR_DELTA_PLAN_2026-05-26.md` – V1008 full service-window fd-negative와 V1010 reduced service-defaults fd-positive를 비교해 after-fd CNSS/service-manager matrix gate를 선택하는 V1011 계획
- `plans/NATIVE_INIT_V1012_AFTER_FD_CNSS_MATRIX_PLAN_2026-05-26.md` – helper `v171` after-fd CNSS/service-manager matrix를 실행해 fd-positive lower state 뒤 CNSS/WLFW precondition을 검증하는 V1012 계획
- `plans/NATIVE_INIT_V1013_V1012_WLFW_GAP_CLASSIFIER_PLAN_2026-05-26.md` – V1012 after-fd CNSS matrix의 WLFW gap을 V1008/Android dmesg/helper-source 증거와 비교해 after-fd Wi-Fi surface matrix를 다음 단위로 선택하는 V1013 계획
- `plans/NATIVE_INIT_V1014_AFTER_FD_WIFI_SURFACE_MATRIX_SUPPORT_PLAN_2026-05-26.md` – helper `v172`에 after-fd Wi-Fi HAL legacy/ext + `wificond` surface matrix order를 source/build-only로 추가하는 V1014 계획
- `plans/NATIVE_INIT_V1015_HELPER_V172_DEPLOY_PLAN_2026-05-26.md` – helper `v172`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 설치하고 remote sha/contract parity를 확인하는 V1015 계획
- `plans/NATIVE_INIT_V1016_AFTER_FD_WIFI_SURFACE_MATRIX_LIVE_PLAN_2026-05-26.md` – helper `v172` after-fd fd predicate 뒤 service-manager/Wi-Fi HAL/`wificond`/CNSS를 시작해 WLFW precondition을 관찰하는 V1016 live 계획
- `plans/NATIVE_INIT_V1017_V1016_ANDROID_LOWER_GAP_CLASSIFIER_PLAN_2026-05-26.md` – V1016 no-WLFW 결과와 Android dmesg의 `/dev/subsys_esoc0`/`wlfw_start` window를 비교해 다음 scoped subsystem-window gate를 고르는 V1017 계획
- `plans/NATIVE_INIT_V1018_AFTER_FD_SUBSYS_WINDOW_SUPPORT_PLAN_2026-05-26.md` – helper `v173`에 after-fd upper-surface 뒤 bounded `/dev/subsys_esoc0` window order/gate를 source/build-only로 추가하는 V1018 계획
- `plans/NATIVE_INIT_V1019_HELPER_V173_DEPLOY_PLAN_2026-05-26.md` – helper `v173`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 설치하고 remote sha/order/gate parity를 확인하는 V1019 계획
- `plans/NATIVE_INIT_V1020_AFTER_FD_SUBSYS_WINDOW_LIVE_PLAN_2026-05-26.md` – helper `v173`으로 fd-positive upper-surface 뒤 WLFW가 없는 상태에서 scoped `/dev/subsys_esoc0` window를 여는 V1020 live 계획
- `plans/NATIVE_INIT_V1021_V1020_ANDROID_RESET_HANDSHAKE_CLASSIFIER_PLAN_2026-05-26.md` – V1020 `sdx50m_toggle_soft_reset` D-state를 Android-good PM/eSoC evidence와 비교해 다음 read-only recapture route를 고르는 V1021 계획
- `plans/NATIVE_INIT_V1022_ANDROID_PM_ESOC_TIMING_SAMPLER_PLAN_2026-05-26.md` – Android 정상 부팅 직후 ADB read-only로 PM/eSoC/GPIO/IRQ/WLFW 타이밍을 캡처하는 V1022 계획
- `plans/NATIVE_INIT_V1023_ANDROID_PM_ESOC_TIMING_HANDOFF_PLAN_2026-05-26.md` – Android boot handoff로 V1022 early/late read-only sampler를 실행하고 native v724 rollback까지 검증하는 V1023 계획
- `plans/NATIVE_INIT_V1024_FAST_FD_CONTRACT_CLASSIFIER_PLAN_2026-05-26.md` – V1022 target-fd-first 개선과 V1024 handoff evidence를 합쳐 Android PM/eSoC fd contract를 분류하는 계획
- `plans/NATIVE_INIT_V1025_PM_FULL_CONTRACT_SUPPORT_PLAN_2026-05-26.md` – helper `v174`에 Android PM full-contract fd gate를 source/build-only로 추가하는 계획
- `plans/NATIVE_INIT_V1026_HELPER_V174_DEPLOY_PLAN_2026-05-26.md` – helper `v174`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 설치하고 remote sha/order parity를 확인하는 계획
- `plans/NATIVE_INIT_V1027_PM_FULL_CONTRACT_LIVE_PLAN_2026-05-26.md` – helper `v174` PM full-contract order를 live로 실행해 `pm_proxy_helper`/`pm-service` `/dev/subsys_modem` fd predicate를 검증하는 계획
- `plans/NATIVE_INIT_V1028_PM_PROXY_HELPER_MODEM_GET_CLASSIFIER_PLAN_2026-05-26.md` – V1024 Android PM fd contract와 V1027 native PM full-contract 실패를 비교해 `pm_proxy_helper` modem subsystem-get blocker를 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V1003_HELPER_V170_DEPLOY_PLAN_2026-05-26.md` – V1002 helper `v170` 산출물을 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 sha/contract parity를 확인하는 V1003 계획
- `plans/NATIVE_INIT_V1002_ANDROID_SERVICE_WINDOW_SUBSYS_TRIGGER_SUPPORT_PLAN_2026-05-26.md` – V1001에서 선택한 service-window-scoped `/dev/subsys_esoc0` trigger capture를 helper `v170`에 source/build-only로 추가하는 V1002 계획
- `plans/NATIVE_INIT_V1001_V1000_ROUTE_COMPARATOR_PLAN_2026-05-26.md` – V1000 Android timing과 V998/V923/V964/V965 native evidence를 비교해 WLFW-precondition gate가 circular인지 host-only로 판정하는 V1001 계획
- `plans/NATIVE_INIT_V1000_ANDROID_ESOC_GPIO_RECAPTURE_HANDOFF_PLAN_2026-05-26.md` – V999 이후 Android boot image로 임시 handoff해 MDM3/eSoC/GPIO/PMIC/PCIe 타이밍을 read-only ADB로 재캡처하고 native v724로 롤백하는 V1000 계획
- `plans/NATIVE_INIT_V999_POST_SELINUX_WLFW_ROUTE_PLAN_2026-05-26.md` – V998 이후 SELinux/service-window blocker가 제거됐지만 WLFW precondition이 남은 상태에서 Android dmesg/eSoC/GPIO 재캡처를 다음 route로 선택할지 host-only로 분류하는 V999 계획
- `plans/NATIVE_INIT_V998_ANDROID_SERVICE_WINDOW_POST_SELINUX_PLAN_2026-05-26.md` – V997 current-boot SELinux proof 이후 helper `v169` Android service-window를 scan/connect 없이 한 번 재검증하는 V998 계획
- `plans/NATIVE_INIT_V997_CURRENT_BOOT_SELINUX_DOMAIN_PROOF_PLAN_2026-05-26.md` – helper `v169` 배포 후 current-boot V401/V490 refresh와 service-window 핵심 domain proof를 실행하는 V997 계획
- `plans/NATIVE_INIT_V996_HELPER_V169_DEPLOY_PLAN_2026-05-26.md` – helper `v169`를 deploy-only로 올리고 remote sha/contract parity를 확인하는 V996 계획
- `plans/NATIVE_INIT_V995_SELINUX_DOMAIN_ALLOWLIST_PLAN_2026-05-26.md` – V994가 선택한 fresh SELinux proof route를 위해 helper `v169`에서 `wificond`/`vndservicemanager` domain proof coverage를 source/build-only로 추가하는 V995 계획
- `plans/NATIVE_INIT_V994_SELINUX_ROUTE_CLASSIFIER_PLAN_2026-05-26.md` – V993 이후 `wificond` SELinux transition gap의 다음 route를 current-boot V490/domain proof refresh로 좁히는 V994 host-only 계획
- `plans/NATIVE_INIT_V968_ANDROID_DMESG_ESOC_GPIO_TIMING_PLAN_2026-05-26.md` – Android-good boot의 MDM3/eSoC GPIO/PMIC/PCIe timing을 read-only dmesg와 sysfs evidence로 분류해 V967 service-window live 전 native divergence를 줄이는 V968 계획
- `plans/NATIVE_INIT_V940_SDX50M_QUEUE_INPUT_CONTRACT_PLAN_2026-05-26.md` – V938/V939 이후 exact property-context override 대신 `mdm_helper`/PeripheralManager SDX50M queue input contract를 host-only로 분류하기 위한 V940 계획
- `plans/NATIVE_INIT_V929_CURRENT_V153_CNSS_SERVICE_MANAGER_MATRIX_PLAN_2026-05-26.md` – V603/V604/V605/V606의 단순 ordering 실패를 반복하지 않도록 helper `v153` repaired namespace 기반 CNSS/service-manager matrix helper `v154`를 source/build-only로 설계하는 V929 계획
- `plans/NATIVE_INIT_V928_CNSS_BINDER_LOWER_INTERSECTION_PLAN_2026-05-26.md` – V927 compact 결과와 V603 service-manager 결과를 host-only로 비교해 다음 blocker가 Binder-clean과 lower publication을 같은 window에 맞추는 문제인지 분류하는 V928 계획
- `plans/NATIVE_INIT_V927_CNSS_BEFORE_ESOC_COMPACT_LIVE_PLAN_2026-05-26.md` – helper `v153` compact CNSS surface로 V923 CNSS-before-eSoC live gate를 재실행해 transcript truncation 없이 WLFW precondition gap을 확인하는 V927 계획
- `plans/NATIVE_INIT_V926_HELPER_V153_DEPLOY_PLAN_2026-05-26.md` – helper `v153`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 remote checksum parity를 증명하는 V926 계획
- `plans/NATIVE_INIT_V925_CNSS_RUNTIME_NAMESPACE_SUPPORT_PLAN_2026-05-26.md` – V924가 지정한 CNSS runtime namespace/output-throttle blocker를 helper `v153` source/build-only로 수리하는 V925 계획
- `plans/NATIVE_INIT_V924_CNSS_WLFW_PRECONDITION_GAP_PLAN_2026-05-26.md` – V923 이후 CNSS가 `cld80211` netlink에는 도달하지만 WLFW/BDF/`wlan0`로 진행하지 못하는 precondition gap을 host-only로 분류하는 V924 계획
- `plans/NATIVE_INIT_V920_CNSS_BEFORE_ESOC_TRIGGER_PLAN_2026-05-26.md` – V919에서 확인된 Android ordering을 반영해 `cnss-daemon wlfw_start` precondition이 관찰될 때만 `/dev/subsys_esoc0` trigger를 여는 fail-closed V920/V921/V923 설계
- `plans/NATIVE_INIT_V919_SDX50M_SOFT_RESET_BLOCKER_PLAN_2026-05-26.md` – V918에서 확인된 `sdx50m_toggle_soft_reset` D-state blocker를 Android/OSRC/DTS evidence로 host-only 분류하는 V919 계획
- `plans/NATIVE_INIT_V915_CORRECTED_NATIVE_TRIGGER_GATE_PLAN_2026-05-26.md` – V914 결과를 반영해 다음 native `/dev/subsys_esoc0` trigger gate의 성공 기준을 WLFW/BDF/wlan0 중심으로 보정하는 V915 계획
- `plans/NATIVE_INIT_V913_ANDROID_ESOC_GPIO_TIMELINE_PLAN_2026-05-26.md` – V912의 `/dev/subsys_esoc0` trigger 전에 Android 정상 부팅의 GPIO135/PMIC GPIO9/GPIO142/PCIe/MDM3/KS/MHI/WLFW 양성 타임라인을 read-only로 재분류하는 V913 계획
- `plans/NATIVE_INIT_V912_MDM_HELPER_SUBSYS_TRIGGER_PLAN_2026-05-26.md` – V911에서 `mdm_helper`가 `ESOC_WAIT_FOR_REQ`에 들어간 뒤 `/dev/subsys_esoc0` powerup trigger를 어떻게 안전하게 계획할지 정의하는 V912 계획
- `plans/NATIVE_INIT_V911_MDM_HELPER_ESOC_FD_STALL_CLASSIFIER_PLAN_2026-05-26.md` – helper `v149` live capture를 분류해 `mdm_helper` worker가 `ESOC_WAIT_FOR_REQ`에 들어가는지 검증하는 V911 계획
- `plans/NATIVE_INIT_V910_HELPER_V149_DEPLOY_PLAN_2026-05-26.md` – helper `v149`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 원격 checksum/mode parity를 증명하는 V910 계획
- `plans/NATIVE_INIT_V909_MDM_HELPER_ESOC_FD_STALL_SUPPORT_PLAN_2026-05-26.md` – V908의 `/dev/esoc-0` fd 이후 `ks`/MHI 미진입 경계를 보기 위한 helper `v149` fdinfo/stall snapshot source/build-only 계획
- `plans/NATIVE_INIT_V908_MDM_HELPER_RUNTIME_CONTRACT_CAPTURE_PLAN_2026-05-26.md` – helper `v148` runtime-contract capture를 selinuxfs mount/cleanup + property shim + `per_mgr_light` 순서로 bounded live 검증하는 V908 계획
- `plans/NATIVE_INIT_V907_HELPER_V148_DEPLOY_PLAN_2026-05-26.md` – helper `v148`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 원격 checksum/mode parity를 증명하는 V907 계획
- `plans/NATIVE_INIT_V906_MDM_HELPER_RUNTIME_CONTRACT_HELPER_PLAN_2026-05-26.md` – helper `v148`에 property shim 기반 `mdm_helper` runtime-contract capture mode를 source/build-only로 추가하는 V906 계획
- `plans/NATIVE_INIT_V905_MDM_HELPER_RUNTIME_REPAIR_DESIGN_PLAN_2026-05-26.md` – V896 Android dmesg/Magisk 재캡처 필요성과 V904 이후 `mdm_helper` runtime-input repair 방향을 host-only로 분류하는 V905 계획
- `plans/NATIVE_INIT_V904_MDM_HELPER_RUNTIME_INPUT_PARITY_PLAN_2026-05-26.md` – Android/native `mdm_helper` runtime input parity를 host-only로 분류하는 V904 계획
- `plans/NATIVE_INIT_V903_MDM_HELPER_ONLY_DEEP_CAPTURE_PLAN_2026-05-26.md` – `/dev/subsys_esoc0` open 없이 native `mdm_helper` process/fd/socket surface만 capture하는 V903 계획
- `plans/NATIVE_INIT_V902_MDM_HELPER_KS_BLOCKER_CAPTURE_PLAN_2026-05-26.md` – V900의 `/dev/subsys_esoc0` block child에 wchan/syscall/stack/status/sched capture를 추가하는 V902 계획
- `plans/NATIVE_INIT_V901_HELPER_V145_ALLOWLIST_DEPLOY_PLAN_2026-05-26.md` – V900 첫 시도에서 드러난 helper global v235 allowlist 누락을 `v145`로 수정하고 deploy-only 배포하는 V901 계획
- `plans/NATIVE_INIT_V900_MDM_HELPER_KS_CONTRACT_LIVE_PLAN_2026-05-26.md` – Android-derived `mdm_helper` before `/dev/subsys_esoc0` + `ks`/MHI 관찰을 bounded live로 검증하는 V900 계획
- `plans/NATIVE_INIT_V899_HELPER_V144_DEPLOY_PLAN_2026-05-26.md` – helper `v144`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 원격 checksum/mode parity를 증명하는 V899 계획
- `plans/NATIVE_INIT_V898_MDM_HELPER_KS_CONTRACT_HELPER_PLAN_2026-05-26.md` – V897에서 요구한 pre-subsys `mdm_helper`/`ks` image-contract mode를 helper `v144`에 source/build-only로 추가하는 V898 계획
- `plans/NATIVE_INIT_V897_MDM_HELPER_KS_CONTRACT_DESIGN_PLAN_2026-05-26.md` – Android `mdm_helper`/`ks` image/link contract를 native helper에 어떻게 옮길지 host-only로 분류하는 V897 계획
- `plans/NATIVE_INIT_V896_ANDROID_MDM_HELPER_IMAGE_CONTRACT_PLAN_2026-05-26.md` – Android `mdm_helper`/`ks` MHI image/link contract를 기존 증거만으로 V895 negative control과 비교 분류하는 V896 계획
- `plans/NATIVE_INIT_V895_MDM2AP_IRQ_SNAPSHOT_PROOF_PLAN_2026-05-26.md` – `IMG_XFER_DONE` 전후 GPIO 142 `mdm status` IRQ count를 bounded live로 관측하는 V895 계획
- `plans/NATIVE_INIT_V894_MDM2AP_READY_SURFACE_PLAN_2026-05-26.md` – MDM2AP status/ready 전환을 관측할 read-only surface를 분류하는 V894 계획
- `plans/NATIVE_INIT_V893_ESOC_POST_IMG_XFER_CLASSIFIER_PLAN_2026-05-26.md` – V891의 `IMG_XFER_DONE` 이후 `GET_STATUS=0` 원인을 source-backed로 분류하는 V893 계획
- `plans/NATIVE_INIT_V892_HELPER_V142_ALLOWLIST_DEPLOY_PLAN_2026-05-26.md` – helper `v142`에서 conditional response mode 전역 allowlist 누락을 수정하고 deploy-only로 올리는 V892 계획
- `plans/NATIVE_INIT_V891_ESOC_CONDITIONAL_RESPONSE_PROOF_PLAN_2026-05-26.md` – `ESOC_REQ_IMG`에 `ESOC_IMG_XFER_DONE`으로 응답하고 status-gated `BOOT_DONE`을 검증하는 V891 계획
- `plans/NATIVE_INIT_V890_HELPER_V141_DEPLOY_PLAN_2026-05-26.md` – helper `v141`을 `/cache/bin/a90_android_execns_probe`에 deploy-only로 올리는 V890 계획
- `plans/NATIVE_INIT_V889_ESOC_CONDITIONAL_RESPONSE_HELPER_PLAN_2026-05-26.md` – helper `v141`에 status-gated eSoC conditional response mode를 source/build-only로 추가하는 V889 계획
- `plans/NATIVE_INIT_V888_ESOC_RESPONSE_GATE_CLASSIFIER_PLAN_2026-05-26.md` – `ESOC_REQ_IMG` 이후 첫 response와 `BOOT_DONE` 조건을 host-only로 분류하는 V888 계획
- `plans/NATIVE_INIT_V887_HELPER_V140_DEPLOY_PLAN_2026-05-26.md` – helper `v140`을 `/cache/bin/a90_android_execns_probe`에 deploy-only로 올리는 V887 계획
- `plans/NATIVE_INIT_V886_ESOC_REQ_IMG_RESPONSE_HELPER_PLAN_2026-05-26.md` – helper `v140`에서 `ESOC_WAIT_FOR_REQ` byte-count 의미를 수정하고 fail-closed response scaffold를 추가하는 V886 계획
- `plans/NATIVE_INIT_V885_ESOC_REQ_IMG_RESPONSE_CLASSIFIER_PLAN_2026-05-26.md` – V884 `ESOC_WAIT_FOR_REQ rc=4 value=1`을 `ESOC_REQ_IMG` response contract로 host-only 분류하는 V885 계획
- `plans/NATIVE_INIT_V884_REQ_REGISTERED_SUBSYS_HOLD_OBSERVER_PLAN_2026-05-26.md` – helper `v139`으로 REQ-registered `/dev/subsys_esoc0` hold window와 passive `ESOC_WAIT_FOR_REQ` observer를 실행하는 V884 계획
- `plans/NATIVE_INIT_V883_HELPER_V139_DEPLOY_PLAN_2026-05-26.md` – helper `v139`을 `/cache/bin/a90_android_execns_probe`에 deploy-only로 올리는 V883 계획
- `plans/NATIVE_INIT_V882_PASSIVE_WAIT_FOR_REQ_HELPER_PLAN_2026-05-26.md` – helper `v139`에 passive `ESOC_WAIT_FOR_REQ` observer support를 source/build-only로 추가하는 V882 계획
- `plans/NATIVE_INIT_V881_HELPER_V138_DEPLOY_PLAN_2026-05-26.md` – helper `v138`을 `/cache/bin/a90_android_execns_probe`에 deploy-only로 올리는 V881 계획
- `plans/NATIVE_INIT_V880_REQ_REGISTERED_SUBSYS_HOLD_HELPER_PLAN_2026-05-26.md` – helper `v138`에 fail-closed REQ-registered subsystem-hold preflight mode를 source/build-only로 추가하는 V880 계획
- `plans/NATIVE_INIT_V879_CMD_ENGINE_OWNERSHIP_CLASSIFIER_PLAN_2026-05-26.md` – V878 `REG_CMD_ENG EBUSY`와 `REG_REQ_ENG rc0`를 다음 subsystem-powerup 후보로 분류하는 V879 계획
- `plans/NATIVE_INIT_V878_ESOC_ENGINE_REGISTER_PREFLIGHT_PLAN_2026-05-25.md` – helper `v137`으로 bounded `REG_CMD_ENG`/`REG_REQ_ENG` registration preflight를 실행하는 V878 계획
- `plans/NATIVE_INIT_V877_HELPER_V137_DEPLOY_PLAN_2026-05-25.md` – helper `v137`을 `/cache/bin/a90_android_execns_probe`에 deploy-only로 올리는 V877 계획
- `plans/NATIVE_INIT_V876_ESOC_ENGINE_REGISTER_HELPER_PLAN_2026-05-25.md` – helper `v137`에 fail-closed CMD/REQ engine registration preflight mode를 source/build-only로 추가하는 V876 계획
- `plans/NATIVE_INIT_V875_ESOC_STATE_MACHINE_PRECONDITION_PLAN_2026-05-25.md` – V874 이후 CMD/REQ registration gate를 live write 전에 host-only로 분류하는 V875 계획
- `plans/NATIVE_INIT_V874_ESOC_CONTROL_PREFLIGHT_PLAN_2026-05-25.md` – helper `v136`으로 `/dev/esoc-0` read-only status ioctl preflight를 실행하는 V874 계획
- `plans/NATIVE_INIT_V873_HELPER_V136_DEPLOY_PLAN_2026-05-25.md` – helper `v136`을 deploy-only로 설치하고 checksum/version/mode parity를 증명하는 V873 계획
- `plans/NATIVE_INIT_V872_ESOC_PREFLIGHT_HELPER_V136_PLAN_2026-05-25.md` – helper `v135`의 eSoC preflight service-manager/SELinuxfs 오분류를 v136에서 분리하는 V872 계획
- `plans/NATIVE_INIT_V870_HELPER_V135_DEPLOY_PLAN_2026-05-25.md` – helper `v135`를 `/cache/bin/a90_android_execns_probe`에 deploy-only로 설치하고 checksum/version/mode parity를 증명하는 V870 계획
- `plans/NATIVE_INIT_V869_ESOC_CONTROL_PREFLIGHT_HELPER_PLAN_2026-05-25.md` – helper `v135`에 `/dev/esoc-0` eSoC control preflight mode를 source/build-only로 추가하는 V869 계획
- `plans/NATIVE_INIT_V868_PM_ESOC_CONTRACT_CLASSIFIER_PLAN_2026-05-25.md` – V867 `pm_proxy_helper` D-state를 로컬 A90 eSoC UAPI와 비교해 다음 gate를 `/dev/esoc-0` control preflight로 좁히는 V868 계획
- `plans/NATIVE_INIT_V829_SERVLOC_DOMAIN_LIST_PROBE_PLAN_2026-05-25.md` – V828에서 도출한 `GET_DOMAIN_LIST wlan/fw` request를 helper v126으로 bounded live QMI probe하고 응답 TLV를 파싱하는 계획
- `plans/NATIVE_INIT_V828_SERVLOC_DOMAIN_LIST_PAYLOAD_PLAN_2026-05-25.md` – V827 이후 service-locator `GET_DOMAIN_LIST wlan/fw` QMI request bytes를 host-only로 도출하는 계획
- `plans/NATIVE_INIT_V827_SERVICE_NOTIFIER_CONTINUATION_PLAN_2026-05-25.md` – V826 visible service-notifier 180 endpoint가 ICNSS continuation에 충분한지 OSRC source와 evidence로 분류하는 계획
- `plans/NATIVE_INIT_V826_QRTR_EVENT_DETAIL_CLASSIFIER_PLAN_2026-05-25.md` – V825 annotated evidence에서 QRTR NEW_SERVER event payload를 host-only로 추출하는 계획
- `plans/NATIVE_INIT_V825_QRTR_ENCODED_MATRIX_PLAN_2026-05-25.md` – V824가 산출한 encoded instance matrix를 helper v125 no-QMI live gate로 검증하는 계획
- `plans/NATIVE_INIT_V824_QRTR_ENCODED_INSTANCE_PLAN_2026-05-25.md` – V823 raw-instance matrix를 Samsung OSRC `qmi_interface.c`의 encoded QRTR instance 규칙과 비교하는 host-only 계획
- `plans/NATIVE_INIT_V823_SSCTL_NAMESERVICE_MATRIX_PLAN_2026-05-25.md` – V822가 특정한 sysmon SSCTL `43/16`을 helper v125 no-QMI nameservice matrix에 추가하는 live 계획
- `plans/NATIVE_INIT_V822_SYSMON_NAMESERVICE_GAP_PLAN_2026-05-25.md` – V821 clean-empty matrix와 OSRC source를 host-only로 비교해 sysmon SSCTL `43/16` 누락 여부를 분류하는 계획
- `plans/NATIVE_INIT_V821_QRTR_NAMESERVICE_MATRIX_PLAN_2026-05-25.md` – V820 결과에 따라 helper v125로 service-locator/service-notifier/WLFW 후보를 in-helper AF_QIPCRTR nameservice matrix로 확인하는 계획
- `plans/NATIVE_INIT_V820_QRTR_NAMESPACE_CLASSIFIER_PLAN_2026-05-25.md` – V819 helper/catalogue evidence를 host-only로 파싱해 QRTR procfs/debugfs 부재와 AF_QIPCRTR readback/service-publication 상태를 분류하는 계획
- `plans/NATIVE_INIT_V819_MDM3_ESOC_REGISTRATION_CATALOGUE_PLAN_2026-05-25.md` – V818이 선정한 mdm3/esoc0 service-locator/sysmon registration catalogue를 V817 lower window 안에서 read-only로 수집하는 계획
- `plans/NATIVE_INIT_V818_MDM3_ESOC_REGISTRATION_CLASSIFIER_PLAN_2026-05-25.md` – V817/V798/V795 증거를 host-only로 묶어 다음 blocker가 mdm3/esoc0 service-locator/sysmon registration인지 분류하는 계획
- `plans/NATIVE_INIT_V817_IN_WINDOW_SYSMON_SAMPLER_PLAN_2026-05-25.md` – V816 이후 기존 lower-trigger window 안에서 before-holder/after-holder/after-companion read-only subsystem/sysmon/service-locator surface를 샘플링하는 계획
- `plans/NATIVE_INIT_V816_IDLE_TRIGGER_DELTA_CLASSIFIER_PLAN_2026-05-25.md` – V815 idle snapshot과 V812 lower-trigger evidence를 host-only로 비교해 mss/sysmon만 전진하고 mdm3/service-publication이 막히는 delta인지 분류하는 계획
- `plans/NATIVE_INIT_V815_SUBSYSTEM_SYSMON_SNAPSHOT_PLAN_2026-05-25.md` – V814 이후 stock v724 idle 상태에서 msm_subsys/sysmon/service-locator/esoc/ICNSS/QRTR/dmesg surface를 read-only로 수집하는 계획
- `plans/NATIVE_INIT_V814_SIBLING_SYSMON_SOURCE_CLASSIFIER_PLAN_2026-05-25.md` – V813 이후 Samsung OSRC `service-notifier`/`sysmon`/`subsystem_restart` 소스 anchor로 다음 blocker가 subsystem/sysmon/service-publication registration surface인지 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V813_POST_SYSMON_PUBLICATION_CLASSIFIER_PLAN_2026-05-25.md` – V812/V811/V785/V783/V626/V739 증거만으로 memshare가 아닌 sibling sysmon/service-publication precondition이 다음 blocker인지 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V812_MDM3_WLANPD_SERVICE69_OBSERVER_PLAN_2026-05-25.md` – V811에서 선정한 mdm3/WLAN-PD/service69 publication blocker를 현재 stock v724에서 V401/V490 refresh와 lower companion/CNSS-only window로 제한 관측하는 계획
- `plans/NATIVE_INIT_V811_WLFW_PUBLICATION_PRECONDITION_CLASSIFIER_PLAN_2026-05-25.md` – V810 이후 Android/native mdm3/WLAN-PD delta와 V626/V731/V733/V735/V738/V808 증거를 묶어 WLFW/service69 publication 전제조건을 host-only로 선정하는 계획
- `plans/NATIVE_INIT_V810_REGISTER_PROBE_WLFW_FWREADY_CLASSIFIER_PLAN_2026-05-25.md` – V809 이후 PLD/SNOC/ICNSS register 자체가 아니라 WLFW/service69와 `FW_READY`가 QCACLD probe를 여는 gate인지 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V809_ICNSS_MODULES_NOT_INITIALIZED_SOURCE_CLASSIFIER_PLAN_2026-05-25.md` – V808 true-overlap 결과의 `icnss: Modules not initialized`/qcwlanstate `OFF`가 원인이 아니라 QCACLD `DRIVER_MODULES_ENABLED` 미도달 status mirror인지 host-only로 소스 매핑하는 계획
- `plans/NATIVE_INIT_V808_OVERLAP_COMPANION_BOOT_WLAN_PLAN_2026-05-25.md` – V807에서 선정한 provider-first companion과 `boot_wlan`의 true overlap live gate로 WLFW/service69 publication 여부를 검증하는 계획
- `plans/NATIVE_INIT_V807_PRE_WLFW_OVERLAP_CLASSIFIER_PLAN_2026-05-25.md` – V806 service69 absent 결과가 provider-first companion과 `boot_wlan`의 sequential cleanup/lifetime gap인지 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V806_WLFW_SERVICE69_LIVE_GATE_PLAN_2026-05-25.md` – V805에서 선정한 WLFW service `0x45/69` publication을 provider-first + `boot_wlan` live gate로 직접 관측하는 계획
- `plans/NATIVE_INIT_V805_ICNSS_FW_READY_WLFW_GATE_CLASSIFIER_PLAN_2026-05-25.md` – V804 이후 ICNSS `FW_READY`가 WLFW service `0x45/69` 도착에 의해 열리는지 source/evidence로 host-only 분류하는 계획
- `plans/NATIVE_INIT_V804_PLD_ICNSS_REGISTER_PROBE_PREREQ_CLASSIFIER_PLAN_2026-05-25.md` – V803 register/probe boundary를 OSRC source와 stock config로 재검증해 PLD register block인지 ICNSS FW_READY/probe gate인지 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V803_PROVIDER_FIRST_HDD_PLD_PREREQ_CLASSIFIER_PLAN_2026-05-25.md` – V802 evidence와 Samsung OSRC source order를 host-only로 비교해 HDD/PLD register/probe boundary를 선정하는 계획
- `plans/NATIVE_INIT_V802_PROVIDER_FIRST_BOOT_WLAN_OBSERVE_PLAN_2026-05-25.md` – V801에서 고른 provider-first context와 V752-style `boot_wlan` observe를 결합해 HDD/ICNSS-QMI/WLFW 경계를 분류하는 live 계획
- `plans/NATIVE_INIT_V801_V800_EDGE_ROUTE_CLASSIFIER_PLAN_2026-05-25.md` – V800 ICNSS edge와 V752 `boot_wlan` stall 증거를 비교해 다음 gate를 provider-first + `boot_wlan` observe로 선정하는 host-only 계획
- `plans/NATIVE_INIT_V800_PROVIDER_FIRST_ICNSS_EDGE_V124_REPLAY_PLAN_2026-05-25.md` – V799에서 고른 service74 양성 + PeripheralManager 확인 + provider-first CNSS tail 경로를 현재 v724/helper v124로 재검증하는 live 계획
- `plans/NATIVE_INIT_V799_POST_V798_ROUTE_CLASSIFIER_PLAN_2026-05-25.md` – V797/V798 lower-only 음성 경로와 V653/V657/V659/V668/V694 service74 양성 경로를 비교해 다음 live gate를 below-HAL CNSS tail replay로 선정하는 host-only 계획
- `plans/NATIVE_INIT_V798_PIL_CODE_GAP_CLASSIFIER_PLAN_2026-05-25.md` – V797 `pil_notif` code `2/3/6/7`를 Samsung OSRC enum에 매핑하고 Android/native service-notifier gap과 대조하는 host-only 계획
- `plans/NATIVE_INIT_V797_PIL_TRACE_PAYLOAD_PLAN_2026-05-25.md` – V796 이후 `msm_pil_event:pil_notif` tracefs payload를 lower-window transition 중 캡처해 PIL event name/code/fw sequence를 얻는 계획
- `plans/NATIVE_INIT_V796_POST_V795_ROUTE_CLASSIFIER_PLAN_2026-05-25.md` – V795 이후 CNSS/BPF/memshare/mdm_helper 증거를 재정렬해 다음 gate를 PIL payload capture로 선정하는 host-only 계획
- `plans/NATIVE_INIT_V795_LOWER_WINDOW_MDM3_ESOC_OBSERVER_PLAN_2026-05-25.md` – V794 idle surface 이후 firmware mounts + `subsys_modem` holder window 안에서 mdm3/esoc/ICNSS/WLFW를 관측하는 계획
- `plans/NATIVE_INIT_V794_MDM3_ICNSS_SURFACE_OBSERVER_PLAN_2026-05-25.md` – V793 이후 현재 idle native surface에서 mdm3/esoc, ICNSS, WLAN control, QRTR, dmesg를 read-only로 캡처하는 계획
- `plans/NATIVE_INIT_V793_CNSS_ICNSS_ROUTE_CLASSIFIER_PLAN_2026-05-25.md` – V792와 과거 CNSS/binder/ICNSS 증거를 비교해 다음 경로를 mdm3 + ICNSS/WLFW continuation으로 좁히는 host-only 계획
- `plans/NATIVE_INIT_V792_KNOWN_ASOC_WARNING_CNSS_WLFW_PLAN_2026-05-25.md` – V791 known ASoC warning 분류를 전제로 CNSS/WLFW readback을 warning-tolerant하게 재검증하는 계획
- `plans/NATIVE_INIT_V791_CURRENT_WARNING_ROUTE_CLASSIFIER_PLAN_2026-05-25.md` – V790/V788/V787 및 Android 증거를 비교해 current `pm_qos` warning이 WLFW route blocker인지 분류하는 host-only 계획
- `plans/NATIVE_INIT_V790_CLEAN_DSP_LOWER_ONLY_PLAN_2026-05-25.md` – V789 결과에 따라 CNSS를 빼고 clean-DSP + V401/V490 + lower-only companion으로 `pm_qos` warning 원인을 좁히는 계획
- `plans/NATIVE_INIT_V789_V788_WARNING_CLASSIFIER_PLAN_2026-05-25.md` – V788 `pm_qos_add_request` warning을 device action 없이 V733/V735/V787 증거와 비교해 다음 live gate를 더 좁게 선정하는 계획
- `plans/NATIVE_INIT_V788_CLEAN_DSP_LOWER_READBACK_PLAN_2026-05-25.md` – V787 clean-DSP proof after current boot prep with V401/V490 refresh, then CNSS-only lower companion readback while keeping HAL/scan/connect blocked
- `plans/NATIVE_INIT_V779_BPF_LOADER_BUILD_PLAN_2026-05-25.md` – V778 결과에 따라 `msm_pil_event:pil_notif` 전용 minimal static aarch64 BPF tracepoint helper를 build-only로 생성하고 deploy/attach 없이 정적 검증하는 계획
- `plans/NATIVE_INIT_V778_BPF_ATTACH_FEASIBILITY_PLAN_2026-05-25.md` – V777에서 선정한 `msm_pil_event:pil_notif` BPF attach proof 전에 device loader/sysctl과 host static helper build 가능성을 분류하는 계획
- `plans/NATIVE_INIT_V777_TRACEPOINT_FORMAT_CLASSIFIER_PLAN_2026-05-25.md` – V776 후보 tracepoint의 `format`/`id` 파일만 읽어 BPF attach proof 전에 event-specific field 의미를 분류하는 계획
- `plans/NATIVE_INIT_V776_TRACEPOINT_INVENTORY_PLAN_2026-05-25.md` – V775 이후 custom kernel flash 대신 recovered v724 stock kernel에서 tracefs `available_events`와 ICNSS/WLAN/QMI/QRTR 후보 tracepoint를 bounded mount/read/cleanup으로 분류하는 계획
- `plans/NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_PLAN_2026-05-25.md` – V774 이후 custom OSRC kernel flash를 중단하고 v724 stock kernel과 V773 diagnostic payload의 non-DTB 차이 및 tracepoint/BPF 관측 후보를 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V773_STOCK_DTB_TAIL_REPACK_PLAN_2026-05-25.md` – V772에서 확인한 DTB tail 누락을 local-only로 보정해 stock v724 appended DTB tail + V769 계측 payload를 repack하는 계획
- `plans/NATIVE_INIT_V772_BOOT_INCOMPAT_CLASSIFIER_PLAN_2026-05-25.md` – V771 boot failure를 live 재플래시 없이 stock/v724 payload와 V770 diagnostic payload의 header/config/FDT/marker 차이로 분류하는 계획
- `plans/NATIVE_INIT_V770_INSTRUMENTED_DIAGNOSTIC_BOOT_STAGING_PLAN_2026-05-25.md` – V769 `Image-dtb`를 현재 native-init ramdisk/header와 local-only로 repack하고 roundtrip hash/marker를 검증하는 계획
- `plans/NATIVE_INIT_V769_RKP_CFP_PYTHON3_PACKAGING_PLAN_2026-05-25.md` – V767 post-link `RKP_CFP` Python2 blocker를 disposable tree 안에서 Python3 호환 수리해 instrumented `Image` 생성까지 확인하는 계획
- `plans/NATIVE_INIT_V768_MDM3_ESOC_GAP_CLASSIFIER_PLAN_2026-05-25.md` – V620/V622/V740/V764/V767 증거를 묶어 `mdm_helper`/esoc 직접 retry를 닫고 다음 gate를 RKP_CFP/package 쪽으로 라우팅하는 host-only 계획
- `plans/NATIVE_INIT_V767_ICNSS_QCACLD_FULL_BUILD_PLAN_2026-05-25.md` – V766 적용済み `A90V765` source tree를 ignored toolchain으로 bounded full build해 계측 객체 컴파일과 final image blocker를 분류하는 계획
- `plans/NATIVE_INIT_V766_ICNSS_QCACLD_PATCH_APPLY_BUILD_PLAN_2026-05-25.md` – V765 `A90V765` patch를 disposable OSRC source tree에 적용하고 bounded defconfig/build-readiness를 확인하는 계획
- `plans/NATIVE_INIT_V765_ICNSS_QCACLD_LOG_PATCH_PLAN_2026-05-24.md` – V764 이후 ICNSS/QCACLD SNOC 경로에 `A90V765` 로그 패치를 review-only로 생성하는 계획
- `plans/NATIVE_INIT_V764_SERVICE180_MDM_HELPER_RETRY_PLAN_2026-05-24.md` – V763 계측 진행 전 service-notifier `180` gated `mdm_helper` retry와 mdm/esoc 표면 확인을 우선 수행하는 계획
- `plans/NATIVE_INIT_V763_ICNSS_ARCH_REBASE_PLAN_2026-05-24.md` – SM-A908N live 경로를 CNSS2/MHI가 아닌 ICNSS/QCACLD SNOC로 재분류하는 계획
- `plans/NATIVE_INIT_V762_SOURCE_TARGET_VERIFICATION_PLAN_2026-05-24.md` – staged Samsung OSRC archive가 ICNSS/QCACLD target source를 포함하는지 검증하는 계획
- `plans/NATIVE_INIT_V761_SOURCE_DOWNLOAD_HANDOFF_PLAN_2026-05-24.md` – Samsung OSRC 수동 다운로드와 ignored staging handoff를 준비하는 계획
- `plans/NATIVE_INIT_V760_SOURCE_STAGING_PLAN_2026-05-24.md` – local `kernel_build/` staging에서 source archive/tree target availability를 검증하는 계획
- `plans/NATIVE_INIT_V759_SOURCE_ACQUISITION_PLAN_2026-05-24.md` – SM-A908N/A908NKSU5EWA3 kernel source acquisition target을 공식 OSRC 기준으로 특정하는 계획
- `plans/NATIVE_INIT_V758_KERNEL_INSTRUMENTATION_FEASIBILITY_PLAN_2026-05-24.md` – rollback-safe kernel/source/boot-image instrumentation 가능 여부를 source 확보 전 분류하는 계획
- `plans/NATIVE_INIT_V757_ANDROID_NATIVE_HDD_PLD_DIFF_PLAN_2026-05-24.md` – Android/native HDD/PLD dmesg 차이와 boot-image log instrumentation 후보를 분류하는 계획
- `plans/NATIVE_INIT_V756_NONFTRACE_HDD_PLD_OBSERVABILITY_PLAN_2026-05-24.md` – ftrace 실패 이후 non-ftrace HDD/PLD 관측성 후보를 분류하는 계획
- `plans/NATIVE_INIT_V755_TRACEFS_MOUNT_FILTER_PROOF_PLAN_2026-05-24.md` – V754 이후 tracefs를 bounded mount/read/cleanup으로 검증하고 HDD/PLD target filter function 노출 여부를 확인하는 계획
- `plans/NATIVE_INIT_V754_HDD_PLD_TRACEABILITY_SELECTOR_PLAN_2026-05-24.md` – V753 이후 HDD/PLD/register-driver 관측성을 ftrace/tracefs/kallsyms로 확보 가능한지 read-only로 분류하는 계획
- `plans/NATIVE_INIT_V753_HDD_PLD_PREREQ_CLASSIFIER_PLAN_2026-05-24.md` – V752 이후 HDD/PLD/register-driver 경계에 명시적 실패 마커가 있는지 read-only로 분류하는 계획
- `plans/NATIVE_INIT_V752_CNSS_THEN_BOOT_WLAN_PLAN_2026-05-24.md` – V751 후보인 CNSS companion start-only 후 bounded `boot_wlan` observe ordering을 service-manager/HAL/connect 없이 검증하는 계획
- `plans/NATIVE_INIT_V751_ICNSS_MODULE_INIT_CLASSIFIER_PLAN_2026-05-24.md` – V750의 lower-window `boot_wlan` 결과를 QCACLD/HDD init 경계에서 read-only로 분류하는 계획
- `plans/NATIVE_INIT_V750_LOWER_WINDOW_BOOT_WLAN_PLAN_2026-05-24.md` – V749가 선정한 lower-window `boot_wlan` proof를 firmware mount, `subsys_modem` holder, lower companion stack 안에서만 bounded 실행하는 계획
- `plans/NATIVE_INIT_V749_NONBIND_TRIGGER_SELECTOR_PLAN_2026-05-24.md` – V748 이후 `fs_ready`, `boot_wlan`, `qcwlanstate` 후보를 read-only로 분류하고 lower-window `boot_wlan` proof를 V750 후보로 선정하는 계획
- `plans/NATIVE_INIT_V748_NONBIND_POWERUP_TRIGGER_PLAN_2026-05-24.md` – V746/V747 이후 남은 후보를 host-only로 정리해 bind/unbind, `mdm_helper`, CNSS/HAL retry, vendor namespace, `wlan` module load를 분류하고 다음 gate를 non-bind ICNSS/QCA WLFW trigger capture로 좁히는 계획
- `plans/NATIVE_INIT_V747_QCA6390_DRIVER_BINDING_DELTA_PLAN_2026-05-24.md` – V746/V717 증거를 묶어 QCA6390 platform child driver link 부재와 MHI device 미생성을 Android/native read-only로 분류하는 다음 계획
- `plans/NATIVE_INIT_V746_SYSMON_GATED_MDM_HELPER_PLAN_2026-05-24.md` – V745에서 service `180` gate가 닫힌 반면 `sysmon-qmi`는 재현된 결과를 반영해 helper v124로 `mdm_helper`를 sysmon 뒤에서만 시작하는 계획
- `plans/NATIVE_INIT_V745_SERVICE180_GATED_MDM_HELPER_PLAN_2026-05-24.md` – V744에서 재현된 service-notifier `180`을 gate로 삼아 `mdm_helper`를 같은 bounded window에서 늦게 시작하는 helper v123/V745 계획
- `plans/NATIVE_INIT_V744_V122_CNSS_ONLY_COMPARISON_PLAN_2026-05-24.md` – V743 service-`74` gate miss가 helper v122 자체 문제인지 분리하기 위해 V735 CNSS-only 경로를 helper v122로 재실행하는 비교 계획
- `plans/NATIVE_INIT_V743_V741_CURRENT_LIVE_EXECUTION_PLAN_2026-05-24.md` – V742 helper v122 배포 후 현재 부팅에서 V741 service-`74` gated `mdm_helper` proof를 제한 실행하는 계획
- `plans/NATIVE_INIT_V742_EXECNS_HELPER_V122_DEPLOY_PLAN_2026-05-24.md` – helper v122를 `/cache/bin/a90_android_execns_probe`로 배포하기 위한 V742 wrapper 계획과 busy read-only preflight blocker 기준
- `plans/NATIVE_INIT_V741_MDM_HELPER_GATED_LIVE_PLAN_2026-05-24.md` – V740이 선정한 post-notifier `mdm_helper` 후보를 service `74` gate 뒤 bounded start-only proof로 검증하기 위한 helper v122/V741 계획
- `plans/NATIVE_INIT_V740_MDM_HELPER_BASEBAND_CONTRACT_PLAN_2026-05-24.md` – V621/V622 `mdm_helper`/`ro.baseband` 계약을 V739 `mdm3=OFFLINING` blocker와 재조합해 blind start 금지와 post-notifier gated proof를 고정하는 V740 계획
- `plans/NATIVE_INIT_V739_MDM3_WLANPD_DELTA_PLAN_2026-05-24.md` – Android `mss/mdm3=ONLINE` + WLAN-PD/WLFW/BDF/`wlan0`와 native V738 `mss=ONLINE, mdm3=OFFLINING`을 host-only로 비교해 다음 gate를 `mdm_helper`/baseband contract 분류로 고정하는 V739 계획
- `plans/NATIVE_INIT_V738_MODEM_WLAN_MHI_OBSERVER_PLAN_2026-05-24.md` – V737이 선정한 real vendor firmware namespace + `subsys_modem` holder + lower/CNSS-only window로 `mss/mdm3`, QCA/MHI/WLFW/service `69`, BDF, `wlan0`를 관측하는 V738 계획
- `plans/NATIVE_INIT_V737_CNSS2_ARCH_REBASE_PLAN_2026-05-24.md` – V736의 service-`74` 중심 next step을 V726/V727 SM8250 CNSS2/PCIe 모델로 재분류해 다음 gate를 modem+WLAN/MHI prerequisite observer로 라우팅하는 V737 host-only 계획
- `plans/NATIVE_INIT_V736_SERVICE180_TO_MHI_GAP_PLAN_2026-05-24.md` – V735 service-notifier `180` 양성 상태를 Android V622 및 V627과 비교해 service `74`/WLAN-PD/MHI/WLFW/`wlan0` 미진입을 host-only로 분류하는 V736 계획
- `plans/NATIVE_INIT_V735_CURRENT_CNSS_ONLY_OBSERVER_PLAN_2026-05-24.md` – V734가 선정한 current-build CNSS-only gate를 실행해 lower companion + `cnss_diag`/`cnss-daemon`까지만 시작하고 service publication, MHI/QCA6390, WLFW/service `69`, BDF, `wlan0`를 관측하는 V735 계획
- `plans/NATIVE_INIT_V734_CURRENT_POST_SYSMON_ROUTE_PLAN_2026-05-24.md` – current V733 post-sysmon 결과를 Android V622 및 V625/V627 safe positive와 비교해 다음 live gate를 current-build CNSS-only replay로 라우팅하는 V734 host-only 계획
- `plans/NATIVE_INIT_V733_HOLDER_LOWER_COMPANION_PLAN_2026-05-24.md` – V732의 firmware-mounted `subsys_modem` holder window에 lower companion/TFTP 4개(`qrtr_ns,rmt_storage,tftp_server,pd_mapper`)만 추가해 QRTR TX/sysmon/WLFW/service `69` 진행 여부를 검증하는 V733 계획
- `plans/NATIVE_INIT_V732_CNSS2_MHI_HOLDER_WINDOW_PLAN_2026-05-24.md` – SM8250 CNSS2/PCIe 모델로 재정렬해 V731 firmware-mounted `subsys_modem` holder window 안에서 `wlan` load semantics, CNSS/MHI/QCA6390/WLFW/service `69`, global WLAN firmware visibility를 read-only로 분류하는 V732 계획
- `plans/NATIVE_INIT_V731_FIRMWARE_MOUNTED_MODEM_HOLDER_PLAN_2026-05-24.md` – V730이 재고정한 current-build firmware mount prerequisite을 실제로 적용해 `/vendor/firmware_mnt`/`/vendor/firmware-modem` read-only mount + `subsys_modem` holder로 `mss`/QRTR RX 복원을 검증하는 V731 계획
- `plans/NATIVE_INIT_V730_MODEM_TRIGGER_RECONCILE_PLAN_2026-05-24.md` – V729 open-pending 결과를 V592 no-firmware class 및 V594/V595/V596 firmware-mounted modem readiness와 대조해, 다음 gate를 `mdm_helper`가 아니라 global firmware mount + `subsys_modem` holder로 재고정하는 V730 계획
- `plans/NATIVE_INIT_V729_MODEM_ONLY_HOLD_PLAN_2026-05-24.md` – V728이 증명한 private real vendor root 이후, `esoc0` 없이 임시 `subsys_modem` cdev만 bounded open해 modem ONLINE/QRTR/sysmon/MHI/WLFW 진행 여부를 분류하는 V729 계획
- `plans/NATIVE_INIT_V728_PRIVATE_VENDOR_ROOT_PLAN_2026-05-24.md` – V727이 확인한 real `sda29` vendor firmware를 기존 exec namespace helper의 private `/vendor` layout과 상관시켜, modem ONLINE 전에 helper namespace vendor root가 맞는지 증명하는 V728 계획
- `plans/NATIVE_INIT_V727_LOWER_PREREQ_PLAN_2026-05-24.md` – V726의 SM8250 CNSS2/PCIe 재해석 이후 current `/vendor`와 isolated `sda29` vendor firmware visibility, `/sys/module/wlan` static surface, modem/MHI/WLFW 상태를 read-only로 분류하는 V727 계획
- `plans/NATIVE_INIT_V726_CNSS2_PCIE_PREREQ_PLAN_2026-05-24.md` – SM8250 CNSS2/PCIe 경로로 모델을 재정렬해 modem MPSS/MDM3 ONLINE, `/proc/modules`의 `wlan`, MHI/QCA6390, `wlanmdsp` firmware 전제조건을 read-only로 분류하는 V726 계획
- `plans/NATIVE_INIT_V725_SERVLOC_MODEM_QMI_GAP_PLAN_2026-05-24.md` – V724가 service-locator timeout은 제거했지만 QRTR RX/TX, sysmon, `mss/mdm3` ONLINE, service `180/74`가 모두 없어 blocker를 modem/QMI readiness gap으로 분류하는 V725 host-only 계획
- `plans/NATIVE_INIT_V724_QRTR_SERVICE_LOCATOR_BOOT_PROOF_PLAN_2026-05-24.md` – V723 late rearm 한계를 반영해 post-ACM boot window에서 lower-only `qrtr-ns`/`pd-mapper`/`rmt_storage`/`tftp_server`를 one-shot으로 시작하는 V724 계획
- `plans/NATIVE_INIT_V723_QRTR_SERVICE_LOCATOR_REARM_PLAN_2026-05-24.md` – boot-time `servloc` timeout 이후 lower-only `qrtr-ns`/service-locator 재연결이 WLAN-PD service `180/74`까지 복구하는지 분류하는 계획
- `plans/NATIVE_INIT_V722_CNSS_LAUNCH_WINDOW_PLAN_2026-05-24.md` – Android V622, native V659/V660, V720을 비교해 early CNSS binder failure와 provider-first late CNSS launch 사이 tradeoff를 분류하는 계획
- `plans/NATIVE_INIT_V721_SERVREG_CNSS2_DELTA_PLAN_2026-05-24.md` – Android V622와 native V720을 host-only로 비교해 service `180/74` 이후 SERVREG/WLAN-PD/CNSS2 callback 경계가 다음 blocker인지 분류하는 계획
- `plans/NATIVE_INIT_V720_SAME_WINDOW_CNSS2_OBSERVER_PLAN_2026-05-24.md` – V712 service-positive window, V706 current read-only capture, and V719 reconciliation을 한 번에 묶어 `qrtr-ns`/SERVREG/CNSS2 trigger gap을 같은 창에서 확인하는 계획
- `plans/NATIVE_INIT_V719_CNSS2_SERVICE_POSITIVE_RECONCILE_PLAN_2026-05-24.md` – V717 service `180/74` 양성 창과 V718 current-boot lower-not-ready 상태를 분리해, 다음 gate를 same-window CNSS2 notifier/SERVREG 관측으로 고정하는 host-only 계획
- `plans/NATIVE_INIT_V718_CNSS2_PD_NOTIFIER_CURRENT_HARDENING_PLAN_2026-05-24.md` – V666/V706 read-only CNSS2 pd-notifier check를 current boot에서 안전하게 재사용하도록 busy-capture 차단과 QCA power/MHI 마커 정밀화를 추가하는 계획
- `plans/NATIVE_INIT_V717_ICNSS_EDGE_LONG_OBSERVE_PLAN_2026-05-24.md` – V712 helper v121 provider-first ICNSS edge proof를 30초 observation window로 재실행해 WLFW/BDF/`wlan0` 미진입이 짧은 대기시간 문제가 아님을 검증하는 계획
- `plans/NATIVE_INIT_V716_QCA_BIND_RECONCILIATION_PLAN_2026-05-24.md` – V715의 QCA6390 child-unbound 결과를 V703 Android reference와 대조해 QCA bind/unbind가 아니라 ICNSS-QMI/WLFW readiness edge가 다음 target임을 고정하는 host-only 계획
- `plans/NATIVE_INIT_V715_ICNSS_EDGE_SURFACE_CLASSIFIER_PLAN_2026-05-24.md` – V712 helper v121 ICNSS edge capture를 host-only로 분류해 ICNSS parent/QCA6390 child/WLFW·BDF·`wlan0` 중 어느 경계에서 멈췄는지 라벨링하는 계획
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
- `plans/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_PLAN_2026-05-25.md` – helper `v134`의 PeripheralManager init-contract mode를 bounded live로 검증하고 cleanup blocker를 분류하는 V867 계획
- `plans/NATIVE_INIT_V866_HELPER_V134_DEPLOY_PLAN_2026-05-25.md` – helper `v134`를 `/cache/bin/a90_android_execns_probe`에 deploy-only로 배포하고 checksum/version parity를 증명하는 V866 계획
- `plans/NATIVE_INIT_V865_PM_INIT_CONTRACT_HELPER_PLAN_2026-05-25.md` – V864가 요구한 PeripheralManager init contract 모델을 helper `v134`에 source/build-only로 추가하는 V865 계획
- `plans/NATIVE_INIT_V864_PM_INIT_CONTRACT_SUPPORT_PLAN_2026-05-25.md` – V861/V862/V863 증거와 helper source를 비교해 PeripheralManager init contract 지원 여부를 host-only로 분류하는 V864 계획
- `plans/NATIVE_INIT_V863_PM_PROXY_HELPER_RC_CAPTURE_PLAN_2026-05-25.md` – V862가 지목한 `pm_proxy_helper.rc`를 live vendor partition에서 read-only로 캡처/분류하는 V863 계획
- `plans/NATIVE_INIT_V862_ANDROID_INIT_SERVICE_CONTRACT_PLAN_2026-05-25.md` – V861 이후 Android init-managed PeripheralManager 서비스 계약을 host-only로 분류하는 V862 계획
- `plans/NATIVE_INIT_V861_PM_SERVICE_DOMAIN_PARITY_PLAN_2026-05-25.md` – V860 이후 `pm-service`/`pm-proxy`에 Android `vendor_per_mgr` exec context를 추가해 subsystem fd hold 여부를 재검증하는 V861 계획
- `plans/NATIVE_INIT_V860_PM_SERVICE_PROPERTY_SUPERSET_PLAN_2026-05-25.md` – V858/V859/V677 property key를 하나의 private property superset으로 묶고 `pm-service`/`pm-proxy` start-only를 재검증하는 V860 계획
- `plans/NATIVE_INIT_V859_PM_SERVICE_PROPERTY_DELTA_REPLAY_PLAN_2026-05-25.md` – V858 property delta 적용 후 helper 재배포 없이 `pm-service`/`pm-proxy` start-only를 재실행해 기존 denial 제거 여부와 새 property gap을 분류하는 V859 계획
- `plans/NATIVE_INIT_V858_PM_SERVICE_PROPERTY_CONTEXT_DELTA_PLAN_2026-05-25.md` – V857에서 드러난 `pm-service`/`pm-proxy` property-context gap 8개를 private property root delta로 매핑/배포하는 V858 계획
- `plans/NATIVE_INIT_V104_WIFI_FEASIBILITY_PLAN_2026-05-04.md` – v104 Wi-Fi enablement feasibility gate 실행 계획
- `plans/NATIVE_INIT_V712_EXECNS_HELPER_V121_ICNSS_EDGE_PLAN_2026-05-24.md` – V711이 고정한 ICNSS-QMI/WLFW readiness edge를 service `180/74` provider window 안에서 캡처하기 위한 helper v121 관측성 추가 계획
- `plans/NATIVE_INIT_V711_ICNSS_EDGE_READONLY_PLAN_2026-05-24.md` – V710의 QCA6390/WLFW event-source 결과를 현재 ICNSS 모델로 재정렬해 다음 target을 qca bind 쓰기가 아닌 ICNSS-QMI/WLFW readiness edge로 고정하는 read-only 계획
- `plans/NATIVE_INIT_V710_KERNEL_EVENT_SOURCE_CLASSIFIER_PLAN_2026-05-24.md` – V708/V709 provider-first CNSS stall과 Android 기준 증거를 대조해 service `180/74` 이후 QCA6390/ICNSS/WLFW event source gap을 host-only로 분류하는 계획
- `plans/NATIVE_INIT_V708_PROVIDER_FIRST_CNSS_V120_STALL_PLAN_2026-05-24.md` – helper v120으로 provider-first CNSS retry를 재실행해 `cnss_daemon_retry` live stall snapshot을 수집하는 계획
- `plans/NATIVE_INIT_V706_CNSS2_PD_NOTIFIER_READONLY_PLAN_2026-05-24.md` – service-notifier `180` 이후 kernel `icnss`/CNSS pd-notifier 및 QCA6390 power/WLFW 진행 여부를 현재 부팅에서 read-only로 분류하는 계획
- `plans/NATIVE_INIT_V705_EXECNS_HELPER_V120_STALL_CAPTURE_PLAN_2026-05-24.md` – provider-first `cnss-daemon` retry의 live stall point를 잡기 위한 helper v120 read-only proc/socket 관측성 추가 계획
- `plans/NATIVE_INIT_V704_CNSS_RETRY_STALL_SNAPSHOT_PLAN_2026-05-24.md` – V700 provider-first `cnss-daemon` retry가 crash/Binder 실패가 아니라 alive pre-WLFW stall인지 기존 proc/fd snapshot으로 분류하는 V704 host-only 계획
- `plans/NATIVE_INIT_V703_ANDROID_NATIVE_BINDING_COMPARE_PLAN_2026-05-24.md` – Android baseline과 V702 native focus를 비교해 다음 target이 `qca6390` bind가 아니라 ICNSS/WLFW readiness edge인지 분류하는 V703 host-only 계획
- `plans/NATIVE_INIT_V702_CNSS2_FOCUS_SURFACE_CLASSIFIER_PLAN_2026-05-24.md` – V700 provider-first retry window의 cnss2/icnss/QCA focus capture를 구조화해 `qca6390` binding gap을 분류하는 V702 host-only 계획
- `plans/NATIVE_INIT_V701_PRE_WLFW_TRIGGER_CLASSIFIER_PLAN_2026-05-24.md` – V700 이후 남은 WLFW 전 정지를 Binder가 아닌 cnss2/icnss/QCA kernel progression gap으로 분류하는 V701 host-only 계획
- `plans/NATIVE_INIT_V700_PROVIDER_FIRST_CNSS_LIVE_PLAN_2026-05-24.md` – V699 helper v119를 배포하고 provider-first initial-suppressed CNSS retry를 bounded live로 검증하는 V700 계획
- `plans/NATIVE_INIT_V699_PROVIDER_FIRST_CNSS_HELPER_PLAN_2026-05-24.md` – V698에서 분리한 초기 pre-provider CNSS 실패를 제거하기 위해 provider-first initial-suppressed CNSS helper v119 모드를 추가하는 V699 계획
- `plans/NATIVE_INIT_V698_CNSS_RETRY_ATTRIBUTION_PLAN_2026-05-24.md` – V695의 Binder `29189/-22`가 post-provider retry가 아니라 초기 pre-provider `cnss-daemon`에 귀속되는지 pid/order/dmesg로 분리하는 V698 host-only 계획
- `plans/NATIVE_INIT_V697_CNSS_BINDER_RUNTIME_TARGET_PLAN_2026-05-24.md` – V666/V667/V681 causal-chain 확인 이후 V684/V695/V696 증거를 합쳐 남은 블로커를 `cnss-daemon`/`libperipheral_client` vendor Binder transaction framing으로 좁히는 V697 host-only 계획
- `plans/NATIVE_INIT_V696_POST_PROVIDER_RETRY_BLOCKER_CLASSIFIER_PLAN_2026-05-24.md` – V695 이후 WLFW 전 정지의 1차 원인이 CNSS Binder `-22`인지 duplicate `pm_qos`인지 Android/V695 dmesg 타이밍으로 분류하는 V696 host-only 계획
- `plans/NATIVE_INIT_V695_PROVIDER_CONFIRMED_CNSS_RETRY_PLAN_2026-05-24.md` – V694로 확인한 `vendor.qcom.PeripheralManager` 등록 뒤 같은 private namespace에서 fresh `cnss-daemon` retry tail을 실행하는 V695 계획
- `plans/NATIVE_INIT_V694_PERIPHERAL_VNDSERVICE_QUERY_PLAN_2026-05-24.md` – V692/V693 registry observability gap 뒤 `vendor.qcom.PeripheralManager`가 실제 `vndservicemanager`에 등록되는지 helper v117 `/vendor/bin/vndservice list`로 확인하는 V694 계획
- `plans/NATIVE_INIT_V693_PERIPHERAL_REGISTRY_EVIDENCE_CLASSIFIER_PLAN_2026-05-24.md` – V692 registry snapshot이 provider 등록을 증명하는지 아니면 Binder 관측성 gap인지 host-only로 분류하는 V693 계획
- `plans/NATIVE_INIT_V692_PERIPHERAL_REGISTRY_SNAPSHOT_PLAN_2026-05-24.md` – V691 post-property provider exit 이후 `pm-service`/`pm-proxy` start 주변 vndservicemanager/binder registry snapshot을 helper v116으로 캡처하는 V692 계획
- `plans/NATIVE_INIT_V691_PERIPHERAL_POST_PROPERTY_EXIT_CLASSIFIER_PLAN_2026-05-24.md` – V690 property ack 이후에도 provider가 남지 않는 post-property exit gap을 host-only로 분류하는 V691 계획
- `plans/NATIVE_INIT_V690_PERIPHERAL_PROPERTY_SHIM_ACK_PLAN_2026-05-24.md` – V689에서 좁힌 exact private property shim ack 두 개를 helper v115로 구현하고 bounded provider/CNSS retry를 검증하는 V690 계획
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

- `reports/NATIVE_INIT_V1005_V1004_FD_GAP_CLASSIFIER_2026-05-26.md` – V1000 Android lower timing, V911 native `mdm_helper` fd positive, V1004 service-window fd-gate miss를 host-only로 비교해 helper `v171` fd-poll support를 다음으로 선택한 V1005 결과
- `reports/NATIVE_INIT_V1006_SERVICE_WINDOW_FD_POLL_SUPPORT_2026-05-26.md` – helper `v171`에 Android service-window `mdm_helper` `/dev/esoc-0` repeated fd-poll markers와 Android-like mdm-helper→cnss timing support를 source/build-only로 추가한 V1006 결과
- `reports/NATIVE_INIT_V1007_HELPER_V171_DEPLOY_2026-05-26.md` – helper `v171`을 `/cache/bin/a90_android_execns_probe`로 deploy-only 설치하고 remote sha/contract parity 및 no-Wi-Fi guard를 확인한 V1007 결과
- `reports/NATIVE_INIT_V1008_SERVICE_WINDOW_FD_POLL_LIVE_2026-05-26.md` – helper `v171` live 결과 current-boot SELinux refresh와 service-window actors는 통과했지만 fd-poll 전 구간에서 `mdm_helper` `/dev/esoc-0`가 0이라 trigger를 미실행한 V1008 결과
- `reports/NATIVE_INIT_V1009_V911_V1008_CONTRACT_COMPARATOR_2026-05-26.md` – V911 reduced path의 `/dev/esoc-0` fd-positive와 V1008 service-window fd-negative를 비교해 다음을 service-defaults reduced `mdm_helper` isolation gate로 선택한 V1009 결과
- `reports/NATIVE_INIT_V1010_MDM_HELPER_RUNTIME_SERVICE_DEFAULTS_2026-05-26.md` – helper `v171` reduced runtime-contract를 service-defaults SELinux로 실행해 `mdm_helper`가 `u:r:vendor_mdm_helper:s0`에서도 `/dev/esoc-0`를 여는 것을 확인한 V1010 결과
- `reports/NATIVE_INIT_V1011_V1008_V1010_ACTOR_DELTA_2026-05-26.md` – V1008 full service-window가 fd predicate를 잃고 V1010 reduced route가 유지함을 비교해 V1012 after-fd CNSS/service-manager matrix를 선택한 결과
- `reports/NATIVE_INIT_V1012_AFTER_FD_CNSS_MATRIX_2026-05-26.md` – V1012 after-fd matrix live 결과 `mdm_helper` fd, service-manager, CNSS는 성립했지만 WLFW precondition은 0으로 남아 `/dev/subsys_esoc0` open 없이 cleanup reboot로 복구한 결과
- `reports/NATIVE_INIT_V1013_V1012_WLFW_GAP_CLASSIFIER_2026-05-26.md` – V1012의 fd-positive/CNSS/no-WLFW와 V1008의 upper-surface/fd-missing split을 비교해 V1014 after-fd Wi-Fi surface helper support를 선택한 결과
- `reports/NATIVE_INIT_V1014_AFTER_FD_WIFI_SURFACE_MATRIX_SUPPORT_2026-05-26.md` – helper `v172`에 fd predicate 이후 Wi-Fi HAL legacy/ext와 `wificond`를 추가하고 CNSS를 그 뒤로 gate하는 source/build-only 결과
- `reports/NATIVE_INIT_V1015_HELPER_V172_DEPLOY_2026-05-26.md` – helper `v172` deploy-only 결과 remote sha/usage contract가 일치하고 daemon/Wi-Fi bring-up 없이 V1016 live gate 준비가 완료된 결과
- `reports/NATIVE_INIT_V1016_AFTER_FD_WIFI_SURFACE_MATRIX_LIVE_2026-05-26.md` – V1016 live 결과 `mdm_helper` fd 이후 service-manager/Wi-Fi HAL/`wificond`/CNSS는 시작됐지만 WLFW precondition은 빠져 `/dev/subsys_esoc0` open 없이 lower gap으로 분류한 결과
- `reports/NATIVE_INIT_V1017_V1016_ANDROID_LOWER_GAP_CLASSIFIER_2026-05-26.md` – V1017 host-only 결과 WLFW-precondition-gated `/dev/subsys_esoc0`가 순환 gate일 가능성이 높아 V1018 helper `v173` scoped subsystem-window support를 선택한 결과
- `reports/NATIVE_INIT_V1018_AFTER_FD_SUBSYS_WINDOW_SUPPORT_2026-05-26.md` – V1018 source/build 결과 helper `v173`에 fd-positive upper-surface 뒤 `post-upper-surface-no-wlfw` scoped `/dev/subsys_esoc0` window support를 추가한 결과
- `reports/NATIVE_INIT_V1019_HELPER_V173_DEPLOY_2026-05-26.md` – V1019 deploy-only 결과 helper `v173` remote sha/order/gate parity가 일치하고 daemon/Wi-Fi bring-up 없이 V1020 live gate 준비가 완료된 결과
- `reports/NATIVE_INIT_V1020_AFTER_FD_SUBSYS_WINDOW_LIVE_2026-05-26.md` – V1020 live 결과 fd-positive upper-surface 뒤 `/dev/subsys_esoc0` open은 실제 시도됐지만 `sdx50m_toggle_soft_reset` D-state로 막혀 cleanup reboot 후 V1021 Android/native reset-handshake classifier가 필요해진 결과
- `reports/NATIVE_INIT_V1021_V1020_ANDROID_RESET_HANDSHAKE_CLASSIFIER_2026-05-26.md` – V1021 host-only 결과 V1020 stall을 lower reset-handshake blocker로 분류하고 blind native retry 대신 Android PM/eSoC read-only timing recapture를 V1022로 선택한 결과
- `reports/NATIVE_INIT_V1022_ANDROID_PM_ESOC_TIMING_SAMPLER_2026-05-26.md` – V1022 source/plan 결과 Android 정상 부팅 직후 ADB read-only PM/eSoC/GPIO/IRQ/WLFW timing sampler가 준비된 결과
- `reports/NATIVE_INIT_V1023_ANDROID_PM_ESOC_TIMING_HANDOFF_2026-05-26.md` – V1023 live 결과 Android handoff에서 V1022 late sampler가 WLFW/FW-ready/`wlan0` 타이밍을 캡처하고 native v724 rollback까지 검증한 결과
- `reports/NATIVE_INIT_V1024_FAST_FD_CONTRACT_CLASSIFIER_2026-05-26.md` – V1024 결과 Android early fd contract(`pm_proxy_helper`/`pm-service` `/dev/subsys_modem`, `mdm_helper` `/dev/esoc-0`)와 late WLFW chain을 같은 handoff에서 확보한 결과
- `reports/NATIVE_INIT_V1025_PM_FULL_CONTRACT_SUPPORT_2026-05-26.md` – V1025 source/build 결과 helper `v174`에 `pm_proxy_helper`/`pm-service` `/dev/subsys_modem` fd gate를 추가한 결과
- `reports/NATIVE_INIT_V1026_HELPER_V174_DEPLOY_2026-05-26.md` – V1026 deploy-only 결과 helper `v174` remote sha/order parity가 일치하고 daemon/Wi-Fi bring-up 없이 V1027 live gate 준비가 완료된 결과
- `reports/NATIVE_INIT_V1027_PM_FULL_CONTRACT_LIVE_2026-05-26.md` – V1027 live 결과 `pm_proxy_helper`는 시작됐지만 `/dev/subsys_modem` fd predicate가 성립하지 않아 post-provider retry 전 PM blocker로 분류한 결과
- `reports/NATIVE_INIT_V1028_PM_PROXY_HELPER_MODEM_GET_CLASSIFIER_2026-05-26.md` – V1028 host-only 결과 native `pm_proxy_helper`가 modem subsystem-get/PIL-loading 경로에서 fd predicate 전 block됨을 Android V1024와 비교 분류한 결과
- `reports/NATIVE_INIT_V1004_SERVICE_WINDOW_SUBSYS_TRIGGER_LIVE_2026-05-26.md` – V1004 live 결과 current-boot SELinux refresh 후 Android service-window actors는 관측됐지만 `mdm_helper`가 `/dev/esoc-0` fd를 hold하지 않아 `/dev/subsys_esoc0` trigger는 안전하게 미실행된 결과
- `reports/NATIVE_INIT_V1003_HELPER_V170_DEPLOY_2026-05-26.md` – helper `v170`을 `/cache/bin/a90_android_execns_probe`로 deploy-only 설치하고 remote sha/contract parity 및 no-Wi-Fi guard를 확인한 V1003 결과
- `reports/NATIVE_INIT_V1002_ANDROID_SERVICE_WINDOW_SUBSYS_TRIGGER_SUPPORT_2026-05-26.md` – helper `v170`에 Android service-window scoped `/dev/subsys_esoc0` trigger capture mode를 source/build-only로 추가한 V1002 결과
- `reports/NATIVE_INIT_V1001_V1000_ROUTE_COMPARATOR_2026-05-26.md` – V1000에서 `/dev/subsys_esoc0` get이 `wlfw_start`보다 앞섰음을 반영해 V1002 service-window-scoped subsystem trigger helper support를 선택한 V1001 결과
- `reports/NATIVE_INIT_V1000_ANDROID_ESOC_GPIO_RECAPTURE_HANDOFF_LIVE_2026-05-26.md` – V1000 live Android handoff가 boot-complete/read-only capture/native rollback을 수행했고, 완전 양성 타임라인은 미충족이지만 `/dev/subsys_esoc0` get 직후 `wlfw_start`/WLAN-PD/ICNSS QMI까지 도달한 현재 Android lower timing 증거
- `reports/NATIVE_INIT_V1000_ANDROID_ESOC_GPIO_RECAPTURE_HANDOFF_PLAN_2026-05-26.md` – V1000 Android eSoC/GPIO read-only recapture handoff의 plan mode가 boot image/rollback 후보와 18-step sequence를 검증한 결과
- `reports/NATIVE_INIT_V999_POST_SELINUX_WLFW_ROUTE_CLASSIFIER_2026-05-26.md` – V998 clean service-window/no-WLFW 결과와 V966/V968/V918/V923/V924/V965 증거를 종합해 다음 단위를 Android-positive read-only eSoC/GPIO dmesg recapture로 선택한 V999 결과
- `reports/NATIVE_INIT_V998_ANDROID_SERVICE_WINDOW_POST_SELINUX_2026-05-26.md` – V997 이후 service-window 재시도에서 `wificond`가 `u:r:wificond:s0`로 exec되고 14개 actor가 모두 관측됐지만 WLFW precondition이 남은 V998 결과
- `reports/NATIVE_INIT_V997_CURRENT_BOOT_SELINUX_DOMAIN_PROOF_2026-05-26.md` – current-boot V401/V490 refresh 후 service-manager trio, `vndservicemanager`, `wificond`, Wi-Fi HAL domain post-exec proof가 5/5 PASS한 V997 결과
- `reports/NATIVE_INIT_V996_HELPER_V169_DEPLOY_2026-05-26.md` – helper `v169`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 설치하고 remote sha/contract parity와 post-deploy health를 확인한 V996 결과
- `reports/NATIVE_INIT_V995_SELINUX_DOMAIN_ALLOWLIST_2026-05-26.md` – helper `v169`에서 `wificond`/`vndservicemanager` SELinux domain proof allowlist와 target profile을 추가하고 static build PASS를 확인한 V995 결과
- `reports/NATIVE_INIT_V994_SELINUX_ROUTE_CLASSIFIER_2026-05-26.md` – V993 service-window가 current-boot SELinux policy-load/domain proof 없이 실행됐음을 분류하고 다음 gate를 V995 fresh SELinux refresh/domain proof로 선택한 V994 결과
- `reports/NATIVE_INIT_V993_ANDROID_SERVICE_WINDOW_LIVE_V168_2026-05-26.md` – helper `v168` Android service-window live proof에서 traced `exec`/`crash` 시점 모두 `wificond`가 `kernel` SELinux context에 남는 것을 확인한 V993 결과
- `reports/NATIVE_INIT_V992_HELPER_V168_DEPLOY_2026-05-26.md` – helper `v168`를 `/cache/bin/a90_android_execns_probe`에 deploy-only로 설치하고 remote sha/mode parity 및 no-Wi-Fi guard를 확인한 V992 결과
- `reports/NATIVE_INIT_V991_SELINUX_EXEC_ATTR_CAPTURE_2026-05-26.md` – helper `v168`에서 traced `exec`/`crash` stop의 SELinux `attr/current`/`attr/exec` 값을 compact capture로 남기도록 source/build-only 보강한 V991 결과
- `reports/NATIVE_INIT_V990_WIFICOND_SERVICE_REGISTRATION_GAP_2026-05-26.md` – `wifinl80211` service context는 존재하지만 `wificond`/`servicemanager`가 `kernel` SELinux context로 남아 `addService`가 실패하는 갭을 분류한 V990 결과
- `reports/NATIVE_INIT_V989_WIFICOND_OFFSET_CLASSIFIER_2026-05-26.md` – V988 `wificond` crash offset을 matching binary로 분류해 `sm->addService(...) == android::NO_ERROR` fatal check가 다음 blocker임을 확인한 V989 결과
- `reports/NATIVE_INIT_V988_ANDROID_SERVICE_WINDOW_LIVE_V167_2026-05-26.md` – helper `v167` Android service-window에서 `wificond` ptrace crash capture가 동작했고 crash offset 분류가 다음 blocker임을 확인한 V988 결과
- `reports/NATIVE_INIT_V987_HELPER_V167_DEPLOY_2026-05-26.md` – helper `v167`를 `/cache/bin/a90_android_execns_probe`에 deploy-only로 설치하고 remote sha/mode parity 및 no-Wi-Fi guard를 확인한 V987 결과
- `reports/NATIVE_INIT_V986_ANDROID_SERVICE_WINDOW_WIFICOND_TRACE_2026-05-26.md` – helper `v167`에서 Android service-window 전용 `wificond` ptrace crash capture를 source/build-only로 추가한 V986 결과
- `reports/NATIVE_INIT_V985_ANDROID_SERVICE_WINDOW_LIVE_V166_2026-05-26.md` – helper `v166` Android service-window에서 property shim은 동작했지만 `wificond` `SIGABRT`와 `wlfw_precondition=0` runtime gap이 남았음을 분류한 V985 결과
- `reports/NATIVE_INIT_V984_HELPER_V166_DEPLOY_2026-05-26.md` – helper `v166`를 `/cache/bin/a90_android_execns_probe`에 deploy-only로 설치하고 remote sha/mode parity 및 no-Wi-Fi guard를 확인한 V984 결과
- `reports/NATIVE_INIT_V983_ANDROID_SERVICE_WINDOW_PROPERTY_SHIM_2026-05-26.md` – helper `v166`에서 Android service-window 전용 mode에 private property service shim을 활성화해 V982 `wificond` property-service gap을 source/build-only로 수리한 V983 결과
- `reports/NATIVE_INIT_V982_ANDROID_SERVICE_WINDOW_LIVE_V165_2026-05-26.md` – helper `v165` Android service-window에서 binder abort는 해소됐으나 property service shim 비활성으로 `wificond` `SIGABRT` runtime gap이 남았음을 분류한 V982 결과
- `reports/NATIVE_INIT_V981_HELPER_V165_DEPLOY_2026-05-26.md` – helper `v165`를 `/cache/bin/a90_android_execns_probe`에 deploy-only로 설치하고 remote sha/mode parity 및 no-Wi-Fi guard를 확인한 V981 결과
- `reports/NATIVE_INIT_V980_ANDROID_SERVICE_WINDOW_BINDER_MATERIALIZATION_2026-05-26.md` – V979 조기 `SIGABRT` 원인이 private namespace `/dev/binder` 부재임을 반영해 helper `v165`에서 Android service-window 전용 binder/hwbinder/vndbinder materialization gate를 source/build-only로 수리한 V980 결과
- `reports/NATIVE_INIT_V979_ANDROID_SERVICE_WINDOW_LIVE_V164_2026-05-26.md` – helper `v164` Android service-window start-only가 14개 actor 실행까지 도달했으나 service-manager/HAL 계열 조기 `SIGABRT`와 `wlfw_precondition=0` runtime gap으로 분류된 V979 결과
- `reports/NATIVE_INIT_V978_HELPER_V164_DEPLOY_2026-05-26.md` – helper `v164`를 `/cache/bin/a90_android_execns_probe`에 deploy-only로 설치하고 remote sha/mode parity 및 no-Wi-Fi guard를 확인한 V978 결과
- `reports/NATIVE_INIT_V977_ANDROID_SERVICE_WINDOW_ALLOW_GATE_REPAIR_2026-05-26.md` – helper `v164`에서 Android service-window mode의 generic predicate coverage는 유지하면서 generic companion allow-flag 요구만 전용 mode에서 제외한 V977 source/build-only 수리 결과
- `reports/NATIVE_INIT_V976_ANDROID_SERVICE_WINDOW_LIVE_V163_2026-05-26.md` – helper `v163` Android service-window live 재시도가 actor 실행 전 generic companion allow-flag gate에 걸렸음을 분류한 V976 결과
- `reports/NATIVE_INIT_V975_HELPER_V163_DEPLOY_2026-05-26.md` – helper `v163`를 `/cache/bin/a90_android_execns_probe`에 deploy-only로 설치하고 remote sha/mode parity 및 no-Wi-Fi guard를 확인한 V975 결과
- `reports/NATIVE_INIT_V974_ANDROID_SERVICE_WINDOW_PREDICATE_REPAIR_2026-05-26.md` – helper `v163`에서 Android service-window mode를 generic Wi-Fi companion predicate에 포함해 `service-defaults`/`property-root` allowlist 누락을 source/build-only로 수리한 V974 결과
- `reports/NATIVE_INIT_V973_ANDROID_SERVICE_WINDOW_LIVE_V162_2026-05-26.md` – helper `v162` Android service-window live 재시도가 actor 실행 전 `--property-root` generic Wi-Fi companion allowlist 누락으로 거부됨을 분류한 V973 결과
- `reports/NATIVE_INIT_V972_HELPER_V162_DEPLOY_2026-05-26.md` – helper `v162`를 `/cache/bin/a90_android_execns_probe`에 deploy-only로 설치하고 remote sha/mode parity 및 no-Wi-Fi guard를 확인한 V972 결과
- `reports/NATIVE_INIT_V971_ANDROID_SERVICE_WINDOW_VALIDATION_REPAIR_2026-05-26.md` – helper `v162`에서 Android service-window mode의 `service-defaults` SELinux context validation allowlist 누락을 source/build-only로 수리한 V971 결과
- `reports/NATIVE_INIT_V970_ANDROID_SERVICE_WINDOW_LIVE_2026-05-26.md` – helper `v161` Android service-window live proof가 actor 실행 전 `android_selinux_context_mode=service-defaults` allowlist 누락으로 거부됨을 분류한 V970 결과
- `reports/NATIVE_INIT_V969_HELPER_V161_DEPLOY_2026-05-26.md` – helper `v161`을 `/cache/bin/a90_android_execns_probe`에 deploy-only로 설치하고 remote sha/mode parity 및 no-Wi-Fi guard를 확인한 V969 결과
- `reports/NATIVE_INIT_V968_ANDROID_DMESG_ESOC_GPIO_TIMING_2026-05-26.md` – V913 Android-good dmesg/sysfs evidence를 재분류해 Wi-Fi 양성 service-window timing은 확보됐지만 GPIO135/142 level-transition timing은 기존 snapshot만으로 부족함을 확정한 V968 결과
- `reports/NATIVE_INIT_V967_ANDROID_WIFI_SERVICE_WINDOW_SUPPORT_2026-05-26.md` – helper `v161`에 Android Wi-Fi service-window start-only mode를 source/build-only로 추가하고 no-qcwlanstate/no-eSoC/no-scan/connect guard를 검증한 V967 결과
- `reports/NATIVE_INIT_V966_ANDROID_WLFW_START_ATTRIBUTION_2026-05-26.md` – V913 Android same-boot dmesg와 V963 native comparator를 host-only로 비교해 `wlfw_start`가 Android init Wi-Fi service-window에서 발생하며 direct eSoC open/qcwlanstate 재시도보다 V967 service-window parity가 먼저임을 분류한 결과
- `reports/NATIVE_INIT_V965_V964_ROUTE_CLASSIFIER_2026-05-26.md` – V963/V964 이후 direct `/dev/subsys_esoc0`, `qcwlanstate`, `IWifi.start` 재시도를 보류하고 다음 단위를 Android `cnss-daemon wlfw_start` trigger attribution으로 선정한 V965 결과
- `reports/NATIVE_INIT_V964_V963_POST_PROVIDER_TRIGGER_CLASSIFIER_2026-05-26.md` – V963 post-provider trigger evidence를 host-only로 분류해 `/dev/subsys_esoc0` open이 `sdx50m_toggle_soft_reset`/`mdm_subsys_powerup` 경로에서 stall됨을 확정한 V964 결과
- `reports/NATIVE_INIT_V963_POST_PROVIDER_TRIGGER_LIVE_2026-05-26.md` – helper `v160`의 `post-provider-no-wlfw` gate로 `/dev/subsys_esoc0` child open을 live 실행하고 cleanup reboot로 회복한 V963 결과
- `reports/NATIVE_INIT_V962_HELPER_V160_DEPLOY_2026-05-26.md` – helper `v160`을 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 no-daemon/no-Wi-Fi guard와 postflight health를 확인한 V962 결과
- `reports/NATIVE_INIT_V961_POST_PROVIDER_TRIGGER_GATE_SUPPORT_2026-05-26.md` – helper `v160`에 명시적 `post-provider-no-wlfw` subsystem trigger gate를 source/build-only로 추가하고 기본 `wlfw-precondition` gate 보존 및 no-Wi-Fi guard를 검증한 V961 결과
- `reports/NATIVE_INIT_V960_V959_FULL_SURFACE_CLASSIFIER_2026-05-26.md` – V959 full-surface evidence를 host-only로 분류해 provider/CNSS netlink는 살아 있고 남은 blocker가 MHI/WLFW/BDF/`wlan0` 부재임을 확정한 V960 결과
- `reports/NATIVE_INIT_V959_PM_PROXY_FULL_SURFACE_LIVE_2026-05-26.md` – helper `v159` `pm-proxy` matrix를 full surface로 재실행해 `cld80211` netlink 도달과 MHI/WLFW/BDF/`wlan0` 부재를 fail-closed로 수집한 V959 결과
- `reports/NATIVE_INIT_V958_V957_PM_PROXY_MATRIX_CLASSIFIER_2026-05-26.md` – V957 `pm-proxy` matrix evidence를 V953과 비교해 provider lifecycle gap은 수리됐고 남은 blocker가 post-provider WLFW/CNSS gap임을 분류한 V958 결과
- `reports/NATIVE_INIT_V957_PM_PROXY_MATRIX_LIVE_2026-05-26.md` – helper `v159` bounded `pm-proxy` matrix live 결과; `pm-service`/`pm-proxy` provider surface는 service-manager/CNSS 이후까지 유지되지만 WLFW precondition은 계속 없음
- `reports/NATIVE_INIT_V956_HELPER_V159_DEPLOY_2026-05-26.md` – helper `v159`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 no-daemon/no-Wi-Fi guard를 확인한 V956 결과
- `reports/NATIVE_INIT_V955_PM_PROXY_MATRIX_SUPPORT_2026-05-26.md` – helper `v159`에 bounded `pm-proxy` matrix order를 source/build-only로 추가하고 `pm_proxy_helper`/subsystem open/Wi-Fi bring-up guard를 검증한 V955 결과
- `reports/NATIVE_INIT_V954_V953_AFTER_MDM_PROVIDER_CLASSIFIER_2026-05-26.md` – V953 after-mdm provider evidence를 host-only로 분류해 다음 safe comparator를 `pm-proxy` matrix로 선정한 V954 결과
- `reports/NATIVE_INIT_V953_MATRIX_PROVIDER_READINESS_AFTER_MDM_2026-05-26.md` – helper `v158` matrix `after-mdm-helper-esoc-fd` order에서 service-manager 전후 `pm-service`/vndbinder provider surface 변화를 관측한 V953 live 결과
- `reports/NATIVE_INIT_V952_V951_MATRIX_PROVIDER_CLASSIFIER_2026-05-26.md` – V951 before-CNSS matrix와 V947 runtime-contract provider evidence를 비교해 `after-mdm-helper-esoc-fd` order를 다음 comparator로 선정한 V952 결과
- `reports/NATIVE_INIT_V951_MATRIX_PROVIDER_READINESS_BEFORE_CNSS_2026-05-26.md` – helper `v158` matrix `before-cnss` order에서 service-manager trio는 존재하지만 `pm-service` provider surface가 사라지는 것을 관측한 V951 live 결과
- `reports/NATIVE_INIT_V950_HELPER_V158_DEPLOY_2026-05-26.md` – helper `v158`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 no-daemon/no-Wi-Fi guard를 확인한 V950 결과
- `reports/NATIVE_INIT_V949_MATRIX_PROVIDER_READINESS_SUPPORT_2026-05-26.md` – helper `v158`에 provider-readiness snapshots를 CNSS/service-manager matrix path까지 확장해 다음 bounded matrix live comparator를 준비한 V949 source/build-only 결과
- `reports/NATIVE_INIT_V948_V947_PROVIDER_READINESS_CLASSIFIER_2026-05-26.md` – V947 provider-readiness evidence를 host-only로 분류해 binder/property surface는 존재하고 다음 비교 대상은 CNSS/service-manager matrix provider fd 관측성임을 확정한 V948 결과
- `reports/NATIVE_INIT_V947_PROVIDER_READINESS_CAPTURE_2026-05-26.md` – helper `v157` live capture에서 `pm-service` vndbinder fd, `mdm_helper` `/dev/esoc-0`, service-manager/proxy absence, subsystem fd absence를 bounded runtime-contract path로 수집한 V947 결과
- `reports/NATIVE_INIT_V946_HELPER_V157_DEPLOY_2026-05-26.md` – helper `v157`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 remote checksum/contract parity와 no-daemon/no-Wi-Fi guard를 확인한 V946 결과
- `reports/NATIVE_INIT_V945_PROVIDER_READINESS_SUPPORT_2026-05-26.md` – V944 provider/lifetime gap 후속으로 기존 bounded `mdm_helper` runtime-contract path에 service-manager/binder/provider fd readiness 관측성을 추가한 helper `v157` source/build-only 결과
- `reports/NATIVE_INIT_V944_V943_QUEUE_TIMING_CLASSIFIER_2026-05-26.md` – V943 fresh queue failure를 host-only로 분류해 `mdm_helper` `/dev/esoc-0` reachability가 아니라 `per_mgr` provider/lifetime gap이 남은 blocker임을 확정한 V944 결과
- `reports/NATIVE_INIT_V943_MDM_HELPER_QUEUE_TIMING_CAPTURE_2026-05-26.md` – helper `v156` queue-timing live capture 결과; `mdm_helper`는 spawn 후 약 14ms 내 `/dev/esoc-0` fd를 잡지만 `per_mgr`는 subsystem fd 없이 살아 있고 fresh SDX50M queue failure가 같은 window에 발생함을 확인한 V943 결과
- `reports/NATIVE_INIT_V942_HELPER_V156_DEPLOY_2026-05-26.md` – helper `v156`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 remote checksum/contract parity와 postflight health를 확인한 V942 결과
- `reports/NATIVE_INIT_V941_MDM_HELPER_QUEUE_TIMING_SUPPORT_2026-05-26.md` – helper `v156`에 `mdm_helper_queue_timing.*` 진단을 기존 runtime-contract mode에 source/build-only로 추가하고 static build/guardrail 검증을 통과한 V941 결과
- `reports/NATIVE_INIT_V940_SDX50M_QUEUE_INPUT_CONTRACT_2026-05-26.md` – V938/V939와 V857/V860/V861/V867 PM evidence를 묶어 다음 작업을 helper `v156` queue-timing diagnostics로 좁힌 V940 결과
- `reports/NATIVE_INIT_V939_V938_LOWER_CONTRACT_CLASSIFIER_2026-05-26.md` – V938/V914 evidence를 host-only로 묶어 exact `mdm_helper` property-context gap은 co-present지만 다음 blocker로 충분하지 않고, 다음 gate를 SDX50M queue input contract 분류로 라우팅한 V939 결과
- `reports/NATIVE_INIT_V938_MDM_HELPER_LOWER_CONTRACT_CAPTURE_2026-05-26.md` – helper `v155` lower-contract live capture 결과; `mdm_helper`는 `/dev/esoc-0` fd까지 도달하지만 `ks`/MHI/WLFW는 없고 exact `mdm_helper` property-context gap이 co-present함을 확인한 V938 결과
- `reports/NATIVE_INIT_V937_HELPER_V155_DEPLOY_2026-05-26.md` – helper `v155`를 `/cache/bin/a90_android_execns_probe`로 deploy-only 배포하고 remote sha/usage, postflight health, no-daemon/no-Wi-Fi guard를 확인한 V937 결과
- `reports/NATIVE_INIT_V936_MDM_HELPER_LOWER_CONTRACT_SUPPORT_2026-05-26.md` – helper `v155`에 `mdm_helper` property-context/SDX50M lower-contract 진단을 기존 runtime-contract mode에 source/build-only로 추가한 V936 결과
- `reports/NATIVE_INIT_V935_MDM_HELPER_SDX50M_QUEUE_CONTRACT_2026-05-26.md` – V931/V933 service-manager matrix evidence를 host-only로 재분류해 현재 Binder blocker는 닫히고 `mdm_helper` SDX50M queue failure와 property-context gap이 남은 lower-contract blocker임을 확정한 V935 결과
- `reports/NATIVE_INIT_V934_CNSS_FRESH_PID_ATTRIBUTION_2026-05-26.md` – V927/V931/V933 dmesg를 현재 child PID 기준으로 재귀속해 service-manager matrix의 현재 Binder failure는 해소됐고 남은 blocker가 `mdm_helper`/SDX50M queue 및 WLFW publication gap임을 정정 분류한 V934 결과
- `reports/NATIVE_INIT_V933_CNSS_SERVICE_MANAGER_BEFORE_CNSS_LIVE_2026-05-26.md` – helper `v154`의 `before-cnss` matrix live 결과; service-manager/`mdm_helper`/CNSS actor와 `/dev/esoc-0` fd는 재현됐고 V934 기준 현재 Binder failure는 해소됐지만 WLFW absence가 유지되어 `/dev/subsys_esoc0` open 없이 fail-closed PASS로 분류한 V933 결과
- `reports/NATIVE_INIT_V932_CNSS_SERVICE_MANAGER_ORDER_DELTA_2026-05-26.md` – V927/V601/V603/V931 evidence를 host-only로 비교해 다음 bounded live order를 helper `v154`의 `before-cnss` matrix로 선정한 V932 결과
- `reports/NATIVE_INIT_V931_CNSS_SERVICE_MANAGER_MATRIX_LIVE_2026-05-26.md` – helper `v154` CNSS/service-manager matrix live 결과; `mdm_helper` `/dev/esoc-0` fd와 service-manager/CNSS actor start는 재현됐지만 WLFW precondition이 없어 `/dev/subsys_esoc0` open 없이 fail-closed PASS로 분류한 V931 결과
- `reports/NATIVE_INIT_V930_HELPER_V154_DEPLOY_2026-05-26.md` – helper `v154`를 `/cache/bin/a90_android_execns_probe`로 serial deploy-only 배포하고 remote sha/mode/order enum parity, postflight health, no-daemon/no-Wi-Fi guard를 확인한 V930 결과
- `reports/NATIVE_INIT_V929_CNSS_SERVICE_MANAGER_MATRIX_SUPPORT_2026-05-26.md` – helper `v154`에 repaired runtime namespace 기반 CNSS/service-manager matrix mode와 order enum을 source/build-only로 추가한 V929 결과
- `reports/NATIVE_INIT_V928_CNSS_BINDER_LOWER_INTERSECTION_2026-05-26.md` – V927에서 namespace/truncation은 해결됐지만 CNSS Binder failure가 남고, V603에서는 service-manager가 Binder failure를 지우지만 service-notifier `180`이 사라진다는 same-window ordering blocker를 host-only로 분류한 V928 결과
- `reports/NATIVE_INIT_V927_CNSS_BEFORE_ESOC_COMPACT_LIVE_2026-05-26.md` – helper `v153` compact CNSS-before-eSoC live gate 결과; runtime namespace repair와 compact output은 동작하지만 WLFW precondition이 없어 `/dev/subsys_esoc0` open 없이 fail-closed PASS로 분류한 V927 결과
- `reports/NATIVE_INIT_V926_HELPER_V153_DEPLOY_2026-05-26.md` – helper `v153`를 serial safe chunk로 `/cache/bin/a90_android_execns_probe`에 deploy하고 remote checksum, bootstatus/selftest, no-daemon/no-Wi-Fi guard를 확인한 V926 결과
- `reports/NATIVE_INIT_V925_CNSS_RUNTIME_NAMESPACE_SUPPORT_2026-05-26.md` – helper `v153`에 compact CNSS-before-eSoC output throttle과 linkerconfig/APEX/VNDK/property-context runtime namespace reporting을 source/build-only로 추가한 V925 결과
- `reports/NATIVE_INIT_V924_CNSS_WLFW_PRECONDITION_GAP_2026-05-26.md` – V923 결과를 host-only로 분류해 native CNSS가 `cld80211` netlink에는 도달하지만 linkerconfig/property-context namespace gap 때문에 WLFW/BDF/`wlan0`로 진행하지 못함을 정리한 V924 결과
- `reports/NATIVE_INIT_V923_CNSS_BEFORE_ESOC_LIVE_2026-05-26.md` – helper `v152`의 CNSS-before-eSoC live gate 결과; `mdm_helper`/CNSS actor는 시작됐지만 WLFW precondition이 없어 `/dev/subsys_esoc0` open 없이 fail-closed PASS로 분류한 V923 결과
- `reports/NATIVE_INIT_V922_HELPER_V152_DEPLOY_2026-05-26.md` – helper `v152`를 `/cache/bin/a90_android_execns_probe`에 deploy-only로 배포하고 sha/mode parity, bootstatus/selftest, no-daemon/no-Wi-Fi guard를 확인한 V922 결과
- `reports/NATIVE_INIT_V921_CNSS_BEFORE_ESOC_HELPER_BUILD_2026-05-26.md` – helper `v152`에 `cnss-daemon wlfw_start` 계열 precondition이 관찰될 때만 `/dev/subsys_esoc0` trigger child를 여는 fail-closed source/build-only V921 결과
- `reports/NATIVE_INIT_V919_SDX50M_SOFT_RESET_BLOCKER_CLASSIFIER_2026-05-26.md` – V918의 `sdx50m_toggle_soft_reset` D-state blocker를 기존 V913 Android dmesg/GPIO/IRQ evidence와 비교해 새 Magisk/Android 재부팅 없이 host-only로 분류한 V919 결과
- `reports/NATIVE_INIT_V918_MDM_HELPER_SUBSYS_TRIGGER_WAIT_LIVE_2026-05-26.md` – helper v151 wait-gated `/dev/subsys_esoc0` trigger 결과; gate는 열렸지만 `sdx50m_toggle_soft_reset` D-state blocker와 cleanup reboot를 확인한 V918 결과
- `reports/NATIVE_INIT_V917_MDM_HELPER_SUBSYS_TRIGGER_LIVE_2026-05-26.md` – helper v150 배포와 corrected native trigger live gate 결과; `mdm_helper`의 `/dev/esoc-0` fd가 최종 시점에만 나타나 V918 bounded wait gate가 필요함을 확정한 V917 결과
- `reports/NATIVE_INIT_V916_MDM_HELPER_SUBSYS_TRIGGER_SUPPORT_2026-05-26.md` – V915 보정 기준에 맞춰 `mdm_helper` 관찰 후 제한적 `/dev/subsys_esoc0` trigger child를 실행하는 helper v150 source/build-only 검증 결과
- `reports/NATIVE_INIT_V914_V913_ANDROID_TIMELINE_RECLASSIFIER_2026-05-26.md` – V913 Android handoff live evidence를 host-only로 재분류해 WLFW/BDF/wlan0는 양성이지만 post-boot mdm3/GPIO142/ks/MHI 표면은 필수 성공조건이 아님을 확정한 V914 결과
- `reports/NATIVE_INIT_V913_ANDROID_ESOC_GPIO_TIMELINE_TOOL_2026-05-26.md` – Android 정상 부팅 후 GPIO135/PMIC GPIO9/GPIO142/PCIe/MDM3/KS/MHI/WLFW 양성 타임라인을 read-only로 수집하는 V913 도구와 현재 native 상태의 ADB unavailable preflight 결과
- `reports/NATIVE_INIT_V913_ANDROID_ESOC_GPIO_TIMELINE_HANDOFF_PLAN_2026-05-26.md` – V913 Android eSoC/GPIO 양성 타임라인 collector를 Android boot/rollback handoff로 실행하기 위한 plan-mode 래퍼 검증 결과
- `reports/NATIVE_INIT_V911_MDM_HELPER_ESOC_FD_STALL_CLASSIFIER_2026-05-26.md` – V911 결과 `mdm_helper`가 `/dev/esoc-0` fd를 보유한 상태에서 worker thread가 `ESOC_WAIT_FOR_REQ` ioctl에 진입함을 분류
- `reports/NATIVE_INIT_V910_HELPER_V149_DEPLOY_2026-05-26.md` – V910 결과 helper `v149` deploy-only PASS, remote sha/mode marker/selftest/actor-clean/Wi-Fi-link-clean 확인
- `reports/NATIVE_INIT_V909_MDM_HELPER_ESOC_FD_STALL_SUPPORT_2026-05-26.md` – V909 결과 helper `v149`에 `/dev/esoc-0` fdinfo와 `mdm_helper` wchan/syscall/stack/status/sched snapshot을 source/build-only로 추가
- `reports/NATIVE_INIT_V908_MDM_HELPER_RUNTIME_CONTRACT_CAPTURE_2026-05-26.md` – V908 결과 `mdm_helper`가 property/per_mgr runtime contract 아래 `/dev/esoc-0` fd까지 도달했지만 `ks`/MHI/WLFW는 아직 없음
- `reports/NATIVE_INIT_V907_HELPER_V148_DEPLOY_2026-05-26.md` – V907 결과 helper `v148` deploy-only PASS, remote sha/mode marker/selftest/actor-clean/Wi-Fi-link-clean 확인
- `reports/NATIVE_INIT_V906_MDM_HELPER_RUNTIME_CONTRACT_HELPER_BUILD_2026-05-26.md` – V906 결과 helper `v148`에 `mdm_helper` runtime-contract capture mode, context mapping, property shim, per_mgr-light ordering, MHI mirror를 source/build-only로 추가
- `reports/NATIVE_INIT_V905_MDM_HELPER_RUNTIME_REPAIR_DESIGN_2026-05-26.md` – V905 결과 Android dmesg/Magisk 재캡처는 즉시 blocker가 아니며 다음은 property shim 기반 `mdm_helper` runtime-contract helper source/build-only 단위임을 분류
- `reports/NATIVE_INIT_V904_MDM_HELPER_RUNTIME_INPUT_PARITY_2026-05-26.md` – V904 결과 native direct `mdm_helper`는 Android init/SELinux/per_mgr runtime contract가 없어 eSoC/MHI path로 진입하지 않음을 분류
- `reports/NATIVE_INIT_V903_MDM_HELPER_ONLY_DEEP_CAPTURE_2026-05-26.md` – V903 결과 native `mdm_helper`는 observable이나 `/dev/esoc-0`/`/dev/subsys_esoc0`/MHI/`ks` surface 미진입
- `reports/NATIVE_INIT_V902_MDM_HELPER_KS_BLOCKER_CAPTURE_2026-05-26.md` – V902 결과 block child wchan=`mdm_subsys_powerup`, stack capture PASS, native `mdm_helper`는 `/dev/esoc-0` 미보유
- `reports/NATIVE_INIT_V901_HELPER_V145_ALLOWLIST_DEPLOY_2026-05-26.md` – V901 결과 helper `v145` allowlist repair/build/deploy PASS
- `reports/NATIVE_INIT_V900_MDM_HELPER_KS_CONTRACT_LIVE_2026-05-26.md` – V900 결과 `mdm_helper`는 observable, `/dev/subsys_esoc0` open child는 blocked/reboot-required, `ks`/MHI/GPIO142 진전 없음
- `reports/NATIVE_INIT_V899_HELPER_V144_DEPLOY_2026-05-26.md` – V899 결과 helper `v144` deploy-only PASS, remote sha/mode marker/selftest/actor-clean/Wi-Fi-link-clean 확인
- `reports/NATIVE_INIT_V898_MDM_HELPER_KS_CONTRACT_HELPER_BUILD_2026-05-26.md` – V898 결과 helper `v144`에 fail-closed `mdm_helper`/`ks` image-contract mode를 source/build-only로 추가하고 static ARM64 build PASS
- `reports/NATIVE_INIT_V897_MDM_HELPER_KS_CONTRACT_DESIGN_2026-05-26.md` – V897 결과 current helper가 pre-subsys `mdm_helper`/`ks` image-contract mode를 아직 갖지 않아 V898 source/build-only helper 작업이 필요함을 분류
- `reports/NATIVE_INIT_V896_ANDROID_MDM_HELPER_IMAGE_CONTRACT_2026-05-26.md` – V896 결과 Android `mdm_helper`/`ks` MHI image/link contract 부재가 V895 native `IMG_XFER_DONE` failure의 다음 blocker임을 host-only로 분류
- `reports/NATIVE_INIT_V895_MDM2AP_IRQ_SNAPSHOT_PROOF_2026-05-26.md` – V895 결과 `IMG_XFER_DONE` 이후에도 GPIO 142 `mdm status` IRQ delta가 0임을 live proof로 분류
- `reports/NATIVE_INIT_V894_MDM2AP_READY_SURFACE_2026-05-26.md` – V894 결과 `/proc/interrupts`의 GPIO 142 `mdm status` IRQ를 다음 readiness observer로 선정
- `reports/NATIVE_INIT_V893_ESOC_POST_IMG_XFER_CLASSIFIER_2026-05-26.md` – V893 결과 `IMG_XFER_DONE`은 readiness setter가 아니며 MDM2AP status/ready 전환이 다음 blocker임을 분류
- `reports/NATIVE_INIT_V892_HELPER_V142_ALLOWLIST_DEPLOY_2026-05-26.md` – V892 결과 helper `v142` allowlist repair/build/deploy PASS
- `reports/NATIVE_INIT_V891_ESOC_CONDITIONAL_RESPONSE_PROOF_2026-05-26.md` – V891 결과 `ESOC_IMG_XFER_DONE` sent, `GET_STATUS` not-ready, cleanup reboot PASS
- `reports/NATIVE_INIT_V890_HELPER_V141_DEPLOY_2026-05-26.md` – V890 결과 helper `v141` deploy-only PASS, remote sha/mode marker/selftest/actor-clean/Wi-Fi-link-clean 확인
- `reports/NATIVE_INIT_V889_ESOC_CONDITIONAL_RESPONSE_HELPER_BUILD_2026-05-26.md` – V889 결과 helper `v141` static build PASS, conditional response mode와 allow flag 추가
- `reports/NATIVE_INIT_V888_ESOC_RESPONSE_GATE_CLASSIFIER_2026-05-26.md` – V888 결과 `ESOC_IMG_XFER_DONE` first, readiness-gated `ESOC_BOOT_DONE` response gate 선정
- `reports/NATIVE_INIT_V887_HELPER_V140_DEPLOY_2026-05-26.md` – V887 결과 helper `v140` deploy-only PASS, remote sha/mode marker와 serial chunk 안전 범위 확인
- `reports/NATIVE_INIT_V886_ESOC_REQ_IMG_RESPONSE_HELPER_BUILD_2026-05-26.md` – V886 결과 helper `v140` static build PASS, `ESOC_REQ_IMG` observer semantic repair와 response scaffold 추가
- `reports/NATIVE_INIT_V885_ESOC_REQ_IMG_RESPONSE_CLASSIFIER_2026-05-26.md` – V885 결과 `ESOC_WAIT_FOR_REQ rc=4 value=1`은 ioctl failure가 아니라 `ESOC_REQ_IMG`이며 V886 helper semantic repair 후보 선정
- `reports/NATIVE_INIT_V884_REQ_REGISTERED_SUBSYS_HOLD_OBSERVER_2026-05-26.md` – V884 결과 `REG_REQ_ENG rc0`, `ESOC_REQ_IMG` 관측, `/dev/subsys_esoc0` D-state/reboot cleanup 확인
- `reports/NATIVE_INIT_V883_HELPER_V139_DEPLOY_2026-05-26.md` – V883 결과 helper `v139` deploy-only PASS, remote sha/mode marker/selftest/actor-clean/Wi-Fi-link-clean 확인
- `reports/NATIVE_INIT_V882_PASSIVE_WAIT_FOR_REQ_HELPER_BUILD_2026-05-26.md` – V882 결과 helper `v139` static build PASS, passive `ESOC_WAIT_FOR_REQ` observer support 추가
- `reports/NATIVE_INIT_V881_HELPER_V138_DEPLOY_2026-05-26.md` – V881 결과 helper `v138` deploy-only PASS, remote sha/mode marker/selftest/actor-clean/Wi-Fi-link-clean 확인과 V882 passive WAIT_FOR_REQ observer route 선정
- `reports/NATIVE_INIT_V880_REQ_REGISTERED_SUBSYS_HOLD_HELPER_BUILD_2026-05-26.md` – V880 결과 helper `v138` static build PASS, stale-open-errno repair와 REQ-registered subsystem-hold preflight mode 추가
- `reports/NATIVE_INIT_V879_CMD_ENGINE_OWNERSHIP_CLASSIFIER_2026-05-26.md` – V879 결과 direct userspace `CMD_EXE` 차단과 V880 helper `v138` source/build-only 후보 선정
- `reports/NATIVE_INIT_V878_ESOC_ENGINE_REGISTER_PREFLIGHT_2026-05-25.md` – V878 결과 `REG_REQ_ENG` rc0, `REG_CMD_ENG` EBUSY로 다음 CMD engine ownership classifier 필요
- `reports/NATIVE_INIT_V877_HELPER_V137_DEPLOY_2026-05-25.md` – V877 결과 helper `v137` deploy-only PASS, remote sha/mode marker/selftest/actor-clean/Wi-Fi-link-clean 확인
- `reports/NATIVE_INIT_V876_ESOC_ENGINE_REGISTER_HELPER_BUILD_2026-05-25.md` – V876 결과 helper `v137` static build PASS, CMD/REQ registration preflight mode 추가, deploy/live ioctl 없음
- `reports/NATIVE_INIT_V875_ESOC_STATE_MACHINE_PRECONDITION_2026-05-25.md` – V875 결과 helper-only CMD/REQ registration support를 V876 후보로 선택, live contact/mutating ioctl 없음
- `reports/NATIVE_INIT_V874_ESOC_CONTROL_PREFLIGHT_2026-05-25.md` – V874 결과 `/dev/esoc-0` read-only ioctl preflight PASS, mutating eSoC ioctl/actor/Wi-Fi bring-up 없음
- `reports/NATIVE_INIT_V873_HELPER_V136_DEPLOY_2026-05-25.md` – V873 결과 helper `v136` deploy-only PASS, remote sha/mode marker 확인
- `reports/NATIVE_INIT_V872_ESOC_PREFLIGHT_HELPER_V136_BUILD_2026-05-25.md` – V872 결과 helper `v136` classification repair와 static ARM64 build PASS
- `reports/NATIVE_INIT_V870_HELPER_V135_DEPLOY_2026-05-25.md` – V870 결과 helper `v135` deploy-only PASS, remote sha/mode marker/selftest/actor-clean/Wi-Fi-link-clean 확인
- `reports/NATIVE_INIT_V869_ESOC_CONTROL_PREFLIGHT_HELPER_BUILD_2026-05-25.md` – V869 결과 helper `v135`가 `wifi-companion-esoc-control-preflight`와 fail-closed eSoC UAPI markers를 포함해 static build 통과
- `reports/NATIVE_INIT_V868_PM_ESOC_CONTRACT_CLASSIFIER_2026-05-25.md` – V868 결과 `pm_proxy_helper` 단독 재시도를 닫고 A90 로컬 `ESOC_REG_REQ_ENG=7`/`ESOC_REG_CMD_ENG=8` 기반 eSoC control preflight를 V869 후보로 선정
- `reports/NATIVE_INIT_V829_SERVLOC_DOMAIN_LIST_PROBE_2026-05-25.md` – V829 결과 service-locator `GET_DOMAIN_LIST wlan/fw` live QMI 응답에서 `msm/modem/wlan_pd` instance `180`을 확인해 V830 service-notifier listener proof로 라우팅
- `reports/NATIVE_INIT_V828_SERVLOC_DOMAIN_LIST_PAYLOAD_2026-05-25.md` – V828 결과 `wlan/fw` `GET_DOMAIN_LIST` request hex를 도출해 V829 bounded no-HAL live QMI probe로 라우팅
- `reports/NATIVE_INIT_V827_SERVICE_NOTIFIER_CONTINUATION_2026-05-25.md` – V827 결과 service-notifier 180은 control endpoint일 뿐이며 ICNSS continuation은 service-locator `wlan/fw` domain-list QMI proof가 필요해 V828로 라우팅
- `reports/NATIVE_INIT_V826_QRTR_EVENT_DETAIL_CLASSIFIER_2026-05-25.md` – V826 결과 service-locator `64/257`은 node `1` port `16475`, service-notifier `66/46081`은 node `0` port `2`로 보여 V827 continuation classifier로 라우팅
- `reports/NATIVE_INIT_V825_QRTR_ENCODED_MATRIX_2026-05-25.md` – V825 결과 encoded service-locator `64/257`과 service-notifier `66/46081` publication이 보여 V826 event-detail observer로 라우팅
- `reports/NATIVE_INIT_V824_QRTR_ENCODED_INSTANCE_2026-05-25.md` – V824 결과 kernel QMI client는 QRTR instance를 `version | instance << 8`로 encode하므로 V825 encoded-instance no-QMI matrix로 라우팅
- `reports/NATIVE_INIT_V823_SSCTL_NAMESERVICE_MATRIX_2026-05-25.md` – V823 결과 `ssctl:43:16`도 AF_QIPCRTR lookup은 성공하지만 service publication은 0이라 kernel QMI client visibility와 userspace nameservice visibility 갭으로 라우팅
- `reports/NATIVE_INIT_V822_SYSMON_NAMESERVICE_GAP_2026-05-25.md` – V822 결과 `sysmon-qmi`의 실제 source lookup은 SSCTL service `43` instance `16`인데 V821 matrix에는 빠져 있어 V823 `ssctl:43:16` no-QMI matrix 확장으로 라우팅
- `reports/NATIVE_INIT_V821_QRTR_NAMESERVICE_MATRIX_2026-05-25.md` – V821 결과 helper v125 matrix에서 service-locator/service-notifier/WLFW 후보 모두 AF_QIPCRTR lookup은 성공했지만 service publication은 0이라 V822 sysmon/service-locator dmesg와 userspace nameservice clean-empty 갭으로 라우팅
- `reports/NATIVE_INIT_V820_QRTR_NAMESPACE_CLASSIFIER_2026-05-25.md` – V820 결과 QIPCRTR/AF_QIPCRTR readback은 동작하지만 `/proc/net/qrtr`/debugfs visibility가 없고 service69 publication이 비어 있어 V821 in-helper nameservice matrix로 라우팅
- `reports/NATIVE_INIT_V819_MDM3_ESOC_REGISTRATION_CATALOGUE_2026-05-25.md` – V819 결과 V817 lower window를 보존하면서 registration catalogue를 수집했고 debugfs service surfaces, `/proc/net/qrtr`, per-process QRTR sections가 비어 있어 V820 helper/per-process QRTR namespace inspection으로 라우팅
- `reports/NATIVE_INIT_V818_MDM3_ESOC_REGISTRATION_CLASSIFIER_2026-05-25.md` – V818 결과 V817 lower window, V798 complete PIL, V795 holder-only 증거를 묶어 mdm3/esoc0 registration gap을 확정하고 V819 bounded read-only catalogue로 라우팅
- `reports/NATIVE_INIT_V817_IN_WINDOW_SYSMON_SAMPLER_2026-05-25.md` – V817 결과 lower window 안에서 mss/QRTR/sysmon은 전진하지만 mdm3는 계속 `OFFLINING`, service74/WLAN-PD/WLFW/BDF/`wlan0`는 absent라 V818 mdm3/esoc0 service-locator/sysmon registration isolation으로 라우팅
- `reports/NATIVE_INIT_V816_IDLE_TRIGGER_DELTA_CLASSIFIER_2026-05-25.md` – V816 결과 idle은 modem/mdm3 OFFLINING과 runtime service-publication absent, V812 lower-trigger는 mss/QRTR/sysmon만 전진하고 mdm3/service74/WLAN-PD/WLFW/BDF/`wlan0`는 absent라 V817 in-window read-only sampler로 라우팅
- `reports/NATIVE_INIT_V815_SUBSYSTEM_SYSMON_SNAPSHOT_2026-05-25.md` – V815 결과 idle stock v724에서 msm_subsys 10개, modem/mss `OFFLINING`, mdm3/esoc0 `OFFLINING`, ICNSS platform present, service-locator timeout marker, runtime service74/WLAN-PD/WLFW/BDF/`wlan0` absent를 read-only로 캡처
- `reports/NATIVE_INIT_V814_SIBLING_SYSMON_SOURCE_CLASSIFIER_2026-05-25.md` – V814 결과 OSRC source가 service-notifier를 SERVREG QMI listener/state indication 경로로, sysmon을 subsystem registration/QMI lookup 경로로 매핑하므로 V815를 stock v724 read-only subsystem/sysmon/service-locator registration snapshot으로 선정
- `reports/NATIVE_INIT_V813_POST_SYSMON_PUBLICATION_CLASSIFIER_2026-05-25.md` – V813 결과 V812는 mss/QRTR/sysmon까지만 도달하고, V785는 memshare를 단독 blocker에서 제외하며, Android는 sibling sysmon/service74/WLAN-PD/WLFW로 이어지지만 native는 sibling sysmon/service74/WLFW가 없어 V814를 service-publication precondition isolation으로 선정
- `reports/NATIVE_INIT_V812_MDM3_WLANPD_SERVICE69_OBSERVER_2026-05-25.md` – V812 결과 V401/V490 refresh와 lower companion/CNSS diagnostic stack 후에도 mss/QRTR/sysmon까지만 도달하고 mdm3 `OFFLINING`, service69/WLFW/BDF/`wlan0` absent가 유지되어 post-sysmon mdm3/WLAN-PD publication precondition으로 라우팅
- `reports/NATIVE_INIT_V811_WLFW_PUBLICATION_PRECONDITION_CLASSIFIER_2026-05-25.md` – V811 결과 Android는 mdm3 `ONLINE` + WLAN-PD/WLFW/BDF/`wlan0`까지 이어지지만 native는 mss/QRTR/sysmon/service-notifier 표면 후 mdm3 `OFFLINING`과 service69 clean-empty로 멈추므로 다음 blocker를 mdm3/WLAN-PD/WLFW publication precondition으로 선정
- `reports/NATIVE_INIT_V810_REGISTER_PROBE_WLFW_FWREADY_CLASSIFIER_2026-05-25.md` – V810 결과 PLD/SNOC/ICNSS register는 async 등록 경로이고 실제 QCACLD probe는 WLFW/service69 -> ICNSS-QMI -> `FW_READY` 이후에만 열리므로 다음 blocker를 WLFW publication precondition으로 선정
- `reports/NATIVE_INIT_V809_ICNSS_MODULES_NOT_INITIALIZED_SOURCE_CLASSIFIER_2026-05-25.md` – V809 결과 qcwlanstate `OFF`는 원인이 아니라 ICNSS/QCACLD가 `DRIVER_MODULES_ENABLED`에 도달하지 못했음을 보여주는 status mirror이며, 다음 blocker를 PLD/ICNSS register-to-WLFW/FW_READY 경계로 선정
- `reports/NATIVE_INIT_V808_OVERLAP_COMPANION_BOOT_WLAN_2026-05-25.md` – V808 결과 provider-first companion이 `boot_wlan` 시작 시 살아 있고 service74/provider/CNSS retry 계약이 성립해도 WLFW/service69/FW_READY/BDF/`wlan0`가 absent라 ICNSS module-initialized prerequisite 분류로 라우팅
- `reports/NATIVE_INIT_V807_PRE_WLFW_OVERLAP_CLASSIFIER_2026-05-25.md` – V807 결과 V806은 companion cleanup 후 `boot_wlan`을 실행한 sequential gate였으므로 V808 overlapped companion + `boot_wlan` live gate로 라우팅
- `reports/NATIVE_INIT_V806_WLFW_SERVICE69_LIVE_GATE_2026-05-25.md` – V806 결과 provider-first + `boot_wlan`에서도 QRTR WLFW service `69`가 absent라 pre-WLFW publication prerequisite 분류로 라우팅
- `reports/NATIVE_INIT_V805_ICNSS_FW_READY_WLFW_GATE_CLASSIFIER_2026-05-25.md` – V805 결과 WLFW service `0x45/69` publication이 `FW_READY`/probe/BDF/`wlan0` 전 첫 missing observable임을 host-only로 선정
- `reports/NATIVE_INIT_V804_PLD_ICNSS_REGISTER_PROBE_PREREQ_CLASSIFIER_2026-05-25.md` – V804 결과 PLD/SNOC register 자체보다 ICNSS FW_READY/WLFW service-arrival gate가 다음 blocker임을 host-only로 재분류
- `reports/NATIVE_INIT_V803_PROVIDER_FIRST_HDD_PLD_PREREQ_CLASSIFIER_2026-05-25.md` – V803 결과 V802 blocker를 `wlan_hdd_register_driver()`/PLD/ICNSS register-probe completion 전후로 좁혀 V804 non-flash prerequisite classifier로 라우팅
- `reports/NATIVE_INIT_V802_PROVIDER_FIRST_BOOT_WLAN_OBSERVE_2026-05-25.md` – V802 결과 provider-first context + `boot_wlan`에서도 HDD init/qcwlanstate까지만 진행되고 ICNSS-QMI/WLFW/BDF/wiphy/`wlan0`는 absent라 V803 HDD/PLD prerequisite classifier로 라우팅
- `reports/NATIVE_INIT_V801_V800_EDGE_ROUTE_CLASSIFIER_2026-05-25.md` – V801 결과 QCA6390 unbound를 1차 목표로 보지 않고 V800 provider-first context와 V752 `boot_wlan` trigger를 결합하는 V802 live gate로 라우팅
- `reports/NATIVE_INIT_V800_PROVIDER_FIRST_ICNSS_EDGE_V124_REPLAY_2026-05-25.md` – V800 결과 v724/helper v124에서도 service74 + PeripheralManager + provider-first CNSS retry + ICNSS edge capture는 통과하지만 QCA6390/WLFW/BDF/`wlan0`는 absent로 유지됨
- `reports/NATIVE_INIT_V799_POST_V798_ROUTE_CLASSIFIER_2026-05-25.md` – V799 결과 현재 lower-only 경로보다 기존 service74 양성 + V694 PeripheralManager 확인 경로가 최단이므로 V800 below-HAL CNSS tail replay로 라우팅
- `reports/NATIVE_INIT_V798_PIL_CODE_GAP_CLASSIFIER_2026-05-25.md` – V798 결과 V797의 modem PIL power-up/proxy sequence는 완성됐지만 native는 여전히 mdm3/service-notifier `74/180`/service `69`/wiphy/`wlan0`가 absent라 V799 service-notifier/root-PD gap으로 라우팅
- `reports/NATIVE_INIT_V797_PIL_TRACE_PAYLOAD_2026-05-25.md` – V797 결과 lower-window transition 중 `msm_pil_event:pil_notif` 8개 payload를 캡처했고 모두 `fw=modem`, code `2/3/6/7`이나 mdm3/service69/WLFW/BDF/`wlan0`는 여전히 absent임을 확인
- `reports/NATIVE_INIT_V796_POST_V795_ROUTE_CLASSIFIER_2026-05-25.md` – V796 결과 V795/V792/V782/V785/V764/V768을 종합해 반복 trigger 대신 `msm_pil_event:pil_notif`의 `event_name`/`code`/`fw_name` payload capture를 다음 gate로 선정
- `reports/NATIVE_INIT_V795_LOWER_WINDOW_MDM3_ESOC_OBSERVER_2026-05-25.md` – V795 결과 firmware-backed `subsys_modem` holder가 `mss=ONLINE`과 QRTR RX는 만들지만 mdm3/esoc0은 OFFLINING, service `69`/WLFW/BDF/`wlan0`는 absent로 남아 V796 mdm3/esoc trigger contract로 라우팅
- `reports/NATIVE_INIT_V794_MDM3_ICNSS_SURFACE_OBSERVER_2026-05-25.md` – V794 결과 idle native에서 modem/esoc0은 OFFLINING, ICNSS는 bound, WLAN control node는 존재하지만 QRTR/service69/WLFW/BDF/`wlan0`는 absent임을 read-only로 확인
- `reports/NATIVE_INIT_V793_CNSS_ICNSS_ROUTE_CLASSIFIER_2026-05-25.md` – V793 결과 service-manager/binder-only/boot_wlan blind retry를 보류하고 다음 경로를 mdm3 + ICNSS/WLFW continuation으로 선정
- `reports/NATIVE_INIT_V792_KNOWN_ASOC_WARNING_CNSS_WLFW_2026-05-25.md` – V792 결과 known ASoC warning을 허용해 CNSS readback을 수행했지만 service `69`/WLFW/BDF/`wlan0`가 모두 absent로 유지됨
- `reports/NATIVE_INIT_V791_CURRENT_WARNING_ROUTE_CLASSIFIER_2026-05-25.md` – V791 결과 current `pm_qos_add_request` warning은 Android에서도 WLFW까지 진행 가능한 known ASoC signature로 분류되어 1차 blocker에서 제외
- `reports/NATIVE_INIT_V790_CLEAN_DSP_LOWER_ONLY_2026-05-25.md` – V790 결과 CNSS 없이 lower-only에서도 동일 `pm_qos_add_request` warning이 재현되어 원인을 clean-DSP/current prep/lower companion/audio deferred-probe 조합으로 좁힘
- `reports/NATIVE_INIT_V789_V788_WARNING_CLASSIFIER_2026-05-25.md` – V789 결과 V788 warning은 service-notifier 이후 ADSP/APR audio deferred probe의 `pm_qos_add_request` duplicate boundary로 분류되어 V790 lower-only clean-DSP replay로 라우팅
- `reports/NATIVE_INIT_V788_CLEAN_DSP_LOWER_READBACK_2026-05-25.md` – V788 결과 clean-DSP/V401/V490/CNSS-only lower readback은 조합됐지만 `pm_qos_add_request` warning boundary가 발생해 HAL/scan/connect로 widening하지 않고 V789 host-only warning classifier로 라우팅
- `reports/NATIVE_INIT_V779_BPF_LOADER_BUILD_2026-05-25.md` – V779 결과 `a90_bpf_trace_probe v779` minimal static aarch64 helper를 build-only로 생성하고 no-INTERP, `--check-only`, `--allow-attach` safety marker를 검증
- `reports/NATIVE_INIT_V778_BPF_ATTACH_FEASIBILITY_2026-05-25.md` – V778 결과 device에 `bpftool`/`bpftrace` loader가 없어 바로 attach하지 않고, host aarch64 static helper build surface가 준비됐음을 확인해 V779 custom minimal loader build gate로 라우팅
- `reports/NATIVE_INIT_V777_TRACEPOINT_FORMAT_CLASSIFIER_2026-05-25.md` – V777 결과 `msm_pil_event:pil_notif` 등 5개 후보 tracepoint format을 읽어 event-specific field를 확인하고, V778 후보를 `msm_pil_event:pil_notif` idle attach/read/detach proof로 선정
- `reports/NATIVE_INIT_V776_TRACEPOINT_INVENTORY_2026-05-25.md` – V776 결과 recovered v724 stock kernel에서 tracefs `available_events=1250`와 후보 event 153개를 확인했고, `msm_pil_event:*`, `dfc:dfc_qmi_tc`, `cfg80211:cfg80211_report_wowlan_wakeup` 등을 V777 format 분류 후보로 선정
- `reports/NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_2026-05-25.md` – V775 결과 V773/V774로 DTB tail 누락은 단독 원인이 아님을 확인하고, pre-DTB `+16` byte delta, kernel provenance/toolchain, RKP/RTIC marker delta를 남은 custom-kernel boot incompatibility 후보로 분류
- `reports/NATIVE_INIT_V774_STOCK_DTB_TAIL_LIVE_BOOT_FAIL_2026-05-25.md` – V774 결과 stock v724 appended DTB tail을 붙인 V773 diagnostic image도 TWRP flash/readback 이후 native verify에 도달하지 못했으며, v724 rollback 후 native `version/status`와 `selftest` 통과로 복구 완료
- `reports/NATIVE_INIT_V773_STOCK_DTB_TAIL_REPACK_2026-05-25.md` – V773 결과 V769 계측 payload에 stock v724 appended DTB tail을 붙여 FDT 3개, `A90V765` marker 19개, roundtrip hash를 local-only로 검증
- `reports/NATIVE_INIT_V772_BOOT_INCOMPAT_CLASSIFIER_2026-05-25.md` – V772 결과 known-good v724 kernel payload에는 appended FDT/DTB 3개가 있지만 V770 diagnostic payload에는 FDT가 없어 boot failure의 유력 원인을 DTB tail 누락으로 분류
- `reports/NATIVE_INIT_V771_ROLLBACK_RECOVERY_2026-05-25.md` – V771 rollback 결과 `stage3/boot_linux_v724.img` flash/readback 후 native `version/status`, `bootstatus`, `selftest` 통과로 복구 완료 확인
- `reports/NATIVE_INIT_V771_DIAGNOSTIC_LIVE_HANDOFF_BOOT_FAIL_2026-05-25.md` – V771 결과 V770 diagnostic image의 TWRP flash/readback은 성공했지만 reboot 후 native verify에 도달하지 못하고 Download mode로 빠져 rollback 필요 상태로 분류
- `reports/NATIVE_INIT_V770_INSTRUMENTED_DIAGNOSTIC_BOOT_STAGING_2026-05-25.md` – V770 결과 V769 계측 kernel을 local diagnostic boot image로 repack하고 kernel roundtrip hash, native-init marker, `A90V765` marker 19개를 검증
- `reports/NATIVE_INIT_V769_RKP_CFP_PYTHON3_PACKAGING_2026-05-25.md` – V769 결과 RKP_CFP Python3 repair 후 ICNSS/QCACLD 계측 `Image`와 `Image-dtb` 생성, 19개 `A90V765` marker 보존, live/device/Wi-Fi action 미실행을 확인
- `reports/NATIVE_INIT_V768_MDM3_ESOC_GAP_CLASSIFIER_2026-05-25.md` – V768 결과 service180-gated `mdm_helper`, raw esoc0, blind `boot_wlan` retry를 현 증거 기준으로 닫고 V769 RKP_CFP/Python2 packaging gate를 다음 후보로 선정
- `reports/NATIVE_INIT_V767_ICNSS_QCACLD_FULL_BUILD_2026-05-25.md` – V767 결과 ICNSS/QCACLD 계측 객체 5개가 빌드되고 19개 `A90V765` marker가 보존됐지만 final `Image`는 post-link `RKP_CFP` Python2 blocker로 분리됨
- `reports/NATIVE_INIT_V766_ICNSS_QCACLD_PATCH_APPLY_BUILD_2026-05-25.md` – V766 결과 V765 patch formatting을 수정한 뒤 disposable source apply, 19개 marker 검증, `r3q_kor_single_defconfig` 통과를 확인하고 full build는 toolchain gate로 분리
- `reports/NATIVE_INIT_V765_ICNSS_QCACLD_LOG_PATCH_2026-05-24.md` – V765 host-only 결과 `A90V765` ICNSS/QCACLD 로그 patch artifact를 생성했고 source/build/boot image/device mutation은 실행하지 않았음을 확인
- `reports/NATIVE_INIT_V764_SERVICE180_MDM_HELPER_RETRY_2026-05-24.md` – V764 live 결과 service `180` gate에서 `mdm_helper`는 시작됐지만 mdm3/WLFW/BDF/`wlan0` 진전은 없어 `mdm_helper`를 즉시 trigger 후보에서 닫음
- `reports/NATIVE_INIT_V763_ICNSS_ARCH_REBASE_2026-05-24.md` – V763 host-only 결과 SM-A908N live path는 ICNSS/QCACLD SNOC이며 instrumentation target을 ICNSS QMI/core, PLD-SNOC, HDD로 재고정
- `reports/NATIVE_INIT_V762_SOURCE_TARGET_VERIFICATION_2026-05-24.md` – V762 host-only 결과 staged OSRC `Kernel.tar.gz`에서 live ICNSS/QCACLD target groups가 확인되어 source acquisition blocker를 해제
- `reports/NATIVE_INIT_V761_SOURCE_DOWNLOAD_HANDOFF_2026-05-24.md` – V761 결과 공식 OSRC download/staging handoff script를 생성했고 브라우저 open은 opt-in으로 유지
- `reports/NATIVE_INIT_V760_SOURCE_STAGING_2026-05-24.md` – V760 결과 source staging verifier가 archive/tree 구조와 target file availability를 분류하도록 준비됨
- `reports/NATIVE_INIT_V759_SOURCE_ACQUISITION_2026-05-24.md` – V759 결과 SM-A908N/A908NKSU5EWA3 official OSRC package와 source upload id를 특정
- `reports/NATIVE_INIT_V758_KERNEL_INSTRUMENTATION_FEASIBILITY_2026-05-24.md` – V758 결과 boot-image tooling은 있으나 exact source가 없어 instrumentation은 source acquisition 전까지 차단됨을 확인
- `reports/NATIVE_INIT_V757_ANDROID_NATIVE_HDD_PLD_DIFF_2026-05-24.md` – V757 결과 기존 Android/native dmesg만으로 PLD/HDD/register-driver 경계를 닫기 어려워 source-backed log instrumentation을 선택
- `reports/NATIVE_INIT_V756_NONFTRACE_HDD_PLD_OBSERVABILITY_2026-05-24.md` – V756 결과 dynamic debug/kprobe/live observers가 현재 kernel state에서 usable하지 않아 non-ftrace source path로 이동
- `reports/NATIVE_INIT_V755_TRACEFS_MOUNT_FILTER_PROOF_2026-05-24.md` – V755 live 결과 tracefs mount/cleanup은 가능하지만 `available_filter_functions`/function filter target이 없어 ftrace 경로는 현재 blocker에 쓸 수 없음을 확인
- `reports/NATIVE_INIT_V754_HDD_PLD_TRACEABILITY_SELECTOR_2026-05-24.md` – V754 read-only 결과 tracefs와 kallsyms 표면은 있으나 tracefs가 미마운트라 V755 bounded mount/filter proof가 필요함을 확인
- `reports/NATIVE_INIT_V753_HDD_PLD_PREREQ_CLASSIFIER_2026-05-24.md` – V753 read-only 결과 V752는 HDD entry/qcwlanstate 생성까지만 증명하고 PLD/hdd_init/register-driver 중 어디서 멈췄는지는 추가 instrumentation 없이는 구분되지 않음을 확인
- `reports/NATIVE_INIT_V752_CNSS_THEN_BOOT_WLAN_2026-05-24.md` – V752 live 결과 `cnss_diag`/`cnss-daemon`을 먼저 시작한 뒤 `boot_wlan`을 실행해도 HDD/qcwlanstate 경계에서 계속 정지하고 driver-loaded/ICNSS-QMI/FW-ready/netdev는 absent임을 확인
- `reports/NATIVE_INIT_V751_ICNSS_MODULE_INIT_CLASSIFIER_2026-05-24.md` – V751 read-only 결과 `boot_wlan`은 QCACLD/HDD init에 진입해 `qcwlanstate`를 만들지만 driver-loaded/ICNSS-QMI/FW-ready/netdev 전 단계에서 정지함을 확인
- `reports/NATIVE_INIT_V750_LOWER_WINDOW_BOOT_WLAN_2026-05-24.md` – V750 live 결과 lower-ready window 안에서 `boot_wlan` write는 성공했지만 `qcwlanstate=OFF`, `/dev/wlan`/wiphy/`wlan0`/WLFW/service69/BDF는 absent라 ICNSS modules-initialized path가 다음 blocker임을 확인
- `reports/NATIVE_INIT_V749_NONBIND_TRIGGER_SELECTOR_2026-05-24.md` – V749 read-only 결과 current native에는 `fs_ready`가 없고 standalone `boot_wlan`/`qcwlanstate`는 이미 부족했으므로 V750 후보를 lower-ready window 안의 bounded `boot_wlan` proof로 선정
- `reports/NATIVE_INIT_V748_NONBIND_POWERUP_TRIGGER_2026-05-24.md` – V748 host-only 결과 bind/unbind, `mdm_helper`, CNSS/HAL retry, vendor namespace, `wlan` module load 후보를 닫고 다음 gate를 read-only non-bind ICNSS/QCA WLFW trigger capture로 선정
- `reports/NATIVE_INIT_V747_QCA6390_DRIVER_BINDING_DELTA_2026-05-24.md` – V746/V715/V716/V703 증거를 host-only로 묶어 QCA6390 child driver-link gap은 재현되지만 bind/unbind 대상이 아니며 다음은 non-bind ICNSS/QCA power-up trigger 분류임을 확인
- `reports/NATIVE_INIT_V746_SYSMON_GATED_MDM_HELPER_LIVE_2026-05-24.md` – helper v124 배포 후 `sysmon-qmi` gate가 열려 `mdm_helper`는 시작됐지만 mdm3/MHI/WLFW/`wlan0` 진전이 없고 QCA6390 platform device driver link가 비어 있음을 확인
- `reports/NATIVE_INIT_V746_SYSMON_GATED_MDM_HELPER_PREP_2026-05-24.md` – helper v124에 `sysmon-qmi` gated `mdm_helper` mode를 추가했고 static build, V746 plan, v124 deploy preflight가 통과했으며 이후 live로 검증됨
- `reports/NATIVE_INIT_V745_SERVICE180_GATED_MDM_HELPER_LIVE_2026-05-24.md` – helper v123 배포 후 V745 live를 실행했지만 service `180` gate가 열리지 않아 `mdm_helper`는 시작되지 않았고, QRTR TX/sysmon까지만 재현됨
- `reports/NATIVE_INIT_V745_SERVICE180_GATED_MDM_HELPER_PREP_2026-05-24.md` – helper v123에 service `180` gated `mdm_helper` mode를 추가했고 static build, V745 plan, v123 deploy preflight가 통과했으며 이후 live로 검증됨
- `reports/NATIVE_INIT_V744_V122_CNSS_ONLY_COMPARISON_2026-05-24.md` – V735 CNSS-only 경로를 helper v122로 재실행해 QRTR TX/sysmon/service-notifier는 재현되고 MHI/WLFW/`wlan0`는 여전히 absent임을 확인했으며, V743 gate miss를 helper v122 자체 문제와 분리
- `reports/NATIVE_INIT_V743_V741_CURRENT_LIVE_EXECUTION_2026-05-24.md` – V741 gated `mdm_helper` proof를 현재 부팅에서 실행했지만 service `74` gate가 열리지 않아 `mdm_helper`는 시작되지 않았고, 안전 경계와 postflight는 통과
- `reports/NATIVE_INIT_V742_EXECNS_HELPER_V122_DEPLOY_2026-05-24.md` – helper v122를 serial chunk `1850`으로 `/cache/bin/a90_android_execns_probe`에 배포했고 remote hash/marker 및 V741 plan rerun이 통과
- `reports/NATIVE_INIT_V742_EXECNS_HELPER_V122_DEPLOY_PREP_2026-05-24.md` – V742 helper v122 deploy wrapper/preflight가 통과했고, auto menu `busy`를 deploy blocker로 승격했으며 실제 배포는 다음 run 단계
- `reports/NATIVE_INIT_V741_MDM_HELPER_GATED_LIVE_2026-05-24.md` – helper v122가 service `74` gate 뒤 `/vendor/bin/mdm_helper`만 추가하는 V741 start-only proof를 구현했고, plan/static 검증은 통과했으며 live는 helper v122 배포 후 실행 예정
- `reports/NATIVE_INIT_V740_MDM_HELPER_BASEBAND_CONTRACT_2026-05-24.md` – V740 host-only 결과 Android `mdm_helper`는 service `180` 이후/WLAN-PD 이전에 시작되므로 first-trigger가 아니라 bounded post-notifier candidate이며 V741은 gated start-only proof로 진행
- `reports/NATIVE_INIT_V739_MDM3_WLANPD_DELTA_2026-05-24.md` – V739 host-only 결과 Android는 `mss/mdm3=ONLINE`과 WLAN-PD/WLFW/BDF/`wlan0`를 갖지만 native V738은 `mss=ONLINE, mdm3=OFFLINING`과 no-MHI/WLFW라 다음은 `mdm_helper`/baseband contract 분류
- `reports/NATIVE_INIT_V738_MODEM_WLAN_MHI_OBSERVER_2026-05-24.md` – V738 live 결과 `mss`는 `ONLINE`까지 가지만 `mdm3`는 `OFFLINING`으로 남고 QCA6390 driver/MHI/WLFW/service `69`/BDF/`wlan0`가 없어 다음은 Android/native `mdm3`/WLAN-PD lower trigger delta
- `reports/NATIVE_INIT_V737_CNSS2_ARCH_REBASE_2026-05-24.md` – V737 host-only 결과 service `180/74` publication은 side evidence이고 V721에서 이미 service-positive/no-WLFW 갭이 확인됐으므로 다음은 real vendor firmware namespace + modem/WLAN/MHI prerequisite observer
- `reports/NATIVE_INIT_V736_SERVICE180_TO_MHI_GAP_2026-05-24.md` – V736 host-only 결과 native는 service `180`까지 도달하지만 Android의 service `74`/WLAN-PD/MHI/WLFW/service `69`/BDF/`wlan0`로 이어지지 않고 QCA6390도 unbound라 다음은 lower service-74/WLAN-PD publisher trigger 분류
- `reports/NATIVE_INIT_V735_CURRENT_CNSS_ONLY_OBSERVER_2026-05-24.md` – V735 live 결과 current-build CNSS-only replay가 `service_notifier=1`까지 진전했지만 WLAN-PD/MHI/QCA6390/WLFW/service `69`/BDF/`wlan0`는 absent라 다음은 WLAN-PD/service-publication-to-MHI gap 분류
- `reports/NATIVE_INIT_V734_CURRENT_POST_SYSMON_ROUTE_2026-05-24.md` – V734 host-only 결과 current V733 lower-only는 QRTR TX/sysmon까지만 복원하고, V625/V627 safe CNSS-only class가 service `180`을 만든 전례가 있어 다음은 current-build CNSS-only replay
- `reports/NATIVE_INIT_V733_HOLDER_LOWER_COMPANION_2026-05-24.md` – V733 live 결과 lower companion/TFTP 4개가 `mss=ONLINE`, QRTR RX/TX, modem `sysmon-qmi`까지 복원했지만 service-notifier/WLFW/service `69`/BDF/`wlan0`는 absent라 다음은 post-sysmon publication gap host-only 분류
- `reports/NATIVE_INIT_V732_CNSS2_MHI_HOLDER_WINDOW_2026-05-24.md` – V732 live 결과 firmware-mounted `subsys_modem` holder가 `mss=ONLINE`과 QRTR RX를 재현했지만 QRTR TX/sysmon/rpmsg/MHI/QCA6390/WLFW/service `69`/BDF/`wlan0`가 모두 absent라 다음은 real vendor-root + lower companion/TFTP gate
- `reports/NATIVE_INIT_V731_FIRMWARE_MOUNTED_MODEM_HOLDER_2026-05-24.md` – V731 live 결과 current V724에서 read-only firmware mount + `subsys_modem` holder가 `mss=ONLINE`과 QRTR RX를 복원했고, `esoc0`/daemon/HAL/scan/connect 없이 reboot cleanup pass라 다음은 같은 창에서 CNSS2/MHI read-only 관측
- `reports/NATIVE_INIT_V730_MODEM_TRIGGER_RECONCILE_2026-05-24.md` – V730 read-only 결과 현재 global `/vendor/firmware_mnt`, `/vendor/firmware-modem`, `/firmware`와 `modem.b00`가 모두 absent라 V729는 no-firmware open-pending 재현으로 분류되고, V731은 current-build read-only firmware mount + `subsys_modem` holder gate가 다음
- `reports/NATIVE_INIT_V729_MODEM_ONLY_HOLD_2026-05-24.md` – V729 live 결과 `subsys_modem` 임시 cdev open attempt는 bounded window 동안 pending/blocking 상태로 남고 `mss/mdm3`는 계속 `OFFLINING`, QRTR/sysmon/MHI/WLFW/BDF/`wlan0`는 0이라 다음은 Android `mdm_helper`/ioctl/property trigger 비교
- `reports/NATIVE_INIT_V728_PRIVATE_VENDOR_ROOT_2026-05-24.md` – V728 live 결과 기존 helper `v121`이 private namespace에서 `sda29`를 `/vendor`로 마운트하고 `/vendor/bin/cnss-daemon`을 볼 수 있으며, 같은 `sda29`에 Wi-Fi firmware가 있음을 상관시켜 V729 safe modem ONLINE trigger proof가 다음
- `reports/NATIVE_INIT_V727_LOWER_PREREQ_2026-05-24.md` – V727 live 결과 current `/vendor -> /mnt/system/vendor`에는 Wi-Fi firmware가 없지만 isolated `sda29` vendor에는 `wlanmdsp.mbn`, `bdwlan.bin`, `regdb.bin`이 있고, `wlan`은 loadable `/proc/modules` 항목이 아니라 static parameter surface로 보여 V728 private vendor root layout proof가 다음
- `reports/NATIVE_INIT_V726_CNSS2_PCIE_PREREQ_2026-05-24.md` – V726 read-only 결과 SM8250 CNSS2는 service `180/74` 중심이 아니라 modem ONLINE + WLAN module/load-state + MHI/QCA6390/WLFW 경로로 봐야 하며, 현재는 `mss/mdm3=OFFLINING`, `/proc/modules`에 `wlan` 없음, `wlanmdsp` 미발견으로 V727 lower-prereq gate가 다음
- `reports/NATIVE_INIT_V725_SERVLOC_MODEM_QMI_GAP_2026-05-24.md` – V725 host-only 결과 V724는 service-locator를 boot window에서 연결했지만 native에는 QRTR RX/TX, sysmon, ONLINE modem/mdm3, rpmsg devices, service `180/74`가 없음을 확인했고, V726에서 이를 SM8250 CNSS2 lower-prereq gap으로 재해석
- `reports/NATIVE_INIT_V724_QRTR_SERVICE_LOCATOR_BOOT_PROOF_LIVE_2026-05-24.md` – post-ACM one-shot V724 boot hook은 service-locator를 4.408초에 연결하고 기존 `servloc` timeout을 제거했지만 service `180/74`/CNSS2/WLFW/`wlan0`는 여전히 없어 다음 gate를 SERVREG/WLAN-PD publication gap으로 고정
- `reports/NATIVE_INIT_V723_QRTR_SERVICE_LOCATOR_REARM_LIVE_2026-05-24.md` – lower-only `qrtr-ns`/`pd-mapper`/`rmt_storage`/`tftp_server` late rearm은 service-locator 재연결까지만 만들고 service `180/74`/CNSS2/WLFW/`wlan0`는 복구하지 못해 다음 gate를 boot-time lower companion proof로 고정
- `reports/NATIVE_INIT_V722_CNSS_LAUNCH_WINDOW_2026-05-24.md` – early native CNSS는 binder failure를 만들고 provider-first native CNSS는 그 failure를 제거하지만 Android WLFW timing보다 늦게 `cnss-daemon`을 시작함을 확인해 다음 gate를 provider-preserving earlier CNSS retry로 고정
- `reports/NATIVE_INIT_V721_SERVREG_CNSS2_DELTA_2026-05-24.md` – Android는 service `180/74` 이후 WLAN-PD/QMI/BDF/fw-ready/`wlan0`까지 진행하지만 native V720은 `qrtr-ns`와 service `180/74` 이후 `SERVICE_STATE_UP`/WLAN-PD/CNSS2/QCA/WLFW 진행이 없어 다음 gate를 SERVREG/CNSS2 callback 관측으로 고정
- `reports/NATIVE_INIT_V720_SAME_WINDOW_CNSS2_OBSERVER_LIVE_2026-05-24.md` – V720 live 결과 `qrtr-ns`와 service `180/74`는 확인됐지만 `SERVICE_STATE_UP`/`wlan_pd`/CNSS2 pd-notifier/QCA power/WLFW/BDF/`wlan0`가 모두 없어 같은 창 CNSS2 trigger gap을 확정
- `reports/NATIVE_INIT_V719_CNSS2_SERVICE_POSITIVE_RECONCILE_2026-05-24.md` – V717 same-window service `180/74` 양성 증거에는 CNSS2 pd-notifier/QCA power/MHI/WLFW/`wlan0` 진행이 없고, V718 post-cleanup current boot는 lower-not-ready라 다음은 same-window CNSS2/SERVREG 관측 gate임을 확정
- `reports/NATIVE_INIT_V718_CNSS2_PD_NOTIFIER_CURRENT_HARDENING_2026-05-24.md` – V706 read-only classifier에 menu busy 차단과 QCA power/MHI 마커 정밀화를 추가하고, 현재 부팅은 service `180/74` 부재 + `mss`/`mdm3` `OFFLINING` 상태라 lower modem/WLAN-PD readiness 복원이 먼저임을 재확인
- `reports/NATIVE_INIT_V717_ICNSS_EDGE_LONG_OBSERVE_2026-05-24.md` – V712 helper v121 provider-first ICNSS edge proof를 30초 observation window로 재실행해 service `180/74`와 provider/CNSS retry는 재현되지만 WLFW/BDF/`wlan0`는 여전히 0임을 확인
- `reports/NATIVE_INIT_V716_QCA_BIND_RECONCILIATION_2026-05-24.md` – V715의 QCA6390 child-unbound는 사실이나 V703 Android reference가 QCA bind/unbind target을 거부하므로 다음 live gate를 ICNSS-QMI/WLFW readiness trigger로 재고정
- `reports/NATIVE_INIT_V715_ICNSS_EDGE_SURFACE_CLASSIFIER_2026-05-24.md` – V714/V712 edge evidence를 host-only 분류한 결과 service `180/74` window에서 ICNSS parent는 bound지만 QCA6390 platform child가 unbound임을 확인했고, V716에서 QCA bind/unbind가 아닌 ICNSS-QMI/WLFW edge로 재라우팅
- `reports/NATIVE_INIT_V714_HELPER_V121_ICNSS_EDGE_LIVE_2026-05-24.md` – helper v121을 serial safe chunk로 배포하고 V712 provider-first ICNSS edge proof를 실행했으며, WLFW/BDF/`wlan0` 미진입과 top-level orchestrator summary 보정 내용을 기록
- `reports/NATIVE_INIT_V713_V666_CNSS2_PD_NOTIFIER_CURRENT_2026-05-24.md` – V666 read-only CNSS2 pd-notifier check를 현재 부팅에서 재실행한 결과 service `180/74` 자체가 없어 현 부팅은 lower modem/WLAN-PD readiness 복원이 먼저이며, service-positive 경로는 V712 helper v121 edge capture로 계속 진행
- `reports/NATIVE_INIT_V712_EXECNS_HELPER_V121_ICNSS_EDGE_PREP_2026-05-24.md` – V712 prep 결과 helper v121 static build/strings 계약과 V712 provider-first/deploy preflight wrapper가 통과했고 실제 배포와 live proof가 다음 gate
- `reports/NATIVE_INIT_V711_ICNSS_EDGE_READONLY_LIVE_2026-05-24.md` – V711 live read-only 결과 현재 ICNSS core는 bound, QCA6390 context는 visible/unbound, `wlan0`는 absent라 다음 V712를 ICNSS-QMI/WLFW event-source window capture로 선정
- `reports/NATIVE_INIT_V710_KERNEL_EVENT_SOURCE_CLASSIFIER_2026-05-24.md` – V710 host-only 결과 service `180/74` + provider + CNSS retry poll wait 이후 QCA6390은 visible/unbound이고 WLFW/BDF/`wlan0`가 없어 다음 target을 QCA6390 bind/power/MHI-or-ICNSS edge로 분류
- `reports/NATIVE_INIT_V709_V708_STALL_CLASSIFIER_2026-05-24.md` – V709 host-only 결과 v120 stall snapshot에서 `cnss-daemon` retry가 service `180/74`와 provider 등록 후 `poll/futex` 대기 중이라 다음은 kernel CNSS/WLFW event source 분류
- `reports/NATIVE_INIT_V708_PROVIDER_FIRST_CNSS_V120_STALL_LIVE_2026-05-24.md` – V708 live 결과 helper v120 provider-first path가 service `180/74`, provider 등록, post-provider CNSS retry, stall snapshot을 모두 통과했지만 WLFW/BDF/`wlan0`는 여전히 0
- `reports/NATIVE_INIT_V707_LOWER_REPLAY_AND_V120_DEPLOY_2026-05-24.md` – V707 결과 V598-class replay는 QRTR/sysmon까지만 복원하고 service `180`은 미재현했으며 helper v120 deploy는 성공
- `reports/NATIVE_INIT_V706_CNSS2_PD_NOTIFIER_READONLY_LIVE_2026-05-24.md` – V706 live 결과 현재 부팅은 service-notifier `180`이 재현되지 않고 `mss`/`mdm3`가 `OFFLINING`이라 CNSS retry/HAL보다 lower modem/WLAN-PD readiness 복원이 선행되어야 함
- `reports/NATIVE_INIT_V705_EXECNS_HELPER_V120_STALL_CAPTURE_PREP_2026-05-24.md` – V705 prep 결과 helper v120이 `cnss_daemon_retry` live `wchan`/`syscall`/task/socket 관측성을 포함해 static build와 deploy preflight 통과
- `reports/NATIVE_INIT_V704_CNSS_RETRY_STALL_SNAPSHOT_2026-05-24.md` – V704 결과 provider-first `cnss-daemon` retry는 alive/sleeping + vndbinder/socket fd 상태로 WLFW 전에서 멈추므로 다음은 live `wchan`/`syscall`/task/socket inode stall capture
- `reports/NATIVE_INIT_V703_ANDROID_NATIVE_BINDING_COMPARE_2026-05-24.md` – V703 결과 Android는 ICNSS parent 아래 `wlan0`와 WLFW/BDF/fw-ready까지 진행하지만 native는 ICNSS-QMI/WLFW 전에서 멈추므로 다음 target은 `qca6390` bind가 아니라 ICNSS/WLFW readiness edge
- `reports/NATIVE_INIT_V702_CNSS2_FOCUS_SURFACE_CLASSIFIER_2026-05-24.md` – V702 결과 `icnss`는 bound, `qca6390` node는 visible이지만 driver symlink가 없고 `wlan0`/debug ICNSS/WLFW/BDF가 없어 다음은 Android-vs-native binding 비교
- `reports/NATIVE_INIT_V701_PRE_WLFW_TRIGGER_CLASSIFIER_2026-05-24.md` – V701 결과 V700의 provider-first CNSS retry는 Binder 실패 없이 netlink/`cld80211`까지만 도달하고 ICNSS/QCA/WLFW/BDF/`wlan0`가 없어 다음은 V702 read-only platform-state capture
- `reports/NATIVE_INIT_V700_PROVIDER_FIRST_CNSS_LIVE_2026-05-24.md` – V700 live 결과 초기 pre-provider CNSS를 억제한 상태에서 provider 등록과 post-provider CNSS retry는 통과했지만 WLFW/BDF/`wlan0`는 여전히 0이라 다음은 pre-WLFW trigger classifier
- `reports/NATIVE_INIT_V699_PROVIDER_FIRST_CNSS_HELPER_2026-05-24.md` – V699 helper-build 결과 `a90_android_execns_probe v119`에 provider-first initial-suppressed CNSS 모드를 추가했고 다음은 helper v119 배포 후 bounded live proof
- `reports/NATIVE_INIT_V698_CNSS_RETRY_ATTRIBUTION_2026-05-24.md` – V698 host-only 결과 Binder `29189/-22`는 초기 pre-provider `cnss-daemon` pid에 귀속되고 post-provider retry는 Binder fail 없이 netlink 뒤 WLFW 전 정지로 분류되어 다음은 provider-first initial-suppressed CNSS live gate
- `reports/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_2026-05-25.md` – V867 bounded live 결과 PM init-contract markers/ioprio/lifecycle은 실행됐지만 `pm_proxy_helper` D-state 잔류로 reboot cleanup이 필요함을 분류
- `reports/NATIVE_INIT_V866_HELPER_V134_DEPLOY_2026-05-25.md` – V866 deploy-only 결과 helper `v134`를 serial 1850-byte chunk로 `/cache/bin`에 배포하고 remote sha/usage/selftest/actor-clean 상태 확인
- `reports/NATIVE_INIT_V865_PM_INIT_CONTRACT_HELPER_BUILD_2026-05-25.md` – V865 source/build-only 결과 helper `v134`에 `pm_proxy_helper`, `ioprio rt 4`, `init.svc.vendor.per_mgr=running`, shutdown-stop 모델을 추가하고 static ARM64 build 및 classifier source-support pass 확인
- `reports/NATIVE_INIT_V864_PM_INIT_CONTRACT_SUPPORT_2026-05-25.md` – V864 host-only 결과 helper가 `pm_proxy_helper`, `ioprio rt 4`, `init.svc.vendor.per_mgr=running`, shutdown-stop 모델을 아직 지원하지 않아 V865 source/build-only 구현으로 라우팅
- `reports/NATIVE_INIT_V863_PM_PROXY_HELPER_RC_CAPTURE_2026-05-25.md` – V863 live 결과 `vendor.per_proxy_helper`가 `post-fs-data`에서 시작되는 disabled/oneshot `system:system` 서비스임을 read-only로 캡처
- `reports/NATIVE_INIT_V862_ANDROID_INIT_SERVICE_CONTRACT_2026-05-25.md` – V862 host-only 결과 `vendor.per_mgr` ioprio/lifecycle 및 Android-started `vendor.per_proxy_helper` 계약 누락을 분류하고 V863 read-only rc capture로 라우팅
- `reports/NATIVE_INIT_V861_PM_SERVICE_DOMAIN_PARITY_2026-05-25.md` – V861 live 결과 `vendor_per_mgr` exec target은 accepted지만 runtime context는 `kernel`로 남고 `pm-service` subsystem fd hold는 여전히 미증명
- `reports/NATIVE_INIT_V860_PM_SERVICE_PROPERTY_SUPERSET_2026-05-25.md` – V860 live 결과 property denial은 0으로 정리됐지만 `pm-service` subsystem fd hold는 아직 미증명이라 다음은 lifetime/provider-input 분류
- `reports/NATIVE_INIT_V859_PM_SERVICE_PROPERTY_DELTA_REPLAY_2026-05-25.md` – V859 live 결과 V858 target denial 8개는 제거됐고 새 `vndservicemanager`/`ServiceManager`/`PerMgrLib` property gap으로 이동했으며 `pm-service` subsystem fd hold는 아직 미증명
- `reports/NATIVE_INIT_V858_PM_SERVICE_PROPERTY_CONTEXT_DELTA_2026-05-25.md` – V858 결과 V857 residual property key 8개를 Android property_context에 모두 매핑하고 private V535 property root에 델타 배포 및 device-side hash 검증 완료
- `reports/NATIVE_INIT_V697_CNSS_BINDER_RUNTIME_TARGET_2026-05-24.md` – V697 host-only 결과 provider 등록, `/dev/vndbinder`, `vndservicemanager`, CNSS SELinux preexec가 모두 확인되어 남은 블로커를 `cnss-daemon` vendor Binder transaction `29189/-22` framing/runtime 경로로 분류
- `reports/NATIVE_INIT_V696_POST_PROVIDER_RETRY_BLOCKER_CLASSIFIER_2026-05-24.md` – V696 host-only 결과 V695 provider-confirmed retry 이후에도 native-only CNSS Binder `-22`가 WLFW 전 primary blocker로 남고 duplicate `pm_qos`는 secondary signal로 분류
- `reports/NATIVE_INIT_V695_PROVIDER_CONFIRMED_CNSS_RETRY_LIVE_2026-05-24.md` – V695 live 결과 provider 등록 확인 뒤 fresh `cnss-daemon` retry tail은 실행됐지만 WLFW/BDF/`wlan0`는 여전히 0이라 다음은 post-provider retry blocker classifier
- `reports/NATIVE_INIT_V693_PERIPHERAL_REGISTRY_EVIDENCE_CLASSIFIER_2026-05-24.md` – V693 host-only 결과 `pm-service`는 `/dev/vndbinder`를 열고 exit 0, `pm-proxy`는 fd 0으로 exit 1이며 Binder debugfs가 없어 V692는 provider 등록 증명이 아니라 관측성 gap으로 분류
- `reports/NATIVE_INIT_V692_PERIPHERAL_REGISTRY_SNAPSHOT_LIVE_2026-05-24.md` – V692 live 결과 helper v116 registry snapshot 5단계가 모두 완료됐고 provider pair는 observable/ready 이후 observe window 전에 종료되어 다음은 `/dev/socket` registry와 provider stdout/stderr 분석
- `reports/NATIVE_INIT_V691_PERIPHERAL_POST_PROPERTY_EXIT_CLASSIFIER_2026-05-24.md` – V691 host-only 결과 property ack는 clean이고 `pm-service`는 vndbinder open 후 exit 0, `pm-proxy`는 exit 1, residual provider process는 0이라 다음은 targeted provider exit/registration capture
- `reports/NATIVE_INIT_V690_PERIPHERAL_PROPERTY_SHIM_ACK_2026-05-24.md` – V690 live 결과 helper v115 exact private property ack는 통과했고 `vendor.peripheral.*.state` set 실패는 제거됐지만 provider는 post-property runtime/registration gap으로 종료
- `reports/NATIVE_INIT_V689_PERIPHERAL_PROPERTY_SHIM_CLASSIFIER_2026-05-24.md` – V689 host-only 결과 V688의 property-service blocker는 exact private shim ack 후보 `vendor.peripheral.SDX50M.state=OFFLINE`와 `vendor.peripheral.modem.state=OFFLINE`로 좁혀져 다음은 helper v115
- `reports/NATIVE_INIT_V694_PERIPHERAL_VNDSERVICE_QUERY_LIVE_2026-05-24.md` – V694 live 결과 helper v117이 service `74` positive private namespace에서 `/vendor/bin/vndservice list`를 두 번 실행했고 `vendor.qcom.PeripheralManager` 등록을 확인했으며 다음은 provider-confirmed CNSS retry tail
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
