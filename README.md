# Samsung Galaxy A90 5G Native Init Workspace

이 저장소는 `Samsung Galaxy A90 5G (SM-A908N)`의 stock Android Linux kernel 위에서
Android userspace 대신 직접 만든 static `/init`를 실행하고,
그 위에 작은 Linux userspace/runtime을 쌓아 가는 실험 작업 공간입니다.

초기 목표였던 `native Linux rechallenge`의 핵심 진입점 확보 단계는 통과했고,
현재 프로젝트의 중심은 **Android kernel 기반 native init 환경을 안정화하고
서버형 임베디드 Linux 콘솔로 확장하는 것**입니다.

## Current State

- device: `SM-A908N`
- build: `A908NKSU5EWA3`
- kernel: Samsung stock Android kernel `Linux 4.14.190`
- recovery: TWRP 사용 가능
- latest verified build: `A90 Linux init 0.9.60 (v261)`
- official version: `0.9.60`
- build tag: `v261`
- creator: `made by temmie0214`
- latest verified source: `stage3/linux_init/init_v261.c` + `stage3/linux_init/v261/*.inc.c` + `stage3/linux_init/helpers/a90_cpustress.c` + `stage3/linux_init/helpers/a90_rshell.c` + `stage3/linux_init/helpers/a90_longsoak.c` + `stage3/linux_init/a90_config.h` + `stage3/linux_init/a90_util.c/h` + `stage3/linux_init/a90_log.c/h` + `stage3/linux_init/a90_timeline.c/h` + `stage3/linux_init/a90_console.c/h` + `stage3/linux_init/a90_cmdproto.c/h` + `stage3/linux_init/a90_run.c/h` + `stage3/linux_init/a90_service.c/h` + `stage3/linux_init/a90_kms.c/h` + `stage3/linux_init/a90_draw.c/h` + `stage3/linux_init/a90_input.c/h` + `stage3/linux_init/a90_input_cmd.c/h` + `stage3/linux_init/a90_kernelinv.c/h` + `stage3/linux_init/a90_sensormap.c/h` + `stage3/linux_init/a90_pstore.c/h` + `stage3/linux_init/a90_watchdoginv.c/h` + `stage3/linux_init/a90_tracefs.c/h` + `stage3/linux_init/a90_hud.c/h` + `stage3/linux_init/a90_menu.c/h` + `stage3/linux_init/a90_metrics.c/h` + `stage3/linux_init/a90_shell.c/h` + `stage3/linux_init/a90_controller.c/h` + `stage3/linux_init/a90_storage.c/h` + `stage3/linux_init/a90_selftest.c/h` + `stage3/linux_init/a90_usb_gadget.c/h` + `stage3/linux_init/a90_netservice.c/h` + `stage3/linux_init/a90_pid1_guard.c/h` + `stage3/linux_init/a90_reaper.c/h` + `stage3/linux_init/a90_runtime.c/h` + `stage3/linux_init/a90_helper.c/h` + `stage3/linux_init/a90_userland.c/h` + `stage3/linux_init/a90_diag.c/h` + `stage3/linux_init/a90_exposure.c/h` + `stage3/linux_init/a90_wifiinv.c/h` + `stage3/linux_init/a90_wififeas.c/h` + `stage3/linux_init/a90_changelog.c/h` + `stage3/linux_init/a90_longsoak.c/h` + `stage3/linux_init/a90_app_about.c/h` + `stage3/linux_init/a90_app_cpustress.c/h` + `stage3/linux_init/a90_app_displaytest.c/h` + `stage3/linux_init/a90_app_inputmon.c/h` + `stage3/linux_init/a90_app_log.c/h` + `stage3/linux_init/a90_app_network.c/h`
- latest verified boot image: `stage3/boot_linux_v261.img`
- previous verified source-layout baseline: `stage3/linux_init/init_v80.c` + `stage3/linux_init/v80/*.inc.c`
- known-good fallback: `stage3/boot_linux_v48.img`
- local artifact retention: keep `v261` latest, `v159` rollback, and `v48` known-good; older ignored `stage3/boot_linux_v*.img`, `stage3/ramdisk_v*`, and compiled `init_v*` outputs are cleanup candidates
- versioning policy: numeric `0.x.y` identifies native init / boot image builds; `v###` identifies project cycles, host tooling, plans, reports, validation gates, or legacy native build tags; see `docs/operations/VERSIONING_POLICY.md`
- control channel: USB CDC ACM serial (`/dev/ttyGS0` ↔ `/dev/ttyACM0`)
- host bridge: `scripts/revalidation/serial_tcp_bridge.py --port 54321`
- display: custom boot splash 후 상태 HUD/menu 자동 전환
- input: VOL+/VOL-/POWER 단일/더블/롱/조합 입력 layout과 input monitor 확인
- logging: SD 정상 시 `/mnt/sdext/a90/logs/native-init.log`, fallback 시 `/cache/native-init.log`, emergency fallback 시 private `/tmp/a90-native/native-init.log`
- blocking cancel: `waitkey`/`readinput`/`watchhud`/`blindmenu` q/Ctrl-C 취소 확인
- boot timeline: `timeline` 명령과 log replay 확인
- boot selftest: `selftest`/`bootstatus`에서 non-destructive module smoke test `pass=11 warn=1 fail=0` 확인; unverified SD BusyBox is intentionally blocked until manifest SHA-256 is provided
- HUD boot summary: `BOOT OK shell` 표시 확인
- run cancel: `/bin/a90sleep` helper로 q 취소 확인
- storage: `/cache` safe write, ext4 SD workspace `/mnt/sdext/a90`, critical partitions do-not-touch
- storage I/O: v161에서 `/mnt/sdext/a90/test-io` 4K/64K/1M/16M write/read/hash/rename/sync/unlink 검증 완료
- process concurrency: v162에서 helper churn 32/32, tcpctl parallel 18/18, `/bin/a90_cpustress 3 2`, busy gate, zombie/fd snapshot 검증 완료
- CPU/memory/thermal: v163에서 `/bin/a90_cpustress` 5사이클, tmpfs 32MiB hash verify, max CPU 43.1C/GPU 39.4C/BAT 31.1C, status max 32ms 검증 완료
- scheduler latency proxy: v164에서 idle/post-cpustress/post-tmpfs-io 각 20샘플, p99 101-102ms, missed deadline 0 검증 완료
- USB recovery: v165에서 `usbacmreset` 3회와 `a90_usbnet ncm/off` 복구 5/5, max recovery 1.905s, final ACM-only 확인
- network throughput: v166은 host NCM IP assignment에 local sudo가 필요해 deferred 처리, operator-configured NCM에서 재개
- FS exerciser mini: v167에서 `/mnt/sdext/a90/test-fsx` 64 deterministic ops, create/write/truncate/rename/unlink/fsync/verify/cleanup PASS
- kselftest feasibility: v168에서 full kselftest/LTP 실행 없이 safe candidates 4, conditional/unknown 5, blocked 6으로 read-only 분류 완료
- fault/debug feasibility: v169에서 debugfs/tracefs/usbmon/fault-injection/pstore reboot/watchdog/crash 계열을 read-only 분류하고 위험 기능은 opt-in 또는 blocked로 유지
- host test harness: v170에서 `scripts/revalidation/a90harness/` 공용 device/evidence/schema와 `native_test_supervisor.py smoke` 추가, `version/status` smoke PASS
- host observer: v171에서 `native_test_supervisor.py observe`와 `observer.jsonl`/`observer-summary.json` read-only sampler 추가, 15초 실기 관찰 samples=21 failures=0
- host module runner: v172에서 `native_test_supervisor.py run kselftest-feasibility`와 `prepare/run/cleanup/verify` module API 추가, observer 포함 실기 run PASS
- host module ports: v173에서 `cpu-mem-thermal` smoke PASS, `storage-io`는 NCM 미구성 상태를 sudo/rebind 없이 structured SKIP으로 기록
- host USB/NCM modules: v174에서 `usb-recovery` smoke PASS, `ncm-tcp-preflight`는 NCM 미구성 상태를 structured SKIP으로 기록
- host evidence bundle: v175에서 supervisor 공통 `README.md`/`bundle-index.json` finalizer 추가, bundle schema `a90-harness-v175` 검증 PASS
- host long-run supervisor: v176에서 `observe --duration-sec unlimited --max-cycles`와 `heartbeat.json` 추가, bounded unlimited smoke PASS
- host safety gate: v177에서 `list`/`plan`/`run --dry-run`과 `--allow-ncm`/`--allow-usb-rebind` gate 추가, 위험/환경 의존 모듈 기본 차단 확인
- screen menu: 자동 메뉴, 앱 폴더, CPU stress app, nonblocking `screenmenu`, serial `hide`/busy gate 확인
- USB map: ACM-only gadget `04e8:6861` / host `cdc_acm` 기준 문서화
- userland: toybox fallback 실행 확인; v124부터 SD runtime BusyBox는 manifest SHA-256 검증 전에는 preferred helper가 되지 않음
- remote shell: token-authenticated custom TCP shell `a90_rshell` over USB NCM `192.168.7.2:2326` 검증
- service manager: `service list/status/start/stop/enable/disable`로 autohud/tcpctl/adbd/rshell 공통 operator view 검증
- USB reattach: v48에서 ACM rebind 후 serial console 재연결 확인
- USB NCM: persistent composite, device `ncm0`, IPv4 ping, IPv6 link-local ping, host→device netcat 확인
- NCM ops: host interface 자동 탐지, ping, static TCP nettest 양방향 payload 검증 완료
- TCP control: NCM 위에서 token-authenticated `/bin/a90_tcpctl` ping/status/run/shutdown 검증 완료
- TCP wrapper: `tcpctl_host.py smoke`로 launch/client/stop 자동 검증 완료
- TCP soak: v160에서 `tcpctl_host.py soak` 3602.5초/360사이클, tcp/status/run/host ping failures 0 검증 완료
- physical USB reconnect: 실제 케이블 unplug/replug 후 ACM bridge, NCM ping, tcpctl 복구 확인
- serial noise: unsolicited `AT` modem probe line 무시 확인
- boot netservice: `/cache/native-init-netservice` opt-in flag 기반 NCM/tcpctl 부팅 자동 시작 검증 완료
- reconnect: v60 `netservice stop/start` software UDC 재열거 후 NCM/TCP 복구 확인
- HUD metrics: CPU/GPU 온도와 사용률 `%` 표시, CPU stress 검증 확인
- dev nodes: `/dev/null`/`/dev/zero` boot-time char device guard 확인
- app menu: APPS/MONITORING/TOOLS/LOGS/NETWORK/POWER 계층 메뉴, CPU stress, input monitor 확인
- boot splash: TEST 패턴 대신 `A90 NATIVE INIT` custom splash 표시 후 HUD 전환 확인
- splash layout: v65에서 긴 문구/footer 잘림 방지를 위해 안전 여백과 자동 축소 적용
- display test: v77에서 color/font/safe-area/layout preview 4페이지로 분리, `cutoutcal` 펀치홀 보정 추가
- SD workspace: `mountsd [status|ro|rw|off|init]`로 ext4 SD `/mnt/sdext/a90` 운영 검증
- boot storage: v79에서 SD boot health check 후 정상 SD는 main runtime storage, 실패 시 `/cache` fallback
- source layout: v80에서 PID1 source를 기능별 include module로 분리
- base modules: v81에서 `a90_config.h`와 `a90_util.c/h`를 실제 `.c/.h` API로 분리
- log/timeline modules: v82에서 `a90_log.c/h`와 `a90_timeline.c/h`를 실제 `.c/.h` API로 분리
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
- UI app split: v106 `a90_app_about.c/h`, v107 `a90_app_displaytest.c/h`, v108 `a90_app_inputmon.c/h` 분리와 실기 flash/quick soak 검증 완료
- structure audit 2: v109에서 post-v108 구조 감사와 next cleanup boundary 기록 완료
- app controller cleanup: v110에서 auto-menu IPC/state를 `a90_controller.c/h` API로 이동
- extended soak RC: v111에서 10-cycle host soak와 final service/selftest 확인 완료
- USB/NCM service soak: v112에서 opt-in NCM/tcpctl start, host ping/TCP control, ACM rollback 확인 완료
- runtime package layout: v113에서 package-friendly runtime paths와 helper manifest path contract 확인 완료
- helper deployment 2: v114에서 helper manifest/plan/deploy log visibility 확인 완료
- remote shell hardening: v115에서 `rshell audit`, token mode `0600`, invalid-token rejection, NCM smoke/rollback 확인 완료
- diagnostics bundle 2: v116에서 runtime/helper/service/net/rshell evidence와 host `diag_collect.py` device evidence 확장 완료
- PID1 slim roadmap baseline: v117에서 v117-v122 cycle guardrail과 next execution plan을 고정하고 실기 flash/quick soak 검증 완료
- shell metadata API: v118에서 `a90_shell.c/h` command stats/flag formatter와 `cmdmeta [verbose]` read-only inventory 추가
- menu route API: v119에서 `a90_menu_action_opens_app()`로 About/Changelog routing 중복 제거
- command group API: v120에서 command table group metadata와 `cmdgroups [verbose]` inventory 추가
- PID1 guard: v121에서 `a90_pid1_guard.c/h`와 `pid1guard [status|run|verbose]`로 boot/control invariant 점검 추가
- Wi-Fi refresh: v122에서 `wifiinv refresh`/`wififeas refresh`로 v103/v104 baseline 대비 read-only 재평가 완료
- security batch 1: v123에서 tcpctl auth/bind, ramdisk tcpctl helper, dangerous `service` gate, reconnect cleanup fail-closed 적용 완료
- security batch 2: v124에서 runtime helper SHA-256 preference, no-follow storage/log writes, mountsd SD identity gate, tcpctl install rollback 적용 완료
- security batch 3: host tooling에서 cmdv1 retry/framing, ADB shell path quoting, NCM interface pinning, serial bridge identity pinning 적용 완료
- security batch 4: v125에서 diagnostics/log owner-only permissions, private fallback log, HUD log tail opt-in 적용 완료
- security batch 5: host/rootfs tooling에서 legacy root SSH default credential 제거와 safe archive extraction 적용 완료
- security batch 6: v126에서 retained-source compatibility, v84 changelog route, v42 run stdin, input event validation 정리 완료
- security batch 7: v127에서 menu-active busy gate를 deny-by-default allowlist로 강화해 F023 종료
- menu subcommand policy: v128에서 F023 mitigation을 유지하면서 read-only subcommand만 menu-visible 상태에서 허용
- changelog paging: v129에서 long changelog viewport, shared changelog data, ABOUT page navigation 적용
- menu hold/back: v130에서 volume hold-repeat scroll과 VOL+DN physical back shortcut 적용
- menu hold timer: v131에서 EV_KEY repeat 없이 key-down 타이머 기반 연속 스크롤 적용, 실기 UX 정상 확인
- changelog cleanup: v132에서 ABOUT/changelog legacy per-version routes를 제거하고 shared changelog table 단일 경로로 정리
- changelog series: v133에서 ABOUT/changelog를 `0.9.x RECENT`, `0.8.x LEGACY` 같은 version series별 목록으로 분리
- network exposure guardrail: v134에서 `exposure [status|verbose|guard]`, `status`, `bootstatus`, `diag`로 USB/NCM/root-control 노출 경계를 read-only로 확인
- controller policy matrix: v135에서 `policycheck [status|run|verbose]`로 menu-visible/power-page command allow/block 정책을 자체 검증
- structure audit 3: v136에서 post-v135 module ownership, duplicate policy, include residue, PID1 growth hotspot 감사 완료
- validation matrix: v137에서 `native_integrated_validate.py`로 selftest/pid1guard/exposure/policy/service/network/UI gate 통합 검증 완료
- extended soak: v138에서 `native_rc_soak.py` RC soak harness 추가, 실기 flash 후 integrated/quick/RC soak 검증 완료
- auto-HUD controller cleanup: v139에서 `auto_hud_loop()` state/helper 경계를 정리하고 integrated/quick/RC soak 검증 완료
- CPU stress app module: v140에서 `a90_app_cpustress.c/h`로 screen CPU stress lifecycle/renderer를 분리하고 helper 포함 ramdisk로 실기 `cpustress 3 2` 검증 완료
- LOG/NETWORK app modules: v141에서 `a90_app_log.c/h`, `a90_app_network.c/h`로 summary renderer를 분리하고 실기 flash/integrated/quick soak 검증 완료
- cutout calibration app API: v142에서 `a90_app_displaytest.c/h`로 cutout state/feed/draw API를 분리하고 `displaytest safe`/`cutoutcal` 검증 완료
- input command module: v143에서 `a90_input_cmd.c/h`로 `waitkey`/`waitgesture`/`inputlayout` command handler를 분리하고 실기 flash/integrated/quick soak 검증 완료
- input monitor foreground app API: v144에서 `a90_app_inputmon.c/h`로 `inputmonitor` foreground command loop를 분리하고 q cancel/integrated/quick soak 검증 완료
- input cancel validation: v145에서 `native_input_cancel_validate.py`로 `waitkey`/`waitgesture`/`inputmonitor` q cancel 자동 검증을 추가하고 실기 PASS 확인
- long soak foundation: v146에서 `/bin/a90_longsoak` device recorder, `longsoak` shell/service control, host `native_long_soak.py` observation harness 검증 완료
- long soak status: v147에서 sample count/last event 요약을 `status`/`bootstatus`/host summary JSON에 연결
- long soak correlation: v148에서 host/device JSONL export와 correlation report PASS 확인
- long soak supervisor: v149에서 recorder health/stale detection을 `status`/`bootstatus`/`selftest`에 연결
- host disconnect classifier: v150에서 serial bridge/cmdv1/NCM ping/longsoak evidence를 분류하는 host report 추가
- long soak bundle: v151에서 host/device JSONL, correlation, disconnect, live status transcript를 한 디렉터리로 묶는 evidence bundle 추가
- power/thermal trend: v152에서 longsoak device JSONL 기반 battery/power/CPU/GPU/mem/load trend report 추가
- longsoak security: v153에서 device-owned bounded export, helper no-follow log writes, private host bundle output 적용
- kernel inventory: v154에서 `kernelinv [summary|full|paths]`와 host `kernel_inventory_collect.py`로 `/proc/config.gz`, filesystems, mounts, pstore, tracefs, watchdog, cgroup, thermal, power_supply, USB gadget 상태를 read-only 수집
- kernel diagnostics bundle: v155에서 host `kernel_diag_bundle.py`로 kernelinv/diag/longsoak/exposure/wifiinv/wififeas read-only evidence를 private bundle로 수집
- thermal/power sensor map: v156에서 `sensormap [summary|thermal|power|full|paths]`와 host `sensor_map_collect.py`로 thermal zones, cooling devices, power supplies를 read-only 수집
- pstore feasibility: v157에서 `pstore [summary|full|paths]`와 host `pstore_feas_collect.py`로 pstore/ramoops 상태를 read-only 수집
- watchdog feasibility: v158에서 `watchdoginv [summary|full|paths]`와 host `watchdog_feas_collect.py`로 watchdog 상태를 read-only 수집
- tracefs feasibility: v159에서 `tracefs [summary|full|paths]`와 host `tracefs_feas_collect.py`로 tracefs/ftrace 상태를 read-only 수집
- kernel config decoder: v197에서 host `kernel_config_decode.py`로 `/proc/config.gz`를 CONFIG 단위 capability matrix로 분류
- netfilter inventory: v198에서 host `netfilter_inventory.py`로 legacy iptables/conntrack/nftables 가능성을 read-only 판정
- cgroup/PSI inventory: v199에서 host `cgroup_psi_inventory.py`로 cgroup controller, PSI, mount 상태와 service isolation 가능성을 read-only 판정
- debug observability plan: v200에서 host `debug_observability_plan.py`로 tracefs/pstore/debugfs/usbmon opt-in 계획을 read-only 생성
- host evidence helper: v201에서 v197-v200 kernel capability tools의 private/no-follow evidence writer를 `a90harness.evidence`로 통합
- kernel capability summary: v202에서 host `kernel_capability_summary.py`로 config/netfilter/cgroup-PSI/tracefs-pstore/Wi-Fi gate를 한 화면에 통합
- Wi-Fi lifecycle research: v203-v228에서 Android/TWRP/native Wi-Fi evidence, vendor firmware path, ICNSS reprobe safety stop, ICNSS/CNSS lifecycle map, Android service replay model, ICNSS debug/recovery inventory, CNSS daemon dry-run model, native Android-env shim matrix, lifecycle-aware preflight gate v2, host vendor/system ELF library evidence, live vendor-root export, reboot-only recovery policy, Android-env shim dry-run artifacts, exposure/security gate v3, controlled CNSS start-only plan을 수집/구현했고 v228 decision은 `cnss-start-plan-ready`다. 다음은 active scan/connect가 아니라 v229 opt-in start-only runner다
- about app: `APPS / ABOUT`에서 version, changelog 목록/상세, credits 표시
- input layout: `inputlayout`, `waitgesture`, `screenmenu`/`blindmenu` gesture action 확인
- input monitor: `TOOLS / INPUT MONITOR`와 `inputmonitor [events]` raw/gesture trace 확인
- log tail panel: v125부터 `hudlog on` opt-in 상태에서만 HUD/menu 최근 native log 표시
- serial reattach log: v75에서 idle-timeout 성공 로그를 억제해 LOG TAIL noise 감소
- serial noise: v76에서 짧은 `A`/`T`/`ATAT` fragment를 unknown command 없이 무시
- menu gate: v128 기준 메뉴 표시 중 read-only status/query subcommand만 추가 허용하고 `run`/`writefile`/`mountfs`/`mknod*`/service mutation은 계속 차단
- shell protocol: `cmdv1`/`A90P1` framed one-shot result와 `a90ctl.py` host wrapper 검증
- shell protocol: v74 `cmdv1x` length-prefixed argv encoding verified for whitespace args
- changelog UI: v129부터 `ABOUT / CHANGELOG`는 viewport 범위 표시와 selected-row auto-scroll을 사용하고, detail/about 화면은 VOL page navigation을 지원; v132부터 shared changelog table 단일 경로, v133부터 version series 분류를 사용
- menu input UX: v131부터 긴 메뉴에서 커널 repeat 이벤트 없이 VOL hold timer scroll을 사용하고 VOL+DN 조합으로 뒤로가기/숨기기를 수행
- ADB: 보류. 현재 기준 제어 채널은 serial bridge

