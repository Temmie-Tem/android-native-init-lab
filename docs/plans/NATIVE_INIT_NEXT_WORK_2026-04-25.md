# Native Init Next Work List (2026-04-25)

이 문서는 `A90 Linux init 0.8.1 (v70)` 기준 이후 작업을 정리한 실행 목록이다.

현재 단계는 넓은 의미의 리버싱도 포함하지만, 중심은 더 이상 Android 전체를
분해하는 것이 아니다. Stock Android kernel과 Samsung vendor driver 위에서
우리의 작은 native userspace, shell, display HUD, input/menu, log/runtime 계층을
만드는 단계다.

따라서 후속 작업은 아래 원칙으로 진행한다.

- 필요한 하드웨어/커널 경로만 역추적한다.
- 셸은 실험 도구이자 운영 콘솔로 안정화한다.
- 화면 HUD는 부팅 상태를 보이게 만드는 최소 UI로 발전시킨다.
- 저장소와 로그는 복구 가능한 영역부터 사용한다.
- ADB는 보류하고 USB ACM serial을 기준 제어 채널로 유지한다.

## 버전 표기 규칙

- numeric `MAJOR.MINOR.PATCH`는 native init / boot image version이다.
- `v###`는 project execution cycle이며 host tooling, 계획, 보고서, 검증 gate에도 사용한다.
- `v###`가 항상 새 boot image나 device flash를 뜻하지 않는다.
- 현재 예: native build `A90 Linux init 0.9.61`, device build tag `v319`, active execution cycle `v319`, device flash 완료.
- 상세 규칙: `docs/operations/VERSIONING_POLICY.md`

---

## 모듈화 설계 기준

v80/v81 이후 모듈화는 단순히 파일을 작게 나누는 작업이 아니라, PID 1이
실패했을 때 원인을 좁히고 복구 가능한 부팅 경로를 유지하기 위한 구조화 작업이다.
분리 기준은 아래 네 가지로 고정한다.

- **부팅 순서**: `init_main`은 PID 1 부팅 흐름만 보여 주고, 세부 구현은 모듈에 둔다.
- **책임 영역**: log, timeline, storage, console, shell, display, input, network를 섞지 않는다.
- **장애 영향 범위**: boot-critical 계층부터 작게 분리하고, UI/network/service는 안정화 후 분리한다.
- **의존성 방향**: 하위 계층인 util/log/timeline이 HUD, shell, menu 같은 상위 계층을 호출하지 않게 한다.

참고 구조:

- Linux initramfs: rootfs의 `/init`이 PID 1로 실행되며 이후 부팅을 책임진다.
  - https://docs.kernel.org/6.2/filesystems/ramfs-rootfs-initramfs.html
- Android init: early mount/dev/proc 준비와 first/second stage 흐름을 나눈다.
  - https://android.googlesource.com/platform/system/core.git/+/1350207265745ad3e5ee26017a0f8cc14dc268b8/init/README.md
- Buildroot/BusyBox init: 임베디드 환경에서는 작은 init과 service/run 구조가 실용적이다.
  - https://buildroot.org/downloads/manual/manual.html
- USB gadget configfs: ACM/NCM은 gadget function/config 조합이므로 USB gadget 제어와 network 정책을 분리한다.
  - https://www.kernel.org/doc/html/latest/usb/gadget_configfs.html
- DRM/KMS dumb buffer: early graphics에는 저수준 KMS와 drawing/HUD/menu 계층 분리가 적합하다.
  - https://www.kernel.org/doc/html/v4.8/gpu/drm-kms.html

목표 모듈 경계:

```text
init_main
  -> util / log / timeline / dev / storage
  -> console / shell / cmdproto / run
  -> metrics / kms / draw / hud / input / menu
  -> usb_gadget / netservice
  -> optional helpers / BusyBox / dropbear
```

`v114 HELPER DEPLOY 2`까지 실기 verified 완료했다. v106-v108은 UI/App Architecture split로 진행했고 ABOUT/changelog, displaytest/cutout, input monitor/layout UI를 각각 `a90_app_about.c/h`, `a90_app_displaytest.c/h`, `a90_app_inputmon.c/h`로 분리했다. v114 결과는
`docs/reports/NATIVE_INIT_V114_HELPER_DEPLOY_2026-05-04.md`에 둔다. v113 결과는
`docs/reports/NATIVE_INIT_V113_RUNTIME_PACKAGE_LAYOUT_2026-05-04.md`에 둔다. v112 결과는
`docs/reports/NATIVE_INIT_V112_USB_SERVICE_SOAK_2026-05-04.md`에 둔다. v111 결과는
`docs/reports/NATIVE_INIT_V111_EXTENDED_SOAK_RC_2026-05-04.md`에 둔다. v110 결과는
`docs/reports/NATIVE_INIT_V110_APP_CONTROLLER_CLEANUP_2026-05-04.md`에 둔다. v109 결과는
`docs/reports/NATIVE_INIT_V109_STRUCTURE_AUDIT_2026-05-04.md`에 둔다. v108 결과는
`docs/reports/NATIVE_INIT_V108_UI_APP_INPUTMON_2026-05-04.md`에 둔다. v107 결과는
`docs/reports/NATIVE_INIT_V107_UI_APP_DISPLAYTEST_2026-05-04.md`에 둔다. v106 결과는
`docs/reports/NATIVE_INIT_V106_UI_APP_ABOUT_2026-05-04.md`에 둔다. v105 결과는
`docs/reports/NATIVE_INIT_V105_SOAK_RC_2026-05-04.md`에 둔다. v104 결과는
`docs/reports/NATIVE_INIT_V104_WIFI_FEASIBILITY_2026-05-04.md`에 둔다. v103 결과는
`docs/reports/NATIVE_INIT_V103_WIFI_INVENTORY_2026-05-04.md`에 둔다. v102 결과는
`docs/reports/NATIVE_INIT_V102_DIAGNOSTICS_2026-05-03.md`에 둔다. v101 결과는
`docs/reports/NATIVE_INIT_V101_SERVICE_MANAGER_2026-05-03.md`에 둔다. v100 결과는
`docs/reports/NATIVE_INIT_V100_REMOTE_SHELL_2026-05-03.md`에 둔다. v99 결과는
`docs/reports/NATIVE_INIT_V99_BUSYBOX_USERLAND_2026-05-03.md`에 둔다. v98 결과는
`docs/reports/NATIVE_INIT_V98_HELPER_DEPLOY_2026-05-03.md`에 둔다. v97 결과는
`docs/reports/NATIVE_INIT_V97_SD_RUNTIME_ROOT_2026-05-03.md`에 둔다. v96 결과는
`docs/reports/NATIVE_INIT_V96_STRUCTURE_AUDIT_2026-05-03.md`에 둔다. v95 결과는
`docs/reports/NATIVE_INIT_V95_NETSERVICE_USB_API_2026-05-03.md`에 둔다. v94 결과는
`docs/reports/NATIVE_INIT_V94_BOOT_SELFTEST_API_2026-05-03.md`에 둔다.
v96-v105 장기 로드맵은
`docs/plans/NATIVE_INIT_LONG_TERM_ROADMAP_2026-05-03.md`를 기준으로 한다.
v103 상세 계획은
`docs/plans/NATIVE_INIT_V103_WIFI_INVENTORY_PLAN_2026-05-04.md`에 둔다.
v104 상세 계획은
`docs/plans/NATIVE_INIT_V104_WIFI_FEASIBILITY_PLAN_2026-05-04.md`에 둔다.
v105 상세 계획은
`docs/plans/NATIVE_INIT_V105_SOAK_RC_PLAN_2026-05-04.md`에 둔다.
v102 상세 계획은
`docs/plans/NATIVE_INIT_V102_DIAGNOSTICS_PLAN_2026-05-03.md`에 둔다. v101 상세 계획은
`docs/plans/NATIVE_INIT_V101_SERVICE_MANAGER_PLAN_2026-05-03.md`에 둔다. v100 상세 계획은
`docs/plans/NATIVE_INIT_V100_REMOTE_SHELL_PLAN_2026-05-03.md`에 둔다. v99 상세 계획은
`docs/plans/NATIVE_INIT_V99_BUSYBOX_USERLAND_PLAN_2026-05-03.md`에 둔다.
v96 상세 계획과 결과는
`docs/plans/NATIVE_INIT_V96_STRUCTURE_AUDIT_PLAN_2026-05-03.md`,
`docs/reports/NATIVE_INIT_V96_STRUCTURE_AUDIT_2026-05-03.md`에 둔다.
v97 상세 계획은
`docs/plans/NATIVE_INIT_V97_SD_RUNTIME_ROOT_PLAN_2026-05-03.md`에 둔다. v98 상세 계획과 결과는
`docs/plans/NATIVE_INIT_V98_HELPER_DEPLOY_PLAN_2026-05-03.md`,
`docs/reports/NATIVE_INIT_V98_HELPER_DEPLOY_2026-05-03.md`에 둔다.
v93 계획과 결과는
`docs/plans/NATIVE_INIT_V93_STORAGE_API_PLAN_2026-05-02.md`,
`docs/reports/NATIVE_INIT_V93_STORAGE_API_2026-05-02.md`에 둔다.
v92 계획과 결과는 `docs/plans/NATIVE_INIT_V92_SHELL_CONTROLLER_PLAN_2026-05-02.md`,
`docs/reports/NATIVE_INIT_V92_SHELL_CONTROLLER_API_2026-05-02.md`에 둔다.
shell/cmdproto 착수 지도와 실행 계획은 각각 `docs/reports/NATIVE_INIT_V83_CONSOLE_SHELL_CMDPROTO_DEPENDENCY_MAP_2026-04-29.md`,
`docs/plans/NATIVE_INIT_V84_SHELL_CMDPROTO_PLAN_2026-04-29.md`에 보존한다.

---

## 프로젝트 목표 재정의

현재 프로젝트의 목표는 `native Linux 진입 가능성 확인`이 아니라,
이미 확보한 진입점을 기반으로 **Android kernel 위에 작은 native Linux userspace를
직접 구성하는 것**이다.

목표 구조:

```text
Samsung bootloader
  -> stock Android Linux kernel
    -> custom static /init (PID 1)
      -> native runtime services
      -> serial shell
      -> KMS HUD/menu
      -> input/button control
      -> sysfs/proc/device map
      -> log/storage layer
      -> optional BusyBox/network/SSH
```

이 프로젝트에서 `서버처럼 사용한다`는 말은 처음부터 Debian 전체를 올린다는 뜻이 아니다.
우선 목표는 아래 조건을 만족하는 초소형 임베디드 Linux 콘솔이다.

- 부팅 진행과 실패 원인이 화면 또는 로그에 남는다.
- serial shell이 성공/실패를 신뢰 가능하게 보고한다.
- 외부 static binary를 실행하고 exit status를 확인할 수 있다.
- `/cache` 같은 안전한 저장소에 로그와 도구를 둘 수 있다.
- 파티션별 안전 등급을 구분해 Android/identity/security 영역을 실수로 덮어쓰지 않는다.
- 버튼만으로 최소한의 상태 확인과 recovery/poweroff 조작이 가능하다.
- 추후 USB network와 SSH/dropbear를 붙일 수 있는 runtime 구조를 가진다.

---

## 구현 범위와 비목표

현재 범위:

- custom `/init` 안정화
- shell/HUD/menu/log/runtime 구현
- 필요한 `/proc`, `/sys`, `/dev`, ioctl 경로 탐색
- safe storage와 boot recovery path 유지
- BusyBox 같은 static userland 검토
- USB serial 기반 운용

명시적 비목표:

- full POSIX shell 직접 구현
- Debian/Ubuntu 전체 배포판 즉시 포팅
- Android framework, Zygote, SurfaceFlinger 복구
- 커널 교체 또는 커널 드라이버 개발
- 카메라/모뎀/GPU 가속 같은 vendor userspace 의존 기능 지원
- `/efs`, RPMB, keymaster, modem 영역 쓰기

---

## 단계별 마일스톤

### M0. Native init 진입 확보 — 완료

- stock Android kernel 부팅
- custom static `/init` PID 1 실행
- USB ACM serial shell 확보
- KMS 화면 출력 확보
- 버튼 입력과 기본 sensor/sysfs 읽기 확보

### M1. 신뢰 가능한 native console

- shell return code 정밀화 — v40 완료
- command duration/result/errno 기록 — v40/v41 완료
- blocking command 취소 정책 통일 — v42 완료
- serial 반향/prompt 오염 방어

### M2. 관찰 가능한 boot/runtime

- `/cache/native-init.log` — v41 완료
- boot readiness timeline — v43 완료
- HUD boot progress/error 표시 — v44 완료
- safe storage/partition map 문서화 — v46 완료

### M3. 단독 운용 가능한 device UI

- 버튼 기반 on-screen menu — v47/v52 완료
- status/log/reboot/recovery/poweroff 조작 — v52 완료
- menu-active serial busy gate와 `hide` 요청 — v53 완료
- unsolicited `AT` serial noise filter — v59 완료
- serial 없이도 최소 복구 조작 가능 — 계속 검증

### M4. 작은 Linux userland

- static toybox 실행 — 완료
- `/cache/bin` 또는 ramdisk 기반 tool path — 완료
- process 실행, timeout, signal, zombie 회수 안정화 — 진행 중

### M5. 서버형 접근

- USB NCM probe — 완료
- USB NCM persistent link + IPv4/IPv6 ping + host→device netcat 검증 — 완료
- USB NCM 운영 helper + TCP nettest helper — 완료
- NCM TCP control helper — 완료
- TCP control host wrapper — 완료
- NCM + TCP control 5분 soak — 완료
- boot-time NCM/tcpctl netservice 정책 — v60 완료
- netservice stop/start software UDC reconnect recovery — v60 완료
- HUD CPU/GPU usage percent 표시 — v61 완료
- CPU stress usage gauge + `/dev/null`/`/dev/zero` guard — v62 완료
- 계층형 앱 메뉴 + CPU stress screen app — v63 완료
- TEST 부팅 화면을 custom boot splash로 교체 — v64 완료
- boot splash 잘림 방지 safe layout — v65 완료
- semantic version + ABOUT/changelog/credits app — v66 완료
- compact ABOUT typography + version별 changelog detail — v67 완료
- HUD log tail + expanded changelog history — v68 완료
- physical-button input gesture layout — v69 완료
- input monitor app + raw/gesture trace — v70 완료
- HUD/menu live log tail panel — v71 완료
- display test screen + framebuffer color fix — v72 완료
- cmdv1/A90P1 shell protocol + host wrapper — v73 완료
- cmdv1x length-prefixed argv encoding — v74 완료
- idle-timeout serial reattach log quieting — v75 완료
- AT fragment serial noise hardening — v76 완료
- display test multi-page app + cutout calibration — v77 완료
- ext4 SD workspace + `mountsd` storage manager — v78 완료
- boot-time SD health check + `/cache` fallback — v79 완료
- PID1 source layout split into include modules — v80 완료
- config/util true `.c/.h` base module extraction — v81 완료
- log/timeline true `.c/.h` API module extraction — v82 완료
- console true `.c/.h` API module extraction — v83 완료
- cmdproto true `.c/.h` API module extraction — v84 완료
- run/service true `.c/.h` API module extraction — v85 완료
- KMS/draw true `.c/.h` API module extraction — v86 완료
- input true `.c/.h` API module extraction — v87 완료
- HUD true `.c/.h` API module extraction — v88 완료
- menu control true `.c/.h` API module extraction + nonblocking `screenmenu` — v89 완료
- metrics true `.c/.h` API module extraction — v90 완료
- CPU stress external helper process separation — v91 완료
- shell/controller metadata and busy policy API extraction — v92 완료
- storage true `.c/.h` API module extraction — v93 완료
- boot selftest non-destructive module smoke test API — v94 완료
- netservice/USB gadget true `.c/.h` API module extraction — v95 완료
- structure audit/refactor debt cleanup — v96 완료
- SD runtime root promotion — v97 완료
- helper deployment/package manifest — v98 완료
- BusyBox static userland evaluation — v99 완료
- TCP shell/dropbear remote access prototype — v100 완료
- Minimal service manager command/view — v101 완료
- Diagnostics/log bundle command and host collector — v102 완료
- Wi-Fi read-only inventory — v103 완료
- Wi-Fi enablement feasibility — v104 완료, 현재 gate 결과 no-go/baseline-required
- long-run soak/recovery release candidate — v105 완료
- ABOUT/displaytest/input monitor UI app split — v106-v108 완료
- post-v108 structure audit — v109 완료
- app controller cleanup — v110 완료
- extended soak RC — v111 완료
- USB/NCM service soak — v112 완료
- runtime package layout — v113 완료
- helper deployment 2 — v114 완료
- remote shell hardening — v115 완료
- diagnostics bundle 2 — v116 완료
- v109-v116 completion audit — 완료
- long soak foundation — v146 완료
- long soak status — v147 완료
- long soak correlation — v148 완료
- static dropbear SSH 또는 custom TCP shell

---

## 현재 기준점

- 최신 확인 버전: `A90 Linux init 0.9.53 (v153)`
- 공식 버전: `0.9.53`
- build tag: `v153`
- creator: `made by temmie0214`
- 최신 verified 소스: `stage3/linux_init/init_v153.c` + `stage3/linux_init/v153/*.inc.c` + `stage3/linux_init/helpers/a90_cpustress.c` + `stage3/linux_init/helpers/a90_rshell.c` + `stage3/linux_init/helpers/a90_longsoak.c` + `stage3/linux_init/a90_config.h` + `stage3/linux_init/a90_util.c/h` + `stage3/linux_init/a90_log.c/h` + `stage3/linux_init/a90_timeline.c/h` + `stage3/linux_init/a90_console.c/h` + `stage3/linux_init/a90_cmdproto.c/h` + `stage3/linux_init/a90_run.c/h` + `stage3/linux_init/a90_service.c/h` + `stage3/linux_init/a90_kms.c/h` + `stage3/linux_init/a90_draw.c/h` + `stage3/linux_init/a90_input.c/h` + `stage3/linux_init/a90_input_cmd.c/h` + `stage3/linux_init/a90_hud.c/h` + `stage3/linux_init/a90_menu.c/h` + `stage3/linux_init/a90_metrics.c/h` + `stage3/linux_init/a90_shell.c/h` + `stage3/linux_init/a90_controller.c/h` + `stage3/linux_init/a90_storage.c/h` + `stage3/linux_init/a90_selftest.c/h` + `stage3/linux_init/a90_usb_gadget.c/h` + `stage3/linux_init/a90_netservice.c/h` + `stage3/linux_init/a90_pid1_guard.c/h` + `stage3/linux_init/a90_runtime.c/h` + `stage3/linux_init/a90_helper.c/h` + `stage3/linux_init/a90_userland.c/h` + `stage3/linux_init/a90_diag.c/h` + `stage3/linux_init/a90_exposure.c/h` + `stage3/linux_init/a90_wifiinv.c/h` + `stage3/linux_init/a90_wififeas.c/h` + `stage3/linux_init/a90_changelog.c/h` + `stage3/linux_init/a90_longsoak.c/h` + `stage3/linux_init/a90_app_about.c/h` + `stage3/linux_init/a90_app_cpustress.c/h` + `stage3/linux_init/a90_app_displaytest.c/h` + `stage3/linux_init/a90_app_inputmon.c/h` + `stage3/linux_init/a90_app_log.c/h` + `stage3/linux_init/a90_app_network.c/h`
- 최신 verified boot image: `stage3/boot_linux_v153.img`
- previous verified source-layout baseline: `stage3/linux_init/init_v80.c` + `stage3/linux_init/v80/*.inc.c`
- known-good fallback: `stage3/boot_linux_v48.img`
- 주 제어 채널: USB CDC ACM serial (`/dev/ttyGS0` ↔ `/dev/ttyACM0`)
- host bridge: `scripts/revalidation/serial_tcp_bridge.py --port 54321`
- 화면 상태: custom boot splash 약 2초 표시 후 상태 HUD/menu 자동 전환
- 버튼 상태: VOL+/VOL-/POWER 입력 확인
- 로그 상태: SD 정상 시 `/mnt/sdext/a90/logs/native-init.log`, fallback 시 `/cache/native-init.log`, emergency fallback 시 private `/tmp/a90-native/native-init.log` boot/command log 확인
- blocking 상태: `waitkey`/`readinput`/`watchhud`/`blindmenu` q/Ctrl-C 취소 확인
- long soak 상태: v146 recorder, v147 status, v148 correlation, v149 supervisor, v150 classifier, v151 bundle, v152 trend, v153 security hardening 실기 검증 완료
- timeline 상태: `timeline` 명령과 current native log replay 확인
- HUD 상태: `BOOT OK shell` summary 표시 확인
- run/log 상태: `/bin/a90sleep` q 취소와 recovery 왕복 log preservation 확인
- storage 상태: `/cache` safe write, ext4 SD workspace `/mnt/sdext/a90`, boot-time SD health check, critical partitions do-not-touch 기준 문서화
- storage I/O 상태: v161에서 `/mnt/sdext/a90/test-io` 4K/64K/1M/16M write/read/hash/rename/sync/unlink 검증 완료
- screen menu 상태: 자동 메뉴, 버튼 조작, input gesture layout, input monitor, serial `hide`/busy gate 확인
- USB 상태: ACM-only gadget `04e8:6861` / host `cdc_acm` 기준 문서화
- USB reattach 상태: v48 `usbacmreset`와 외부 helper `off` 후 serial 복구 확인
- USB NCM 상태: host `cdc_ncm` + device `ncm0`, IPv4 ping, IPv6 link-local ping, host→device netcat 확인
- NCM 운영 helper 상태: host interface 자동 탐지, ping, static TCP nettest 양방향 payload 검증 완료
- TCP control 상태: NCM 위에서 token-authenticated `/bin/a90_tcpctl` ping/status/run/shutdown 검증 완료
- TCP wrapper 상태: `tcpctl_host.py smoke` launch/client/stop 자동 검증 완료
- TCP soak 상태: v160에서 `tcpctl_host.py soak` 3602.5초/360사이클 안정성 검증 완료
- serial noise 상태: unsolicited `AT` modem probe line 무시 확인
- boot netservice 상태: opt-in flag 기반 NCM/tcpctl 부팅 자동 시작과 rollback 검증 완료
- netservice 기본값: disabled. `/cache/native-init-netservice` flag가 있을 때만 자동 시작
- reconnect 상태: v60 `netservice stop/start` software UDC 재열거 후 NCM/TCP 복구 확인
- HUD metrics 상태: CPU/GPU 온도와 사용률 `%` 표시, `cpustress`로 CPU usage 상승 확인
- dev node 상태: `/dev/null`/`/dev/zero` boot-time char device guard 확인
- app menu 상태: APPS/MONITORING/TOOLS/LOGS/NETWORK/POWER 계층 메뉴와 CPU stress 시간 선택 확인
- boot splash 상태: `A90 NATIVE INIT` custom splash와 `display-splash` timeline 기록 확인
- splash layout 상태: v65에서 긴 문구/footer 잘림 방지 safe layout 적용
- about app 상태: `APPS / ABOUT`에 version, changelog 목록/상세, credits 추가
- menu gate 상태: v128 기준 메뉴 표시 중 read-only status/query subcommand만 추가 허용하고 side-effect 명령은 `[busy]` 차단
- Wi-Fi 상태: v122 `wifiinv refresh`/`wififeas refresh` 기준 active bring-up은 계속 blocked
- Security Batch 1 상태: v123에서 tcpctl auth/bind, ramdisk tcpctl helper, dangerous `service` gate, reconnect cleanup fail-closed 적용 완료
- Security Batch 2 상태: v124에서 runtime helper SHA-256 preference, no-follow storage/log writes, mountsd SD identity gate, tcpctl install rollback 적용 완료
- Security Batch 3 상태: host tooling에서 cmdv1 retry/framing, ADB shell path quoting, NCM interface pinning, serial bridge identity pinning 적용 완료
- Security Batch 4 상태: v125에서 diagnostics/log owner-only permissions, private fallback log, HUD log tail opt-in 적용 완료
- Security Batch 5 상태: host/rootfs tooling에서 legacy root SSH default credential 제거와 safe archive extraction 적용 완료
- Security Batch 6 상태: v126에서 retained-source compatibility, v84 changelog route, v42 run stdin, input event validation 정리 완료
- Security Batch 7 상태: v127에서 menu-active busy gate deny-by-default allowlist 적용으로 F023 종료
- v128 상태: F023 mitigation을 유지하면서 menu-visible read-only subcommand policy 적용 완료
- v129 상태: changelog viewport/shared data/about page navigation 적용 완료
- v130 상태: volume hold-repeat scroll과 VOL+DN physical back shortcut 적용 완료
- v131 상태: EV_KEY repeat 미발생 환경을 위해 timer-based hold scroll 적용 완료, 실기 UX 정상 확인
- v132 상태: ABOUT/changelog legacy route 제거와 shared changelog table 단일 경로 정리 완료, 실기 flash/quick soak 확인
- v133 상태: ABOUT/changelog version series 분류 메뉴 적용 완료, 실기 flash/quick soak 및 수동 화면 확인
- v134 상태: network exposure guardrail 적용 완료, 실기 flash 후 `exposure status|verbose|guard`, `diag`, `screenmenu` 회귀 확인
- v135 상태: controller policy matrix 적용 완료, 실기 flash 후 `policycheck run`, menu-visible allow/block 대표 케이스, quick soak 확인
- v136 상태: post-v135 structure audit 완료, 실기 flash 후 `selftest verbose`, `exposure guard`, `policycheck run`, quick soak 확인
- v137 상태: integrated validation matrix 적용 완료, 실기 flash 후 `native_integrated_validate.py`, quick soak 확인
- v138 상태: release-candidate extended soak 적용 완료, 실기 flash 후 `native_integrated_validate.py`, quick soak, `native_rc_soak.py --cycles 3` 확인
- v139 상태: auto-HUD/menu controller cleanup 적용 완료, 실기 flash 후 integrated/quick/RC soak 확인
- v140 상태: CPU stress screen app lifecycle/renderer를 `a90_app_cpustress.c/h`로 분리하고 helper 포함 ramdisk로 실기 flash, `cpustress 3 2`, integrated/quick soak 확인
- v141 상태: LOG/NETWORK summary renderer를 `a90_app_log.c/h`, `a90_app_network.c/h`로 분리하고 실기 flash, integrated/quick soak 확인
- v142 상태: cutout calibration state/feed/draw API를 `a90_app_displaytest.c/h`로 분리하고 실기 flash, `displaytest safe`, `cutoutcal`, integrated/quick soak 확인
- v143 상태: `waitkey`/`waitgesture`/`inputlayout` command handler를 `a90_input_cmd.c/h`로 분리하고 실기 flash, inputlayout/hide/version, integrated/quick soak 확인
- v144 상태: `inputmonitor` foreground command loop를 `a90_app_inputmon.c/h`로 분리하고 실기 flash, inputmonitor q cancel, integrated/quick soak 확인
- v145 상태: `native_input_cancel_validate.py`로 `waitkey`/`waitgesture`/`inputmonitor` q cancel 자동 검증을 추가하고 실기 flash, cancel harness, integrated/quick soak 확인
- ADB 상태: 보류

다음 실행 후보:

- v134 exposure guardrail과 v135 policy matrix 검증 완료. F021/F030 accepted boundary는 `exposure`/`diag`/`status`에서 관찰 가능해야 유지된다.
- 최신 local targeted rescan은 `docs/security/scans/SECURITY_FRESH_SCAN_F038_F044_2026-05-09.md` 기준 PASS=27/WARN=1/FAIL=0이다. 다음 보안 입력은 Codex Cloud fresh scan 또는 새 network-facing 변경 이후 scan 결과로 삼는다.
- C/B 후보를 버전 분리했다.
  - v136: post-v135 structure audit 완료. 보고서 `docs/reports/NATIVE_INIT_V136_STRUCTURE_AUDIT_2026-05-07.md`.
  - v137: integrated validation matrix 완료. 보고서 `docs/reports/NATIVE_INIT_V137_VALIDATION_MATRIX_2026-05-07.md`.
  - v138: release-candidate extended soak 완료. 보고서 `docs/reports/NATIVE_INIT_V138_EXTENDED_SOAK_2026-05-08.md`.
  - v139: auto-HUD/menu controller cleanup 완료. 보고서 `docs/reports/NATIVE_INIT_V139_AUTOHUD_CONTROLLER_2026-05-08.md`.
  - v140: CPU stress app module split 완료. 보고서 `docs/reports/NATIVE_INIT_V140_CPUSTRESS_APP_2026-05-08.md`.
  - v141: LOG/NETWORK app renderer split 완료. 보고서 `docs/reports/NATIVE_INIT_V141_LOG_NETWORK_APP_2026-05-08.md`.
  - v142: cutout calibration app API split 완료. 보고서 `docs/reports/NATIVE_INIT_V142_CUTOUT_APP_2026-05-08.md`.
  - v143: input command handler API split 완료. 보고서 `docs/reports/NATIVE_INIT_V143_INPUT_COMMAND_2026-05-08.md`.
  - v144: inputmonitor foreground app API split 완료. 보고서 `docs/reports/NATIVE_INIT_V144_INPUTMON_APP_2026-05-08.md`.
  - v145: input cancel validation harness 완료. 보고서 `docs/reports/NATIVE_INIT_V145_INPUT_CANCEL_VALIDATION_2026-05-08.md`.
- network-facing 기능 확장은 v145 통합 검증 gate와 local security rescan이 green인 상태에서만 다시 판단한다.
- post-v145 다음 후보는 fresh Codex Cloud scan follow-up, network-facing 판단, 또는 남은 UI/app renderer split 중에서 다시 선정한다.

상세 상태 문서:

- `docs/reports/NATIVE_INIT_V82_LOG_TIMELINE_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V81_CONFIG_UTIL_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V80_SOURCE_MODULES_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V79_BOOT_STORAGE_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V78_SD_WORKSPACE_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V77_DISPLAY_TEST_PAGES_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V76_AT_FRAGMENT_FILTER_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V75_QUIET_IDLE_REATTACH_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V74_CMDV1X_ARG_ENCODING_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V73_CMDV1_PROTOCOL_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V45_RUN_LOG_2026-04-25.md`
- `docs/reports/NATIVE_INIT_STORAGE_MAP_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V47_SCREEN_MENU_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V48_USB_REATTACH_NCM_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V53_MENU_BUSY_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V54_NCM_LINK_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V55_NCM_OPS_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V56_TCPCTL_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V57_TCPCTL_HOST_WRAPPER_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V58_TCPCTL_SOAK_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V59_AT_NOISE_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V60_NETSERVICE_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V60_RECONNECT_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V61_CPU_GPU_USAGE_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V62_CPUSTRESS_2026-04-26.md`
- `docs/reports/NATIVE_INIT_USB_GADGET_MAP_2026-04-25.md`
- `docs/reports/NATIVE_INIT_USERLAND_CANDIDATES_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V44_HUD_BOOT_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V43_TIMELINE_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V42_CANCEL_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V41_LOGGING_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V40_BUILD_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V39_STATUS_2026-04-25.md`

---

## P0. 운영 안정성

### 1. Shell return code 정밀화

목표:

- `[done]`이 단순히 command dispatch 완료가 아니라 실제 성공에 가깝게 보이도록 한다.
- 실패한 내부 syscall, mount, file open, ioctl, exec 결과를 command result에 반영한다.

현재 상태:

- `init_v40`에서 1차 구현 및 실기 검증 완료
- 상세 기록: `docs/reports/NATIVE_INIT_V40_BUILD_2026-04-25.md`
- `/cache/native-init.log`는 `init_v41`에서 구현 및 실기 검증 완료

대상:

- display 명령
- mount 명령
- file 명령
- input 명령
- process 실행 명령

작업:

- legacy `cmd_*` 함수 중 `void` 계열을 `int` 반환으로 단계 전환
- 실패 시 `errno` 보존
- `last`가 실제 실패 원인을 더 잘 보여주도록 정리
- unknown command, usage error, syscall error를 구분

검증:

- 존재하지 않는 파일 `cat`
- 잘못된 mount source
- 잘못된 display color
- 없는 executable `run`
- 정상 명령과 실패 명령의 `[done]`/`[err]` 차이 확인

### 2. 파일 로그 추가

목표:

- serial이 끊기거나 화면이 멈춘 것처럼 보여도 부팅 진행과 명령 결과를 나중에 확인한다.

우선 저장 위치:

- 1순위: `/cache/native-init.log`
- 2순위: `/tmp/native-init.log`

기록 항목:

- boot step
- version
- mount 결과
- display init 결과
- serial attach 결과
- command start/end
- result code
- `errno`
- duration

주의:

- `/cache` mount 실패 시 `/tmp`로 fallback
- 로그 파일이 너무 커지지 않도록 단순 rotation 또는 truncate 정책 필요
- `/data`, `/efs`, modem 관련 영역은 로그 대상으로 쓰지 않음

현재 상태:

- `init_v41`에서 구현 및 실기 검증 완료
- 상세 기록: `docs/reports/NATIVE_INIT_V41_LOGGING_2026-04-25.md`
- `logpath`, `logcat` 명령 추가
- `/sys/class/block/<name>/dev` 기반 동적 block node 생성으로 `sda28`, `sda31` major/minor 변동 대응
- recovery 왕복 후 로그 보존 재확인은 별도 항목으로 남김

검증:

- 부팅 후 `cat /cache/native-init.log`
- 고의 실패 명령 실행 후 로그에 실패 원인 기록 여부 확인
- recovery 재부팅 후 로그 보존 여부 확인

### 3. Blocking command 취소 정책 통일

목표:

- 오래 기다리는 명령에서 shell을 잃지 않도록 한다.

대상:

- `watchhud`
- `waitkey`
- `readinput`
- `blindmenu`
- `run`

정책:

- `q`: 정상 취소
- `Ctrl-C`: 강제 취소
- timeout 옵션: 선택적 지원

현재 상태:

- `init_v42`에서 공통 cancel helper 구현 및 실기 검증 완료
- 상세 기록: `docs/reports/NATIVE_INIT_V42_CANCEL_2026-04-25.md`
- `q`/`Ctrl-C`는 `-ECANCELED` (`errno=125`)로 `last`와 log에 남김
- 실기 검증 완료:
  - `waitkey`
  - `readinput`
  - `watchhud`
  - `blindmenu`
- `run`/`runandroid` cancelable child wait는 구현됐지만, 안전한 long-running static test binary가 없어 실기 cancel은 보류

검증:

- 각 blocking 명령에서 `q`로 prompt 복귀 — 부분 완료
- `Ctrl-C` 입력 후 prompt 복귀 — `waitkey` 완료
- 취소 후 `status`, `last`, `help`가 정상 동작 — 완료

---

## P1. 필요한 역추적 목록

### 1. Boot readiness timeline

목표:

- native init 기준으로 커널 리소스가 언제 준비되는지 단계표를 만든다.

현재 상태:

- `init_v43`에서 자동 기록 및 실기 검증 완료
- 상세 기록: `docs/reports/NATIVE_INIT_V43_TIMELINE_2026-04-25.md`
- `timeline` shell 명령 추가
- `/cache` mount 전 초기 timeline은 `/cache` 선택 후 log에 replay

확인 항목:

- `/proc` mount 시점
- `/sys` mount 시점
- `/dev` 또는 수동 device node 생성 시점
- `/cache` mount 시점
- USB gadget configfs 준비 시점
- `/dev/ttyGS0` attach 시점
- DRM/KMS open 가능 시점
- input event node 준비 시점
- power/thermal sysfs 준비 시점

출력 형태:

- boot log
- `status`
- 별도 report 문서

### 2. Display pipeline

목표:

- 현재 HUD 출력이 왜 안정적으로 보이는지, 어떤 부분이 아직 불안정한지 분리한다.

확인 항목:

- DRM card 번호
- connector id
- encoder/crtc id
- mode 정보
- dumb framebuffer 생성/매핑
- `SETCRTC` 성공 조건
- page flip 실패 원인
- backlight sysfs 경로
- blank/unblank 경로
- 화면 회전/좌표계
- punch-hole/cutout 안전 영역

참고 후보:

- TWRP recovery ramdisk의 display 초기화 방식
- kernel DRM sysfs
- 기존 `kmsprobe`, `drminfo`, `fbinfo` 출력

검증:

- custom boot splash
- debug TEST pattern
- HUD
- 단색 출력
- 작은 글자 출력
- 화면 꺼짐/켜짐
- 밝기 변경

### 3. Input/event map

목표:

- 물리 버튼과 event node 관계를 고정한다.

현재 확인:

- `event0`: `qpnp_pon`, POWER/VOLDOWN
- `event3`: `gpio_keys`, VOLUP

추가 확인:

- long press 이벤트
- key release 이벤트
- repeat 이벤트
- recovery/TWRP에서 같은 event map 유지 여부
- 터치 event node 존재 여부

검증:

- `inputinfo`
- `inputcaps`
- `readinput`
- `waitkey`
- 화면 메뉴에서 선택 이동/확정

### 4. Power, battery, thermal units

목표:

- HUD에 표시되는 전력/온도/배터리 값의 단위와 신뢰도를 확정한다.

확인 항목:

- battery capacity
- battery status
- battery temp unit
- voltage unit
- `power_now`
- `power_avg`
- CPU thermal zone
- GPU thermal zone
- throttling 관련 sysfs

주의:

- Samsung vendor sysfs는 표준 단위와 다를 수 있다.
- 전력 표시는 확정 전까지 `W?`처럼 불확실성을 표시한다.

검증:

- 충전기 연결/해제 전후 값 변화
- 화면 켜짐/꺼짐 전후 값 변화
- HUD refresh 반영 여부

### 5. Safe storage map

목표:

- native init에서 안전하게 읽고 쓸 수 있는 저장소를 구분한다.

현재 상태:

- `docs/reports/NATIVE_INIT_STORAGE_MAP_2026-04-25.md`로 v46 기준 1차 문서화 완료
- `/cache`는 persistent safe write로 사용
- `userdata`는 대용량 후보지만 Android FBE/user data와 엮여 있어 별도 의사결정 전까지 보류
- `efs`, `sec_efs`, modem, persist, key/security, vbmeta, bootloader 계열은 do-not-touch

후보:

- `/cache`
- `/tmp`
- `/mnt/system` read-only
- `/metadata` read-only 탐색 후보

금지 또는 주의:

- `/efs`
- modem 관련 파티션
- RPMB/keymaster/keystore 관련 영역
- `/data` 암호화 영역
- bootloader/vbmeta 계열

검증:

