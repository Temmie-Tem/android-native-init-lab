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
- 현재 예: native build `A90 Linux init 0.9.60`, device build tag `v261`, active execution cycle `v261`, device flash 완료.
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
   - live daemon start 범위를 벗어나는 Wi-Fi scan/connect/link-up/credential/DHCP/routing은 별도 계획과 승인 전까지 blocked

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