## Current Objective

현재 메인 목표는 `stock Android kernel 위의 자체 native userspace`를 만드는 것입니다.

구조는 다음과 같습니다.

```text
Samsung bootloader
  -> stock Android Linux kernel
    -> custom static /init (PID 1)
      -> serial shell
      -> display HUD
      -> input/button handling
      -> sensor/sysfs reader
      -> logging/runtime layer
      -> optional BusyBox/network/SSH layer
```

즉 이 프로젝트는 더 이상 단순히 “Linux 진입이 가능한가?”를 확인하는 단계가 아니라,
확보한 진입점을 기반으로 **반복 운용 가능한 최소 Linux 콘솔/서버 환경**을 만드는 단계입니다.

장기 모듈 경계는 아래처럼 잡습니다.

- `init_main`: PID 1 부팅 흐름만 담당
- `util/log/timeline/dev/storage`: boot/runtime 기반 계층
- `console/shell/cmdproto/run`: serial 제어와 명령 실행 계층
- `metrics/kms/draw/hud/input/menu`: 센서 snapshot, 화면, 버튼 입력, device UI 계층
- `usb_gadget/netservice`: USB ACM/NCM, TCP control, 서버형 접근 계층

## What This Is

- Android kernel과 Samsung vendor driver를 그대로 활용하는 native userspace 실험
- boot ramdisk의 `/init`를 교체해 PID 1부터 직접 구성하는 작업
- USB serial, KMS display, input, battery/thermal sysfs를 사용하는 임베디드 콘솔
- 장기적으로 BusyBox, USB network, dropbear SSH 같은 서버형 구성으로 확장할 수 있는 기반