- `/proc/partitions`
- `/proc/mounts`
- `stat`
- `mountsystem ro`
- `/cache` write/read/sync

### 6. USB gadget map

목표:

- 현재 안정적인 ACM serial을 기준으로, 추후 네트워크/ADB 가능성을 판단할 자료를 만든다.

현재 상태:

- `docs/reports/NATIVE_INIT_USB_GADGET_MAP_2026-04-25.md`로 1차 문서화 완료
- 현재 active gadget은 ACM-only
- host descriptor는 CDC ACM control/data 2-interface만 노출
- ADB는 FunctionFS `ep0 only`/`adbd` zombie 문제가 blocker
- USB networking은 ACM rescue channel 유지 후 두 번째 function으로 probe 예정

확인 항목:

- configfs gadget path
- UDC name
- ACM function 설정
- host enumeration 상태
- FunctionFS ADB endpoint 생성 실패 조건
- RNDIS/NCM function 사용 가능성

현재 판단:

- ADB보다 ACM serial이 안정적이다.
- 추후 네트워크가 필요하면 ADB 복구보다 RNDIS/NCM + 작은 server가 더 현실적일 수 있다.

---

## P1. Shell 기능 개선 목록

### 1. 명령 help 정리

목표:

- `help` 출력이 너무 길어져도 읽을 수 있게 그룹화한다.

그룹 후보:

- core
- files
- mounts
- display
- input
- sensors
- process
- power
- debug

검증:

- `help`
- `help display`
- `help input`

### 2. 명령 parser 개선

목표:

- 실험에 필요한 최소 수준의 인자 처리를 안정화한다.

후보:

- quote 처리
- escaped space
- empty argument
- usage error 메시지 통일

비목표:

- full POSIX shell 구현
- pipe/redirection
- shell script language

### 3. File utility 보강

목표:

- device에서 직접 정보를 수집하기 쉽게 한다.

후보 명령:

- `readlink`
- `hexdump`
- `grep` 또는 단순 `findtext`
- `find`
- `tree` 제한 버전
- `tail`
- `log`

주의:

- 복잡한 BusyBox 재구현으로 흐르지 않게 한다.
- 필요한 것부터 작게 추가한다.

### 4. Process 실행 안정화

목표:

- 외부 static binary를 실험적으로 실행할 수 있게 한다.

작업:

- `run` timeout
- exit status 표시
- signal 종료 표시
- stdout/stderr 처리 정책
- child zombie 회수

검증:

- 정상 static binary
- 없는 binary
- crash binary
- 장시간 sleep binary

---

## P1. 화면/HUD/Menu

### 1. HUD 정보 레이아웃 안정화

목표:

- punch-hole, edge clipping, 색상 대비 문제를 피한다.

작업:

- safe margin 상수화
- font scale 정책 정리
- 상단 상태 위치 고정
- 하단 help text clipping 방지
- black-on-black 방지

검증:

- 검은 배경
- 밝은 배경
- 충전기 연결/해제
- 화면 회전 없이 1080x2400 기준 유지

### 2. Boot screen sequence

목표:

- 부팅 후 사용자가 “멈춘 것인지 진행 중인지” 알 수 있게 한다.

현재:

- v70 custom boot splash 약 2초
- HUD/menu 자동 전환

추가 후보:

- boot step progress text
- serial ready 표시
- cache/log ready 표시
- error 발생 시 붉은 상태줄

### 3. On-screen menu

목표:

- serial 없이도 최소 조작을 가능하게 한다.

현재 상태:

- `init_v47`에서 `menu`/`screenmenu` 화면 메뉴 초안 구현
- `RESUME`, `STATUS`, `LOG`, `RECOVERY`, `REBOOT`, `POWEROFF` 항목 제공
- q cancel 후 autohud 복구 확인
- 실제 버튼 이동/선택과 위험 동작은 수동 검증 대기

후보 메뉴:

- status
- refresh
- mount system ro
- reboot recovery
- poweroff
- show log
- start serial hint

입력:

- VOLUP: move up
- VOLDOWN: move down
- POWER: select

검증:

- 각 버튼 1회 입력
- 길게 누르기
- prompt와 menu mode 전환

---

## P2. 네트워크와 외부 도구

### 1. BusyBox/toolbox류 도구 검토

목표:

- 모든 유틸을 직접 구현하지 않고, 필요한 static userland를 가져올 수 있는지 판단한다.

확인:

- static ARM64 BusyBox 실행 가능 여부
- 라이선스/배포 방식
- `/cache/bin` 또는 ramdisk 탑재 방식
- `PATH` 정책

주의:

- core shell 안정화 전에는 도구 추가가 문제를 가릴 수 있다.

현재 상태:

- V49로 승격해 진행 중이다.
- 후보 리포트: `docs/reports/NATIVE_INIT_USERLAND_CANDIDATES_2026-04-25.md`
- 1차 방향은 boot ramdisk 포함이 아니라 `/cache/bin`에 static ARM64 multi-call binary를 올리고 `run /cache/bin/<tool> <applet>` 형태로 명시 실행하는 것이다.
- host build prerequisite 설치 후 `scripts/revalidation/build_static_toybox.sh`로 `toybox 0.8.13` static ARM64 빌드가 성공했다.
- 산출물은 `external_tools/userland/bin/toybox-aarch64-static-0.8.13`이며 SHA256은 `92a0917579c76fec965578ac242afbf7dedc4428297fb90f4c9caf7f538a718c`다.
- TWRP ADB로 `/cache/bin/toybox` 배치 후 native init에서 주요 applet 실기 실행을 확인했다.
- `ifconfig -a`, `route -n`, `netcat --help`가 동작하므로 USB networking probe의 userland 기반은 확보됐다.

### 2. 네트워크

목표:

- 장기적으로 일반 Linux 서버처럼 접근할 수 있는 경로를 검토한다.

후보:

- USB RNDIS/NCM
- static telnetd
- static dropbear SSH
- host bridge 기반 custom RPC

현 판단:

- 당장은 serial bridge가 가장 단순하고 안정적이다.
- SSH/server화는 log, process, storage가 안정화된 뒤 검토한다.

### 3. ADB 재검토

목표:

- 현재 보류한 ADB를 나중에 다시 판단할 근거를 남긴다.

현재 문제:

- `adbd` zombie
- FunctionFS `ep0`만 생성
- `ep1`/`ep2` 미생성
- Android property service, SELinux context, bionic/apex 환경 부재

재검토 조건:

- FunctionFS endpoint 생성 흐름 이해
- 필요한 property/socket/context 최소셋 확인
- ADB가 serial/RNDIS보다 가치가 큰지 재판단

---

## 당장 다음 실행 순서

상세 실행 큐는 `docs/plans/NATIVE_INIT_TASK_QUEUE_2026-04-25.md`를 따른다.

1. v185 Communication Broker Protocol Plan
   - 계획: `docs/plans/NATIVE_INIT_V185_COMMUNICATION_BROKER_PLAN_2026-05-11.md`
   - 최신 증거: `docs/reports/NATIVE_INIT_V184_24H_SERVERIZATION_READINESS_2026-05-11.md` PASS
   - 선택 이유: Wi-Fi/NCM 노출을 넓히기 전에 raw ACM bridge를 직접 여러 도구가 공유하는 구조를 정리한다
   - v185는 실기기 플래시 버전이 아니라 v159 실기기 위에서 수행할 host protocol/broker 설계 cycle이다
2. v182-v184 Mixed Soak / Serverization Gate
   - v182 failure classifier는 완료됐다
   - v183 8h pilot은 PASS했다
   - v184 24h+ readiness gate는 PASS했다
   - Wi-Fi baseline refresh와 exposure hardening은 post-v184 roadmap에서 우선순위를 다시 정한다
3. v186+ Broker Skeleton / Harness Integration
   - `A90B1` host-local broker skeleton은 `scripts/revalidation/a90_broker.py`로 시작했다
   - live ACM bridge smoke, concurrent read-only client, rebind block 검증은 PASS했다
   - `DeviceClient`와 `native_test_supervisor.py`의 broker backend 연결을 시작했다
   - broker-backed supervisor smoke/observe live 검증은 PASS했다
   - mixed-soak dry-run도 PASS했다
   - v188은 broker audit/reporting으로 시작했다
   - live ACM broker audit report와 broker-backed supervisor smoke audit report는 PASS했다
   - v189 broker concurrent smoke script는 fake/live ACM 모두 PASS했다
   - v190 broker mixed-soak gate는 live ACM에서 PASS했다
   - v191 NCM/tcpctl broker backend는 NCM `run` path와 ACM fallback 모두 PASS했다
   - v192 broker failure/recovery tests는 fake/live 모두 PASS했다
   - 다음은 v193 후보 재선정 또는 broker/auth hardening follow-up이다
4. v193+ Broker/Auth Hardening Follow-up
   - v193 broker/auth hardening은 PASS했다: no-auth explicit allow gate, token validation, auth-failed classification, token redaction
   - v194 NCM/tcpctl listener lifecycle automation은 dry-run PASS했다
   - v195 broker-backed soak suite는 dry-run PASS했다
   - v196 fresh security scan follow-up workflow는 PASS했다: CSV 2건 indexed, local scan PASS/WARN/FAIL=29/1/0
   - 다음은 post-v196 후보 재선정이다
5. 이후 Wi-Fi Baseline Refresh / Network Exposure Hardening
   - v203 계획서: `docs/plans/NATIVE_INIT_V203_WIFI_BASELINE_REFRESH_PLAN_2026-05-13.md`
   - v203 collector: `scripts/revalidation/wifi_baseline_refresh.py`
   - v203 보고서: `docs/reports/NATIVE_INIT_V203_WIFI_BASELINE_REFRESH_2026-05-13.md`
   - broker/security gate 이후 native/mounted-system Wi-Fi 자료를 read-only로 다시 수집했다
   - v203 상태: PASS, final decision `no-go`
   - v204 계획서: `docs/plans/NATIVE_INIT_V204_ANDROID_TWRP_WIFI_BASELINE_PLAN_2026-05-13.md`
   - v204 collector: `scripts/revalidation/android_twrp_wifi_baseline.py`
   - v204 보고서: `docs/reports/NATIVE_INIT_V204_ANDROID_TWRP_WIFI_BASELINE_2026-05-13.md`
   - v204 상태: TWRP ADB PASS, decision `driver-candidate-found`
   - v204 Android 상태: Android ADB + Magisk root PASS, decision `ready-for-readonly-nl80211-probe-plan`
   - v205 계획서: `docs/plans/NATIVE_INIT_V205_ICNSS_NL80211_READONLY_PLAN_2026-05-13.md`
   - v205 collector: `scripts/revalidation/wifi_icnss_nl80211_probe.py`
   - v205 helper source: `stage3/linux_init/helpers/a90_nl80211_ro.c`
   - v205 보고서: `docs/reports/NATIVE_INIT_V205_ICNSS_NL80211_READONLY_2026-05-13.md`
   - v205 상태: PASS, decision `native-icnss-present-no-wiphy`
   - v206 계획서: `docs/plans/NATIVE_INIT_V206_ANDROID_ICNSS_CNSS_MAP_PLAN_2026-05-13.md`
   - v206 collector: `scripts/revalidation/android_icnss_cnss_map.py`
   - v206 보고서: `docs/reports/NATIVE_INIT_V206_ANDROID_ICNSS_CNSS_MAP_2026-05-13.md`
   - v206 상태: PASS, decision `ready-for-native-preflight-plan`
   - v206 실기: Android ADB/root collector PASS 후 native v159 복구 PASS
   - v207 계획서: `docs/plans/NATIVE_INIT_V207_NATIVE_WIFI_PREFLIGHT_PLAN_2026-05-13.md`
   - v207 collector: `scripts/revalidation/native_wifi_preflight.py`
   - v207 보고서: `docs/reports/NATIVE_INIT_V207_NATIVE_WIFI_PREFLIGHT_2026-05-13.md`
   - v207 상태: PASS, decision `missing-mounted-vendor`
   - v207 실기: native basic control, `mountsystem ro`, ICNSS sysfs PASS; mounted vendor firmware/init path, WLAN netdev/wiphy/rfkill, remote `a90_nl80211_ro`는 absent
   - v208 계획서: `docs/plans/NATIVE_INIT_V208_VENDOR_FIRMWARE_MOUNT_PLAN_2026-05-13.md`
   - v208 collector: `scripts/revalidation/native_vendor_mount_probe.py`
   - v208 보고서: `docs/reports/NATIVE_INIT_V208_VENDOR_FIRMWARE_MOUNT_2026-05-13.md`
   - v208 상태: PASS, decision `vendor-block-candidate-found`
   - v208 실기: native basic control PASS; `sda29` vendor 후보가 `/proc/partitions`와 `/sys/class/block`에 보이나 `/dev/block/sda29`/by-name 노드는 absent, mounted vendor firmware/init path는 absent
   - v209 계획서: `docs/plans/NATIVE_INIT_V209_VENDOR_RO_MOUNT_PROBE_PLAN_2026-05-13.md`
   - v209 collector: `scripts/revalidation/native_vendor_ro_mount_probe.py`
   - v209 보고서: `docs/reports/NATIVE_INIT_V209_VENDOR_RO_MOUNT_PROBE_2026-05-13.md`
   - v209 상태: PASS, decision `vendor-assets-visible`
   - v209 실기: `sda29` 임시 block node + isolated mountpoint + ext4 `ro,noload` mount PASS, cleanup PASS, vendor init/Wi-Fi firmware assets visible
   - v210 계획서: `docs/plans/NATIVE_INIT_V210_VENDOR_WIFI_CNSS_ASSET_CLASSIFIER_PLAN_2026-05-13.md`
   - v210 collector: `scripts/revalidation/native_vendor_asset_classifier.py`
   - v210 보고서: `docs/reports/NATIVE_INIT_V210_VENDOR_WIFI_CNSS_ASSET_CLASSIFIER_2026-05-13.md`
   - v210 상태: PASS, decision `firmware-path-policy-needed`
   - v210 실기: required vendor firmware/init rc/service binaries/VINTF는 native-visible vendor mount에서 확인됐고, `firmware_class.path=/vendor/firmware_mnt/image`가 현재 visible Wi-Fi firmware layout을 가리키지 않는 것이 다음 blocker다
   - v211 계획서: `docs/plans/NATIVE_INIT_V211_FIRMWARE_PATH_POLICY_PLAN_2026-05-13.md`
   - v211 collector: `scripts/revalidation/native_firmware_path_policy_probe.py`
   - v211 보고서: `docs/reports/NATIVE_INIT_V211_FIRMWARE_PATH_POLICY_2026-05-13.md`
   - v211 상태: PASS, decision `sysfs-path-update-needed`
   - v211 실기: isolated `/mnt/vendor/firmware` model과 synthetic `/vendor/firmware_mnt/image` bind model은 likely request names를 모두 resolve하지만, 현재 `/vendor/firmware_mnt/image`는 resolve하지 못한다
   - v212 계획서: `docs/plans/NATIVE_INIT_V212_FIRMWARE_PATH_ROLLBACK_PLAN_2026-05-13.md`
   - v212 collector: `scripts/revalidation/native_firmware_path_apply_probe.py`
   - v212 보고서: `docs/reports/NATIVE_INIT_V212_FIRMWARE_PATH_ROLLBACK_2026-05-13.md`
   - v212 상태: PASS, decision `path-rollback-pass`
   - v212 dry-run 실기: `/mnt/vendor/firmware` likely request paths는 모두 visible, cleanup PASS, `firmware_class.path`는 `/vendor/firmware_mnt/image`로 유지
   - v212 apply 실기: `/cache/bin/a90_fwpathctl` fixed-target helper로 `firmware_class.path=/mnt/vendor/firmware` 적용/readback 후 `/vendor/firmware_mnt/image`로 rollback PASS, leftover mount 없음
   - v213 계획서: `docs/plans/NATIVE_INIT_V213_FIRMWARE_REQUEST_EVIDENCE_PLAN_2026-05-13.md`
   - v213 collector: `scripts/revalidation/native_firmware_request_probe.py`
   - v213 optional helper source: `stage3/linux_init/helpers/a90_icnssctl.c`
   - v213 보고서: `docs/reports/NATIVE_INIT_V213_FIRMWARE_REQUEST_EVIDENCE_2026-05-13.md`
   - v213 상태: PASS, baseline decision `baseline-only`, path-only decision `path-only-pass`
   - v213 실기: read-only ICNSS baseline PASS, `/mnt/vendor/firmware` path apply/readback/rollback PASS, likely request paths visible, leftover mount 없음
   - v213 live constraint: dynamic debug/tracefs firmware events는 absent, ICNSS sysfs node와 driver bind/unbind controls는 present
   - v214 계획서: `docs/plans/NATIVE_INIT_V214_ICNSS_REPROBE_EXECUTION_PLAN_2026-05-13.md`
   - v214 보고서: `docs/reports/NATIVE_INIT_V214_ICNSS_REPROBE_EXECUTION_2026-05-13.md`
   - v214 상태: SAFETY STOP, decision `icnss-rebind-failed`
   - v214 실기: `/cache/bin/a90_icnssctl` 배포 PASS, `/mnt/vendor/firmware` path apply/readback/rollback PASS, ICNSS unbind PASS, ICNSS bind FAIL
   - v214 dmesg: `icnss: Driver is already initialized`, `probe of 18800000.qcom,icnss failed with error -17`
   - v214 recovery: native reboot 후 ICNSS bound 복구 PASS, `firmware_class.path=/vendor/firmware_mnt/image`
   - v215-v225 큰 계획: `docs/plans/NATIVE_INIT_V215_V225_WIFI_BIG_PLAN_2026-05-13.md`
   - v215-v225 상세 로드맵: `docs/plans/NATIVE_INIT_V215_V225_WIFI_LIFECYCLE_ROADMAP_2026-05-13.md`
   - v215-v225 version master plan:
     `docs/plans/NATIVE_INIT_V215_V225_WIFI_VERSION_MASTER_PLAN_2026-05-13.md`
   - v215 계획서: `docs/plans/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_PLAN_2026-05-13.md`
   - v215 보고서: `docs/reports/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_2026-05-13.md`
   - v215 상태: PASS, decision `lifecycle-map-ready`
   - v215 실기: manifest-only PASS, native bridge read-only PASS, live captures `16/16`
   - v216 계획서: `docs/plans/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_PLAN_2026-05-13.md`
   - v216 보고서: `docs/reports/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_2026-05-13.md`
   - v216 상태: PASS, decision `replay-model-ready`
   - v216 결과: `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, `wpa_supplicant`, `hostapd` service graph 작성 완료
   - v217 계획서: `docs/plans/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_PLAN_2026-05-13.md`
   - v217 보고서: `docs/reports/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_2026-05-13.md`
   - v217 상태: PASS, decision `state-only-inventory`
   - v217 결과: native read-only captures `11/11`, controls `168`, dangerous controls `bind`/`unbind`/`driver_override`
   - v218 계획서: `docs/plans/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_PLAN_2026-05-13.md`
   - v218 보고서: `docs/reports/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_2026-05-13.md`
   - v218 상태: PASS, decision `daemon-dryrun-partial`
   - v218 결과: `cnss-daemon`/`cnss_diag` binary visibility는 v210 기준 확인, ELF/library inspection은 host vendor root 부재로 incomplete
   - v219 계획서: `docs/plans/NATIVE_INIT_V219_NATIVE_ANDROID_ENV_SHIM_PLAN_2026-05-13.md`
   - v219 보고서: `docs/reports/NATIVE_INIT_V219_NATIVE_ANDROID_ENV_SHIM_2026-05-13.md`
   - v219 상태: PASS, decision `shim-plan-partial`
   - v219 결과: bounded shim matrix 생성 완료, property/QMI/recovery blocker와 host ELF/library evidence gap은 유지
   - v220 계획서: `docs/plans/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_PLAN_2026-05-13.md`
   - v220 보고서: `docs/reports/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_2026-05-13.md`
   - v220 상태: PASS, decision `no-go`
   - v220 결과: gate counts `pass=3`, `warn=1`, `fail=0`, `blocked=3`
   - v220 blocked: `icnss_recovery`, `shim_policy`, `security_exposure`
   - 다음은 v221 host vendor ELF/library evidence closure와 recovery/security prerequisite closure다. daemon 실행, generic sysfs unbind/bind, Wi-Fi scan/connect는 blocked
   - v221 계획서: `docs/plans/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_PLAN_2026-05-13.md`
   - v221 보고서: `docs/reports/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_2026-05-13.md`
   - v221 상태: PASS, decision `vendor-root-required`
   - v221 결과: host-visible vendor root가 필요하며 required paths는 `<vendor-root>/bin/cnss-daemon`, `<vendor-root>/bin/cnss_diag`
   - v222 계획서: `docs/plans/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_PLAN_2026-05-13.md`
   - v222 보고서: `docs/reports/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_2026-05-13.md`
   - v222 상태: PASS, decision `export-source-required`
   - v222 결과: `scripts/revalidation/wifi_vendor_root_evidence_export.py` 구현 완료, source vendor root 미제공 상태에서는 private/no-follow export plan과 required paths만 생성
   - v223 계획서: `docs/plans/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_PLAN_2026-05-13.md`
   - v223 보고서: `docs/reports/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_2026-05-13.md`
   - v223 상태: PASS, decision `reboot-recovery-accepted`
   - v223 결과: reboot만 accepted recovery primitive로 고정, generic ICNSS unbind/bind와 unreviewed sysfs/debugfs/configfs writes는 denied
   - v224 계획서: `docs/plans/NATIVE_INIT_V224_ANDROID_ENV_SHIM_DRYRUN_MATERIALIZATION_PLAN_2026-05-13.md`
   - v224 보고서: `docs/reports/NATIVE_INIT_V224_ANDROID_ENV_SHIM_MATERIALIZE_2026-05-13.md`
   - v224 상태: PASS, decision `shim-source-required`
   - v224 결과: host-side shim dry-run artifacts 생성 완료, v219 blocked rows 유지, v223 policy hard dependency 기록, source vendor root blocker 유지
   - v225 계획서: `docs/plans/NATIVE_INIT_V225_WIFI_EXPOSURE_SECURITY_GATE_V3_PLAN_2026-05-13.md`
   - v225 보고서: `docs/reports/NATIVE_INIT_V225_WIFI_EXPOSURE_SECURITY_GATE_V3_2026-05-13.md`
   - v225 상태: PASS, decision `still-no-go`
   - v225 결과: root-control exposure/credential policy는 gate v3에 반영됐지만 `vendor_evidence`, `shim_materialization` blocker가 남아 active Wi-Fi는 계속 blocked
   - v226 계획서: `docs/plans/NATIVE_INIT_V226_VENDOR_ROOT_LIVE_EXPORT_PLAN_2026-05-14.md`
   - v226 보고서: `docs/reports/NATIVE_INIT_V226_VENDOR_ROOT_LIVE_EXPORT_2026-05-14.md`
   - v226 상태: PASS, decision `vendor-source-exported`
   - v226 결과: live native `sda29` ro,noload vendor export 완료, v222는 `vendor-root-ready`, v224는 `shim-dryrun-ready`로 전환
   - v227 계획서: `docs/plans/NATIVE_INIT_V227_ANDROID_CORE_SYSTEM_LIBRARY_EVIDENCE_PLAN_2026-05-14.md`
   - v227 보고서: `docs/reports/NATIVE_INIT_V227_ANDROID_CORE_SYSTEM_LIBRARY_EVIDENCE_2026-05-14.md`
   - v227 상태: PASS, decision `system-root-ready`
   - v227 결과: live native `/mnt/system/system/lib*`에서 Android core/system libraries export 완료
   - 재검증 결과: v221 `elf-evidence-ready`, v224 `shim-dryrun-ready`, v225 `cnss-start-plan-approved`
   - v228 계획서: `docs/plans/NATIVE_INIT_V228_CONTROLLED_CNSS_START_PLAN_2026-05-14.md`
   - v228 보고서: `docs/reports/NATIVE_INIT_V228_CONTROLLED_CNSS_START_PLAN_2026-05-14.md`
   - v228 상태: PASS, decision `cnss-start-plan-ready`
   - v228 결과: daemon 실행 없이 command allowlist, start plan, rollback policy, exposure boundary 산출
   - v229 계획서: `docs/plans/NATIVE_INIT_V229_CONTROLLED_CNSS_START_RUNNER_PLAN_2026-05-14.md`
   - v229 보고서: `docs/reports/NATIVE_INIT_V229_CONTROLLED_CNSS_START_RUNNER_2026-05-15.md`
   - v229 구현: `scripts/revalidation/wifi_cnss_start_experiment.py`
   - v229 상태: dry-run PASS + live preflight PASS/safe-stop, decision `start-only-runtime-gap`
   - v229 목표: opt-in controlled CNSS start-only runner. 기본은 plan/preflight/dry-run이며 live daemon start는 `--allow-daemon-start --assume-yes` 명시 전까지 금지
   - v229 preflight 결과: `/mnt/system/system/bin/linker64`는 보이나 `/mnt/system/vendor/bin/cnss-daemon`과 global `/system/bin/linker64`/`/system/vendor/bin/cnss-daemon` namespace가 없어 daemon 실행 전 중단
   - v230 계획서: `docs/plans/NATIVE_INIT_V230_ANDROID_EXEC_NAMESPACE_PLAN_2026-05-15.md`
   - v230 host tool: `scripts/revalidation/wifi_android_exec_namespace_probe.py`
   - v230 보고서: `docs/reports/NATIVE_INIT_V230_ANDROID_EXEC_NAMESPACE_PROBE_2026-05-15.md`
   - v230 live inventory PASS, decision `android-exec-namespace-runtime-gap`
   - 확인: `/mnt/system/system/vendor -> /vendor`, vendor source `needs-remount`, APEX runtime available
   - 남은 blocker: `linkerconfig-need-unproven`
   - v231 계획서: `docs/plans/NATIVE_INIT_V231_LINKERCONFIG_NAMESPACE_HELPER_PLAN_2026-05-15.md`
   - v231 보고서: `docs/reports/NATIVE_INIT_V231_LINKERCONFIG_NAMESPACE_HELPER_2026-05-15.md`
   - v231 상태: private mount namespace helper와 host probe 경로 구현 완료, static ARM64 build PASS, NCM deploy PASS
   - 실기 probe: helper setup은 `namespace-ready`, vendor `sda29`는 private temp block node로 ro,noload mount, `/linkerconfig`는 `/mnt/system/linkerconfig` read-only bind
   - 결과: `/system/bin/linker64 --list /vendor/bin/cnss-daemon`가 stdout/stderr 없이 `SIGSEGV(11)`로 종료, decision `android-namespace-manual-review-required`
   - 확인: `/mnt/system/linkerconfig`는 empty, `/mnt/system/system/etc/ld.config*.txt`는 absent, linker 바이너리에는 `--list`와 `/linkerconfig/ld.config.txt` 참조가 존재
   - v232 상태: private-only linkerconfig materialization 구현/실기 실행 완료
   - v232 계획서: `docs/plans/NATIVE_INIT_V232_LINKERCONFIG_MATERIALIZATION_PLAN_2026-05-15.md`
   - v232 보고서: `docs/reports/NATIVE_INIT_V232_LINKERCONFIG_MATERIALIZATION_2026-05-15.md`
   - v232 결과: `minimal-vendor` private linkerconfig에서도 `/system/bin/linker64 --list /vendor/bin/cnss-daemon`가 stdout/stderr 없이 `SIGSEGV(11)`로 종료했다
   - v233 보고서: `docs/reports/NATIVE_INIT_V233_REAL_LINKERCONFIG_COPY_REAL_2026-05-15.md`
   - v233 상태: stock Android boot에서 real `/linkerconfig/ld.config.txt`를 read-only capture했고, native v159 복구 후 `copy-real` probe까지 실행했다
   - v233 결과: real Android generated linkerconfig에서도 `/system/bin/linker64 --list /vendor/bin/cnss-daemon`가 stdout/stderr 없이 `SIGSEGV(11)`로 종료했다
   - v234 계획서: `docs/plans/NATIVE_INIT_V234_LINKER_CRASH_CONTEXT_PLAN_2026-05-15.md`
   - v234 보고서: `docs/reports/NATIVE_INIT_V234_LINKER_CRASH_CONTEXT_2026-05-15.md`
   - v234 결과: `system-toybox`, `system-sh`, `linker64-self`, `cnss-daemon` 모두 `linker64 --list`에서 `SIGSEGV(11)`로 종료했다
   - v234 decision: `android-linker-crash-generic`; 문제는 `cnss-daemon` target-specific이 아니라 generic Android linker invocation/private namespace context 쪽이다
   - v235 계획서: `docs/plans/NATIVE_INIT_V235_LINKER_INVOCATION_PATH_PLAN_2026-05-15.md`
   - v235 보고서: `docs/reports/NATIVE_INIT_V235_LINKER_INVOCATION_PATH_2026-05-18.md`
   - v235 결과: `/system/bin/linker64`와 direct `/apex/com.android.runtime/bin/linker64` 모두 20-case matrix에서 child `SIGSEGV(11)`, stdout/stderr empty
   - v235 decision: `android-linker-crash-path-independent`; symlink path 문제가 아니라 Android linker process context/namespace crash 쪽이다
   - v236 계획서: `docs/plans/NATIVE_INIT_V236_LINKER_CRASH_CAPTURE_PLAN_2026-05-18.md`
   - v236 보고서: `docs/reports/NATIVE_INIT_V236_LINKER_CRASH_CAPTURE_2026-05-18.md`
   - v236 결과: 6-case matrix 모두 `SIGSEGV(11)` 재현, ptrace-lite exec/crash context capture 성공
   - v236 crash pattern: fault addr `0xa1`, linker64 PC file offset `0x1002f4`, regset `272` bytes
   - v237 계획서: `docs/plans/NATIVE_INIT_V237_LINKER_OFFSET_SYMBOLIZATION_PLAN_2026-05-18.md`
   - v237 host tool: `scripts/revalidation/wifi_linker_offset_symbolize.py`
   - v237 결과: `/mnt/system/system/apex/com.android.runtime/bin/linker64` export + readelf/objdump 분석 PASS, decision `linker-offset-symbolized`
   - v237 symbolization: offset `0x1002f4` -> `.text` / `__dl__ZL13__early_aborti+0x14` / `str wzr, [x8]`, linker64 SHA-256 `ebd1db608558ccb01f851a4988abea2f2dd8844b7bc09e1847ebaf05e36a421d`
   - v237 해석: crash는 임의 미상 코드가 아니라 bionic linker의 intentional early-abort trap이며, 다음은 `__early_abort` call-site/abort-code 분석
   - v238 계획서: `docs/plans/NATIVE_INIT_V238_LINKER_EARLY_ABORT_MAP_PLAN_2026-05-18.md`
   - v238 host tool: `scripts/revalidation/wifi_linker_early_abort_map.py`
   - v238 보고서: `docs/reports/NATIVE_INIT_V238_LINKER_EARLY_ABORT_MAP_2026-05-18.md`
   - v238 결과: decision `linker-early-abort-dev-null-open-failed`, abort code `0xa1` maps to call site `0x1000b8` in `__dl__Z21__libc_init_AT_SECUREPPc+0xa0`
   - v238 해석: private Android execution namespace 안에 bionic이 기대하는 `/dev/null` 또는 `/sys/fs/selinux/null` context가 없어서 `linker64 --list`도 early abort한다
   - 다음 blocker closure: v239에서 private namespace root에 최소 `/dev/null` materialization/bind 후 linker list matrix 재실행
   - v239 계획서: `docs/plans/NATIVE_INIT_V239_PRIVATE_DEVNULL_PROBE_PLAN_2026-05-18.md`
   - v239 보고서: `docs/reports/NATIVE_INIT_V239_PRIVATE_DEVNULL_PROBE_2026-05-18.md`
   - v239 결과: `a90_android_execns_probe v6` + `--null-device-mode dev-null` 실기 PASS, decision `android-linker-devnull-early-abort-cleared`
   - v239 해석: `/dev/null` char device `1:3` materialization만으로 `0xa1` early abort와 `SIGSEGV(11)`가 6-case matrix에서 사라졌다
   - 새 blocker: `cnss-daemon` linker-list가 정상 stderr로 `library "libcutils.so" not found`를 보고한다; 다음은 linker namespace/dependency search path 분류
   - v240 계획서: `docs/plans/NATIVE_INIT_V240_LINKER_NAMESPACE_GAP_PLAN_2026-05-18.md`
   - v240 host tool: `scripts/revalidation/wifi_linker_namespace_gap_probe.py`
   - v240 보고서: `docs/reports/NATIVE_INIT_V240_LINKER_NAMESPACE_GAP_2026-05-18.md`
   - v240 결과: decision `android-linker-vndk-apex-version-alias-gap`
   - v240 해석: real linkerconfig는 vendor target의 `libcutils.so`를 `vndk` linked namespace로 허용하지만, path는 `/apex/com.android.vndk.v30`를 가리키고 live system image는 `/apex/com.android.vndk.current`만 노출한다
   - 다음 blocker closure: v241에서 helper private namespace 안에서만 `com.android.vndk.v30 -> com.android.vndk.current` alias/materialization을 테스트한다
   - v241 계획서: `docs/plans/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_PLAN_2026-05-18.md`
   - v241 보고서: `docs/reports/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_2026-05-18.md`
   - v241 결과: decision `android-linker-vndk-apex-alias-cnss-list-pass`
   - v241 해석: private `/apex` symlink farm + `com.android.vndk.v30 -> /system/apex/com.android.vndk.current` alias로 `cnss-daemon` linker-list dependency graph가 양쪽 linker path에서 exit `0`으로 완료됐다
   - v242 계획서: `docs/plans/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_PLAN_2026-05-18.md`
   - v242 보고서: `docs/reports/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_2026-05-18.md`
   - v242 결과: decision `cnss-runtime-inventory-ready-for-launcher-contract-plan`
   - v242 해석: linker prerequisite은 닫혔지만 `cnss-daemon`은 user/group/capability, property socket, SELinux service context, diag/QRTR device, private path alias 계약이 필요하다
   - v243 계획서: `docs/plans/NATIVE_INIT_V243_CNSS_LAUNCHER_CONTRACT_PLAN_2026-05-18.md`
   - v243 보고서: `docs/reports/NATIVE_INIT_V243_CNSS_LAUNCHER_CONTRACT_PLAN_2026-05-18.md`
   - v243 결과: decision `cnss-launcher-contract-ready`
   - v243 해석: start-only runner는 `system=1000`, groups `inet=3003/net_admin=3005/wifi=1010`, `CAP_NET_ADMIN`, v241 private namespace를 만족해야 한다
   - v244 계획서: `docs/plans/NATIVE_INIT_V244_CNSS_IDENTITY_PROBE_PLAN_2026-05-19.md`
   - v244 보고서: `docs/reports/NATIVE_INIT_V244_CNSS_IDENTITY_PROBE_2026-05-19.md`
   - v244 결과: decision `cnss-identity-probe-pass`
   - v244 해석: non-starting harmless child에서 uid/gid/groups/`CAP_NET_ADMIN` 계약과 post-exec `/proc/self/status` 검증이 통과했다. dynamic exec에는 v241 symlink farm 대신 bind-backed private `/apex` farm이 필요했다
   - v245 계획서: `docs/plans/NATIVE_INIT_V245_CNSS_START_ONLY_RUNNER_PLAN_2026-05-19.md`
   - v245 보고서: `docs/reports/NATIVE_INIT_V245_CNSS_START_ONLY_RUNNER_2026-05-19.md`
   - v245 방향: v229 `runandroid` path를 버리고 v244 private namespace/helper 계약 기반의 controlled start-only runner를 만든다
   - v245 결과: `scripts/revalidation/wifi_cnss_start_only_runner.py` plan/preflight/dry-run PASS, live `run` 기본값은 fail-closed
   - v246 계획서: `docs/plans/NATIVE_INIT_V246_CNSS_START_ONLY_HELPER_MODE_PLAN_2026-05-19.md`
   - v246 보고서: `docs/reports/NATIVE_INIT_V246_CNSS_START_ONLY_HELPER_MODE_2026-05-19.md`
   - v246 결과: helper에 guarded `--mode cnss-start-only` / `--allow-cnss-start-only` 추가, no-allow 직접 실행은 `cnss_start.result=start-only-blocked`, runner plan/preflight/dry-run PASS, runner `run` 기본값은 fail-closed
   - v246 helper SHA-256: `5ae105f0d397f845cd602eb4b283cdbd817146eff9405d10c090320eded25c65`
   - v247 계획서: `docs/plans/NATIVE_INIT_V247_CNSS_START_OBSERVE_STOP_BODY_PLAN_2026-05-19.md`
   - v247 보고서: `docs/reports/NATIVE_INIT_V247_CNSS_START_OBSERVE_STOP_BODY_2026-05-19.md`
   - v247 결과: helper에 실제 start/observe/stop body와 host parser 구현 완료, static + safe no-start 검증 PASS, 직접 no-allow는 `cnss_start.result=start-only-blocked`, runner `plan`/`preflight`/`dry-run` PASS, runner `run` 기본값은 fail-closed
   - v247 helper SHA-256: `77fbdcdcbc6774abe5e34712097496edbac4a4ed763d87c82cf02effb88cd319`
   - v248 계획서: `docs/plans/NATIVE_INIT_V248_CNSS_RUNTIME_PRIMITIVE_PREFLIGHT_PLAN_2026-05-19.md`
   - v248 보고서: `docs/reports/NATIVE_INIT_V248_CNSS_RUNTIME_PRIMITIVES_PREFLIGHT_2026-05-19.md`
   - v248 결과: decision `cnss-runtime-primitives-ready-for-live-approval`, daemon start not executed, helper no-allow namespace/guard PASS, private `/vendor/bin/cnss-daemon` target evidence PASS
   - v248 runtime gaps: property service/socket area, SELinux null, `/dev/diag`, `/dev/qrtr`, global `/vendor` remain missing/expected gaps
   - v249 계획서: `docs/plans/NATIVE_INIT_V249_CNSS_RUNTIME_GAP_CLASSIFIER_PLAN_2026-05-19.md`
   - v249 보고서: `docs/reports/NATIVE_INIT_V249_CNSS_RUNTIME_GAP_CLASSIFIER_2026-05-19.md`
   - v249 결과: decision `cnss-runtime-gaps-classified`, daemon start not executed, `QIPCRTR` kernel family present, helper `dev-null-selinux` no-allow materialization PASS
   - v249 해석: property service/area는 Android-init-owned gap, QRTR은 kernel family가 아니라 userspace nameservice/endpoint risk, diag는 `cnss_diag` phase2 blocker
   - v250 계획서: `docs/plans/NATIVE_INIT_V250_QRTR_SOCKET_PROBE_PLAN_2026-05-19.md`
   - v250 보고서: `docs/reports/NATIVE_INIT_V250_QRTR_SOCKET_PROBE_2026-05-19.md`
   - v250 결과: decision `qrtr-socket-local-bind-pass`, daemon start not executed, `AF_QIPCRTR` socket open and local ephemeral bind PASS, no send/connect
   - v250 해석: QRTR은 kernel socket-family/local bind 수준에서는 blocker가 아니며, 남은 리스크는 userspace nameservice/endpoint behavior
   - v262 계획서: `docs/plans/NATIVE_INIT_V262_QRTR_QMI_NO_SCAN_PROBE_PLAN_2026-05-19.md`
   - v262 보고서: `docs/reports/NATIVE_INIT_V262_QRTR_QMI_NO_SCAN_PROBE_2026-05-19.md`
   - v262 결과: decision `qrtr-qmi-no-scan-ready`, v261 clean baseline에서 CNSS process clean, `QIPCRTR` protocol present, QRTR helper `bind-pass`, no send/connect, no `wlan*` link surface
   - v262 해석: `/dev/qrtr`, `/dev/diag`, `/dev/ipa`, `/dev/wlan`은 여전히 absent이고 남은 gap은 userspace/runtime endpoint 또는 nameservice behavior다. 실제 packet transmission은 별도 explicit approval gate 뒤로 둔다
   - v263 계획서: `docs/plans/NATIVE_INIT_V263_CNSS_WARNING_DISPOSITION_PLAN_2026-05-19.md`
   - v263 보고서: `docs/reports/NATIVE_INIT_V263_CNSS_WARNING_DISPOSITION_2026-05-19.md`
   - v263 결과: decision `cnss-warning-disposition-ready`, `perfd-client-unavailable`과 `kmsg-write-denied`는 start-only 허용 경고로 분류, `shell-quote-noise`는 kmsg logging-path noise로 병합
   - v263 approved live retry: `tmp/wifi/v263-cnss-live-retry-20260519-091608/`, decision `start-only-pass`, postflight `cnss-process-clean`
   - v263 해석: start-only를 막는 경고는 남지 않았지만 broader Wi-Fi 전에는 perfd/property/kmsg shim을 opt-in으로 설계해야 한다
   - v264 계획서: `docs/plans/NATIVE_INIT_V264_QRTR_QMI_NAMESERVICE_MODEL_PLAN_2026-05-19.md`
   - v264 보고서: `docs/reports/NATIVE_INIT_V264_QRTR_QMI_NAMESERVICE_MODEL_2026-05-19.md`
   - v264 결과: decision `qrtr-qmi-userspace-model-ready`, QRTR/QMI userspace boundary modeled without packet transmission
   - v264 해석: QRTR kernel socket readiness는 충분조건이 아니며, nameservice/QMI request transmission은 별도 explicit approval gate가 필요하다
   - v265 계획서: `docs/plans/NATIVE_INIT_V265_QRTR_NAMESERVICE_APPROVAL_CONTRACT_PLAN_2026-05-19.md`
   - v265 보고서: `docs/reports/NATIVE_INIT_V265_QRTR_NAMESERVICE_APPROVAL_CONTRACT_2026-05-19.md`
   - v265 결과: decision `qrtr-nameservice-approval-contract-ready`, future command template generated but not executed
   - v265 해석: 다음 QRTR nameservice no-scan runner는 구현 가능하지만 실제 packet transmission은 명시 승인이 필요하다
   - v266 계획서: `docs/plans/NATIVE_INIT_V266_QRTR_NAMESERVICE_RUNNER_SKELETON_PLAN_2026-05-19.md`
   - v266 보고서: `docs/reports/NATIVE_INIT_V266_QRTR_NAMESERVICE_RUNNER_SKELETON_2026-05-19.md`
   - v266 결과: runner skeleton PASS, read-only preflight PASS, no-approval run fail-closed PASS, approval-flag run still `transmit-not-implemented`
   - v266 해석: 실제 QRTR packet 송신은 아직 구현되지 않았고, v267 helper design 또는 explicit approval-gated bounded run이 다음 경계다
   - v267 계획서: `docs/plans/NATIVE_INIT_V267_QRTR_PACKET_LAYOUT_PLAN_2026-05-19.md`
   - v267 보고서: `docs/reports/NATIVE_INIT_V267_QRTR_PACKET_LAYOUT_2026-05-19.md`
   - v267 결과: `QRTR_TYPE_NEW_LOOKUP`/`DEL_LOOKUP` 20-byte little-endian packet layout generated, wildcard lookup block verified
   - v267 해석: helper code review에 필요한 byte layout은 준비됐지만 실제 QRTR 송신은 여전히 explicit approval-gated다
   - v268 계획서: `docs/plans/NATIVE_INIT_V268_QRTR_NS_HELPER_SOURCE_PLAN_2026-05-19.md`
   - v268 보고서: `docs/reports/NATIVE_INIT_V268_QRTR_NS_HELPER_SOURCE_2026-05-19.md`
   - v268 결과: `a90_qrtr_ns_probe.c` source/build PASS, static ARM64 helper hash `c2d8707155b776c6c31e815136a66060f2087c4606c8a48cf9bd4b7944fdbb2a`
   - v268 해석: transmit-capable helper source exists but was not deployed or executed; actual lookup remains explicit approval gated
   - v269 계획서: `docs/plans/NATIVE_INIT_V269_QRTR_NAMESERVICE_LIVE_RETRY_PLAN_2026-05-19.md`
   - v269 보고서: `docs/reports/NATIVE_INIT_V269_QRTR_NAMESERVICE_LIVE_RETRY_2026-05-19.md`
   - v269 결과: explicit approval-gated `a90_qrtr_ns_probe` deploy/run PASS, `QRTR_TYPE_NEW_LOOKUP` + cleanup `DEL_LOOKUP` sent for service `1` instance `1`, `qrtr_ns.status=lookup-sent`, `qmi_attempted=0`
   - v269 해석: basic QRTR nameservice send path is no longer the blocker; no `cnss-daemon` or `wlan*` appeared, so next blocker is endpoint/service visibility and possible QMI-control discovery under a separate approval gate
   - v270 계획서: `docs/plans/NATIVE_INIT_V270_QRTR_NAMESERVICE_READBACK_PLAN_2026-05-19.md`
   - v270 보고서: `docs/reports/NATIVE_INIT_V270_QRTR_NAMESERVICE_READBACK_2026-05-19.md`
   - v270 결과: `a90_qrtr_ns_probe v2` readback PASS, 1s/3s windows both `qrtr-ns-readback-timeout`, events `0`, service events `0`, `qmi_attempted=0`
   - v270 해석: QRTR nameservice control send works but service `1` instance `1` produced no visible nameservice notification; next is service/instance evidence correlation before any QMI-control payload plan
   - v271 계획서: `docs/plans/NATIVE_INIT_V271_QRTR_SERVICE_SELECTOR_PLAN_2026-05-19.md`
   - v271 보고서: `docs/reports/NATIVE_INIT_V271_QRTR_SERVICE_SELECTOR_2026-05-19.md`
   - v271 결과: host-only selector PASS, decision `qrtr-service-selector-ready`, service `1`/instance `1` negative evidence confirmed, DMS strong service-object-backed candidate, WLFW strong but unresolved
   - v271 해석: 다음 단계는 QMI payload가 아니라 real service object 기반 numeric service id extraction이다. QRTR/QMI live payload는 계속 별도 approval gate로 둔다
   - v272 계획서: `docs/plans/NATIVE_INIT_V272_QMI_SERVICE_OBJECT_EXTRACTOR_PLAN_2026-05-19.md`
   - v272 보고서: `docs/reports/NATIVE_INIT_V272_QMI_SERVICE_OBJECT_EXTRACTOR_2026-05-19.md`
   - v272 결과: host-only ELF parser PASS, decision `qmi-service-object-ids-extracted`, DMS service id `2`, service id `1` maps to WDS, WLFW exported object unresolved
   - v272 해석: v269/v270의 service `1` 실험은 WDS 기반 negative evidence로 정리한다. 다음은 DMS `2` visibility matrix 또는 WLFW service-object locator이며 QMI payload는 계속 금지한다
   - v273 계획서: `docs/plans/NATIVE_INIT_V273_QRTR_READBACK_MATRIX_PLAN_2026-05-19.md`
   - v273 보고서: `docs/reports/NATIVE_INIT_V273_QRTR_READBACK_MATRIX_2026-05-19.md`
   - v273 결과: approved bounded matrix PASS, WDS `1`/DMS `2` with instances `0,1` all `qrtr-readback-matrix-timeout`, events `0`, `qmi_attempted=0`
   - v273 해석: DMS/WDS visible service lookup도 현재 native state에서 QRTR service notification을 만들지 않는다. 다음은 WLFW service-object locator 또는 CNSS/runtime endpoint registration 조건 분석이다
   - v274 계획서: `docs/plans/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_PLAN_2026-05-19.md`
   - v274 보고서: `docs/reports/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_2026-05-19.md`
   - v274 결과: host-only locator PASS, decision `wlfw-service-id-source-backed`, WLFW service id `0x45` / `69`, version `1`, local CNSS WLFW strings matched
   - v274 해석: 다음 live 후보는 WLFW service `0x45` instance `0,1`에 대한 bounded QRTR nameservice readback이다. QMI payload는 계속 금지한다
   - v251 계획서: `docs/plans/NATIVE_INIT_V251_CNSS_PROPERTY_SURFACE_PLAN_2026-05-19.md`
   - v251 보고서: `docs/reports/NATIVE_INIT_V251_CNSS_PROPERTY_SURFACE_2026-05-19.md`
   - v251 결과: decision `cnss-property-read-only-surface`, host-only analysis, property read symbols `property_get`/`property_get_int32`, no property write/control symbols detected
   - v251 해석: property service/area gap은 write/control risk보다 read/default risk이며, `/data/vendor/wifi/sockets/...`는 별도 runtime filesystem/socket surface로 분리
   - v252 계획서: `docs/plans/NATIVE_INIT_V252_CNSS_DATA_WIFI_SURFACE_PLAN_2026-05-19.md`
   - v252 보고서: `docs/reports/NATIVE_INIT_V252_CNSS_DATA_WIFI_SURFACE_2026-05-19.md`
   - v252 결과: decision `cnss-data-wifi-surface-missing`, `/data`는 있으나 `/data/vendor`, `/data/vendor/wifi`, `/data/vendor/wifi/sockets`는 missing, daemon start not executed
   - v252 해석: runtime Wi-Fi data tree는 property service/QRTR와 별도 gap이며, helper private namespace 안에서만 materialize할지 별도 계획 필요
   - v253 계획서: `docs/plans/NATIVE_INIT_V253_PRIVATE_DATA_WIFI_MATERIALIZATION_PLAN_2026-05-19.md`
   - v253 보고서: `docs/reports/NATIVE_INIT_V253_PRIVATE_DATA_WIFI_MATERIALIZATION_2026-05-19.md`
   - v253 결과: decision `private-data-wifi-materialization-pass`, helper v9 SHA `80e8afb1b77fdba23dfbc71d6a8e17e5a2a095ed1de728474fd2855923c351a1`, private `/data/vendor/wifi/sockets` materialization PASS, real `/data/vendor/wifi` remains missing
   - v253 해석: runtime data tree gap은 helper private namespace 안에서 닫을 수 있음. 다음 live profile에는 `dev-null-selinux` + `private-empty` 조합을 제안할 수 있으나 실행은 여전히 approval-gated
   - v254 계획서: `docs/plans/NATIVE_INIT_V254_START_ONLY_PROFILE_REFRESH_PLAN_2026-05-19.md`
   - v254 보고서: `docs/reports/NATIVE_INIT_V254_START_ONLY_PROFILE_REFRESH_2026-05-19.md`
   - v254 결과: decision `start-only-profile-refresh-pass`, runner default profile updated to `--null-device-mode dev-null-selinux` + `--data-wifi-mode private-empty`, helper no-allow validation kept `cnss_start.result=start-only-blocked` and `exec_attempted=0`
   - v254 해석: latest no-start runtime shims are now the default proposed start-only profile. This is still approval-gated and does not execute the daemon by default
   - v255 계획서: `docs/plans/NATIVE_INIT_V255_CNSS_LIVE_APPROVAL_PACKET_PLAN_2026-05-19.md`
   - v255 보고서: `docs/reports/NATIVE_INIT_V255_CNSS_LIVE_APPROVAL_PACKET_2026-05-19.md`
   - v255 결과: decision `live-approval-packet-ready`, generated exact manual live command, helper no-allow remained `start-only-blocked`, real `/data/vendor/wifi` state unchanged, no daemon execution
   - v255 live attempt: explicit approval 후 실행했으나 `manual-review-required`, helper가 signal 15로 종료되고 `cnss-daemon` PID 5900이 남음. manual `kill -TERM 5900`으로 회수했고 최종 `pidof cnss-daemon` rc=1, `/proc/net/dev`에 `wlan*` 없음
   - v256 계획서: `docs/plans/NATIVE_INIT_V256_CNSS_CLEANUP_RACE_FIX_PLAN_2026-05-19.md`
   - v256 보고서: `docs/reports/NATIVE_INIT_V256_CNSS_CLEANUP_RACE_FIX_2026-05-19.md`
   - v256 결과: helper v10 SHA `1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750`, child `setsid()` pgid race fix, no-allow validation PASS, runner plan/preflight/dry-run PASS, v10 approval packet PASS
   - v256 해석: first live proved daemon can start far enough to persist, but cleanup race made the result unsafe. Future live retry requires v10 helper and explicit operator approval
   - v257 계획서: `docs/plans/NATIVE_INIT_V257_CNSS_V10_LIVE_RETRY_PLAN_2026-05-19.md`
   - v257 보고서: `docs/reports/NATIVE_INIT_V257_CNSS_V10_LIVE_RETRY_2026-05-19.md`
   - v257 결과: explicit approval 후 v10 bounded live retry PASS, decision `start-only-pass`, `cnss_start.observable=1`, `reaped=1`, `postflight_safe=1`, final `pidof cnss-daemon` rc=1, `/proc/net/dev`에 `wlan*` 없음
   - v257 해석: `cnss-daemon -n -l` start/observe/stop/reap primitive는 검증됐다. 아직 Wi-Fi scan/connect/link-up/credential/DHCP/routing readiness는 아니다
   - v258 계획서: `docs/plans/NATIVE_INIT_V258_CNSS_LIVE_EVIDENCE_ANALYZER_PLAN_2026-05-19.md`
   - v258 보고서: `docs/reports/NATIVE_INIT_V258_CNSS_LIVE_EVIDENCE_ANALYZER_2026-05-19.md`
   - v258 결과: `scripts/revalidation/wifi_cnss_live_evidence_analyzer.py` 구현, V257 evidence를 `cnss-start-only-evidence-classified`로 분류, checks `11/11` PASS
   - v258 해석: lifecycle/identity/namespace/maps/postflight는 pass. runtime warning은 `perfd-client-unavailable`, `kmsg-write-denied`, `shell-quote-noise`
   - v259 계획서: `docs/plans/NATIVE_INIT_V259_CNSS_WARNING_SURFACE_PLAN_2026-05-19.md`
   - v259 보고서: `docs/reports/NATIVE_INIT_V259_CNSS_WARNING_SURFACE_2026-05-19.md`
   - v259 결과: `scripts/revalidation/wifi_cnss_warning_surface_probe.py` 구현, decision `cnss-warning-surface-classified`, daemon 실행 없이 PASS
   - v259 해석: perfd client surface는 있으나 runtime socket 없음, Android property service/socket/area 없음, kmsg/quote noise는 helper source가 아니라 daemon/library logging-path stderr로 분류
   - v260 계획서: `docs/plans/NATIVE_INIT_V260_CNSS_ZOMBIE_POSTFLIGHT_PLAN_2026-05-19.md`
   - v260 보고서: `docs/reports/NATIVE_INIT_V260_CNSS_ZOMBIE_POSTFLIGHT_2026-05-19.md`
   - v260 결과: `scripts/revalidation/wifi_cnss_zombie_audit.py` 구현, current session에서 `5900 Zs [cnss-daemon]` PID1 zombie 확인, runner preflight는 `start-only-blocked`, analyzer는 process evidence 제공 시 `cnss-start-only-evidence-incomplete`
   - v260 해석: `pidof` absence만으로 CNSS cleanup을 판정하면 안 된다. 다음 live retry/QRTR probe 전 clean-state 또는 PID1 reaper hardening이 필요하다
   - v261 계획서: `docs/plans/NATIVE_INIT_V261_PID1_ORPHAN_REAPER_PLAN_2026-05-19.md`
   - v261 보고서: `docs/reports/NATIVE_INIT_V261_PID1_ORPHAN_REAPER_2026-05-19.md`
   - v261 결과: `A90 Linux init 0.9.60 (v261)` 실기 플래시 PASS, `reaper [status|run|verbose]` 추가, `pid1guard` reaper 항목 PASS, CNSS zombie audit clean PASS
   - v261 live retry: explicit approval 후 bounded CNSS start-only retry PASS, decision `start-only-pass`, `reaped=1`, `postflight_safe=1`, postflight CNSS process clean PASS
   - v261 해석: PID1 orphan reaper와 process-table audit gate가 동작한다. 다음 후보는 QRTR/QMI endpoint interaction no-scan probe 또는 CNSS warning/perfd/kmsg noise 개선이다
   - v274 계획서: `docs/plans/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_PLAN_2026-05-19.md`
   - v274 보고서: `docs/reports/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_2026-05-19.md`
   - v274 결과: decision `wlfw-service-id-source-backed`, WLFW service id `69`/`0x45`, version `1`, local cnss-daemon WLFW string coverage PASS
   - v275 계획서: `docs/plans/NATIVE_INIT_V275_WLFW_QRTR_READBACK_PLAN_2026-05-19.md`
   - v275 보고서: `docs/reports/NATIVE_INIT_V275_WLFW_QRTR_READBACK_2026-05-19.md`
   - v275 결과: decision `qrtr-readback-matrix-timeout`, WLFW service `69` instance `0/1` both timeout with events `0`, service_events `0`, qmi_attempted `0`
   - v275 해석: WDS/DMS/WLFW 모두 native QRTR nameservice readback에서 notification이 없으므로 다음은 QMI payload가 아니라 QRTR/CNSS registration-state correlation이다
   - v276 계획서: `docs/plans/NATIVE_INIT_V276_QRTR_CNSS_REGISTRATION_CORRELATION_PLAN_2026-05-19.md`
   - v276 보고서: `docs/reports/NATIVE_INIT_V276_QRTR_CNSS_REGISTRATION_CORRELATION_2026-05-19.md`
   - v276 결과: decision `qrtr-cnss-platform-surface-visible`, QIPCRTR/no-send probe PASS, active `/dev` endpoint `0`, `/sys` CNSS/WLAN/QRTR surfaces `68`, cnss process clean, no `wlan*`
   - v276 해석: QRTR socket readiness가 blocker는 아니며, static platform state를 read-only로 더 좁혀야 한다. QMI payload는 계속 blocked
   - v277 계획서: `docs/plans/NATIVE_INIT_V277_ICNSS_PLATFORM_SURFACE_PLAN_2026-05-19.md`
   - v277 보고서: `docs/reports/NATIVE_INIT_V277_ICNSS_PLATFORM_SURFACE_2026-05-19.md`
   - v277 결과: decision `icnss-platform-present-no-wlan-netdev`, ICNSS node/driver/device present, QCA6390 node present but driver link absent, `/sys/module/wlan` present but no `wlan*`/wiphy/rfkill
   - v277 해석: 플랫폼/펌웨어 경로는 보이지만 QCA6390 driver lifecycle 또는 userspace sequencing 전 netdev registration이 빠져 있다. QMI payload는 계속 blocked
   - v278 계획서: `docs/plans/NATIVE_INIT_V278_QCA6390_DRIVER_PARAM_PLAN_2026-05-19.md`
   - v278 보고서: `docs/reports/NATIVE_INIT_V278_QCA6390_DRIVER_PARAM_2026-05-19.md`
   - v278 결과: decision `qca6390-match-visible-driver-unbound`, QCA6390 compatible/modalias visible, driver link absent, WLAN params 9/9 readable (`fwpath` empty, `country_code=(null)`, `con_mode=0`), no `wlan*`/wiphy/rfkill
   - v278 해석: QCA6390 OF match는 있으나 native state에서 driver binding이 없다. 다음은 CNSS/QCA6390 probe expectation 비교 또는 명시 승인 start-only delta observation이다
   - v279 계획서: `docs/plans/NATIVE_INIT_V279_CNSS_QCA6390_START_DELTA_PLAN_2026-05-19.md`
   - v279 보고서: `docs/reports/NATIVE_INIT_V279_CNSS_QCA6390_START_DELTA_2026-05-19.md`
   - v279 결과: decision `cnss-qca6390-no-driver-delta`, guarded CNSS start-only PASS, QCA6390 driver link absent before/after, WLAN params unchanged, no `wlan*`/wiphy/rfkill, postflight process clean
   - v279 해석: start-only alone does not bind QCA6390 or change WLAN parameter state. 다음은 no-start CNSS/QCA6390 source/sysfs expectation comparison, read-only kernel log extraction, or separately approved QRTR/WLFW readback during start-only이다
   - v280 계획서: `docs/plans/NATIVE_INIT_V280_CNSS_QCA6390_PROBE_EXPECTATION_PLAN_2026-05-19.md`
   - v280 보고서: `docs/reports/NATIVE_INIT_V280_CNSS_QCA6390_PROBE_EXPECTATION_2026-05-19.md`
   - v280 결과: decision `cnss2-driver-dir-missing-qca-unbound`, QCA6390 compatible/modalias visible, QCA6390 driver link absent, `/sys/bus/platform/drivers/cnss2` absent, `/sys/bus/platform/drivers/icnss` present, `CONFIG_CNSS2=n`, no `wlan*`/wiphy
   - v280 해석: CNSS2 source model is not the live kernel binding model. 다음은 live `icnss` driver model/source/sysfs expectation comparison이다
   - v281 계획서: `docs/plans/NATIVE_INIT_V281_ICNSS_PROBE_EXPECTATION_PLAN_2026-05-19.md`
   - v281 보고서: `docs/reports/NATIVE_INIT_V281_ICNSS_PROBE_EXPECTATION_2026-05-19.md`
   - v281 결과: decision `icnss-core-bound-host-driver-waits-fw`, ICNSS core bound, QCA6390 context visible, WLAN module sysfs present, `CONFIG_ICNSS=y`, `CONFIG_ICNSS_QMI=y`, no `wlan*`/wiphy
   - v281 해석: live model은 ICNSS core plus WLAN host-driver registration이며 host-driver probe는 firmware-ready/QMI state를 기다리는 구조다
   - v282 계획서: `docs/plans/NATIVE_INIT_V282_ICNSS_WLFW_READINESS_SURFACE_PLAN_2026-05-19.md`
   - v282 보고서: `docs/reports/NATIVE_INIT_V282_ICNSS_WLFW_READINESS_SURFACE_2026-05-19.md`
   - v282 결과: decision `icnss-readiness-sysfs-candidates-limited`, ICNSS core bound, WLAN module sysfs present, `CONFIG_DEBUG_FS=y`, `CONFIG_ICNSS_DEBUG=n`, `/sys/kernel/debug/icnss` absent, no readiness dmesg, no `wlan*`/wiphy
   - v282 해석: no-start 상태에서 직접 WLFW firmware-ready state file은 보이지 않는다. 다음은 검증된 start-only primitive로 before/during/after readiness delta를 관찰하는 v283이다
   - v283 계획서: `docs/plans/NATIVE_INIT_V283_ICNSS_WLFW_START_DELTA_PLAN_2026-05-19.md`
   - v283 보고서: `docs/reports/NATIVE_INIT_V283_ICNSS_WLFW_START_DELTA_2026-05-19.md`
   - v283 결과: decision `icnss-wlfw-start-no-readiness-delta`, nested runner `start-only-pass`, child pid/pgid `1077/1077`, reaped, postflight clean, dmesg readiness `0 -> 0`, sysfs candidates `13 -> 13`, no `wlan*`/wiphy
   - v283 해석: `cnss-daemon -n -l` start-only는 안전하게 실행/정리되지만 ICNSS/WLFW readiness surface를 바꾸지 않는다. 반복보다는 NCM/tcpctl 또는 broker 기반 concurrent side-channel observer가 다음 후보이다
   - v284 계획서: `docs/plans/NATIVE_INIT_V284_CNSS_CONCURRENT_SIDECHANNEL_PLAN_2026-05-19.md`
   - v284 보고서: `docs/reports/NATIVE_INIT_V284_CNSS_CONCURRENT_SIDECHANNEL_2026-05-19.md`
   - v284 결과: decision `cnss-sidechannel-no-readiness-delta`, serial CNSS start-only `start-only-pass`, NCM/tcpctl 12/12 concurrent samples PASS, no readiness lines, no `wlan*`/wiphy, postflight clean
   - v284 해석: side-channel 구조는 동작한다. 다음은 같은 구조로 ICNSS/QCA6390 sysfs/module/interrupt/dmesg 상태를 더 좁게 샘플링하는 v285가 적절하다
   - v285 계획서: `docs/plans/NATIVE_INIT_V285_ICNSS_QCA6390_DURING_START_PLAN_2026-05-19.md`
   - v285 보고서: `docs/reports/NATIVE_INIT_V285_ICNSS_QCA6390_DURING_START_2026-05-19.md`
   - v285 결과: decision `icnss-qca6390-focused-no-during-delta`, serial CNSS start-only `start-only-pass`, NCM/tcpctl 19 focused samples PASS, focused delta `0`, no `wlan*`/wiphy, postflight clean
   - v285 해석: focused ICNSS/QCA6390 during-start sampling also shows no state delta. 동일 start-only 반복보다는 Android/TWRP/native ICNSS boot timing 비교가 다음 후보이다
   - v286 계획서: `docs/plans/NATIVE_INIT_V286_ICNSS_BOOT_TIMING_COMPARE_PLAN_2026-05-19.md`
   - v286 보고서: `docs/reports/NATIVE_INIT_V286_ICNSS_BOOT_TIMING_COMPARE_2026-05-19.md`
   - v286 결과: decision `icnss-boot-timing-gap-mapped`, first missing native event `android_wifi_action`, Android Wi-Fi service/WLFW/QMI readiness chain visible around `7s..15s`, native boot-window evidence lacks that chain
   - v286 해석: 다음은 blind start-only 반복이 아니라 Android Wi-Fi service-order replay plan이다. QMI payload와 link-up은 계속 blocked
   - v287 계획서: `docs/plans/NATIVE_INIT_V287_WIFI_SERVICE_ORDER_REPLAY_PLAN_2026-05-19.md`
   - v287 보고서: `docs/reports/NATIVE_INIT_V287_WIFI_SERVICE_ORDER_REPLAY_MODEL_2026-05-19.md`
   - v287 결과: decision `wifi-service-order-replay-model-ready`, first missing service boundary `vendor.wifi_hal_ext`, `cnss-daemon`은 bounded start-only candidate로만 유지, Wi-Fi HAL/`cnss_diag`/`wificond`/supplicant/hostapd는 blocked
   - v287 해석: 다음은 HAL/framework boundary inventory이다. binder/hwbinder/hwservicemanager/VINTF/property/socket/SELinux/capability/linker namespace를 확인하기 전 HAL 또는 `wificond` 실행은 금지한다
   - v288 계획서: `docs/plans/NATIVE_INIT_V288_HAL_FRAMEWORK_BOUNDARY_PLAN_2026-05-19.md`
   - v288 보고서: `docs/reports/NATIVE_INIT_V288_HAL_FRAMEWORK_BOUNDARY_2026-05-19.md`
   - v288 결과: decision `hal-framework-boundary-native-blocked`, native `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder`, service-manager process, property runtime이 blocker로 확인됨
   - v288 해석: binary/VINTF 일부가 보여도 HAL/`wificond` 실행 준비는 아니다. 다음은 Binder/service-manager feasibility inventory가 우선이다
   - v289 계획서: `docs/plans/NATIVE_INIT_V289_BINDER_SERVICE_MANAGER_FEASIBILITY_PLAN_2026-05-19.md`
   - v289 보고서: `docs/reports/NATIVE_INIT_V289_BINDER_SERVICE_MANAGER_FEASIBILITY_2026-05-19.md`
   - v289 결과: decision `binder-kernel-present-devnodes-missing`, `CONFIG_ANDROID_BINDER_IPC=y`, `CONFIG_ANDROID_BINDER_DEVICES=binder,hwbinder,vndbinder`, `/proc/misc` Binder devices present, native Binder `/dev` nodes absent, binderfs absent
   - v289 해석: Binder 커널 지원은 있으나 native init이 Binder devnode를 만들지 않는다. 다음은 service-manager/HAL 실행이 아니라 private Binder devnode feasibility plan이다
   - v290 계획서: `docs/plans/NATIVE_INIT_V290_BINDER_DEVNODE_FEASIBILITY_PLAN_2026-05-19.md`
   - v290 보고서: `docs/reports/NATIVE_INIT_V290_BINDER_DEVNODE_FEASIBILITY_2026-05-19.md`
   - v290 결과: decision `binder-devnode-plan-ready`, Binder devnode 후보 `10:81`, `10:80`, `10:79` 확인, native `/dev` 노드는 계속 absent
   - v290 해석: 다음은 read-only inventory가 아니라 temporary Binder devnode create/cleanup smoke이다. 이는 `mknod`를 수행하는 non-read-only 단계이므로 실행 전 범위가 명확해야 한다
   - v291 계획서: `docs/plans/NATIVE_INIT_V291_BINDER_DEVNODE_SMOKE_PLAN_2026-05-19.md`
   - v291 보고서: `docs/reports/NATIVE_INIT_V291_BINDER_DEVNODE_SMOKE_2026-05-19.md`
   - v291 결과: decision `binder-devnode-create-cleanup-pass`, 세 Binder devnode를 `mknodc`로 생성하고 `stat` 확인 후 `toybox rm -f`로 정리 PASS
   - v291 해석: native `/dev` Binder surface는 임시 복구 가능하다. 다음은 Binder protocol이 아니라 open/close만 검증하는 static helper smoke이다
   - v292 계획서: `docs/plans/NATIVE_INIT_V292_BINDER_OPEN_SMOKE_PLAN_2026-05-19.md`
   - v292 보고서: `docs/reports/NATIVE_INIT_V292_BINDER_OPEN_SMOKE_2026-05-19.md`
   - v292 결과: decision `binder-open-only-smoke-pass`, `toybox dd if=/dev/<binder-node> of=/dev/null bs=1 count=0`로 세 Binder domain open/close PASS, cleanup PASS
   - v292 해석: Binder device open 최저 레벨 blocker는 제거됐다. 다음은 service-manager process/property/SELinux/linker namespace prerequisite model이며, HAL/`wificond` 실행은 아직 금지다
   - v293 계획서: `docs/plans/NATIVE_INIT_V293_SERVICE_MANAGER_PREREQ_PLAN_2026-05-19.md`
   - v293 보고서: `docs/reports/NATIVE_INIT_V293_SERVICE_MANAGER_PREREQ_2026-05-19.md`
   - v293 결과: decision `service-manager-prereq-blockers-mapped`, service-manager process model absent, Android property runtime absent, linker/runtime partial
   - v293 해석: Binder open은 통과했지만 service-manager 실행은 아직 이르다. 다음은 property-runtime feasibility inventory이다
   - v294 계획서: `docs/plans/NATIVE_INIT_V294_PROPERTY_RUNTIME_FEASIBILITY_PLAN_2026-05-19.md`
   - v294 보고서: `docs/reports/NATIVE_INIT_V294_PROPERTY_RUNTIME_FEASIBILITY_2026-05-19.md`
   - v294 결과: decision `property-runtime-inputs-visible-runtime-absent`, mounted property contexts/build props visible, `/dev/socket/property_service`, `/dev/__properties__`, `/dev/socket` absent
   - v294 해석: Android property 입력은 보이지만 runtime은 없다. 다음은 service-manager 실행이 아니라 read-only property snapshot/shim model이다
   - v295 계획서: `docs/plans/NATIVE_INIT_V295_PROPERTY_SNAPSHOT_MODEL_PLAN_2026-05-19.md`
   - v295 보고서: `docs/reports/NATIVE_INIT_V295_PROPERTY_SNAPSHOT_MODEL_2026-05-19.md`
   - v295 결과: decision `property-snapshot-model-ready`, static property `248`개와 property context `1264`라인 파싱, Wi-Fi 관련 property `7`개, selected required baseline `1/4`
   - v295 해석: 정적 property snapshot은 만들 수 있으나 live property runtime은 아니다. 다음은 property shim strategy model이다
   - v296 계획서: `docs/plans/NATIVE_INIT_V296_PROPERTY_SHIM_STRATEGY_PLAN_2026-05-19.md`
   - v296 보고서: `docs/reports/NATIVE_INIT_V296_PROPERTY_SHIM_STRATEGY_2026-05-19.md`
   - v296 결과: decision `property-shim-strategy-capture-needed`, static snapshot에서 `ro.product.name`, `ro.hardware`, `ro.vendor.build.version.sdk` 누락
   - v296 해석: property shim을 합성하기 전에 Android boot 상태의 `getprop`/property baseline capture가 필요하다
   - v297 계획서: `docs/plans/NATIVE_INIT_V297_ANDROID_PROPERTY_CAPTURE_PLAN_2026-05-19.md`
   - v297 보고서: `docs/reports/NATIVE_INIT_V297_ANDROID_PROPERTY_CAPTURE_2026-05-19.md`
   - v297 결과: host capture tool은 준비됐고 현재 native 상태에서는 decision `android-property-capture-waiting-for-android`
   - v297 해석: 다음 live 단계는 명시적으로 Android로 부팅한 뒤 read-only `getprop` baseline을 캡처하는 것이다. 그 전까지 native property runtime 생성과 service-manager 실행은 blocked
   - v298 계획서: `docs/plans/NATIVE_INIT_V298_PROPERTY_BASELINE_COMPARE_PLAN_2026-05-19.md`
   - v298 보고서: `docs/reports/NATIVE_INIT_V298_PROPERTY_BASELINE_COMPARE_2026-05-19.md`
   - v298 결과: decision `property-baseline-compare-waiting-for-android`, v297 Android capture manifest가 아직 없으므로 shim 설계는 blocked
   - v298 해석: 다음은 추가 host-only 모델이 아니라 Android boot 후 v297 capture 실행이다
   - v299 계획서: `docs/plans/NATIVE_INIT_V299_ANDROID_CAPTURE_HANDOFF_PLAN_2026-05-19.md`
   - v299 보고서: `docs/reports/NATIVE_INIT_V299_ANDROID_CAPTURE_HANDOFF_2026-05-19.md`
   - v299 결과: decision `android-capture-handoff-ready-needs-operator`, native rollback image와 Android boot candidate가 확인됐고 native bridge `version/status` PASS
   - v299 해석: Android property capture를 위해 boot partition 전환이 필요하므로 여기서 명시적 operator 승인 경계다. 승인 전 자동 reboot/flash는 하지 않는다
   - v300 계획서: `docs/plans/NATIVE_INIT_V300_ANDROID_CAPTURE_EXECUTOR_PLAN_2026-05-19.md`
   - v300 보고서: `docs/reports/NATIVE_INIT_V300_ANDROID_CAPTURE_EXECUTOR_2026-05-19.md`
   - v300 결과: decision `android-capture-executor-dryrun-ready`, 승인 없는 `run`은 `android-capture-executor-approval-required`로 거부됨
   - v300 해석: live Android handoff 실행기는 준비됐지만 `--allow-android-boot-flash --assume-yes --i-understand-native-rollback` 명시 승인 전까지 실행 금지
   - v301 계획서: `docs/plans/NATIVE_INIT_V301_PROPERTY_SHIM_SEED_PLAN_2026-05-19.md`
   - v301 보고서: `docs/reports/NATIVE_INIT_V301_PROPERTY_SHIM_SEED_2026-05-19.md`
   - v301 결과: decision `property-shim-seed-waiting-for-android`, `seed.json`은 생성됐지만 모든 selected key가 Android capture 부재로 blocked
   - v301 해석: 추가 host-only 모델은 준비됐고, 실제 unblock은 v300 live handoff로 Android capture를 얻는 것이다
   - v302 계획서: `docs/plans/NATIVE_INIT_V302_ANDROID_CAPTURE_APPROVAL_PACKET_PLAN_2026-05-19.md`
   - v302 보고서: `docs/reports/NATIVE_INIT_V302_ANDROID_CAPTURE_APPROVAL_PACKET_2026-05-19.md`
   - v302 결과: decision `android-capture-approval-ready`, v299/v300/current-native evidence를 묶은 final approval packet 생성
   - v302 pre-live audit: v300 executor와 `native_init_flash.py`가 explicit `--adb`/`--serial`을 Android capture 및 native rollback까지 전파하도록 보강했고, target-audit dry-run PASS
   - v302 해석: 이제 남은 것은 host-only 준비가 아니라 operator-approved live command 실행이다
   - v303 계획서: `docs/plans/NATIVE_INIT_V303_ANDROID_CAPTURE_POSTPROCESS_PLAN_2026-05-19.md`
   - v303 보고서: `docs/reports/NATIVE_INIT_V303_ANDROID_CAPTURE_POSTPROCESS_2026-05-19.md`
   - v303 결과: current decision `android-capture-postprocess-waiting-for-live`, synthetic ready path `android-capture-postprocess-seed-ready`
   - v303 해석: live 이후 v300/v297/v298/v301 결과 판독은 자동화됐고, 현재 blocker는 여전히 v300 live handoff 명시 승인이다
   - v304 계획서: `docs/plans/NATIVE_INIT_V304_ANDROID_CAPTURE_LIVE_GUARD_PLAN_2026-05-19.md`
   - v304 보고서: `docs/reports/NATIVE_INIT_V304_ANDROID_CAPTURE_LIVE_GUARD_2026-05-19.md`
   - v304 결과: decision `android-capture-live-guard-go`, v302 approval/v300 target propagation/image hash/native bridge/v303 waiting state PASS
   - v304 해석: host-side readiness is GO; destructive live handoff remains blocked only by explicit operator approval
   - v305 계획서: `docs/plans/NATIVE_INIT_V305_ANDROID_CAPTURE_RESCUE_DOCTOR_PLAN_2026-05-19.md`
   - v305 보고서: `docs/reports/NATIVE_INIT_V305_ANDROID_CAPTURE_RESCUE_DOCTOR_2026-05-19.md`
   - v305 결과: decision `native-ready`, rescue doctor generated live/rollback/capture operator aid commands without executing them
   - v306 계획서: `docs/plans/NATIVE_INIT_V306_ANDROID_CAPTURE_LIVE_RESULT_PLAN_2026-05-19.md`
   - v306 보고서: `docs/reports/NATIVE_INIT_V306_ANDROID_CAPTURE_LIVE_RESULT_2026-05-19.md`
   - v306 결과: approval-gated v300 live handoff PASS, Android property capture PASS, baseline compare READY, Android-backed seed READY, native v261 restored and verified
   - v306 해석: property shim 설계에 필요한 Android-backed required keys가 확보됐다. 다음 후보는 read-only property shim design이며, property runtime mutation/service-manager/HAL/Wi-Fi daemon/scan/connect는 계속 별도 safety gate 전까지 금지다
   - v307 계획서: `docs/plans/NATIVE_INIT_V307_PROPERTY_SHIM_DESIGN_PLAN_2026-05-19.md`
   - v307 보고서: `docs/reports/NATIVE_INIT_V307_PROPERTY_SHIM_DESIGN_2026-05-19.md`
   - v307 결과: decision `property-shim-design-model-ready`, selected next prototype `private-readonly-property-area`
   - v307 해석: 다음은 private namespace 안에서 read-only property area format/proof 모델을 만드는 것이며, global `/dev/__properties__`나 property service socket 생성은 여전히 금지다
   - v308 계획서: `docs/plans/NATIVE_INIT_V308_PRIVATE_PROPERTY_AREA_PROOF_PLAN_2026-05-19.md`
   - v308 보고서: `docs/reports/NATIVE_INIT_V308_PRIVATE_PROPERTY_AREA_PROOF_2026-05-19.md`
   - v308 결과: decision `private-property-area-proof-needs-format-source`
   - v308 해석: Android-backed seed는 read-only 모델 입력으로 유효하지만 property area binary layout과 serialized `property_info` compatibility가 아직 증명되지 않았다. 다음은 runtime node 생성이 아니라 AOSP source 기반 format extractor/proof이다
   - v309 계획서: `docs/plans/NATIVE_INIT_V309_PROPERTY_FORMAT_SOURCE_PROBE_PLAN_2026-05-19.md`
   - v309 보고서: `docs/reports/NATIVE_INIT_V309_PROPERTY_FORMAT_SOURCE_PROBE_2026-05-19.md`
   - v309 결과: decision `property-format-source-map-ready`
   - v309 해석: Android 12 AOSP source에서 property area constants, serialized `property_info` header/version, bionic `ContextsSerialized` read path를 확인했다. 다음은 여전히 host-only인 serializer/parser compatibility proof이며 runtime property file creation은 아직 금지다
   - v310 계획서: `docs/plans/NATIVE_INIT_V310_PROPERTY_SERIALIZER_PROOF_PLAN_2026-05-19.md`
   - v310 보고서: `docs/reports/NATIVE_INIT_V310_PROPERTY_SERIALIZER_PROOF_2026-05-19.md`
   - v310 결과: decision `property-serializer-proof-ready`
   - v310 해석: host-only `property_info`/`prop_area` binary roundtrip은 통과했다. 다만 synthetic context를 사용했으므로 다음은 실제 `property_contexts` 기반 context-aware mapping proof이며, runtime install은 아직 금지다
   - v311 계획서: `docs/plans/NATIVE_INIT_V311_PROPERTY_CONTEXT_MAPPING_PLAN_2026-05-19.md`
   - v311 보고서: `docs/reports/NATIVE_INIT_V311_PROPERTY_CONTEXT_MAPPING_2026-05-19.md`
   - v311 결과: decision `property-context-mapping-ready`
   - v311 해석: selected seed keys가 captured Android `property_contexts`로 실제 context/type에 매핑되고 context-aware `property_info` roundtrip도 통과했다. 다음은 live install이 아니라 private runtime layout package dry-run이다
   - v312 계획서: `docs/plans/NATIVE_INIT_V312_PRIVATE_PROPERTY_LAYOUT_PLAN_2026-05-19.md`
   - v312 보고서: `docs/reports/NATIVE_INIT_V312_PRIVATE_PROPERTY_LAYOUT_2026-05-19.md`
   - v312 결과: decision `private-property-layout-dryrun-ready`
   - v312 해석: private `/dev/__properties__` layout이 host-only로 생성/roundtrip 검증됐다. 다음은 실제 materialization이 아니라 명시적 approval packet 작성이며, live install/bind mount/daemon start는 계속 금지다
   - v313 계획서: `docs/plans/NATIVE_INIT_V313_PRIVATE_PROPERTY_MATERIALIZATION_APPROVAL_PLAN_2026-05-19.md`
   - v313 보고서: `docs/reports/NATIVE_INIT_V313_PRIVATE_PROPERTY_MATERIALIZATION_APPROVAL_2026-05-19.md`
   - v313 결과: decision `private-property-materialization-approval-ready`
   - v313 해석: 다음 v314는 live mutation boundary라서 `approve v314 private property namespace materialization only; no daemon start and no Wi-Fi bring-up` 문구의 명시 승인이 필요하다
   - v314 계획서: `docs/plans/NATIVE_INIT_V314_PRIVATE_PROPERTY_MATERIALIZATION_EXECUTOR_PLAN_2026-05-19.md`
   - v314 보고서: `docs/reports/NATIVE_INIT_V314_PRIVATE_PROPERTY_MATERIALIZATION_EXECUTOR_2026-05-19.md`
   - v314 결과: decisions `private-property-materialization-executor-plan-ready`, `private-property-materialization-executor-approval-required`, `private-property-materialization-executor-live-not-implemented`
   - v314 해석: executor scaffold가 future live sequence와 approval gate를 문서화했지만, v314는 device command/ADB command/generated file install/bind mount를 전혀 수행하지 않는다. 다음은 v315에서 더 작은 live-readonly proof를 둘지, 첫 private namespace materialization 구현으로 갈지 결정해야 한다
   - v315 계획서: `docs/plans/NATIVE_INIT_V315_PRIVATE_PROPERTY_LIVE_PREFLIGHT_PLAN_2026-05-19.md`
   - v315 보고서: `docs/reports/NATIVE_INIT_V315_PRIVATE_PROPERTY_LIVE_PREFLIGHT_2026-05-19.md`
   - v315 결과: decision `private-property-live-preflight-ready`
   - v315 해석: 실제 native v261 기기에서 version/status/selftest/storage/mountsd/logpath read-only preflight가 PASS했다. SD workspace는 rw 상태이고 netservice는 disabled, selftest는 fail=0이다. 다음 v316은 승인된 최소 private namespace copy/materialization proof 후보이며 daemon/Wi-Fi bring-up은 여전히 금지다
   - v316 계획서: `docs/plans/NATIVE_INIT_V316_PRIVATE_PROPERTY_LIVE_APPROVAL_PLAN_2026-05-19.md`
   - v316 보고서: `docs/reports/NATIVE_INIT_V316_PRIVATE_PROPERTY_LIVE_APPROVAL_2026-05-19.md`
   - v316 결과: decision `private-property-live-approval-ready`
   - v316 해석: v317 최소 private namespace proof의 승인 문구를 고정했다. 진행하려면 `approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up` 문구의 명시 승인이 필요하다
   - v317 계획서: `docs/plans/NATIVE_INIT_V317_PRIVATE_PROPERTY_NAMESPACE_PROOF_PLAN_2026-05-19.md`
   - v317 보고서: `docs/reports/NATIVE_INIT_V317_PRIVATE_PROPERTY_NAMESPACE_PROOF_2026-05-19.md`
   - v317 결과: decisions `private-property-namespace-proof-plan-ready`, `private-property-namespace-proof-approval-required`, `private-property-namespace-proof-audit-pass`, `private-property-namespace-proof-audit-selftest-pass`
   - v317 해석: runner는 구현됐고 plan/refusal/audit/selftest 검증은 PASS했다. 승인 후에도 범위는 `/mnt/sdext/a90/private-property-v317` private workdir 생성, v312 layout 파일 복사, SHA-256 검증, cleanup으로 제한한다. v316 승인 범위가 daemon start를 금지하므로 NCM/tcpctl 전송은 사용하지 않는다. 현재 전송 추정은 files 5, bytes 524988, chunks 471, estimated device commands 505이다
   - v318 계획서: `docs/plans/NATIVE_INIT_V318_PRIVATE_PROPERTY_TRANSFER_PRIMITIVE_PLAN_2026-05-19.md`
   - v318 보고서: `docs/reports/NATIVE_INIT_V318_PRIVATE_PROPERTY_TRANSFER_PRIMITIVE_2026-05-19.md`
   - v318 결과: decision `private-property-transfer-primitive-preflight-ready`
   - v318 해석: read-only live preflight에서 `toybox sh`가 없다는 사실을 확인했다. 따라서 v317 runner는 shell pipeline/base64 redirection이 아니라 `touch` + native `writefile` ASCII staging + `toybox uudecode -o` + `sha256sum` 방식으로 바뀌어야 한다
   - v319 계획서: `docs/plans/NATIVE_INIT_V319_SERIAL_TRANSFER_APPEND_PLAN_2026-05-19.md`
   - v319 보고서: `docs/reports/NATIVE_INIT_V319_SERIAL_TRANSFER_APPEND_2026-05-19.md`
   - v319 결과: `A90 Linux init 0.9.61 (v319)` 실기 플래시 PASS, scoped `appendfile` 추가, 4096-byte shell/cmdv1x buffer 적용, appendfile transfer smoke PASS
   - v319 해석: V317 runner는 이제 `appendfile` + `toybox uudecode -o` + `sha256sum` 방식으로 private workdir 전송을 수행할 준비가 됐다. live V317 proof는 여전히 exact approval phrase 없이는 실행되지 않는다
   - v320 계획서: `docs/plans/NATIVE_INIT_V320_PRIVATE_PROPERTY_LOOKUP_PROOF_PLAN_2026-05-19.md`
   - v320 보고서: `docs/reports/NATIVE_INIT_V320_PRIVATE_PROPERTY_LOOKUP_PROOF_2026-05-19.md`
   - v320 해석: V317 live PASS 후에만 진행하는 조건부 계획과 fail-closed host runner를 준비했다. 현재 runner는 V317 PASS evidence가 없으면 `private-property-lookup-blocked-v317-missing`으로 거부하며, 목표는 Android-linked read-only property reader를 private namespace 안에서 실행해 v317 private `/dev/__properties__` tree의 값을 읽을 수 있는지 확인하는 것이다. global property runtime, property service socket, daemon start, Wi-Fi bring-up은 계속 금지한다
   - v321 계획서: `docs/plans/NATIVE_INIT_V321_EXECNS_PROPERTY_LOOKUP_HELPER_PLAN_2026-05-19.md`
   - v321 보고서: `docs/reports/NATIVE_INIT_V321_EXECNS_PROPERTY_LOOKUP_HELPER_2026-05-19.md`
   - v321 해석: `a90_android_execns_probe v11`에 `property-lookup`/`system-getprop` helper support를 추가했다. 정적 ARM64 빌드와 marker 검증은 PASS했지만, live 실행은 아직 V317 PASS와 V320 approval gate 전까지 금지다
   - v322 계획서: `docs/plans/NATIVE_INIT_V322_PRIVATE_PROPERTY_LOOKUP_RUNNER_PLAN_2026-05-19.md`
   - v322 보고서: `docs/reports/NATIVE_INIT_V322_PRIVATE_PROPERTY_LOOKUP_RUNNER_2026-05-19.md`
   - v322 해석: V320 runner가 v321 helper command를 생성하고 future live run path를 갖도록 통합됐다. 현재 `plan`/approval-flagged `run` 모두 V317 PASS missing으로 차단되며 device command/mutation은 0이다
   - v323 계획서: `docs/plans/NATIVE_INIT_V323_PRIVATE_PROPERTY_CHAIN_AUDIT_PLAN_2026-05-19.md`
   - v323 보고서: `docs/reports/NATIVE_INIT_V323_PRIVATE_PROPERTY_CHAIN_AUDIT_2026-05-19.md`
   - v323 해석: host-only gate audit 결과 `private-property-chain-blocked-v317-missing`, audit PASS, chain_ready=false다. v312/v315/v316/v317-plan/v317-audit/v319/v321/v322는 PASS이고 남은 live blocker는 v317 PASS evidence뿐이다
   - v324 계획서: `docs/plans/NATIVE_INIT_V324_PRIVATE_PROPERTY_APPROVAL_REFRESH_PLAN_2026-05-19.md`
   - v324 보고서: `docs/reports/NATIVE_INIT_V324_PRIVATE_PROPERTY_APPROVAL_REFRESH_2026-05-19.md`
   - v324 해석: 최신 approval packet을 재생성했다. live_execution_approved=false, transfer estimate는 files 5 / bytes 524988 / chunks 471 / estimated commands 505이며 exact v317 phrase 없이는 실행하지 않는다
   - v325 계획서: `docs/plans/NATIVE_INIT_V325_EXECNS_HELPER_DEPLOY_PREFLIGHT_PLAN_2026-05-19.md`
   - v325 보고서: `docs/reports/NATIVE_INIT_V325_EXECNS_HELPER_DEPLOY_PREFLIGHT_2026-05-19.md`
   - v325 해석: `a90_android_execns_probe v11` fresh artifact를 private evidence에 빌드했고 deploy preflight PASS다. ignored default local helper는 아직 `v10` stale이므로, live deploy 시 v325 evidence artifact 또는 재빌드 산출물을 사용해야 한다
   - v326 계획서: `docs/plans/NATIVE_INIT_V326_PRIVATE_PROPERTY_CHAIN_V325_GATE_PLAN_2026-05-19.md`
   - v326 보고서: `docs/reports/NATIVE_INIT_V326_PRIVATE_PROPERTY_CHAIN_V325_GATE_2026-05-19.md`
   - v326 해석: chain audit에 `v325-fresh-helper-preflight` required gate를 추가했다. 현재 v312/v315/v316/v317-plan/v317-audit/v319/v321/v322/v325는 PASS이고, live blocker는 여전히 v317 PASS evidence missing이다
   - v327 계획서: `docs/plans/NATIVE_INIT_V327_PRIVATE_PROPERTY_APPROVAL_REFRESH_PLAN_2026-05-19.md`
   - v327 보고서: `docs/reports/NATIVE_INIT_V327_PRIVATE_PROPERTY_APPROVAL_REFRESH_2026-05-19.md`
   - v327 해석: approval refresh 기본 chain audit을 v326으로 올렸다. 최신 approval packet도 live_execution_approved=false이며 exact v317 phrase 없이는 실행하지 않는다
   - v328 계획서: `docs/plans/NATIVE_INIT_V328_V317_RUNNER_APPROVAL_REFRESH_GATE_PLAN_2026-05-19.md`
   - v328 보고서: `docs/reports/NATIVE_INIT_V328_V317_RUNNER_APPROVAL_REFRESH_GATE_2026-05-19.md`
   - v328 해석: V317 runner가 v327 approval refresh manifest를 blocker로 요구하도록 조정했다. plan은 PASS, run-without-approval은 approval-required로 fail-closed이며 device command/mutation은 없다
   - v329 계획서: `docs/plans/NATIVE_INIT_V329_WIFI_READINESS_DASHBOARD_PLAN_2026-05-19.md`
   - v329 보고서: `docs/reports/NATIVE_INIT_V329_WIFI_READINESS_DASHBOARD_2026-05-19.md`
   - v329 해석: Wi-Fi readiness dashboard를 host-only로 생성했다. 현재 decision은 `wifi-readiness-dashboard-ready-blocked-by-v317`이며, vendor assets/property layout은 준비됐지만 CNSS start-only 반복은 유효하지 않고 service-manager는 property runtime/process prerequisites로 막혀 있다
   - v330 계획서: `docs/plans/NATIVE_INIT_V330_WIFI_EVIDENCE_FRESHNESS_PLAN_2026-05-19.md`
   - v330 보고서: `docs/reports/NATIVE_INIT_V330_WIFI_EVIDENCE_FRESHNESS_2026-05-19.md`
   - v330 해석: V325-V329 evidence를 current clean git head에서 재생성했는지 audit했다. decision은 `wifi-evidence-freshness-clean`이며 device command/mutation은 없다
   - v331 계획서: `docs/plans/NATIVE_INIT_V331_V317_LIVE_READINESS_PACKET_PLAN_2026-05-19.md`
   - v331 보고서: `docs/reports/NATIVE_INIT_V331_V317_LIVE_READINESS_PACKET_2026-05-19.md`
   - v331 해석: V317 live proof용 operator handoff packet을 host-only로 만들었다. exact approval phrase가 제공되기 전까지 live_execution_approved=false이며 device command/mutation은 없다
   - v332 계획서: `docs/plans/NATIVE_INIT_V332_CURRENT_READONLY_LIVE_PREFLIGHT_PLAN_2026-05-19.md`
   - v332 보고서: `docs/reports/NATIVE_INIT_V332_CURRENT_READONLY_LIVE_PREFLIGHT_2026-05-19.md`
   - v332 해석: 현재 연결된 native device에서 read-only V317 preflight가 PASS했다. native version `A90 Linux init 0.9.61 (v319)`, SD writable, selftest fail=0, netservice disabled, logpath on SD 확인. device mutation은 없다
   - v333 계획서: `docs/plans/NATIVE_INIT_V333_POST_V317_ROUTER_PLAN_2026-05-19.md`
   - v333 보고서: `docs/reports/NATIVE_INIT_V333_POST_V317_ROUTER_2026-05-19.md`
   - v333 해석: V317 결과 라우터를 host-only로 추가했다. 현재 decision은 `post-v317-router-awaiting-v317`이며, V317 PASS 전에는 V320 property lookup을 실행하지 않는다
   - v334 계획서: `docs/plans/NATIVE_INIT_V334_WIFI_EVIDENCE_FRESHNESS_EXPANSION_PLAN_2026-05-19.md`
   - v334 보고서: `docs/reports/NATIVE_INIT_V334_WIFI_EVIDENCE_FRESHNESS_EXPANSION_2026-05-19.md`
   - v334 해석: freshness audit 범위를 V325-V333으로 확장했다. current clean head에서 전체 approval 직전 evidence가 fresh인지 확인한다
   - v335 계획서: `docs/plans/NATIVE_INIT_V335_WIFI_APPROVAL_GATE_REGRESSION_PLAN_2026-05-19.md`
   - v335 보고서: `docs/reports/NATIVE_INIT_V335_WIFI_APPROVAL_GATE_REGRESSION_2026-05-19.md`
   - v335 해석: V317/V320 approval gate regression을 host-only로 추가했다. partial approval과 V320-before-V317은 device command/mutation 없이 거부된다
   - v336 계획서: `docs/plans/NATIVE_INIT_V336_V317_PRELIVE_GATE_AUDIT_PLAN_2026-05-19.md`
   - v336 보고서: `docs/reports/NATIVE_INIT_V336_V317_PRELIVE_GATE_AUDIT_2026-05-19.md`
   - v336 해석: V325-V335 gate evidence를 통합 감사했다. 현재 remaining blocker는 `exact-v317-approval-phrase` 하나이며, V317 live proof 자체는 아직 실행하지 않았다
   - v337 계획서: `docs/plans/NATIVE_INIT_V337_V317_RUNNER_PRELIVE_GATE_PLAN_2026-05-19.md`
   - v337 보고서: `docs/reports/NATIVE_INIT_V337_V317_RUNNER_PRELIVE_GATE_2026-05-19.md`
   - v337 해석: V317 runner가 exact approval만으로 실행되지 않도록 V336 pre-live gate와 clean current HEAD를 추가로 요구하게 했다. dirty-tree exact approval은 device command 없이 blocked 처리된다
   - v338 계획서: `docs/plans/NATIVE_INIT_V338_V317_READINESS_PACKET_V336_AWARE_PLAN_2026-05-19.md`
   - v338 보고서: `docs/reports/NATIVE_INIT_V338_V317_READINESS_PACKET_V336_AWARE_2026-05-19.md`
   - v338 해석: V317 readiness packet이 V336 pre-live gate를 명시적으로 확인하고 generated live command에 `--prelive-gate-manifest`를 포함하도록 갱신했다
   - v339 계획서: `docs/plans/NATIVE_INIT_V339_V317_LIVE_SURFACE_LINTER_PLAN_2026-05-19.md`
   - v339 보고서: `docs/reports/NATIVE_INIT_V339_V317_LIVE_SURFACE_LINTER_2026-05-19.md`
   - v339 해석: V317 runner의 `device_cmd()` 호출 표면을 AST로 검사해 허용된 private-workdir 파일 작업만 남아 있음을 확인했다
   - v340 계획서: `docs/plans/NATIVE_INIT_V340_V317_FINAL_HANDOFF_PACKET_PLAN_2026-05-19.md`
   - v340 보고서: `docs/reports/NATIVE_INIT_V340_V317_FINAL_HANDOFF_PACKET_2026-05-19.md`
   - v340 해석: V331/V336/V339를 단일 operator handoff packet으로 묶었다. 남은 blocker는 `exact-v317-approval-phrase` 하나다
   - v341 계획서: `docs/plans/NATIVE_INIT_V341_HANDOFF_REQUIRES_CURRENT_PRELIVE_PLAN_2026-05-19.md`
   - v341 보고서: `docs/reports/NATIVE_INIT_V341_HANDOFF_REQUIRES_CURRENT_PRELIVE_2026-05-19.md`
   - v341 해석: V340 handoff가 runner와 동일하게 V336 pre-live gate를 current clean HEAD로 요구하도록 수정했다. stale V336은 handoff 단계에서 blocked 된다
   - v342 계획서: `docs/plans/NATIVE_INIT_V342_V317_APPROVED_PREFLIGHT_PLAN_2026-05-19.md`
   - v342 보고서: `docs/reports/NATIVE_INIT_V342_V317_APPROVED_PREFLIGHT_2026-05-19.md`
   - v342 해석: V317 runner에 no-device-command `preflight` 모드를 추가하고 handoff packet에 preflight command와 current-tree-clean check를 추가했다
   - v343 계획서: `docs/plans/NATIVE_INIT_V343_BREAK_V331_V336_CYCLE_PLAN_2026-05-19.md`
   - v343 보고서: `docs/reports/NATIVE_INIT_V343_BREAK_V331_V336_CYCLE_2026-05-19.md`
   - v343 해석: V342 후 발견된 V331/V336/V333 순환 의존성을 끊었다. clean HEAD `da70622`에서 V336/V331/V339/V340과 approved preflight가 PASS했고 남은 blocker는 exact V317 approval phrase 하나다
   - v344 계획서: `docs/plans/NATIVE_INIT_V344_V317_GATE_REFRESH_PLAN_2026-05-19.md`
   - v344 보고서: `docs/reports/NATIVE_INIT_V344_V317_GATE_REFRESH_2026-05-19.md`
   - v344 해석: V317 approval 직전 evidence refresh 순서를 `wifi_v317_gate_refresh.py`로 자동화했다. clean current HEAD에서 optional approved preflight 포함 PASS했고, live proof는 여전히 exact approval phrase 없이는 실행하지 않는다
   - v345 계획서: `docs/plans/NATIVE_INIT_V345_POST_V317_ROUTER_REGRESSION_PLAN_2026-05-19.md`
   - v345 보고서: `docs/reports/NATIVE_INIT_V345_POST_V317_ROUTER_REGRESSION_2026-05-19.md`
   - v345 해석: V317 live proof 이후 V333 router가 PASS/cleanup/failure/manual-review/prereq-blocked 결과를 안전하게 분기하는지 host-only synthetic regression으로 검증했다
   - v346 계획서: `docs/plans/NATIVE_INIT_V346_HANDOFF_PREFLIGHT_OUTDIR_PLAN_2026-05-19.md`
   - v346 보고서: `docs/reports/NATIVE_INIT_V346_HANDOFF_PREFLIGHT_OUTDIR_2026-05-19.md`
   - v346 해석: V340 generated preflight command가 live V317 result path를 오염시키지 않도록 별도 preflight out-dir을 쓰게 수정했고, generated preflight command 자체가 no-device PASS임을 확인했다
   - v347 계획서: `docs/plans/NATIVE_INIT_V347_GATE_REFRESH_GENERATED_PREFLIGHT_PLAN_2026-05-19.md`
   - v347 보고서: `docs/reports/NATIVE_INIT_V347_GATE_REFRESH_GENERATED_PREFLIGHT_2026-05-19.md`
   - v347 해석: `wifi_v317_gate_refresh.py --run-approved-preflight`가 V340 manifest의 generated preflight command까지 직접 실행해 검증하도록 확장했고, clean HEAD에서 direct/generated preflight 모두 PASS했다
   - v348 계획서: `docs/plans/NATIVE_INIT_V348_HANDOFF_COMMAND_CONTRACT_PLAN_2026-05-19.md`
   - v348 보고서: `docs/reports/NATIVE_INIT_V348_HANDOFF_COMMAND_CONTRACT_2026-05-19.md`
   - v348 해석: V340 generated preflight/live/cleanup command의 script/subcommand/out-dir/approval/gate contract를 host-only linter로 검증했다
   - v349 계획서: `docs/plans/NATIVE_INIT_V349_FINAL_READINESS_AGGREGATOR_PLAN_2026-05-19.md`
   - v349 보고서: `docs/reports/NATIVE_INIT_V349_FINAL_READINESS_AGGREGATOR_2026-05-19.md`
   - v349 해석: V344 refresh, V345 router regression, V348 command contract를 하나로 묶는 final readiness aggregator를 추가했고 clean HEAD에서 PASS했다
   - v350 계획서: `docs/plans/NATIVE_INIT_V350_V317_OPERATOR_CHECKLIST_PLAN_2026-05-19.md`
   - v350 보고서: `docs/reports/NATIVE_INIT_V350_V317_OPERATOR_CHECKLIST_2026-05-19.md`
   - v350 해석: V340 live/cleanup command와 V349 final readiness를 사람이 실행하기 쉬운 operator checklist로 결합했고 clean HEAD에서 PASS했다
   - v351 계획서: `docs/plans/NATIVE_INIT_V351_V317_LIVE_EXECUTOR_PLAN_2026-05-19.md`
   - v351 보고서: `docs/reports/NATIVE_INIT_V351_V317_LIVE_EXECUTOR_2026-05-19.md`
   - v351 해석: V350 checklist를 직접 실행하는 fail-closed executor guard를 추가했고 clean HEAD `plan`이 PASS했다. 승인 없는 `run`은 즉시 거부된다
   - v352 계획서: `docs/plans/NATIVE_INIT_V352_V317_LIVE_EXECUTOR_REGRESSION_PLAN_2026-05-19.md`
   - v352 보고서: `docs/reports/NATIVE_INIT_V352_V317_LIVE_EXECUTOR_REGRESSION_2026-05-19.md`
   - v352 해석: V351 executor의 no-approval/partial-approval/plan 경로를 host-only regression으로 고정했고 clean HEAD에서 PASS했다
   - v353 계획서: `docs/plans/NATIVE_INIT_V353_OPERATOR_EXECUTOR_PREFERENCE_PLAN_2026-05-19.md`
   - v353 보고서: `docs/reports/NATIVE_INIT_V353_OPERATOR_EXECUTOR_PREFERENCE_2026-05-19.md`
   - v353 해석: V350 operator checklist의 기본 실행 경로를 raw V340 command가 아니라 V351 executor로 전환했고 clean HEAD에서 V350/V351/V352 PASS했다
   - v354 계획서: `docs/plans/NATIVE_INIT_V354_CLEANUP_APPROVAL_REGRESSION_PLAN_2026-05-19.md`
   - v354 보고서: `docs/reports/NATIVE_INIT_V354_CLEANUP_APPROVAL_REGRESSION_2026-05-19.md`
   - v354 해석: V351 cleanup 경로의 phrase-only/flags-only partial approval 회귀를 추가했고 clean HEAD에서 PASS했다
   - v355 계획서: `docs/plans/NATIVE_INIT_V355_APPROVAL_MATRIX_REGRESSION_PLAN_2026-05-19.md`
   - v355 보고서: `docs/reports/NATIVE_INIT_V355_APPROVAL_MATRIX_REGRESSION_2026-05-19.md`
   - v355 해석: V351 run/cleanup 경로에서 exact phrase가 있어도 mutation 확인 플래그 하나가 빠진 조합을 거부하는 회귀를 추가했고 clean HEAD에서 PASS했다
   - v356 계획서: `docs/plans/NATIVE_INIT_V356_WRONG_PHRASE_REGRESSION_PLAN_2026-05-19.md`
   - v356 보고서: `docs/reports/NATIVE_INIT_V356_WRONG_PHRASE_REGRESSION_2026-05-19.md`
   - v356 해석: mutation flags가 모두 있어도 exact phrase가 아니면 거부하는 회귀를 추가했고 clean HEAD에서 PASS했다
   - v357 계획서: `docs/plans/NATIVE_INIT_V357_PREAPPROVAL_AUDIT_PLAN_2026-05-19.md`
   - v357 보고서: `docs/reports/NATIVE_INIT_V357_PREAPPROVAL_AUDIT_2026-05-19.md`
   - v357 해석: V349/V350/V351-plan/V352-regression을 한 번 더 묶어 clean HEAD/current evidence/no-device-action/exact-approval-only 상태인지 확인하는 host-only pre-approval audit를 추가했고 clean HEAD에서 PASS했다
   - v358 계획서: `docs/plans/NATIVE_INIT_V358_APPROVAL_SUDO_BOUNDARY_PLAN_2026-05-19.md`
   - v358 보고서: `docs/reports/NATIVE_INIT_V358_APPROVAL_SUDO_BOUNDARY_2026-05-19.md`
   - v358 해석: V317 live 전 host-only/no-sudo, host-sudo, exact approval required, separate approval required 명령군을 운영 문서로 고정했고 clean HEAD V357 audit도 계속 PASS했다
   - v359 계획서: `docs/plans/NATIVE_INIT_V359_LIVE_BLOCKER_SNAPSHOT_PLAN_2026-05-19.md`
   - v359 보고서: `docs/reports/NATIVE_INIT_V359_LIVE_BLOCKER_SNAPSHOT_2026-05-19.md`
   - v359 해석: V357/V350을 기반으로 live blocker 상태를 manifest로 남겨 exact approval phrase만 남았는지 재확인했고 clean HEAD에서 PASS했다
   - v317 live 해석: exact approval phrase 수신 후 V351 executor `run --timeout 900`으로 minimal private property namespace proof를 실행했고 `private-property-namespace-proof-pass` / `post-v317-router-v320-ready`를 확인했다
   - v320/v323 해석: V317 PASS 이후 V320 plan은 `private-property-lookup-plan-ready`, V323 chain audit는 `private-property-chain-ready-for-v320-approval`로 전환됐다. 이후 exact V320 approval phrase로 live lookup을 실행했고, stale v10 helper와 unmounted `/mnt/system` 실패를 거쳐 v11 helper serial deploy + `mountsystem ro` 조건에서 `private-property-lookup-getprop-pass`를 확인했다
   - v320 결과: private property namespace 안에서 `/system/bin/getprop`가 allowlisted 4개 property를 v312 expected value와 동일하게 읽었다. 이는 property lookup 조건이 충족됐다는 뜻이며, daemon start/Wi-Fi bring-up 승인은 아직 아니다
   - v360 계획서: `docs/plans/NATIVE_INIT_V360_CNSS_PRESTART_RUNNER_REFRESH_PLAN_2026-05-19.md`
   - v360 보고서: `docs/reports/NATIVE_INIT_V360_CNSS_PRESTART_RUNNER_REFRESH_2026-05-19.md`
   - v360 해석: V320에서 배포된 v11 helper SHA를 CNSS start-only runner 기본값으로 반영했다. no-start `plan`/`preflight`/`dry-run`은 모두 PASS했고 `daemon_start_executed=false`를 유지했다
   - v361 계획서: `docs/plans/NATIVE_INIT_V361_CNSS_START_ONLY_APPROVAL_PACKET_PLAN_2026-05-19.md`
   - v361 보고서: `docs/reports/NATIVE_INIT_V361_CNSS_START_ONLY_APPROVAL_PACKET_2026-05-19.md`
   - v361 해석: v11 helper 기준 approval packet을 재생성했고 `live-approval-packet-ready` PASS, helper no-allow fail-closed PASS, `daemon_start_executed=false`를 확인했다. 생성된 future command는 별도 bounded start-only 승인 전까지 실행하지 않는다
   - v362 계획서: `docs/plans/NATIVE_INIT_V362_CNSS_START_ONLY_LIVE_PLAN_2026-05-20.md`
   - v362 보고서: `docs/reports/NATIVE_INIT_V362_CNSS_START_ONLY_LIVE_2026-05-20.md`
   - v362 해석: 별도 daemon start 요청 후 bounded `cnss-daemon -n -l` start-only live run을 1회 실행했고 `start-only-pass` / `cnss-start-only-evidence-classified` / `cnss-warning-disposition-ready`를 확인했다
   - v362 결과: child observable, timeout 후 SIGTERM/SIGKILL/reap, `postflight_safe=1`, postflight process count/running/zombie `0`, `/proc/net/dev`와 `wifiinv full`에서 `wlan*`/wlan-like interface 없음, `scan_connect_linkup=0`
   - v362 경계: 이 결과는 CNSS daemon start-only 가능성만 의미한다. Wi-Fi scan/connect/link-up/credential/DHCP/routing/supplicant/wificond/hostapd/Wi-Fi HAL은 별도 계획과 승인 전까지 계속 blocked
   - v363 계획서: `docs/plans/NATIVE_INIT_V363_WIFI_BRINGUP_PHASE0_PLAN_2026-05-20.md`
   - v363 보고서: `docs/reports/NATIVE_INIT_V363_WIFI_BRINGUP_PHASE0_2026-05-20.md`
   - v363 해석: Wi-Fi bring-up 방향은 수락됐지만 첫 단계는 no-scan/no-connect baseline gate로 제한했다. live baseline은 `wifi-bringup-phase0-live-baseline-ready` PASS
   - v363 결과: `wlan` module present, ICNSS core bound, QCA6390 node present but driver link absent, no `wlan*`, no Wi-Fi rfkill, no CNSS process leak
   - v363 다음: V364 no-scan/no-connect HAL/service-manager readiness gate. CNSS 단독 반복보다 Android Wi-Fi HAL/service-manager/property/Binder chain을 좁히는 것이 다음 병목이다
   - v364 계획서: `docs/plans/NATIVE_INIT_V364_HAL_SERVICE_READINESS_GATE_PLAN_2026-05-20.md`
   - v364 보고서: `docs/reports/NATIVE_INIT_V364_HAL_SERVICE_READINESS_GATE_2026-05-20.md`
   - v364 해석: V292/V320/V362/V363 선행 증거는 PASS지만 live gate는 `hal-service-readiness-blocked`로 판정됐다. 현재 Binder devnodes, service-manager process, mutable property runtime, linkerconfig visibility가 없다
   - v364 결과: no `wlan*`, no Wi-Fi rfkill, no CNSS process leak은 유지됐다. service binary visibility는 partial이고 Wi-Fi VINTF metadata는 present다
   - v364 다음: V365 bounded Binder/property/linker namespace readiness repair or approval packet. Wi-Fi HAL/service-manager start-only도 아직 별도 계획 전까지 blocked
   - v365 계획서: `docs/plans/NATIVE_INIT_V365_SERVICE_RUNTIME_REPAIR_PACKET_PLAN_2026-05-20.md`
   - v365 보고서: `docs/reports/NATIVE_INIT_V365_SERVICE_RUNTIME_REPAIR_PACKET_2026-05-20.md`
   - v365 해석: V364 blocker를 V366 no-daemon repair smoke packet으로 전환했다. helper, real linkerconfig, private property root, system root, service-manager binaries는 준비됐고 `/dev/block/sda29`는 `/proc/partitions` `259:13` 기반 temporary `mknodb` 후보로 정리됐다
   - v365 결과: `service-runtime-repair-packet-ready`, next approval phrase `approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up`
   - v365 다음: V366 bounded temporary device-node + private property/linker repair smoke. 아직 service-manager/HAL/scan/connect는 blocked
   - v366 계획서: `docs/plans/NATIVE_INIT_V366_RUNTIME_REPAIR_SMOKE_PLAN_2026-05-20.md`
   - v366 보고서: `docs/reports/NATIVE_INIT_V366_RUNTIME_REPAIR_SMOKE_2026-05-20.md`
   - v366 해석: guarded runtime repair smoke runner를 추가했고 plan/preflight/no-approval refusal 경로를 검증했다. no-approval run은 `runtime-repair-smoke-approval-required`로 PASS했고 mutation step은 실행하지 않았다. 이후 `preexisting-temp-nodes` blocker를 추가해 기존 `/dev` 노드가 있으면 승인 실행도 막도록 보강했다
   - v366 다음: exact phrase `approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up`가 들어오기 전까지 temporary `/dev` node 생성/property lookup smoke도 보류한다
   - v367 계획서: `docs/plans/NATIVE_INIT_V367_RUNTIME_REPAIR_SMOKE_REGRESSION_PLAN_2026-05-20.md`
   - v367 보고서: `docs/reports/NATIVE_INIT_V367_RUNTIME_REPAIR_SMOKE_REGRESSION_2026-05-20.md`
   - v367 해석: V366 승인 경로에서 preexisting-node blocker가 mutation 전에 평가되도록 순서를 수정했고, host-only synthetic regression으로 no-approval/wrong-phrase/clean-approved/preexisting-approved 케이스를 검증했다
   - v368 계획서: `docs/plans/NATIVE_INIT_V368_RUNTIME_REPAIR_CLEANUP_GATE_PLAN_2026-05-20.md`
   - v368 보고서: `docs/reports/NATIVE_INIT_V368_RUNTIME_REPAIR_CLEANUP_GATE_2026-05-20.md`
   - v368 해석: cleanup도 device mutation이므로 exact phrase + `--apply --assume-yes` 없이는 실행하지 않게 막았다. live cleanup refusal은 `steps=[]`로 PASS했다
   - v369 계획서: `docs/plans/NATIVE_INIT_V369_RUNTIME_REPAIR_APPROVAL_PACKET_PLAN_2026-05-20.md`
   - v369 보고서: `docs/reports/NATIVE_INIT_V369_RUNTIME_REPAIR_APPROVAL_PACKET_2026-05-20.md`
   - v369 해석: V366 live smoke approval packet을 생성했고, preflight/run-refusal/cleanup-refusal/regression과 run/cleanup command contract가 PASS했다. packet 자체는 `live_execution_approved=false`이며 실제 smoke는 아직 실행하지 않았다
   - v370 계획서: `docs/plans/NATIVE_INIT_V370_RUNTIME_REPAIR_RESULT_ROUTER_PLAN_2026-05-20.md`
   - v370 보고서: `docs/reports/NATIVE_INIT_V370_RUNTIME_REPAIR_RESULT_ROUTER_2026-05-20.md`
   - v370 해석: V366 live smoke 결과 router를 추가했고 현재 상태는 `runtime-repair-smoke-router-awaiting-approval`이다. live smoke가 PASS하면 다음은 service-manager start-only approval packet이고, HAL/scan/connect는 여전히 별도 승인 전까지 금지다
   - v371 계획서: `docs/plans/NATIVE_INIT_V371_RUNTIME_REPAIR_SMOKE_LIVE_EXECUTOR_PLAN_2026-05-20.md`
   - v371 보고서: `docs/reports/NATIVE_INIT_V371_RUNTIME_REPAIR_SMOKE_LIVE_EXECUTOR_2026-05-20.md`
   - v371 해석: exact V366 approval phrase 이후 V371 executor로 bounded runtime repair smoke를 실행했고 `runtime-repair-smoke-live-executor-run-pass` / `runtime-repair-smoke-router-service-runtime-next-ready`를 확인했다. temporary `/dev/block/sda29`/binder node 생성, private property lookup, cleanup, postflight cleanliness까지만 수행했고 service-manager/HAL/scan/connect는 실행하지 않았다
   - v371 다음: separate service-manager start-only approval packet 작성. 이 단계도 Wi-Fi HAL start, scan/connect/link-up/credential/DHCP/routing은 제외해야 한다
   - v372 계획서: `docs/plans/NATIVE_INIT_V372_SERVICE_MANAGER_START_ONLY_APPROVAL_PACKET_PLAN_2026-05-20.md`
   - v372 보고서: `docs/reports/NATIVE_INIT_V372_SERVICE_MANAGER_START_ONLY_APPROVAL_PACKET_2026-05-20.md`
   - v372 해석: V371/V366 PASS와 현재 read-only native state를 묶어 `service-manager-start-only-approval-packet-ready`를 확인했다. `servicemanager`/`hwservicemanager` binary visible, service-manager process clean, Wi-Fi link clean, temporary Binder nodes cleaned 상태다
   - v372 다음: V373 fail-closed service-manager start-only smoke runner 구현. required phrase는 `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up`
   - v373 계획서: `docs/plans/NATIVE_INIT_V373_SERVICE_MANAGER_START_ONLY_SMOKE_PLAN_2026-05-20.md`
   - v373 보고서: `docs/reports/NATIVE_INIT_V373_SERVICE_MANAGER_START_ONLY_SMOKE_2026-05-20.md`
   - v373 해석: service-manager start-only runner scaffold를 추가했고 no-approval run은 `service-manager-start-only-smoke-approval-required` / `steps=0`으로 막혔다. preflight는 read-only로 PASS 조건을 확인했지만 `helper-service-manager-mode` 부재로 mutation 전 blocked 됐다
   - v373 다음: V374에서 `a90_android_execns_probe`에 bounded service-manager start-only mode를 추가하거나 동등한 fail-closed primitive를 설계한다
   - v374 계획서: `docs/plans/NATIVE_INIT_V374_EXECNS_SERVICE_MANAGER_MODE_PLAN_2026-05-20.md`
   - v374 보고서: `docs/reports/NATIVE_INIT_V374_EXECNS_SERVICE_MANAGER_MODE_2026-05-20.md`
   - v374 해석: `a90_android_execns_probe v12` source와 로컬 static ARM64 artifact를 만들었고 `service-manager-start-only`, `--allow-service-manager-start-only`, `system-servicemanager`, `system-hwservicemanager` 문자열을 확인했다. 아직 `/cache/bin` 배포나 daemon start는 하지 않았다
   - v374 다음: V375 helper deploy/preflight packet. v12를 `/cache/bin/a90_android_execns_probe`에 설치/검증하고 V373 preflight를 재실행하되 service-manager live start는 여전히 별도 exact approval 전까지 blocked
   - v375 계획서: `docs/plans/NATIVE_INIT_V375_EXECNS_HELPER_V12_DEPLOY_PREFLIGHT_PLAN_2026-05-20.md`
   - v375 보고서: `docs/reports/NATIVE_INIT_V375_EXECNS_HELPER_V12_DEPLOY_PREFLIGHT_2026-05-20.md`
   - v375 해석: fail-closed helper deploy/preflight runner를 추가했고, NCM host IP 불안정 상황을 serial `appendfile` + `toybox uudecode -o` fallback으로 보강했다. exact phrase 이후 `/cache/bin/a90_android_execns_probe`를 v12로 설치했고 remote SHA/marker/service-manager mode를 확인했다
   - v375 결과: `execns-helper-v12-deploy-pass`, remote SHA `fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918`, V373 post-deploy preflight `service-manager-start-only-smoke-approval-required`, `helper-service-manager-mode` PASS, daemon start/Wi-Fi bring-up 없음
   - v375 다음: 별도 exact phrase `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up`가 있을 때만 V373 service-manager start-only smoke를 실행한다. Wi-Fi HAL/scan/connect/link-up/credential/DHCP/routing은 계속 blocked

   - v376 계획서: `docs/plans/NATIVE_INIT_V376_SERVICE_MANAGER_START_ONLY_LIVE_RUNNER_PLAN_2026-05-20.md`
   - v376 보고서: `docs/reports/NATIVE_INIT_V376_SERVICE_MANAGER_START_ONLY_LIVE_RUNNER_2026-05-20.md`
   - v376 해석: V375 helper v12 배포 이후 service-manager start-only live runner 실행 본문을 추가했다. plan/preflight/no-approval refusal은 PASS했고, generic approval은 거부된다. live start는 exact phrase `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up` + `--apply --assume-yes` 없이는 실행하지 않는다
   - v376 결과: exact phrase 이후 approved live run을 실행했고 `service-manager-start-only-live-runtime-gap`이 나왔다. 두 target 모두 `SIGABRT`로 종료했으며 첫 hard blocker는 helper namespace 안의 `/dev/binder` 부재다. postflight는 clean이고 Wi-Fi bring-up은 없음
   - v376 다음: runtime-gap을 분류/수정하기 전 HAL start-only approval packet은 금지한다. Wi-Fi HAL/scan/connect/link-up/credential/DHCP/routing은 계속 blocked

   - v377 계획서: `docs/plans/NATIVE_INIT_V377_SERVICE_MANAGER_RESULT_ROUTER_PLAN_2026-05-20.md`
   - v377 보고서: `docs/reports/NATIVE_INIT_V377_SERVICE_MANAGER_RESULT_ROUTER_2026-05-20.md`
   - v377 해석: V376 result router를 host-only로 추가했다. synthetic regression은 PASS했고 approved V376 evidence route는 `service-manager-start-only-router-runtime-gap`이다. device command/mutation 없이 runtime-gap classification 필요성을 명확히 분류한다
   - v377 다음: V378 runtime-gap classifier/repair planning. 현재 직접 원인은 Binder driver `/dev/binder` open 실패이며, helper private namespace에서 Binder devnode를 안전하게 provisioning하는 방향이 우선이다

   - v378 계획서: `docs/plans/NATIVE_INIT_V378_SERVICE_MANAGER_RUNTIME_GAP_CLASSIFIER_PLAN_2026-05-20.md`
   - v378 보고서: `docs/reports/NATIVE_INIT_V378_SERVICE_MANAGER_RUNTIME_GAP_CLASSIFIER_2026-05-20.md`
   - v378 해석: V376 runtime-gap을 host-only로 분류했고 decision은 `service-manager-runtime-gap-binder-devnode-required`다. current Binder metadata refresh도 `binder-devnode-plan-ready`로, `/dev/binder c 10 81`, `/dev/hwbinder c 10 80`, `/dev/vndbinder c 10 79` 후보가 유지된다
   - v378 다음: V379에서 service-manager start-only helper namespace 안에 private Binder devnode provisioning을 추가한다. binderfs는 별도 mount/ioctl 정책이 필요하므로 우선 static misc devnode 방식이 더 작다
   - live daemon start 범위를 벗어나는 Wi-Fi scan/connect/link-up/credential/DHCP/routing은 별도 계획과 승인 전까지 blocked

   - v379 계획서: `docs/plans/NATIVE_INIT_V379_EXECNS_PRIVATE_BINDER_DEVNODES_PLAN_2026-05-20.md`
   - v379 보고서: `docs/reports/NATIVE_INIT_V379_EXECNS_PRIVATE_BINDER_DEVNODES_2026-05-20.md`
   - v379 해석: `a90_android_execns_probe v13` 로컬 static helper에 service-manager start-only 전용 private `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` provisioning을 추가했다. helper child는 Android `system` uid로 drop되므로 private Binder nodes는 `0666`으로 만든다. 아직 `/cache/bin` 배포나 daemon start는 하지 않았다
   - v379 다음: V380에서 v13 helper를 배포/검증하고, 별도 live 승인 범위에서 bounded service-manager start-only를 재실행한다

   - v380 계획서: `docs/plans/NATIVE_INIT_V380_EXECNS_HELPER_V13_DEPLOY_LIVE_PLAN_2026-05-20.md`
   - v380 보고서: `docs/reports/NATIVE_INIT_V380_EXECNS_HELPER_V13_DEPLOY_LIVE_2026-05-20.md`
   - v380 해석: v13 helper를 `/cache/bin/a90_android_execns_probe`에 serial fallback으로 배포했고 remote SHA를 확인했다. 승인된 bounded service-manager start-only에서 `hwservicemanager`는 timeout까지 관찰 후 clean stop 됐고, `servicemanager`는 SIGABRT로 runtime-gap이다. private Binder nodes는 helper namespace 안에 정상 생성됐으므로 Binder blocker는 해소됐다
   - v380 다음: classifier decision은 `service-manager-runtime-gap-property-runtime-required`다. V381에서 private `/dev/__properties__`와 최소 `/data` runtime materialization을 설계한다. Wi-Fi HAL/start/bring-up은 계속 blocked

   - v381 계획서: `docs/plans/NATIVE_INIT_V381_EXECNS_SERVICE_PROPERTY_RUNTIME_PLAN_2026-05-20.md`
   - v381 보고서: `docs/reports/NATIVE_INIT_V381_EXECNS_SERVICE_PROPERTY_RUNTIME_2026-05-20.md`
   - v381 해석: `a90_android_execns_probe v14` 로컬 static helper에서 service-manager start-only mode가 `--property-root`를 받을 수 있게 했다. 기존 V317 private `/dev/__properties__`를 helper temp-root에 read-only bind하고, 다음 live smoke에서 `--data-wifi-mode private-empty`로 최소 `/data` tree를 제공할 수 있다. 아직 `/cache/bin` 배포나 daemon start는 하지 않았다
   - v381 다음: V382에서 v14 helper를 배포하고 private property root + private-empty data mode로 bounded service-manager start-only를 재실행한다

   - v382 계획서: `docs/plans/NATIVE_INIT_V382_EXECNS_HELPER_V14_DEPLOY_LIVE_PLAN_2026-05-20.md`
   - v382 준비 보고서: `docs/reports/NATIVE_INIT_V382_RUNTIME_PROFILE_WRAPPER_2026-05-20.md`
   - v382 라우터 보고서: `docs/reports/NATIVE_INIT_V382_RESULT_ROUTER_2026-05-20.md`
   - v382 final readiness 보고서: `docs/reports/NATIVE_INIT_V382_FINAL_READINESS_2026-05-20.md`
   - v382 deploy/live executor 보고서: `docs/reports/NATIVE_INIT_V382_DEPLOY_LIVE_EXECUTOR_2026-05-20.md`
   - v382 준비: `scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py`가 V375 deploy mechanics를 재사용하되 helper marker `a90_android_execns_probe v14`, artifact `tmp/wifi/v381-a90_android_execns_probe-v14/a90_android_execns_probe`, sha256 `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7`, approval phrase `approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up`로 고정한다
   - v382 live wrapper: `scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py`가 기존 V376 runner를 재사용하되 helper sha256 v14, `--property-root /mnt/sdext/a90/private-property-v317/dev/__properties__`, `--data-wifi-mode private-empty`를 기본 profile로 고정한다
   - v382 result router: `scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py`가 V377 router를 재사용하되 권장 live command를 V382 wrapper로 고정한다. no-approval route는 `service-manager-start-only-router-awaiting-approval`로 PASS했고 device command/mutation은 없음
   - v382 final readiness: `scripts/revalidation/wifi_v382_final_readiness.py`가 deploy plan/preflight, live plan/no-approval, router regression/no-approval route를 한 번에 검증한다. clean HEAD run은 `v382-final-readiness-awaiting-deploy-approval` PASS이며, 남은 blocker는 exact deploy/live approval phrases뿐이다
   - v382 로컬 검증: live wrapper plan은 PASS했고, read-only preflight는 property root visible/data profile PASS 후 remote helper가 아직 v13이어서 `helper-v14` blocker로 멈춘다. daemon start와 Wi-Fi bring-up은 없음
   - v382 executor: `scripts/revalidation/wifi_v382_deploy_live_executor.py`가 final readiness → v14 deploy → live preflight → bounded service-manager start-only → result router/classifier 순서를 fail-closed로 묶는다. no-approval deploy/live/full은 모두 `approval-required` PASS, device command/mutation/daemon/Wi-Fi 없음
   - v382 approved 결과 보고서: `docs/reports/NATIVE_INIT_V382_APPROVED_DEPLOY_LIVE_RESULT_2026-05-20.md`
   - v382 결과: exact approval 후 executor `full` PASS. `/cache/bin/a90_android_execns_probe`는 v14 SHA `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7`로 교체됐고, live는 `service-manager-start-only-live-runtime-gap` / router `service-manager-start-only-router-runtime-gap`이다. `hwservicemanager`는 bounded pass, `servicemanager`는 SIGABRT manual-review. Wi-Fi HAL/scan/connect/link-up/credential/DHCP/routing은 실행 안 됨
   - v383 classifier 보고서: `docs/reports/NATIVE_INIT_V383_SERVICEMANAGER_SIGABRT_CLASSIFIER_2026-05-20.md`
   - v383 결과: `scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py`가 V382 live evidence를 `service-manager-runtime-gap-servicemanager-sigabrt-capture-required`로 분류한다. device command/mutation 없이 regression PASS
   - v384 계획서: `docs/plans/NATIVE_INIT_V384_SERVICEMANAGER_CRASH_CAPTURE_PLAN_2026-05-20.md`
   - v384 구현 보고서: `docs/reports/NATIVE_INIT_V384_SERVICEMANAGER_CRASH_CAPTURE_2026-05-20.md`
   - v384 결과: 로컬 `a90_android_execns_probe v15`가 `service-manager-start-only --capture-mode ptrace-lite`를 지원한다. deploy/live wrapper는 fail-closed이며, v382/v373 승인 문구로는 v384 live/deploy가 실행되지 않는다. 아직 v15 배포와 live crash capture는 미실행
   - v384 executor 보고서: `docs/reports/NATIVE_INIT_V384_DEPLOY_LIVE_EXECUTOR_2026-05-20.md`
   - v384 handoff: `docs/operations/WIFI_V384_PTRACE_LIVE_HANDOFF.md`
   - v384 preflight ready report: `docs/reports/NATIVE_INIT_V384_PREFLIGHT_READY_2026-05-20.md`
   - v384 preapproval audit: `scripts/revalidation/wifi_v384_preapproval_audit.py`, report `docs/reports/NATIVE_INIT_V384_PREAPPROVAL_AUDIT_2026-05-20.md`, clean HEAD decision `v384-preapproval-audit-pass`
   - v384 executor 결과: `scripts/revalidation/wifi_v384_deploy_live_executor.py`가 helper v15 deploy → ptrace-lite live capture → classifier를 fail-closed로 순서화한다. `plan`/no-approval `full` 회귀에서 device command/mutation/daemon/Wi-Fi 모두 false
   - v384 실행 조건: deploy는 exact `approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요
   - v384 다음: exact v384 deploy 승인으로 v15를 `/cache/bin`에 배포한 뒤, exact v384 ptrace-lite 승인으로 bounded service-manager crash capture를 실행한다. Wi-Fi HAL/start/scan/connect는 계속 blocked