## What This Is Not

- 일반 Debian/Ubuntu/Red Hat 배포판 포팅 완료 상태가 아님
- Android framework, 앱, SurfaceFlinger, Zygote를 복구하는 프로젝트가 아님
- 커널 교체나 커널 드라이버 개발이 현재 목표가 아님
- 카메라, 모뎀, GPU 가속 등 vendor userspace 의존 기능을 즉시 지원하는 환경이 아님

## Near-Term Roadmap

1. shell result/return code를 신뢰 가능하게 정리 — v40 완료
2. `/cache/native-init.log` 기반 boot/command 로그 추가 — v41 완료
3. blocking command 취소 정책 통일 — v42 완료
4. boot readiness timeline 자동 기록 — v43 완료
5. HUD에 boot progress/error 상태 표시 — v44 완료
6. recovery log preservation + `run` cancel helper — v45 완료
7. safe storage/partition map 문서화 — v46 완료
8. 버튼 기반 on-screen menu 초안 구현 — v47 완료
9. USB gadget/device/sysfs map 문서화 — 완료
10. Toybox/static userland build + device validation — 완료
11. USB ACM reattach + NCM probe — v48 완료
12. 상태 HUD/menu TUI 개선 — v52 실기 표시 확인
13. menu-active serial busy gate + flash auto-hide — v53 완료
14. USB NCM persistent link + IPv4/IPv6 ping + host→device netcat 검증 — 완료
15. NCM host setup helper + TCP nettest helper — 완료
16. NCM TCP control helper — 완료
17. TCP control host wrapper — 완료
18. NCM + TCP control 5분 soak — 완료
19. unsolicited `AT` serial noise filter — v59 완료
20. opt-in boot-time NCM/tcpctl netservice — v60 완료
21. netservice stop/start UDC reconnect recovery — v60 완료
22. HUD CPU/GPU usage percent 표시 — v61 완료
23. CPU stress usage gauge + `/dev/null`/`/dev/zero` guard — v62 완료
24. 계층형 앱 메뉴 + CPU stress screen app — v63 완료
25. TEST 부팅 화면을 custom boot splash로 교체 — v64 완료
26. boot splash 잘림 방지 safe layout — v65 완료
27. semantic version + ABOUT/changelog/credits app — v66 완료
28. compact ABOUT typography + per-version changelog detail — v67 완료
29. HUD log tail + expanded changelog history — v68 완료
30. physical-button input gesture layout — v69 완료
31. input monitor app + raw/gesture trace — v70 완료
32. HUD/menu live log tail panel — v71 완료
33. display test screen + framebuffer color fix — v72 완료
34. shell protocol v1 + host wrapper — v73 완료
35. cmdv1x argument encoding — v74 완료
36. idle serial reattach log quieting — v75 완료
37. AT fragment serial noise hardening — v76 완료
38. display test multi-page app + cutout calibration — v77 완료
39. ext4 SD workspace + `mountsd` storage manager — v78 완료
40. boot-time SD health check + `/cache` fallback — v79 완료
41. PID1 source layout split into include modules — v80 완료
42. Config/util true `.c/.h` base module extraction — v81 완료
43. Log/timeline true `.c/.h` API module extraction — v82 완료
44. Console true `.c/.h` API module extraction — v83 완료
45. Cmdproto true `.c/.h` API module extraction — v84 완료
46. Run/service lifecycle `.c/.h` API module extraction — v85 완료
47. KMS/draw true `.c/.h` API module extraction — v86 완료
48. Input true `.c/.h` API module extraction — v87 완료
49. HUD true `.c/.h` API module extraction — v88 완료
50. Menu control true `.c/.h` API module extraction + nonblocking `screenmenu` — v89 완료
51. Metrics true `.c/.h` API module extraction — v90 완료
52. CPU stress external helper process separation — v91 완료
53. Shell/controller metadata and busy policy API extraction — v92 완료
54. Storage state, SD probe, cache fallback API extraction — v93 완료
55. Boot selftest non-destructive module smoke test API — v94 완료
56. Netservice/USB gadget API extraction — v95 완료
57. Structure audit / refactor debt cleanup — v96 완료
58. SD runtime root promotion — v97 완료
59. Helper deployment / package manifest — v98 완료
60. BusyBox static userland evaluation — v99 완료
61. Custom token TCP remote shell over USB NCM — v100 완료
62. Minimal service manager command/view — v101 완료
63. Diagnostics/log bundle command and host collector — v102 완료
64. Wi-Fi read-only inventory — v103 완료
65. Wi-Fi enablement feasibility gate — v104 완료
66. Long-run soak/recovery RC — v105 완료
67. ABOUT/changelog UI app module extraction — v106 완료
68. Displaytest/cutoutcal UI app module extraction — v107 완료
69. Input monitor/layout UI app module extraction — v108 완료
70. Post-v108 structure audit and v110 cleanup boundary — v109 완료
71. App controller auto-menu IPC cleanup — v110 완료
72. Extended soak release-candidate baseline — v111 완료
73. USB/NCM service soak and rollback baseline — v112 완료
74. Runtime package layout and manifest path contract — v113 완료
75. Helper manifest and deploy plan visibility — v114 완료
76. Remote shell hardening audit and invalid-token smoke — v115 완료
77. Diagnostics bundle 2 evidence closure — v116 완료