---

## 당장 하지 않을 것

- Android framework 전체 복구
- SELinux/property service 전체 재구현
- 커널 교체
- EFS/modem/keymaster/RPMB 영역 쓰기
- full POSIX shell 구현
- package manager 만들기
- ADB를 최우선 과제로 되돌리기

---

## 완료 기준

단기 완료 기준:

- serial shell이 실패/성공을 신뢰할 수 있게 보고한다.
- 부팅 로그가 `/cache` 또는 `/tmp`에 남는다.
- 화면 HUD가 진행 상태와 에러를 표시한다.
- 버튼만으로 최소 메뉴를 조작할 수 있다.

중기 완료 기준:

- native init 환경이 “부팅되는 실험”이 아니라 “반복 운용 가능한 최소 Linux 콘솔”이 된다.
- 디스플레이, 입력, 센서, 저장소, USB의 안전 사용 범위가 문서화된다.
- 추가 userland 도구나 네트워크를 올릴 기반이 생긴다.

## V109-V116 다음 사이클

- roadmap: `docs/plans/NATIVE_INIT_V109_V116_ROADMAP_2026-05-04.md`
- starting point: `A90 Linux init 0.9.9 (v109)`
- first item: v109 post-v108 structure audit — DONE
- next item: v117 planning
- cycle goal: structure cleanup, extended soak, USB/service/runtime hardening, diagnostics bundle improvement

## V117-V122 다음 사이클

- roadmap: `docs/plans/NATIVE_INIT_V117_V122_ROADMAP_2026-05-05.md`
- starting point: `A90 Linux init 0.9.16 (v116)`
- status: completed through `docs/reports/NATIVE_INIT_V117_V122_COMPLETION_AUDIT_2026-05-05.md`
- current item: post-v122 planning
- planned sequence: v117 roadmap baseline, v118 shell metadata cleanup, v119 menu routing cleanup, v120 command group split, v121 PID1 guard, v122 Wi-Fi inventory refresh
- cycle goal: reduce PID 1 control debt before deciding whether Wi-Fi can move beyond read-only inventory
- guardrails: no risky Wi-Fi bring-up, no partition writes, USB ACM serial remains rescue channel

   - v384 approved live result: `docs/reports/NATIVE_INIT_V384_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v384 approved deploy/live evidence:
     - initial full executor: `tmp/wifi/v384-approved-full-20260520-042720/`
     - compact live rerun: `tmp/wifi/v384-approved-live-compact-20260520-044147/`
   - v384 해석: v15 deploy는 PASS했고 ptrace-lite live는 실제 daemon start-only까지 진입했다. `servicemanager`는 SIGABRT crash context를 확보했고, `hwservicemanager`는 timeout까지 observable 상태였으나 helper 내부 process-group postflight proof가 실패해 `start-only-reboot-required`로 분류됐다. host postflight/selftest는 clean, Wi-Fi bring-up은 없음
   - v384 도구 수정: native shell 30-arg 한계 때문에 service-manager live command에서 `--data-wifi-mode private-empty`만 compact path에서 생략한다. shell wrapper는 `/cache/bin/toybox`에 `sh` applet이 없어 사용하지 않는다
   - v385 다음: `a90_android_execns_probe v16`에서 direct child reap 이후 남은 process group을 final SIGKILL로 정리하고, 잔존 process-group evidence를 캡처한다. Wi-Fi HAL/start/scan/connect는 계속 blocked

   - v385 plan: `docs/plans/NATIVE_INIT_V385_RESIDUAL_PGID_CLEANUP_PLAN_2026-05-20.md`
   - v385 readiness report: `docs/reports/NATIVE_INIT_V385_RESIDUAL_PGID_CLEANUP_2026-05-20.md`
   - v385 구현 상태: `a90_android_execns_probe v16`은 residual process-group scan/final SIGKILL/recheck evidence를 추가한다. 로컬 SHA256은 `4478c73518e950b425af0cf7db28e9570c983f428fbb0d4b5d2ee45573d37cd8`이다
   - v385 검증 상태: static build/py_compile/diff check PASS. no-approval executor는 device mutation/daemon/Wi-Fi 없이 막혔고, preflight는 remote helper가 아직 v15이므로 v16 deploy 필요로 막힌다
   - v385 실행 조건: deploy는 exact `approve v385 deploy execns helper v16 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v385 service-manager residual pgid cleanup only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v385 approved result report: `docs/reports/NATIVE_INIT_V385_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v385 approved deploy: serial transfer installed helper v16 SHA `4478c73518e950b425af0cf7db28e9570c983f428fbb0d4b5d2ee45573d37cd8`; daemon start/Wi-Fi bring-up 없음
   - v385 approved live: `servicemanager` cleanup proof PASS but runtime gap remains. `hwservicemanager` produced large ptrace exec snapshot and host capture missed `A90P1 END`; bridge capture shows eventual 85s completion, but `service_manager_start.*` summary fields were not captured. Postflight device state is clean
   - v386 다음: compact ptrace capture mode. service-manager live proof must reduce serial output and preserve machine-readable residual cleanup summary before any Wi-Fi HAL/start/scan/connect step

   - v386 plan: `docs/plans/NATIVE_INIT_V386_COMPACT_PTRACE_CAPTURE_PLAN_2026-05-20.md`
   - v386 readiness report: `docs/reports/NATIVE_INIT_V386_COMPACT_PTRACE_CAPTURE_2026-05-20.md`
   - v386 구현 상태: `a90_android_execns_probe v17`은 service-manager `ptrace-lite`에서 raw maps/mountinfo/register dump를 serial stdout으로 뿌리지 않고 compact summary만 보낸다. 로컬 SHA256은 `45c27e28c90a86c75a291edaf16d8233da51358647c1e6d1700f0e4f9cf437c5`이다
   - v386 검증 상태: static build/py_compile/diff check/no-approval executor gate PASS. device deploy/live는 아직 실행하지 않았다
   - v386 실행 조건: deploy는 exact `approve v386 deploy execns helper v17 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v386 service-manager compact ptrace capture only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v386 approved result report: `docs/reports/NATIVE_INIT_V386_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v386 approved deploy: serial transfer installed helper v17 SHA `45c27e28c90a86c75a291edaf16d8233da51358647c1e6d1700f0e4f9cf437c5`; daemon start/Wi-Fi bring-up 없음
   - v386 approved live: compact ptrace capture fixed the v385 serial output blocker. Both service-manager targets returned `A90P1 END` and machine-readable `service_manager_start.*` fields. `servicemanager` remains `start-only-runtime-gap` with cleanup PASS. `hwservicemanager` is still `start-only-reboot-required` because timeout cleanup treats a ptrace stop as reaped and leaves a temporary zombie until PID1 reaps it
   - v387 다음: ptrace timeout cleanup fix. WIFSTOPPED must not be counted as reaped; cleanup must continue the tracee with termination signal and wait for real WIFEXITED/WIFSIGNALED before claiming postflight safe

   - v387 plan: `docs/plans/NATIVE_INIT_V387_PTRACE_TIMEOUT_CLEANUP_PLAN_2026-05-20.md`
   - v387 readiness report: `docs/reports/NATIVE_INIT_V387_PTRACE_TIMEOUT_CLEANUP_2026-05-20.md`
   - v387 구현 상태: `a90_android_execns_probe v18`은 service-manager `ptrace-lite` timeout cleanup에서 `WIFSTOPPED`를 reap으로 계산하지 않고, TERM/KILL cleanup phase에서 `PTRACE_CONT`로 종료 시그널을 주입한다. 로컬 SHA256은 `1131f0e3dd61bafc5023c25d7fb019303902cdf6cea76dd2e09b44b13a42378e`이다
   - v387 검증 상태: static build/required strings/py_compile/plan-only gates/no-approval executor PASS. read-only device preflight는 remote helper가 아직 v17이므로 expected `helper-v18` blocker로 막혔고 daemon start/Wi-Fi bring-up은 없음
   - v387 실행 조건: deploy는 exact `approve v387 deploy execns helper v18 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v387 service-manager ptrace timeout cleanup only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v387 approved result report: `docs/reports/NATIVE_INIT_V387_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v387 approved deploy: serial transfer installed helper v18 SHA `1131f0e3dd61bafc5023c25d7fb019303902cdf6cea76dd2e09b44b13a42378e`; daemon start/Wi-Fi bring-up 없음
   - v387 approved live: `hwservicemanager` cleanup blocker is fixed. It now reports `start-only-pass`, `cleanup_stop_continued=1`, `reaped=1`, `residual_cleared=1`, `postflight_safe=1`. `servicemanager` still exits with SIGABRT but crash evidence is captured and cleanup is safe
   - v388 다음: `servicemanager` SIGABRT evidence triage and targeted runtime repair planning. Wi-Fi HAL/start/scan/connect remains blocked until this runtime gap is understood

   - v388 plan: `docs/plans/NATIVE_INIT_V388_SERVICEMANAGER_SIGABRT_TRIAGE_PLAN_2026-05-20.md`
   - v388 report: `docs/reports/NATIVE_INIT_V388_SERVICEMANAGER_SIGABRT_TRIAGE_2026-05-20.md`
   - v388 결과: host-only triage가 V387 `servicemanager` SIGABRT를 분석했고 `servicemanager-sigabrt-triage-needs-enhanced-crash-capture` PASS로 분류했다. `/dev/binder`, property root, SELinux null node는 materialized지만 abort message, register values, stack/abort-message memory가 없어 AOSP fatal site는 아직 미확정이다
   - v389 다음: bounded enhanced crash capture. `NT_PRSTATUS` selected register values, stack/ASCII summary, abort-message memory/string scan을 compact하게 추가한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v389 plan: `docs/plans/NATIVE_INIT_V389_ENHANCED_CRASH_CAPTURE_PLAN_2026-05-20.md`
   - v389 readiness report: `docs/reports/NATIVE_INIT_V389_ENHANCED_CRASH_CAPTURE_2026-05-20.md`
   - v389 구현 상태: `a90_android_execns_probe v19`은 service-manager crash snapshot에서 selected `NT_PRSTATUS` register values(x0-x8/lr/sp/pc/pstate)와 bounded stack/register-pointer ASCII scan을 추가한다. 로컬 SHA256은 `e3da79dec1c7ca58d3208fb0d9a55ce1411fff7159ab613ff9daf6d6befd3e6d`이다
   - v389 검증 상태: static build/required strings/py_compile/plan-only gates/no-approval executor PASS. read-only device preflight는 remote helper가 아직 v18이므로 expected `helper-v19` blocker로 막혔고 daemon start/Wi-Fi bring-up은 없음
   - v389 실행 조건: deploy는 exact `approve v389 deploy execns helper v19 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v389 service-manager enhanced crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v389 approved live result: `docs/reports/NATIVE_INIT_V389_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v389 approved deploy: serial transfer installed helper v19 SHA `e3da79dec1c7ca58d3208fb0d9a55ce1411fff7159ab613ff9daf6d6befd3e6d`; daemon start/Wi-Fi bring-up 없음
   - v389 approved live: `hwservicemanager` remains `start-only-pass`; `servicemanager` remains `start-only-runtime-gap` with SIGABRT, but selected register values, stack scan, register-pointer scans, and compact maps metadata are now captured
   - v389 해석: `x8=0xf0`은 AArch64 `rt_tgsigqueueinfo` syscall path로 보이며 PC/LR은 abort delivery 경로에 멈춘 상태다. 현재 capture는 map row/library offset을 보존하지 않아 fatal site symbolization이 아직 불가하다
   - v390 다음: crash map-row/symbolization capture. `pc`/`lr`가 속한 `/proc/<pid>/maps` row와 library-relative offsets를 bounded output으로 추가한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v390 plan: `docs/plans/NATIVE_INIT_V390_CRASH_MAP_CAPTURE_PLAN_2026-05-20.md`
   - v390 readiness report: `docs/reports/NATIVE_INIT_V390_CRASH_MAP_CAPTURE_2026-05-20.md`
   - v390 구현 상태: `a90_android_execns_probe v20`은 crash snapshot에서 PC/LR map row, mapping permissions, file offset, relative offset, path, escaped maps line을 추가한다. 로컬 SHA256은 `44efea328220d37f09d91e4906b7490903d789ef509f0ae2ba74a64049a47171`이다
   - v390 host tool: `scripts/revalidation/wifi_service_manager_crash_symbolize.py`가 V390 live log의 map-row evidence를 파싱하고 matching ELF root가 있을 때 `addr2line` symbolization을 시도한다
   - v390 검증 상태: static build/required strings/py_compile/plan-only gates/no-approval executor PASS. read-only device preflight는 remote helper가 아직 v19이므로 expected `helper-v20` blocker로 막혔고 daemon start/Wi-Fi bring-up은 없음
   - v390 실행 조건: deploy는 exact `approve v390 deploy execns helper v20 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v390 service-manager crash map capture only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v390 approved live result: `docs/reports/NATIVE_INIT_V390_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v390 approved deploy: serial transfer installed helper v20 SHA `44efea328220d37f09d91e4906b7490903d789ef509f0ae2ba74a64049a47171`; daemon start/Wi-Fi bring-up 없음
   - v390 approved live: `hwservicemanager` remains `start-only-pass`; `servicemanager` remains `start-only-runtime-gap` with SIGABRT, but PC/LR map rows are captured and both point into bionic `libc.so`
   - v390 해석: PC=`libc.so+0x8bebc`, LR=`libc.so+0x8be90`, `x8=0xf0` still indicates abort delivery via `rt_tgsigqueueinfo`. host symbolizer is `maprow-ready` but blocked by missing host-side Android ELF
   - v391 다음: read-only Android `libc.so` ELF pull/mirror and symbolization/disassembly around offsets `0x8be90`/`0x8bebc`. Wi-Fi HAL/start/scan/connect remains blocked

   - v391 plan: `docs/plans/NATIVE_INIT_V391_LIBC_SYMBOLIZATION_PLAN_2026-05-20.md`
   - v391 result: `docs/reports/NATIVE_INIT_V391_LIBC_SYMBOLIZATION_2026-05-20.md`
   - v391 evidence: `tmp/wifi/v391-libc-symbolize-20260520-065233/`
   - v391 결과: read-only `libc.so` pull PASS, ELF SHA `05b46edc9bf95e52c7eaf73ee340d78c52971ca2482cafa3c4d0c510691ba204`, PC/LR both resolve to bionic `abort`
   - v391 해석: captured PC/LR are abort delivery, not original fatal caller. `x8=0xf0`/`svc #0` confirms SIGABRT send path
   - v392 다음: service-manager crash caller-context/backchain capture. x29/frame pointer, stack words, candidate return-address map rows, bounded backchain reconstruction을 추가한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v392 plan: `docs/plans/NATIVE_INIT_V392_BACKCHAIN_CAPTURE_PLAN_2026-05-20.md`
   - v392 readiness report: `docs/reports/NATIVE_INIT_V392_BACKCHAIN_CAPTURE_2026-05-20.md`
   - v392 handoff/analyzer report: `docs/reports/NATIVE_INIT_V392_HANDOFF_AND_FRAMECHAIN_ANALYZER_2026-05-20.md`
   - v392 executor integration report: `docs/reports/NATIVE_INIT_V392_EXECUTOR_FRAMECHAIN_INTEGRATION_2026-05-20.md`
   - v392 live handoff: `docs/operations/WIFI_V392_BACKCHAIN_LIVE_HANDOFF.md`
   - v392 구현 상태: `a90_android_execns_probe v21`은 crash snapshot에서 `x29`/frame pointer와 up to 8 frame-chain 후보를 캡처하고, 각 return address를 `frameN_ra` map row로 기록한다. 로컬 SHA256은 `c6216cc3b579f78bfd668148a24e1948e9e08621ea7d4e21c8b280475cc09ab8`이다
   - v392 분석 도구: `scripts/revalidation/wifi_service_manager_framechain_analyze.py`는 V392 live log의 frame-chain evidence와 `frameN_ra` map rows를 host-only로 파싱하고, matching ELF root가 있을 때 return-address symbolization을 시도한다. `scripts/revalidation/wifi_v392_deploy_live_executor.py`는 approved runtime-gap live 후 이 분석기를 자동 실행한다
   - v392 검증 상태: static build/required strings/py_compile/plan-only gates/no-approval executor PASS. read-only device preflight는 remote helper가 아직 v20이므로 expected `helper-v21` blocker로 막혔고 daemon start/Wi-Fi bring-up은 없음. framechain analyzer negative check는 V390 log에서 expected `service-manager-framechain-needs-v392-live` PASS. executor framechain integration smoke도 V390 runtime-gap evidence 기준 PASS
   - v392 실행 조건: deploy는 exact `approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v393 plan: `docs/plans/NATIVE_INIT_V393_FRAMECHAIN_AUTO_ELF_RESOLVER_PLAN_2026-05-20.md`
   - v393 report: `docs/reports/NATIVE_INIT_V393_FRAMECHAIN_AUTO_ELF_RESOLVER_2026-05-20.md`
   - v393 결과: framechain analyzer가 V391 read-only `libc.so` pull과 V221/V227/V222 host-side ELF roots를 자동 재사용한다. synthetic framechain log에서 `/tmp/.../root/apex/com.android.runtime/lib64/bionic/libc.so + 0x8be90`을 `abort`로 symbolization PASS했고 V390 negative regression은 expected `service-manager-framechain-needs-v392-live` PASS
   - v393 해석: 다음 approved V392 live에서 frame return-address가 cached Android ELF에 매핑되면 수동 `--elf-root` 없이 top-level executor route가 symbolized caller inspection으로 이어질 수 있다. Wi-Fi HAL/start/scan/connect remains blocked until V392 exact approval

   - v394 plan: `docs/plans/NATIVE_INIT_V394_POST_V392_ROUTER_PLAN_2026-05-20.md`
   - v394 report: `docs/reports/NATIVE_INIT_V394_POST_V392_ROUTER_2026-05-20.md`
   - v394 결과: `scripts/revalidation/wifi_v392_post_live_router.py`가 V392 executor/framechain manifest를 host-only로 라우팅한다. synthetic regression PASS, current no-approval route는 expected `v392-post-live-router-awaiting-approval` PASS
   - v394 해석: approved V392 live 후 framechain 결과가 symbolized caller, abort-only, missing ELF, missing maprow, clean service-manager 중 어디에 해당하는지 자동 분기한다. Wi-Fi HAL/start/scan/connect remains blocked until V392 evidence says service-manager path is clean enough for a separate HAL start-only approval packet

   - v395 plan: `docs/plans/NATIVE_INIT_V395_CURRENT_READINESS_PACKET_PLAN_2026-05-20.md`
   - v395 report: `docs/reports/NATIVE_INIT_V395_CURRENT_READINESS_PACKET_2026-05-20.md`
   - v395 결과: `scripts/revalidation/wifi_v392_current_readiness_packet.py`가 최신 safe preflight/no-approval/router/read-only health evidence를 묶어 `v392-current-readiness-ready-for-approval` PASS로 판정했다. 디바이스 명령 실행/뮤테이션/daemon/Wi-Fi bring-up은 없음
   - v395 해석: V392 approved executor를 실행할 준비는 됐지만 exact approval phrase 두 개가 없으면 계속 fail-closed 상태다

   - v392 approved backchain result: `docs/reports/NATIVE_INIT_V392_APPROVED_BACKCHAIN_CAPTURE_RESULT_2026-05-20.md`
   - v392 approved 결과: helper v21 deploy PASS, service-manager backchain capture PASS, `hwservicemanager`은 `start-only-pass`, `servicemanager`은 SIGABRT `start-only-runtime-gap`이나 cleanup/postflight safe. framechain은 7 frames를 캡처했고 libc frame `__libc_init`만 symbolization PASS, `servicemanager`/`libbase`/`liblog` frames는 matching ELF artifact가 없어 미해석
   - v396 다음: read-only frame ELF pull/symbolization. `/mnt/system/system/bin/servicemanager`, `/mnt/system/system/lib64/libbase.so`, `/mnt/system/system/lib64/liblog.so`를 host에 안전하게 mirror한 뒤 V392 framechain analyzer를 재실행한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v396 plan: `docs/plans/NATIVE_INIT_V396_FRAME_ELF_SYMBOLIZATION_PLAN_2026-05-20.md`
   - v396 report: `docs/reports/NATIVE_INIT_V396_FRAME_ELF_SYMBOLIZATION_2026-05-20.md`
   - v396 evidence: `tmp/wifi/v396-frame-elf-pull-20260520-073940/`
   - v396 결과: read-only `servicemanager`/`libbase.so`/`liblog.so` pull PASS, framechain rerun `service-manager-framechain-symbolization-pass`, `device_mutations=False`, `daemon_start_executed=False`, `wifi_bringup_executed=False`
   - v396 해석: missing-ELF blocker는 제거됐다. frame0/1은 fatal-log abort path이고 frame2 `servicemanager+0x8294`는 `frameworks/native/cmds/servicemanager/Access.cpp` fatal-log site 근방이다. 주변 문자열상 `selinux_status_open(true)`, `gSehandle`, `getcon` 관련 SELinux runtime/status surface가 가장 강한 후보지만 아직 확정은 아니다
   - v397 다음: private Android namespace에서 `/sys/fs/selinux`, SELinux status/context/service-context 입력, binder devnode와 service-manager fatal 조건을 read-only로 증명한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v397 plan: `docs/plans/NATIVE_INIT_V397_SELINUX_SURFACE_PROOF_PLAN_2026-05-20.md`
   - v397 report: `docs/reports/NATIVE_INIT_V397_SELINUX_SURFACE_PROOF_2026-05-20.md`
   - v397 evidence: `tmp/wifi/v397-selinux-surface-final-20260520-075153/`
   - v397 결과: `service-manager-selinux-status-native-missing` PASS as blocker classification. `/proc/filesystems`에는 `selinuxfs`가 있으나 `/proc/mounts`에는 `/sys/fs/selinux` selinuxfs mount가 없고 `/sys/fs/selinux/status`, `/sys/fs/selinux/enforce`가 absent
   - v397 해석: `servicemanager` crash는 Wi-Fi 자체보다 Android `servicemanager`가 요구하는 SELinux runtime surface 부재 쪽으로 좁혀졌다. mounted Android service context input은 일부 보이지만 native/private runtime status page가 없다
   - v398 다음: minimal SELinux runtime surface plan. 우선 helper v22 private context proof 또는 native selinuxfs mount/bind 설계를 안전하게 분리하고, service-manager clean-start 전까지 Wi-Fi HAL/start/scan/connect remains blocked

   - v398 plan: `docs/plans/NATIVE_INIT_V398_SELINUXFS_MOUNT_APPROVAL_PACKET_PLAN_2026-05-20.md`
   - v398 report: `docs/reports/NATIVE_INIT_V398_SELINUXFS_MOUNT_APPROVAL_PACKET_2026-05-20.md`
   - v398 evidence: `tmp/wifi/v398-selinuxfs-mount-approval-packet-final-20260520-080150/`
   - v398 결과: `selinuxfs-mount-approval-packet-ready` PASS. V399 executor는 exact approval phrase 없이는 run/cleanup 모두 device command 전에 refuse한다. packet은 fresh V397 read-only proof를 포함했고 device mutation/daemon/Wi-Fi bring-up은 없음
   - v398 해석: 다음 live mutation은 명확히 `mount selinuxfs /sys/fs/selinux selinuxfs` 하나로 제한된다. cleanup은 `umount /sys/fs/selinux`로 분리되어 있으며 service-manager와 Wi-Fi는 여전히 범위 밖이다
   - v399 다음: exact-approved SELinuxfs mount smoke. `/sys/fs/selinux/status` 가시성을 증명한 뒤 별도 cycle에서 service-manager start-only packet으로 넘어간다. Wi-Fi HAL/start/scan/connect remains blocked

   - v399 report: `docs/reports/NATIVE_INIT_V399_SELINUXFS_MOUNT_SMOKE_2026-05-20.md`
   - v399 evidence: `tmp/wifi/v399-selinuxfs-mount-live-20260520-080657/`
   - v399 post-proof: `tmp/wifi/v399-post-smoke-proof-20260520-080750/`
   - v399 결과: `selinuxfs-mount-live-executor-run-review`. 승인된 mutation path까지 갔지만 `cmdv1 mount`가 `unknown command: mount`로 거부되어 실제 selinuxfs mount/status page는 생성되지 않았다. post-smoke proof는 여전히 `service-manager-selinux-status-native-missing`
   - v399 해석: 커널 SELinuxfs mount 불가가 아니라 executor command surface 오류다. `cmdv1 run /cache/bin/toybox mount` read-only inventory는 동작하므로 V400은 toybox-backed mount/umount executor로 좁힌다
   - v400 다음: toybox-backed SELinuxfs mount approval packet. Wi-Fi HAL/start/scan/connect remains blocked

   - v400 plan: `docs/plans/NATIVE_INIT_V400_TOYBOX_SELINUXFS_MOUNT_APPROVAL_PACKET_PLAN_2026-05-20.md`
   - v400 report: `docs/reports/NATIVE_INIT_V400_TOYBOX_SELINUXFS_MOUNT_APPROVAL_PACKET_2026-05-20.md`
   - v400 evidence: `tmp/wifi/v400-toybox-selinuxfs-mount-approval-packet-final-20260520-081415/`
   - v401 preapproval syntax evidence: `tmp/wifi/v401-preapproval-toybox-syntax-20260520-082122/`
   - v400 결과: `toybox-selinuxfs-mount-approval-packet-ready` PASS. V401 executor는 exact approval phrase 없이는 run/cleanup 모두 device command 전에 refuse한다. packet은 fresh SELinux proof, read-only toybox mount inventory, executor plan/refusal checks를 포함했고 device mutation/daemon/Wi-Fi bring-up은 없음
   - v401 preapproval syntax 결과: direct `toybox mount --help` and `toybox umount --help` PASS. `toybox --list`는 unsupported지만 V401 command contract에는 필요 없다
   - v400 해석: V399 tooling gap의 수정 경로가 준비됐다. 다음 live mutation은 `run /cache/bin/toybox mount -t selinuxfs selinuxfs /sys/fs/selinux` 하나로 제한된다. cleanup은 `run /cache/bin/toybox umount /sys/fs/selinux`로 분리한다
   - v401 다음: exact-approved toybox-backed SELinuxfs mount smoke. `/sys/fs/selinux/status` 가시성을 증명한 뒤 별도 cycle에서 service-manager start-only packet으로 넘어간다. Wi-Fi HAL/start/scan/connect remains blocked

   - v401 report: `docs/reports/NATIVE_INIT_V401_TOYBOX_SELINUXFS_MOUNT_SMOKE_2026-05-20.md`
   - v401 evidence: `tmp/wifi/v401-toybox-selinuxfs-mount-live-20260520-082325/`
   - v401 post-proof: `tmp/wifi/v401-post-mount-selinux-proof-20260520-082352/`
   - v401 결과: `toybox-selinuxfs-mount-live-executor-run-pass`. `/sys/fs/selinux/status` visible, `/sys/fs/selinux/enforce=0`, `/proc/mounts` includes `selinuxfs /sys/fs/selinux selinuxfs rw,relatime 0 0`
   - v401 post-proof 결과: `service-manager-selinux-surface-native-ready-private-proof-needed`. native SELinux runtime/status surface는 준비됐지만 private service-manager execution namespace에서 status/context/binder/property visibility는 아직 미증명
   - v402 다음: private namespace SELinux surface proof. service-manager start-only는 V402 proof 이후 별도 승인으로 분리한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v402 plan: `docs/plans/NATIVE_INIT_V402_PRIVATE_SELINUX_SURFACE_PROOF_PLAN_2026-05-20.md`
   - v402 packet: `docs/reports/NATIVE_INIT_V402_PRIVATE_SELINUX_SURFACE_PROOF_PACKET_2026-05-20.md`
   - v402 helper artifact: `tmp/wifi/v402-a90_android_execns_probe-v22/a90_android_execns_probe`, SHA `55f83cfa43ebc69ab37b3181262fbdf0e3ed6b5b11f0e41e63d3b56e7ea080e6`
   - v402 결과: helper v22 `private-selinux-proof` mode와 fail-closed deploy/private-proof runners를 준비했다. no-approval run은 mutation/daemon/Wi-Fi 없이 거부되고, read-only private proof preflight는 remote helper가 아직 v22가 아니어서 expected `helper-v22` blocker로 멈춘다
   - v402 실행 조건: deploy는 exact `approve v402 deploy execns helper v22 only; no daemon start and no Wi-Fi bring-up`, private proof는 exact `approve v402 private selinux namespace proof only; no daemon start and no Wi-Fi bring-up` 필요
   - v402 다음: exact-approved helper v22 deploy 후 private SELinux namespace proof. service-manager start-only, Wi-Fi HAL/start/scan/connect는 계속 별도 승인 전까지 blocked

   - v402 live report: `docs/reports/NATIVE_INIT_V402_PRIVATE_SELINUX_SURFACE_PROOF_LIVE_2026-05-20.md`
   - v402 live evidence: deploy `tmp/wifi/v402-execns-helper-v22-deploy-live-20260520-084231/`, proof `tmp/wifi/v402-private-selinux-surface-live-20260520-084832/`, postflight `tmp/wifi/v402-private-proof-postflight-20260520-084853/`
   - v402 live 결과: `execns-helper-v22-deploy-pass` 후 `private-selinux-surface-proof-pass`. private namespace에서 SELinuxfs status/enforce/policy, Binder devnodes, V317 private property tree, service/hwservice context files가 함께 visible하다
   - v402 live 해석: V401 이후 남은 private namespace SELinux surface blocker는 제거됐다. 다음은 V403 bounded service-manager start-only retry approval packet이며, Wi-Fi HAL/start/scan/connect는 계속 blocked

   - v403 plan: `docs/plans/NATIVE_INIT_V403_SERVICE_MANAGER_START_ONLY_RETRY_PLAN_2026-05-20.md`
   - v403 packet: `docs/reports/NATIVE_INIT_V403_SERVICE_MANAGER_START_ONLY_RETRY_APPROVAL_PACKET_2026-05-20.md`
   - v403 evidence: `tmp/wifi/v403-service-manager-start-only-retry-approval-packet-20260520-085357/`
   - v403 결과: `scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py`와 approval packet을 준비했다. runner plan/preflight/no-approval refusal 모두 PASS했고 packet decision은 `v403-service-manager-start-only-retry-approval-packet-ready`
   - v403 실행 조건: exact `approve v403 service-manager start-only retry only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요
   - v403 다음: 승인 시 bounded service-manager/hwservicemanager start-only retry를 실행하고 결과를 라우팅한다. Wi-Fi HAL/start/scan/connect는 계속 blocked

   - v403 live report: `docs/reports/NATIVE_INIT_V403_SERVICE_MANAGER_START_ONLY_RETRY_LIVE_2026-05-20.md`
   - v403 live evidence: `tmp/wifi/v403-service-manager-start-only-retry-live-20260520-085702/`, postflight `tmp/wifi/v403-service-manager-start-only-postflight-20260520-085747/`
   - v403 live 결과: `service-manager-start-only-live-pass`. `servicemanager`와 `hwservicemanager` 모두 bounded observation window 동안 살아 있었고, timeout 후 terminate/reap/postflight clean을 증명했다. Wi-Fi bring-up은 없음
   - v403 supplemental HAL gate: old V364 gate refresh는 global/current runtime 기준이라 `current-binder-devnodes`, `current-service-manager-processes`, `current-property-runtime`, `linkerconfig-visibility` blocker로 남는다. 이는 V403 private helper-owned namespace PASS와 충돌하지 않는다
   - v403 다음: V404 private-composite Wi-Fi HAL readiness packet. V403-proven service-manager/hwservicemanager pair를 같은 bounded helper-owned runtime 안에서 유지하는 설계를 먼저 만든 뒤 HAL start-only를 별도 승인으로 분리한다. Wi-Fi scan/connect/link-up/credentials remain blocked

   - v404 plan: `docs/plans/NATIVE_INIT_V404_PRIVATE_COMPOSITE_HAL_READINESS_PLAN_2026-05-20.md`
   - v404 report: `docs/reports/NATIVE_INIT_V404_PRIVATE_COMPOSITE_HAL_READINESS_PACKET_2026-05-20.md`
   - v404 evidence: `tmp/wifi/v404-private-composite-hal-readiness-packet-fixed-20260520-090542/`
   - v404 결과: `v404-private-composite-hal-readiness-packet-ready` PASS. packet은 V402/V403/V210/V216/V287 입력과 현재 read-only native 상태를 묶어 blocker checks PASS로 판정했다. live execution approval, device mutation, daemon start, Wi-Fi bring-up은 모두 false
   - v404 HAL boundary: first candidate는 `vendor.wifi_hal_ext`, sibling fallback은 `vendor.wifi_hal_legacy`. vendor HAL binary/init rc/VINTF 가시성은 현재 global `/mnt/system/vendor` stat가 아니라 V210 vendor-root evidence를 기준으로 판단한다
   - v404 다음: V405 composite helper/runner approval packet. 현재 helper는 한 invocation에 한 target만 start하므로, HAL start-only 전에 `servicemanager` + `hwservicemanager` + 첫 HAL 후보를 같은 helper-owned private namespace에서 bounded supervision하는 실행기를 만들어야 한다. Wi-Fi scan/connect/link-up/credentials/DHCP/routing remain blocked

   - v405 plan: `docs/plans/NATIVE_INIT_V405_COMPOSITE_HAL_APPROVAL_PACKET_PLAN_2026-05-20.md`
   - v405 report: `docs/reports/NATIVE_INIT_V405_COMPOSITE_HAL_APPROVAL_PACKET_2026-05-20.md`
   - v405 evidence: `tmp/wifi/v405-composite-hal-approval-packet-final-20260520-092442/`
   - v405 결과: `v405-composite-hal-approval-packet-ready` PASS. helper v23 local artifact SHA는 `64c80e73d791b82e0b9f60b05db1df1781bf5033b1ffd76e323cf52ce3dbc520`이고, `wifi-hal-composite-start-only`, `vendor-wifi-hal-ext`, `vendor-wifi-hal-legacy`, `--allow-wifi-hal-start-only` guard strings가 확인됐다
   - v405 guard 결과: deploy preflight는 expected `execns-helper-v23-deploy-preflight-ready-needs-deploy`, deploy no-approval은 `execns-helper-v23-deploy-approval-required`, HAL runner no-approval은 `composite-hal-start-only-approval-required`로 모두 fail-closed. device mutation, daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v405 다음: exact-approved helper v23 deploy only. HAL start-only는 deploy 후 V405 runner preflight PASS를 본 뒤 별도 exact approval로만 진행한다. scan/connect/link-up/credentials/DHCP/routing remain blocked

   - v405 deploy report: `docs/reports/NATIVE_INIT_V405_HELPER_V23_DEPLOY_LIVE_2026-05-20.md`
   - v405 deploy evidence: `tmp/wifi/v405-execns-helper-v23-deploy-live-20260520-092918/`
   - v405 post-deploy checks: helper check `tmp/wifi/v405-execns-helper-v23-deploy-postcheck-20260520-093620/`, composite preflight `tmp/wifi/v405-composite-hal-preflight-post-deploy-20260520-093529/`
   - v405 deploy 결과: exact-approved helper v23 deploy PASS. serial fallback으로 783 chunks / 1,094,836 encoded bytes를 전송했고 remote helper SHA/mode가 v23으로 확인됐다. daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v405 post-deploy preflight 결과: `composite-hal-start-only-preflight-ready` PASS. 남은 gate는 exact approval phrase뿐이다
   - v405 다음: `approve v405 composite Wi-Fi HAL start-only smoke only; no scan/connect/link-up and no Wi-Fi bring-up` 승인 시 bounded composite HAL start-only smoke만 실행한다. Wi-Fi scan/connect/link-up/credentials/DHCP/routing remain blocked

   - v405 live report: `docs/reports/NATIVE_INIT_V405_COMPOSITE_HAL_START_ONLY_LIVE_2026-05-20.md`
   - v405 live evidence: `tmp/wifi/v405-composite-hal-start-only-live-20260520-094000/`
   - v405 library locate evidence: `tmp/wifi/v405-wifi-hal-lib-locate-20260520-094105/`
   - v405 live 결과: exact-approved composite start-only smoke는 승인 경계 안에서 실행됐고 safety PASS. `servicemanager`, `hwservicemanager`, `vendor.samsung.hardware.wifi@2.0-service`가 같은 helper-owned namespace에서 시작됐지만 Wi-Fi HAL이 `android.hardware.wifi@1.0.so` 미해결로 exit `1` 처리되어 `composite-hal-start-only-runtime-gap`로 분류됐다. scan/connect/link-up 및 Wi-Fi bring-up은 false
   - v405 해석: blocker는 service-manager runtime이 아니라 private APEX materialization이다. 필요한 Wi-Fi HIDL interface libs는 `/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/`에 있고, 현재 helper는 `/mnt/system/system/apex` 기반 private farm만 구성한다
   - v406 다음: private `/apex/com.android.vndk.v30`에 `system_ext/apex/com.android.vndk.v30`를 bind/materialize하는 helper/runner를 만들고 linker-list closure를 먼저 증명한다. HAL start-only retry, scan/connect/link-up, credentials, DHCP, routing은 별도 gate로 유지한다

   - v406 plan: `docs/plans/NATIVE_INIT_V406_SYSTEM_EXT_VNDK_APEX_PLAN_2026-05-20.md`
   - v406 report: `docs/reports/NATIVE_INIT_V406_SYSTEM_EXT_VNDK_APEX_PREP_2026-05-20.md`
   - v406 helper artifact: `tmp/wifi/v406-a90_android_execns_probe-v24/a90_android_execns_probe`
   - v406 결과: helper v24가 `v30-to-system-ext-v30` private APEX materialization mode를 추가했고 static ARM64 build PASS, SHA `7ec11d95085f1c3dc370884725b080b44150bf8b0a5f7d897df048188a815063`
   - v406 gate 결과: runner preflight는 `system-ext-vndk-linker-list-preflight-ready-needs-deploy`, deploy preflight는 `execns-helper-v24-deploy-preflight-ready-needs-deploy`, deploy no-approval은 `execns-helper-v24-deploy-approval-required`, runner no-approval은 `system-ext-vndk-linker-list-approval-required`. daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v406 다음: 먼저 `approve v406 deploy execns helper v24 only; no daemon start and no Wi-Fi bring-up` 승인으로 helper deploy만 진행한다. 그 다음 별도 `approve v406 system_ext VNDK APEX linker-list proof only; no daemon start and no Wi-Fi bring-up` 승인으로 linker-list proof만 진행한다

   - v406 deploy report: `docs/reports/NATIVE_INIT_V406_HELPER_V24_DEPLOY_LIVE_2026-05-20.md`
   - v406 deploy evidence: `tmp/wifi/v406-execns-helper-v24-deploy-live-20260520-095625/`
   - v406 post-deploy checks: helper check `tmp/wifi/v406-execns-helper-v24-deploy-postcheck-20260520-100244/`, runner preflight `tmp/wifi/v406-system-ext-vndk-runner-post-deploy-preflight-20260520-100252/`
   - v406 deploy 결과: exact-approved helper v24 deploy PASS. serial fallback으로 783 chunks / 1,094,836 encoded bytes를 전송했고 remote helper SHA/mode가 v24로 확인됐다. daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v406 post-deploy preflight 결과: `system-ext-vndk-linker-list-preflight-ready` PASS. 남은 gate는 exact approval phrase뿐이다
   - v406 다음: `approve v406 system_ext VNDK APEX linker-list proof only; no daemon start and no Wi-Fi bring-up` 승인 시 linker-list proof만 실행한다. HAL start-only retry, scan/connect/link-up, credentials, DHCP, routing은 별도 gate로 유지한다

   - v406 linker-list report: `docs/reports/NATIVE_INIT_V406_SYSTEM_EXT_VNDK_LINKER_LIST_LIVE_2026-05-20.md`
   - v406 linker-list evidence: `tmp/wifi/v406-system-ext-vndk-linker-list-live-20260520-100627/`
   - v406 linker-list 결과: exact-approved proof PASS. helper v24 `v30-to-system-ext-v30` mode에서 `/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service`가 linker-list child exit `0`, signal `0`, timed_out `0`, missing_libs `[]`로 완료됐다. device mutation, daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v406 해석: V405의 `android.hardware.wifi@1.0.so` missing blocker는 system_ext VNDK v30 APEX materialization으로 해소됐다
   - v407 다음: bounded composite Wi-Fi HAL start-only retry plan/approval packet을 작성한다. 같은 helper-owned namespace에서 `servicemanager`, `hwservicemanager`, `vendor.wifi_hal_ext`만 시작하고 scan/connect/link-up, credentials, DHCP, routing은 계속 별도 gate로 유지한다

   - v407 plan: `docs/plans/NATIVE_INIT_V407_COMPOSITE_HAL_RETRY_PLAN_2026-05-20.md`
   - v407 report: `docs/reports/NATIVE_INIT_V407_COMPOSITE_HAL_RETRY_APPROVAL_PACKET_2026-05-20.md`
   - v407 runner: `scripts/revalidation/wifi_composite_hal_start_only_v407_runner.py`
   - v407 결과: approval packet PASS. plan은 `v407-composite-hal-start-only-retry-plan-ready`, no-approval은 `v407-composite-hal-start-only-retry-approval-required`, read-only preflight는 `v407-composite-hal-start-only-retry-preflight-ready`
   - v407 guard 결과: V406 linker-list input, helper v24 SHA/mode, system_ext VNDK v30 source, manager binaries, process surface, Wi-Fi link surface가 모두 pass. device mutation, daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v407 다음: `approve v407 composite Wi-Fi HAL start-only retry only; no scan/connect/link-up and no Wi-Fi bring-up` 승인 시 bounded start-only retry만 실행한다. scan/connect/link-up, credentials, DHCP, routing은 별도 gate로 유지한다

   - v407 live report: `docs/reports/NATIVE_INIT_V407_COMPOSITE_HAL_START_ONLY_RETRY_LIVE_2026-05-20.md`
   - v407 live evidence: `tmp/wifi/v407-composite-hal-start-only-retry-live-20260520-101410/`
   - v407 live 결과: exact-approved bounded composite HAL start-only retry PASS. `servicemanager`, `hwservicemanager`, `vendor.samsung.hardware.wifi@2.0-service`가 모두 observe window 끝까지 observable했고 SIGTERM cleanup/reap/postflight safe로 종료됐다. scan/connect/link-up 및 Wi-Fi bring-up은 false
   - v407 해석: private namespace와 helper v24 `v30-to-system-ext-v30` 조합은 첫 HAL 후보를 bounded start-only로 유지할 수 있다
   - v408 다음: HAL registration/service-surface evidence를 수집하는 plan/approval packet을 작성한다. scan/connect/link-up, credentials, DHCP, routing은 계속 별도 gate로 유지한다

   - v408 plan: `docs/plans/NATIVE_INIT_V408_HAL_REGISTRATION_SURFACE_PLAN_2026-05-20.md`
   - v408 report: `docs/reports/NATIVE_INIT_V408_HAL_REGISTRATION_SURFACE_PACKET_2026-05-20.md`
   - v408 evidence: `tmp/wifi/v408-hal-registration-surface-packet-20260520-102249/`
   - v408 runner: `scripts/revalidation/wifi_hal_registration_surface_v408_packet.py`
   - v408 결과: host-only evidence packet PASS. V407 transcript에서 no-bring-up boundary, composite child start, private Binder/HwBinder/VndBinder devnodes, hwservice context inputs, HAL/hwservicemanager proc/fd/maps captures, Wi-Fi HIDL/HwBinder maps, fatal-runtime-noise absence, clean postflight를 모두 확인했다. V408 자체는 device command, daemon start, HAL start, Wi-Fi bring-up을 실행하지 않았다
   - v408 해석: V407은 실제 Wi-Fi bring-up이 아니라 “HAL service surface까지 살아 있음”을 증명한다. `hwservicemanager`에 실제 service publication/listing이 되었는지는 아직 미검증이다
   - v409 다음: 같은 bounded trio를 live로 띄운 상태에서 `hwservicemanager`/HIDL service-list registration query를 수행하는 gate를 설계한다. scan/connect/link-up, credentials, DHCP, routing은 계속 별도 gate로 유지한다

   - v409 plan: `docs/plans/NATIVE_INIT_V409_HAL_REGISTRATION_QUERY_PLAN_2026-05-20.md`
   - v409 report: `docs/reports/NATIVE_INIT_V409_HAL_REGISTRATION_QUERY_PREP_2026-05-20.md`
   - v409 helper artifact: `tmp/wifi/v409-a90_android_execns_probe-v25/a90_android_execns_probe`
   - v409 deploy wrapper: `scripts/revalidation/wifi_execns_helper_v25_deploy_preflight.py`
   - v409 query runner: `scripts/revalidation/wifi_hal_registration_query_v409_runner.py`
   - v409 결과: helper v25 `wifi-hal-composite-lshal-list` mode와 `--allow-hal-service-query` guard를 구현했고 static ARM64 build PASS, SHA `e90639d55dacc5486c998c4d1470235a6c72e4759cc63ebd1f07cf90c5852b37`. plan/no-approval manifests는 모두 device command와 mutation 없이 fail-closed PASS
   - v409 해석: 실제 `hwservicemanager` publication listing은 `/system/bin/lshal` 또는 별도 HIDL client가 필요하다. V409 runner는 먼저 `/mnt/system/system/bin/lshal` 존재를 read-only preflight로 확인하고, 없으면 V410으로 라우팅한다
   - v409 superseded: V409 approved-plan argcheck가 native argument budget을 맞추기 위해 `--data-wifi-mode private-empty`를 생략해야 했으므로 live deploy 전에 V410으로 대체했다. V409 deploy/query scripts는 이제 `v409-superseded-by-v410`으로 fail-closed된다

   - v409 read-only deploy preflight: `tmp/wifi/v409-helper-v25-deploy-readonly-preflight-20260520-103906/`
   - v409 read-only query preflight: `tmp/wifi/v409-registration-query-readonly-preflight-20260520-103926/`
   - v409 preflight 결과: deploy preflight는 `execns-helper-v25-deploy-preflight-ready-needs-deploy` PASS. query preflight는 `v409-hal-registration-query-blocked`이며 blocker는 `helper-v25`뿐이다. `/mnt/system/system/bin/lshal`, runtime materials, system_ext VNDK v30, service-manager binaries, process surface, Wi-Fi link surface는 모두 pass. device mutation, daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v409 preflight 해석: `lshal` direct path는 존재하지만 V409 arg-budget contract가 약하므로 exact-approved helper v25 deploy는 더 이상 next step이 아니다. V410 helper v26 + implicit `private-empty` contract가 대체 경로다
   - v409 guardcheck: `tmp/wifi/v409-helper-v25-deploy-guardcheck-preflight-20260520-104455/` PASS. deploy wrapper now records `local-helper-v25-query-guard=pass` and `remote-helper-v25-query-guard=needs-deploy`, proving the local artifact contains the explicit `--allow-hal-service-query` guard before deploy

   - v410 plan: `docs/plans/NATIVE_INIT_V410_ARG_BUDGET_REPAIR_PLAN_2026-05-20.md`
   - v410 report: `docs/reports/NATIVE_INIT_V410_ARG_BUDGET_REPAIR_PREP_2026-05-20.md`
   - v410 helper artifact: `tmp/wifi/v410-a90_android_execns_probe-v26/a90_android_execns_probe`
   - v410 deploy wrapper: `scripts/revalidation/wifi_execns_helper_v26_deploy_preflight.py`
   - v410 query runner: `scripts/revalidation/wifi_hal_registration_query_v410_runner.py`
   - v410 배경: exact-approved v409 query plan에서 command length는 29였지만 `--data-wifi-mode private-empty`가 빠졌다. live query에서 V407과 같은 private `/data/vendor/wifi` boundary를 유지하려면 배포 전 수정이 필요했다
   - v410 결과: helper v26은 `wifi-hal-composite-lshal-list` mode에서 `--data-wifi-mode`가 생략되면 `private-empty`를 기본값으로 설정한다. approved V410 query plan은 command length 29, `--allow-hal-service-query` present, `helper_implicit_data_wifi_mode=private-empty`, device commands false
   - v410 preflight 결과: deploy plan/preflight/no-approval PASS. query read-only preflight는 `lshal-binary` PASS와 `helper-v26` blocker만 확인했다. device mutation, daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v410 contract linter: `tmp/wifi/v410-arg-budget-linter-privatewrite-20260520-110025/` PASS. helper source default, data-wifi allowlist, runner implicit plan marker, deploy v26 guard, approved command arg budget, query guard, and host-only manifest contract all agree. Evidence output uses 0700 directory and 0600 no-follow/exclusive files
   - v410 deploy/live 결과: helper v26 deploy PASS 후 exact-approved bounded `lshal` registration query를 실행했다. Trio(`servicemanager`, `hwservicemanager`, Wi-Fi HAL)는 observable/clean stop PASS였고 Wi-Fi bring-up은 false였지만 `/system/bin/lshal` 기본 실행은 `lshal-timeout`으로 `v410-hal-registration-query-runtime-gap`을 반환했다
   - v410 해석: 기본 `lshal`은 binderized/passthrough 범위가 넓어 이 gate의 질문보다 과하다. 다음은 V411에서 `lshal list --types=binderized --neat`처럼 hwservicemanager 등록 목록만 좁혀 확인하는 helper/runner를 준비한다

   - v411 plan: `docs/plans/NATIVE_INIT_V411_BINDERIZED_LSHAL_QUERY_PLAN_2026-05-20.md`
   - v411 report: `docs/reports/NATIVE_INIT_V411_BINDERIZED_LSHAL_QUERY_PREP_2026-05-20.md`
   - v411 helper artifact: `tmp/wifi/v411-a90_android_execns_probe-v27/a90_android_execns_probe`
   - v411 deploy wrapper: `scripts/revalidation/wifi_execns_helper_v27_deploy_preflight.py`
   - v411 query runner: `scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py`
   - v411 결과: helper v27 `wifi-hal-composite-lshal-binderized-list` mode를 추가했고 query child를 `/system/bin/lshal list --types=binderized --neat`로 좁혔다. Static ARM64 build PASS, SHA `0519b557482f347d47962e9da76ee7afcce270bf12df860d37678e9a26bf2c74`. approved query plan은 command length 29로 유지된다
   - v411 preflight 결과: query read-only preflight는 expected blocker `helper-v27`만 남기고 `lshal-binary`, runtime materials, system_ext VNDK v30, service-manager binaries, process surface, Wi-Fi link surface를 PASS로 확인했다. deploy read-only preflight는 `execns-helper-v27-deploy-preflight-ready-needs-deploy` PASS
   - v411 contract linter: `tmp/wifi/v411-binderized-lshal-linter-20260520-113507/` PASS. helper source, runner, deploy wrapper, approved-plan/noapproval manifests, deploy plan, and read-only preflight all agree on the binderized-only lshal contract. Evidence output uses 0700 directory and 0600 no-follow/exclusive files
   - v411 다음: exact-approved helper v27 deploy only. Required phrase: `approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up`