## Repository Layout

- `docs/`
  현재 문서 인덱스, 프로젝트 상태, v39/v40/v41/v42 상태 보고서, 다음 작업 목록
- `stage3/`
  native init 소스, 빌드 산출물, boot image 실험 파일
- `scripts/`
  serial bridge, console, revalidation helper
- `firmware/`
  stock firmware, patched AP, TWRP 이미지
- `mkbootimg/`
  boot/recovery/vendor_boot 분석과 repack에 쓰는 도구
- `backups/`
  known-good boot/recovery/vbmeta 등 복구 기준점

## Active Documents

전체 문서 목록과 읽는 순서는 `docs/README.md`를 기준으로 한다.

바로 볼 문서:

- `docs/README.md`
- `docs/overview/PROJECT_STATUS.md`
- `docs/overview/PROGRESS_LOG.md`
- `docs/overview/VERSIONING.md`
- `CHANGELOG.md`
- `docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md`
- `docs/operations/CLAUDE_NATIVE_INIT_RUNBOOK.md`
- `docs/plans/NATIVE_INIT_LONG_TERM_ROADMAP_2026-05-03.md`
- `docs/plans/NATIVE_INIT_V96_STRUCTURE_AUDIT_PLAN_2026-05-03.md`
- `docs/plans/NATIVE_INIT_V97_SD_RUNTIME_ROOT_PLAN_2026-05-03.md`
- `docs/plans/NATIVE_INIT_V98_HELPER_DEPLOY_PLAN_2026-05-03.md`
- `docs/plans/NATIVE_INIT_V99_BUSYBOX_USERLAND_PLAN_2026-05-03.md`
- `docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md`
- `docs/plans/NATIVE_INIT_TASK_QUEUE_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V97_SD_RUNTIME_ROOT_2026-05-03.md`
- `docs/reports/NATIVE_INIT_V98_HELPER_DEPLOY_2026-05-03.md`
- `docs/reports/NATIVE_INIT_V96_STRUCTURE_AUDIT_2026-05-03.md`
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
- `docs/reports/NATIVE_INIT_V63_APP_MENU_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V64_BOOT_SPLASH_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V65_SPLASH_SAFE_LAYOUT_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V66_ABOUT_VERSIONING_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V67_CHANGELOG_DETAILS_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V69_INPUT_LAYOUT_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V70_INPUT_MONITOR_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V72_DISPLAY_TEST_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V73_CMDV1_PROTOCOL_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V74_CMDV1X_ARG_ENCODING_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V75_QUIET_IDLE_REATTACH_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V76_AT_FRAGMENT_FILTER_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V77_DISPLAY_TEST_PAGES_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V78_SD_WORKSPACE_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V79_BOOT_STORAGE_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V80_SOURCE_MODULES_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V81_CONFIG_UTIL_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V82_LOG_TIMELINE_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V83_CONSOLE_API_2026-04-29.md`