### V428. Explicit lshal Status-Column Probe — RUNTIME-GAP / SAFE CLEANUP

- plan: `docs/plans/NATIVE_INIT_V428_LSHAL_STATUS_COLUMNS_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V428_LSHAL_STATUS_COLUMNS_2026-05-20.md`
- helper: `a90_android_execns_probe v29`
- helper artifact: `tmp/wifi/v428-a90_android_execns_probe-v29/a90_android_execns_probe`
- helper SHA256: `fcb1a7440995d018a73d52e74fbdd826102cc3fa93ba5f46d50bdca585f2d1bb`
- deploy evidence: `tmp/wifi/v428-helper-v29-deploy-live-20260520-141412/`
- live evidence: `tmp/wifi/v428-lshal-status-query-live-after-selinux-20260520-142354/`
- result:
  - deploy decision `execns-helper-v29-deploy-pass`.
  - live decision `v428-lshal-status-query-runtime-gap`.
  - VINTF-only native rows include `vendor.samsung.hardware.wifi@2.2::ISehWifi/default` as `declared`.
  - VINTF-only native rows do not include Samsung `ISehWifi/default` `@2.0` or `@2.1`.
  - composite status query child timed out: `wifi_hal_service_query.result=service-query-timeout`.
  - composite children were observable and postflight safe.
  - postflight process surface and Wi-Fi link surface were clean.
  - `wifi_bringup_executed=False`.
- interpretation: native private runtime still does not prove live Samsung Wi-Fi hwservice registration. Android boot-complete remains the richer service surface. Next should split the query into cheaper VINTF-only and binderized-only status probes before deciding on Android-managed Wi-Fi runtime control.
- next execution item: V429 minimal lshal status split; no Wi-Fi scan/connect/link-up yet.

### V429. Minimal lshal Status Split — RUNTIME-GAP / SAFE CLEANUP

- plan: `docs/plans/NATIVE_INIT_V429_LSHAL_MINIMAL_SPLIT_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V429_LSHAL_MINIMAL_SPLIT_2026-05-20.md`
- helper: `a90_android_execns_probe v30`
- helper artifact: `tmp/wifi/v429-a90_android_execns_probe-v30/a90_android_execns_probe`
- helper SHA256: `65b279db9f5a66979140b71688cd3998ddc5832c1ca374e2187db981d5c17757`
- deploy evidence: `tmp/wifi/v429-helper-v30-deploy-live-20260520-143348/`
- live evidence: `tmp/wifi/v429-lshal-minimal-split-live-20260520-144031/`
- result:
  - deploy decision `execns-helper-v30-deploy-pass`.
  - live decision `v429-lshal-minimal-split-runtime-gap`.
  - VINTF-only native rows include `vendor.samsung.hardware.wifi@2.2::ISehWifi/default` as `declared`.
  - VINTF-only native rows do not include Samsung `ISehWifi/default` `@2.0` or `@2.1`.
  - binderized-only status query child timed out: `wifi_hal_service_query.result=service-query-timeout`.
  - query argv was reduced to `/system/bin/lshal list --types=binderized --neat -S`.
  - composite children were observable and postflight safe.
  - postflight process surface and Wi-Fi link surface were clean.
  - `wifi_bringup_executed=False`.
- interpretation: V429 rules out V428's heavy `-p -e -c` and mixed `binderized,vintf` output as the main cause. Native private runtime still cannot return Samsung Wi-Fi binderized registrations. Android boot-complete evidence remains the stronger path.
- next execution item: V430 Android explicit-column mirror. Boot Android to `sys.boot_completed=1`, run read-only minimal `lshal` status commands, restore native v319, then decide Android-managed runtime pivot versus further native reconstruction.

### V430. Android lshal Explicit Mirror Result

- plan: `docs/plans/NATIVE_INIT_V430_ANDROID_LSHAL_EXPLICIT_MIRROR_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V430_ANDROID_LSHAL_EXPLICIT_MIRROR_2026-05-20.md`
- live evidence: `tmp/wifi/v430-android-lshal-explicit-handoff-live-fix-20260520-145456/`
- result: Android boot-complete handoff and native rollback PASS. Android neat `lshal` shows all three Samsung `ISehWifi/default` target rows, but explicit `lshal -S` exits `rc=136`; Wi-Fi bring-up remains false.
- next: V431 Android Wi-Fi runtime gap map. Collect read-only Android init rc/service/property/socket/devnode/data surfaces and compare them with the native private namespace before deciding Android-managed Wi-Fi control or native repair.

### V431. Android Wi-Fi Runtime Gap Map Result

- plan: `docs/plans/NATIVE_INIT_V431_ANDROID_RUNTIME_GAP_MAP_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V431_ANDROID_RUNTIME_GAP_MAP_2026-05-20.md`
- live evidence: `tmp/wifi/v431-android-runtime-gap-handoff-live-su-quote-20260520-152315/`
- result: Android boot-complete runtime map PASS. Android has the four target Wi-Fi runtime services running and defined, plus framework services, wifihal/wpa/CNSS sockets, `/dev/wlan`, `wlan0`/`swlan0`/`wifi-aware0`, and `/data/vendor/wifi` layout. Wi-Fi bring-up remains false and native v319 rollback was verified.
- next: V432 Android-managed Wi-Fi control gate plan. Split first control into a narrow enable/status gate with explicit cleanup; keep scan/connect/credentials/routing as later gates.

### V432. Android Wi-Fi Control Gate Result

- plan: `docs/plans/NATIVE_INIT_V432_ANDROID_WIFI_CONTROL_GATE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V432_ANDROID_WIFI_CONTROL_GATE_2026-05-20.md`
- live evidence: `tmp/wifi/v432-android-control-gate-handoff-live-classifierfix-20260520-154009/`
- result: Android boot-complete handoff and native rollback PASS. Android Wi-Fi was already enabled and connected from saved framework state by boot-complete, with `wifi_connected=True`, `android_auto_connect_observed=True`, and `wlan0_has_ip=True`. V432 did not issue enable/scan/connect/credential/routing operations and `wifi_bringup_executed=False`.
- next: V433 Android Wi-Fi auto-connect containment/stability gate. Do not proceed to scan/connect or server exposure until routing exposure, stability, cleanup, and intentional-disable behavior are characterized.

### V433. Android Wi-Fi Auto-connect Containment Result

- plan: `docs/plans/NATIVE_INIT_V433_ANDROID_WIFI_AUTOCONNECT_CONTAINMENT_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V433_ANDROID_WIFI_AUTOCONNECT_CONTAINMENT_2026-05-20.md`
- live evidence: `tmp/wifi/v433-android-autoconnect-containment-handoff-live-redactfix2-20260520-160156/`
- result: Android boot-complete handoff and native rollback PASS. Wi-Fi auto-connect was stable, `wlan0` had IP, default-route/local-route evidence pointed to `wlan0`, Android connectivity was validated, DNS surface was present, and no global listening sockets were observed. V433 did not send external probes or mutate Wi-Fi state; `wifi_bringup_executed=False`.
- next: V434 Android Wi-Fi auto-connect policy gate. Decide whether lab runs should disable/contain Android auto-connect or explicitly accept it for longer exposure-aware stability testing before any server exposure or explicit scan/connect work.

### V434. Android Wi-Fi Auto-connect Policy Result

- plan: `docs/plans/NATIVE_INIT_V434_ANDROID_WIFI_AUTOCONNECT_POLICY_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V434_ANDROID_WIFI_AUTOCONNECT_POLICY_2026-05-20.md`
- live evidence: `tmp/wifi/v434-android-autoconnect-policy-handoff-live-20260520-161134/`
- result: fresh V433 containment handoff plus host-side policy selection PASS. Policy is `contain-first` because Android Wi-Fi is stable and externally routed through saved auto-connect state. Native rollback restored `A90 Linux init 0.9.61 (v319)`, postflight selftest passed, and redaction scan passed.
- next: V435 bounded Android Wi-Fi auto-connect disable/containment proof. This is the first cleanup/containment gate; it should still forbid scan/connect, credentials, server exposure, and external probes.

### V435. Android Wi-Fi Auto-connect Disable Result

- plan: `docs/plans/NATIVE_INIT_V435_ANDROID_WIFI_AUTOCONNECT_DISABLE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V435_ANDROID_WIFI_AUTOCONNECT_DISABLE_2026-05-20.md`
- live evidence: `tmp/wifi/v435-android-wifi-disable-handoff-live-statefix-20260520-163102/`
- result: bounded Android Wi-Fi disable containment PASS. `cmd wifi set-wifi-enabled disabled` executed, final corrected state had Wi-Fi disabled, no `wlan0` IP, no `wlan0` route candidate, no active validated Wi-Fi connectivity, no DNS surface, and no global listener. Native rollback restored `A90 Linux init 0.9.61 (v319)`.
- next: V436 Android Wi-Fi disabled persistence check. Boot Android and verify containment without another disable command before deciding controlled re-enable or native-side Wi-Fi work.

### V436. Android Wi-Fi Disabled Persistence Result

- plan: `docs/plans/NATIVE_INIT_V436_ANDROID_WIFI_DISABLED_PERSISTENCE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V436_ANDROID_WIFI_DISABLED_PERSISTENCE_2026-05-20.md`
- live evidence: `tmp/wifi/v436-android-wifi-disabled-persistence-handoff-live-20260520-164037/`
- result: read-only Android disabled persistence PASS. Android boot-complete showed Wi-Fi still disabled, no `wlan0` IP, no `wlan0` route candidate, no active validated Wi-Fi connectivity, no active DNS surface, and no global listener. No additional disable command ran.
- next: V437 controlled Android Wi-Fi branch decision. Decide whether to run a controlled re-enable observation gate or resume native-side Wi-Fi integration while preserving Android disabled containment.