`docs/plans/NATIVE_LINUX_RECHALLENGE_PLAN.md`와 `docs/plans/REVALIDATION_PLAN.md`는
진입점 확보 이전의 부트체인 재검증 기록으로 보존한다.

## Working Rules

- known-good boot image와 TWRP recovery 복구 경로를 항상 유지한다.
- 한 번에 하나의 boot/init 변수만 바꾼다.
- 새 boot image는 version, source path, SHA256, 실기 관찰 결과를 기록한다.
- 로컬 stage3 산출물은 최신 verified, 직전 rollback, known-good fallback만 보존하고 나머지는 `scripts/revalidation/cleanup_stage3_artifacts.py`로 정리한다.
- USB ACM serial bridge를 기준 제어 채널로 사용한다.
- `/efs`, modem, RPMB, keymaster, keystore, bootloader 계열에는 쓰기 작업을 하지 않는다.
- `/data` 암호화 영역은 명확한 목적과 복구 계획 없이는 건드리지 않는다.
- 파티션은 by-name과 `/sys/class/block/<name>/dev` 기준으로 식별하고 major/minor를 hardcode하지 않는다.
- 로그와 실험 산출물은 우선 `/cache` 또는 repo 문서에 남긴다.
- ADB 안정화는 후순위로 두고, serial/HUD/log/menu 안정화를 먼저 진행한다.

## Safety Note

이 저장소에는 실제 플래시 대상 바이너리와 Samsung 전용 이미지가 포함될 수 있습니다.
실험 전에는 항상 현재 boot/recovery/vbmeta 상태와 복구 가능한 known-good 이미지를
확인한 뒤 진행합니다.