### V437. Wi-Fi Branch Decision Result

- plan: `docs/plans/NATIVE_INIT_V437_WIFI_BRANCH_DECISION_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V437_WIFI_BRANCH_DECISION_2026-05-20.md`
- host-run evidence: `tmp/wifi/v437-wifi-branch-decision-hostrun-20260520-164708/`
- result: host-side branch decision PASS. Selected `controlled-android-reenable-observation` because V436 proved persistent disabled containment. No device command or mutation ran.
- next: V438 controlled Android Wi-Fi re-enable observation. Permit only bounded `cmd wifi set-wifi-enabled enabled`; still forbid scan/connect, credentials, server exposure, external probes, and routing mutation.

### V438. Android Wi-Fi Re-enable Observation Result

- plan: `docs/plans/NATIVE_INIT_V438_ANDROID_WIFI_REENABLE_OBSERVATION_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V438_ANDROID_WIFI_REENABLE_OBSERVATION_2026-05-20.md`
- live evidence: `tmp/wifi/v438-android-wifi-reenable-handoff-live-20260520-165358/`
- result: bounded Android Wi-Fi re-enable observation PASS. Android accepted `cmd wifi set-wifi-enabled enabled`; post-enable status reported Wi-Fi enabled, but no active Wi-Fi connection, no `wlan0` IP, no `wlan0` route candidate, no validated Wi-Fi connectivity, no DNS surface, and no global listener were observed. Native rollback restored `A90 Linux init 0.9.61 (v319)`, postflight selftest passed, and redaction scan passed.
- interpretation: V438 is a controlled bring-up observation, not permission for scan/connect, credentials, server exposure, or external traffic. Android framework Wi-Fi is now set enabled and may persist on a future Android boot, even though the current native boot is contained.
- next: V439 post-reenable persistence and containment decision. Either run a longer read-only enabled observation, or disable Wi-Fi again to restore the V436 contained baseline before continuing native/server-side work.

### V439. Android Post-reenable Observation Result

- plan: `docs/plans/NATIVE_INIT_V439_ANDROID_POST_REENABLE_OBSERVATION_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V439_ANDROID_POST_REENABLE_OBSERVATION_2026-05-20.md`
- live evidence: `tmp/wifi/v439-android-wifi-post-reenable-handoff-live-20260520-170736/`
- result: Android post-reenable observation PASS with exposure observed. V439 did not enable Wi-Fi; it observed the V438-enabled Android state. Android immediately auto-connected and exposed `wlan0` IP, default route, route-get, DNS, and validated Wi-Fi connectivity across seven samples, with no global listener observed. Final cleanup disable passed and removed active IP/route/DNS/connectivity exposure. Native rollback restored `A90 Linux init 0.9.61 (v319)`.
- interpretation: Android-managed Wi-Fi is now proven functional, but it is also proven to create external network exposure via saved auto-connect. Cleanup containment works, so lab-safe work should default to disabled Wi-Fi except during bounded Wi-Fi tests.
- next: V440 Android Wi-Fi control policy after proven auto-connect. Decide contained lab mode versus exposure-aware Android Wi-Fi mode versus explicit scan/connect mode before any server exposure or credential work.

### V440. Android Wi-Fi Control Policy Result

- plan: `docs/plans/NATIVE_INIT_V440_ANDROID_WIFI_CONTROL_POLICY_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V440_ANDROID_WIFI_CONTROL_POLICY_2026-05-20.md`
- host-run evidence: `tmp/wifi/v440-android-wifi-control-policy-hostrun-20260520-171835/`
- result: host-side policy selector PASS. Selected `contained-lab-default` because V439 proved Android-managed Wi-Fi functionality, immediate external route/DNS/connectivity exposure through saved auto-connect, no global listener, and successful cleanup containment.
- interpretation: default lab state is Wi-Fi disabled unless a bounded Wi-Fi test is active. Android-managed Wi-Fi may be used for explicit exposure-aware test windows, but server exposure and explicit scan/connect remain blocked until policy/credential/target handling is documented.
- next: V441 planning. Choose exposure-aware Wi-Fi stability observation with cleanup, or explicit scan/connect credential and target allowlist design. Serverization remains blocked.

### V441. Android Wi-Fi Exposure-aware Stability Result

- plan: `docs/plans/NATIVE_INIT_V441_ANDROID_WIFI_EXPOSURE_STABILITY_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V441_ANDROID_WIFI_EXPOSURE_STABILITY_2026-05-20.md`
- live evidence: `tmp/wifi/v441-android-wifi-exposure-stability-live-20260520-172446/`
- result: exposure-aware Android-managed Wi-Fi stability PASS. V441 used V438 to enable Wi-Fi and V439 to observe 11 samples over 300 seconds. All samples stayed connected/exposed with `wlan0` IP, default route, route-get, validated connectivity, and DNS surface; no global listener was observed. Cleanup disable passed and removed active IP/route/DNS/connectivity exposure. Native rollback restored `A90 Linux init 0.9.61 (v319)`.
- interpretation: Android-managed Wi-Fi is functionally stable enough for bounded test windows. The next risk boundary is explicit scan/connect and credential/target handling, not basic connectivity. Server exposure remains blocked.
- next: V442 credential/target allowlist design before explicit scan/connect. Longer stability can be run later, but the immediate design gap is policy-safe credential and target handling.

### V442. Wi-Fi Target Policy Result

- plan: `docs/plans/NATIVE_INIT_V442_WIFI_TARGET_POLICY_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V442_WIFI_TARGET_POLICY_2026-05-20.md`
- host-run evidence: `tmp/wifi/v442-android-wifi-target-policy-hostrun-20260520-174415/`
- result: host-side target/credential policy gate PASS in template mode. V441 evidence was ready, V442 generated a secret-free target policy template, and the tracked example policy was correctly rejected as not live-ready because it contains a placeholder `ssid_sha256`.
- interpretation: explicit scan/connect is now blocked on an operator-provided private untracked target policy, not on basic Wi-Fi function. Raw SSID/BSSID/password/passphrase/PSK values must not enter tracked files or evidence.
- next: V443 private-policy validation plus explicit scan/connect preflight. Do not issue scan/connect until V442 returns `v442-wifi-target-policy-allowlist-ready` for a private policy.

### V443. Wi-Fi Private Policy Materialize Result

- plan: `docs/plans/NATIVE_INIT_V443_WIFI_PRIVATE_POLICY_MATERIALIZE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V443_WIFI_PRIVATE_POLICY_MATERIALIZE_2026-05-20.md`
- evidence:
  - `tmp/wifi/v443-private-policy-materialize-plan-20260520-174833/`
  - `tmp/wifi/v443-private-policy-materialize-env-missing-20260520-174833/`
- result: materializer plan PASS and env-missing negative validation PASS. `A90_WIFI_SSID` and `A90_WIFI_PSK` are not currently present, so V443 refused to create a private policy.
- interpretation: the private policy materializer is ready. The next blocker is local operator env values, which must not be pasted into chat, committed, or written to tracked files.
- next: set `A90_WIFI_SSID` and `A90_WIFI_PSK` locally, rerun V443 to produce `v443-wifi-private-policy-materialized-pass`, then proceed to V444 explicit scan/connect preflight.

### V444. Wi-Fi Explicit Connect Preflight Result

- plan: `docs/plans/NATIVE_INIT_V444_WIFI_EXPLICIT_CONNECT_PREFLIGHT_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V444_WIFI_EXPLICIT_CONNECT_PREFLIGHT_2026-05-20.md`
- evidence:
  - `tmp/wifi/v444-explicit-connect-preflight-plan-20260520-175411/`
  - `tmp/wifi/v444-explicit-connect-preflight-missing-policy-20260520-175411/`
  - `tmp/wifi/v444-explicit-connect-preflight-synthetic-pass-20260520-175411/`
- result: host-side explicit scan/connect preflight implemented. Missing real private policy is blocked as expected. Synthetic positive path passed and did not leak synthetic SSID/PSK into evidence.
- interpretation: V445 live execution is now technically gated, but real execution remains blocked until V443 materializes a private policy from local env values and V444 returns `v444-wifi-explicit-connect-preflight-ready` for that policy.
- next: provide local private env values, rerun V443 and V444, then run V445 bounded explicit scan/connect. Server exposure remains blocked.

### V445. Wi-Fi Explicit Connect Live Runner Result

- plan: `docs/plans/NATIVE_INIT_V445_WIFI_EXPLICIT_CONNECT_LIVE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V445_WIFI_EXPLICIT_CONNECT_LIVE_2026-05-20.md`
- evidence:
  - `tmp/wifi/v445-explicit-connect-live-plan-20260520-180041/`
  - `tmp/wifi/v445-explicit-connect-live-dryrun-20260520-180041/`
  - `tmp/wifi/v445-explicit-connect-live-missing-policy-fixed-20260520-180117/`
- result: V445 bounded explicit scan/connect live runner implemented. Plan/dry-run passed. Missing real policy live attempt was blocked by V444 preflight before Android boot/flash; no device commands, no device mutations, no Wi-Fi bring-up.
- interpretation: the live runner exists and is fail-closed at the correct boundary. Actual V445 live remains blocked until V443 materializes a private policy and V444 returns ready for that policy.
- next: set local private env values, run V443, rerun V444, then run V445 live. Server exposure remains blocked.

### V446. Wi-Fi Private Secret Guard Result

- plan: `docs/plans/NATIVE_INIT_V446_WIFI_PRIVATE_SECRET_GUARD_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V446_WIFI_PRIVATE_SECRET_GUARD_2026-05-20.md`
- evidence:
  - clean scan `tmp/wifi/v446-wifi-private-secret-guard-postdoc-20260520-181446/`
  - negative probe `tmp/wifi/v446-wifi-private-secret-guard-negative-20260520-181251/`
- result: repository-side private Wi-Fi secret guard PASS. `.gitignore` now blocks local env and private/local Wi-Fi target policy filenames. The scanner passed on current tracked plus untracked repository-visible files, and a synthetic negative probe correctly failed closed with findings before the probe was removed.
- interpretation: V445 live is still blocked by missing real private env/policy, but the local credential flow now has a repo guard before V443/V444/V445.
- next: set local private env values outside chat/tracked files, run V443 materialization, run V444 preflight, then run V445 live. Server exposure remains blocked.

### V447. Wi-Fi Explicit Connect Flow Result

- plan: `docs/plans/NATIVE_INIT_V447_WIFI_EXPLICIT_CONNECT_FLOW_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V447_WIFI_EXPLICIT_CONNECT_FLOW_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v447-explicit-connect-flow-plan-final2-20260520-182148/`
  - env-missing `tmp/wifi/v447-explicit-connect-flow-env-missing-final2-20260520-182148/`
  - synthetic preflight `tmp/wifi/v447-explicit-connect-flow-synthetic-final2-20260520-182148/`
- result: one-command gated flow implemented. Current real env state blocks at V443 because `A90_WIFI_SSID` and `A90_WIFI_PSK` are absent. Synthetic host-only flow passed V446, V443, and V444 and stopped before V445 live.
- interpretation: manual sequencing is no longer the blocker. The next blocker is local private Wi-Fi env input, followed by a V447 host preflight and explicit V447/V445 live run.
- next: set private local env values outside chat/tracked files, run V447 host preflight, then rerun V447 with live flags for bounded explicit scan/connect. Server exposure remains blocked.

### V448. Wi-Fi Operator Handoff Packet Result

- plan: `docs/plans/NATIVE_INIT_V448_WIFI_OPERATOR_HANDOFF_PACKET_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V448_WIFI_OPERATOR_HANDOFF_PACKET_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v448-operator-handoff-packet-plan-final-20260520-182644/`
  - run `tmp/wifi/v448-operator-handoff-packet-run-final-20260520-182644/`
- result: private handoff packet PASS. V448 ran V446, ran V447 plan, then generated ignored scripts for V447 host preflight and V447 live without storing Wi-Fi values.
- interpretation: the repo-side and operator-sequencing work is ready for the real private Wi-Fi input. V448 itself did not run V443/V444/V445, mutate the device, or bring Wi-Fi up.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v448-operator-handoff-packet-run-final-20260520-182644/run-v447-host-preflight.sh`, enter Wi-Fi values locally, then run the generated live script only if preflight returns ready. Server exposure remains blocked.

### V449. Wi-Fi Handoff Result Router Result

- plan: `docs/plans/NATIVE_INIT_V449_WIFI_HANDOFF_RESULT_ROUTER_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V449_WIFI_HANDOFF_RESULT_ROUTER_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v449-wifi-handoff-result-router-plan-final-20260520-183130/`
  - run `tmp/wifi/v449-wifi-handoff-result-router-run-final-20260520-183130/`
- result: handoff result router PASS. V449 read current V448/V447/V445 evidence, ignored synthetic/plan/env-missing evidence by default, and classified the state as `v449-wifi-handoff-packet-ready-run-preflight`.
- interpretation: the current safe next action is the generated V448 host preflight script. No private V447 preflight result exists yet.
- next: run the recommended host preflight script, then rerun V449. If private preflight passes, V449 should recommend the generated live script. Server exposure remains blocked.

### V450. Wi-Fi Operator Preflight Readiness Result

- plan: `docs/plans/NATIVE_INIT_V450_WIFI_OPERATOR_PREFLIGHT_READINESS_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V450_WIFI_OPERATOR_PREFLIGHT_READINESS_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v450-operator-preflight-readiness-plan-final-20260520-183553/`
  - run `tmp/wifi/v450-operator-preflight-readiness-run-final-20260520-183553/`
- result: operator preflight readiness PASS. V450 confirmed the latest V448 packet is ready, generated scripts are private and structurally valid, V449 routes to host preflight, and no private preflight/live result has superseded the packet yet.
- interpretation: there is no remaining repo-side/env-free blocker before local Wi-Fi input. The next required action is running the generated host preflight script.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v448-operator-handoff-packet-run-final-20260520-182644/run-v447-host-preflight.sh`, then rerun V449/V450. Server exposure remains blocked.

### V451. Wi-Fi Operator Script Validation Result

- plan: `docs/plans/NATIVE_INIT_V451_WIFI_OPERATOR_SCRIPT_VALIDATION_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V451_WIFI_OPERATOR_SCRIPT_VALIDATION_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v451-operator-script-validation-plan-final-20260520-184016/`
  - run `tmp/wifi/v451-operator-script-validation-run-final-20260520-184016/`
- result: operator script validation PASS. V451 validated generated V448 host preflight/live scripts with `bash -n`, verified host preflight empty-input fail-closed behavior, and verified live cancellation fail-closed behavior.
- interpretation: generated operator scripts now have syntax and fail-closed prompt validation in addition to V450 structural/private-mode validation.
- next: run the generated host preflight script, enter Wi-Fi values locally, then rerun V449/V450. Server exposure remains blocked.

### V452. Wi-Fi Live Cleanup Proof Result

- plan: `docs/plans/NATIVE_INIT_V452_WIFI_LIVE_CLEANUP_PROOF_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V452_WIFI_LIVE_CLEANUP_PROOF_2026-05-20.md`
- evidence:
  - pre-live run `tmp/wifi/v452-wifi-live-cleanup-proof-run-final-20260520-184611/`
  - synthetic pass `tmp/wifi/v452-wifi-live-cleanup-proof-synth-pass-final-20260520-184611/`
  - synthetic blocked cleanup `tmp/wifi/v452-wifi-live-cleanup-proof-synth-block-final-20260520-184611/`
- result: post-live cleanup proof gate implemented. Current real state is `v452-wifi-live-cleanup-proof-awaiting-live`, which is expected before private host preflight/live. Synthetic pass and blocked-cleanup paths verified that the gate accepts complete cleanup evidence and fails closed on incomplete cleanup.
- interpretation: after eventual V447 live, V452 must pass before Wi-Fi stability or server binding work proceeds.
- next: run the generated host preflight script, enter Wi-Fi values locally, run live if routed, then run V452 on live evidence. Server exposure remains blocked.

### V453. Wi-Fi Operator Post-route Packet Result

- plan: `docs/plans/NATIVE_INIT_V453_WIFI_OPERATOR_POSTROUTE_PACKET_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V453_WIFI_OPERATOR_POSTROUTE_PACKET_2026-05-20.md`
- evidence:
  - packet `tmp/wifi/v453-operator-postroute-packet-run-final-20260520-185152/`
  - router `tmp/wifi/v449-wifi-handoff-result-router-v453-final-20260520-185152/`
  - readiness `tmp/wifi/v450-operator-preflight-readiness-v453-final-20260520-185152/`
- result: post-route operator packet PASS. V453 generated preflight/live scripts that run V449/V450/V452 automatically after V447 attempts, validated their shell syntax and fail-closed prompt behavior, and updated V449/V450 routing to prefer the latest V448 or V453 packet.
- interpretation: V453 supersedes the older V448 packet for the next operator action. The next command now records routing/proof evidence automatically after execution.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v453-operator-postroute-packet-run-final-20260520-185152/run-v453-host-preflight-and-route.sh`, enter Wi-Fi values locally, then follow the routed live command. Server exposure remains blocked.

### V454. Wi-Fi Operator Strict Post-route Packet Result

- plan: `docs/plans/NATIVE_INIT_V454_WIFI_OPERATOR_STRICT_POSTROUTE_PACKET_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V454_WIFI_OPERATOR_STRICT_POSTROUTE_PACKET_2026-05-20.md`
- evidence:
  - packet `tmp/wifi/v454-operator-strict-postroute-packet-run-20260520-185718/`
  - router `tmp/wifi/v449-wifi-handoff-result-router-v454-20260520-185718/`
  - readiness `tmp/wifi/v450-operator-preflight-readiness-v454-20260520-185718/`
- result: strict post-route operator packet PASS. V454 generated preflight/live scripts that run V449/V450/V452 automatically after V447 attempts and return a post-route failure if V447 succeeds but route/proof evidence generation fails.
- interpretation: V454 supersedes V453 for the next operator action. It is the strongest current handoff packet.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v454-operator-strict-postroute-packet-run-20260520-185718/run-v454-host-preflight-strict-route.sh`, enter Wi-Fi values locally, then follow the routed live command. Server exposure remains blocked.

### V455. Wi-Fi Strict Post-route Semantics Result

- plan: `docs/plans/NATIVE_INIT_V455_WIFI_STRICT_POSTROUTE_SEMANTICS_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V455_WIFI_STRICT_POSTROUTE_SEMANTICS_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v455-strict-postroute-semantics-plan-20260520-190248/`
  - run `tmp/wifi/v455-strict-postroute-semantics-run-20260520-190248/`
- result: strict post-route semantics PASS. V455 audited the generated V454 scripts for strict markers and proved the return-code matrix: V447 success plus route/proof failure fails the script, while V447 failure preserves the V447 return code.
- interpretation: V454 strict behavior is now proven without executing generated operator scripts or device commands.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v454-operator-strict-postroute-packet-run-20260520-185718/run-v454-host-preflight-strict-route.sh`, enter Wi-Fi values locally, then follow the routed live command. Server exposure remains blocked.

### V456. Wi-Fi Operator One-session Packet Result

- plan: `docs/plans/NATIVE_INIT_V456_WIFI_OPERATOR_ONE_SESSION_PACKET_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V456_WIFI_OPERATOR_ONE_SESSION_PACKET_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v456-operator-one-session-packet-plan-20260520-191243/`
  - packet `tmp/wifi/v456-operator-one-session-packet-run-20260520-191231/`
  - router `tmp/wifi/v449-wifi-handoff-result-router-v456-20260520-191231/`
  - readiness `tmp/wifi/v450-operator-preflight-readiness-v456-20260520-191231/`
  - secret guard `tmp/wifi/v446-wifi-private-secret-guard-v456-repair2-20260520-191231/`
- result: one-session operator packet PASS. V456 generated one private script that prompts once, runs V447 preflight, routes/proves the result, then optionally runs V447 live after exact `V447-LIVE` confirmation.
- interpretation: V456 supersedes V454 as the next operator action because it preserves strict post-route behavior while removing duplicate Wi-Fi credential prompts.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v456-operator-one-session-packet-run-20260520-191231/run-v456-one-session-wifi-flow.sh`, enter Wi-Fi values locally, and type `V447-LIVE` only if preflight passes. Server exposure remains blocked.

### V457. Wi-Fi Operator Session Outcome Result

- plan: `docs/plans/NATIVE_INIT_V457_WIFI_OPERATOR_SESSION_OUTCOME_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V457_WIFI_OPERATOR_SESSION_OUTCOME_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v457-wifi-operator-session-outcome-plan-20260520-191957/`
  - run `tmp/wifi/v457-wifi-operator-session-outcome-run-20260520-191957/`
  - secret guard `tmp/wifi/v446-wifi-private-secret-guard-v457-20260520-191957/`
- result: outcome gate PASS. Current state is `v457-wifi-session-awaiting-operator` because V456 is ready and no real V447 preflight/live evidence exists yet.
- interpretation: V457 is the no-secret post-run classifier. After the operator runs V456, V457 summarizes whether the session is blocked, live-pending, cleanup-proof-pending, or ready for bounded stability/server-binding policy.
- next: run the V456 one-session script locally, then run `python3 scripts/revalidation/wifi_operator_session_outcome_v457.py run`. Server exposure remains blocked.

### V458. Wi-Fi Operator Session Bundle Result

- plan: `docs/plans/NATIVE_INIT_V458_WIFI_OPERATOR_SESSION_BUNDLE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V458_WIFI_OPERATOR_SESSION_BUNDLE_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v458-wifi-operator-session-bundle-plan-20260520-192406/`
  - run `tmp/wifi/v458-wifi-operator-session-bundle-run-20260520-192406/`
  - secret guard `tmp/wifi/v446-wifi-private-secret-guard-v458-20260520-192406/`
- result: sanitized session bundle PASS. Current state is `v458-wifi-session-bundle-awaiting-operator` with `leak_findings=0`.
- interpretation: after V456 runs, V457 should classify the result and V458 should package the current evidence as a sanitized index without copying raw captures.
- next: run the V456 one-session script locally, then run V457 and V458. Server exposure remains blocked.

### V459. Wi-Fi NetworkManager Profile Handoff Result

- plan: `docs/plans/NATIVE_INIT_V459_WIFI_NM_PROFILE_HANDOFF_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V459_WIFI_NM_PROFILE_HANDOFF_2026-05-20.md`
- evidence:
  - packet `tmp/wifi/v459-nm-profile-handoff-packet-run-20260520-193122/`
  - router `tmp/wifi/v449-wifi-handoff-result-router-v459-20260520-193122/`
  - readiness `tmp/wifi/v450-operator-preflight-readiness-v459-20260520-193122/`
  - outcome `tmp/wifi/v457-wifi-operator-session-outcome-v459-20260520-193122/`
  - bundle `tmp/wifi/v458-wifi-operator-session-bundle-v459-20260520-193122/`
  - secret guard `tmp/wifi/v446-wifi-private-secret-guard-v459-final-20260520-193122/`
- result: saved-profile handoff PASS. V459 generated a private script that lists saved NetworkManager Wi-Fi profiles by number and length metadata only, then runs V447 preflight/live with strict route/proof handling.
- interpretation: V459 supersedes V456 as the preferred next local action on this host because two saved Wi-Fi profiles exist and the operator can choose by number without typing SSID/PSK into the terminal.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v459-nm-profile-handoff-packet-run-20260520-193122/run-v459-nm-profile-wifi-flow.sh`, select the intended saved profile, and type `V447-LIVE` only if preflight passes. Server exposure remains blocked.

### V460. Wi-Fi Live Retry Pass Result

- plan: `docs/plans/NATIVE_INIT_V460_WIFI_LIVE_RETRY_PASS_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V460_WIFI_LIVE_RETRY_PASS_2026-05-20.md`
- evidence:
  - live `tmp/wifi/v447-explicit-connect-flow-live-20260520-194306/`
  - cleanup proof `tmp/wifi/v452-wifi-live-cleanup-proof-postlive-20260520-194829/`
  - outcome `tmp/wifi/v457-wifi-operator-session-outcome-postlive2-20260520-194857/`
  - bundle `tmp/wifi/v458-wifi-operator-session-bundle-postlive2-20260520-194857/`
- result: bounded Wi-Fi live PASS. V447 live produced explicit scan/connect evidence, V452 proved cleanup containment and rollback step presence, and native `A90 Linux init 0.9.61 (v319)` was verified after rollback.
- interpretation: Wi-Fi bring-up is proven for a bounded live run. This is not yet a long-running Wi-Fi stability or server exposure approval.
- next: plan bounded Wi-Fi stability and binding policy before any server exposure. Server exposure remains blocked.

### V742. Execns Helper v122 Deploy Result

- plan: `docs/plans/NATIVE_INIT_V742_EXECNS_HELPER_V122_DEPLOY_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V742_EXECNS_HELPER_V122_DEPLOY_2026-05-24.md`
- evidence: `tmp/wifi/v742-execns-helper-v122-deploy-run-serial1850/`
- result: helper v122 deployed to `/cache/bin/a90_android_execns_probe`; remote SHA `032fe43041b908577bb1a2e4b3ff7a7dfea24958169723907df5d403f811e989` and marker `a90_android_execns_probe v122` verified.
- interpretation: helper v122 deployment is not the active blocker. Serial chunk size `1850` is safe; chunk size `3000` was rejected before writes because it exceeded the safe command-line limit.
- next: run current-boot V741 gated `mdm_helper` proof after SELinuxfs and policy-load prep.

### V743. V741 Current Live Execution Result

- plan: `docs/plans/NATIVE_INIT_V743_V741_CURRENT_LIVE_EXECUTION_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V743_V741_CURRENT_LIVE_EXECUTION_2026-05-24.md`
- evidence: `tmp/wifi/v743-v741-mdm-helper-gated-live-current/`
- result: V741 gated mode ran safely, `mss` reached `ONLINE`, lower/CNSS children started, but service `74` gate stayed closed and `mdm_helper` was not started. Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping were not executed.
- interpretation: do not force `mdm_helper`; first separate whether the gate miss is helper v122 regression or gated-mode timing/logic.
- next: rerun V735 CNSS-only path with helper v122.

### V744. V122 CNSS-only Comparison Result

- plan: `docs/plans/NATIVE_INIT_V744_V122_CNSS_ONLY_COMPARISON_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V744_V122_CNSS_ONLY_COMPARISON_2026-05-24.md`
- evidence: `tmp/wifi/v744-v122-cnss-only-comparison-retry/`
- result: helper v122 still reproduces the V735 CNSS-only service publication path: `mss=ONLINE`, QRTR RX/TX, `sysmon-qmi`, and service-notifier `180` appeared; MHI/QCA6390/WLFW/service `69`/BDF/`wlan0` remained absent.
- interpretation: helper v122 itself is not the regression. The active blocker is now the service-publication-to-MHI/WLFW gap, plus a secondary repair candidate in V741 gated `mdm_helper` gate timing.
- next: implement a two-phase same-window proof: first observe CNSS-only service publication, then start `mdm_helper` only after that marker, still below service-manager/HAL/scan/connect.

### V745. Service180-gated MDM Helper Prep Result

- plan: `docs/plans/NATIVE_INIT_V745_SERVICE180_GATED_MDM_HELPER_PLAN_2026-05-24.md`
- prep report: `docs/reports/NATIVE_INIT_V745_SERVICE180_GATED_MDM_HELPER_PREP_2026-05-24.md`
- live report: `docs/reports/NATIVE_INIT_V745_SERVICE180_GATED_MDM_HELPER_LIVE_2026-05-24.md`
- evidence:
  - helper build `tmp/wifi/v745-execns-helper-v123-build/`
  - runner plan `tmp/wifi/v745-mdm-helper-service180-live-plan2/`
  - deploy preflight `tmp/wifi/v745-execns-helper-v123-deploy-preflight-after-hide/`
  - deploy run `tmp/wifi/v745-execns-helper-v123-deploy-run-serial1850/`
  - live run `tmp/wifi/v745-mdm-helper-service180-live-current/`
- result: helper v123 deployed and live-tested. The run reached `mss=ONLINE`, QRTR RX/TX, and `sysmon-qmi`, but service `180` gate stayed closed; `mdm_helper`, service-manager, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, and external ping were not executed.
- interpretation: service `180` is not stable enough as the next live gate. `sysmon-qmi` is the reproducible lower marker in the same window.
- next: implement and deploy helper v124 with sysmon-gated `mdm_helper` start-only.

### V746. Sysmon-gated MDM Helper Prep Result

- plan: `docs/plans/NATIVE_INIT_V746_SYSMON_GATED_MDM_HELPER_PLAN_2026-05-24.md`
- prep report: `docs/reports/NATIVE_INIT_V746_SYSMON_GATED_MDM_HELPER_PREP_2026-05-24.md`
- live report: `docs/reports/NATIVE_INIT_V746_SYSMON_GATED_MDM_HELPER_LIVE_2026-05-24.md`
- evidence:
  - helper build `tmp/wifi/v746-execns-helper-v124-build/`
  - runner plan `tmp/wifi/v746-mdm-helper-sysmon-live-plan-final/`
  - deploy preflight `tmp/wifi/v746-execns-helper-v124-deploy-preflight-final/`
  - deploy run `tmp/wifi/v746-execns-helper-v124-deploy-run-serial1850/`
  - live run `tmp/wifi/v746-mdm-helper-sysmon-live-current/`
- result: helper v124 deployed and live-tested. The `sysmon-qmi` gate opened, `mdm_helper` started and was postflight-safe, but `mdm3` stayed `OFFLINING`; MHI/QCA6390/WLFW/service `69`/BDF/`wlan0` stayed absent. Service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not executed.
- interpretation: `mdm_helper` is not sufficient for the current lower blocker. Native evidence now shows the `a0000000.qcom,cnss-qca6390` platform device exists but has no `driver` link, and `/sys/bus/mhi/devices` is empty.
- next: V747 should be a read-only Android/native QCA6390 driver-binding and MHI power-up comparison. Do not perform generic ICNSS/CNSS bind or unbind.

### V747. QCA6390 Driver-binding Delta Plan

- plan: `docs/plans/NATIVE_INIT_V747_QCA6390_DRIVER_BINDING_DELTA_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V747_QCA6390_DRIVER_BINDING_DELTA_2026-05-24.md`
- basis evidence:
  - `tmp/wifi/v746-mdm-helper-sysmon-live-current/`
  - `tmp/wifi/v717-provider-first-icnss-edge-long-observe-20260524-103333/`
  - `tmp/wifi/v717-icnss-edge-surface-classifier/`
  - `tmp/wifi/v717-qca-bind-reconciliation/`
- run evidence: `tmp/wifi/v747-qca6390-driver-binding-delta/`
- result: host-only classifier passed with decision `v747-qca-driver-link-gap-not-bind-target`. V746 confirms `mdm_helper` is safe but insufficient; QCA6390 child remains unbound; V716 keeps bind/unbind blocked; Android reference is usable.
- interpretation: the next target is not `mdm_helper` and not QCA6390 `bind`/`unbind`.
- next: V748 classified the remaining candidate matrix and selected a read-only non-bind ICNSS/QCA WLFW trigger capture as the next gate.

### V748. Non-bind ICNSS/QCA Power-up Trigger Classifier

- plan: `docs/plans/NATIVE_INIT_V748_NONBIND_POWERUP_TRIGGER_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V748_NONBIND_POWERUP_TRIGGER_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_nonbind_powerup_trigger_v748.py`
- plan evidence: `tmp/wifi/v748-nonbind-powerup-trigger-plan/`
- preflight evidence: `tmp/wifi/v748-nonbind-powerup-trigger-preflight/`
- run evidence: `tmp/wifi/v748-nonbind-powerup-trigger/`
- decision: `v748-icnss-qmi-wlfw-nonbind-trigger-selected`
- result: host-only classifier passed. It rejected QCA6390 `bind`/`unbind`, `mdm_helper` retry, repeated CNSS/HAL start, and `wlan` module load; it marked the private vendor firmware namespace as satisfied.
- interpretation: the remaining pre-connection blocker is below Wi-Fi HAL/connect. The next unit must identify the non-bind ICNSS/CNSS2/QCA path that advances Android from ICNSS parent readiness to WLFW/BDF/`wlan0`.
- next: V749 selected the concrete non-bind control candidate for the next lower-window proof.

### V749. Non-bind Trigger Selector

- plan: `docs/plans/NATIVE_INIT_V749_NONBIND_TRIGGER_SELECTOR_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V749_NONBIND_TRIGGER_SELECTOR_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_nonbind_trigger_selector_v749.py`
- plan evidence: `tmp/wifi/v749-nonbind-trigger-selector-plan/`
- preflight evidence: `tmp/wifi/v749-nonbind-trigger-selector-preflight/`
- run evidence: `tmp/wifi/v749-nonbind-trigger-selector/`
- decision: `v749-lower-window-boot-wlan-trigger-selected`
- result: read-only selector passed. Current native exposes `boot_wlan` and `qcwlanstate=OFF`, does not expose `fs_ready`, and still has no `/dev/wlan`, wiphy, or `wlan0`.
- interpretation: standalone `boot_wlan` and standalone `qcwlanstate` are already rejected by V508/V513. The only useful next write is a bounded `boot_wlan` proof inside the lower-ready firmware/modem/companion window.
- next: V750 should implement lower-window `boot_wlan` observe only. Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and bind/unbind blocked.

### V750. Lower-window Boot WLAN Proof

- plan: `docs/plans/NATIVE_INIT_V750_LOWER_WINDOW_BOOT_WLAN_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V750_LOWER_WINDOW_BOOT_WLAN_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_lower_window_boot_wlan_v750.py`
- evidence:
  - plan `tmp/wifi/v750-lower-window-boot-wlan-plan/`
  - first preflight `tmp/wifi/v750-lower-window-boot-wlan-preflight/`
  - current V401 `tmp/wifi/v750-v401-current-run/`
  - current V490 `tmp/wifi/v750-v490-current-run/`
  - final preflight `tmp/wifi/v750-lower-window-boot-wlan-preflight-retry/`
  - live `tmp/wifi/v750-lower-window-boot-wlan/`
- decision: `v750-lower-window-boot-wlan-control-surface-only`
- result: live proof passed safely. Firmware mounts, `subsys_modem` holder, QRTR RX/TX, `sysmon-qmi`, lower companion contract, `boot_wlan` write, and reboot cleanup all passed. `qcwlanstate` stayed `OFF`; `/dev/wlan`, wiphy, `wlan0`, WLFW/service `69`, and BDF stayed absent.
- interpretation: lower-window `boot_wlan` is not the missing single trigger. The active blocker is now the ICNSS/QCA "modules initialized" path before WLFW/BDF/`wlan0`.
- next: V751 should classify why `icnss: Modules not initialized just return` persists in native. Keep bind/unbind, `driver_override`, module load/unload, service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V751. ICNSS Module-init Classifier

- plan: `docs/plans/NATIVE_INIT_V751_ICNSS_MODULE_INIT_CLASSIFIER_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V751_ICNSS_MODULE_INIT_CLASSIFIER_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_icnss_module_init_classifier_v751.py`
- evidence:
  - plan `tmp/wifi/v751-icnss-module-init-classifier-plan/`
  - run `tmp/wifi/v751-icnss-module-init-classifier/`
- decision: `v751-boot-wlan-hdd-init-stalls-before-driver-loaded`
- result: read-only classifier passed. V750 `boot_wlan` enters QCACLD/HDD init and creates `qcwlanstate`, but `wlan: driver loaded`, ICNSS-QMI, firmware-ready, wiphy, and `wlan0` never appear. Current native has ICNSS parent bound, but no ICNSS net/ieee80211 child and no MHI devices.
- interpretation: the blocker is inside or before the HDD/PLD/register-driver completion path, not the fixed `boot_wlan` write itself.
- next: V752 should choose between bounded CNSS-daemon plus `boot_wlan` ordering proof and deeper HDD/PLD prerequisite instrumentation. Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, bind/unbind, `driver_override`, and module load/unload blocked.

### V752. CNSS then Boot WLAN Proof

- plan: `docs/plans/NATIVE_INIT_V752_CNSS_THEN_BOOT_WLAN_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V752_CNSS_THEN_BOOT_WLAN_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_cnss_then_boot_wlan_v752.py`
- evidence:
  - plan `tmp/wifi/v752-cnss-then-boot-wlan-plan2/`
  - initial preflight `tmp/wifi/v752-cnss-then-boot-wlan-preflight/`
  - current V401 `tmp/wifi/v752-v401-current-run/`
  - current V490 `tmp/wifi/v752-v490-current-run/`
  - final preflight `tmp/wifi/v752-cnss-then-boot-wlan-preflight-retry/`
  - live `tmp/wifi/v752-cnss-then-boot-wlan/`
- decision: `v752-cnss-then-boot-wlan-hdd-init-still-stalls`
- result: live proof passed safely. Firmware mounts, `subsys_modem` holder, QRTR RX/TX, `sysmon-qmi`, six-child CNSS companion start-only, `boot_wlan` observe, and reboot cleanup all passed. `cnss_diag` and `cnss-daemon` started, but `qcwlanstate` stayed `OFF`; `/dev/wlan`, ICNSS net/ieee80211 child, wiphy, `wlan0`, WLFW/service `69`, BDF, ICNSS-QMI, and firmware-ready stayed absent.
- interpretation: CNSS companion ordering before `boot_wlan` is not sufficient. The blocker remains inside or immediately before HDD/PLD/register-driver completion.
- next: V753 should instrument HDD/PLD prerequisites and the missing driver-loaded / ICNSS-QMI transition. Do not repeat CNSS plus `boot_wlan` ordering blindly; keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, bind/unbind, `driver_override`, and module load/unload blocked.

### V753. HDD/PLD Prerequisite Classifier

- plan: `docs/plans/NATIVE_INIT_V753_HDD_PLD_PREREQ_CLASSIFIER_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V753_HDD_PLD_PREREQ_CLASSIFIER_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_hdd_pld_prereq_classifier_v753.py`
- evidence:
  - plan `tmp/wifi/v753-hdd-pld-prereq-classifier-plan/`
  - run `tmp/wifi/v753-hdd-pld-prereq-classifier/`
- decision: `v753-hdd-pld-register-driver-gap-needs-instrumentation`
- result: read-only classifier passed. V752 is valid input, stayed in the safety envelope, and confirmed HDD entry (`boot_wlan=True`, `wlan_loading=1`, `hdd_state_major=1`, `qcwlanstate=30`). No explicit `hdd_init`/PLD/register-driver failure marker appeared, and no driver-loaded/ICNSS-QMI/FW-ready/WLFW/BDF/wiphy/`wlan0` marker appeared. Current native remains healthy and contained with no wiphy/`wlan0`.
- interpretation: current evidence cannot distinguish `pld_init`, `hdd_init`, and `wlan_hdd_register_driver` as the stall point. Another CNSS/`boot_wlan` retry is not useful without new instrumentation.
- next: V754 should add bounded, source-backed HDD/PLD/register-driver observability. If this needs boot image changes, use the standard build/flash/rollback gate; keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V754. HDD/PLD Traceability Selector

- plan: `docs/plans/NATIVE_INIT_V754_HDD_PLD_TRACEABILITY_SELECTOR_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V754_HDD_PLD_TRACEABILITY_SELECTOR_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_hdd_pld_traceability_selector_v754.py`
- evidence:
  - plan `tmp/wifi/v754-hdd-pld-traceability-selector-plan/`
  - run `tmp/wifi/v754-hdd-pld-traceability-selector/`
- decision: `v754-tracefs-mount-gated-observer-needed`
- result: read-only selector passed. tracefs/debugfs filesystem support exists, tracefs/debugfs are not mounted, target symbols are partially visible in `/proc/kallsyms`, and no tracefs mount or ftrace write was executed. `available_filter_functions` is not readable until a mount/filter proof.
- interpretation: ftrace readiness is not proven yet, but a bounded tracefs mount/filter proof is the least invasive next observability gate before any boot image instrumentation or another Wi-Fi trigger.
- next: V755 should mount tracefs with cleanup, read `available_tracers`/`current_tracer`/`available_filter_functions`, verify target filter functions, then stop before `boot_wlan`, service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

### V755. Tracefs Mount/Filter Proof

- plan: `docs/plans/NATIVE_INIT_V755_TRACEFS_MOUNT_FILTER_PROOF_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V755_TRACEFS_MOUNT_FILTER_PROOF_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_tracefs_mount_filter_proof_v755.py`
- evidence:
  - plan `tmp/wifi/v755-tracefs-mount-filter-proof-plan/`
  - preflight retry `tmp/wifi/v755-tracefs-mount-filter-proof-preflight-retry/`
  - final live `tmp/wifi/v755-tracefs-mount-filter-proof-retry/`
- decision: `v755-tracefs-mounted-no-target-filter-functions`
- result: bounded live proof passed. Tracefs mount returned `0`, controls were readable only for `available_tracers`, `current_tracer`, `tracing_on`, and `trace`; `available_filter_functions`, `set_ftrace_filter`, and `set_graph_function` were not readable. Target filter hits were `0`. Cleanup unmounted tracefs and postflight confirmed `mount_tracefs=no`.
- interpretation: ftrace/function-filter instrumentation is not available for the HDD/PLD target on this kernel state. Do not proceed to ftrace write or boot_wlan trace pairing.
- next: V756 should plan non-ftrace HDD/PLD observability: Android/native dmesg differential expansion, source-backed boot image/kernel-log instrumentation feasibility, or another safe non-ftrace signal path. Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V756. Non-ftrace HDD/PLD Observability

- plan: `docs/plans/NATIVE_INIT_V756_NONFTRACE_HDD_PLD_OBSERVABILITY_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V756_NONFTRACE_HDD_PLD_OBSERVABILITY_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_nonftrace_hdd_pld_observability_v756.py`
- evidence:
  - plan `tmp/wifi/v756-nonftrace-hdd-pld-observability-plan/`
  - run `tmp/wifi/v756-nonftrace-hdd-pld-observability/`
- decision: `v756-nonftrace-live-observers-exhausted`
- result: read-only classifier passed. Dynamic debug is not compiled in and has no control catalog; kprobes and kprobe events are not configured; printk exists but current dmesg does not expose the missing PLD/HDD/register-driver boundary; target kallsyms remain partially visible; no wiphy or `wlan0` appeared.
- interpretation: live ftrace/dyndbg/kprobe instrumentation is not available on this kernel state. Another `boot_wlan` retry will not add evidence.
- next: V757 should either perform expanded Android/native dmesg differential analysis around the HDD/PLD window or plan a rollback-safe boot-image/kernel-log instrumentation unit. Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V757. Android/Native HDD/PLD Differential

- plan: `docs/plans/NATIVE_INIT_V757_ANDROID_NATIVE_HDD_PLD_DIFF_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V757_ANDROID_NATIVE_HDD_PLD_DIFF_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_android_native_hdd_pld_diff_v757.py`
- evidence:
  - plan `tmp/wifi/v757-android-native-hdd-pld-diff-plan/`
  - run `tmp/wifi/v757-android-native-hdd-pld-diff/`
- decision: `v757-boot-image-log-instrumentation-selected`
- result: host-only classifier passed. Android success evidence contains QMI/BDF/FW-ready/`wlan0`; native V752 evidence contains HDD entry/qcwlanstate creation with success-marker absence; existing Android dmesg has post-FW HDD markers but no pre-QMI PLD/HDD/register-driver boundary.
- interpretation: existing dmesg proves the gap but cannot locate the internal failing call. Live ftrace/dyndbg/kprobe routes are closed.
- next: V758 should classify rollback-safe kernel/source/boot-image log instrumentation feasibility before any patch. Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V758. Kernel Instrumentation Feasibility

- plan: `docs/plans/NATIVE_INIT_V758_KERNEL_INSTRUMENTATION_FEASIBILITY_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V758_KERNEL_INSTRUMENTATION_FEASIBILITY_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_kernel_instrumentation_feasibility_v758.py`
- evidence:
  - plan `tmp/wifi/v758-kernel-instrumentation-feasibility-plan/`
  - run `tmp/wifi/v758-kernel-instrumentation-feasibility/`
- decision: `v758-source-acquisition-required-before-kernel-instrumentation`
- result: host-only classifier passed. Boot image tooling and rollback artifacts exist, including current/v319/v261/v48 images, but exact local kernel/QCACLD/CNSS source is absent.
- interpretation: boot-image handoff is feasible after source exists, but patching now would be blind and should remain blocked.
- next: V759 should acquire or stage exact SM-A908N/A908NKSU5EWA3-compatible Samsung kernel source and verify target files before any instrumentation patch. Keep live device, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V759. Source Acquisition Gate

- plan: `docs/plans/NATIVE_INIT_V759_SOURCE_ACQUISITION_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V759_SOURCE_ACQUISITION_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_source_acquisition_v759.py`
- evidence:
  - plan `tmp/wifi/v759-source-acquisition-plan/`
  - run `tmp/wifi/v759-source-acquisition/`
- decision: `v759-official-source-identified-manual-download-gated`
- result: host-only classifier passed. The exact Samsung OSRC package is identified as `SM-A908N_KOR_12_Opensource.zip` for `SM-A908N` / `A908NKSU5EWA3` with source upload id `13272` and announcement attach id `39494`; the source download is hCaptcha/manual-browser gated and the archive is not staged locally.
- interpretation: kernel instrumentation remains blocked until the official source archive is manually downloaded, staged under an ignored path, and verified for target QCACLD/CNSS files.
- next: V760 should verify the staged official archive/source tree and target file availability before any kernel instrumentation patch. Keep live device, boot-image writes, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V760. Source Staging Verifier

- plan: `docs/plans/NATIVE_INIT_V760_SOURCE_STAGING_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V760_SOURCE_STAGING_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_source_staging_v760.py`
- evidence:
  - plan `tmp/wifi/v760-source-staging-plan/`
  - run `tmp/wifi/v760-source-staging/`
- decision: `v760-source-stage-missing`
- result: host-only verifier passed as a classifier. `kernel_build/` is now an explicit ignored staging area with a tracked README/.gitkeep, but the official source archive or extracted source tree is still absent. Target QCACLD/CNSS files are not verified.
- interpretation: the kernel instrumentation path is still blocked by external/manual source staging, not by repo tooling.
- next: manually download `SM-A908N_KOR_12_Opensource.zip`, stage it under `kernel_build/`, rerun V760, and only proceed to V761 kernel log instrumentation planning after target source files are verified. Keep live device, boot-image writes, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V761. Source Download Handoff

- plan: `docs/plans/NATIVE_INIT_V761_SOURCE_DOWNLOAD_HANDOFF_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V761_SOURCE_DOWNLOAD_HANDOFF_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_source_handoff_v761.py`
- evidence:
  - plan `tmp/wifi/v761-source-download-handoff-plan/`
  - run `tmp/wifi/v761-source-download-handoff/`
- decision: `v761-source-download-handoff-ready`
- result: host-only handoff packet passed. It generated private `handoff.md` and `run-v761-source-download-handoff.sh`; the script opens the browser only with `V761_OPEN_BROWSER=1`, copies only an already downloaded official archive into ignored `kernel_build/`, and reruns V760.
- interpretation: the source blocker is reduced to one manual browser download plus rerun; no device or boot-image work is justified until V760 verifies target source files.
- next: execute the generated V761 handoff after downloading the official OSRC package, rerun V760, then proceed to kernel log instrumentation planning only after target files are verified. Keep live device, boot-image writes, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V762. Source Target Verification

- plan: `docs/plans/NATIVE_INIT_V762_SOURCE_TARGET_VERIFICATION_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V762_SOURCE_TARGET_VERIFICATION_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_source_staging_v760.py`
- evidence:
  - run `tmp/wifi/v760-source-staging/`
- decision: `v760-source-targets-verified`
- result: host-only verifier passed after operator staging. `Kernel.tar.gz` inside `kernel_build/SM-A908N_KOR_12_Opensource/` exposes the live ICNSS/QCACLD target groups: `qcacld_hdd_main`, `qcacld_hdd_driver_ops`, `qcacld_pld_snoc`, `icnss_core`, and `icnss_qmi`. V760 was tightened to require those groups and accept Samsung's actual `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0` path.
- interpretation: the source acquisition blocker is cleared for planning, and the instrumentation target must be ICNSS/QMI/WLFW service-69 plus PLD-SNOC callbacks rather than CNSS2/MHI. This does not authorize patching, building, flashing, or live Wi-Fi bring-up yet.
- next: V763 should rebase the architecture target to ICNSS/QCACLD before V764 plans minimal kernel log instrumentation. Keep source patching/building, boot-image writes, live device, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until their own gates.

### V763. ICNSS Architecture Rebase

- plan: `docs/plans/NATIVE_INIT_V763_ICNSS_ARCH_REBASE_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V763_ICNSS_ARCH_REBASE_2026-05-24.md`
- runner: host/source/evidence review
- evidence:
  - `tmp/wifi/v760-source-staging/`
  - `tmp/wifi/v711-icnss-edge-readonly-live/native/`
  - `tmp/wifi/v744-v122-cnss-only-comparison/native/cnss2-driver-ls-before.txt`
- decision: `v763-icnss-architecture-rebased`
- result: host-only correction passed. SM-A908N live path is ICNSS/QCACLD SNOC, not CNSS2/MHI. Source and evidence identify `drivers/soc/qcom/icnss_qmi.c`, `drivers/soc/qcom/icnss.c`, `pld_snoc.c`, and HDD files as the instrumentation targets.
- interpretation: the root edge to prove is WLFW service `69` -> `wlfw_new_server()` -> `icnss_call_driver_probe()` -> `pld_snoc_probe()` -> HDD startup. Service `180/74` remains side evidence, but V764 was redirected to retry the current service180-gated `mdm_helper` question before source instrumentation.
- next: V764 should classify V745-V749 evidence and rerun a bounded service180-gated `mdm_helper` proof with direct mdm/esoc surface capture. Keep source patching/building, boot-image writes, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until their own gates.

### V764. Service180-gated MDM Helper Retry

- plan: `docs/plans/NATIVE_INIT_V764_SERVICE180_MDM_HELPER_RETRY_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V764_SERVICE180_MDM_HELPER_RETRY_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_mdm_helper_service180_retry_v764.py`
- evidence:
  - V401 prerequisite: `tmp/wifi/v764-v401-toybox-selinuxfs-mount/`
  - live: `tmp/wifi/v764-mdm-helper-service180-retry/`
- decision: `v764-mdm-helper-started-no-lower-progress`
- result: bounded live proof passed. Current service-notifier `180` opened, helper v124 started `mdm_helper`, and cleanup left native healthy. `mss` reached `ONLINE`, but `mdm3` stayed `OFFLINING`; WLFW service `69`, MHI/QCA6390, BDF, and `wlan0` remained absent. No service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, esoc0 open/hold, subsystem write, bind/unbind, or boot image write was executed.
- access surface: `/sys/bus/esoc/devices/esoc0` and `/sys/class/subsys/subsys_esoc0` are visible with `SDX50M`/`PCIe` metadata, but `/dev/subsys_esoc0` is absent. Global native `/vendor/bin/mdm_helper` is not visible; it only starts inside the private vendor namespace helper path.
- interpretation: this closes the requested mdm_helper retry. `mdm_helper` is safe and startable under service180, but still insufficient as the lower trigger. Unless new evidence changes the service180/esoc model, do not repeat `mdm_helper` as the primary trigger.
- next: reconcile V764 with V749/V750 lower-window `boot_wlan` and the later HDD/PLD stall evidence. If that still cannot locate the gap, return to minimal ICNSS/QCACLD source log instrumentation as a separate V765+ gate.

### V765. ICNSS/QCACLD Log Patch Generator

- plan: `docs/plans/NATIVE_INIT_V765_ICNSS_QCACLD_LOG_PATCH_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V765_ICNSS_QCACLD_LOG_PATCH_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_log_patch_v765.py`
- evidence:
  - `tmp/wifi/v765-icnss-qcacld-log-patch/manifest.json`
  - `tmp/wifi/v765-icnss-qcacld-log-patch/a90-v765-icnss-qcacld-log.patch`
- decision: `v765-icnss-qcacld-log-patch-ready`
- result: host-only patch generator passed. It generated a review-only unified diff with 19 `A90V765` log insertions across ICNSS QMI/core, PLD-SNOC, and QCACLD HDD loader/register/startup paths. It did not mutate `kernel_build`, build a kernel, write a boot image, or run any device command.
- interpretation: after V764 closed the `mdm_helper` retry path, the strongest next path is source-backed instrumentation. V765 provides the patch artifact needed to locate the HDD/PLD/register-driver stall, while keeping build/apply/flash as separate gates.
- next: V766 should apply the generated patch to a disposable source build tree and run build/package checks. Keep boot-image writes, live handoff, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until their own gates.

### V766. ICNSS/QCACLD Patch Apply Build-readiness

- plan: `docs/plans/NATIVE_INIT_V766_ICNSS_QCACLD_PATCH_APPLY_BUILD_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V766_ICNSS_QCACLD_PATCH_APPLY_BUILD_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_patch_apply_build_v766.py`
- evidence:
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/manifest.json`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/logs/patch-dry-run.txt`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/logs/patch-apply.txt`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/logs/defconfig.txt`
- decision: `v766-patch-applied-defconfig-pass-toolchain-incomplete`
- result: V766 corrected the V765 patch formatting issue, safely extracted the Samsung OSRC source to private evidence, applied the `A90V765` patch cleanly, verified 19 markers, and passed `r3q_kor_single_defconfig`. It did not mutate `kernel_build`, run a full kernel build, write a boot image, or run any device command.
- interpretation: instrumentation is now source-apply-ready and defconfig-ready. The next host blocker is not patch context; it is selecting/staging a compatible Android/Samsung toolchain for a bounded full kernel build/package check.
- next: V767 should select or stage toolchain inputs and run a bounded full kernel build/package readiness gate. Keep boot-image writes, live handoff, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until their own gates.

### V767. ICNSS/QCACLD Full Build Gate

- plan: `docs/plans/NATIVE_INIT_V767_ICNSS_QCACLD_FULL_BUILD_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V767_ICNSS_QCACLD_FULL_BUILD_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_full_build_v767.py`
- evidence:
  - `tmp/wifi/v767-icnss-qcacld-full-build/manifest.json`
  - `tmp/wifi/v767-icnss-qcacld-full-build/logs/kernel-build.txt`
- decision: `v767-instrumented-objects-built-rkp-cfp-python2-blocked`
- result: V767 staged ignored Android/Samsung toolchain inputs, applied disposable host-build repairs, and ran a bounded full kernel build. The build compiled all five ICNSS/QCACLD instrumented target objects with all 19 `A90V765` markers preserved. Final `Image` packaging did not complete because Samsung post-link `scripts/rkp_cfp/instrument.py` is Python2-only and fails under the current host Python path.
- interpretation: the V765 patch is now source-apply, defconfig, and target-object compile proven. This does not explain why WLFW service `69` is absent at runtime; it only proves the planned printk instrumentation can compile up to the relevant object boundary.
- next: split the work into two gates. V768 should classify the mdm_helper/esoc/mdm3 gap without repeating blind Wi-Fi starts. A later packaging gate can decide whether to provide Python2, port/patch `RKP_CFP`, or intentionally bypass that post-link step for a diagnostic boot image. Keep boot-image writes, live handoff, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until their own gates.

### V768. MDM3/ESOC Gap Classifier

- plan: `docs/plans/NATIVE_INIT_V768_MDM3_ESOC_GAP_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V768_MDM3_ESOC_GAP_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_mdm3_esoc_gap_classifier_v768.py`
- evidence:
  - `tmp/wifi/v768-mdm3-esoc-gap-classifier/manifest.json`
  - `tmp/wifi/v768-mdm3-esoc-gap-classifier/summary.md`
- decision: `v768-mdm3-esoc-gap-rerouted-to-instrumentation-packaging`
- result: host-only classifier PASS. V764 already proves service180-gated `mdm_helper` starts with no mdm3/WLFW/BDF/`wlan0` progress. Direct esoc0 open/hold remains unavailable because `/dev/subsys_esoc0` is absent and no safe init-visible contract is proven. Blind lower-window `boot_wlan` retry remains rejected without new observability. V767 proves the ICNSS/QCACLD instrumentation objects compile.
- interpretation: the runtime `mdm_helper`/esoc direct retry branch is not the best next step. The nearest diagnostic path is to get the V767 instrumented kernel through final packaging so the missing HDD/PLD/ICNSS boundary can be observed on-device.
- next: V769 should solve the RKP_CFP/Python2 packaging blocker inside the disposable source tree, or explicitly classify a diagnostic-only RKP_CFP bypass. Keep boot-image handoff, flash, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until separate gates.

### V769. RKP_CFP Python3 Packaging Gate

- plan: `docs/plans/NATIVE_INIT_V769_RKP_CFP_PYTHON3_PACKAGING_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V769_RKP_CFP_PYTHON3_PACKAGING_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_rkp_cfp_packaging_v769.py`
- evidence:
  - `tmp/wifi/v769-rkp-cfp-python3-packaging/manifest.json`
  - `tmp/wifi/v769-rkp-cfp-python3-packaging/logs/kernel-build.txt`
  - `tmp/wifi/v769-rkp-cfp-python3-packaging/logs/rkp-cfp-py-compile.txt`
- decision: `v769-rkp-cfp-python3-repair-image-pass`
- result: bounded host packaging gate PASS. The runner applies idempotent Python3 compatibility repairs for Samsung `scripts/rkp_cfp`, compiles the repaired scripts, and reruns the V767 bounded build path. Final `Image` and `Image-dtb` are present in the disposable source tree; all five ICNSS/QCACLD instrumented objects still exist and preserve all 19 `A90V765` markers.
- safety: no boot image write, partition write, flash, reboot, device command, service-manager/Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, or external ping was executed.
- interpretation: the V767 final-image blocker was host `RKP_CFP` Python compatibility, not the Wi-Fi instrumentation patch. The instrumented kernel is now image-ready for a separate diagnostic boot-image staging gate.
- next: V770 should package/stage a diagnostic boot image from the V769 `Image` and existing boot artifacts without flashing. Live flash/reboot and Wi-Fi observation remain separate explicit gates.

### V770. Instrumented Diagnostic Boot Staging

- plan: `docs/plans/NATIVE_INIT_V770_INSTRUMENTED_DIAGNOSTIC_BOOT_STAGING_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V770_INSTRUMENTED_DIAGNOSTIC_BOOT_STAGING_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_diag_boot_staging_v770.py`
- evidence:
  - `tmp/wifi/v770-instrumented-diagnostic-boot-staging/manifest.json`
  - `tmp/wifi/v770-instrumented-diagnostic-boot-staging/boot_linux_v770_icnss_diag.img`
  - `tmp/wifi/v770-instrumented-diagnostic-boot-staging/logs/unpack-staged.txt`
- decision: `v770-instrumented-diagnostic-boot-staged`
- result: local-only staging PASS. The runner repacked V769 `Image-dtb` with the current verified v724 native-init ramdisk/header metadata. The staged image is 4096-byte aligned, mode `0600`, contains the native-init v724 marker and all 19 `A90V765` markers, and unpacks back to a kernel hash matching the V769 `Image-dtb`.
- safety: created a local tmp boot image only. No device command, partition write, flash, reboot, service-manager/Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, or external ping was executed.
- interpretation: the diagnostic boot artifact is ready for an explicitly gated live handoff. This still has not proven runtime Wi-Fi; it only prepares the observable kernel needed to classify the HDD/PLD/ICNSS stall on-device.
- next: V771 should flash the staged diagnostic image under rollback rules, boot native init, verify serial/bridge health, capture dmesg for `A90V765` markers around `boot_wlan`, and roll back if health fails. Wi-Fi scan/connect and credential use remain blocked until `wlan0`/wiphy exists.

### V771. Diagnostic Live Handoff Boot Failure

- report: `docs/reports/NATIVE_INIT_V771_DIAGNOSTIC_LIVE_HANDOFF_BOOT_FAIL_2026-05-25.md`
- recovery_report: `docs/reports/NATIVE_INIT_V771_ROLLBACK_RECOVERY_2026-05-25.md`
- evidence:
  - `tmp/wifi/v771-diagnostic-live-handoff-20260525-013724/native-init-flash.txt`
  - `tmp/wifi/v771-diagnostic-live-handoff-20260525-013724/abort-state.txt`
  - `tmp/wifi/v771-rollback-v724-20260525-014803/native-init-flash-rollback.txt`
  - `tmp/wifi/v771-rollback-v724-20260525-014803/post-rollback-verify.txt`
- decision: `v771-instrumented-kernel-boot-failed-download-mode`
- result: live handoff failed after a successful TWRP flash/readback. The V770 image was pushed to recovery, remote sha256 matched local, `dd` to `/dev/block/by-name/boot` completed, and boot partition prefix sha256 matched. After `twrp reboot`, native init did not verify and the phone enumerated as Samsung Download mode (`04e8:685d`) with no ADB device.
- interpretation: the failure is not an adb push, TWRP transfer, or boot partition write mismatch. The V769/V770 instrumented OSRC kernel image is not currently boot-compatible with the known-good native-init boot image. Do not retry the same V770 image as-is.
- recovery: completed. TWRP flashed `stage3/boot_linux_v724.img`, remote sha256 and boot prefix sha256 matched `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682`, and native verify passed with `version/status rc=0 status=ok`. Post-rollback `bootstatus` reports `BOOT OK shell 4.1s`; `selftest` reports `pass=11 warn=1 fail=0`.
- next: V772 should run a host-only boot incompatibility classifier before any further custom-kernel flash. Wi-Fi scan/connect and credential use remain blocked until `wlan0`/wiphy exists on a healthy native boot.

### V772. Boot Incompatibility Classifier

- plan: `docs/plans/NATIVE_INIT_V772_BOOT_INCOMPAT_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V772_BOOT_INCOMPAT_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_boot_incompat_classifier_v772.py`
- evidence:
  - `tmp/wifi/v772-boot-incompat-classifier/manifest.json`
  - `tmp/wifi/v772-boot-incompat-classifier/logs/base-ikconfig.txt`
  - `tmp/wifi/v772-boot-incompat-classifier/logs/diag-ikconfig.txt`
- decision: `v772-boot-fail-likely-missing-appended-dtb`
- result: host-only classifier PASS. The known-good v724 kernel payload has three appended FDT blobs at offsets `48830500`, `49327831`, and `49827440`; the V770 diagnostic payload has zero FDT magic hits. The stock DTB tail is `997113` bytes. Embedded kernel configs match, and the diagnostic payload still contains all 19 `A90V765` markers.
- interpretation: V771 likely failed because V770 packaged a bare OSRC-built/instrumented kernel payload without the appended device DTB tail required by this boot path. The write/readback was valid, but the kernel payload was structurally not boot-compatible. Do not retry V770 as-is.
- next: V773 should be local-only: append the stock v724 DTB tail to the V769 instrumented Image payload, repack, and verify FDT/marker/roundtrip checks before any live flash is considered.

### V773. Stock DTB Tail Repack

- plan: `docs/plans/NATIVE_INIT_V773_STOCK_DTB_TAIL_REPACK_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V773_STOCK_DTB_TAIL_REPACK_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_dtb_tail_repack_v773.py`
- evidence:
  - `tmp/wifi/v773-stock-dtb-tail-repack/manifest.json`
  - `tmp/wifi/v773-stock-dtb-tail-repack/instrumented-image-with-stock-dtb-tail.bin`
  - `tmp/wifi/v773-stock-dtb-tail-repack/boot_linux_v773_icnss_diag_stockdtb.img`
- decision: `v773-stock-dtb-tail-diagnostic-boot-staged`
- result: local-only repack PASS. The runner appended the stock v724 DTB tail to the V769 instrumented payload and repacked a private diagnostic boot image. The combined kernel has three FDT blobs at offsets `48830516`, `49327847`, and `49827456`, preserves all 19 `A90V765` markers, and roundtrips through `unpack_bootimg.py`. The staged boot image is 4096-byte aligned, mode `0600`, size `53972992`, sha256 `0fcde6e76fd0de3d2b974aad20dcbbba714e5a81b9fccf5ea2b6a67bdc06f400`.
- safety: no device command, partition write, flash, reboot, service-manager/Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, or external ping was executed.
- interpretation: V773 removes the missing-DTB-tail structural blocker found by V772, but live boot is still unproven. A future live gate must flash only this V773 artifact with rollback ready and immediate health checks.
- next: superseded by V774 live result. Wi-Fi scan/connect and credentials remain blocked until `wlan0`/wiphy exists.

### V774. Stock DTB Tail Live Boot Failure

- report: `docs/reports/NATIVE_INIT_V774_STOCK_DTB_TAIL_LIVE_BOOT_FAIL_2026-05-25.md`
- evidence:
  - `tmp/wifi/v774-stockdtb-live-handoff-20260525-015926/native-init-flash-v773.txt`
  - `tmp/wifi/v774-stockdtb-live-handoff-20260525-015926/abort-state.txt`
  - `tmp/wifi/v774-rollback-v724-20260525-020056/native-init-flash-rollback.txt`
- decision: `v774-stock-dtb-tail-kernel-boot-failed-recovery-mode`
- result: live handoff failed after a successful TWRP flash/readback of the V773 stock-DTB-tail image. The local image sha256 was `0fcde6e76fd0de3d2b974aad20dcbbba714e5a81b9fccf5ea2b6a67bdc06f400`; the remote pushed image matched; `dd` to `/dev/block/by-name/boot` completed; and the boot partition prefix sha256 matched. After `twrp reboot`, native init did not verify. The abort snapshot initially showed no ADB devices, and recovery/TWRP was subsequently available.
- recovery: completed. TWRP flashed `stage3/boot_linux_v724.img`, remote sha256 and boot prefix sha256 matched `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682`, and native verify passed with `version/status rc=0 status=ok`. Current native status reports `BOOT OK shell 4.2s`; `selftest` reports `pass=11 warn=1 fail=0`.
- interpretation: V773 eliminated the missing appended DTB tail as the sole V771 root cause, but the current Samsung OSRC-built instrumented kernel remains live-boot incompatible. V774 differs from V771 because the failure returned to or remained recoverable through TWRP/recovery instead of Download mode, but the same no-retry rule applies to the current custom-kernel artifacts.
- next: superseded by V775. Prefer stock-kernel runtime observability over further custom-kernel flash.

### V775. Boot Incompatibility Postmortem

- plan: `docs/plans/NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_boot_incompat_postmortem_v775.py`
- evidence:
  - `tmp/wifi/v775-boot-incompat-postmortem/manifest.json`
  - `tmp/wifi/v775-boot-incompat-postmortem/summary.md`
  - `tmp/wifi/v775-boot-incompat-postmortem/logs/unpack-base-boot.txt`
  - `tmp/wifi/v775-boot-incompat-postmortem/logs/unpack-diag-boot.txt`
- decision: `v775-non-dtb-custom-kernel-incompat-classified`
- result: host-only classifier PASS. The v724 stock and V773 diagnostic boot header args match after normalized unpack, and both kernel payloads contain three appended FDT blobs. The remaining differences are non-DTB: V773 diagnostic kernel size is `49827629` vs stock `49827613`, every appended FDT offset is shifted by `16` bytes, kernel provenance/toolchain strings differ, and coarse RKP/RTIC marker counts differ.
- observability: config surface confirms `CONFIG_KPROBES=n`, `CONFIG_DYNAMIC_DEBUG=n`, `CONFIG_FUNCTION_TRACER=n`, `CONFIG_FTRACE=y`, `CONFIG_TRACEPOINTS=y`, `CONFIG_BPF_SYSCALL=y`, and `CONFIG_BPF_EVENTS=y`.
- interpretation: missing appended DTB tail is no longer the sole cause. The custom OSRC kernel flash route is paused until a separate host-only compatibility gate explains the remaining production/provenance/pre-DTB delta. Repeating V770, V773, or equivalent OSRC-built images is blocked.
- next: superseded by V776. No custom kernel flash.

### V776. Tracepoint Inventory

- plan: `docs/plans/NATIVE_INIT_V776_TRACEPOINT_INVENTORY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V776_TRACEPOINT_INVENTORY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_tracepoint_inventory_v776.py`
- evidence:
  - `tmp/wifi/v776-tracepoint-inventory/manifest.json`
  - `tmp/wifi/v776-tracepoint-inventory/summary.md`
  - `tmp/wifi/v776-tracepoint-inventory/native/available-events-head.txt`
  - `tmp/wifi/v776-tracepoint-inventory/native/candidate-*.txt`
- decision: `v776-tracepoint-candidates-found`
- result: live stock-v724 bounded tracefs inventory PASS. V776 temporarily mounted tracefs, read event surfaces, and unmounted cleanly. `available_events` is readable with `1250` events. Candidate counts: ICNSS/WLAN/Wi-Fi `1`, QMI/QRTR/service `1`, subsystem/remoteproc `3`, network stack `39`, scheduler/workqueue/IRQ `109`, total `153`.
- focused candidates: `cfg80211:cfg80211_report_wowlan_wakeup`, `dfc:dfc_qmi_tc`, and `msm_pil_event:{pil_event,pil_notif,pil_func}`. Network and scheduler events are broad context rather than primary Wi-Fi bring-up evidence.
- safety: BPF attach, ftrace control writes, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, and partition write were all not executed. Postflight tracefs status confirms no tracefs mount remains.
- interpretation: stock kernel static tracepoints are viable enough for a next observer gate, but not yet enough for BPF attach. V777 should inspect selected tracepoint `format` files and field semantics before any attach proof. Custom OSRC kernel flashing remains paused.
- next: superseded by V777.

### V777. Tracepoint Format Classifier

- plan: `docs/plans/NATIVE_INIT_V777_TRACEPOINT_FORMAT_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V777_TRACEPOINT_FORMAT_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_tracepoint_format_classifier_v777.py`
- evidence:
  - `tmp/wifi/v777-tracepoint-format-classifier/manifest.json`
  - `tmp/wifi/v777-tracepoint-format-classifier/summary.md`
  - `tmp/wifi/v777-tracepoint-format-classifier/native/format-*.txt`
- decision: `v777-tracepoint-format-fields-classified`
- result: live stock-v724 bounded format read PASS. All 5 selected tracepoints have readable `format` files and event-specific fields. `msm_pil_event:pil_event` exposes `event_name,fw_name`; `msm_pil_event:pil_notif` exposes `event_name,code,fw_name`; `msm_pil_event:pil_func` exposes `func_name`; `dfc:dfc_qmi_tc` exposes `dev_name,txq,enable`; `cfg80211:cfg80211_report_wowlan_wakeup` exposes wiphy/wakeup fields.
- safety: BPF attach, ftrace control writes, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, and partition write were all not executed. Tracefs was unmounted after the read window.
- interpretation: `msm_pil_event:pil_notif` is the best V778 target because it is modem/PIL-adjacent and exposes event name, code, and firmware name without requiring Wi-Fi HAL or network actions. `cfg80211` is likely post-wiphy and not useful for the current pre-`wlan0` blocker.
- next: superseded by V778. No modem/Wi-Fi trigger, scan/connect, credential use, or custom kernel flash.

### V778. BPF Attach Feasibility

- plan: `docs/plans/NATIVE_INIT_V778_BPF_ATTACH_FEASIBILITY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V778_BPF_ATTACH_FEASIBILITY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_bpf_attach_feasibility_v778.py`
- evidence:
  - `tmp/wifi/v778-bpf-attach-feasibility/manifest.json`
  - `tmp/wifi/v778-bpf-attach-feasibility/summary.md`
  - `tmp/wifi/v778-bpf-attach-feasibility/native/bpf-loader-surface.txt`
- decision: `v778-custom-bpf-loader-build-needed`
- result: live feasibility classifier PASS. `msm_pil_event:pil_notif` remains the selected target with `event_name,code,fw_name`, but no `bpftool` or `bpftrace` exists on the device. Device sysctls: `perf_event_paranoid=3`, `unprivileged_bpf_disabled=0`. `/sys/kernel/tracing` exists and `/sys/kernel/debug/tracing` is absent.
- host surface: `aarch64-linux-gnu-gcc`, `aarch64-linux-gnu-strip`, and `aarch64-linux-gnu-readelf` are present, and BPF/perf headers are available. Host can build a minimal static aarch64 C helper.
- safety: BPF attach, ftrace control writes, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, and partition write were all not executed.
- interpretation: V778 cannot proceed directly to attach because there is no existing loader. V779 should be build-only: create and statically build a minimal reviewed helper for one target, then audit it before any deploy or attach proof.
- next: superseded by V779.

### V779. BPF Loader Build

- plan: `docs/plans/NATIVE_INIT_V779_BPF_LOADER_BUILD_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V779_BPF_LOADER_BUILD_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_bpf_loader_build_v779.py`
- source: `stage3/linux_init/helpers/a90_bpf_trace_probe.c`
- evidence:
  - `tmp/wifi/v779-bpf-loader-build/manifest.json`
  - `tmp/wifi/v779-bpf-loader-build/summary.md`
  - `tmp/wifi/v779-bpf-loader-build/a90_bpf_trace_probe-aarch64-static`
  - `tmp/wifi/v779-bpf-loader-build/logs/readelf-program.txt`
- decision: `v779-bpf-loader-build-pass`
- result: host build-only PASS. The minimal helper compiles with `aarch64-linux-gnu-gcc -static`, strips successfully, has no `INTERP` program header, preserves marker `a90_bpf_trace_probe v779`, and includes explicit `--check-only` and `--allow-attach` gates. Artifact size is `597920` bytes; sha256 is `9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3`.
- helper contract: default run is check-only and no attach. Attach path is present but gated by `--allow-attach`, targets only `msm_pil_event:pil_notif`, reads the tracepoint id from tracefs, loads a minimal two-instruction tracepoint BPF program, attaches through `perf_event_open`, waits briefly, disables, and closes fds.
- safety: no device command, deploy, BPF attach, ftrace control write, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, or partition write was executed.
- next: V780 should deploy the helper and run only `--check-only` on device, verifying remote hash/version/default no-attach behavior. BPF attach remains blocked until a later separate gate.

### V780. BPF Loader Deploy Check-Only

- plan: `docs/plans/NATIVE_INIT_V780_BPF_LOADER_DEPLOY_CHECKONLY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V780_BPF_LOADER_DEPLOY_CHECKONLY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_bpf_loader_deploy_checkonly_v780.py`
- evidence:
  - `tmp/wifi/v780-bpf-loader-deploy-checkonly/manifest.json`
  - `tmp/wifi/v780-bpf-loader-deploy-checkonly/summary.md`
  - `tmp/wifi/v780-bpf-loader-deploy-checkonly/native/sha-helper.txt`
  - `tmp/wifi/v780-bpf-loader-deploy-checkonly/native/helper-check-only.txt`
  - `tmp/wifi/v780-bpf-loader-deploy-checkonly/native/helper-default.txt`
- decision: `v780-bpf-loader-deploy-checkonly-pass`
- result: serial deploy to `/cache/bin/a90_bpf_trace_probe` PASS. Remote sha256 matched `9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3`. `--check-only` and default no-argument modes both printed marker `a90_bpf_trace_probe v779`, `result=check-only`, and `attach_attempted=0`.
- hard gates: no `--allow-attach`, BPF attach, ftrace control write, Wi-Fi action, scan/connect, credential use, DHCP/routes/external ping, reboot/flash/partition write was executed.
- next: V781 may be planned as a separate bounded idle attach/detach proof for `msm_pil_event:pil_notif`.

### V781. BPF Idle Attach Classifier

- plan: `docs/plans/NATIVE_INIT_V781_BPF_IDLE_ATTACH_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V781_BPF_IDLE_ATTACH_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_bpf_idle_attach_v781.py`
- evidence:
  - `tmp/wifi/v781-bpf-idle-attach/manifest.json`
  - `tmp/wifi/v781-bpf-idle-attach/summary.md`
  - `tmp/wifi/v781-bpf-idle-attach/native/helper-allow-attach.txt`
  - `tmp/wifi/v781-bpf-idle-attach/native/status-after.txt`
- decision: `v781-bpf-idle-attach-detach-pass`
- result: BPF tracepoint attach/detach PASS on stock v724. Tracepoint `msm_pil_event:pil_notif` id was `595`; helper returned `bpf_prog_fd=3`, `result=attach-detach-pass`, `attach_attempted=1`. Tracefs cleanup passed and status after remained `BOOT OK`.
- hard gates: no modem/WLAN trigger, Wi-Fi HAL/service-manager, scan/connect, credential use, DHCP/routes/external ping, module load/unload, sysfs bind/unbind, reboot/flash/partition write was executed.
- next: V782 can use the BPF observer around one bounded modem/WLAN state transition, still without Wi-Fi scan/connect or external networking.
