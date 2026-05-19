# Native Init Task Queue (2026-04-25)

이 문서는 `A90 Linux init 0.9.61 (v319)` verified 이후 바로 실행할 작업 큐다.
큰 방향은 “보이는 부팅 → 복구 가능한 로그 → 단독 조작 → 작은 userland → USB networking” 순서다.

## 버전 표기 규칙

- numeric `MAJOR.MINOR.PATCH`는 native init / boot image의 canonical version이다.
  - 예: `A90 Linux init 0.9.61`, `0.9.61`
  - PID 1, ramdisk helper, boot image, device-visible native behavior가 바뀌고 실기기에 flash할 때만 증가시킨다.
- `v###`는 project execution cycle이다.
  - host tooling, security batch, 계획/보고서, long-soak/mixed-soak gate, documentation-only milestone에도 사용할 수 있다.
  - `v###`가 항상 boot image 또는 device flash를 의미하지 않는다.
- 모든 계획/보고서는 `Native build`, `Cycle label`, `Device flash`, `Host commit`을 분리해 적는다.
- 현재 기준 예:
  - Native build: `A90 Linux init 0.9.61`
  - Device build tag: `v319`
  - Cycle label: `v185` host protocol/broker design
  - Device flash: none
- 상세 규칙: `docs/operations/VERSIONING_POLICY.md`

## 현재 고정 기준점

- latest verified build: `A90 Linux init 0.9.61 (v319)`
- official version: `0.9.61`
- build tag: `v319`
- creator: `made by temmie0214`
- latest verified source: `stage3/linux_init/init_v319.c` + `stage3/linux_init/v319/*.inc.c` + `stage3/linux_init/helpers/a90_cpustress.c` + `stage3/linux_init/helpers/a90_rshell.c` + `stage3/linux_init/helpers/a90_longsoak.c` + `stage3/linux_init/a90_config.h` + `stage3/linux_init/a90_util.c/h` + `stage3/linux_init/a90_log.c/h` + `stage3/linux_init/a90_timeline.c/h` + `stage3/linux_init/a90_console.c/h` + `stage3/linux_init/a90_cmdproto.c/h` + `stage3/linux_init/a90_run.c/h` + `stage3/linux_init/a90_service.c/h` + `stage3/linux_init/a90_kms.c/h` + `stage3/linux_init/a90_draw.c/h` + `stage3/linux_init/a90_input.c/h` + `stage3/linux_init/a90_input_cmd.c/h` + `stage3/linux_init/a90_kernelinv.c/h` + `stage3/linux_init/a90_sensormap.c/h` + `stage3/linux_init/a90_pstore.c/h` + `stage3/linux_init/a90_watchdoginv.c/h` + `stage3/linux_init/a90_tracefs.c/h` + `stage3/linux_init/a90_hud.c/h` + `stage3/linux_init/a90_menu.c/h` + `stage3/linux_init/a90_metrics.c/h` + `stage3/linux_init/a90_shell.c/h` + `stage3/linux_init/a90_controller.c/h` + `stage3/linux_init/a90_storage.c/h` + `stage3/linux_init/a90_selftest.c/h` + `stage3/linux_init/a90_usb_gadget.c/h` + `stage3/linux_init/a90_netservice.c/h` + `stage3/linux_init/a90_pid1_guard.c/h` + `stage3/linux_init/a90_reaper.c/h` + `stage3/linux_init/a90_runtime.c/h` + `stage3/linux_init/a90_helper.c/h` + `stage3/linux_init/a90_userland.c/h` + `stage3/linux_init/a90_diag.c/h` + `stage3/linux_init/a90_exposure.c/h` + `stage3/linux_init/a90_wifiinv.c/h` + `stage3/linux_init/a90_wififeas.c/h` + `stage3/linux_init/a90_changelog.c/h` + `stage3/linux_init/a90_longsoak.c/h` + `stage3/linux_init/a90_app_about.c/h` + `stage3/linux_init/a90_app_cpustress.c/h` + `stage3/linux_init/a90_app_displaytest.c/h` + `stage3/linux_init/a90_app_inputmon.c/h` + `stage3/linux_init/a90_app_log.c/h` + `stage3/linux_init/a90_app_network.c/h`
- latest verified boot image: `stage3/boot_linux_v319.img`
- previous verified source-layout baseline: `stage3/linux_init/init_v80.c` + `stage3/linux_init/v80/*.inc.c`
- known-good fallback: `stage3/boot_linux_v48.img`
- local artifact retention: `v319` latest, `v261` rollback, `v48` known-good만 보존하고 나머지 ignored stage3 산출물은 정리 가능
- control channel: USB ACM serial bridge
- log: SD 정상 시 `/mnt/sdext/a90/logs/native-init.log`, fallback 시 `/cache/native-init.log`, emergency fallback 시 private `/tmp/a90-native/native-init.log`
- verified:
  - shell result/errno/duration
  - boot/command file log
  - blocking command q/Ctrl-C cancel
  - boot readiness timeline
  - HUD boot summary
  - `run` cancel helper
  - recovery log preservation
  - safe storage/partition map
  - screen menu draft
  - screen menu polished TUI
  - menu-active serial busy gate
  - USB gadget map
  - USB reattach / NCM probe
  - USB NCM persistent link + IPv6 netcat
  - KMS HUD
  - VOL+/VOL-/POWER input
  - hierarchical app menu
  - custom boot splash
  - ABOUT/versioning/changelog metadata
  - compact ABOUT/changelog detail screens
  - long soak device recorder and host observation harness
  - long soak status summary in `status`/`bootstatus` and host summary JSON
  - long soak host/device JSONL correlation report
  - long soak recorder health/stale detection in status/selftest
  - host disconnect classification report for serial/NCM/control path triage
  - long soak evidence bundle with live read-only transcripts
  - power/thermal/memory/load trend analysis from device JSONL
  - HUD log tail (`hudlog on` opt-in)
  - physical-button input gesture layout
  - input monitor app / raw gesture trace
  - HUD/menu live log tail panel
  - display test screen for color/font/wrap/grid/cutout checks
  - cmdv1/A90P1 shell protocol + a90ctl host wrapper
  - config/util/log/timeline compiled API modules
  - console fd/attach/readline/cancel compiled API module
  - cmdproto frame/decode compiled API module
  - run/service lifecycle compiled API modules
  - KMS/draw framebuffer compiled API modules
  - input/HUD/menu/metrics compiled API modules
  - CPU stress external helper process separation
  - shell/controller metadata and busy policy compiled API modules
  - storage/selftest/USB/netservice/runtime compiled API modules
  - PID1 guard invariant checks and `pid1guard` command
  - Wi-Fi read-only refresh against v103/v104 baseline
  - Security Batch 1 tcpctl auth/bind, ramdisk tcpctl helper, dangerous service gate
  - Security Batch 2 helper hash preference, no-follow storage/log writes, mountsd SD identity gate
  - Security Batch 3 host tooling trust boundary hardening
  - Security Batch 4 diagnostics/log owner-only permissions, private fallback log, HUD log tail opt-in
  - Security Batch 5 legacy root SSH credential removal and safe archive extraction
  - Security Batch 6 retained-source reliability and strict input event validation
  - Security Batch 7 menu busy gate deny-by-default allowlist
  - v128 menu-visible read-only subcommand policy
  - v129 changelog viewport/shared data/about paging
  - v130 menu hold-repeat scroll and physical combo back
  - v131 timer-based hold scroll without EV_KEY repeat dependency and physical UX confirmation
  - v132 changelog cleanup with shared changelog table single route and quick soak
  - v133 changelog series menus with 0.9.x/0.8.x grouped navigation and quick soak
  - v134 network exposure guardrail with read-only `exposure`/`diag`/`status` summaries
  - v135 policy matrix with `policycheck` menu/power command allow/block validation
  - v136 structure audit 3 with module ownership/hotspot review
  - v137 integrated validation matrix with safety/service/network/UI gate
  - v138 release-candidate extended soak with reusable `native_rc_soak.py`

### V159. Tracefs/Ftrace Feasibility — DONE

- 계획: `docs/plans/NATIVE_INIT_V159_TRACEFS_FEASIBILITY_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V159_TRACEFS_FEASIBILITY_2026-05-08.md`
- build: `A90 Linux init 0.9.59 (v159)`
- 의도: tracefs/debugfs support, mount state, ftrace control file readability를 read-only로 수집
- 검증: real-device flash PASS, `tracefs full` PASS, `tracefs_feas_collect.py` PASS, integrated PASS, static checks PASS
- 다음 실행 항목: v160 NCM/TCP Stability

### V160. NCM/TCP Stability — DONE

- 계획: `docs/plans/NATIVE_INIT_V160_NCM_TCP_STABILITY_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V160_NCM_TCP_STABILITY_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: USB NCM + token-authenticated `a90_tcpctl` 경로를 1시간 반복 검증
- 검증: NCM setup PASS, tcpctl soak 3602.5s/360 cycles PASS, tcp ping 360/360, status 120/120, run 120/120, host ping 360/360, failures 0
- longsoak correlation: PASS, host failures 0, device samples 428, sequence/time/uptime monotonic
- 다음 실행 항목: v161 Storage I/O Integrity

### V161. Storage I/O Integrity — DONE

- 계획: `docs/plans/NATIVE_INIT_V161_STORAGE_IO_INTEGRITY_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V161_STORAGE_IO_INTEGRITY_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: SD runtime root write/read/hash/rename/sync/unlink 검증
- 검증: smoke 4K/64K PASS, full 4K/64K/1M/16M PASS, cleanup PASS
- post-test: `storage`, `mountsd status`, `selftest verbose`, `longsoak status verbose` PASS
- 다음 실행 항목: v162 Process Concurrency

### V162. Process/Concurrency Stability — DONE

- 계획: `docs/plans/NATIVE_INIT_V162_PROCESS_CONCURRENCY_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V162_PROCESS_CONCURRENCY_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: PID1 run/service/reap 경계와 tcpctl multi-client path 동시성 검증
- 검증: smoke PASS, full helper churn 32/32, tcpctl parallel ops 18/18, `/bin/a90_cpustress 3 2` PASS
- process snapshot: pid count 393→392, PID1 fd 5→5, global zombies 0, controlled zombies 0
- busy gate: menu visible 상태에서 unsafe `run` blocked `busy/-16`, `policycheck run` PASS
- 다음 실행 항목: v163 CPU/Mem/Thermal

### V163. CPU/Memory/Thermal Stability — DONE

- 계획: `docs/plans/NATIVE_INIT_V163_CPU_MEM_THERMAL_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V163_CPU_MEM_THERMAL_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: bounded CPU stress, tmpfs memory verify, thermal/power/status trend 검증
- 검증: smoke PASS, full `/bin/a90_cpustress` 5 cycles PASS, tmpfs 32MiB SHA-256 verify PASS
- thermal/power: max CPU 43.1C, GPU 39.4C, battery 31.1C, power 0.4W
- responsiveness: status samples 6/6, max status duration 32ms, longsoak health ok, controlled zombies 0
- 다음 실행 항목: v164 Scheduler/Latency Baseline

### V164. Scheduler/Latency Baseline — DONE

- 계획: `docs/plans/NATIVE_INIT_V164_SCHED_LATENCY_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V164_SCHED_LATENCY_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: PID1 run/cmdv1 latency proxy 기준선 수집
- 검증: smoke PASS, full idle/post-cpustress/post-tmpfs-io 각 20 samples PASS
- latency: idle p99 102ms, post-cpustress p99 102ms, post-tmpfs-io p99 101ms, missed deadline 0
- 한계: true `clock_nanosleep`/cyclictest helper가 아니라 현재 run-loop regression baseline
- 다음 실행 항목: v165 USB Recovery Stability

### V165. USB Recovery Stability — DONE

- 계획: `docs/plans/NATIVE_INIT_V165_USB_RECOVERY_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V165_USB_RECOVERY_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: software USB rebind 후 ACM bridge recovery와 NCM on/off rollback 검증
- 검증: smoke PASS, full `usbacmreset` 3회 + `a90_usbnet ncm/off` PASS
- recovery: recovered 5/5, max recovery 1.905s, NCM function present after NCM step, final ACM-only
- supplemental: 1-cycle USB recovery 중 longsoak before/after health=ok running=yes 확인
- final checks: `version` PASS, `selftest verbose` PASS
- 다음 실행 항목: v166 Network Throughput / Impairment

### V166. Network Throughput / Impairment — DEFERRED

- 계획: `docs/plans/NATIVE_INIT_V166_NETWORK_THROUGHPUT_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V166_NETWORK_THROUGHPUT_DEFERRED_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: USB NCM throughput/checksum/impairment baseline
- deferral: host NCM `192.168.7.1/24` assignment requires local sudo; current non-interactive run cannot configure host network
- evidence: final v165 state is ACM-only, `netservice: ncm0=absent tcpctl=stopped`, no host `192.168.7.1/24` interface present
- resume: operator-configured NCM 후 throughput report 작성
- 다음 실행 항목: v167 FS Exerciser Mini

### V167. Filesystem Exerciser Mini — DONE

- 계획: `docs/plans/NATIVE_INIT_V167_FS_EXERCISER_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V167_FS_EXERCISER_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: `/mnt/sdext/a90/test-fsx` 내부 deterministic filesystem operation sequence 검증
- 검증: smoke 10 ops PASS, full 64 ops PASS, cleanup PASS
- operation counts: create 12, write 11, truncate 7, rename 6, unlink 10, fsync 9, verify 9, final-verify 2
- failed records: 0
- 다음 실행 항목: v168 Kernel Selftest Feasibility

### V168. Kernel Selftest Feasibility — DONE

- 계획: `docs/plans/NATIVE_INIT_V168_KSELFTEST_FEASIBILITY_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V168_KSELFTEST_FEASIBILITY_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: full kselftest/LTP 실행 전 native init에서 안전하게 차용 가능한 userspace subset 분류
- 검증: mandatory inventory 8/8 PASS, optional inventory 10/10 PASS, mutation_performed=False
- 분류: safe candidates 4, conditional/unknown 5, blocked 6
- evidence: `tmp/soak/kselftest-feasibility/v168-kselftest-20260508T171140Z/`
- 다음 실행 항목: v169 Fault/Debug Feasibility

### V169. Fault/Debug Feasibility — DONE

- 계획: `docs/plans/NATIVE_INIT_V169_FAULT_DEBUG_FEASIBILITY_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V169_FAULT_DEBUG_FEASIBILITY_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: fault/debug/trace/usbmon/pstore reboot 계열을 실제 실행 전 read-only로 분류
- 검증: mandatory inventory 8/8 PASS, optional absence evidence 7건 기록, mutation_performed=False
- 분류: debugfs read-only-only, tracefs active mode read-only-only, usbmon unavailable, pstore reboot opt-in-safe-candidate, fault/LKDTM/watchdog/raw-device blocked
- evidence: `tmp/soak/fault-debug-feasibility/v169-fault-debug-20260508T171514Z/`
- 다음 실행 항목: v170 Harness Foundation

### V170. Harness Foundation — DONE

- 로드맵: `docs/plans/NATIVE_INIT_V170_V177_HARNESS_ROADMAP_2026-05-09.md`
- 계획: `docs/plans/NATIVE_INIT_V170_HARNESS_FOUNDATION_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V170_HARNESS_FOUNDATION_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: host-side 공용 device client, private evidence writer, result schema, supervisor smoke CLI 추가
- 검증: `native_test_supervisor.py smoke` PASS, `version/status` rc=0 status=ok, failed_checks=0, failed_commands=0
- evidence: `tmp/soak/harness/v170-smoke-20260508T173932Z/`
- 다음 실행 항목: v171 Observer API

### V171. Observer API — DONE

- 계획: `docs/plans/NATIVE_INIT_V171_OBSERVER_API_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V171_OBSERVER_API_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: 공용 read-only observer와 `native_test_supervisor.py observe` 추가
- 검증: 15초/5초 interval observer PASS, cycles=3, samples=21, failures=0, version_matches=True
- evidence: `tmp/soak/harness/v171-observer-20260508T174309Z/`
- 다음 실행 항목: v172 Module Runner

### V172. Module Runner — DONE

- 계획: `docs/plans/NATIVE_INIT_V172_MODULE_RUNNER_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V172_MODULE_RUNNER_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: `prepare/run/cleanup/verify` module interface와 supervisor runner 고정
- 검증: `native_test_supervisor.py run kselftest-feasibility --observer-duration-sec 5` PASS
- 결과: module steps prepare/run/cleanup/verify 모두 PASS, observer samples=14 failures=0
- evidence: `tmp/soak/harness/v172-kselftest-feasibility-20260508T175009Z/`
- 다음 실행 항목: v173 Storage/CPU Module Port

### V173. Storage/CPU Module Port — DONE

- 계획: `docs/plans/NATIVE_INIT_V173_STORAGE_CPU_MODULES_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V173_STORAGE_CPU_MODULES_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: 기존 storage/CPU validator를 supervisor module wrapper로 포팅
- 검증: `cpu-mem-thermal --profile smoke --observer-duration-sec 5` PASS
- storage 상태: host NCM `192.168.7.2` 미도달로 `storage-io` structured SKIP, sudo/rebind/host network mutation 없음
- evidence: `tmp/soak/harness/v173-cpu-mem-thermal-20260508T175358Z/`
- evidence: `tmp/soak/harness/v173-storage-io-20260508T175421Z/`
- 다음 실행 항목: v174 USB/NCM Module Port

### V174. USB/NCM Module Port — DONE

- 계획: `docs/plans/NATIVE_INIT_V174_USB_NCM_MODULES_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V174_USB_NCM_MODULES_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: USB recovery와 NCM/TCP validator를 supervisor module wrapper로 포팅
- 검증: `usb-recovery --profile smoke` PASS, max recovery 1.904s
- NCM/TCP 상태: host NCM `192.168.7.2` 미도달로 structured SKIP, sudo/rebind/host network mutation 없음
- evidence: `tmp/soak/harness/v174-usb-recovery-20260508T175639Z/`
- evidence: `tmp/soak/harness/v174-ncm-tcp-preflight-20260508T175654Z/`
- 다음 실행 항목: v175 Unified Evidence Bundle

### V175. Unified Evidence Bundle — DONE

- 계획: `docs/plans/NATIVE_INIT_V175_UNIFIED_EVIDENCE_BUNDLE_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V175_UNIFIED_EVIDENCE_BUNDLE_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: supervisor run output layout을 `manifest.json`/`summary.md`/`README.md`/`bundle-index.json`로 표준화
- 검증: `native_test_supervisor.py run kselftest-feasibility --observer-duration-sec 5 --run-dir tmp/soak/harness/v175-bundle-20260508T175913Z` PASS
- 결과: bundle schema `a90-harness-v175`, indexed files=27, directory 0700, key files 0600
- evidence: `tmp/soak/harness/v175-bundle-20260508T175913Z/`
- 다음 실행 항목: v176 Long-Run Supervisor

### V176. Long-Run Supervisor — DONE

- 계획: `docs/plans/NATIVE_INIT_V176_LONG_RUN_SUPERVISOR_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V176_LONG_RUN_SUPERVISOR_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: observer를 bounded/unlimited 장시간 실행과 partial-report-safe evidence 구조로 확장
- 검증: `observe --duration-sec unlimited --max-cycles 2 --interval 2` PASS
- 결과: cycles=2, samples=14, failures=0, stop_reason=max-cycles, heartbeat 기록
- evidence: `tmp/soak/harness/v176-long-run-20260508T180122Z/`
- 다음 실행 항목: v177 Safety Gate / Dry-Run Policy

### V177. Safety Gate / Dry-Run Policy — DONE

- 계획: `docs/plans/NATIVE_INIT_V177_SAFETY_GATE_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V177_SAFETY_GATE_2026-05-09.md`
- baseline build: `A90 Linux init 0.9.59 (v159)`
- 의도: 위험/환경 의존 module 실행 전 `list`/`plan`/`run --dry-run`과 explicit allow gate 추가
- 검증: `list`, `plan usb-recovery`, `run usb-recovery --dry-run`, `run usb-recovery` rc=2 block, `run kselftest-feasibility` PASS
- gate: NCM modules require `--allow-ncm`, USB rebind modules require `--allow-usb-rebind --assume-yes`
- evidence: `tmp/soak/harness/v177-gate-allowed-20260508T180349Z/`
- 다음 실행 항목: v184 24h+ Serverization Readiness Gate

### V170-V177. Host Harness Completion Audit — DONE

- 산출: `docs/reports/NATIVE_INIT_V170_V177_COMPLETION_AUDIT_2026-05-09.md`
- 의도: v170~v177 전체 루프의 계획/구현/검증/보고서/커밋/evidence를 실제 상태 기준으로 감사
- 검증: plan/report pair 모두 존재, evidence manifest 모두 pass, static validation PASS, v177 gate block rc=2 확인
- deferral: storage/NCM full PASS는 host NCM 미구성으로 structured SKIP 및 explicit gate로 문서화
- 다음 실행 항목: v184 24h+ Serverization Readiness Gate


### V178. Post-Security Harness Baseline — PASS

- 계획: `docs/plans/NATIVE_INIT_V178_POST_SECURITY_BASELINE_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V178_POST_SECURITY_BASELINE_2026-05-09.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v178은 host-harness/report label이며 별도 `init_v178.c`/`boot_linux_v178.img` 없음
- 의도: F038-F044 보안 패치 이후 host harness가 다시 신뢰 가능한 evidence producer인지 검증
- 검증: live v159 verify-only PASS, status/bootstatus/selftest/storage/exposure/policycheck PASS, observer smoke PASS, FS exerciser smoke PASS
- NCM: 현재 ACM-only/netservice disabled 환경이라 `ncm-tcp-preflight`는 structured SKIP 처리 PASS
- evidence: `tmp/soak/harness/v178-post-security-observe-20260509-042523/`, `tmp/soak/fs-exerciser/v178-fsx-smoke-20260509-042552/`, `tmp/soak/harness/v178-ncm-preflight-20260509-042552/`
- 다음 실행 항목: v184 24h+ Serverization Readiness Gate

### V179. Mixed Soak Scheduler Foundation — PASS

- 계획: `docs/plans/NATIVE_INIT_V179_MIXED_SOAK_SCHEDULER_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V179_MIXED_SOAK_SCHEDULER_2026-05-09.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v179는 host-harness scheduler foundation이며 별도 native-init boot image 없음
- 구현: `scripts/revalidation/a90harness/scheduler.py`, `native_test_supervisor.py mixed-soak`
- 검증: Python compile PASS, `git diff --check` PASS, dry-run PASS, real-device 30s smoke PASS, deterministic seed PASS
- evidence: `tmp/soak/harness/v179-dry-run-20260509-044249/`, `tmp/soak/harness/v179-smoke-20260509-044258/`
- 다음 실행 항목: v184 24h+ Serverization Readiness Gate

### V180. CPU/Memory Workload Profiles — PASS

- 계획: `docs/plans/NATIVE_INIT_V180_CPU_MEMORY_PROFILES_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V180_CPU_MEMORY_PROFILES_2026-05-09.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v180은 host-harness workload profile이며 별도 native-init boot image 없음
- 구현: `scripts/revalidation/a90harness/modules/cpu_memory_profiles.py`, mixed-soak default CPU workload 갱신
- 검증: Python compile PASS, `git diff --check` PASS, `run cpu-memory-profiles --profile quick` PASS, `mixed-soak` 30s smoke PASS
- evidence: `tmp/soak/harness/v180-cpumem-quick-20260509-045117/`, `tmp/soak/harness/v180-mixed-smoke-20260509-045226/`
- 다음 실행 항목: v184 24h+ Serverization Readiness Gate

### V181. NCM/TCP + Storage Workload Integration — PASS

- 계획: `docs/plans/NATIVE_INIT_V181_NCM_TCP_STORAGE_INTEGRATION_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V181_NCM_TCP_STORAGE_PREFLIGHT_2026-05-09.md`, `docs/reports/NATIVE_INIT_V181_NCM_TCP_STORAGE_FULL_2026-05-09.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v181은 host-harness workload integration이며 별도 native-init boot image 없음
- 구현: `DeviceClient.exclusive()`, `external_bridge_client`, `external-bridge` schedule lock
- 검증: Python compile PASS, `git diff --check` PASS, `--allow-ncm` dry-run PASS, ACM-only mixed smoke PASS, full NCM/TCP + storage mixed run PASS
- evidence: `tmp/soak/harness/v181-ncm-full-20260509-052830/`
- full result: workloads=3 pass=3 skipped=0 blocked=0 observer_failures=0 failure_classifications=0
- note: v159에는 `/bin/a90_tcpctl`이 없어 harness가 검증된 `/cache/bin/a90_tcpctl` fallback을 사용했다.
- 다음 실행 항목: v184 24h+ Serverization Readiness Gate

### V182. Failure Classifier + Recovery Policy — PASS

- 계획: `docs/plans/NATIVE_INIT_V182_FAILURE_CLASSIFIER_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V182_FAILURE_CLASSIFIER_2026-05-09.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v182는 host-harness classifier이며 별도 native-init boot image 없음
- 구현: `scripts/revalidation/a90harness/failure.py`, `failure-classification.json`, interrupt partial bundle handling
- 검증: Python compile PASS, `git diff --check` PASS, `policy-blocked` PASS, `env-ncm-missing` PASS, interrupt bundle PASS
- evidence: `tmp/soak/harness/v182-policy-blocked-20260509-050457/`, `tmp/soak/harness/v182-ncm-missing-20260509-050519/`, `tmp/soak/harness/v182-interrupt-20260509-050613/`
- 다음 실행 항목: v184 24h+ Serverization Readiness Gate

### V183. 8h Pilot Mixed Soak — PASS

- 계획: `docs/plans/NATIVE_INIT_V183_8H_PILOT_MIXED_SOAK_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V183_8H_PILOT_MIXED_SOAK_2026-05-10.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v183은 host-harness 8h validation gate이며 별도 native-init boot image 없음
- precondition: v181 full NCM/TCP + storage PASS 또는 최소 host NCM ping/TCP control 복구
- command: `native_test_supervisor.py mixed-soak --duration-sec 28800 --observer-interval 30 --profile balanced --workload-profile quick --seed 183 --allow-ncm --stop-on-failure`
- 검증: 8h complete, workloads=3 pass=3 skipped=0 blocked=0, observer_failures=0, failure_classifications=0
- evidence: `tmp/soak/harness/v183-8h-pilot-20260509-230134/`
- 다음 실행 항목: v184 24h+ Serverization Readiness Gate

### V184. 24h+ Serverization Readiness Gate — PASS

- 계획: `docs/plans/NATIVE_INIT_V184_24H_SERVERIZATION_READINESS_PLAN_2026-05-09.md`
- 산출: `docs/reports/NATIVE_INIT_V184_24H_SERVERIZATION_READINESS_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v184는 host-harness 24h+ validation gate이며 별도 native-init boot image 없음
- precondition: v181 full NCM/TCP + storage PASS, v183 8h pilot PASS
- command: `native_test_supervisor.py mixed-soak --duration-sec 86400 --observer-interval 30 --profile balanced --workload-profile quick --seed 184 --allow-ncm --stop-on-failure`
- 검증: 24h+ complete, workloads=3 pass=3 skipped=0 blocked=0, observer_failures=0, failure_classifications=0
- decision: `GO`
- evidence: `tmp/soak/harness/v184-24h-readiness-20260510-095036/`
- 다음 실행 항목: v185 Communication Broker Protocol Plan

### V185. Communication Broker Protocol Plan — PLANNED

- 계획: `docs/plans/NATIVE_INIT_V185_COMMUNICATION_BROKER_PLAN_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v185는 host protocol/broker 설계 cycle이며 별도 native-init boot image 없음
- 의도: Wi-Fi/server-style exposure 전에 USB ACM serial bridge, `cmdv1`/`A90P1`, NCM `tcpctl`, rshell 경계를 하나의 broker 정책으로 정리한다.
- 핵심 설계:
  - host-local `A90B1` request/response schema
  - broker가 serial/NCM transport의 single owner가 됨
  - command class: observe, operator-action, exclusive, rebind/destructive
  - request id, client id, timeout, cancel, backend, audit JSONL
  - ACM direct path는 rescue로 유지하고 public/multi-client root shell로 확장하지 않음
- 다음 실행 항목: v186 host broker skeleton live ACM smoke

### V186. Host Broker Skeleton — STARTED

- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v186은 host-side broker skeleton이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/a90_broker.py`
  - `A90B1` JSON request/response
  - private Unix socket endpoint
  - single worker queue
  - backend `acm-cmdv1` wrapper around `run_cmdv1_command()`
  - backend `fake` selftest/smoke
  - rebind/destructive command broker block
  - private audit JSONL
- 검증:
  - Python compile PASS
  - fake backend selftest PASS
  - fake Unix socket serve/call smoke PASS
  - live ACM `version`/`status` through broker PASS
  - concurrent read-only clients `version`/`status`/`bootstatus` through broker PASS
  - live ACM `selftest verbose` through broker PASS
  - live backend rebind/destructive block `reboot` PASS
- 남은 검증:
  - broker audit bundle retention/reporting
- 다음 실행 항목: v188 broker audit/reporting or NCM/tcpctl backend selection

### V188. Broker Audit Reporting — PASS

- 보고서: `docs/reports/NATIVE_INIT_V188_BROKER_AUDIT_REPORTING_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v188은 host-side broker evidence/reporting cycle이며 별도 native-init boot image 없음
- 구현:
  - `a90_broker.py report`
  - audit JSONL integrity summary
  - request/result counts, status/class/backend/command counts, duration summary
  - redacted audit records output
  - report output via private/no-follow evidence helpers
  - audit `accept`/`dispatch` argv redaction
- 검증:
  - Python compile PASS
  - `a90_broker.py selftest` PASS with audit integrity check
  - fake backend serve/call/report PASS
  - live ACM broker audit report PASS
  - broker-backed supervisor smoke + audit report PASS
  - evidence: `tmp/a90-v188-broker-20260511-202018/`
- 남은 검증:
  - 없음
- 다음 실행 항목: v189 broker concurrent smoke script

### V189. Broker Concurrent Smoke — PASS

- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v189는 host-side broker concurrency validation이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/a90_broker_concurrent_smoke.py`
  - broker subprocess 자동 실행 또는 기존 broker socket 사용
  - concurrent host client request fan-out
  - read-only command response/id/version validation
  - blocked `reboot` request가 `operator-required`로 남는지 확인
  - private summary/response/audit evidence 생성
- 검증:
  - Python compile PASS
  - fake backend concurrent smoke PASS: clients=4 rounds=3 requests=16 blocked_expected=4
  - live ACM backend concurrent smoke PASS: clients=4 rounds=2 requests=12 blocked_expected=4
  - live audit integrity PASS: accepted=12 dispatched=12 results=12 non_ok=4
  - evidence:
    - `tmp/a90-v189-fake-20260511-204752/`
    - `tmp/a90-v189-live-20260511-204803/`
- 보고서: `docs/reports/NATIVE_INIT_V189_BROKER_CONCURRENT_SMOKE_2026-05-11.md`
- 남은 검증:
  - 없음
- 다음 실행 항목: v190 broker mixed-soak gate

### V190. Broker Mixed-Soak Gate — PASS

- 계획: `docs/plans/NATIVE_INIT_V190_BROKER_MIXED_SOAK_GATE_PLAN_2026-05-11.md`
- 보고서: `docs/reports/NATIVE_INIT_V190_BROKER_MIXED_SOAK_GATE_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v190은 host-side broker/supervisor gate이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/a90_broker_mixed_soak_gate.py`
  - broker subprocess 자동 실행
  - `native_test_supervisor.py mixed-soak --device-backend broker` 실행
  - supervisor manifest와 broker audit summary를 함께 판정
  - 기본 workload는 `cpu-memory-profiles`로 observer/workload command 모두 broker를 경유
- 검증:
  - Python compile PASS
  - dry-run PASS: `tmp/a90-v190-dry-fixed-20260511-212931/`
  - live ACM broker mixed-soak PASS: `tmp/a90-v190-live-fixed-20260511-212947/`
  - supervisor PASS: workload_count=1 pass_count=1 fail_count=0 observer_failures=0 samples=28
  - broker audit PASS: accepted=42 dispatched=42 results=42 non_ok=0 status=ok
- 남은 검증:
  - 없음
- 다음 실행 항목: v191 NCM/tcpctl broker backend

### V191. NCM/tcpctl Broker Backend — PASS

- 계획: `docs/plans/NATIVE_INIT_V191_NCM_TCPCTL_BROKER_BACKEND_PLAN_2026-05-11.md`
- 보고서: `docs/reports/NATIVE_INIT_V191_NCM_TCPCTL_BROKER_BACKEND_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v191은 host-side broker backend 확장이며 별도 native-init boot image 없음
- 구현:
  - `a90_broker.py serve --backend ncm-tcpctl`
  - `run /absolute/path ...` 요청은 NCM `a90_tcpctl`로 전달
  - native shell built-in은 ACM `cmdv1` fallback 유지
  - broker audit result에 실제 실행 backend를 기록하도록 backend result 모델 추가
  - `a90_broker_concurrent_smoke.py`가 `ncm-tcpctl` backend 옵션을 지원
- 검증:
  - Python compile PASS
  - `a90_broker.py selftest` PASS
  - fake/acm regression PASS
  - NCM host ping PASS after NetworkManager `a90-ncm-v191` activation
  - `/cache/bin/a90_tcpctl` listener with `max_clients=0` PASS
  - NCM broker smoke PASS: `tmp/a90-v191-ncm-smoke-fixed-20260511-213909/`
  - NCM audit PASS: accepted=12 dispatched=12 results=12 non_ok=0 backend=`ncm-tcpctl`
  - ACM fallback PASS: `tmp/a90-v191-ncm-fallback-20260511-213933/`, backend=`acm-cmdv1`
- note:
  - v159에는 `/bin/a90_tcpctl`이 없어서 live validation은 검증된 `/cache/bin/a90_tcpctl` helper를 사용했다.
  - 첫 NCM attempt는 listener `max_clients=8`로 인해 8회 처리 후 종료되어 실패했고, `max_clients=0`으로 재실행해 PASS했다.
- 남은 검증:
  - 없음
- 다음 실행 항목: v192 Broker Failure/Recovery Tests

### V192. Broker Failure/Recovery Tests — PASS

- 계획: `docs/plans/NATIVE_INIT_V192_BROKER_RECOVERY_TESTS_PLAN_2026-05-11.md`
- 보고서: `docs/reports/NATIVE_INIT_V192_BROKER_RECOVERY_TESTS_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v192는 host-side broker failure/recovery validation이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/a90_broker_recovery_tests.py`
  - fake backend recovery tests:
    - blocked command audit
    - broker restart after stale socket
    - stale non-socket path refusal
  - live tests:
    - NCM listener down → `transport-error`
    - `ncm-tcpctl` backend native shell built-in → ACM fallback
- 검증:
  - Python compile PASS
  - fake-only recovery PASS: `tmp/a90-v192-fake-20260511-214426/`
  - live recovery PASS: `tmp/a90-v192-live-20260511-214438/`
  - live result: tests=5 failed=0
  - blocked audit: `operator-required`
  - NCM down audit: `transport-error`
  - fallback audit: backend=`acm-cmdv1`
- 남은 검증:
  - 없음
- 다음 실행 항목: v193 후보 재선정 또는 v193 broker/auth hardening follow-up

### V193. Broker/Auth Hardening Follow-up — PASS

- 계획: `docs/plans/NATIVE_INIT_V193_BROKER_AUTH_HARDENING_PLAN_2026-05-11.md`
- 보고서: `docs/reports/NATIVE_INIT_V193_BROKER_AUTH_HARDENING_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v193은 host-side broker/auth hardening이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/a90_broker.py` no-auth explicit allow gate, token validation, auth-failed classification, token redaction
  - `scripts/revalidation/a90_broker_auth_hardening_check.py`
- 검증:
  - Python compile PASS
  - auth hardening check PASS: `tmp/a90-v193-auth-check/`
  - fake concurrent regression PASS: `tmp/a90-v193-fake-regress/`
- 남은 검증: 없음
- 다음 실행 항목: v194 NCM/tcpctl listener lifecycle automation

### V194. NCM/tcpctl Broker Lifecycle Automation — PASS

- 계획: `docs/plans/NATIVE_INIT_V194_NCM_TCPCTL_LIFECYCLE_PLAN_2026-05-11.md`
- 보고서: `docs/reports/NATIVE_INIT_V194_NCM_TCPCTL_LIFECYCLE_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v194는 host-side lifecycle wrapper이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/a90_broker_ncm_lifecycle_check.py`
  - authenticated tcpctl start → NCM broker smoke → tcpctl stop lifecycle wrapper
  - dry-run command plan mode
- 검증:
  - Python compile PASS
  - dry-run lifecycle PASS: `tmp/a90-v194-dry-run/`
- 남은 검증:
  - live NCM lifecycle는 bridge/NCM 준비 시 선택 실행
- 다음 실행 항목: v195 broker-backed long/mixed soak

### V195. Broker-backed Soak Suite — PASS

- 계획: `docs/plans/NATIVE_INIT_V195_BROKER_SOAK_SUITE_PLAN_2026-05-11.md`
- 보고서: `docs/reports/NATIVE_INIT_V195_BROKER_SOAK_SUITE_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v195는 host-side broker suite이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/a90_broker_soak_suite.py`
  - concurrent smoke + mixed-soak gate + recovery tests orchestration
- 검증:
  - Python compile PASS
  - dry-run suite PASS: `tmp/a90-v195-dry-suite/`
- 남은 검증:
  - live 장시간 suite는 bridge/NCM 준비 시 선택 실행
- 다음 실행 항목: v196 fresh security scan follow-up workflow

### V196. Fresh Security Scan Follow-up Workflow — PASS

- 계획: `docs/plans/NATIVE_INIT_V196_SECURITY_SCAN_FOLLOWUP_PLAN_2026-05-11.md`
- 보고서: `docs/reports/NATIVE_INIT_V196_SECURITY_SCAN_FOLLOWUP_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v196은 host-side security follow-up workflow이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/security_scan_followup.py`
  - `docs/security/scans/SECURITY_FRESH_SCAN_V196_2026-05-11.md`
- 검증:
  - Python compile PASS
  - security scan follow-up PASS: `tmp/a90-v196-security-followup/`
  - local targeted security rescan PASS/WARN/FAIL = 29/1/0
- 남은 검증: 없음
- 다음 실행 항목: v197 kernel config decoder

### V197. Kernel Config Decoder / Capability Matrix — PASS

- 계획: `docs/plans/NATIVE_INIT_V197_KERNEL_CONFIG_DECODER_PLAN_2026-05-12.md`
- 보고서: `docs/reports/NATIVE_INIT_V197_KERNEL_CONFIG_DECODER_2026-05-12.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v197은 host-side read-only kernel config decoder이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/a90_kernel_tools.py`
  - `scripts/revalidation/kernel_config_decode.py`
- 검증:
  - Python compile PASS
  - `/proc/config.gz` decode PASS: `tmp/kernel-config/v197-kernel-config.md`
  - parsed CONFIG entries: `5724`
- 남은 검증: 없음
- 다음 실행 항목: v198 netfilter/nftables exposure inventory

### V198. Netfilter / Nftables Exposure Inventory — PASS

- 계획: `docs/plans/NATIVE_INIT_V198_NETFILTER_INVENTORY_PLAN_2026-05-12.md`
- 보고서: `docs/reports/NATIVE_INIT_V198_NETFILTER_INVENTORY_2026-05-12.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v198은 host-side read-only network exposure inventory이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/netfilter_inventory.py`
- 검증:
  - Python compile PASS
  - live netfilter inventory PASS: `tmp/netfilter/v198-netfilter.md`
  - decision: `legacy-iptables-runtime-present`
- 남은 검증: 없음
- 다음 실행 항목: v199 cgroup/PSI resource control inventory

### V199. Cgroup / PSI Resource Control Inventory — PASS

- 계획: `docs/plans/NATIVE_INIT_V199_CGROUP_PSI_INVENTORY_PLAN_2026-05-12.md`
- 보고서: `docs/reports/NATIVE_INIT_V199_CGROUP_PSI_INVENTORY_2026-05-12.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v199은 host-side read-only cgroup/PSI inventory이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/cgroup_psi_inventory.py`
- 검증:
  - Python compile PASS
  - live cgroup/PSI inventory PASS: `tmp/cgroup-psi/v199-cgroup-psi.md`
  - decision: `supported-unmounted-psi-present`
- 남은 검증: 없음
- 다음 실행 항목: v200 tracefs/pstore debug observability plan

### V200. Tracefs / Pstore Debug Observability Plan — PASS

- 계획: `docs/plans/NATIVE_INIT_V200_DEBUG_OBSERVABILITY_PLAN_2026-05-12.md`
- 보고서: `docs/reports/NATIVE_INIT_V200_DEBUG_OBSERVABILITY_2026-05-12.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v200은 host-side read-only debug observability planner이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/debug_observability_plan.py`
- 검증:
  - Python compile PASS
  - live tracefs/pstore observability plan PASS: `tmp/debug-observability/v200-debug-observability.md`
  - tracefs support yes/mounted no, pstore support yes/mounted no, usbmon kernel-missing
- 남은 검증: 없음
- 다음 실행 항목: v201 host evidence helper consolidation

### V201. Host Evidence Helper Consolidation — PASS

- 계획: `docs/plans/NATIVE_INIT_V201_HOST_EVIDENCE_HELPER_PLAN_2026-05-12.md`
- 보고서: `docs/reports/NATIVE_INIT_V201_HOST_EVIDENCE_HELPER_2026-05-12.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v201은 host-side evidence helper consolidation이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/a90_kernel_tools.py`
  - shared private output path: `scripts/revalidation/a90harness/evidence.py`
- 검증:
  - Python compile PASS
  - v197-v200 live collector rerun PASS
  - evidence: `tmp/kernel-config/v201-kernel-config.json`, `tmp/netfilter/v201-netfilter.json`, `tmp/cgroup-psi/v201-cgroup-psi.json`, `tmp/debug-observability/v201-debug-observability.json`
- 남은 검증: legacy v154-v159 collector full migration은 별도 후보
- 다음 실행 항목: v202 kernel capability summary view

### V202. Kernel Capability Summary View — PASS

- 계획: `docs/plans/NATIVE_INIT_V202_KERNEL_CAPABILITY_SUMMARY_PLAN_2026-05-12.md`
- 보고서: `docs/reports/NATIVE_INIT_V202_KERNEL_CAPABILITY_SUMMARY_2026-05-12.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v202는 host-side kernel capability summary이며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/kernel_capability_summary.py`
- 검증:
  - Python compile PASS
  - summary from existing JSON PASS: `tmp/kernel-capability/v202-kernel-capability.json`
  - summary with `--refresh` PASS: `tmp/kernel-capability/v202-kernel-capability-refresh.json`
  - Wi-Fi gate: `baseline-required`
- 남은 검증: 없음
- 다음 실행 항목: v203 read-only Wi-Fi baseline refresh 계획서 구현

### V203. Wi-Fi Read-Only Baseline Refresh — PASS

- 계획: `docs/plans/NATIVE_INIT_V203_WIFI_BASELINE_REFRESH_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V203_WIFI_BASELINE_REFRESH_2026-05-13.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v203은 host-side Wi-Fi baseline evidence refresh로 시작하며 별도 native-init boot image 없음
- 구현:
  - `scripts/revalidation/wifi_baseline_refresh.py`
  - `--host/--bridge-host`, `--port/--bridge-port`, `--mount-system-ro`, `--no-mount-system-ro`
  - kernel capability summary 자동 refresh fallback
- 의도:
  - F055 패치 후 live `wififeas gate`를 필수 preflight로 사용
  - native/mounted-system/optional Android-TWRP Wi-Fi evidence를 private host bundle로 재수집
  - active Wi-Fi bring-up 여부가 아니라 v204 controlled read-only probe 가능성만 판정
- guardrails:
  - Wi-Fi enablement, rfkill write, `wlan0` link-up, module load/unload, firmware mutation, Android Wi-Fi service start 금지
  - USB ACM bridge와 NCM rescue boundary 유지
- 정적 검증:
  - Python compile PASS
  - command guard PASS
  - `git diff --check` PASS
- 실기 검증:
  - `python3 scripts/revalidation/wifi_baseline_refresh.py --out-dir tmp/wifi/v203-baseline` PASS
  - decision: `no-go`
  - missing gates: `native-wlan-interface`, `wifi-rfkill`, `wlan-cnss-qca-module-evidence`
  - mounted Android-side candidates: system Wi-Fi init/permission/sysconfig files only
- 남은 검증: 없음
- 다음 실행 항목: v204 read-only Android/TWRP Wi-Fi driver and firmware baseline 구현

### V204. Android/TWRP Wi-Fi Driver and Firmware Baseline — PASS

- 계획: `docs/plans/NATIVE_INIT_V204_ANDROID_TWRP_WIFI_BASELINE_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V204_ANDROID_TWRP_WIFI_BASELINE_2026-05-13.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)` + Android/TWRP ADB read-only modes
- device flash: native-init boot image 없음. Android run은 `backups/baseline_a_20260423_030309/boot.img`를 일시 flash했고, 수집 후 `stage3/boot_linux_v159.img`로 복구했다.
- 구현:
  - `scripts/revalidation/android_twrp_wifi_baseline.py`
  - `--android-adb`, `--twrp-adb`, `--serial`, `--v203-manifest`, `--out-dir`
  - private/no-follow evidence bundle output
  - v203-v204 comparison matrix
  - active Wi-Fi command guard
- 의도:
  - v203 `no-go` 원인을 Android/TWRP read-only evidence로 좁힌다
  - driver/module/rfkill/firmware/HAL/init/log 근거를 수집한다
  - v205 read-only `nl80211/cfg80211` probe 계획 가능 여부만 판정한다
- guardrails:
  - Wi-Fi enablement, rfkill write, WLAN link-up, module mutation, firmware mutation, supplicant/hostapd/vendor daemon start 금지
  - `/data/misc/wifi`, `dumpsys wifi`, saved network material은 기본 제외
  - evidence output은 private/no-follow 유지
- 정적 검증:
  - Python compile PASS
  - command guard PASS
  - `--help` PASS
- 실기 검증:
  - native bridge `recovery` → TWRP ADB PASS
  - `python3 scripts/revalidation/android_twrp_wifi_baseline.py --twrp-adb --v203-manifest tmp/wifi/v203-baseline/manifest.json --out-dir tmp/wifi/v204-twrp-baseline` PASS
  - TWRP decision: `driver-candidate-found`
  - TWRP evidence: ICNSS/WLAN kernel log hints and firmware search path present
  - still missing: WLAN interface, Wi-Fi rfkill, loaded WLAN/CNSS/QCA module
  - Android boot image restored from `backups/baseline_a_20260423_030309/boot.img`
  - Android ADB PASS: `product:r3qks model:SM_A908N device:r3q`
  - Magisk root PASS: `uid=0(root) ... context=u:r:magisk:s0`
  - `python3 scripts/revalidation/android_twrp_wifi_baseline.py --android-adb --v203-manifest tmp/wifi/v203-baseline/manifest.json --out-dir tmp/wifi/v204-android-baseline` PASS
  - Android decision: `ready-for-readonly-nl80211-probe-plan`
  - Android evidence: `wlan0`, `swlan0`, `p2p0`, `wifi-aware0`, ICNSS rfkill/sysfs, firmware/HAL/init assets, root dmesg ICNSS/WLAN readiness
  - native boot restore PASS: `stage3/boot_linux_v159.img`, SHA256 `7e7e81a6af774b3b523c993851d64b86484be4c471dbee02edf062b3903c536f`
  - post-restore `cmdv1 version/status` PASS
- 남은 검증: 없음
- 다음 실행 항목: v205 ICNSS/WCNSS/QCA + nl80211 read-only sysfs/firmware probe 계획

### V205. ICNSS/WCNSS/QCA + nl80211 Read-Only Probe — PASS

- 계획: `docs/plans/NATIVE_INIT_V205_ICNSS_NL80211_READONLY_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V205_ICNSS_NL80211_READONLY_2026-05-13.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v205는 host-side/native read-only Wi-Fi probe로 시작한다.
- 배경:
  - v203 native baseline은 `no-go`: WLAN netdev, Wi-Fi rfkill, WLAN/CNSS/QCA module evidence 없음
  - v204 Android baseline은 `ready-for-readonly-nl80211-probe-plan`: `wlan0`, `swlan0`, `p2p0`, `wifi-aware0`, ICNSS rfkill/sysfs, root dmesg readiness 확인
- 구현 후보:
  - `scripts/revalidation/wifi_icnss_nl80211_probe.py`
  - optional `/cache/bin/a90_nl80211_ro` read-only helper
  - private/no-follow evidence output under `tmp/wifi/v205-icnss-nl80211-readonly`
- 허용:
  - `/sys/class/net`, `/sys/class/rfkill`, `/sys/class/ieee80211`, ICNSS sysfs, firmware path read-only 수집
  - `NL80211_CMD_GET_PROTOCOL_FEATURES`, `NL80211_CMD_GET_WIPHY`, `NL80211_CMD_GET_INTERFACE`
  - v203/v204 evidence 비교
- 금지:
  - Wi-Fi enablement, rfkill write, `ip link set wlan0 up`
  - scan/connect, `NL80211_CMD_TRIGGER_SCAN`, `SET_INTERFACE`, `SET_WIPHY`
  - module load/unload, firmware mutation, Android Wi-Fi service/supplicant/hostapd start
- 결정 모델:
  - `no-native-icnss`
  - `native-icnss-present-no-wiphy`
  - `native-wiphy-readonly-ok`
  - `android-only-driver-ready`
  - `manual-review-required`
- 검증:
  - Python compile PASS
  - v205 command guard PASS
  - `a90_nl80211_ro` static ARM64 build PASS
  - native `mountsystem ro` PASS
  - `python3 scripts/revalidation/wifi_icnss_nl80211_probe.py --native-bridge --v203-manifest tmp/wifi/v203-baseline/manifest.json --v204-android-manifest tmp/wifi/v204-android-baseline/manifest.json --out-dir tmp/wifi/v205-icnss-nl80211-readonly` PASS
- 실기 결과:
  - decision: `native-icnss-present-no-wiphy`
  - native ICNSS sysfs: present
  - native WLAN netdev/wiphy/Wi-Fi rfkill: absent
  - remote `/cache/bin/a90_nl80211_ro`: absent on current v159 runtime
- 다음 실행 항목: v206 Android ICNSS/CNSS dependency map live Android 실행

### V206. Android ICNSS/CNSS Dependency Map — PASS

- 계획: `docs/plans/NATIVE_INIT_V206_ANDROID_ICNSS_CNSS_MAP_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V206_ANDROID_ICNSS_CNSS_MAP_2026-05-13.md`
- device flash: 없음. v206은 host-side Android ADB/root read-only dependency map collector다.
- 기준:
  - v204 Android baseline: `ready-for-readonly-nl80211-probe-plan`
  - v205 native baseline: `native-icnss-present-no-wiphy`
- 구현:
  - `scripts/revalidation/android_icnss_cnss_map.py`
  - private/no-follow evidence output under `tmp/wifi/v206-android-icnss-cnss-map`
  - v204/v205 manifest comparison
  - active Wi-Fi command guard
- 허용:
  - Android init rc/service/property state read-only 수집
  - firmware path/stat read-only 수집
  - ICNSS/WLAN/rfkill/ieee80211 sysfs read-only 수집
  - dmesg/logcat Wi-Fi/CNSS/ICNSS/QMI/firmware readiness grep
- 금지:
  - Wi-Fi enablement, rfkill write, WLAN link-up
  - scan/connect, module load/unload, firmware mutation
  - Android Wi-Fi service/supplicant/hostapd/cnss-daemon start
  - `/data/misc/wifi`, `dumpsys wifi`, saved network material 기본 수집
- 결정 모델:
  - `ready-for-native-preflight-plan`
  - `android-cnss-map-complete`
  - `missing-firmware-map`
  - `missing-service-map`
  - `native-replay-prereq-missing`
  - `manual-review-required`
- 정적 검증:
  - Python compile PASS
  - v206 command guard PASS
- 실기 검증:
  - Android boot image flash: `backups/baseline_a_20260423_030309/boot.img`, SHA256 `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`
  - Android ADB/root PASS: `product:r3qks model:SM_A908N device:r3q`, `uid=0(root) ... context=u:r:magisk:s0`
  - `python3 scripts/revalidation/android_icnss_cnss_map.py --android-adb --su --v204-android-manifest tmp/wifi/v204-android-baseline/manifest.json --v205-manifest tmp/wifi/v205-icnss-nl80211-readonly/manifest.json --out-dir tmp/wifi/v206-android-icnss-cnss-map` PASS
  - decision: `ready-for-native-preflight-plan`
  - evidence: service/init/firmware/interface/ICNSS/QMI/log/mount 모두 mapped
  - manifest SHA256: `2837fe4d2003b3fa25d0a1b590068f9e9cc8b4975d371b084f103fa3ed93ac20`
  - summary SHA256: `1232ca6b2888cb966aaa796fd3178c1ee368af90933f581e57a68c7749c3603c`
  - native restore: `stage3/boot_linux_v159.img`, SHA256 `7e7e81a6af774b3b523c993851d64b86484be4c471dbee02edf062b3903c536f`
  - post-restore `cmdv1 version/status` PASS: `A90 Linux init 0.9.59 (v159)`
- 다음 실행 항목:
  - v207 native read-only Wi-Fi preflight 계획
  - active Wi-Fi bring-up은 계속 blocked

### V207. Native Read-Only Wi-Fi Preflight — PASS

- 계획: `docs/plans/NATIVE_INIT_V207_NATIVE_WIFI_PREFLIGHT_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V207_NATIVE_WIFI_PREFLIGHT_2026-05-13.md`
- device flash: 없음. v207은 host-side/native read-only preflight collector로 시작한다.
- 기준:
  - v205 native baseline: `native-icnss-present-no-wiphy`
  - v206 Android map: `ready-for-native-preflight-plan`
- 구현:
  - `scripts/revalidation/native_wifi_preflight.py`
  - private/no-follow evidence output under `tmp/wifi/v207-native-wifi-preflight`
  - v205/v206 manifest comparison
  - active Wi-Fi command guard
- 허용:
  - native version/status/bootstatus metadata 수집
  - `mountsystem ro` 후 mounted-system firmware/init rc path read-only 확인
  - ICNSS sysfs, WLAN netdev, rfkill, `ieee80211`, firmware loader state read-only 수집
  - existing `/cache/bin/a90_nl80211_ro` GET-only helper 실행 if already present
- 금지:
  - Wi-Fi enablement, rfkill write, WLAN link-up
  - scan/connect, active `nl80211` set/scan/connect commands
  - module load/unload, `firmware_class.path` write, firmware mutation
  - `cnss-daemon`, `wificond`, Wi-Fi HAL, supplicant, hostapd start
  - `/data/misc/wifi`, `cmd wifi`, `svc wifi`, `dumpsys wifi` collection
- 결정 모델:
  - `native-preflight-ready`
  - `userspace-service-gap-confirmed`
  - `missing-mounted-vendor`
  - `missing-firmware-path`
  - `missing-icnss-sysfs`
  - `missing-nl80211-helper`
  - `missing-wiphy-netdev`
  - `manual-review-required`
- 검증 계획:
  - Python compile PASS
  - v207 command guard PASS
  - `git diff --check` PASS
  - native bridge live collector run PASS
- 실기 결과:
  - runtime: `A90 Linux init 0.9.59 (v159)`
  - decision: `missing-mounted-vendor`
  - basic control: PASS
  - `mountsystem ro`: PASS
  - native ICNSS sysfs: present
  - mounted system init path: present
  - mounted vendor firmware/init paths: missing
  - native WLAN netdev/wiphy/Wi-Fi rfkill: absent
  - remote `/cache/bin/a90_nl80211_ro`: absent
  - manifest SHA256: `d3d88598d9b66b179044416a404d5649f377567482a74e214ac07706e9aae7b4`
  - summary SHA256: `ef1dd5cfa4acca5003fb2041f194834b796ab1402981d3a712228ef31490edb6`
- 다음 실행 항목:
  - v208 native vendor/firmware mount visibility 계획
  - active Wi-Fi bring-up은 계속 blocked

### V208. Native Vendor/Firmware Mount Visibility — PASS

- 계획: `docs/plans/NATIVE_INIT_V208_VENDOR_FIRMWARE_MOUNT_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V208_VENDOR_FIRMWARE_MOUNT_2026-05-13.md`
- device flash: 없음. v208은 host-side/native read-only block/mount visibility collector로 시작한다.
- 기준:
  - v206 Android map: `ready-for-native-preflight-plan`
  - v207 native preflight: `missing-mounted-vendor`
- 구현:
  - `scripts/revalidation/native_vendor_mount_probe.py`
  - private/no-follow evidence output under `tmp/wifi/v208-vendor-firmware-mount`
  - v206/v207 manifest comparison
  - mount/write/destructive command guard
- 허용:
  - native version/status/bootstatus metadata 수집
  - `/proc/mounts`, `/proc/partitions`, `/dev/block`, `/sys/class/block` read-only inventory
  - known physical candidates `sda28`, `sda29`, `sda30`, `sda32` read-only 확인
  - possible `dm-*`, `super`, `metadata` read-only 확인
  - `/mnt/system/vendor` and `/vendor` firmware/init path visibility 확인
  - firmware loader path read-only 확인
- 금지:
  - Wi-Fi enablement, rfkill write, WLAN link-up
  - scan/connect, module load/unload, firmware mutation
  - `firmware_class.path` write
  - `cnss-daemon`, `wificond`, Wi-Fi HAL, supplicant, hostapd start
  - vendor/product/system writes
  - mount/umount by default
  - destructive storage commands
- 결정 모델:
  - `vendor-visible-existing-mount`
  - `vendor-block-candidate-found`
  - `dynamic-partition-mapping-required`
  - `vendor-path-still-missing`
  - `manual-review-required`
- 검증:
  - Python compile PASS
  - v208 command guard PASS
  - `git diff --check` PASS
  - native bridge live collector run PASS
- 실기 결과:
  - runtime: `A90 Linux init 0.9.59 (v159)`
  - decision: `vendor-block-candidate-found`
  - reason: `a plausible vendor block candidate exists, but default native mounts do not expose vendor assets`
  - basic control: PASS
  - existing vendor mount: false
  - known physical vendor candidate: true
  - `/proc/partitions`: `sda29`, `sda30`, `sda32` present
  - `/sys/class/block/sda29`: present, `dev=259:22`, `size=2764800`
  - `/dev/block/sda29`: absent
  - `/dev/block/by-name`: absent
  - `/dev/block/bootdevice/by-name`: absent
  - `dm-*`/`super` evidence: absent
  - mounted vendor firmware/init paths: missing
  - firmware_class path: `/vendor/firmware_mnt/image`
  - manifest SHA256: `73938c3ec139dbee5fbd5c61c13335f5bf530ed40873b5ef249cff81e2048755`
  - summary SHA256: `81d8af25a7e0a0620233fbe1e179dae87fcb96b61e345cae14d1f79d9d53ea10`
- 다음 실행 항목:
  - v209 explicit read-only vendor partition mount probe
  - active Wi-Fi bring-up은 계속 blocked

### V209. Vendor Read-Only Mount Probe — PASS

- 계획: `docs/plans/NATIVE_INIT_V209_VENDOR_RO_MOUNT_PROBE_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V209_VENDOR_RO_MOUNT_PROBE_2026-05-13.md`
- 목표:
  - v208에서 확인한 `sda29` vendor 후보를 native init에서 안전하게 임시 mount할 수 있는지 확인
  - Android vendor firmware/init asset이 native-visible 상태가 되는지 확인
- 핵심 안전 기준:
  - plain `mountfs ... ext4 ro` 금지
  - ext4 journal replay write를 피하기 위해 `ro,noload` 필수
  - 임시 block node와 mountpoint는 `/tmp/a90-v209-*` 아래에만 생성
  - 성공/실패와 무관하게 `umount`와 post-mount cleanup 검증 필수
- 구현 후보:
  - `scripts/revalidation/native_vendor_ro_mount_probe.py`
  - evidence output: `tmp/wifi/v209-vendor-ro-mount-probe`
  - report: `docs/reports/NATIVE_INIT_V209_VENDOR_RO_MOUNT_PROBE_2026-05-13.md`
- 결정 모델:
  - `vendor-assets-visible`
  - `vendor-mounted-no-wifi-assets`
  - `vendor-mount-failed`
  - `candidate-node-missing`
  - `unsafe-ro-noload-unavailable`
  - `cleanup-failed`
  - `manual-review-required`
- 검증:
  - Python compile PASS
  - v209 command guard PASS
  - `git diff --check` PASS
  - native bridge live collector run PASS
- 실기 결과:
  - runtime: `A90 Linux init 0.9.59 (v159)`
  - decision: `vendor-assets-visible`
  - reason: `safe ro,noload mount exposed vendor firmware/init assets`
  - `sda29` major/minor: `259:22`
  - ext4 available: true
  - mount command: `run /cache/bin/toybox mount -t ext4 -o ro,noload /tmp/a90-v209-*/sda29 /tmp/a90-v209-*/vendor`
  - mounted line: `ext4 ro,relatime,norecovery,i_version`
  - cleanup rc: `0`
  - leftover mount: false
  - visible assets: `etc/init`, `etc/init/hw`, `android.hardware.wifi.supplicant-service.rc`, `android.hardware.wifi@1.0-service.rc`, `hostapd.android.rc`, `init.qcom.rc`, `etc/wifi`, `firmware/wlan/qca_cld/bdwlan.bin`, `firmware/wlan/qca_cld/regdb.bin`, `firmware/wlanmdsp.mbn`, `lib/modules`
  - manifest SHA256: `b5a4fc182c84c97d9ae5533f4f39e57ce55765461e919bcf5f9fd67a34ed4b1c`
  - summary SHA256: `f7f01980ce2a580839bb7996ae985659f7d33a2114e044d5b982fe1e1cb66f42`
- 다음 실행 항목:
  - v210 vendor Wi-Fi/CNSS asset classifier
  - active Wi-Fi bring-up은 계속 blocked

### V210. Vendor Wi-Fi/CNSS Asset Classifier — PASS

- 계획: `docs/plans/NATIVE_INIT_V210_VENDOR_WIFI_CNSS_ASSET_CLASSIFIER_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V210_VENDOR_WIFI_CNSS_ASSET_CLASSIFIER_2026-05-13.md`
- 목표:
  - v209에서 확인한 native-visible vendor mount를 기준으로 Wi-Fi/CNSS asset map 작성
  - firmware/init rc/service binary/library/module/VINTF/firmware loader implication 분류
  - Android v206 evidence와 native-visible vendor asset parity 확인
- 핵심 안전 기준:
  - v209와 같은 ext4 `ro,noload` temporary vendor mount만 허용
  - `firmware_class.path` write 금지
  - Wi-Fi enable, rfkill write, WLAN link-up, scan/connect 금지
  - `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, hostapd start 금지
- 구현 후보:
  - `scripts/revalidation/native_vendor_asset_classifier.py`
  - evidence output: `tmp/wifi/v210-vendor-asset-classifier`
  - report: `docs/reports/NATIVE_INIT_V210_VENDOR_WIFI_CNSS_ASSET_CLASSIFIER_2026-05-13.md`
- 결정 모델:
  - `asset-map-ready`
  - `firmware-path-policy-needed`
  - `service-dependency-gap`
  - `vendor-assets-incomplete`
  - `dependency-parser-unavailable`
  - `cleanup-failed`
  - `manual-review-required`
- 검증:
  - Python compile PASS
  - v210 command guard PASS
  - `git diff --check` PASS
  - native bridge live collector run PASS
- 실기 결과:
  - runtime: `A90 Linux init 0.9.59 (v159)`
  - decision: `firmware-path-policy-needed`
  - reason: `required firmware exists, but current firmware_class.path does not point at the visible vendor firmware layout`
  - `sda29` major/minor: `259:22`
  - ext4 available: true
  - mount command: `run /cache/bin/toybox mount -t ext4 -o ro,noload /tmp/a90-v210-*/sda29 /tmp/a90-v210-*/vendor`
  - mounted line: `ext4 ro,relatime,norecovery,i_version`
  - cleanup rc: `0`
  - leftover mount: false
  - visible paths: `47`
  - missing required firmware/init rc/binaries: `0/0/0`
  - parsed services: `btcoex_cont_config`, `cnss-daemon`, `cnss_diag`, `hostapd`, `vendor.wifi_hal_ext`, `vendor.wifi_hal_legacy`, `wpa_supplicant`
  - firmware loader state: `firmware_class.path=/vendor/firmware_mnt/image`, required Wi-Fi firmware under current loader path: none
  - manifest SHA256: `8a820f74497de2118e3bcc5f7e9af718894f5504993caccfe811fffdbd1b0fd7`
  - summary SHA256: `5ec39f8a7d4d71c824015acb3cb6c7a9cae77630d2e929dbd10a9628a3af9588`
- 다음 실행 항목:
  - v211 firmware path/layout policy 계획
  - active Wi-Fi bring-up은 계속 blocked

### V211. Firmware Path / Vendor Layout Policy — PASS

- 계획: `docs/plans/NATIVE_INIT_V211_FIRMWARE_PATH_POLICY_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V211_FIRMWARE_PATH_POLICY_2026-05-13.md`
- 목표:
  - v210 `firmware-path-policy-needed` 결과를 기준으로 native firmware lookup policy를 먼저 설계
  - required Wi-Fi/CNSS firmware request name이 어떤 candidate root에서 resolve되는지 read-only로 모델링
  - `firmware_class.path` write, `/vendor` bind layout, full vendor layout 중 가장 낮은 리스크 경로 결정
- 핵심 안전 기준:
  - active Wi-Fi bring-up 금지
  - `firmware_class.path` write 금지
  - `/vendor`, `/lib/firmware`, `/cache` 등 persistent path bind/copy 금지
  - v209/v210과 같은 temporary `ro,noload` vendor mount만 허용
  - `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, hostapd start 금지
- 구현 후보:
  - `scripts/revalidation/native_firmware_path_policy_probe.py`
  - evidence output: `tmp/wifi/v211-firmware-path-policy`
  - report: `docs/reports/NATIVE_INIT_V211_FIRMWARE_PATH_POLICY_2026-05-13.md`
- 정책 후보:
  - Option A: isolated vendor firmware root + future guarded `firmware_class.path=/mnt/vendor/firmware`
  - Option B: synthetic `/vendor/firmware_mnt/image` read-only bind layout
  - Option C: full read-only vendor layout, later service feasibility용으로 보류
  - Option D: copy firmware into `/lib/firmware`, 현재 reject
- 결정 모델:
  - `path-policy-ready`
  - `request-name-unknown`
  - `bind-layout-needed`
  - `sysfs-path-update-needed`
  - `vendor-layout-risk-too-high`
  - `cleanup-failed`
  - `manual-review-required`
- 검증:
  - Python compile PASS
  - v211 command guard PASS
  - `git diff --check` PASS
  - native bridge live collector run PASS
- 실기 결과:
  - runtime: `A90 Linux init 0.9.59 (v159)`
  - decision: `sysfs-path-update-needed`
  - reason: `isolated vendor firmware root resolves likely request names; future implementation needs guarded firmware_class.path update`
  - `sda29` major/minor: `259:22`
  - ext4 available: true
  - mount command: `run /cache/bin/toybox mount -t ext4 -o ro,noload /tmp/a90-v211-*/sda29 /tmp/a90-v211-*/vendor`
  - mounted line: `ext4 ro,relatime,norecovery,i_version`
  - cleanup rc: `0`
  - leftover mount: false
  - `firmware_class.path`: `/vendor/firmware_mnt/image`
  - post-probe `firmware_class.path`: `/vendor/firmware_mnt/image`
  - current `/vendor/firmware_mnt/image` model: likely request names resolve none
  - isolated `/mnt/vendor/firmware` model: likely request names resolve all
  - synthetic `/vendor/firmware_mnt/image` bind model: likely request names resolve all
  - uncertain bare request names unresolved: `WCNSS_qcom_cfg.ini`, `bdwlan.bin`, `regdb.bin`
  - manifest SHA256: `5ad7c822cf9d9214bc9803f393865a2f8a87a739b31de2cb4744d94a6d5c0c51`
  - summary SHA256: `2ccf688181243c6f84f76f72c5d784a9c1ee39f88be34c10235d9d2726c01bdf`
- 다음 실행 항목:
  - v212 guarded opt-in `firmware_class.path=/mnt/vendor/firmware` update and rollback test 계획
  - active Wi-Fi bring-up은 계속 blocked

### V212. Guarded Firmware Path Apply / Rollback Probe — PASS

- 계획: `docs/plans/NATIVE_INIT_V212_FIRMWARE_PATH_ROLLBACK_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V212_FIRMWARE_PATH_ROLLBACK_2026-05-13.md`
- 목표:
  - v211 `sysfs-path-update-needed` 결과를 기준으로 `firmware_class.path=/mnt/vendor/firmware` 적용/원복 가능성 검증
  - no-newline sysfs write, readback, likely request resolution, rollback, cleanup을 한 번에 증명
  - Wi-Fi daemon/HAL/supplicant/hostapd 실행 없이 firmware loader path만 다룸
- 구현 후보:
  - `scripts/revalidation/native_firmware_path_apply_probe.py`
  - `stage3/linux_init/helpers/a90_fwpathctl.c`
  - `scripts/revalidation/build_fwpathctl_helper.sh`
  - evidence output: `tmp/wifi/v212-firmware-path-rollback`
  - report: `docs/reports/NATIVE_INIT_V212_FIRMWARE_PATH_ROLLBACK_2026-05-13.md`
- 결정 모델:
  - `path-rollback-pass`
  - `apply-required`
  - `write-helper-unavailable`
  - `path-readback-mismatch`
  - `rollback-failed`
  - `cleanup-failed`
  - `request-name-unknown`
  - `manual-review-required`
- 핵심 안전 기준:
  - dry-run은 sysfs write 금지
  - apply mode는 `--apply` 명시 시에만 허용
  - plain `echo`/shell redirection 금지, `/cache/bin/a90_fwpathctl` fixed-target write만 허용
  - 원래 `firmware_class.path` readback/rollback 필수
  - active Wi-Fi bring-up, rfkill write, link-up, scan/connect, daemon start, firmware copy, bind mount 금지
- 검증:
  - Python compile PASS
  - v212 command guard PASS
  - `a90_fwpathctl` static ARM64 build PASS
  - `/cache/bin/a90_fwpathctl` IPv6 link-local NCM deploy PASS
  - `git diff --check` PASS
  - native bridge dry-run collector PASS
  - native bridge apply rollback collector PASS
- dry-run 실기 결과:
  - runtime: `A90 Linux init 0.9.59 (v159)`
  - decision: `apply-required`
  - reason: `dry-run mount and request resolution passed; rerun with --apply to test sysfs write rollback`
  - `sda29` major/minor: `259:22`
  - ext4 available: true
  - mount command: `run /cache/bin/toybox mount -t ext4 -o ro,noload /tmp/a90-v212-*/sda29 /mnt/vendor`
  - mounted line: `ext4 ro,relatime,norecovery,i_version`
  - cleanup rc: `0`
  - leftover `/mnt/vendor` mount: false
  - leftover `/tmp/a90-v212-*` mount: false
  - original `firmware_class.path`: `/vendor/firmware_mnt/image`
  - post-run `firmware_class.path`: `/vendor/firmware_mnt/image`
  - likely request paths under `/mnt/vendor/firmware`: all visible
  - manifest SHA256: `64d4ebc3d7a0d913c09dc0393adc2484f0cd66097d9d16e8172cfc7c8d6cf6d5`
  - summary SHA256: `23190130f3ad30b04be0c4b48d6bf0a42a77d96ebbcb789fb3ddf23ec1a52e09`
- apply 실기 결과:
  - decision: `path-rollback-pass`
  - reason: `firmware_class.path apply, readback, request resolution, rollback, and cleanup passed`
  - helper: `/cache/bin/a90_fwpathctl`, SHA256 `8d08de43edd921099a6c2e627222e06488913d93f56fc0db01b5c7902df5e3cc`
  - applied `firmware_class.path`: `/mnt/vendor/firmware`
  - rolled back `firmware_class.path`: `/vendor/firmware_mnt/image`
  - post-run `firmware_class.path`: `/vendor/firmware_mnt/image`
  - leftover `/mnt/vendor` mount: false
  - leftover `/tmp/a90-v212-*` mount: false
  - manifest SHA256: `f1fea94259a979f0d9dee7c2ba548d77bb7fde1ab6b550c492f550276d7f2ba8`
  - summary SHA256: `9320206dc5734a312cd93e09872cee9dbfb1707cdf09e20ef2b78f50a1150acb`
- 다음 실행 항목:
  - v214 ICNSS reprobe 실행 완료, `icnss-rebind-failed`로 safety stop
  - v215에서 ICNSS/CNSS lifecycle research를 진행
  - active Wi-Fi bring-up은 계속 blocked

### V213. Firmware Request Evidence / ICNSS Reprobe Preflight — PASS

- 계획: `docs/plans/NATIVE_INIT_V213_FIRMWARE_REQUEST_EVIDENCE_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V213_FIRMWARE_REQUEST_EVIDENCE_2026-05-13.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- 구현:
  - `scripts/revalidation/native_firmware_request_probe.py`
  - `stage3/linux_init/helpers/a90_icnssctl.c`
  - `scripts/revalidation/build_icnssctl_helper.sh`
  - evidence output:
    - `tmp/wifi/v213-firmware-request-evidence-baseline`
    - `tmp/wifi/v213-firmware-request-evidence`
- live constraint:
  - `/proc/dynamic_debug/control`: absent
  - `/sys/kernel/tracing/events`: absent
  - ICNSS node: `/sys/devices/platform/soc/18800000.qcom,icnss`
  - ICNSS driver: `/sys/bus/platform/drivers/icnss`
  - bind/unbind controls exist and are write-only root sysfs files
- baseline 실기 결과:
  - result: PASS
  - decision: `baseline-only`
  - reason: `read-only ICNSS firmware request baseline collected`
  - captures: 24
  - expected absent captures: dynamic debug, tracefs events, debug tracing firmware events
  - manifest SHA256: `4ec982d385048e05078124f46a26a80ed9def439d454336652c8b2f8e621dbc6`
  - summary SHA256: `80249d1e7551c1b93982feb5f8856538a67419d33d3774caac56109784bbd02c`
- path-only 실기 결과:
  - result: PASS
  - decision: `path-only-pass`
  - reason: `firmware path apply/readback/rollback passed without ICNSS reprobe`
  - captures: 49
  - applied `firmware_class.path`: `/mnt/vendor/firmware`
  - rolled back `firmware_class.path`: `/vendor/firmware_mnt/image`
  - post-run `firmware_class.path`: `/vendor/firmware_mnt/image`
  - likely request paths under `/mnt/vendor/firmware`: all visible
  - leftover `/mnt/vendor` mount: false
  - leftover `/tmp/a90-v213-*` mount: false
  - manifest SHA256: `b71bbc0518e3a6109574f4ccc443f15dff486ca2528f411a0d118bf66f430c81`
  - summary SHA256: `44d5e11dd6b216d3e34d6e0edec4b62a9a97f9548cd1c6766640398b842a1234`
- guardrails:
  - default mode performs no mutation
  - `firmware_class.path` apply requires `--apply-path`
  - ICNSS unbind/bind requires both `--reprobe` and `--i-understand-icnss-reprobe`
  - active Wi-Fi bring-up, rfkill write, link-up, scan/connect, daemon/HAL/supplicant/hostapd start, module load/unload, firmware copy, persistent mount are forbidden
- 다음 실행 항목:
  - v214 결과에 따라 ICNSS generic unbind/bind는 unsafe로 취급
  - active Wi-Fi scan/connect는 계속 blocked

### V214. ICNSS Reprobe Execution / Firmware Request Evidence — SAFETY STOP

- 계획: `docs/plans/NATIVE_INIT_V214_ICNSS_REPROBE_EXECUTION_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V214_ICNSS_REPROBE_EXECUTION_2026-05-13.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- helper:
  - source: `stage3/linux_init/helpers/a90_icnssctl.c`
  - target: `/cache/bin/a90_icnssctl`
  - deployment: TWRP ADB push
  - SHA256: `652b66cb9079b0e9dd194c871bee7aca8dde16577a53f1837be71bd25babf0d5`
- collector update:
  - `scripts/revalidation/native_firmware_request_probe.py`
  - live `/sys/class/block/sda29/dev` major/minor 사용으로 수정
  - post-reprobe ICNSS bound 판정이 pre-reprobe evidence를 재사용하지 않도록 수정
- reprobe 실기 결과:
  - result: FAIL / safety stop
  - decision: `icnss-rebind-failed`
  - reason: `ICNSS bind/rebind evidence did not return to bound state`
  - `sda29`: `259:32`
  - temporary vendor `ro,noload` mount: PASS
  - `firmware_class.path` apply: `/mnt/vendor/firmware`
  - likely request paths under `/mnt/vendor/firmware`: all visible
  - `icnss unbind`: PASS
  - `icnss bind`: FAIL, userspace `write icnss control: No such device`
  - dmesg: `icnss: Driver is already initialized`
  - dmesg: `icnss: probe of 18800000.qcom,icnss failed with error -17`
  - request evidence: none
  - `firmware_class.path` rollback: PASS
  - cleanup: PASS, leftover mount 없음
  - manifest SHA256: `4e71bef89f30c3e5633aa99bc8a39882a2374c39135f154751d22b72c00e094f`
  - summary SHA256: `c9bc79cff9ecb97e838fe422c307a5b2deb604fa49d2aca68c36292bbca50df1`
- recovery:
  - manual bind retry도 동일한 `-17` 실패
  - native reboot 후 ICNSS bound 복구 PASS
  - post-reboot `firmware_class.path`: `/vendor/firmware_mnt/image`
  - post-reboot helper SHA 유지 PASS
- 다음 실행 항목:
  - v215 ICNSS/CNSS lifecycle research
  - v215-v225 큰 계획: `docs/plans/NATIVE_INIT_V215_V225_WIFI_BIG_PLAN_2026-05-13.md`
  - v215-v225 상세 로드맵: `docs/plans/NATIVE_INIT_V215_V225_WIFI_LIFECYCLE_ROADMAP_2026-05-13.md`
  - Android/TWRP dmesg/init service ordering, ICNSS recovery/debug controls, vendor CNSS hooks 조사
  - 추가 unbind/bind와 Wi-Fi scan/connect는 blocked

### V215-V225. ICNSS/CNSS Lifecycle to Controlled Wi-Fi Bring-Up — ROADMAP

- 큰 계획: `docs/plans/NATIVE_INIT_V215_V225_WIFI_BIG_PLAN_2026-05-13.md`
- 상세 로드맵: `docs/plans/NATIVE_INIT_V215_V225_WIFI_LIFECYCLE_ROADMAP_2026-05-13.md`
- version master plan:
  `docs/plans/NATIVE_INIT_V215_V225_WIFI_VERSION_MASTER_PLAN_2026-05-13.md`
- 기준:
  - v214가 `icnss-rebind-failed`로 safety stop 되었으므로 active Wi-Fi bring-up은 계속 blocked
  - generic ICNSS sysfs `unbind`/`bind`는 unsafe path로 분류
  - v215-v220은 lifecycle/dependency/read-only gate 중심
  - v221-v225는 현재 active Wi-Fi가 아니라 evidence/recovery/shim/security blocker closure
  - v225 gate v3도 `still-no-go`이므로 scan/connect는 계속 blocked
- 버전 축:
  - v215: ICNSS/CNSS lifecycle research
  - v216: Android service replay model
  - v217: ICNSS debug/recovery inventory
  - v218: CNSS daemon dry-run feasibility
  - v219: native Android-env shim plan
  - v220: Wi-Fi bring-up preflight gate v2
  - v221: host vendor ELF/library evidence closure
  - v222: vendor root evidence export/extraction
  - v223: recovery/rollback policy hardening
  - v224: Android-env shim dry-run materialization
  - v225: Wi-Fi exposure/credential security gate + preflight gate v3
- 다음 실행 항목:
  - v222 vendor root evidence export/extraction 구현 또는 source vendor root 확보
  - 추가 unbind/bind, rfkill write, link-up, scan/connect는 계속 금지
  - v221 결과가 `vendor-root-required`이므로 controlled CNSS start는 vendor root evidence 확보 전까지 blocked

### V215. ICNSS/CNSS Lifecycle Research — PASS

- 계획: `docs/plans/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_2026-05-13.md`
- 구현:
  - `scripts/revalidation/wifi_icnss_lifecycle_collect.py`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- 결과:
  - manifest-only: PASS, decision `lifecycle-map-ready`
  - native bridge read-only: PASS, decision `lifecycle-map-ready`
  - native live captures: `16/16`
  - service evidence: `51`
  - init evidence: `48`
  - firmware evidence: `28`
  - interface evidence: `133`
  - ICNSS evidence: `160`
  - QMI evidence: `17`
  - log evidence: `160`
- 해석:
  - Android lifecycle evidence plus v214 failure are sufficient for v216 service replay modeling
  - generic ICNSS unbind/bind, rfkill write, link-up, scan/connect remain blocked
- 다음 실행 항목:
  - v216 Android service replay model 계획서 작성
  - Android init rc service/class/property trigger를 native에서 실행하지 않고 dependency graph로 모델링

### V216. Android Service Replay Model — PASS

- 계획: `docs/plans/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_2026-05-13.md`
- 구현:
  - `scripts/revalidation/wifi_service_replay_model.py`
- 입력:
  - `tmp/wifi/v206-android-icnss-cnss-map/manifest.json`
  - `tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json`
  - `tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json`
- 결과:
  - PASS, decision `replay-model-ready`
  - output: `tmp/wifi/v216-service-replay-model`
  - service graph: `cnss-daemon`, `cnss_diag`, `vendor.wifi_hal_legacy`, `vendor.wifi_hal_ext`, `wificond`, `wpa_supplicant`, `hostapd`
- 해석:
  - first-class Android Wi-Fi/CNSS service chain is modeled without execution approval
  - `cnss-daemon`/`cnss_diag` 실행은 ICNSS recovery/debug inventory 전까지 blocked
  - Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect는 계속 blocked
- 다음 실행 항목:
  - v217 ICNSS debug/recovery inventory 계획서 작성
  - read-only로 ICNSS debugfs/sysfs/ramdump/recovery controls를 분류

### V217. ICNSS Debug / Recovery Inventory — PASS

- 계획: `docs/plans/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_2026-05-13.md`
- 목표:
  - v214에서 실패한 generic ICNSS `unbind`/`bind` 대신, driver-specific debug/recovery/status surface를 read-only로 분류
  - `cnss-daemon`/`cnss_diag` 실행 전 ICNSS recovery/debug controls의 위험도를 명확히 함
- 구현:
  - `scripts/revalidation/wifi_icnss_recovery_inventory.py`
- 입력:
  - `tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json`
  - `tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json`
  - `tmp/wifi/v216-service-replay-model/manifest.json`
- 산출물:
  - `tmp/wifi/v217-icnss-debug-recovery-inventory/manifest.json`
  - `tmp/wifi/v217-icnss-debug-recovery-inventory/controls.json`
  - `tmp/wifi/v217-icnss-debug-recovery-inventory/source-hints.json`
  - `tmp/wifi/v217-icnss-debug-recovery-inventory/summary.md`
- 결과:
  - manifest-only PASS, decision `state-only-inventory`
  - native bridge read-only PASS, decision `state-only-inventory`
  - native captures `11/11`
  - native controls `168`
  - native risk summary: `debug-state=1`, `ramdump-crash-evidence=11`, `read-only-state=146`, `writable-unknown=7`, `write-only-dangerous=3`
- 해석:
  - safe active recovery control은 아직 없음
  - ICNSS `bind`/`unbind`, `driver_override`는 denied dangerous controls
  - future CNSS execution experiment는 reboot를 유일하게 검증된 recovery path로 취급해야 함
- 금지:
  - ICNSS `unbind`/`bind`
  - ICNSS/debugfs/sysfs write
  - `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, supplicant, hostapd start
  - rfkill write, link-up, scan/connect
- 다음 실행 항목:
  - v218 CNSS daemon dry-run feasibility 계획서 작성
  - daemon 실행 없이 executable/library/mount/property/socket/device-node/capability requirements 조사

### V218. CNSS Daemon Dry-Run Feasibility — PASS

- 계획: `docs/plans/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_2026-05-13.md`
- 목표:
  - `cnss-daemon`/`cnss_diag` 실행 없이 executable, linker/library, mount alias, property/socket/device-node/capability requirements를 모델링
  - v219 native Android-env shim 계획으로 진행 가능한지 판정
- 구현:
  - `scripts/revalidation/wifi_cnss_daemon_dryrun.py`
- 입력:
  - `tmp/wifi/v210-vendor-asset-classifier/manifest.json`
  - `tmp/wifi/v216-service-replay-model/manifest.json`
  - `tmp/wifi/v217-icnss-debug-recovery-inventory/manifest.json`
  - `tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json`
- 산출물:
  - `tmp/wifi/v218-cnss-daemon-dryrun/manifest.json`
  - `tmp/wifi/v218-cnss-daemon-dryrun/daemon-dependencies.json`
  - `tmp/wifi/v218-cnss-daemon-dryrun/summary.md`
- 결과:
  - manifest-only PASS, decision `daemon-dryrun-partial`
  - native bridge read-only PASS, decision `daemon-dryrun-partial`
  - native captures `5/11` ok; `/vendor` and `/system/vendor` default paths are expected missing in native state
- 해석:
  - v210 기준 `cnss-daemon`/`cnss_diag` binary visibility는 확보
  - local host vendor root가 없어 ELF/library inspection은 incomplete
  - daemon execution은 여전히 blocked
- 금지:
  - `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, hostapd 실행
  - Android `ctl.start`/`class_start`
  - ICNSS sysfs/debugfs writes
  - rfkill write, link-up, scan/connect
- 다음 실행 항목:
  - v219 native Android-env shim plan 작성
  - mount visibility, path alias, property/socket/user/group/capability/log policy와 rollback/evidence policy 정의

### V219. Native Android-Env Shim Plan — PASS

- 계획: `docs/plans/NATIVE_INIT_V219_NATIVE_ANDROID_ENV_SHIM_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V219_NATIVE_ANDROID_ENV_SHIM_2026-05-13.md`
- 목표:
  - CNSS service experiment 전에 필요한 최소 Android-env shim 범위를 정의
  - mount/path alias, property/socket, user/group/capability, logging/evidence, recovery/rollback policy를 allow/deny list로 분리
- 구현:
  - `scripts/revalidation/wifi_android_env_shim_plan.py`
- 입력:
  - `tmp/wifi/v216-service-replay-model/manifest.json`
  - `tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json`
  - `tmp/wifi/v218-cnss-daemon-dryrun/manifest.json`
  - `tmp/wifi/v218-cnss-daemon-dryrun-native/manifest.json`
- 산출물:
  - `tmp/wifi/v219-native-android-env-shim/manifest.json`
  - `tmp/wifi/v219-native-android-env-shim/shim-matrix.json`
  - `tmp/wifi/v219-native-android-env-shim/summary.md`
- 결과:
  - PASS, decision `shim-plan-partial`
  - matrix: `available=3`, `shim-required=5`, `host-evidence-required=1`, `blocked=4`, `out-of-scope=1`
- 해석:
  - v220 gate input으로 사용할 bounded shim matrix 생성 완료
  - daemon execution은 승인하지 않음
  - property/QMI/recovery blocker와 host ELF/library evidence gap은 유지
- 금지:
  - daemon/service 실행
  - Android property mutation
  - binder/hwbinder service publication
  - writable vendor/system/data mount
  - Wi-Fi scan/connect
- 다음 실행 항목:
  - v220 Wi-Fi bring-up preflight gate v2 계획서 작성
  - v216-v219 evidence를 gate input으로 통합

### V220. Wi-Fi Bring-Up Preflight Gate v2 — PASS

- 계획: `docs/plans/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_2026-05-13.md`
- 목표:
  - v210-v219 evidence를 통합해 active Wi-Fi 준비 여부를 `go-scan-prep` 또는 `no-go`로 판정
  - static inventory만 보던 기존 gate를 lifecycle/recovery/shim/security-aware gate로 확장
- 구현:
  - `scripts/revalidation/wifi_bringup_gate_v2.py`
- 입력:
  - v210 vendor asset classifier
  - v211/v212 firmware path policy/rollback
  - v216 service replay model
  - v217 ICNSS debug/recovery inventory
  - v218 daemon dry-run model
  - v219 shim matrix
- 산출물:
  - `tmp/wifi/v220-bringup-gate-v2/manifest.json`
  - `tmp/wifi/v220-bringup-gate-v2/gate.json`
  - `tmp/wifi/v220-bringup-gate-v2/summary.md`
- 결과:
  - PASS, decision `no-go`
  - status counts: `pass=3`, `warn=1`, `fail=0`, `blocked=3`
  - blocked: `icnss_recovery`, `shim_policy`, `security_exposure`
  - warning: `daemon_dryrun`
- 해석:
  - `vendor_assets`, `firmware_path`, `service_replay`는 통과
  - reboot-only recovery, blocked shim items, pre-connect exposure/security review가 active Wi-Fi blocker로 남음
  - `no-go`는 정상 성공 결과이며 daemon 실행, rfkill write, link-up, scan/connect는 계속 blocked
- 다음 실행 항목:
  - v221은 controlled CNSS start가 아니라 host vendor ELF/library evidence closure와 recovery/security prerequisite closure로 진행
  - `cnss-daemon`/`cnss_diag` ELF/interpreter/DT_NEEDED/config/library path evidence를 먼저 닫는다

### V221. Host Vendor ELF / Library Evidence Closure — PASS

- 계획: `docs/plans/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_2026-05-13.md`
- 목표:
  - v218 blocker `elf-inspection-no-host-vendor-root`를 daemon 실행 없이 닫는다
  - `cnss-daemon`/`cnss_diag` ELF interpreter, `DT_NEEDED`, `DT_RPATH`, `DT_RUNPATH`, library path evidence를 수집한다
  - vendor root가 없으면 `vendor-root-required`를 PASS planning result로 출력하고 필요한 경로 checklist를 만든다
- 구현:
  - `scripts/revalidation/wifi_vendor_elf_library_closure.py`
- 입력:
  - v210 vendor asset classifier
  - v216 service replay model
  - v218 daemon dry-run model
  - v219 shim matrix
  - v220 bring-up gate v2
  - optional `--vendor-root`
- 산출물:
  - `tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json`
  - `tmp/wifi/v221-host-vendor-elf-library-evidence/elf-dependencies.json`
  - `tmp/wifi/v221-host-vendor-elf-library-evidence/summary.md`
- 결과:
  - PASS, decision `vendor-root-required`
  - `vendor_root_status=not-provided`
  - `visible_vendor_paths_count=47`
  - required paths: `<vendor-root>/bin/cnss-daemon`, `<vendor-root>/bin/cnss_diag`
- 해석:
  - v218 blocker가 정확히 host-visible vendor root 부재로 좁혀짐
  - daemon 실행은 승인되지 않음
  - 기존 v222 recovery/rollback policy hardening은 vendor root evidence 확보 후로 미룸
- 금지:
  - daemon 실행
  - Android service start
  - rfkill write, link-up, scan/connect
  - ICNSS/sysfs/debugfs writes
- 다음 실행 항목:
  - v222 vendor root evidence export/extraction 구현 완료
  - source vendor root 확보 후 v222 `--source-vendor-root`와 v221 `--vendor-root` 재실행

### V215-V225. Wi-Fi Big Plan — REFERENCE

- 큰 계획: `docs/plans/NATIVE_INIT_V215_V225_WIFI_BIG_PLAN_2026-05-13.md`
- 역할: v215-v225 Wi-Fi blocker closure의 버전별 목적, gate, stop condition을 한 화면에서 본다
- 상세 실행은 각 버전별 plan/report 문서를 기준으로 한다

### V222. Vendor Root Evidence Export / Extraction — PASS

- 계획: `docs/plans/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_2026-05-13.md`
- 구현: `scripts/revalidation/wifi_vendor_root_evidence_export.py`
- 결과:
  - decision `export-source-required`
  - no source-root 기본 실행 PASS
  - required paths: `<vendor-root>/bin/cnss-daemon`, `<vendor-root>/bin/cnss_diag`
  - private/no-follow output: `tmp/wifi/v222-vendor-root-evidence-export/manifest.json`, `export-plan.json`, `summary.md`
  - synthetic source-root export smoke PASS, final retained output은 plan-only `export-source-required`
- 금지 유지:
  - daemon 실행
  - writable vendor/system mount
  - full uncontrolled partition dump into world-readable path
  - Wi-Fi scan/connect
- 다음 실행 항목:
  - source vendor root 확보 후 v222 `--source-vendor-root` 실행
  - `vendor-root-ready`가 나오면 v221 `--vendor-root tmp/wifi/v222-vendor-root-evidence-export/vendor-root` 재실행
  - source 확보 전에는 v225 `still-no-go` 상태를 유지하고 active Wi-Fi는 금지


### V223. Recovery / Rollback Policy Hardening — PASS

- 계획: `docs/plans/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_2026-05-13.md`
- 구현: `scripts/revalidation/wifi_recovery_rollback_policy.py`
- 결과:
  - decision `reboot-recovery-accepted`
  - v214 post-reboot recovery evidence complete
  - v217 unsafe write count `10`
  - v220 `icnss_recovery` gate remains `blocked`
  - accepted primitive: native reboot only
  - denied: generic ICNSS unbind/bind, `driver_override`, unreviewed sysfs/debugfs/configfs writes
- 금지 유지:
  - live device command by default
  - reboot 실행
  - ICNSS sysfs/debugfs/configfs write
  - daemon 실행
  - rfkill write, link-up, scan/connect
- 다음 실행 항목:
  - v225 gate v3 결과가 `still-no-go`이므로 source vendor root 확보 후 v222/v221/v224/v225 순서 재검증
  - source 확보 전 active Wi-Fi는 금지


### V224. Android-Env Shim Dry-Run Materialization — PASS

- 계획: `docs/plans/NATIVE_INIT_V224_ANDROID_ENV_SHIM_DRYRUN_MATERIALIZATION_PLAN_2026-05-13.md`
- 보고서: `docs/reports/NATIVE_INIT_V224_ANDROID_ENV_SHIM_MATERIALIZE_2026-05-13.md`
- 구현: `scripts/revalidation/wifi_android_env_shim_materialize.py`
- 결과:
  - decision `shim-source-required`
  - host-side dry-run artifacts 생성 완료
  - v219 status counts: `available=3`, `blocked=4`, `host-evidence-required=1`, `out-of-scope=1`, `shim-required=5`
  - v219 `blocked` rows kept blocked
  - v223 reboot-only recovery policy hard dependency 기록
  - source vendor root blocker 유지
- 금지 유지:
  - daemon 실행
  - Android property mutation
  - QMI/PDR/SSR writes
  - binder/HAL publication
  - Wi-Fi credential path 접근
  - rfkill write, link-up, scan/connect
- 다음 실행 항목:
  - v225 Wi-Fi exposure/security gate + gate v3 구현
  - v225도 source vendor root blocker를 명시적으로 보존해야 함

### V225. Wi-Fi Exposure / Credential Security Gate v3 — PASS

- 계획: `docs/plans/NATIVE_INIT_V225_WIFI_EXPOSURE_SECURITY_GATE_V3_PLAN_2026-05-13.md`
- 구현: `scripts/revalidation/wifi_exposure_security_gate_v3.py`
- 산출: `tmp/wifi/v225-exposure-security-gate-v3/`
- 보고서: `docs/reports/NATIVE_INIT_V225_WIFI_EXPOSURE_SECURITY_GATE_V3_2026-05-13.md`
- 목표:
  - v220-v224 manifest를 통합해 gate v3 판정 생성
  - ACM/NCM/tcpctl/rshell/broker/netservice/future Wi-Fi exposure matrix 작성
  - credential/redaction/test-AP isolation policy를 Wi-Fi active plan 전에 고정
  - 현재 `vendor-root-required`, `export-source-required`, `shim-source-required`
    blocker를 닫지 않고 그대로 보존
- decision: `still-no-go`
- gate counts: `pass=4`, `warn=0`, `blocked=2`, `fail=0`
- blockers: `vendor_evidence`, `shim_materialization`
- 금지 유지:
  - live device command by default
  - daemon 실행
  - rfkill write, link-up, scan/connect
  - credential collection
  - listener bind broadening
  - firewall mutation
- 다음 실행 항목:
  - v226 live vendor-root export로 source blocker를 닫고 v222/v221/v224/v225 순서로 재검증

### V226. Native Vendor Root Live Export — PASS

- 계획: `docs/plans/NATIVE_INIT_V226_VENDOR_ROOT_LIVE_EXPORT_PLAN_2026-05-14.md`
- 보고서: `docs/reports/NATIVE_INIT_V226_VENDOR_ROOT_LIVE_EXPORT_2026-05-14.md`
- 구현: `scripts/revalidation/wifi_vendor_live_export.py`
- 산출: `tmp/wifi/v226-vendor-root-live-export/`
- 결과:
  - decision `vendor-source-exported`
  - live native `sda29` temporary mount: ext4 `ro,noload`
  - dynamic major/minor: `259:32`
  - cleanup: PASS, leftover mount 없음
  - pulled files: `22`, total `1405464` bytes
  - required binaries: `bin/cnss-daemon`, `bin/cnss_diag`
- 재검증:
  - v222: PASS, decision `vendor-root-ready`
  - v221: FAIL, decision `daemon-native-blocked`
  - v224: PASS, decision `shim-dryrun-ready`
  - v225: PASS, decision `still-no-go`, blocker `vendor_evidence`
- 남은 blocker:
  - `libcutils.so`
  - `libnl.so`
  - `libhardware_legacy.so`
- 금지 유지:
  - daemon 실행
  - writable vendor/system mount
  - rfkill write, link-up, scan/connect
  - credential collection
- 다음 실행 항목:
  - v227 Android core/system library evidence closure
  - v221 unresolved libraries가 해결되기 전 active Wi-Fi 작업 금지

### V227. Android Core/System Library Evidence Export — PASS

- 계획: `docs/plans/NATIVE_INIT_V227_ANDROID_CORE_SYSTEM_LIBRARY_EVIDENCE_PLAN_2026-05-14.md`
- 보고서: `docs/reports/NATIVE_INIT_V227_ANDROID_CORE_SYSTEM_LIBRARY_EVIDENCE_2026-05-14.md`
- 구현: `scripts/revalidation/wifi_android_core_library_export.py`
- 확장: `scripts/revalidation/wifi_vendor_elf_library_closure.py --system-root`
- 산출: `tmp/wifi/v227-android-core-system-library-evidence/`
- 결과:
  - v227: PASS, decision `system-root-ready`
  - v221: PASS, decision `elf-evidence-ready`
  - v224: PASS, decision `shim-dryrun-ready`
  - v225: PASS, decision `cnss-start-plan-approved`
- export libraries:
  - `libcutils.so`
  - `libnl.so`
  - `libhardware_legacy.so`
  - `android.system.suspend@1.0.so`
- 금지 유지:
  - daemon 실행
  - Android service start
  - rfkill write, link-up, scan/connect
  - credential collection
- 다음 실행 항목:
  - controlled CNSS start plan 작성
  - start-only 실험 전 recovery/timeout/exposure/rollback 정책 명시


### V228. Controlled CNSS Start-Only Experiment Plan — PASS

- 계획: `docs/plans/NATIVE_INIT_V228_CONTROLLED_CNSS_START_PLAN_2026-05-14.md`
- 보고서: `docs/reports/NATIVE_INIT_V228_CONTROLLED_CNSS_START_PLAN_2026-05-14.md`
- 구현: `scripts/revalidation/wifi_cnss_start_plan.py`
- 산출: `tmp/wifi/v228-controlled-cnss-start-plan/`
- decision: `cnss-start-plan-ready`
- 목표:
  - v225 `cnss-start-plan-approved` 이후 첫 controlled start-only 설계
  - v228에서는 daemon 실행 없이 command allowlist, runtime shim, timeout, stop/reap, reboot-only recovery, exposure boundary를 고정
  - active scan/connect/credential/routing/DHCP는 계속 금지
- 입력 증거:
  - v216 service replay model
  - v221 `elf-evidence-ready`
  - v222 `vendor-root-ready`
  - v223 `reboot-recovery-accepted`
  - v224 `shim-dryrun-ready`
  - v225 `cnss-start-plan-approved`
  - v227 `system-root-ready`
- 다음 실행 항목:
  - v229 controlled CNSS start planner/runner 구현
  - 실험 실행은 별도 explicit operator confirmation 이후에만 허용

### V229. Controlled CNSS Start-Only Runner — PREFLIGHT SAFE STOP

- 계획: `docs/plans/NATIVE_INIT_V229_CONTROLLED_CNSS_START_RUNNER_PLAN_2026-05-14.md`
- 보고서: `docs/reports/NATIVE_INIT_V229_CONTROLLED_CNSS_START_RUNNER_2026-05-15.md`
- 구현: `scripts/revalidation/wifi_cnss_start_experiment.py`
- 산출: `tmp/wifi/v229-controlled-cnss-start-experiment/`
- preflight 산출: `tmp/wifi/v229-controlled-cnss-start-experiment-preflight/`
- decision: `start-only-runtime-gap`
- 목표:
  - v228 `cnss-start-plan-ready`를 입력으로 opt-in host/device start-only runner를 구현한다
  - 기본 모드는 `plan`/`preflight`/`dry-run`이며 live daemon start는 `--allow-daemon-start --assume-yes` 없이는 실행하지 않는다
  - `cnss-daemon` start/observe/stop만 범위로 두고, `cnss_diag` phase2와 scan/connect/link-up/credential/DHCP/routing은 계속 금지한다
- 필수 경계:
  - v221/v222/v223/v224/v225/v227/v228 decision 재검증
  - Android runtime shim은 `/tmp/a90-v229-*` 같은 임시 경로만 사용
  - Android 동적 linker/interpreter가 실행 namespace에서 보이지 않으면 `start-only-runtime-gap`으로 중단
  - cleanup 실패 또는 ICNSS/WLAN state drift는 `start-only-reboot-required`로 기록하고 reboot-only recovery를 따른다
- 실기 결과:
  - bridge/cmdv1 `version` PASS, device `A90 Linux init 0.9.59 (v159)`
  - live daemon start 없음
  - command_count `29`, ok_count `23`
  - runtime gap: `/mnt/system/vendor/bin/cnss-daemon`, `/system/bin/linker64`, `/system/bin/toybox`, `/system/vendor/bin/cnss-daemon`
  - active Wi-Fi warning 없음
- 다음 실행 항목:
  - v230 temporary Android execution namespace/shim 계획
  - vendor source와 Android `/system` dynamic linker namespace를 임시/비영구 방식으로 노출한 뒤 v229 preflight 재실행

### V230. Temporary Android Execution Namespace Probe — LIVE INVENTORY PASS / RUNTIME GAP

- 계획: `docs/plans/NATIVE_INIT_V230_ANDROID_EXEC_NAMESPACE_PLAN_2026-05-15.md`
- 보고서: `docs/reports/NATIVE_INIT_V230_ANDROID_EXEC_NAMESPACE_PROBE_2026-05-15.md`
- 구현: `scripts/revalidation/wifi_android_exec_namespace_probe.py`
- 산출: `tmp/wifi/v230-android-exec-namespace-inventory-20260515-033554/`
- decision: `android-exec-namespace-runtime-gap`
- 목표:
  - v229 `start-only-runtime-gap`의 원인인 Android absolute path namespace gap을 안전하게 좁힌다
  - 먼저 `/system/vendor` 관계, `/linkerconfig`/`/apex` 필요성, live vendor source 상태, fresh v229 preflight 결과를 read-only inventory로 확정한다
  - 그 다음에만 `/system`, `/vendor`, `/system/vendor`, `/apex`, `/linkerconfig`를 temporary/private namespace 안에서 read-only로 보이게 하는 probe를 설계한다
  - `cnss-daemon` 실행은 하지 않고, 실행 전 필수 path/linkerconfig/vendor library visibility만 검증한다
- 구현 후보:
  - host tool: `scripts/revalidation/wifi_android_exec_namespace_probe.py`
  - 필요 시 device helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- guardrails:
  - default는 `plan`/`preflight`
  - 실제 temporary namespace mount probe는 `--allow-temp-namespace --assume-yes` 필요
  - no daemon execution, no scan/connect/link-up, no credential, no ICNSS unbind/bind, no persistent Android partition write
- 실기 결과:
  - fresh v229 preflight는 계속 `start-only-runtime-gap`
  - `/mnt/system/system/vendor -> /vendor`
  - vendor source는 `needs-remount`
  - APEX runtime은 available
  - 남은 blocker는 `linkerconfig-need-unproven`
  - post-inventory `version`, `netservice status`, `selftest verbose` PASS
- 다음 실행 항목:
  - `/linkerconfig` 필요성 입증 또는 documented absence 처리
  - v231 private namespace helper에서 vendor `sda29` ro,noload remount + `/system/vendor -> /vendor` 구성 설계

### V231. Linkerconfig Decision + Private Android Namespace Helper — HELPER EXECUTED / LINKERCONFIG BLOCKED

- 계획: `docs/plans/NATIVE_INIT_V231_LINKERCONFIG_NAMESPACE_HELPER_PLAN_2026-05-15.md`
- 보고서: `docs/reports/NATIVE_INIT_V231_LINKERCONFIG_NAMESPACE_HELPER_2026-05-15.md`
- 구현:
  - `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - `scripts/revalidation/build_android_execns_probe_helper.sh`
  - `scripts/revalidation/wifi_android_exec_namespace_probe.py`
  - `scripts/revalidation/helper_deploy.py`
- 산출:
  - `tmp/wifi/v231-plan-local-check/`
  - `tmp/wifi/v231-android-linker-list-probe-live/`
- decision: `android-namespace-manual-review-required`
- 상태:
  - local static ARM64 helper build PASS
  - host `plan` mode PASS
  - NCM helper deploy PASS
  - remote SHA256 PASS: `b200a8608eba661186650a93e380a5e2e0283090774f6cd44519913939316f86`
  - `/system/bin/linker64 --list /vendor/bin/cnss-daemon` 실기 실행까지 도달
  - private namespace setup은 `namespace-ready`
  - linker child는 stdout/stderr 없이 `SIGSEGV(11)` 종료
  - postflight `version/status/netservice/selftest` PASS, private mount leak 없음
- 목표:
  - v230의 `linkerconfig-need-unproven` blocker를 닫는다
  - device-side static helper `a90_android_execns_probe`로 private mount namespace를 만들고 global mount를 피한다
  - `/mnt/system/system`을 `/system`으로, vendor `sda29`를 `/vendor`로 private namespace 안에서 read-only 구성한다
  - `/system/vendor -> /vendor` symlink 관계를 보존한다
  - `cnss-daemon` 직접 실행 대신 `/system/bin/linker64 --list /vendor/bin/cnss-daemon`만 실행해 dependency/linkerconfig 판정을 한다
- guardrails:
  - no daemon entrypoint, no `cnss_diag`, no scan/connect/link-up, no credential, no ICNSS unbind/bind, no persistent Android write
  - `probe`는 `--allow-temp-namespace --allow-linker-list --assume-yes` 필요
  - helper와 host wrapper 모두 exact allowlist와 timeout/postflight 검증 필요
  - `/proc`는 `chroot` 이전에 `<root>/proc`로 private namespace 안에서 mount해야 한다
  - vendor `sda29`가 `needs-remount`이면 helper가 매번 private namespace 안에서 mount하고 reverse-order cleanup을 수행한다
  - `linker64 --list` stdout/stderr는 명시된 pattern priority로 `documented-absent|required|runtime-gap|manual-review` 중 하나로 분류한다
- 참고:
  - Android linker namespace와 linkerconfig는 vendor process dependency resolution에 직접 영향 가능
  - bionic linker `--list`는 ldd-like mode로 target entrypoint 이전에 종료하므로 v231 dry-run에 적합
- 다음 실행 항목:
  - v232 private-only linkerconfig materialization plan
  - `/mnt/system/linkerconfig` empty + `/system/etc/ld.config*.txt` absent 상태에서 linker namespace config를 어떻게 공급할지 설계
  - 계속 금지: daemon entrypoint, global mount, persistent Android write, Wi-Fi scan/connect/link-up

### V232. Private Linkerconfig Materialization Probe — EXECUTED / CRASH PERSISTS

- 계획: `docs/plans/NATIVE_INIT_V232_LINKERCONFIG_MATERIALIZATION_PLAN_2026-05-15.md`
- 보고서: `docs/reports/NATIVE_INIT_V232_LINKERCONFIG_MATERIALIZATION_2026-05-15.md`
- 입력:
  - v231 report `android-namespace-manual-review-required`
  - helper setup `namespace-ready`
  - linker child `SIGSEGV(11)`
  - `/mnt/system/linkerconfig` empty
  - `/mnt/system/system/etc/ld.config*.txt` absent
- 목표:
  - global mount나 Android partition write 없이 private root 안에만 `/linkerconfig/ld.config.txt`를 공급한다
  - real Android linkerconfig capture를 우선 경로로 두고, 불가하면 `minimal-vendor` synthetic config를 명시적으로 표시한다
  - 다시 `/system/bin/linker64 --list /vendor/bin/cnss-daemon`만 실행한다
- guardrails:
  - `--allow-private-linkerconfig` 같은 별도 opt-in 필요
  - no daemon entrypoint, no `cnss_diag`, no scan/connect/link-up, no credential
  - no global bind mount, no persistent Android write
  - `allow_all_shared_libs`는 별도 계획 전 금지
- 다음 실행 항목:
  - 구현: `a90_android_execns_probe v2`, `--linkerconfig-mode none|copy-real|minimal-vendor`
  - 배포: `/cache/bin/a90_android_execns_probe`, SHA256 `a4a56e6b1cc263602b143003c2807b0f896bbdd94c75d8bbd945776434b85e23`
  - 실기 결과: `minimal-vendor` private linkerconfig에서도 child `SIGSEGV(11)`, stdout/stderr empty
  - 비교 결과: `none` baseline도 child `SIGSEGV(11)`, no mount leak observed
  - 다음 후보: stock Android boot에서 real `/linkerconfig` capture 후 `copy-real` 재검증 또는 linker crash context 수집

### V233. Real Android Linkerconfig Copy-Real Probe — EXECUTED / CRASH PERSISTS

- 보고서: `docs/reports/NATIVE_INIT_V233_REAL_LINKERCONFIG_COPY_REAL_2026-05-15.md`
- stock Android capture:
  - boot image: `backups/baseline_a_20260423_025322/boot.img`
  - `/linkerconfig/ld.config.txt`: size `134256`, SHA256 `1ab340f0ee1e5f6d7c43e372dfe3bc9164d34b348dd9c716ded1b4e56e079f1a`
  - `/linkerconfig/apex.libraries.config.txt`: size `366`, SHA256 `5419adf6ed8f74c480d79096681a19a8570470ab8359c6e8c0be110da434f16e`
- native restore:
  - restored `stage3/boot_linux_v159.img`
  - `cmdv1 version/status` PASS, selftest `fail=0`
- copy-real probe:
  - source deployed temporarily as `/cache/bin/a90_real_ld.config.txt`, SHA256 verified, removed after probe
  - helper mode: `copy-real`
  - result: child `SIGSEGV(11)`, stdout/stderr empty, no mount leak observed
- conclusion:
  - real Android generated linkerconfig does not resolve the `linker64 --list` crash
  - next work should be linker crash-context comparison before any Wi-Fi daemon start

### V234. Linker Crash Context Comparison — EXECUTED / GENERIC LINKER CRASH

- 계획: `docs/plans/NATIVE_INIT_V234_LINKER_CRASH_CONTEXT_PLAN_2026-05-15.md`
- 보고서: `docs/reports/NATIVE_INIT_V234_LINKER_CRASH_CONTEXT_2026-05-15.md`
- 기준:
  - native device baseline remains `A90 Linux init 0.9.59 (v159)`
  - v234는 PID1 boot image 변경 없이 helper/host probe만 확장했다
  - v231 none, v232 minimal-vendor, v233 copy-real 모두 `linker64 --list /vendor/bin/cnss-daemon` child `SIGSEGV(11)`로 동일하게 실패했다
- 목표:
  - crash가 `cnss-daemon` target-specific인지, Android linker direct invocation/private namespace generic 문제인지 분리한다
  - target profile matrix와 debug env mode로 stdout/stderr blind spot을 줄였다
  - 결과: `system-toybox`, `system-sh`, `linker64-self`, `cnss-daemon` 모두 clean/ld-debug-1에서 child `SIGSEGV(11)`, stdout/stderr empty
  - decision: `android-linker-crash-generic`
- guardrails:
  - no daemon entrypoint, no Wi-Fi scan/connect/link-up, no credential/DHCP/routing
  - no global bind mount, no persistent Android partition write
  - no ptrace by default; ptrace/register/map capture는 v235 후보로 분리
- 다음 실행 항목:
  - 완료: helper v3 allowlisted target profiles, debug env modes, pre-exec context output
  - 완료: host wrapper `scripts/revalidation/wifi_linker_crash_context_probe.py`
  - 완료: v235 direct APEX linker invocation path 비교 구현 준비
  - 다음 후보: v235 live matrix 실행 후 direct APEX 결과에 따라 v236 bounded crash context capture 판단

### V235. Linker Invocation Path Comparison — EXECUTED / PATH-INDEPENDENT CRASH

- 계획: `docs/plans/NATIVE_INIT_V235_LINKER_INVOCATION_PATH_PLAN_2026-05-15.md`
- 보고서: `docs/reports/NATIVE_INIT_V235_LINKER_INVOCATION_PATH_2026-05-18.md`
- 기준:
  - native device baseline remains `A90 Linux init 0.9.59 (v159)`
  - v235는 PID1 boot image 변경 없이 helper/host probe만 확장했다
  - v234 decision은 `android-linker-crash-generic`
- 구현:
  - helper v4: `/system/bin/linker64`와 `/apex/com.android.runtime/bin/linker64` linker path allowlist
  - target profile 추가: `apex-linker64-self`
  - host wrapper 추가: `scripts/revalidation/wifi_linker_invocation_path_probe.py`
- 검증:
  - NCM ping PASS, helper v4 deploy PASS, real linkerconfig deploy PASS
  - matrix: 2 linker paths x 5 targets x 2 env modes = 20 cases
  - result: all cases child `SIGSEGV(11)`, stdout/stderr empty
  - decision: `android-linker-crash-path-independent`
  - cleanup: temporary real linkerconfig files removed and verified absent
  - final selftest: `pass=11 warn=1 fail=0`
- 다음 실행 항목:
  - 완료: v236 bounded crash context capture 계획/구현 착수
  - Wi-Fi daemon start remains blocked

### V236. Bounded Linker Crash Context Capture — EXECUTED / CONTEXT CAPTURED

- 계획: `docs/plans/NATIVE_INIT_V236_LINKER_CRASH_CAPTURE_PLAN_2026-05-18.md`
- 보고서: `docs/reports/NATIVE_INIT_V236_LINKER_CRASH_CAPTURE_2026-05-18.md`
- 기준:
  - native device baseline remains `A90 Linux init 0.9.59 (v159)`
  - v236는 PID1 boot image 변경 없이 helper/host probe만 확장했다
  - v235 decision은 `android-linker-crash-path-independent`
- 구현:
  - helper v5 `--capture-mode ptrace-lite`
  - self-child only ptrace, exec-stop/crash-stop bounded `/proc` context capture
  - host wrapper `scripts/revalidation/wifi_linker_crash_capture_probe.py`
- 검증:
  - helper static build PASS, Python compile PASS, plan smoke PASS
  - live matrix: 2 linker paths x 3 targets x 1 env = 6 cases
  - decision: `android-linker-crash-context-captured`
  - all cases: `SIGSEGV(11)`, `capture.exec_captured=true`, `capture.crash_captured=true`, `siginfo_signo=11`, `regset_bytes=272`
  - crash pattern: fault addr `0xa1`, linker64 PC file offset `0x1002f4`
  - cleanup: temporary real linkerconfig files removed and verified absent
  - final selftest: `pass=11 warn=1 fail=0`
- 다음 실행 항목:
  - v237 linker64 offset symbolization/disassembly or Android-vs-native process context comparison
  - Wi-Fi daemon start remains blocked

### V237. Linker Offset Symbolization — EXECUTED / EARLY ABORT SYMBOLIZED

- 계획: `docs/plans/NATIVE_INIT_V237_LINKER_OFFSET_SYMBOLIZATION_PLAN_2026-05-18.md`
- 보고서: `docs/reports/NATIVE_INIT_V237_LINKER_OFFSET_SYMBOLIZATION_2026-05-18.md`
- 기준:
  - native device baseline target remains `A90 Linux init 0.9.59 (v159)`
  - v237는 PID1 boot image 변경 없이 host-side evidence tooling만 추가했다
  - v236 decision은 `android-linker-crash-context-captured`
- 구현:
  - host wrapper `scripts/revalidation/wifi_linker_offset_symbolize.py`
  - v236 crash text parser: PC + linker64 maps 기반 file offset 계산
  - read-only linker64 pull: `mountsystem ro` + `toybox base64` from allowlisted path
  - host `readelf`/`objdump` section/symbol/disassembly analysis
- 검증:
  - Python compile PASS
  - plan smoke PASS
  - no-ELF analysis: v236 6-case evidence parsed, offset set = `0x1002f4`
  - local ELF smoke: section/disassembly machinery PASS against static helper binary
  - live pull/analyze PASS: decision `linker-offset-symbolized`
  - exported linker64 SHA-256 `ebd1db608558ccb01f851a4988abea2f2dd8844b7bc09e1847ebaf05e36a421d`, size `1816360`, BuildID `e8fdced9e7490875160097adfe101461`
  - offset `0x1002f4` -> `.text` / `__dl__ZL13__early_aborti+0x14` / `str wzr, [x8]`
- 해석:
  - crash is intentional bionic linker early-abort trap, not unknown arbitrary code execution
  - v236 fault address `0xa1` is the abort-code address written by `str wzr, [x8]`
- 다음 실행 항목:
  - 완료: v238 `__early_abort` call-site and abort-code mapping
  - 다음: v239 private namespace `/dev/null` materialization probe
  - Wi-Fi daemon start remains blocked

### V238. Linker Early-Abort Call-Site Map — EXECUTED / DEV NULL BLOCKER IDENTIFIED

- 계획: `docs/plans/NATIVE_INIT_V238_LINKER_EARLY_ABORT_MAP_PLAN_2026-05-18.md`
- 보고서: `docs/reports/NATIVE_INIT_V238_LINKER_EARLY_ABORT_MAP_2026-05-18.md`
- 기준:
  - native device baseline target remains `A90 Linux init 0.9.59 (v159)`
  - v238는 PID1 boot image 변경 없이 host-side ELF/disassembly tooling만 추가했다
  - v237 decision은 `linker-offset-symbolized`
- 구현:
  - host wrapper `scripts/revalidation/wifi_linker_early_abort_map.py`
  - local `linker64` full disassembly scan
  - all `__dl__ZL13__early_aborti` call-site extraction
  - backward `mov w0, #imm` abort-code recovery
  - captured fault address `0xa1` to caller correlation
- 검증:
  - Python compile PASS
  - plan smoke PASS
  - analyze PASS: decision `linker-early-abort-dev-null-open-failed`
  - selected caller: `0x1000b8` in `__dl__Z21__libc_init_AT_SECUREPPc+0xa0`
  - abort code: `0xa1` / `161`, loaded at `0x1000b4`
  - full call map: abort codes `0xa1`, `0xba`, `0xbd`, `0x14f`, `0xc4`
  - string correlation: `/dev/null`, `/sys/fs/selinux/null`, `failed to open /dev/null`, `__dl_libc_init_common.cpp`
- 해석:
  - v236/v237/v238 now point to bionic stdio nullification before normal linker execution
  - current blocker is missing null-device context inside the private Android execution namespace
  - problem remains generic linker process context, not `cnss-daemon` target-specific behavior
- 다음 실행 항목:
  - 완료: v239 private namespace `/dev/null` materialization probe
  - 다음: v240 `cnss-daemon` linker dependency/namespace gap classification
  - Wi-Fi daemon start remains blocked

### V239. Private Devnull Materialization Probe — EXECUTED / EARLY ABORT CLEARED

- 계획: `docs/plans/NATIVE_INIT_V239_PRIVATE_DEVNULL_PROBE_PLAN_2026-05-18.md`
- 보고서: `docs/reports/NATIVE_INIT_V239_PRIVATE_DEVNULL_PROBE_2026-05-18.md`
- 기준:
  - native device baseline target remains `A90 Linux init 0.9.59 (v159)`
  - v239는 PID1 boot image 변경 없이 helper/host probe만 확장했다
  - v238 decision은 `linker-early-abort-dev-null-open-failed`
- 구현:
  - `a90_android_execns_probe v6`
  - `--null-device-mode none|dev-null|dev-null-selinux`
  - private `<root>/dev/null` char device `1:3`, mode `0666`
  - host probe fault-address reporting and v239 classifier
- 검증:
  - helper static build PASS, SHA-256 `822608844d89ea8d888c7f16000256acc0dc9a2583d1a330c74f32c323fd6438`
  - helper deployed to `/cache/bin/a90_android_execns_probe`
  - real linkerconfig support files reinstalled from v233 evidence
  - live probe PASS: decision `android-linker-devnull-early-abort-cleared`
  - 6 selected matrix rows: no `SIGSEGV(11)`, no fault addr `0xa1`
  - `system-toybox` baseline linker-list PASS under both `/system/bin/linker64` and direct APEX linker invocation
- 해석:
  - v238 hypothesis is confirmed: missing private `/dev/null` caused the generic bionic early abort
  - `/sys/fs/selinux/null` fallback was not needed in this run
  - blocker moved to normal target dependency/namespace resolution for `cnss-daemon`
  - new blocker text: `library "libcutils.so" not found: needed by main executable`
- 다음 실행 항목:
  - 완료: v240 `cnss-daemon` linker namespace gap classification
  - 다음: v241 private VNDK APEX alias/materialization probe
  - compare `/apex/com.android.vndk.v30` -> `/apex/com.android.vndk.current` inside helper namespace only
  - Wi-Fi daemon start remains blocked

### V240. Linker Namespace Gap Classification — EXECUTED / VNDK APEX ALIAS GAP

- 계획: `docs/plans/NATIVE_INIT_V240_LINKER_NAMESPACE_GAP_PLAN_2026-05-18.md`
- 보고서: `docs/reports/NATIVE_INIT_V240_LINKER_NAMESPACE_GAP_2026-05-18.md`
- host tool: `scripts/revalidation/wifi_linker_namespace_gap_probe.py`
- 기준:
  - native device baseline target remains `A90 Linux init 0.9.59 (v159)`
  - v240는 PID1 boot image 변경 없이 host-side analysis/live read-only stat probe만 추가했다
  - v239 cleared `0xa1` early abort and exposed normal `libcutils.so` resolution failure for `cnss-daemon`
- 검증:
  - Python compile PASS
  - minimal-vendor cnss linker-list smoke PASS: both linker paths exit `0` and resolve system/vendor libraries
  - live v240 probe PASS: decision `android-linker-vndk-apex-version-alias-gap`
- 핵심 증거:
  - `/vendor/bin/cnss-daemon` maps to linkerconfig `[vendor]` section
  - `[vendor] namespace.default.links` includes `vndk`
  - `namespace.default.link.vndk.shared_libs` includes `libcutils.so`
  - `/mnt/system/system/apex/com.android.vndk.v30/lib64/libcutils.so` is absent
  - `/mnt/system/system/apex/com.android.vndk.current/lib64/libcutils.so` is present
- 해석:
  - current blocker is private namespace APEX path/version alias mismatch
  - real linkerconfig expects `/apex/com.android.vndk.v30`, while mounted system image exposes `com.android.vndk.current`
  - not a generic linker crash, not a missing `/system/lib64/libcutils.so`, and not the v238 `/dev/null` blocker
- 다음 실행 항목:
  - 완료: v241 private-only VNDK APEX alias/materialization probe
  - 다음: v242 controlled start-only runtime probe or runtime requirement inventory
  - Wi-Fi daemon start remains blocked until an explicit start-only plan is approved

### V241. Private VNDK APEX Alias Probe — EXECUTED / CNSS LINKER-LIST PASS

- 계획: `docs/plans/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_PLAN_2026-05-18.md`
- 보고서: `docs/reports/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_2026-05-18.md`
- 기준:
  - native device baseline target remains `A90 Linux init 0.9.59 (v159)`
  - v241는 PID1 boot image 변경 없이 helper/host probe만 확장했다
  - v240 decision은 `android-linker-vndk-apex-version-alias-gap`
- 구현:
  - `a90_android_execns_probe v7`
  - `--vndk-apex-alias-mode none|v30-to-current`
  - private `/apex` symlink farm with `com.android.vndk.v30 -> /system/apex/com.android.vndk.current`
  - host probe missing-library tracking and v241 classifier
- 검증:
  - helper static build PASS, SHA-256 `d6bd192b46cdeea93e8d0581335393d7101b3731a28cd441a1081e773329b2a4`
  - helper deployed to `/cache/bin/a90_android_execns_probe`
  - live probe PASS: decision `android-linker-vndk-apex-alias-cnss-list-pass`
  - `system-linker` and `apex-linker` both resolve `cnss-daemon` linker-list with child exit `0`, signal `0`, missing libs `[]`
  - postflight selftest PASS: `fail=0`
- 해석:
  - v240 blocker is closed inside a private namespace
  - `cnss-daemon` linker dependency graph can complete with real linkerconfig plus private VNDK APEX alias
  - this is not daemon start or Wi-Fi bring-up; runtime sockets/properties/device nodes/capabilities may still block start-only
- 다음 실행 항목:
  - 완료: v242 daemon runtime requirement inventory
  - 다음: v243 native launcher contract plan for bounded CNSS start-only
  - if start-only is selected later, keep it short-timeout, opt-in, no scan/connect, process-group cleanup
  - Wi-Fi scan/connect remains blocked

### V242. CNSS Runtime Requirement Inventory — EXECUTED / LAUNCHER CONTRACT NEEDED

- 계획: `docs/plans/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_PLAN_2026-05-18.md`
- 보고서: `docs/reports/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_2026-05-18.md`
- host tool: `scripts/revalidation/wifi_cnss_runtime_inventory.py`
- 기준:
  - native device baseline target remains `A90 Linux init 0.9.59 (v159)`
  - v242는 PID1 boot image 변경 없이 host-side live read-only inventory만 추가했다
  - v241 decision은 `android-linker-vndk-apex-alias-cnss-list-pass`
- 검증:
  - Python compile PASS
  - dry-run PASS
  - live inventory PASS: decision `cnss-runtime-inventory-ready-for-launcher-contract-plan`
  - 44 live read-only captures collected
- 핵심 증거:
  - `cnss-daemon` service contract: `/system/vendor/bin/cnss-daemon -n -l`, user `system`, groups `system,inet,net_admin,wifi`, capability `NET_ADMIN`
  - `cnss_diag` remains phase2-only because diagnostic device availability is not proven
  - helper, real linkerconfig, system linker, and v241 private VNDK APEX alias prerequisite are present
- 남은 blocker:
  - launcher identity/capability contract
  - Android property runtime gap
  - SELinux domain transition gap
  - `/dev/diag` and `/dev/qrtr` gaps
  - global `/system/vendor`/`/vendor` path alias gap outside private helper namespace
- 다음 실행 항목:
  - 완료: v243 native launcher contract plan for bounded CNSS start-only
  - 다음: v244 non-starting launcher dry-run and harmless identity/capability probe
  - Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked

### V243. CNSS Launcher Contract Plan — EXECUTED / IDENTITY-CAPABILITY PROBE NEXT

- 계획: `docs/plans/NATIVE_INIT_V243_CNSS_LAUNCHER_CONTRACT_PLAN_2026-05-18.md`
- 보고서: `docs/reports/NATIVE_INIT_V243_CNSS_LAUNCHER_CONTRACT_PLAN_2026-05-18.md`
- host tool: `scripts/revalidation/wifi_cnss_launcher_contract_plan.py`
- 기준:
  - v242 decision은 `cnss-runtime-inventory-ready-for-launcher-contract-plan`
  - v243는 PID1 boot image 변경 없이 host-side contract planner만 추가했다
  - daemon start는 계속 blocked
- 검증:
  - Python compile PASS
  - contract planner PASS: decision `cnss-launcher-contract-ready`
- 핵심 계약:
  - target: `/vendor/bin/cnss-daemon -n -l` inside private Android execution namespace
  - identity: uid/gid `system=1000`, supplemental groups `inet=3003`, `net_admin=3005`, `wifi=1010`
  - capability: `NET_ADMIN` / `CAP_NET_ADMIN`
  - required namespace: v241 private `/dev/null`, real linkerconfig, private VNDK APEX alias
- 다음 실행 항목:
  - 완료: v244 non-starting launcher dry-run and harmless identity/capability probe
  - first `cnss-daemon` start-only remains blocked until an explicit opt-in start-only runner is planned and approved

### V244. CNSS Identity / Capability Probe — EXECUTED / START-ONLY RUNNER NEXT

- 계획: `docs/plans/NATIVE_INIT_V244_CNSS_IDENTITY_PROBE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V244_CNSS_IDENTITY_PROBE_2026-05-19.md`
- host tool: `scripts/revalidation/wifi_cnss_identity_probe.py`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- 기준:
  - v243 decision은 `cnss-launcher-contract-ready`
  - v244는 PID1 boot image 변경 없이 helper/host probe만 확장했다
  - daemon start는 계속 blocked
- 구현:
  - `a90_android_execns_probe v8`
  - `--mode identity-probe`
  - private `/dev/null`, real linkerconfig, private read-only vendor mount
  - private bind-backed `/apex` farm plus `com.android.vndk.v30` alias
  - harmless child drops to uid/gid `system=1000`, groups `inet=3003/net_admin=3005/wifi=1010`, and `CAP_NET_ADMIN`
  - post-exec verification uses only `/system/bin/toybox cat /proc/self/status`
- 검증:
  - helper static build PASS, SHA-256 `4ce17edfdfe9935da8a320e5a570d301517d518d0ae1dcadaef8bafec7415647`
  - helper deployed to `/cache/bin/a90_android_execns_probe`
  - live probe PASS: decision `cnss-identity-probe-pass`
  - pre-exec uid/gid/groups/capability PASS
  - post-exec uid/gid/groups and `CapEff`/`CapPrm`/`CapAmb` include `CAP_NET_ADMIN`
- 해석:
  - launcher identity/capability prerequisite is closed on a harmless target
  - v241 symlink-only APEX farm is superseded by bind-backed APEX entries for dynamic exec
  - this is not daemon start or Wi-Fi bring-up
- 다음 실행 항목:
  - 완료: v245 controlled CNSS start-only runner plan/preflight/dry-run
  - 다음: v246 helper `cnss-start-only` mode implementation plan
  - keep start-only opt-in, short-timeout, no scan/connect, process-group cleanup, postflight, and reboot-only recovery policy
  - Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked

### V245. CNSS Start-Only Runner — SAFE PLAN/PREFLIGHT/DRY-RUN PASS

- 계획: `docs/plans/NATIVE_INIT_V245_CNSS_START_ONLY_RUNNER_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V245_CNSS_START_ONLY_RUNNER_2026-05-19.md`
- host tool: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- 기준:
  - v244 decision은 `cnss-identity-probe-pass`
  - v245는 PID1 boot image 변경 없이 host-side start-only runner safe modes만 추가했다
  - live daemon start는 실행하지 않았다
- 핵심 방향:
  - v229 `runandroid` path는 superseded
  - future runner는 v244 private Android execution namespace와 bind-backed `/apex` farm을 재사용
  - default subcommands는 `plan`, `preflight`, `dry-run` only
  - `run`은 `--allow-daemon-start --assume-yes --i-understand-reboot-only-recovery` 없이는 fail closed
- guardrails:
  - no scan/connect/link-up/credential/DHCP/routing
  - no `cnss_diag`
  - no rfkill unblock, `ip link set wlan* up`, `iw scan/connect`
  - no ICNSS generic bind/unbind or persistent Android partition write
- 다음 실행 항목:
  - 완료: v246 helper `cnss-start-only` mode implementation plan
  - 완료: v246 helper mode safe implementation
  - 다음: v247 actual start/observe/stop body plan, or explicit operator approval gate for first bounded live start-only attempt
  - live start-only run requires separate operator approval after reviewing v246 fail-closed evidence

### V246. CNSS Start-Only Helper Mode — SAFE GUARD PASS

- 계획: `docs/plans/NATIVE_INIT_V246_CNSS_START_ONLY_HELPER_MODE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V246_CNSS_START_ONLY_HELPER_MODE_2026-05-19.md`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- host tool: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- 기준:
  - v245 decision은 `preflight-ready`
  - v245 runner can build safe dry-run graph
  - v246 helper now exposes guarded `--mode cnss-start-only`
  - live daemon start remains blocked
- 핵심 방향:
  - helper mode `--mode cnss-start-only` 추가 완료
  - helper-level guard flag `--allow-cnss-start-only` 추가 완료
  - v244 private namespace, bind-backed `/apex`, identity/groups/capability contract 재사용
  - fixed daemon argv is surfaced as `/vendor/bin/cnss-daemon -n -l`
  - safe build emits stable `cnss_start.*` keys but does not execute daemon
- 검증:
  - helper SHA-256: `5ae105f0d397f845cd602eb4b283cdbd817146eff9405d10c090320eded25c65`
  - direct helper no-allow run: `cnss_start.result=start-only-blocked`
  - runner `plan`: `dry-run-ready` / PASS / daemon not executed
  - runner `preflight`: `preflight-ready` / PASS / daemon not executed
  - runner `dry-run`: `preflight-ready` / PASS / daemon not executed
  - runner `run` without live flags: `start-only-blocked` / expected fail-closed / daemon not executed
- 다음 실행 항목:
  - 완료: v247 actual helper start/observe/stop body design
  - 다음: v247 helper start/observe/stop body implementation with safe no-start validation first
  - live start-only execution remains a separate approval gate after safe evidence review
  - Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked

### V247. CNSS Start/Observe/Stop Body — SAFE BODY PASS / LIVE APPROVAL REQUIRED

- 계획: `docs/plans/NATIVE_INIT_V247_CNSS_START_OBSERVE_STOP_BODY_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V247_CNSS_START_OBSERVE_STOP_BODY_2026-05-19.md`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- host tool: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- 기준:
  - v246 decision은 `preflight-ready`
  - v246 helper supports guarded `--mode cnss-start-only`
  - v246 no-allow helper run returns `cnss_start.result=start-only-blocked`
  - host runner `plan`/`preflight`/`dry-run` are PASS and `run` without flags remains fail-closed
- 구현:
  - implement exactly one bounded `/vendor/bin/cnss-daemon -n -l` start/observe/stop body behind `--allow-cnss-start-only`
  - preserve v246 no-allow behavior
  - keep host runner non-starting by default
  - capture stable `cnss_start.*` lifecycle keys for host parsing
- 검증:
  - helper SHA-256: `77fbdcdcbc6774abe5e34712097496edbac4a4ed763d87c82cf02effb88cd319`
  - direct no-allow helper run: `cnss_start.result=start-only-blocked`
  - runner `plan`: `dry-run-ready` / PASS / daemon not executed
  - runner `preflight`: `preflight-ready` / PASS / daemon not executed
  - runner `dry-run`: `preflight-ready` / PASS / daemon not executed
  - runner `run` without flags: `start-only-blocked` / expected fail-closed / daemon not executed
  - `pidof cnss-daemon`: absent after safe validation
- guardrails:
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing
  - no `cnss_diag`
  - no rfkill unblock, `ip link set wlan* up`, `iw scan/connect`
  - no ICNSS bind/unbind, firmware mutation, persistent Android partition write, or automatic reboot
- 다음 실행 항목:
  - stop at `LIVE APPROVAL REQUIRED` before first daemon execution
  - if approved, run exactly one bounded v247 `run --allow-daemon-start --assume-yes --i-understand-reboot-only-recovery`
  - if not approved, plan v248 runtime primitive preflight/deeper evidence without daemon start

### V248. CNSS Runtime Primitive Preflight — PASS / LIVE APPROVAL STILL REQUIRED

- 계획: `docs/plans/NATIVE_INIT_V248_CNSS_RUNTIME_PRIMITIVE_PREFLIGHT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V248_CNSS_RUNTIME_PRIMITIVES_PREFLIGHT_2026-05-19.md`
- host tool: `scripts/revalidation/wifi_cnss_runtime_primitives_preflight.py`
- output: `tmp/wifi/v248-cnss-runtime-primitives-preflight/`
- decision: `cnss-runtime-primitives-ready-for-live-approval`
- daemon start: not executed
- 검증:
  - `python3 -m py_compile scripts/revalidation/wifi_cnss_runtime_primitives_preflight.py` PASS
  - `git diff --check` PASS
  - v242/v243/v244/v247 prerequisite gates PASS
  - helper SHA-256: `77fbdcdcbc6774abe5e34712097496edbac4a4ed763d87c82cf02effb88cd319`
  - helper no-allow path: `helper_status=namespace-ready`, `cnss_start.result=start-only-blocked`, `exec_attempted=0`
  - private namespace target: `/vendor/bin/cnss-daemon` exists and is executable inside helper namespace
  - no active `wlan*` in `/proc/net/dev`
  - `pidof cnss-daemon` returned rc=1 after validation
- runtime gaps:
  - property service socket missing
  - Android property area missing
  - SELinux null missing
  - `/dev/diag` missing
  - `/dev/qrtr` missing
  - global `/vendor` absent outside private helper namespace
- guardrails:
  - no `--allow-cnss-start-only`
  - no `cnss-daemon` or `cnss_diag` execution
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing
  - no rfkill unblock, ICNSS bind/unbind, firmware mutation, Android partition write, or reboot
- 다음 실행 항목:
  - first bounded live start-only operator approval review, or
  - continue no-start analysis for property/QRTR/SELinux runtime primitive gaps

### V249. CNSS Runtime Gap Classifier — PASS / LIVE APPROVAL STILL REQUIRED

- 계획: `docs/plans/NATIVE_INIT_V249_CNSS_RUNTIME_GAP_CLASSIFIER_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V249_CNSS_RUNTIME_GAP_CLASSIFIER_2026-05-19.md`
- host tool: `scripts/revalidation/wifi_cnss_runtime_gap_classifier.py`
- output: `tmp/wifi/v249-cnss-runtime-gap-classifier/`
- decision: `cnss-runtime-gaps-classified`
- daemon start: not executed
- 검증:
  - `python3 -m py_compile scripts/revalidation/wifi_cnss_runtime_gap_classifier.py` PASS
  - `git diff --check` PASS
  - v248 prerequisite PASS
  - required cmdv1 control captures PASS
  - `pidof cnss-daemon` returned rc=1 before/after validation
  - `QIPCRTR` present in `/proc/net/protocols`
  - helper no-allow `dev-null-selinux` variant reached `namespace-ready`
  - helper no-allow guard remained `cnss_start.result=start-only-blocked`, `exec_attempted=0`
  - private `/sys/fs/selinux/null` materialization PASS inside helper namespace
- gap classification:
  - property service/property area: Android-init-owned runtime gap; do not fake before a dedicated shim plan
  - SELinux null: helper-compatible private materialization, but no Android domain transition
  - QRTR: kernel family present; remaining risk is userspace nameservice/endpoint behavior
  - diag: still blocks `cnss_diag`, not necessarily primary start-only
  - init rc hints: reference-only; do not replay Android service manager in PID1
- guardrails:
  - no `--allow-cnss-start-only`
  - no `cnss-daemon` or `cnss_diag` execution
  - no property service emulation, scan/connect/link-up/credential/DHCP/routing
  - no ICNSS bind/unbind, firmware mutation, Android partition write, or reboot
- 다음 실행 항목:
  - if no live approval yet, plan no-start AF_QIPCRTR socket/nameservice probe
  - otherwise request explicit approval for exactly one bounded live start-only attempt

### V250. QRTR Socket No-Start Probe — PASS

- 계획: `docs/plans/NATIVE_INIT_V250_QRTR_SOCKET_PROBE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V250_QRTR_SOCKET_PROBE_2026-05-19.md`
- device helper: `stage3/linux_init/helpers/a90_qrtr_probe.c`
- host tool: `scripts/revalidation/wifi_qrtr_socket_probe.py`
- output: `tmp/wifi/v250-qrtr-socket-probe/`
- helper SHA-256: `92500fa51a7c910877d59b704210b915dfeed4abb0daca36d894b10f319be8a5`
- decision: `qrtr-socket-local-bind-pass`
- daemon start: not executed
- 검증:
  - `scripts/revalidation/build_qrtr_probe_helper.sh` PASS, static ARM64/no INTERP/no dynamic section
  - NCM/tcpctl deploy to `/cache/bin/a90_qrtr_probe` PASS
  - `python3 -m py_compile scripts/revalidation/wifi_qrtr_socket_probe.py` PASS
  - `git diff --check` PASS
  - `AF_QIPCRTR` socket open PASS (`domain=42`, `type=2`)
  - local ephemeral bind PASS (`node=1`, selected port `16424`)
  - helper reports `send_attempted=0`, `connect_attempted=0`
  - `pidof cnss-daemon` returned rc=1 after validation
- 해석:
  - QRTR is not blocked at kernel socket-family or local bind level
  - remaining QRTR risk is userspace nameservice/endpoint behavior
  - this still does not authorize Wi-Fi scan/connect/link-up
- 다음 실행 항목:
  - first bounded live start-only operator approval review, or
  - no-start QRTR nameservice visibility / property-read surface analysis

### V251. CNSS Property Surface — PASS

- 계획: `docs/plans/NATIVE_INIT_V251_CNSS_PROPERTY_SURFACE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V251_CNSS_PROPERTY_SURFACE_2026-05-19.md`
- host tool: `scripts/revalidation/wifi_cnss_property_surface.py`
- output: `tmp/wifi/v251-cnss-property-surface/`
- decision: `cnss-property-read-only-surface`
- device live command: none required
- daemon start: not executed
- 검증:
  - `python3 -m py_compile scripts/revalidation/wifi_cnss_property_surface.py` PASS
  - `git diff --check` PASS
  - host-only `file`/`readelf -Ws`/`strings -a` analysis PASS
  - input binary: `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`
- findings:
  - property read symbols: `property_get`, `property_get_int32`
  - property write/control symbols: none detected
  - detected property keys: `persist.vendor.cnss-daemon.debug_level`, `persist.vendor.cnss-daemon.hw_trc_disable_override`, `persist.vendor.cnss-daemon.kmsg_logging`, `ro.baseband`, `ro.board.platform`, `ro.vendor.extension_library`
- 해석:
  - property service/area gap is likely read/default risk, not a write/control-surface risk
  - `/data/vendor/wifi/sockets/...` strings are a separate runtime filesystem/socket surface
- 다음 실행 항목:
  - first bounded live start-only operator approval review, or
  - no-start `/data/vendor/wifi` socket path/runtime filesystem surface analysis

### V252. CNSS Data Wi-Fi Runtime Surface — PASS / SURFACE MISSING

- 계획: `docs/plans/NATIVE_INIT_V252_CNSS_DATA_WIFI_SURFACE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V252_CNSS_DATA_WIFI_SURFACE_2026-05-19.md`
- host tool: `scripts/revalidation/wifi_cnss_data_wifi_surface.py`
- output: `tmp/wifi/v252-cnss-data-wifi-surface/`
- decision: `cnss-data-wifi-surface-missing`
- daemon start: not executed
- 검증:
  - `python3 -m py_compile scripts/revalidation/wifi_cnss_data_wifi_surface.py` PASS
  - `git diff --check` PASS
  - v251 prerequisite PASS
  - current `/data` exists, but `/data/vendor`, `/data/vendor/wifi`, `/data/vendor/wifi/sockets` are missing
  - `pidof cnss-daemon` returned rc=1 after validation
- relevant strings:
  - `/data/vendor/wifi/sockets/cnss_user_client`
  - `/data/vendor/wifi/sockets/cnss_user_server`
  - `/data/vendor/wifi/wlfw_cal_%02d.bin`
  - `/data/vendor/wifi/qdss_trace*.bin`
- 해석:
  - runtime Wi-Fi data tree is a separate gap from property service and QRTR
  - no directory creation, userdata mount/remount, ownership/permission mutation was performed
- 다음 실행 항목:
  - first bounded live start-only operator approval review, or
  - no-mutation plan for private runtime directory materialization inside helper namespace

### V253. Private Data Wi-Fi Materialization — PASS

- 계획: `docs/plans/NATIVE_INIT_V253_PRIVATE_DATA_WIFI_MATERIALIZATION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V253_PRIVATE_DATA_WIFI_MATERIALIZATION_2026-05-19.md`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- host tool: `scripts/revalidation/wifi_cnss_private_data_wifi_probe.py`
- output: `tmp/wifi/v253-private-data-wifi-probe/`
- helper version: `a90_android_execns_probe v9`
- helper SHA-256: `80e8afb1b77fdba23dfbc71d6a8e17e5a2a095ed1de728474fd2855923c351a1`
- decision: `private-data-wifi-materialization-pass`
- daemon start: not executed
- 구현:
  - add `--data-wifi-mode none|private-empty`
  - print context uid/gid for helper paths
  - materialize private `/data/vendor/wifi/sockets` as `system:wifi` mode `0770`
- 검증:
  - helper static ARM64 build PASS
  - NCM/tcpctl deploy to `/cache/bin/a90_android_execns_probe` PASS
  - `py_compile` for dependent host tools PASS
  - `git diff --check` PASS
  - helper no-allow guard remains `cnss_start.result=start-only-blocked`, `exec_attempted=0`
  - real `/data/vendor/wifi` remains missing after validation
  - `pidof cnss-daemon` returned rc=1 after validation
- 다음 실행 항목:
  - update start-only runner dry-run plan to include `dev-null-selinux` + `private-empty` profile without running live daemon
  - first bounded live start-only still requires explicit operator approval

### V254. CNSS Start-Only Profile Refresh — PASS

- 계획: `docs/plans/NATIVE_INIT_V254_START_ONLY_PROFILE_REFRESH_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V254_START_ONLY_PROFILE_REFRESH_2026-05-19.md`
- host tool: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- output:
  - `tmp/wifi/v254-start-only-profile-plan/`
  - `tmp/wifi/v254-start-only-profile-preflight/`
  - `tmp/wifi/v254-start-only-profile-dryrun/`
  - `tmp/wifi/v254-start-only-profile-run-blocked/`
- decision: `start-only-profile-refresh-pass`
- device build: `A90 Linux init 0.9.59 (v159)`
- helper version: `a90_android_execns_probe v9`
- helper SHA-256: `80e8afb1b77fdba23dfbc71d6a8e17e5a2a095ed1de728474fd2855923c351a1`
- daemon start: not executed
- 구현:
  - runner default profile now uses `--null-device-mode dev-null-selinux`
  - runner default profile now uses `--data-wifi-mode private-empty`
  - dry-run manifest exposes `runtime_materialization`
- 검증:
  - `py_compile` PASS
  - `git diff --check` PASS
  - runner `plan` decision `dry-run-ready`
  - runner `preflight` decision `preflight-ready`
  - runner `dry-run` decision `preflight-ready`
  - default runner `run` remains `start-only-blocked` without approval
  - helper no-allow direct run keeps `cnss_start.result=start-only-blocked`, `exec_attempted=0`
  - `pidof cnss-daemon` returned rc=1 after validation
- 다음 실행 항목:
  - first bounded live start-only operator approval review, or
  - freeze the no-start live profile and rollback checklist before approval

### V255. CNSS Live Approval Packet — PASS / OPERATOR APPROVAL REQUIRED

- 계획: `docs/plans/NATIVE_INIT_V255_CNSS_LIVE_APPROVAL_PACKET_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V255_CNSS_LIVE_APPROVAL_PACKET_2026-05-19.md`
- host tool: `scripts/revalidation/wifi_cnss_live_approval_packet.py`
- output: `tmp/wifi/v255-cnss-live-approval-packet/`
- decision: `live-approval-packet-ready`
- device build: `A90 Linux init 0.9.59 (v159)`
- daemon start: not executed
- generated manual command:
  - `python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v255-cnss-live-start-only-run --max-runtime-sec 10 run --allow-daemon-start --assume-yes --i-understand-reboot-only-recovery`
- 검증:
  - `py_compile` PASS
  - `git diff --check` PASS
  - prerequisites matched `6/6`
  - runtime materialization profile PASS
  - approved helper argv includes `--allow-cnss-start-only`
  - denied pattern matches `[]`
  - no `wlan*` interface in `/proc/net/dev`
  - helper no-allow result `start-only-blocked`, `exec_attempted=false`, `postflight_safe=true`
  - `pidof cnss-daemon` rc=1 before and after no-allow helper validation
  - real `/data/vendor/wifi` state unchanged rc=-2 before/after
- 다음 실행 항목:
  - explicit operator approval for first bounded live start-only run, or
  - another no-start review if approval is not granted


### V256. CNSS Cleanup Race Fix — PASS / LIVE RETRY REQUIRES APPROVAL

- 계획: `docs/plans/NATIVE_INIT_V256_CNSS_CLEANUP_RACE_FIX_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V256_CNSS_CLEANUP_RACE_FIX_2026-05-19.md`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- host tools:
  - `scripts/revalidation/wifi_cnss_start_only_runner.py`
  - `scripts/revalidation/wifi_cnss_live_approval_packet.py`
- V255 live result: `manual-review-required`, helper killed by signal 15 before trusted markers
- recovery: manual `kill -TERM 5900`, then `pidof cnss-daemon` rc=1
- root cause: parent captured child pgid before child `setsid()`, so timeout cleanup could signal the helper/control process group and leave daemon child alive
- helper version: `a90_android_execns_probe v10`
- helper SHA-256: `1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750`
- 구현:
  - added wait for child session pgid before start-only cleanup
  - updated runner default helper SHA
  - updated live approval packet future output path to `tmp/wifi/v256-cnss-live-start-only-run`
- 검증:
  - static ARM64 helper build PASS
  - helper deploy to `/cache/bin/a90_android_execns_probe` PASS
  - direct helper no-allow v10 PASS: `start-only-blocked`, `exec_attempted=0`, `postflight_safe=1`
  - runner v10 `plan`/`preflight`/`dry-run` PASS
  - v10 approval packet PASS: `live-approval-packet-ready`
  - final `pidof cnss-daemon` rc=1
  - final `/proc/net/dev` has no `wlan*`
- 다음 실행 항목:
  - explicit operator approval for a v10 bounded live retry, or
  - no-start hardening of post-run analyzer before retry

### V257. CNSS V10 Bounded Live Retry — PASS

- 계획: `docs/plans/NATIVE_INIT_V257_CNSS_V10_LIVE_RETRY_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V257_CNSS_V10_LIVE_RETRY_2026-05-19.md`
- host tool: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- helper: `a90_android_execns_probe v10`
- helper SHA-256: `1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750`
- approval: explicit operator approval granted for exactly one bounded v10 retry
- live output: `tmp/wifi/v257-cnss-live-start-only-run/`
- decision: `start-only-pass`
- result:
  - `cnss_start.exec_attempted=1`
  - `cnss_start.child_started=1`
  - `cnss_start.pid=5965`
  - `cnss_start.pgid=5965`
  - `cnss_start.observable=1`
  - `cnss_start.reaped=1`
  - `cnss_start.postflight_safe=1`
  - `cnss_start.reason=observed-until-timeout-clean-stop`
- postflight:
  - `pidof cnss-daemon` rc=1
  - `/proc/net/dev` has no `wlan*`
  - `wifiinv full` reports `wlan_like=0`
  - `status` remains healthy; selftest fail=0
- 해석:
  - v10 cleanup race fix is validated by a real bounded daemon start/observe/stop.
  - This is not Wi-Fi scan/connect/link-up readiness.
- 다음 실행 항목:
  - analyze V257 captured CNSS runtime evidence for property/socket/device-node/QRTR blockers, or
  - build no-start post-run analyzer before any broader live operation

### V258. CNSS Live Evidence Analyzer — PASS

- 계획: `docs/plans/NATIVE_INIT_V258_CNSS_LIVE_EVIDENCE_ANALYZER_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V258_CNSS_LIVE_EVIDENCE_ANALYZER_2026-05-19.md`
- tool: `scripts/revalidation/wifi_cnss_live_evidence_analyzer.py`
- input: `tmp/wifi/v257-cnss-live-start-only-run/`
- output: `tmp/wifi/v258-cnss-live-evidence-analysis/`
- decision: `cnss-start-only-evidence-classified`
- checks: `11/11` PASS
- classified:
  - lifecycle: `start-only-pass`, `observable=1`, `reaped=1`, `postflight_safe=1`
  - identity: uid/gid `1000/1000`, groups `1010,3003,3005`, CAP_NET_ADMIN effective
  - namespace: required context paths present
  - mapped libs: `apex=12`, `system=6`, `vendor=8`, `target=1`, QMI/peripheral related libs `6`
  - postflight: no daemon, no `wlan*`, `wlan_like=0`
- runtime warnings:
  - `perfd-client-unavailable`
  - `kmsg-write-denied`
  - `shell-quote-noise`
- 다음 실행 항목:
  - V259 perfd/property/kmsg warning surface classification, or
  - QRTR/QMI socket/device-node interaction probe without scan/connect/link-up

### V259. CNSS Warning Surface Probe — PASS

- 계획: `docs/plans/NATIVE_INIT_V259_CNSS_WARNING_SURFACE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V259_CNSS_WARNING_SURFACE_2026-05-19.md`
- tool: `scripts/revalidation/wifi_cnss_warning_surface_probe.py`
- output: `tmp/wifi/v259-cnss-warning-surface/`
- decision: `cnss-warning-surface-classified`
- daemon execution: none
- critical checks:
  - v258 prerequisite PASS
  - `pidof cnss-daemon` rc=1
- findings:
  - `perfd-client-surface-present-socket-absent`
  - `property-service-socket-absent`
  - `property-area-absent`
  - `shell-quote-noise-not-helper-source`
- 해석:
  - V258 warnings are Android runtime service/logging gaps, not helper cleanup bugs.
  - V257 start-only lifecycle needed stronger process-table postflight because `pidof` can miss zombies.
- 다음 실행 항목:
  - V260 CNSS zombie postflight hardening before QRTR/QMI or another live retry

### V260. CNSS Zombie Postflight Hardening — TOOL PASS / LIVE BLOCKED

- 계획: `docs/plans/NATIVE_INIT_V260_CNSS_ZOMBIE_POSTFLIGHT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V260_CNSS_ZOMBIE_POSTFLIGHT_2026-05-19.md`
- tool: `scripts/revalidation/wifi_cnss_zombie_audit.py`
- outputs:
  - `tmp/wifi/v260-cnss-zombie-audit/`
  - `tmp/wifi/v260-runner-preflight-with-zombie/`
  - `tmp/wifi/v260-cnss-live-evidence-reclass-with-process-audit/`
- device action: read-only process/status audit only
- finding:
  - `pidof cnss-daemon` rc=1 is insufficient
  - `ps -A -o pid,stat,comm` shows `5900 Zs [cnss-daemon]`
  - `/proc/5900/status` confirms `State: Z (zombie)` and `PPid: 1`
- tool changes:
  - start-only runner now blocks preflight when CNSS target zombie/running residue exists
  - live evidence analyzer now marks post-process zombie evidence as critical failure
- decision:
  - no further live CNSS retry while target zombie residue exists
  - QRTR/QMI probing is deferred until clean-state validation or explicit blocker acceptance
- next execution item:
  - PID1 orphan/zombie reaper hardening, or
  - reboot/clean-state validation before QRTR/QMI endpoint probing

### V261. PID1 Orphan Reaper + CNSS Clean Live Retry — PASS

- 계획: `docs/plans/NATIVE_INIT_V261_PID1_ORPHAN_REAPER_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V261_PID1_ORPHAN_REAPER_2026-05-19.md`
- build: `A90 Linux init 0.9.60 (v261)`
- artifacts: `stage3/linux_init/init_v261`, `stage3/ramdisk_v261.cpio`, `stage3/boot_linux_v261.img`
- hashes:
  - init: `88d2212bfd0aa249381728da040d0601f47bce5deef63d774f70c950b04bc72a`
  - ramdisk: `1a38ccc156abb649ce03b72eb2e36c23e370840719d4808cdfe458807f643031`
  - boot: `5a314c2adbd5547b7de8b6dd76ba380e41a8dec61184166efda412389355a31e`
- validation:
  - real-device flash PASS
  - `version/status/selftest/pid1guard/reaper` PASS
  - post-flash CNSS zombie audit PASS: `cnss-process-clean`
  - explicit approval live retry PASS: `start-only-pass`, `reaped=1`, `postflight_safe=1`, CNSS process clean
- guardrails:
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing
  - no `cnss_diag`, rfkill unblock, ICNSS bind/unbind

### V262. QRTR/QMI No-Scan Probe — PASS

- 계획: `docs/plans/NATIVE_INIT_V262_QRTR_QMI_NO_SCAN_PROBE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V262_QRTR_QMI_NO_SCAN_PROBE_2026-05-19.md`
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- boot image change: 없음
- host tool: `scripts/revalidation/wifi_qrtr_qmi_no_scan_probe.py`
- output: `tmp/wifi/v262-qrtr-qmi-no-scan-probe/`
- decision: `qrtr-qmi-no-scan-ready`
- validation:
  - required captures PASS
  - CNSS process clean PASS
  - `QIPCRTR` present in `/proc/net/protocols`
  - `/cache/bin/a90_qrtr_probe` SHA PASS
  - QRTR helper `socket.rc=0`, `status=bind-pass`, `send_attempted=0`, `connect_attempted=0`
  - no `wlan*` in `/proc/net/dev` or `/sys/class/net`
- interpretation:
  - QRTR kernel socket/local bind remains ready
  - visible `/dev` QRTR/QMI/diag/IPA/WLAN nodes remain absent
  - remaining gap is userspace/runtime endpoint or nameservice behavior, not basic QRTR socket availability
### V263. CNSS Warning Disposition — PASS

- 계획: `docs/plans/NATIVE_INIT_V263_CNSS_WARNING_DISPOSITION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V263_CNSS_WARNING_DISPOSITION_2026-05-19.md`
- baseline evidence: `tmp/wifi/v261-cnss-live-evidence-analysis-final-20260519-085902/manifest.json`
- approved retry evidence: `tmp/wifi/v263-cnss-live-retry-20260519-091608/`
- boot image change: 없음
- host tool: `scripts/revalidation/wifi_cnss_warning_disposition.py`
- output: `tmp/wifi/v263-cnss-warning-disposition/`
- decision: `cnss-warning-disposition-ready`
- validation:
  - analysis-pass PASS
  - warning-surface PASS
  - post CNSS process audit PASS: `cnss-process-clean`
  - approved bounded live retry PASS: `start-only-pass`
  - retry postflight PASS: `cnss-process-clean`, evidence analyzer PASS, warning disposition PASS
- dispositions:
  - `perfd-client-unavailable`: accepted for start-only, broader-Wi-Fi runtime service gap
  - `kmsg-write-denied`: accepted for start-only, private namespace logging gap
  - `shell-quote-noise`: coalesced with kmsg logging-path stderr noise
- next execution item:
  - QRTR/QMI userspace nameservice model with packet transmission still approval-gated, or
  - opt-in kmsg/perfd shim design without execution

### V264. QRTR/QMI Userspace Nameservice Model — PASS

- 계획: `docs/plans/NATIVE_INIT_V264_QRTR_QMI_NAMESERVICE_MODEL_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V264_QRTR_QMI_NAMESERVICE_MODEL_2026-05-19.md`
- baseline evidence: `tmp/wifi/v262-qrtr-qmi-no-scan-probe/manifest.json`
- warning evidence: `tmp/wifi/v263-cnss-live-retry-20260519-091608/warning-disposition/manifest.json`
- boot image change: 없음
- daemon start: 없음
- QRTR/QMI packet transmission: 없음
- host tool: `scripts/revalidation/wifi_qrtr_qmi_nameservice_model.py`
- output: `tmp/wifi/v264-qrtr-qmi-nameservice-model/`
- decision: `qrtr-qmi-userspace-model-ready`
- validation:
  - v262 no-scan manifest PASS
  - `QIPCRTR` kernel protocol + AF_QIPCRTR bind readiness PASS
  - prior QRTR send/connect attempt count `0`
  - CNSS process clean PASS
  - no `wlan*` link surface PASS
  - v263 warning disposition PASS
- interpretation:
  - QRTR socket readiness is necessary but not sufficient for Wi-Fi bring-up
  - actual QRTR nameservice packet or QMI service request remains explicit-approval-gated
  - `cnss_diag`, scan/connect/link-up, credentials, DHCP, and routing remain blocked
- next execution item:
  - QRTR nameservice packet design document without execution, or
  - opt-in perfd/property/kmsg shim design without execution, or
  - bounded QRTR nameservice no-scan probe only after explicit packet-transmission approval

### V265. QRTR Nameservice Approval Contract — PASS

- 계획: `docs/plans/NATIVE_INIT_V265_QRTR_NAMESERVICE_APPROVAL_CONTRACT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V265_QRTR_NAMESERVICE_APPROVAL_CONTRACT_2026-05-19.md`
- baseline input: `tmp/wifi/v264-qrtr-qmi-nameservice-model/manifest.json`
- boot image change: 없음
- daemon start: 없음
- QRTR/QMI packet transmission: 없음
- host tool: `scripts/revalidation/wifi_qrtr_nameservice_approval_contract.py`
- output: `tmp/wifi/v265-qrtr-nameservice-approval-contract/`
- decision: `qrtr-nameservice-approval-contract-ready`
- validation:
  - v264 model prerequisite PASS
  - future command template includes `--allow-qrtr-ns-transmit`, `--assume-yes`, and `--i-understand-qrtr-packet-transmission`
  - wildcard lookup blocked by default
  - QMI payload and Wi-Fi link actions blocked
  - no bridge/device execution in v265
- interpretation:
  - v265 is the last safe non-transmit step before QRTR nameservice probing
  - future runner can be designed next, but actual QRTR packet transmission needs explicit user approval
  - QMI service request, `cnss_diag`, scan/connect/link-up, credentials, DHCP, and routing remain blocked
- next execution item:
  - request explicit approval for bounded QRTR nameservice no-scan runner design/run, or
  - choose a non-transmit alternative such as opt-in perfd/property/kmsg shim design

### V266. QRTR Nameservice Runner Skeleton — PASS

- 계획: `docs/plans/NATIVE_INIT_V266_QRTR_NAMESERVICE_RUNNER_SKELETON_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V266_QRTR_NAMESERVICE_RUNNER_SKELETON_2026-05-19.md`
- baseline input: `tmp/wifi/v264-qrtr-qmi-nameservice-model/manifest.json`
- boot image change: 없음
- daemon start: 없음
- QRTR/QMI packet transmission: 구현 안 됨, 실행 안 됨
- host tool: `scripts/revalidation/wifi_qrtr_nameservice_runner.py`
- output: `tmp/wifi/v266-qrtr-nameservice-runner-skeleton/`
- validation:
  - `plan`: decision `qrtr-ns-runner-plan-ready`, PASS
  - `preflight`: decision `qrtr-ns-runner-preflight-ready`, PASS
  - `run` without approval: decision `qrtr-ns-runner-fail-closed`, PASS
  - `run` with approval flags: decision `qrtr-ns-runner-transmit-not-implemented`, exit 1
- interpretation:
  - runner command surface now exists
  - read-only bridge preflight passes
  - no-approval run is fail-closed
  - even with approval flags, v266 cannot transmit because no helper exists
- next execution item:
  - v267 transmit-capable helper design without execution, or
  - explicit approval for bounded `QRTR_TYPE_NEW_LOOKUP` no-scan implementation/run after design review

### V267. QRTR Nameservice Packet Layout — PASS

- 계획: `docs/plans/NATIVE_INIT_V267_QRTR_PACKET_LAYOUT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V267_QRTR_PACKET_LAYOUT_2026-05-19.md`
- boot image change: 없음
- daemon start: 없음
- QRTR/QMI packet transmission: 없음
- host tool: `scripts/revalidation/wifi_qrtr_nameservice_packet_layout.py`
- output: `tmp/wifi/v267-qrtr-packet-layout/`
- decision: `qrtr-packet-layout-ready`
- validation:
  - `QRTR_TYPE_NEW_LOOKUP` command value `10` PASS
  - `QRTR_TYPE_DEL_LOOKUP` command value `11` PASS
  - packet length `20` bytes PASS
  - service/instance little-endian field layout PASS
  - wildcard lookup blocked by default PASS
  - wildcard regression `service=0 instance=0` returned `qrtr-packet-layout-blocked`, exit 1
- packet bytes:
  - NEW_LOOKUP: `0a00000001000000010000000000000000000000`
  - DEL_LOOKUP: `0b00000001000000010000000000000000000000`
- interpretation:
  - helper code review에 필요한 bytes/offsets are fixed
  - actual QRTR nameservice transmission remains explicit-approval-gated
- next execution item:
  - v268 transmit-capable helper source/design without deployment/execution, or
  - explicit approval request for bounded QRTR nameservice no-scan transmission after design review

### V268. QRTR Nameservice Helper Source — PASS

- 계획: `docs/plans/NATIVE_INIT_V268_QRTR_NS_HELPER_SOURCE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V268_QRTR_NS_HELPER_SOURCE_2026-05-19.md`
- boot image change: 없음
- helper deployment: 없음
- helper execution: 없음
- QRTR/QMI packet transmission: 없음
- helper source: `stage3/linux_init/helpers/a90_qrtr_ns_probe.c`
- build script: `scripts/revalidation/build_qrtr_ns_probe_helper.sh`
- build output: `tmp/wifi/v268-build/a90_qrtr_ns_probe`
- sha256: `c2d8707155b776c6c31e815136a66060f2087c4606c8a48cf9bd4b7944fdbb2a`
- validation:
  - static ARM64 build PASS
  - no `INTERP` PASS
  - no dynamic section PASS
  - marker strings PASS: `a90_qrtr_ns_probe v1`, `--allow-qrtr-ns-transmit`, `qrtr_ns.send_attempted=0`
  - helper source defaults to blocked/no-send without approval flag
- interpretation:
  - transmit-capable source exists for review
  - helper was not deployed or executed
  - actual QRTR nameservice transmission remains explicit-approval-gated
- next execution item:
  - v269 runner integration for approval-gated deploy/run path without execution, or
  - explicit approval to deploy and run one bounded nameservice lookup

### V269. QRTR Nameservice Live Retry — PASS

- 계획: `docs/plans/NATIVE_INIT_V269_QRTR_NAMESERVICE_LIVE_RETRY_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V269_QRTR_NAMESERVICE_LIVE_RETRY_2026-05-19.md`
- boot image change: 없음
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- runner: `scripts/revalidation/wifi_qrtr_nameservice_runner.py`
- helper device path: `/cache/bin/a90_qrtr_ns_probe`
- helper sha256: `c2d8707155b776c6c31e815136a66060f2087c4606c8a48cf9bd4b7944fdbb2a`
- live evidence: `tmp/wifi/v269-qrtr-nameservice-live-retry6-20260519-102134/`
- validation:
  - `plan` non-transmit PASS
  - `preflight` non-transmit PASS
  - no-approval `run` fail-closed PASS
  - approved `run` PASS: `qrtr-ns-runner-lookup-sent`
  - helper deploy PASS via short-lived host HTTP + device `toybox wget`
  - helper hash check PASS
- live result:
  - `QRTR_TYPE_NEW_LOOKUP` sent: service `1`, instance `1`
  - `QRTR_TYPE_DEL_LOOKUP` cleanup sent: service `1`, instance `1`
  - `qrtr_ns.status=lookup-sent`
  - `qrtr_ns.send_attempted=1`
  - `qrtr_ns.qmi_attempted=0`
- guardrails:
  - no QMI payload
  - no Wi-Fi scan/connect/link-up
  - no `cnss-daemon`/`cnss_diag`/HAL/supplicant/wificond/hostapd start
  - no rfkill, ICNSS, firmware, Android partition, property, perfd, kmsg, DHCP, or routing mutation
- interpretation:
  - QRTR nameservice lookup/delete packet path works under explicit approval
  - no `cnss-daemon` process or `wlan*` link surface appeared after the run
  - remaining Wi-Fi blocker is endpoint/service visibility and possible QMI-control discovery, not basic QRTR nameservice send ability
- next execution item:
  - v270 QRTR endpoint/service visibility classifier, or
  - v270 QMI-control discovery plan with separate explicit approval gate

### V270. QRTR Nameservice Readback — PASS

- 계획: `docs/plans/NATIVE_INIT_V270_QRTR_NAMESERVICE_READBACK_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V270_QRTR_NAMESERVICE_READBACK_2026-05-19.md`
- boot image change: 없음
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- helper source: `stage3/linux_init/helpers/a90_qrtr_ns_probe.c`
- runner: `scripts/revalidation/wifi_qrtr_nameservice_runner.py`
- helper device path: `/cache/bin/a90_qrtr_ns_probe`
- helper sha256: `375c30c21e5715218698a67832bf31d8052be95d4933d2ab98c198d73a45076a`
- live evidence:
  - `tmp/wifi/v270-qrtr-ns-readback-live-20260519-103623/`
  - `tmp/wifi/v270-qrtr-ns-readback-live-long-20260519-103732/`
- validation:
  - static ARM64 helper build PASS
  - `plan` non-transmit PASS
  - `preflight` non-transmit PASS
  - no-approval `run` fail-closed PASS
  - approved 1s readback PASS: `qrtr-ns-readback-timeout`
  - approved 3s readback PASS: `qrtr-ns-readback-timeout`
- live result:
  - `QRTR_TYPE_NEW_LOOKUP` sent: service `1`, instance `1`
  - `QRTR_TYPE_DEL_LOOKUP` cleanup sent: service `1`, instance `1`
  - `qrtr_ns.qmi_attempted=0`
  - readback events: `0`
  - readback service events: `0`
  - readback end-of-list marker: `0`
  - readback timeout: `1`
- interpretation:
  - QRTR nameservice control send works, but no service notification returned for service `1` instance `1`
  - selected service/instance is not enough evidence for a visible Wi-Fi control endpoint
  - next step should select/correlate service IDs before any QMI-control payload plan
- guardrails:
  - no QMI payload
  - no Wi-Fi scan/connect/link-up
  - no `cnss-daemon`/`cnss_diag`/HAL/supplicant/wificond/hostapd start
  - no rfkill, ICNSS, firmware, Android partition, property, perfd, kmsg, DHCP, or routing mutation
- next execution item:
  - v271 QRTR service/instance selection and evidence correlation plan

### V271. QRTR Service Selector — PASS

- 계획: `docs/plans/NATIVE_INIT_V271_QRTR_SERVICE_SELECTOR_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V271_QRTR_SERVICE_SELECTOR_2026-05-19.md`
- boot image change: 없음
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_qrtr_service_selector.py`
- evidence: `tmp/wifi/v271-qrtr-service-selector/`
- validation:
  - host-only analyzer PASS: `qrtr-service-selector-ready`
  - v270 primary/long readback evidence recognized as service `1`, instance `1`, zero events, `qmi_attempted=0`
  - `cnss-daemon` QMI client imports PASS
  - DMS service object evidence PASS
  - WLFW string evidence PASS
  - `qmi_idl_get_service_id` helper evidence PASS
- interpretation:
  - service `1`, instance `1` is negative/weak because both v270 readback windows returned zero events
  - DMS is the strongest exported service-object-backed candidate
  - WLFW is Wi-Fi-specific but unresolved because current evidence does not show an exported service object symbol
  - next step should extract numeric service ids from real service objects before another live QRTR lookup or any QMI-control payload plan
- guardrails:
  - no QRTR socket opened
  - no QRTR nameservice packet sent
  - no QMI payload sent
  - no device command executed
  - no Wi-Fi scan/connect/link-up or daemon start
- next execution item:
  - v272 QMI service-object ID extractor plan without QMI payloads

### V272. QMI Service Object Extractor — PASS

- 계획: `docs/plans/NATIVE_INIT_V272_QMI_SERVICE_OBJECT_EXTRACTOR_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V272_QMI_SERVICE_OBJECT_EXTRACTOR_2026-05-19.md`
- boot image change: 없음
- device command: 없음
- QRTR/QMI packet transmission: 없음
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_qmi_service_object_extractor.py`
- evidence: `tmp/wifi/v272-qmi-service-object-extractor/`
- validation:
  - host-only ELF parser PASS: `qmi-service-object-ids-extracted`
  - extracted service object count: `37`
  - DMS service id extracted: `2`
  - service id `1` maps to WDS
  - WLFW exported service object remains absent/unresolved
- interpretation:
  - v269/v270 service `1`, instance `1` was not a useful Wi-Fi firmware-control selector; it maps to WDS in vendor evidence
  - DMS is resolved and can be used for a future nameservice visibility matrix if explicitly approved
  - WLFW remains the Wi-Fi-specific unresolved candidate and needs source/blob symbol location
- guardrails:
  - no Android code execution
  - no device command executed
  - no QRTR socket opened
  - no QRTR nameservice packet sent
  - no QMI payload sent
  - no Wi-Fi scan/connect/link-up or daemon start
- next execution item:
  - v273 explicit-approval QRTR nameservice readback matrix for known service ids, or
  - v273 WLFW service-object locator

### V273. QRTR Readback Matrix — PASS

- 계획: `docs/plans/NATIVE_INIT_V273_QRTR_READBACK_MATRIX_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V273_QRTR_READBACK_MATRIX_2026-05-19.md`
- boot image change: 없음
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_qrtr_readback_matrix.py`
- helper: `/cache/bin/a90_qrtr_ns_probe`
- helper sha256: `375c30c21e5715218698a67832bf31d8052be95d4933d2ab98c198d73a45076a`
- live evidence: `tmp/wifi/v273-qrtr-readback-matrix-live-20260519-110229/`
- validation:
  - plan mode PASS, no packet transmission
  - preflight PASS: `qrtr-readback-matrix-preflight-ready`
  - approved live matrix PASS: `qrtr-readback-matrix-timeout`
  - postflight PASS: shell responsive, `cnss-daemon` absent, no `wlan*`
- matrix:
  - WDS service `1`, instance `0`: timeout, events `0`, `qmi_attempted=0`
  - WDS service `1`, instance `1`: timeout, events `0`, `qmi_attempted=0`
  - DMS service `2`, instance `0`: timeout, events `0`, `qmi_attempted=0`
  - DMS service `2`, instance `1`: timeout, events `0`, `qmi_attempted=0`
- interpretation:
  - evidence-based DMS/WDS nameservice visibility still produced no QRTR service notifications
  - remaining blocker is likely CNSS/runtime endpoint registration or unresolved WLFW service-object identity
  - this result does not justify QMI payloads
- guardrails:
  - no QMI payload
  - no Wi-Fi scan/connect/link-up or daemon start
  - service id `0` global wildcard blocked
- next execution item:
  - v274 WLFW service-object locator

### V274. WLFW Service Locator — PASS

- 계획: `docs/plans/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_2026-05-19.md`
- boot image change: 없음
- device command: 없음
- packet transmission: 없음
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_wlfw_service_locator.py`
- evidence: `tmp/wifi/v274-wlfw-service-locator/`
- validation:
  - host-only locator PASS: `wlfw-service-id-source-backed`
  - WLFW service id: `69` / `0x45`
  - WLFW service version: `1`
  - local `cnss-daemon` WLFW string coverage PASS
  - local exported WLFW service object remains absent/unresolved
- interpretation:
  - WLFW is now a concrete Wi-Fi-specific service-id candidate
  - WDS/DMS readback timeout does not close the WLFW path
  - next live step can be a bounded WLFW QRTR nameservice readback matrix, still no QMI payload
- guardrails:
  - no Android code execution
  - no device command executed
  - no QRTR socket opened
  - no QRTR nameservice packet sent
  - no QMI payload sent
  - no Wi-Fi scan/connect/link-up or daemon start
- next execution item:
  - v275 explicit-approval WLFW QRTR nameservice readback matrix

### V275. WLFW QRTR Readback — PASS

- 계획: `docs/plans/NATIVE_INIT_V275_WLFW_QRTR_READBACK_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V275_WLFW_QRTR_READBACK_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_qrtr_readback_matrix.py`
- helper: `/cache/bin/a90_qrtr_ns_probe`
- live evidence: `tmp/wifi/v275-wlfw-qrtr-readback-live-20260519-111529/`
- decision: `qrtr-readback-matrix-timeout`
- result:
  - WLFW service `69` instance `0`: timeout, events `0`, service_events `0`, qmi_attempted `0`
  - WLFW service `69` instance `1`: timeout, events `0`, service_events `0`, qmi_attempted `0`
- interpretation:
  - source-backed WLFW service id did not produce QRTR nameservice notifications in current native state
  - WDS/DMS/WLFW all timing out points toward runtime endpoint registration or CNSS/platform state, not only service-id selection
  - QMI request payloads remain blocked
- safety:
  - only QRTR nameservice `NEW_LOOKUP` plus cleanup `DEL_LOOKUP` packets were sent
  - no QMI payload, daemon start, scan/connect/link-up, credentials, DHCP, routing, rfkill write, ICNSS bind/unbind, firmware mutation, partition write, or reboot
- next:
  - v276 QRTR/CNSS registration-state correlation plan before any QMI payload consideration

### V276. QRTR/CNSS Registration Correlation — PASS

- 계획: `docs/plans/NATIVE_INIT_V276_QRTR_CNSS_REGISTRATION_CORRELATION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V276_QRTR_CNSS_REGISTRATION_CORRELATION_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_qrtr_cnss_registration_correlator.py`
- evidence: `tmp/wifi/v276-qrtr-cnss-registration-correlation/`
- decision: `qrtr-cnss-platform-surface-visible`
- result:
  - QIPCRTR protocol present
  - no-send QRTR probe `bind-pass`, socket rc `0`, send/connect attempted `0`
  - v273 WDS/DMS and v275 WLFW nameservice readback evidence all timeout with events `0` and qmi_attempted `0`
  - `/dev` QRTR/QMI/CNSS/WLAN/DIAG/IPA matches `0`
  - `/sys` QRTR/QMI/CNSS/WLAN/ICNSS matches `68`
  - `cnss-daemon`/`cnss_diag` process table clean and no `wlan*` interface
- interpretation:
  - QRTR socket readiness is not the blocker
  - static CNSS/WLAN/QRTR platform surfaces are present, but no active QRTR service notification is visible in native state
  - QMI payloads remain blocked
- safety:
  - no packet transmission, no daemon start, no scan/connect/link-up, no rfkill/ICNSS write, no partition write, no reboot
- next:
  - v277 ICNSS/CNSS platform surface classifier with read-only sysfs/devicetree probes

### V277. ICNSS/CNSS Platform Surface — PASS

- 계획: `docs/plans/NATIVE_INIT_V277_ICNSS_PLATFORM_SURFACE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V277_ICNSS_PLATFORM_SURFACE_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_icnss_platform_surface_classifier.py`
- evidence: `tmp/wifi/v277-icnss-platform-surface/`
- decision: `icnss-platform-present-no-wlan-netdev`
- result:
  - ICNSS platform node/driver/driver-device present
  - QCA6390 platform node present, driver link absent
  - `/sys/module/wlan` present, `wlan` absent from `/proc/modules`
  - firmware path `/vendor/firmware_mnt/image`
  - no `wlan*` netdev, wiphy, or Wi-Fi rfkill readiness surface
- interpretation:
  - platform description is present, but WLAN interface registration is still absent
  - next blocker is likely QCA6390/platform-driver lifecycle or userspace runtime sequencing
  - QMI payloads remain blocked
- safety:
  - no sysfs write, no bind/unbind/driver_override, no packet, no daemon, no scan/connect/link-up, no reboot/remount
- next:
  - v278 QCA6390 driver/bus and WLAN module parameter read-only classifier

### V278. QCA6390 Driver / WLAN Parameter — PASS

- 계획: `docs/plans/NATIVE_INIT_V278_QCA6390_DRIVER_PARAM_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V278_QCA6390_DRIVER_PARAM_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_qca6390_driver_param_classifier.py`
- evidence: `tmp/wifi/v278-qca6390-driver-param/`
- decision: `qca6390-match-visible-driver-unbound`
- result:
  - QCA6390 compatible/modalias visible: `qcom,cnss-qca6390`
  - QCA6390 driver link absent
  - platform driver candidates: `ipa_smmu_wlan`, `icnss`, `icnss/18800000.qcom,icnss`
  - WLAN module parameters `9/9` readable: `fwpath` empty, `country_code=(null)`, `con_mode=0`
  - no `wlan*` netdev, wiphy, or Wi-Fi rfkill readiness surface
- interpretation:
  - concrete QCA6390 OF match is visible but unbound in current native state
  - next step should be no-start source/evidence comparison or explicit-approval start-only delta observation, still no scan/connect/link-up
  - QMI payloads remain blocked
- safety:
  - no sysfs write, no bind/unbind/driver_override, no packet, no daemon, no scan/connect/link-up, no reboot/remount
- next:
  - v279 CNSS/QCA6390 probe-expectation comparison or start-only delta observation plan

### V279. CNSS QCA6390 Start-Only Delta — PASS

- 계획: `docs/plans/NATIVE_INIT_V279_CNSS_QCA6390_START_DELTA_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V279_CNSS_QCA6390_START_DELTA_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_cnss_qca6390_start_delta_observer.py`
- evidence: `tmp/wifi/v279-cnss-qca6390-start-delta-live-20260519-114525/`
- decision: `cnss-qca6390-no-driver-delta`
- result:
  - guarded CNSS start-only runner PASS: `start-only-pass`
  - QCA6390 driver link absent before and after
  - WLAN params unchanged: `fwpath` empty, `country_code=(null)`, `con_mode=0`
  - no `wlan*` netdev, wiphy, or Wi-Fi rfkill before/after
  - postflight `cnss-daemon` absent
- interpretation:
  - bounded `cnss-daemon -n -l` start-only alone does not bind QCA6390 or change WLAN module/runtime parameter state
  - next blocker is likely platform-driver lifecycle, probe expectation, or missing runtime control/event path rather than basic daemon execution
  - QMI payloads remain blocked
- safety:
  - no QRTR nameservice packet, no QMI payload, no scan/connect/link-up, no rfkill/ICNSS write, no partition write, no reboot
- next:
  - v280 no-start CNSS/QCA6390 source/sysfs expectation comparison, or read-only kernel log extraction if accessible

### V280. CNSS/QCA6390 Probe Expectation — PASS

- 계획: `docs/plans/NATIVE_INIT_V280_CNSS_QCA6390_PROBE_EXPECTATION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V280_CNSS_QCA6390_PROBE_EXPECTATION_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_cnss_qca6390_probe_expectation.py`
- evidence: `tmp/wifi/v280-cnss-qca6390-probe-expectation/`
- decision: `cnss2-driver-dir-missing-qca-unbound`
- result:
  - QCA6390 compatible/modalias visible: `qcom,cnss-qca6390`
  - QCA6390 driver link absent
  - `/sys/bus/platform/drivers/cnss2` absent
  - `/sys/bus/platform/drivers/icnss` present
  - kernel config sample: `CONFIG_CNSS2=n`, `CONFIG_CNSS_QCA6390=n`, `CONFIG_WLAN=y`, `CONFIG_QCA_CLD_WLAN=y`
  - `/sys/kernel/cnss` absent, `/sys/kernel/shutdown_wlan` present
  - no `wlan*` netdev, wiphy, or CNSS process
- interpretation:
  - CNSS2 source model is not the live kernel binding model on this device
  - repeating userspace `cnss-daemon` start-only is unlikely to bind QCA6390 by itself
  - next blocker is the live `icnss` platform-driver model and why QCA6390 remains a separate unbound node
- safety:
  - no daemon start, no QRTR nameservice packet, no QMI payload, no scan/connect/link-up, no sysfs/control write, no reboot/remount
- next:
  - v281 ICNSS source/sysfs expectation comparison, read-only first

### V281. ICNSS Probe Expectation — PASS

- 계획: `docs/plans/NATIVE_INIT_V281_ICNSS_PROBE_EXPECTATION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V281_ICNSS_PROBE_EXPECTATION_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_icnss_probe_expectation.py`
- evidence: `tmp/wifi/v281-icnss-probe-expectation/`
- decision: `icnss-core-bound-host-driver-waits-fw`
- result:
  - ICNSS compatible visible: `qcom,icnss`
  - ICNSS driver-device link present
  - QCA6390 context visible but QCA6390 driver link absent
  - WLAN module sysfs present, `wlan` absent from `/proc/modules`
  - config sample: `CONFIG_ICNSS=y`, `CONFIG_ICNSS_QMI=y`, `CONFIG_WLAN=y`, `CONFIG_QCA_CLD_WLAN=y`, `CONFIG_CNSS2=n`
  - WLAN params: `fwpath=""`, `con_mode=0`
  - ICNSS params: `quirks=128`, `dynamic_feature_mask=1`
  - no `wlan*` netdev, wiphy, or CNSS process
- interpretation:
  - live model is ICNSS core plus WLAN host-driver registration, not direct CNSS2/QCA6390 platform-driver binding
  - host-driver probe likely waits on firmware-ready/QMI state; repeating generic start-only is not enough evidence
  - next work should target ICNSS/WLFW readiness state surfaces
- safety:
  - no daemon start, no QRTR nameservice packet, no QMI payload, no scan/connect/link-up, no sysfs/control write, no reboot/remount
- next:
  - v282 ICNSS/WLFW readiness-state observation plan, no-start first

### V282. ICNSS/WLFW Readiness Surface — PASS

- 계획: `docs/plans/NATIVE_INIT_V282_ICNSS_WLFW_READINESS_SURFACE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V282_ICNSS_WLFW_READINESS_SURFACE_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_icnss_wlfw_readiness_surface.py`
- evidence: `tmp/wifi/v282-icnss-wlfw-readiness-surface/`
- decision: `icnss-readiness-sysfs-candidates-limited`
- result:
  - ICNSS core driver-device link present
  - WLAN module sysfs present, but no `wlan*`, no wiphy, no target CNSS process
  - `CONFIG_DEBUG_FS=y`, `CONFIG_ICNSS_DEBUG=n`
  - debugfs is not mounted and `/sys/kernel/debug/icnss` is absent
  - `/sys/kernel/shutdown_wlan` present but not readable
  - ICNSS/WLFW readiness dmesg lines: `0`
- scope:
  - no-start, read-only ICNSS/WLFW readiness-state surface observer
  - existing sysfs/debugfs names only; no debugfs mount by default
  - filtered kernel log history for `fw_ready`, `wlfw`, `qmi`, and driver probe messages
- safety:
  - no daemon start, no QRTR nameservice packet, no QMI payload, no scan/connect/link-up, no sysfs/debugfs/control write, no reboot/remount
- next:
  - v283 bounded start-only readiness-delta observer, reusing the validated start-only primitive while capturing before/during/after ICNSS/WLFW/QMI state

### V283. ICNSS/WLFW Start-Only Delta — PASS

- 계획: `docs/plans/NATIVE_INIT_V283_ICNSS_WLFW_START_DELTA_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V283_ICNSS_WLFW_START_DELTA_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_icnss_wlfw_start_delta_observer.py`
- evidence: `tmp/wifi/v283-icnss-wlfw-start-delta-live-20260519-123206/`
- decision: `icnss-wlfw-start-no-readiness-delta`
- result:
  - nested start-only runner decision: `start-only-pass`
  - helper result: `start-only-pass`
  - child pid/pgid observed: `1077` / `1077`
  - process group reaped and postflight safe
  - dmesg readiness lines: `0 -> 0`
  - sysfs readiness candidates: `13 -> 13`
  - debugfs readiness candidates: `0 -> 0`
  - no `wlan*`, no wiphy, no target CNSS process after run
- interpretation:
  - bounded `cnss-daemon -n -l` alone does not expose ICNSS/WLFW readiness state
  - repeating the same serial-only test is unlikely to add evidence
  - next work needs a concurrent side-channel if live during-start sampling is required
- safety:
  - no QRTR nameservice packet from observer, no direct QMI payload, no scan/connect/link-up, no rfkill/ICNSS bind/unbind/debugfs write, no reboot/remount
- next:
  - v284 CNSS concurrent side-channel observer feasibility using NCM/tcpctl or harness broker, still read-only during sampling

### V284. CNSS Concurrent Side-Channel Observer — PASS

- 계획: `docs/plans/NATIVE_INIT_V284_CNSS_CONCURRENT_SIDECHANNEL_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V284_CNSS_CONCURRENT_SIDECHANNEL_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py`
- evidence: `tmp/wifi/v284-cnss-concurrent-sidechannel-live-20260519-130404/`
- decision: `cnss-sidechannel-no-readiness-delta`
- result:
  - serial ACM ran one bounded CNSS start-only helper command
  - NCM/tcpctl completed 12 concurrent read-only sample cycles while serial was busy
  - helper result `start-only-pass`, child pid/pgid `1258/1258`, reaped, postflight clean
  - readiness line count `0`, no `wlan*`, no wiphy, no CNSS process leak
  - temporary `/bin/a90_tcpctl` alias and `netservice` were cleaned up
- safety:
  - no QMI payload, no QRTR nameservice packet, no scan/connect/link-up, no credential/DHCP/routing
  - no rfkill write, no ICNSS bind/unbind, no reboot/recovery/poweroff
- next:
  - v285 ICNSS/QCA6390 focused during-start sampler using the proven v284 side-channel pattern

### V285. ICNSS/QCA6390 Focused During-Start Sampler — PASS

- 계획: `docs/plans/NATIVE_INIT_V285_ICNSS_QCA6390_DURING_START_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V285_ICNSS_QCA6390_DURING_START_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_icnss_qca6390_during_start_sampler.py`
- evidence: `tmp/wifi/v285-icnss-qca6390-during-start-live-20260519-132119/`
- decision: `icnss-qca6390-focused-no-during-delta`
- result:
  - serial ACM ran one bounded CNSS start-only helper command
  - NCM/tcpctl completed 19 focused samples around/during the serial run
  - helper result `start-only-pass`, child pid/pgid `1731/1731`, reaped, postflight clean
  - focused delta count `0`, new focus line count `0`
  - no `wlan*`, no wiphy, no CNSS process leak
  - temporary `/bin/a90_tcpctl` alias and `netservice` were cleaned up
- interpretation:
  - generic side-channel and focused ICNSS/QCA6390 sampling both show no start-only readiness delta
  - repeating the same bounded `cnss-daemon -n -l` run is unlikely to add evidence
  - next work should compare Android/TWRP/native ICNSS boot timing before any QMI payload experiment
- safety:
  - no QMI payload, no QRTR nameservice packet, no scan/connect/link-up, no credential/DHCP/routing
  - no rfkill write, no ICNSS bind/unbind, no debugfs mount, no reboot/recovery/poweroff
- next:
  - v286 Android/TWRP/native ICNSS boot-log timing comparison

### V286. ICNSS Boot Timing Compare — PASS

- 계획: `docs/plans/NATIVE_INIT_V286_ICNSS_BOOT_TIMING_COMPARE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V286_ICNSS_BOOT_TIMING_COMPARE_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_icnss_boot_timing_compare.py`
- evidence: `tmp/wifi/v286-icnss-boot-timing-native-20260519-133421/`
- decision: `icnss-boot-timing-gap-mapped`
- result:
  - existing Android/TWRP Wi-Fi evidence parsed
  - current native dmesg/netdev/wiphy/rfkill/module/process evidence collected read-only
  - native version matched `A90 Linux init 0.9.60 (v261)`
  - Android event count `195`, TWRP event count `3`, native event count `132`
  - native boot-window filter excludes prior start-only residual dmesg entries
  - first missing native event: `android_wifi_action`
- interpretation:
  - Android reaches Wi-Fi service ordering and WLFW/QMI readiness around `7s..15s`
  - native lacks Android Wi-Fi service ordering in boot-window evidence
  - next work should model service-order replay before any QMI payload or link-up probe
- safety:
  - no daemon execution, no QMI payload, no QRTR nameservice packet
  - no scan/connect/link-up, no credential/DHCP/routing, no rfkill/ICNSS writes
- next:
  - v287 Android Wi-Fi service-order replay plan

### V287. Wi-Fi Service-Order Replay Model — PASS

- 계획: `docs/plans/NATIVE_INIT_V287_WIFI_SERVICE_ORDER_REPLAY_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V287_WIFI_SERVICE_ORDER_REPLAY_MODEL_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_service_order_replay_model.py`
- evidence: `tmp/wifi/v287-wifi-service-order-replay-model/`
- decision: `wifi-service-order-replay-model-ready`
- result:
  - v216 Android service graph, v228 CNSS start plan, v286 timing comparison merged
  - replay stages mapped from Android timing evidence
  - first missing native boundary: `vendor.wifi_hal_ext`
  - `cnss-daemon` remains the only bounded start-only candidate, but v287 executed nothing
  - Wi-Fi HALs, `cnss_diag`, `wificond`, `wpa_supplicant`, and `hostapd` remain blocked
- safety:
  - no device command execution, no service start, no QMI/QRTR payload
  - no scan/connect/link-up, no credential/DHCP/routing, no rfkill/ICNSS writes
- next:
  - v288 HAL/framework boundary inventory before any HAL or `wificond` execution

### V288. HAL / Framework Boundary Inventory — PASS

- 계획: `docs/plans/NATIVE_INIT_V288_HAL_FRAMEWORK_BOUNDARY_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V288_HAL_FRAMEWORK_BOUNDARY_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_hal_framework_boundary_inventory.py`
- evidence:
  - `tmp/wifi/v288-hal-framework-boundary-plan/`
  - `tmp/wifi/v288-hal-framework-boundary-live-20260519-135154/`
- decision: `hal-framework-boundary-native-blocked`
- result:
  - Android HAL service metadata, VINTF Wi-Fi evidence, HAL process domains, and Android Wi-Fi socket surfaces are present
  - native `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` are absent
  - native `servicemanager`/`hwservicemanager`/`vndservicemanager` processes are absent
  - native property runtime socket/area is absent
  - native `wificond` and service-manager binaries may be visible through mounted system, but that is not execution readiness
- safety:
  - no service execution, no QMI/QRTR payload, no scan/connect/link-up, no rfkill/ICNSS writes
  - `mountsystem ro` used only as read-only visibility step
- next:
  - v289 Binder / service-manager feasibility inventory

### V289. Binder / Service-Manager Feasibility Inventory — PASS

- 계획: `docs/plans/NATIVE_INIT_V289_BINDER_SERVICE_MANAGER_FEASIBILITY_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V289_BINDER_SERVICE_MANAGER_FEASIBILITY_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_binder_service_manager_feasibility.py`
- evidence:
  - `tmp/wifi/v289-binder-service-manager-plan/`
  - `tmp/wifi/v289-binder-service-manager-live-20260519-135726/`
- decision: `binder-kernel-present-devnodes-missing`
- result:
  - `CONFIG_ANDROID_BINDER_IPC=y`
  - `CONFIG_ANDROID_BINDER_DEVICES=binder,hwbinder,vndbinder`
  - Binder misc devices are registered in `/proc/misc`
  - native `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` are absent
  - `CONFIG_ANDROID_BINDERFS=n` and binderfs is absent from `/proc/filesystems`
  - service-manager binaries are visible through read-only mounted system, but service-manager processes are absent
- safety:
  - no `mknod`, no binderfs mount, no Binder ioctl, no service-manager execution
  - no Wi-Fi daemon execution, no QMI/QRTR payload, no scan/connect/link-up
- next:
  - v290 private Binder devnode feasibility plan before any service-manager/HAL execution

### V290. Binder Devnode Feasibility Inventory — PASS

- 계획: `docs/plans/NATIVE_INIT_V290_BINDER_DEVNODE_FEASIBILITY_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V290_BINDER_DEVNODE_FEASIBILITY_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_binder_devnode_feasibility.py`
- evidence:
  - `tmp/wifi/v290-binder-devnode-plan/`
  - `tmp/wifi/v290-binder-devnode-live-20260519-140441/`
- decision: `binder-devnode-plan-ready`
- result:
  - `/sys/class/misc/binder/dev` and `/proc/misc` agree on `10:81`
  - `/sys/class/misc/hwbinder/dev` and `/proc/misc` agree on `10:80`
  - `/sys/class/misc/vndbinder/dev` and `/proc/misc` agree on `10:79`
  - native `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` remain absent
  - non-executed candidates were emitted:
    - `mknod -m 0600 /dev/binder c 10 81`
    - `mknod -m 0600 /dev/hwbinder c 10 80`
    - `mknod -m 0600 /dev/vndbinder c 10 79`
- safety:
  - no `mknod`, no Binder ioctl/open smoke, no service-manager execution
  - no Wi-Fi daemon execution, no QMI/QRTR payload, no scan/connect/link-up
- next:
  - v291 temporary Binder devnode create/cleanup smoke, with explicit approval because it is non-read-only

### V291. Binder Devnode Create/Cleanup Smoke — PASS

- 계획: `docs/plans/NATIVE_INIT_V291_BINDER_DEVNODE_SMOKE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V291_BINDER_DEVNODE_SMOKE_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_binder_devnode_smoke.py`
- evidence:
  - `tmp/wifi/v291-binder-devnode-smoke-plan/`
  - `tmp/wifi/v291-binder-devnode-smoke-live-20260519-140937/`
- decision: `binder-devnode-create-cleanup-pass`
- result:
  - pre-state confirmed `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` absent
  - `mknodc /dev/binder 10 81` PASS
  - `mknodc /dev/hwbinder 10 80` PASS
  - `mknodc /dev/vndbinder 10 79` PASS
  - created-state `stat` PASS for all three nodes
  - cleanup `run /cache/bin/toybox rm -f ...` PASS
  - post-state confirmed all three nodes absent
- safety:
  - no Binder open, no Binder ioctl, no binderfs mount
  - no service-manager/HAL/`wificond` execution
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- next:
  - v292 Binder open-only helper smoke, still no Binder ioctl or service-manager execution

### V292. Binder Open-Only Smoke — PASS

- 계획: `docs/plans/NATIVE_INIT_V292_BINDER_OPEN_SMOKE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V292_BINDER_OPEN_SMOKE_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_binder_open_smoke.py`
- evidence:
  - `tmp/wifi/v292-binder-open-smoke-plan/`
  - `tmp/wifi/v292-binder-open-smoke-live-20260519-141358/`
- decision: `binder-open-only-smoke-pass`
- result:
  - temporary `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` creation PASS
  - `toybox dd if=/dev/<node> of=/dev/null bs=1 count=0` PASS for all three nodes
  - all three nodes removed after the test
  - `dd` copied `0` bytes, so this was open/close only
- safety:
  - no Binder ioctl, no binderfs mount
  - no service-manager/HAL/`wificond` execution
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- next:
  - v293 service-manager prerequisite model before any service-manager execution

### V293. Service-Manager Prerequisite Model — PASS

- 계획: `docs/plans/NATIVE_INIT_V293_SERVICE_MANAGER_PREREQ_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V293_SERVICE_MANAGER_PREREQ_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_service_manager_prereq_model.py`
- evidence:
  - `tmp/wifi/v293-service-manager-prereq-plan/`
  - `tmp/wifi/v293-service-manager-prereq-live-20260519-141752/`
- decision: `service-manager-prereq-blockers-mapped`
- result:
  - v292 Binder open-only PASS accepted as input
  - service-manager binaries partially visible: `present=2/3`
  - service-manager processes absent: `process_count=0`
  - Android property runtime absent
  - SELinux surface present but not modeled
  - linker/runtime namespace remains partial
- safety:
  - no service-manager execution
  - no Binder ioctl or Binder devnode creation
  - no Wi-Fi daemon execution, QMI/QRTR, scan/connect/link-up
- next:
  - v294 Android property-runtime feasibility before any service-manager execution

### V294. Android Property Runtime Feasibility — PASS

- 계획: `docs/plans/NATIVE_INIT_V294_PROPERTY_RUNTIME_FEASIBILITY_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V294_PROPERTY_RUNTIME_FEASIBILITY_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_property_runtime_feasibility.py`
- evidence:
  - `tmp/wifi/v294-property-runtime-plan/`
  - `tmp/wifi/v294-property-runtime-live-20260519-142338/`
- decision: `property-runtime-inputs-visible-runtime-absent`
- result:
  - Android property input files are visible through mounted system evidence
  - live native property runtime paths are absent:
    - `/dev/socket/property_service` absent
    - `/dev/__properties__` absent
    - `/dev/socket` absent
  - first live run exposed an overly narrow path-list assumption; tool was corrected to use live `find` evidence
- safety:
  - no property service creation or property mutation
  - no service-manager execution
  - no Binder ioctl/devnode creation
  - no Wi-Fi daemon execution, QMI/QRTR, scan/connect/link-up
- next:
  - v295 read-only property snapshot/shim model before any service-manager execution

### V295. Read-Only Property Snapshot Model — PASS

- 계획: `docs/plans/NATIVE_INIT_V295_PROPERTY_SNAPSHOT_MODEL_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V295_PROPERTY_SNAPSHOT_MODEL_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_property_snapshot_model.py`
- evidence:
  - `tmp/wifi/v295-property-snapshot-plan/`
  - `tmp/wifi/v295-property-snapshot-live-20260519-142740/`
- decision: `property-snapshot-model-ready`
- result:
  - parsed `3` property files
  - parsed `248` property key/value pairs
  - parsed `2` property context files and `1264` context lines
  - found `7` Wi-Fi-related static properties
  - selected required runtime baseline keys are partial: `1/4`
- safety:
  - no property service creation or property mutation
  - no service-manager execution
  - no Binder ioctl/devnode creation
  - no Wi-Fi daemon execution, QMI/QRTR, scan/connect/link-up
- next:
  - v296 property shim strategy model before any property runtime creation or service-manager execution

### V296. Property Shim Strategy Model — PASS

- 계획: `docs/plans/NATIVE_INIT_V296_PROPERTY_SHIM_STRATEGY_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V296_PROPERTY_SHIM_STRATEGY_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_property_shim_strategy.py`
- evidence: `tmp/wifi/v296-property-shim-strategy/`
- decision: `property-shim-strategy-capture-needed`
- result:
  - static property count: `248`
  - property context line count: `1264`
  - Wi-Fi property count: `7`
  - required present: `ro.build.version.sdk`
  - required missing: `ro.product.name`, `ro.hardware`, `ro.vendor.build.version.sdk`
- safety:
  - no property runtime creation or property mutation
  - no service-manager execution
  - no Binder ioctl/devnode creation
  - no Wi-Fi daemon execution, QMI/QRTR, scan/connect/link-up
- next:
  - v297 Android-boot property capture plan before any native property shim creation

### V297. Android Property Capture — TOOL READY / WAITING FOR ANDROID

- 계획: `docs/plans/NATIVE_INIT_V297_ANDROID_PROPERTY_CAPTURE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V297_ANDROID_PROPERTY_CAPTURE_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_android_property_capture.py`
- evidence:
  - `tmp/wifi/v297-android-property-capture-plan/`
  - `tmp/wifi/v297-android-property-capture-preflight/`
- decision:
  - plan: `android-property-capture-plan-ready`
  - preflight: `android-property-capture-waiting-for-android`
- result:
  - host tool and guardrails are ready
  - current device state is not Android ADB: `adb get-state` returned `error: no devices/emulators found`
  - actual Android `getprop` capture is deferred until Android is intentionally booted
- safety:
  - no property mutation or runtime creation
  - no service-manager/HAL/Wi-Fi daemon execution
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing
  - no partition backup/write, mount mutation, or reboot
- next:
  - boot Android intentionally and run v297 capture before property shim design

### V298. Property Baseline Compare — TOOL READY / WAITING FOR ANDROID

- 계획: `docs/plans/NATIVE_INIT_V298_PROPERTY_BASELINE_COMPARE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V298_PROPERTY_BASELINE_COMPARE_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_property_baseline_compare.py`
- evidence: `tmp/wifi/v298-property-baseline-compare-waiting/`
- decision: `property-baseline-compare-waiting-for-android`
- result:
  - v295 static snapshot is available
  - v297 Android capture is not available yet
  - required Android-side property values are missing until Android ADB capture is performed
- safety:
  - host-side manifest comparison only
  - no property mutation/runtime creation
  - no service-manager/HAL/Wi-Fi daemon execution
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- next:
  - Android boot + v297 live capture remains the blocker before property shim design

### V299. Android Capture Handoff — PREFLIGHT READY / OPERATOR APPROVAL REQUIRED

- 계획: `docs/plans/NATIVE_INIT_V299_ANDROID_CAPTURE_HANDOFF_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V299_ANDROID_CAPTURE_HANDOFF_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/android_capture_handoff_preflight.py`
- evidence:
  - `tmp/wifi/v299-android-capture-handoff-plan/`
  - `tmp/wifi/v299-android-capture-handoff-preflight/`
- decision: `android-capture-handoff-ready-needs-operator`
- result:
  - native bridge `version/status` PASS
  - native rollback image `stage3/boot_linux_v261.img` present, hash prefix `5a314c2adbd5547b`
  - Android boot candidate `backups/baseline_a_20260423_025322/boot.img` present, hash prefix `c15ce425abb8da41`
  - generated operator handoff and rollback commands
- safety:
  - v299 executed no reboot, recovery transition, boot partition write, or Android flash
  - property/service-manager/HAL/Wi-Fi daemon/scan/connect actions remain blocked
- next:
  - operator-approved Android boot handoff, then v297 capture and v298 compare

### V300. Android Capture Executor — DRY-RUN PASS / APPROVAL REQUIRED

- 계획: `docs/plans/NATIVE_INIT_V300_ANDROID_CAPTURE_EXECUTOR_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V300_ANDROID_CAPTURE_EXECUTOR_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/android_capture_handoff_execute.py`
- evidence:
  - `tmp/wifi/v300-android-capture-executor-plan/`
  - `tmp/wifi/v300-android-capture-executor-dryrun/`
  - `tmp/wifi/v300-android-capture-executor-refuse/`
- decisions:
  - `android-capture-executor-plan-ready`
  - `android-capture-executor-dryrun-ready`
  - `android-capture-executor-approval-required`
- result:
  - dry-run recorded the full Android handoff, v297 capture, v298 compare, and native rollback sequence
  - `run` without `--allow-android-boot-flash --assume-yes --i-understand-native-rollback` refused before dangerous actions
  - post-check still shows native `A90 Linux init 0.9.60 (v261)`
- safety:
  - no live reboot/recovery/flash was executed
  - no property mutation or Wi-Fi bring-up action was executed
- next:
  - explicit operator approval is required before v300 live `run`

### V301. Property Shim Seed — WAITING FOR ANDROID CAPTURE

- 계획: `docs/plans/NATIVE_INIT_V301_PROPERTY_SHIM_SEED_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V301_PROPERTY_SHIM_SEED_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_property_shim_seed.py`
- evidence: `tmp/wifi/v301-property-shim-seed-waiting/`
- decision: `property-shim-seed-waiting-for-android`
- result:
  - generated `seed.json`
  - selected keys remain blocked because Android capture is absent
  - static-only `ro.build.version.sdk` is not treated as sufficient runtime truth
- safety:
  - no device command execution
  - no property runtime/service creation
  - no service-manager/HAL/Wi-Fi daemon execution
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- next:
  - operator-approved v300 live run remains the blocker before Android-backed seed generation

### V302. Android Capture Approval Packet — READY / OPERATOR APPROVAL REQUIRED

- 계획: `docs/plans/NATIVE_INIT_V302_ANDROID_CAPTURE_APPROVAL_PACKET_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V302_ANDROID_CAPTURE_APPROVAL_PACKET_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/android_capture_approval_packet.py`
- evidence: `tmp/wifi/v302-android-capture-approval-packet/`
- decision: `android-capture-approval-ready`
- result:
  - v299 preflight PASS
  - v300 dry-run/refusal PASS
  - current native `version/status` PASS
  - live command and abort conditions generated
  - pre-live target propagation audit PASS: explicit `--adb`/`--serial` now
    propagate to Android property capture and native rollback restore
- safety:
  - no reboot/recovery/flash was executed
  - no property mutation or Wi-Fi bring-up action was executed
- next:
  - execute v300 live command only with explicit operator approval

### V303. Android Capture Postprocess Harness — WAITING FOR LIVE

- 계획: `docs/plans/NATIVE_INIT_V303_ANDROID_CAPTURE_POSTPROCESS_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V303_ANDROID_CAPTURE_POSTPROCESS_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/android_capture_postprocess.py`
- evidence:
  - `tmp/wifi/v303-android-capture-postprocess-waiting/`
  - `tmp/wifi/v303-android-capture-postprocess-waiting-run/`
  - `tmp/wifi/v303-synthetic/out/`
- decisions:
  - current state: `android-capture-postprocess-waiting-for-live`
  - synthetic ready path: `android-capture-postprocess-seed-ready`
- result:
  - v303 can classify missing live handoff, failed live handoff, missing Android capture/compare, seed-ready, and seed-blocked states
  - `run` is host-only and invokes v301 seed generation only after v297/v298 are ready
- safety:
  - no device command, ADB command, reboot, recovery, flash, property mutation, or Wi-Fi bring-up action was executed
- next:
  - explicit operator approval for v300 live handoff remains the blocker

### V304. Android Capture Live Guard — GO / OPERATOR APPROVAL REQUIRED

- 계획: `docs/plans/NATIVE_INIT_V304_ANDROID_CAPTURE_LIVE_GUARD_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V304_ANDROID_CAPTURE_LIVE_GUARD_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/android_capture_live_guard.py`
- evidence: `tmp/wifi/v304-android-capture-live-guard/`
- decision: `android-capture-live-guard-go`
- result:
  - v302 approval packet PASS
  - v300 target propagation PASS
  - Android boot image and native rollback image hash/size PASS
  - v303 postprocess waiting state PASS
  - current native `version/status` PASS
  - generated `live-command.txt` only because blocker checks passed
- safety:
  - guard executed no ADB command, reboot, recovery, flash, property mutation, or Wi-Fi bring-up action
- next:
  - explicit operator approval is still required before executing the v300 live command

### V305. Android Capture Rescue Doctor — NATIVE READY

- 계획: `docs/plans/NATIVE_INIT_V305_ANDROID_CAPTURE_RESCUE_DOCTOR_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V305_ANDROID_CAPTURE_RESCUE_DOCTOR_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/android_capture_rescue_doctor.py`
- evidence: `tmp/wifi/v305-android-capture-rescue-doctor/`
- decision: `native-ready`
- result:
  - native bridge version probe PASS
  - ADB devices read-only probe PASS, no ADB targets present
  - generated operator aid commands for live handoff, native rollback, and Android capture path
- safety:
  - no recommended command was executed
  - no reboot/recovery/flash/property mutation/Wi-Fi bring-up action was executed
- next:
  - after explicit live handoff approval, run v304 guard once more and execute v300 live command

### V306. Android Capture Live Result — PASS / NATIVE RESTORED

- 계획: `docs/plans/NATIVE_INIT_V306_ANDROID_CAPTURE_LIVE_RESULT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V306_ANDROID_CAPTURE_LIVE_RESULT_2026-05-19.md`
- boot image change: Android boot temporarily flashed, then native v261 restored
- restored device build: `A90 Linux init 0.9.60 (v261)`
- evidence:
  - `tmp/wifi/v300-android-capture-executor-live/`
  - `tmp/wifi/v297-android-property-capture-android/`
  - `tmp/wifi/v298-property-baseline-compare-android/`
  - `tmp/wifi/v303-android-capture-postprocess-after-live/`
  - `tmp/wifi/v301-property-shim-seed-android/`
  - `tmp/wifi/v305-android-capture-rescue-doctor-after-live/`
- decisions:
  - live handoff: `android-capture-executor-pass`
  - Android property capture: `android-property-capture-pass`
  - baseline compare: `property-baseline-compare-ready`
  - postprocess: `android-capture-postprocess-seed-ready`
  - seed: `property-shim-seed-ready`
  - rescue doctor: `native-ready`
- result:
  - Android boot image flash/readback PASS
  - Android ADB reached `device`
  - captured required Android property keys: `ro.build.version.sdk=31`, `ro.product.name=r3qks`, `ro.hardware=qcom`, `ro.vendor.build.version.sdk=30`
  - native rollback restored and verified `A90 Linux init 0.9.60 (v261)`
- safety:
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing was executed
  - no property runtime mutation or service-manager/HAL/Wi-Fi daemon execution was performed
- next:
  - v307 candidate: read-only property shim design using Android-backed seed

### V307. Property Shim Design Model — READY

- 계획: `docs/plans/NATIVE_INIT_V307_PROPERTY_SHIM_DESIGN_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V307_PROPERTY_SHIM_DESIGN_2026-05-19.md`
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_property_shim_design.py`
- evidence: `tmp/wifi/v307-property-shim-design/`
- decision: `property-shim-design-model-ready`
- selected next prototype: `private-readonly-property-area`
- result:
  - Android-backed property seed is complete for selected keys
  - candidate matrix created for `analysis-only-seed`, `private-readonly-property-area`, `ld-preload-property-get-shim`, and `minimal-property-service-socket`
  - `minimal-property-service-socket` remains blocked as too broad/high-risk
- safety:
  - host-only design model
  - no property runtime node creation, ADB/device command, Android service start, or Wi-Fi bring-up action
- next:
  - v308 candidate: private read-only property area format/proof model, still no runtime node creation

### V308. Private Property Area Proof Model — NEEDS FORMAT SOURCE

- 계획: `docs/plans/NATIVE_INIT_V308_PRIVATE_PROPERTY_AREA_PROOF_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V308_PRIVATE_PROPERTY_AREA_PROOF_2026-05-19.md`
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_private_property_area_proof.py`
- evidence: `tmp/wifi/v308-private-property-area-proof/`
- decision: `private-property-area-proof-needs-format-source`
- result:
  - Android-backed selected seed keys are valid read-only `ro.*` values
  - v297 Android capture and v307 design selection are present
  - property area binary layout and serialized `property_info` compatibility remain unproven
- safety:
  - host-only proof model
  - no device/ADB command, property runtime node, socket, service-manager/HAL/Wi-Fi daemon, or Wi-Fi bring-up action
- next:
  - v309 candidate: AOSP property area/property info format extractor before any runtime prototype

### V309. Property Format Source Probe — READY

- 계획: `docs/plans/NATIVE_INIT_V309_PROPERTY_FORMAT_SOURCE_PROBE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V309_PROPERTY_FORMAT_SOURCE_PROBE_2026-05-19.md`
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_property_format_source_probe.py`
- evidence: `tmp/wifi/v309-property-format-source-probe/`
- decision: `property-format-source-map-ready`
- result:
  - Android 12 AOSP ref `android-12.0.0_r34` selected for SDK 31 seed
  - source fetch `11/11` PASS
  - prop area constants, bionic serialized read path, and property info serializer/parser markers found
- safety:
  - host-only source probe
  - no device/ADB command, runtime property file, property service socket, daemon, or Wi-Fi bring-up action
- next:
  - v310 candidate: host-side `property_info` / `prop_area` serializer compatibility proof

### V310. Property Serializer Compatibility Proof — READY

- 계획: `docs/plans/NATIVE_INIT_V310_PROPERTY_SERIALIZER_PROOF_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V310_PROPERTY_SERIALIZER_PROOF_2026-05-19.md`
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_property_serializer_proof.py`
- evidence: `tmp/wifi/v310-property-serializer-proof/`
- decision: `property-serializer-proof-ready`
- result:
  - host-only serialized `property_info` binary generated and parsed
  - host-only `prop_area` binary generated and parsed
  - selected Android-backed seed keys roundtrip PASS
  - model still uses synthetic context `u:object_r:default_prop:s0`
- safety:
  - no device/ADB command, runtime property file install, property service socket, daemon, or Wi-Fi bring-up action
- next:
  - v311 candidate: context-aware `property_contexts` mapping proof before runtime prototype

### V311. Property Context Mapping Proof — READY

- 계획: `docs/plans/NATIVE_INIT_V311_PROPERTY_CONTEXT_MAPPING_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V311_PROPERTY_CONTEXT_MAPPING_2026-05-19.md`
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_property_context_mapping_proof.py`
- evidence: `tmp/wifi/v311-property-context-mapping-proof/`
- decision: `property-context-mapping-ready`
- result:
  - captured Android `property_contexts` rule count `1264`
  - selected seed key mappings PASS
  - context-aware `property_info` binary roundtrip PASS
- safety:
  - host-only mapping proof
  - no device/ADB command, runtime property install, property service socket, daemon, or Wi-Fi bring-up action
- next:
  - v312 candidate: private property runtime layout package dry-run before any live install

### V312. Private Property Runtime Layout Dry-run — READY

- 계획: `docs/plans/NATIVE_INIT_V312_PRIVATE_PROPERTY_LAYOUT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V312_PRIVATE_PROPERTY_LAYOUT_2026-05-19.md`
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_private_property_layout_dryrun.py`
- evidence: `tmp/wifi/v312-private-property-runtime-layout/`
- decision: `private-property-layout-dryrun-ready`
- result:
  - local `layout/dev/__properties__/property_info` generated
  - local `properties_serial` generated
  - local per-context `prop_area` files generated for `bootloader_prop`, `build_prop`, `build_vendor_prop`
  - layout roundtrip PASS
- safety:
  - host-only dry-run
  - no device/ADB command, runtime install, bind mount, property service socket, daemon, or Wi-Fi bring-up action
- next:
  - v313 candidate: private property runtime materialization approval packet

### V313. Private Property Materialization Approval Packet — READY / WAITING FOR OPERATOR

- 계획: `docs/plans/NATIVE_INIT_V313_PRIVATE_PROPERTY_MATERIALIZATION_APPROVAL_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V313_PRIVATE_PROPERTY_MATERIALIZATION_APPROVAL_2026-05-19.md`
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_private_property_materialization_approval.py`
- evidence: `tmp/wifi/v313-private-property-materialization-approval/`
- decision: `private-property-materialization-approval-ready`
- result:
  - v312 layout prerequisite PASS
  - live materialization scope recorded
  - explicit not-approved actions recorded
  - required approval phrase emitted
- required approval phrase:
  - `approve v314 private property namespace materialization only; no daemon start and no Wi-Fi bring-up`
- next:
  - v314 executor scaffold records the future live sequence and keeps execution fail-closed

### V314. Private Property Materialization Executor Scaffold — READY / LIVE NOT IMPLEMENTED

- 계획: `docs/plans/NATIVE_INIT_V314_PRIVATE_PROPERTY_MATERIALIZATION_EXECUTOR_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V314_PRIVATE_PROPERTY_MATERIALIZATION_EXECUTOR_2026-05-19.md`
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_private_property_materialization_executor.py`
- evidence:
  - `tmp/wifi/v314-private-property-materialization-executor/`
  - `tmp/wifi/v314-private-property-materialization-executor-refuse/`
  - `tmp/wifi/v314-private-property-materialization-executor-approved-refuse/`
- decisions:
  - `private-property-materialization-executor-plan-ready`
  - `private-property-materialization-executor-approval-required`
  - `private-property-materialization-executor-live-not-implemented`
- result:
  - future materialization sequence recorded
  - exact approval phrase and approval flags checked
  - even approved `run` remains fail-closed in v314
- safety:
  - no device command, no ADB command, no generated file installation
  - no bind mount, no property service socket, no daemon start, no Wi-Fi bring-up
- next:
  - v315 read-only live preflight before any materialization implementation

### V315. Private Property Live Preflight — PASS

- 계획: `docs/plans/NATIVE_INIT_V315_PRIVATE_PROPERTY_LIVE_PREFLIGHT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V315_PRIVATE_PROPERTY_LIVE_PREFLIGHT_2026-05-19.md`
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_private_property_live_preflight.py`
- evidence: `tmp/wifi/v315-private-property-live-preflight/`
- decision: `private-property-live-preflight-ready`
- result:
  - live native version/status/selftest/storage/mountsd/logpath read-only checks PASS
  - SD workspace is mounted read-write and expected
  - netservice remains disabled
  - selftest reports `fail=0`
- safety:
  - `device_mutations=false`
  - no `run`, write, mount, push, reboot, property service socket, daemon start, or Wi-Fi bring-up action
- next:
  - v316 approval packet for the next minimal private namespace copy/materialization proof

### V316. Private Property Live Approval Packet — READY / WAITING FOR OPERATOR

- 계획: `docs/plans/NATIVE_INIT_V316_PRIVATE_PROPERTY_LIVE_APPROVAL_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V316_PRIVATE_PROPERTY_LIVE_APPROVAL_2026-05-19.md`
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_private_property_live_approval_packet.py`
- evidence: `tmp/wifi/v316-private-property-live-approval/`
- decision: `private-property-live-approval-ready`
- result:
  - v314 executor plan PASS
  - v315 read-only live preflight PASS
  - exact v317 approval phrase emitted
- required approval phrase:
  - `approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up`
- safety:
  - `device_commands_executed=false`
  - no device command, ADB command, generated file copy, mount, daemon start, or Wi-Fi bring-up
- next:
  - v317 plan is ready; live execution is blocked until explicit operator approval

### V317. Minimal Private Property Namespace Proof — LIVE PASS

- 계획: `docs/plans/NATIVE_INIT_V317_PRIVATE_PROPERTY_NAMESPACE_PROOF_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V317_PRIVATE_PROPERTY_NAMESPACE_PROOF_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_private_property_namespace_proof.py`
- evidence:
  - `tmp/wifi/v317-private-property-namespace-proof-plan/`
  - `tmp/wifi/v317-private-property-namespace-proof-refuse/`
  - `tmp/wifi/v317-private-property-namespace-proof-cleanup-refuse/`
  - `tmp/wifi/v317-private-property-namespace-proof-audit/`
  - `tmp/wifi/v317-private-property-namespace-proof/`
  - `tmp/wifi/v351-v317-live-executor/`
  - `tmp/wifi/v333-post-v317-router/`
- decisions:
  - `private-property-namespace-proof-plan-ready`
  - `private-property-namespace-proof-approval-required`
  - `private-property-namespace-proof-audit-pass`
  - `private-property-namespace-proof-audit-selftest-pass`
  - `private-property-namespace-proof-pass`
  - `v317-live-executor-run-pass`
  - `post-v317-router-v320-ready`
- transfer estimate:
  - files `5`, bytes `524988`, chunks `471`, estimated device commands `505`
- required approval phrase:
  - `approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up`
- intended scope:
  - create `/mnt/sdext/a90/private-property-v317`
  - copy v312 generated property layout files under that private workdir only
  - verify device SHA-256 for copied files
  - cleanup only that versioned workdir
- transfer policy:
  - existing ACM bridge only
  - no NCM/tcpctl start because the approval packet forbids daemon start
- safety:
  - no global `/dev/__properties__` replacement
  - no property service socket
  - no service-manager/HAL/Wi-Fi daemon start
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing
  - audit confirms plan/refusal manifests are fail-closed and scope-bounded
  - audit selftest confirms bad path, missing blocked-actions, excessive transfer, and mutation records are blocked
- live result:
  - approved V351 executor run PASS after retry with `--timeout 900`
  - remote workdir `/mnt/sdext/a90/private-property-v317`
  - 5 files copied and SHA-256 verified, 502 device commands, no daemon start, no Wi-Fi bring-up
- next:
  - run V320 plan first
  - V320 live lookup still needs its own exact approval phrase

### V318. Private Property Transfer Primitive Preflight — PASS

- 계획: `docs/plans/NATIVE_INIT_V318_PRIVATE_PROPERTY_TRANSFER_PRIMITIVE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V318_PRIVATE_PROPERTY_TRANSFER_PRIMITIVE_2026-05-19.md`
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_private_property_transfer_primitive_preflight.py`
- evidence: `tmp/wifi/v318-private-property-transfer-primitive-preflight/`
- decision: `private-property-transfer-primitive-preflight-ready`
- result:
  - read-only live primitive checks PASS
  - `toybox uudecode -o`, `base64 -d [FILE...]`, `touch`, `writefile`, and `sha256sum` are available
  - `toybox sh` is unavailable and must not be used for V317 transfer
- safety:
  - `device_mutations=false`
  - no file write/create/remove, no NCM/tcpctl start, no daemon start, no Wi-Fi bring-up
- next:
  - patch V317 runner to use a redirection-free `uudecode -o` transfer strategy before any live namespace proof

### V319. Serial Transfer Append — PASS

- 계획: `docs/plans/NATIVE_INIT_V319_SERIAL_TRANSFER_APPEND_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V319_SERIAL_TRANSFER_APPEND_2026-05-19.md`
- native build: `A90 Linux init 0.9.61 (v319)`
- boot image: `stage3/boot_linux_v319.img`
- artifact sha256:
  - init `d8cf63a6231d95a1c29e4a3587cc38e900ff46007f8f686f22c9fc814c60d7d1`
  - ramdisk `d264d2130f1480e4cc19f33b618fd4365e65238101b9fe13c38474d138ee7256`
  - boot `98cc57153bcc4c235193e28fd52650485ffc1f19aa6464942e5216839d4597c8`
- validation:
  - native-init flash PASS
  - `cmdv1 version/status` PASS
  - appendfile transfer smoke PASS
  - long `cmdv1x` 1500-byte append PASS
  - V317 plan/refusal/audit revalidation PASS
- result:
  - added scoped `appendfile` and 4096-byte shell/cmdv1x buffers
  - V317 runner now uses `appendfile` + `uudecode -o` instead of unavailable `toybox sh`
- next:
  - V317 live private namespace proof may run after the exact V317 approval phrase; still no daemon start or Wi-Fi bring-up

### V320. Private Property Lookup Proof — LIVE PASS

- 계획: `docs/plans/NATIVE_INIT_V320_PRIVATE_PROPERTY_LOOKUP_PROOF_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V320_PRIVATE_PROPERTY_LOOKUP_PROOF_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_lookup_proof.py`
- native build baseline: `A90 Linux init 0.9.61 (v319)`
- device flash: 없음. v320은 host runner skeleton이며 boot image 변경 없음
- prerequisite:
  - v317 live proof `private-property-namespace-proof-pass` — now available
  - v317 cleanup or explicit stale-workdir cleanup
  - v312 generated property layout evidence
- validation:
  - `py_compile` PASS
  - `plan` decision `private-property-lookup-blocked-v317-missing`
  - `run` decision `private-property-lookup-blocked-v317-missing`
  - `cleanup` decision `private-property-lookup-cleanup-not-needed`
  - `device_commands_executed=false`, `device_mutations=false`
  - post-V317 plan decision `private-property-lookup-plan-ready`
  - post-V317 plan `device_commands_executed=false`, `device_mutations=false`
  - exact V320 approval phrase received
  - helper v11 serial deploy decision `execns-helper-v11-serial-deploy-pass`
  - live stale-helper failure recorded for v10
  - live unmounted-system failure recorded for v11 before `mountsystem ro`
  - live mounted-system decision `private-property-lookup-getprop-pass`
  - four allowlisted properties matched v312 expected values
- intended proof:
  - run an Android-linked read-only property reader such as `/system/bin/getprop` inside a private Android execution namespace
  - expose only the v317 private property directory to that child as `/dev/__properties__`
  - compare selected property output against v312 generated seed values
- guardrails:
  - no global `/dev/__properties__` replacement or bind mount
  - no `/dev/socket/property_service`
  - no property mutation, daemon start, Wi-Fi scan/connect/link-up, credential, DHCP, routing, rfkill write, module load, or firmware mutation
- next:
  - proceed to bounded CNSS pre-start environment probe planning
  - daemon start and Wi-Fi bring-up remain blocked until a new explicit approval boundary

### V321. Execns Property Lookup Helper Support — STATIC PASS / DEPLOYED FOR V320

- 계획: `docs/plans/NATIVE_INIT_V321_EXECNS_PROPERTY_LOOKUP_HELPER_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V321_EXECNS_PROPERTY_LOOKUP_HELPER_2026-05-19.md`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper marker: `a90_android_execns_probe v11`
- boot image: 없음. v321은 helper-only/static support이며 native init version 변경 없음
- artifact sha256:
  - `/tmp/a90_android_execns_probe_v321` `f40db33a2823662f64d7a2b3c6dca9ce174801208c14c4a83647a12db1ce636b`
- validation:
  - static ARM64 helper build PASS
  - `strings` marker/options check PASS
  - `py_compile` PASS
  - `git diff --check` PASS
- implemented boundary:
  - new mode `property-lookup`
  - new target profile `system-getprop` mapped to `/system/bin/getprop`
  - private `/dev/__properties__` bind only inside the helper private root
  - narrow property-root and property-key allowlists
- live status:
  - v11 helper was deployed over serial for V320 live proof
  - deploy evidence: `tmp/wifi/v320-helper-v11-serial-deploy/`
  - no daemon start or Wi-Fi bring-up was performed by helper deployment
- next:
  - V320 proved the v11 `property-lookup` mode against four allowlisted properties

### V322. Private Property Lookup Runner Integration — FAIL-CLOSED PASS / V320 LIVE PASS

- 계획: `docs/plans/NATIVE_INIT_V322_PRIVATE_PROPERTY_LOOKUP_RUNNER_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V322_PRIVATE_PROPERTY_LOOKUP_RUNNER_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_lookup_proof.py`
- boot image: 없음. v322는 host runner integration이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - `plan` decision `private-property-lookup-blocked-v317-missing`
  - approval-flagged `run` decision `private-property-lookup-blocked-v317-missing`
  - `device_commands_executed=false`
  - `device_mutations=false`
  - planned helper commands: 4
- implemented boundary:
  - bridge/helper args added
  - future helper command uses `run /cache/bin/a90_android_execns_probe --mode property-lookup --target-profile system-getprop`
  - lookup keys filtered to the v321 helper allowlist
- live status:
  - executed through V320 after exact approval phrase
  - final evidence: `tmp/wifi/v320-private-property-lookup-proof-live-v11-mounted/`
  - live decision: `private-property-lookup-getprop-pass`
- next:
  - use the V320 pass as prerequisite for bounded CNSS pre-start environment probing

### V323. Private Property Chain Gate Audit — PASS / V320 LIVE BOUNDARY CROSSED

- 계획: `docs/plans/NATIVE_INIT_V323_PRIVATE_PROPERTY_CHAIN_AUDIT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V323_PRIVATE_PROPERTY_CHAIN_AUDIT_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_chain_audit.py`
- evidence: `tmp/wifi/v323-private-property-chain-audit/`
- boot image: 없음. v323은 host-only gate audit이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - audit decision `private-property-chain-blocked-v317-missing`
  - `audit_pass=true`
  - `chain_ready=false`
  - `device_commands_executed=false`
  - `device_mutations=false`
  - post-V317 audit decision `private-property-chain-ready-for-v320-approval`
  - post-V317 `chain_ready=true`
- gate result:
  - v312/v315/v316/v317-plan/v317-audit/v317-live/v319/v321/v322/v325 prerequisites PASS
  - V320 exact approval phrase was received and used for the recorded live proof
  - V320 live proof passed after v11 helper deploy and `mountsystem ro`
- next:
  - plan bounded CNSS pre-start environment probe
  - daemon start and Wi-Fi bring-up remain outside the current approval boundary

### V324. Private Property Live Approval Refresh — READY / LIVE NOT APPROVED

- 계획: `docs/plans/NATIVE_INIT_V324_PRIVATE_PROPERTY_APPROVAL_REFRESH_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V324_PRIVATE_PROPERTY_APPROVAL_REFRESH_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_approval_refresh.py`
- evidence: `tmp/wifi/v324-private-property-approval-refresh/`
- boot image: 없음. v324는 host-only approval packet refresh이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `private-property-approval-refresh-ready`
  - `pass=true`
  - `live_execution_approved=false`
  - `device_commands_executed=false`
  - `device_mutations=false`
- transfer estimate:
  - files 5, bytes 524988, chunks 471, estimated commands 505, max cmdv1x script length 3294
- required exact phrase:
  - `approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up`
- next:
  - if exact approval is provided, run v317 live proof
  - otherwise continue read-only Wi-Fi/kernel inventory work

### V325. Execns Helper Deploy Preflight — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V325_EXECNS_HELPER_DEPLOY_PREFLIGHT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V325_EXECNS_HELPER_DEPLOY_PREFLIGHT_2026-05-19.md`
- tool: `scripts/revalidation/wifi_execns_helper_deploy_preflight.py`
- evidence: `tmp/wifi/v325-execns-helper-deploy-preflight/`
- boot image: 없음. v325는 host-only helper deploy preflight이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `execns-helper-deploy-preflight-ready`
  - `pass=true`
  - built marker `a90_android_execns_probe v11`
  - built sha256 `f40db33a2823662f64d7a2b3c6dca9ce174801208c14c4a83647a12db1ce636b`
  - local default helper status `stale`
  - local default marker `a90_android_execns_probe v10`
  - `device_commands_executed=false`
  - `device_mutations=false`
- deploy boundary:
  - future deploy target `/cache/bin/a90_android_execns_probe`
  - deployment is a separate explicit device-mutation step
- next:
  - if exact v317 approval is provided, run the v317 minimal live proof
  - use the fresh v11 helper for the later v320 private property lookup stage after v317 PASS evidence exists
  - otherwise continue host-only or read-only Wi-Fi/kernel inventory work

### V326. Private Property Chain V325 Gate — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V326_PRIVATE_PROPERTY_CHAIN_V325_GATE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V326_PRIVATE_PROPERTY_CHAIN_V325_GATE_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_chain_audit.py`
- evidence: `tmp/wifi/v326-private-property-chain-audit/`
- boot image: 없음. v326은 host-only chain audit update이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `private-property-chain-blocked-v317-missing`
  - `audit_pass=true`
  - `chain_ready=false`
  - v325 gate `v325-fresh-helper-preflight` PASS
  - v317 live PASS evidence missing
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 v317 minimal live proof 진행
  - approval이 없으면 다른 host-only/read-only Wi-Fi readiness 작업 진행

### V327. Private Property Approval Refresh With V326 Gate — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V327_PRIVATE_PROPERTY_APPROVAL_REFRESH_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V327_PRIVATE_PROPERTY_APPROVAL_REFRESH_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_approval_refresh.py`
- evidence: `tmp/wifi/v327-private-property-approval-refresh/`
- boot image: 없음. v327은 host-only approval packet refresh이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `private-property-approval-refresh-ready`
  - `pass=true`
  - `live_execution_approved=false`
  - chain audit path `tmp/wifi/v326-private-property-chain-audit/manifest.json`
  - `device_commands_executed=false`
  - `device_mutations=false`
- required exact phrase:
  - `approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up`
- next:
  - exact v317 approval phrase가 있으면 v317 minimal live proof 진행
  - approval이 없으면 다른 host-only/read-only Wi-Fi readiness 작업 진행

### V328. V317 Runner Approval Refresh Gate — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V328_V317_RUNNER_APPROVAL_REFRESH_GATE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V328_V317_RUNNER_APPROVAL_REFRESH_GATE_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_namespace_proof.py`
- evidence:
  - `tmp/wifi/v328-v317-runner-plan/`
  - `tmp/wifi/v328-v317-runner-refuse/`
- boot image: 없음. v328은 host-only runner gate alignment이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - plan decision `private-property-namespace-proof-plan-ready`
  - run-without-approval decision `private-property-namespace-proof-approval-required`
  - `approval-refresh` blocker check PASS
  - run refusal executed no device command and performed no device mutation
- next:
  - exact v317 approval phrase가 있으면 v317 minimal live proof 진행
  - approval이 없으면 다른 host-only/read-only Wi-Fi readiness 작업 진행

### V329. Wi-Fi Readiness Dashboard — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V329_WIFI_READINESS_DASHBOARD_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V329_WIFI_READINESS_DASHBOARD_2026-05-19.md`
- tool: `scripts/revalidation/wifi_readiness_dashboard.py`
- evidence: `tmp/wifi/v329-wifi-readiness-dashboard/`
- boot image: 없음. v329는 host-only evidence aggregation이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `wifi-readiness-dashboard-ready-blocked-by-v317`
  - `pass=true`
  - `device_commands_executed=false`
  - `device_mutations=false`
- current summary:
  - vendor assets visible
  - repeated CNSS start-only path is not useful because prior deltas showed no WLAN/wiphy readiness change
  - Binder open-only blocker is cleared, but service-manager remains blocked by property runtime/process requirements
  - Android property capture and private property layout are ready
  - next concrete live gate remains V317 exact approval
- next:
  - exact v317 approval phrase가 있으면 v317 minimal live proof 진행
  - approval이 없으면 dashboard 기반으로 다른 host-only/read-only 후보 선정

### V330. Wi-Fi Evidence Freshness Audit — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V330_WIFI_EVIDENCE_FRESHNESS_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V330_WIFI_EVIDENCE_FRESHNESS_2026-05-19.md`
- tool: `scripts/revalidation/wifi_evidence_freshness_audit.py`
- evidence: `tmp/wifi/v330-evidence-freshness-audit/`
- boot image: 없음. v330은 host-only evidence freshness audit이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `wifi-evidence-freshness-clean`
  - `pass=true`
  - V325-V329 evidence git head matches current clean head
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 v317 minimal live proof 진행
  - approval이 없으면 다른 host-only/read-only 후보 선정

### V331. V317 Live Readiness Packet — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V331_V317_LIVE_READINESS_PACKET_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V331_V317_LIVE_READINESS_PACKET_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_live_readiness_packet.py`
- evidence: `tmp/wifi/v331-v317-live-readiness-packet/`
- boot image: 없음. v331은 host-only operator handoff packet이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `v317-live-readiness-packet-ready`
  - `pass=true`
  - `live_execution_approved=false`
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 readiness packet의 command로 v317 minimal live proof 진행
  - approval이 없으면 다른 host-only/read-only 후보 선정

### V332. Current Read-only Live Preflight — PASS / READ-ONLY DEVICE

- 계획: `docs/plans/NATIVE_INIT_V332_CURRENT_READONLY_LIVE_PREFLIGHT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V332_CURRENT_READONLY_LIVE_PREFLIGHT_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_live_preflight.py`
- evidence: `tmp/wifi/v332-current-readonly-live-preflight/`
- boot image: 없음. v332는 현재 native device read-only preflight이며 native init version 변경 없음
- validation:
  - decision `private-property-live-preflight-ready`
  - `pass=true`
  - evidence git head `b7965ab`
  - evidence git dirty `false`
  - native version `A90 Linux init 0.9.61 (v319)` PASS
  - storage/mountsd/logpath/selftest/status PASS
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 readiness packet의 command로 v317 minimal live proof 진행
  - approval이 없으면 다른 host-only/read-only 후보 선정

### V333. Post-V317 Router — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V333_POST_V317_ROUTER_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V333_POST_V317_ROUTER_2026-05-19.md`
- tool: `scripts/revalidation/wifi_post_v317_router.py`
- evidence: `tmp/wifi/v333-post-v317-router/`
- boot image: 없음. v333은 host-only result router이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `post-v317-router-awaiting-v317`
  - `pass=true`
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 router/readiness packet의 command로 v317 minimal live proof 진행
  - V317 PASS 후 router를 재실행해 V320 plan/live lookup 여부를 결정

### V334. Wi-Fi Evidence Freshness Expansion — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V334_WIFI_EVIDENCE_FRESHNESS_EXPANSION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V334_WIFI_EVIDENCE_FRESHNESS_EXPANSION_2026-05-19.md`
- tool: `scripts/revalidation/wifi_evidence_freshness_audit.py`
- evidence: `tmp/wifi/v334-evidence-freshness-audit/`
- boot image: 없음. v334는 host-only freshness audit expansion이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `wifi-evidence-freshness-clean`
  - `pass=true`
  - V325-V333 evidence checked
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 router/readiness packet의 command로 v317 minimal live proof 진행

### V335. Wi-Fi Approval Gate Regression — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V335_WIFI_APPROVAL_GATE_REGRESSION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V335_WIFI_APPROVAL_GATE_REGRESSION_2026-05-19.md`
- tool: `scripts/revalidation/wifi_approval_gate_regression.py`
- evidence: `tmp/wifi/v335-approval-gate-regression/`
- boot image: 없음. v335는 host-only approval gate regression이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `wifi-approval-gate-regression-pass`
  - `pass=true`
  - `device_commands_executed=false`
  - `device_mutations=false`
  - dangerous V317 full-approval case intentionally not run
- next:
  - exact v317 approval phrase가 있으면 router/readiness packet의 command로 v317 minimal live proof 진행

### V336. V317 Pre-live Gate Audit — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V336_V317_PRELIVE_GATE_AUDIT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V336_V317_PRELIVE_GATE_AUDIT_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_prelive_gate_audit.py`
- evidence: `tmp/wifi/v336-v317-prelive-gate-audit/`
- boot image: 없음. v336은 host-only pre-live gate audit이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `v317-prelive-gate-awaiting-approval`
  - `pass=true`
  - remaining blocker `exact-v317-approval-phrase`
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 readiness packet의 command로 v317 minimal live proof 진행

### V337. V317 Runner Pre-live Gate Requirement — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V337_V317_RUNNER_PRELIVE_GATE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V337_V317_RUNNER_PRELIVE_GATE_2026-05-19.md`
- target: `scripts/revalidation/wifi_private_property_namespace_proof.py`
- boot image: 없음. v337은 host-side runner gate hardening이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - no-approval run remains `private-property-namespace-proof-approval-required`
  - dirty-tree exact approval blocks on `v336-prelive-gate`
  - approval gate regression remains `wifi-approval-gate-regression-pass`
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - impacted host-only gate evidence를 clean HEAD에서 재생성한 뒤 exact v317 approval phrase가 있으면 V317 minimal live proof 진행

### V338. V317 Readiness Packet V336-aware Update — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V338_V317_READINESS_PACKET_V336_AWARE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V338_V317_READINESS_PACKET_V336_AWARE_2026-05-19.md`
- target:
  - `scripts/revalidation/wifi_v317_live_readiness_packet.py`
  - `scripts/revalidation/wifi_v317_prelive_gate_audit.py`
- boot image: 없음. v338은 host-side handoff packet hardening이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - readiness packet includes `v336-prelive-gate`
  - generated live command includes `--prelive-gate-manifest`
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - clean HEAD에서 canonical V331/V336 evidence 재생성 후 exact v317 approval phrase가 있으면 V317 minimal live proof 진행

### V339. V317 Live Surface Linter — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V339_V317_LIVE_SURFACE_LINTER_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V339_V317_LIVE_SURFACE_LINTER_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_live_surface_linter.py`
- evidence: `tmp/wifi/v339-v317-live-surface-linter/`
- boot image: 없음. v339는 host-only static live-surface linter이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `v317-live-surface-lint-pass`
  - all V317 `device_cmd()` signatures allowlisted
  - readiness packet includes V336 gate and `--prelive-gate-manifest`
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 V317 minimal live proof 진행

### V340. V317 Final Handoff Packet — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V340_V317_FINAL_HANDOFF_PACKET_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V340_V317_FINAL_HANDOFF_PACKET_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_handoff_packet.py`
- evidence: `tmp/wifi/v340-v317-final-handoff-packet/`
- boot image: 없음. v340은 host-only operator handoff packet이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - decision `v317-handoff-awaiting-approval`
  - remaining blocker `exact-v317-approval-phrase`
  - V331/V336/V339 gates PASS
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 handoff packet의 command로 V317 minimal live proof 진행

### V341. Handoff Requires Current V336 Pre-live Gate — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V341_HANDOFF_REQUIRES_CURRENT_PRELIVE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V341_HANDOFF_REQUIRES_CURRENT_PRELIVE_2026-05-19.md`
- target: `scripts/revalidation/wifi_v317_handoff_packet.py`
- boot image: 없음. v341은 host-side handoff correctness fix이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - stale V336 pre-live manifest blocks handoff
  - post-commit V336/V331/V340 canonical evidence regenerated
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 handoff packet의 command로 V317 minimal live proof 진행

### V342. V317 Approved Preflight Mode — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V342_V317_APPROVED_PREFLIGHT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V342_V317_APPROVED_PREFLIGHT_2026-05-19.md`
- target:
  - `scripts/revalidation/wifi_private_property_namespace_proof.py`
  - `scripts/revalidation/wifi_v317_handoff_packet.py`
- boot image: 없음. v342는 host-side runner/handoff preflight 개선이며 native init version 변경 없음
- validation:
  - `py_compile` PASS
  - `git diff --check` PASS
  - no-approval preflight remains approval-required
  - dirty-tree handoff blocks on `current-tree-clean`
  - post-commit approved preflight returns `private-property-namespace-proof-preflight-ready`
  - approved preflight `commands=[]`
  - `device_commands_executed=false`
  - `device_mutations=false`
- next:
  - exact v317 approval phrase가 있으면 handoff packet의 preflight command를 먼저 실행하고, PASS 후 live `run` command를 별도 실행


### V343. Break V331/V336 Handoff Cycle — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V343_BREAK_V331_V336_CYCLE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V343_BREAK_V331_V336_CYCLE_2026-05-19.md`
- target: `scripts/revalidation/wifi_v317_prelive_gate_audit.py`
- boot image: 없음. v343은 host-side gate dependency correction이며 native init version 변경 없음
- 변경:
  - V336 pre-live gate에서 V331 readiness packet 의존성 제거
  - V336 pre-live gate에서 V333 post-V317 router 의존성 제거
  - V340이 V331/V336/V339를 묶는 최종 handoff aggregation point로 유지
- pre-commit validation:
  - `py_compile` PASS
  - V336 audit에서 V331/V333 순환 blocker 제거 확인
- post-commit validation:
  - clean HEAD `da70622`에서 V326/V327/V328/V335/V336/V331/V339/V340 evidence 재생성 PASS
  - approved `preflight`가 device command 없이 `private-property-namespace-proof-preflight-ready` PASS
  - V340 remaining blocker는 `exact-v317-approval-phrase` 하나
- next:
  - exact V317 approval phrase 없이는 live proof 실행하지 않음


### V344. V317 Gate Refresh Helper — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V344_V317_GATE_REFRESH_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V344_V317_GATE_REFRESH_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_gate_refresh.py`
- boot image: 없음. v344는 host-side evidence refresh helper이며 native init version 변경 없음
- 구현:
  - V317 plan, V326/V327/V328/V335/V336/V331/V339/V340/V333 evidence를 dependency order로 재생성
  - optional approved preflight 실행 시 no-device `preflight`만 수행
  - consolidated manifest와 transcripts 생성
- pre-commit validation:
  - `py_compile` PASS
  - `git diff --check` PASS
- post-commit validation:
  - clean current HEAD에서 `wifi_v317_gate_refresh.py --run-approved-preflight refresh` PASS
  - decision `v317-gate-refresh-ready`
  - approved preflight step `private-property-namespace-proof-preflight-ready` PASS
  - `device_commands_executed=false`, `device_mutations=false`
  - remaining blocker `exact-v317-approval-phrase`
- next:
  - exact V317 approval phrase 없이는 live proof 실행하지 않음


### V345. Post-V317 Router Regression — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V345_POST_V317_ROUTER_REGRESSION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V345_POST_V317_ROUTER_REGRESSION_2026-05-19.md`
- tool: `scripts/revalidation/wifi_post_v317_router_regression.py`
- boot image: 없음. v345는 host-only synthetic router regression이며 native init version 변경 없음
- 구현:
  - V317 missing/pass/cleaned/failed/live_error/unexpected/prereq-blocked synthetic manifest cases 추가
  - V333 router decision, rc, pass value, recommended command count/fragments 검증
  - recommended command는 문자열 검사만 하고 실행하지 않음
- pre-commit validation:
  - `py_compile` PASS
  - router regression `post-v317-router-regression-pass` PASS
  - `git diff --check` PASS
- post-commit validation:
  - clean current HEAD에서 router regression 재실행 PASS
  - decision `post-v317-router-regression-pass`
  - blocked cases 없음
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 live proof 실행하지 않음


### V346. Handoff Preflight Output Isolation — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V346_HANDOFF_PREFLIGHT_OUTDIR_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V346_HANDOFF_PREFLIGHT_OUTDIR_2026-05-19.md`
- target: `scripts/revalidation/wifi_v317_handoff_packet.py`
- boot image: 없음. v346은 host-side handoff command safety fix이며 native init version 변경 없음
- 구현:
  - V340 generated preflight command의 `--out-dir`를 live result path와 분리
  - `preflight-command-contract`와 `preflight-output-isolated` handoff check 추가
  - handoff manifest에 `preflight_out_dir` 기록
- pre-commit validation:
  - `py_compile` PASS
  - dirty-tree 상태에서 V340는 `current-tree-clean`으로 block되지만 preflight out-dir contract checks PASS
- post-commit validation:
  - clean HEAD에서 V344 refresh PASS
  - V340 handoff `v317-handoff-awaiting-approval` PASS
  - generated V340 preflight command 실행 PASS
  - generated preflight `private-property-namespace-proof-preflight-ready`, `commands=[]`
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 live proof 실행하지 않음


### V347. Gate Refresh Runs Generated Handoff Preflight — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V347_GATE_REFRESH_GENERATED_PREFLIGHT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V347_GATE_REFRESH_GENERATED_PREFLIGHT_2026-05-19.md`
- target: `scripts/revalidation/wifi_v317_gate_refresh.py`
- boot image: 없음. v347은 host-side evidence refresh coverage fix이며 native init version 변경 없음
- 구현:
  - `--run-approved-preflight`가 direct runner preflight와 generated V340 handoff preflight를 모두 실행
  - generated handoff preflight는 V340 manifest의 `preflight_command`를 그대로 사용
  - no-device preflight manifest decision을 검증
- pre-commit validation:
  - `py_compile` PASS
  - dirty-tree refresh는 block되지만 `v340-generated-preflight` step 포함 확인
  - `device_commands_executed=false`, `device_mutations=false`
- post-commit validation:
  - clean HEAD에서 V344 refresh 재실행 PASS
  - `v342-approved-preflight` PASS
  - `v340-generated-preflight` PASS
  - `device_commands_executed=false`, `device_mutations=false`
  - blocked steps 없음
- next:
  - exact V317 approval phrase 없이는 live proof 실행하지 않음


### V348. V317 Handoff Command Contract — PASS / HOST-ONLY

- 계획: `docs/plans/NATIVE_INIT_V348_HANDOFF_COMMAND_CONTRACT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V348_HANDOFF_COMMAND_CONTRACT_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_handoff_command_contract.py`
- boot image: 없음. v348은 host-only handoff command contract linter이며 native init version 변경 없음
- 구현:
  - V340 generated preflight/live/cleanup command를 `shlex`로 파싱
  - script/subcommand/out-dir/V336 gate manifest/exact approval phrase/approval flags 검증
  - preflight/live/cleanup output directory distinct 검증
  - generated command는 실행하지 않음
- validation:
  - `py_compile` PASS
  - decision `v317-handoff-command-contract-pass`
  - blocked checks 없음
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 live proof 실행하지 않음


### V349. V317 Final Readiness Aggregator — HOST-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V349_FINAL_READINESS_AGGREGATOR_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V349_FINAL_READINESS_AGGREGATOR_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_final_readiness.py`
- boot image: 없음. v349는 host-only final readiness aggregator이며 native init version 변경 없음
- 구현:
  - V344 refresh, V345 router regression, V348 command contract를 순서대로 실행
  - 각 evidence가 current clean HEAD인지 검증
  - no device command/mutation 및 remaining blocker 검증
- pre-commit validation:
  - `py_compile` PASS
  - dirty tree에서는 final readiness block 확인
  - `device_commands_executed=false`, `device_mutations=false`
- post-commit validation:
  - clean HEAD에서 `v317-final-readiness-awaiting-approval` PASS
  - `remaining_blockers=[exact-v317-approval-phrase]`
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 live proof 실행하지 않음


### V350. V317 Operator Checklist — HOST-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V350_V317_OPERATOR_CHECKLIST_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V350_V317_OPERATOR_CHECKLIST_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_operator_checklist.py`
- boot image: 없음. v350은 host-only operator checklist이며 native init version 변경 없음
- 구현:
  - V340 handoff packet과 V349 final readiness를 하나의 operator checklist로 결합
  - preflight/live/cleanup command contract와 output dir, approval phrase, gate manifest 검증
  - current clean HEAD와 no device command/mutation 검증
- pre-commit validation:
  - `py_compile` PASS
  - dirty tree에서는 `current-tree-clean` block 확인
  - `device_commands_executed=false`, `device_mutations=false`
- post-commit validation:
  - clean HEAD에서 `v317-operator-checklist-ready` PASS
  - `remaining_blockers=[exact-v317-approval-phrase]`
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 live proof 실행하지 않음


### V351. V317 Live Executor Guard — HOST-ONLY PLAN PASS

- 계획: `docs/plans/NATIVE_INIT_V351_V317_LIVE_EXECUTOR_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V351_V317_LIVE_EXECUTOR_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_live_executor.py`
- boot image: 없음. v351은 host-side executor guard이며 native init version 변경 없음
- 구현:
  - `plan`은 V349/V350을 재검증하고 live/cleanup/router command를 기록
  - `run`/`cleanup`은 exact V317 approval phrase + mutation flags 없이는 즉시 거부
  - 승인된 run/cleanup path는 V349/V350 재검증 후 V350 command를 실행하도록 구성
- pre-commit validation:
  - `py_compile` PASS
  - no-approval `run`이 device action 없이 거부됨
  - dirty tree `plan`이 V349/V350 clean-head check에서 block됨
- post-commit validation:
  - clean HEAD에서 `v317-live-executor-plan-ready` PASS
  - `live_execution_approved=false`
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 executor `run`/`cleanup` 실행하지 않음


### V352. V317 Live Executor Regression — HOST-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V352_V317_LIVE_EXECUTOR_REGRESSION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V352_V317_LIVE_EXECUTOR_REGRESSION_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_live_executor_regression.py`
- boot image: 없음. v352는 host-side regression이며 native init version 변경 없음
- 구현:
  - no-approval/partial-approval `run`과 `cleanup` 거부 경로 회귀
  - current-state `plan` 경로 회귀
  - no live approval/device command/device mutation 검증
- pre-commit validation:
  - `py_compile` PASS
  - regression PASS
  - dirty tree에서 `plan-current-state`가 readiness-blocked로 pass
  - `device_commands_executed=false`, `device_mutations=false`
- post-commit validation:
  - clean HEAD에서 `v317-live-executor-regression-pass` PASS
  - `plan-current-state`가 `v317-live-executor-plan-ready`로 PASS
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 executor `run`/`cleanup` 실행하지 않음


### V353. Operator Executor Preference — HOST-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V353_OPERATOR_EXECUTOR_PREFERENCE_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V353_OPERATOR_EXECUTOR_PREFERENCE_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_operator_checklist.py`
- boot image: 없음. v353은 host-side checklist hardening이며 native init version 변경 없음
- 구현:
  - V350 checklist의 preferred live/cleanup command를 V351 executor command로 변경
  - raw V340 live/cleanup command는 internal raw command로만 유지
  - exact V317 approval phrase gate 유지
- validation:
  - `py_compile` PASS
  - V350 checklist `v317-operator-checklist-ready` PASS
  - V351 executor plan `v317-live-executor-plan-ready` PASS
  - V352 executor regression `v317-live-executor-regression-pass` PASS
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 executor `run`/`cleanup` 실행하지 않음


### V354. Cleanup Approval Regression Expansion — HOST-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V354_CLEANUP_APPROVAL_REGRESSION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V354_CLEANUP_APPROVAL_REGRESSION_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_live_executor_regression.py`
- boot image: 없음. v354는 host-side regression expansion이며 native init version 변경 없음
- 구현:
  - `cleanup-phrase-only` 회귀 추가
  - `cleanup-flags-only` 회귀 추가
  - cleanup partial approval도 device action 없이 거부되는지 검증
- pre-commit validation:
  - `py_compile` PASS
  - regression PASS
  - `cleanup-no-approval`, `cleanup-phrase-only`, `cleanup-flags-only` PASS
  - `device_commands_executed=false`, `device_mutations=false`
- post-commit validation:
  - clean HEAD에서 `v317-live-executor-regression-pass` PASS
  - `cleanup-no-approval`, `cleanup-phrase-only`, `cleanup-flags-only` PASS
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 executor `run`/`cleanup` 실행하지 않음


### V355. Approval Matrix Regression Expansion — HOST-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V355_APPROVAL_MATRIX_REGRESSION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V355_APPROVAL_MATRIX_REGRESSION_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_live_executor_regression.py`
- boot image: 없음. v355는 host-side regression expansion이며 native init version 변경 없음
- 구현:
  - `run-phrase-allow-only`, `run-phrase-assume-only` 회귀 추가
  - `cleanup-phrase-allow-only`, `cleanup-phrase-assume-only` 회귀 추가
  - exact phrase가 있어도 mutation 확인 플래그 하나만 빠지면 device action 없이 거부되는지 검증
- pre-commit validation:
  - `py_compile` PASS
  - regression PASS
  - missing-one-flag approval cases PASS
  - `device_commands_executed=false`, `device_mutations=false`
- post-commit validation:
  - clean HEAD에서 `v317-live-executor-regression-pass` PASS
  - missing-one-flag approval cases PASS
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 executor `run`/`cleanup` 실행하지 않음


### V356. Wrong-Phrase Approval Regression — HOST-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V356_WRONG_PHRASE_REGRESSION_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V356_WRONG_PHRASE_REGRESSION_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_live_executor_regression.py`
- boot image: 없음. v356은 host-side regression expansion이며 native init version 변경 없음
- 구현:
  - `run-wrong-phrase-full-flags` 회귀 추가
  - `cleanup-wrong-phrase-full-flags` 회귀 추가
  - full mutation flags가 있어도 exact phrase가 아니면 device action 없이 거부되는지 검증
- pre-commit validation:
  - `py_compile` PASS
  - regression PASS
  - wrong-phrase full-flags cases PASS
  - `device_commands_executed=false`, `device_mutations=false`
- post-commit validation:
  - clean HEAD에서 `v317-live-executor-regression-pass` PASS
  - wrong-phrase full-flags cases PASS
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 executor `run`/`cleanup` 실행하지 않음

### V357. V317 Pre-Approval Audit — HOST-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V357_PREAPPROVAL_AUDIT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V357_PREAPPROVAL_AUDIT_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_preapproval_audit.py`
- boot image: 없음. v357은 host-side audit이며 native init version 변경 없음
- 구현:
  - V349 final readiness, V350 operator checklist, V351 executor plan, V352 executor regression을 한 번에 재검증
  - clean HEAD/current evidence/no device mutation/approval blocker only 조건을 통합 검사
  - V350 executor preference, V351 no-approval plan, no/partial/wrong phrase regression matrix를 재확인
  - V351 executor manifest에 approval blocker metadata를 명시해 audit 대상에 포함
- validation:
  - pre-commit dirty tree에서 `v317-preapproval-audit-blocked` 확인
  - pre-commit `device_commands_executed=false`, `device_mutations=false` 확인
  - post-commit clean HEAD에서 `v317-preapproval-audit-awaiting-approval` PASS
  - V349/V350/V351-plan/V352-regression 모두 current clean-head PASS
- next:
  - exact V317 approval phrase 없이는 executor `run`/`cleanup` 실행하지 않음

### V358. V317 Approval/Sudo Boundary Matrix — HOST-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V358_APPROVAL_SUDO_BOUNDARY_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V358_APPROVAL_SUDO_BOUNDARY_2026-05-19.md`
- 운영 문서: `docs/operations/WIFI_V317_APPROVAL_AND_SUDO_MATRIX.md`
- boot image: 없음. v358은 host-side 운영 경계 문서화이며 native init version 변경 없음
- 구현:
  - host-only/no-sudo, host-sudo, exact approval required, separate approval required 명령군을 구분
  - V317 exact phrase가 승인하는 범위와 승인하지 않는 범위를 명시
  - host `sudo`는 실행 권한일 뿐 device mutation approval이 아님을 명시
- validation:
  - `git diff --check`
  - operation/plans/reports 용어 연결 확인
  - V357 pre-approval audit 재실행으로 `v317-preapproval-audit-awaiting-approval` PASS
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact V317 approval phrase 없이는 executor `run`/`cleanup` 실행하지 않음

### V359. V317 Live Blocker Snapshot — HOST-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V359_LIVE_BLOCKER_SNAPSHOT_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V359_LIVE_BLOCKER_SNAPSHOT_2026-05-19.md`
- tool: `scripts/revalidation/wifi_v317_blocker_snapshot.py`
- boot image: 없음. v359는 host-side blocker snapshot이며 native init version 변경 없음
- 구현:
  - V357 pre-approval audit를 재실행하고 V350 operator checklist를 읽어 현재 live blocker 상태를 manifest로 기록
  - V317 live proof가 `exact-v317-approval-phrase` 하나 때문에 막힌 상태인지 확인
  - preferred live path가 V351 executor인지 확인
- validation:
  - pre-commit dirty tree에서 `v317-live-blocker-snapshot-blocked` 확인
  - pre-commit `device_commands_executed=false`, `device_mutations=false` 확인
  - post-commit clean HEAD에서 `v317-live-blocked-awaiting-exact-approval` PASS
  - V357/V350/V351 command/exact phrase checks 모두 PASS
- next:
  - exact V317 approval phrase 없이는 executor `run`/`cleanup` 실행하지 않음

### V360. CNSS Pre-Start Runner Refresh After V320 — NO-START PASS

- 계획: `docs/plans/NATIVE_INIT_V360_CNSS_PRESTART_RUNNER_REFRESH_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V360_CNSS_PRESTART_RUNNER_REFRESH_2026-05-19.md`
- target: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- boot image: 없음. v360은 host runner default refresh이며 native init version 변경 없음
- 배경:
  - V320 live property lookup PASS 후 `/cache/bin/a90_android_execns_probe`는 v11 helper로 교체됐다
  - 기존 CNSS start-only runner 기본 helper SHA가 v10이라 no-start preflight가 false `start-only-blocked`를 냈다
- 구현:
  - default helper SHA를 v11 `f40db33a2823662f64d7a2b3c6dca9ce174801208c14c4a83647a12db1ce636b`로 갱신
  - `run` mode, daemon start, Wi-Fi bring-up은 실행하지 않음
- validation:
  - `py_compile` PASS
  - CNSS start plan decision `cnss-start-plan-ready`
  - runner `plan` decision `dry-run-ready`
  - runner `preflight` decision `preflight-ready`
  - runner `dry-run` decision `preflight-ready`
  - preflight `helper_sha256_match=true`, `required_failures=[]`
  - `daemon_start_executed=false`
- next:
  - 별도 exact approval boundary 없이는 `wifi_cnss_start_only_runner.py run` 실행하지 않음
  - 다음 후보는 bounded CNSS start-only approval packet refresh 또는 추가 no-start readiness probe

### V361. CNSS Start-Only Approval Packet Refresh — NO-START PASS

- 계획: `docs/plans/NATIVE_INIT_V361_CNSS_START_ONLY_APPROVAL_PACKET_PLAN_2026-05-19.md`
- 보고서: `docs/reports/NATIVE_INIT_V361_CNSS_START_ONLY_APPROVAL_PACKET_2026-05-19.md`
- tool: `scripts/revalidation/wifi_cnss_live_approval_packet.py`
- boot image: 없음. v361은 host/no-start approval packet refresh이며 native init version 변경 없음
- prerequisite:
  - V320 live property lookup PASS
  - V360 no-start runner default v11 SHA PASS
- validation:
  - `py_compile` PASS
  - decision `live-approval-packet-ready`
  - prerequisites match PASS
  - runtime materialization profile PASS
  - approved helper argv profile PASS
  - helper no-allow fail-closed PASS
  - `pidof cnss-daemon` before/after PASS
  - no `wlan*` before PASS
  - `/data/vendor/wifi` state unchanged PASS
  - `daemon_start_executed=false`
- generated future command:
  - `python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v361-cnss-live-start-only-run-v11-after-v320 --max-runtime-sec 10 run --allow-daemon-start --assume-yes --i-understand-reboot-only-recovery`
- next:
  - future command remains blocked until a separate explicit operator instruction for bounded CNSS start-only
  - Wi-Fi scan/connect/link-up remains blocked even if start-only is later approved

### V362. Bounded CNSS Start-Only Live Run — START-ONLY PASS

- 계획: `docs/plans/NATIVE_INIT_V362_CNSS_START_ONLY_LIVE_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V362_CNSS_START_ONLY_LIVE_2026-05-20.md`
- tool: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- analyzer: `scripts/revalidation/wifi_cnss_live_evidence_analyzer.py`
- warning disposition: `scripts/revalidation/wifi_cnss_warning_disposition.py`
- boot image: 없음. v362는 host/live validation이며 native init version 변경 없음
- approval:
  - user explicitly requested daemon start; execution scope was restricted to one bounded CNSS start-only run
  - Wi-Fi scan/connect/link-up/credential/DHCP/routing remain outside approval scope
- validation:
  - preflight decision `preflight-ready`
  - approval packet decision `live-approval-packet-ready`
  - live runner decision `start-only-pass`
  - evidence analyzer decision `cnss-start-only-evidence-classified`
  - warning disposition decision `cnss-warning-disposition-ready`
- key markers:
  - `daemon_start_executed=true`
  - `cnss_start.observable=1`
  - `cnss_start.timed_out=1`
  - `cnss_start.term_sent=1`
  - `cnss_start.kill_sent=1`
  - `cnss_start.reaped=1`
  - `cnss_start.postflight_safe=1`
  - `cnss_start.scan_connect_linkup=0`
  - postflight target process count/running/zombie all `0`
  - postflight `/proc/net/dev` and `wifiinv full` show no `wlan*`/wlan-like interface
- warnings accepted for start-only:
  - `perfd-client-unavailable`
  - `kmsg-write-denied`
  - `shell-quote-noise`
- next:
  - plan no-scan/no-connect readiness delta observer before any broader Wi-Fi action
  - broader Wi-Fi scan/connect/link-up remains blocked until a separate explicit plan and approval

### V363. Wi-Fi Bring-Up Phase 0 Baseline Gate — PASS

- 계획: `docs/plans/NATIVE_INIT_V363_WIFI_BRINGUP_PHASE0_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V363_WIFI_BRINGUP_PHASE0_2026-05-20.md`
- evidence: `tmp/wifi/v363-bringup-preflight-20260520-001255/`
- boot image: 없음. v363은 live read-only baseline gate이며 native init version 변경 없음
- approval:
  - user requested Wi-Fi bring-up direction
  - v363 deliberately limited the first step to no-scan/no-connect baseline capture
- validation:
  - decision `wifi-bringup-phase0-live-baseline-ready`
  - native baseline `A90 Linux init 0.9.61 (v319)`
  - `wlan` module present and parameters readable
  - ICNSS core node present and bound to `icnss`
  - QCA6390 node present but driver link absent
  - no `wlan*` netdev
  - no Wi-Fi rfkill
  - no `cnss-daemon`/`cnss_diag` process
- interpretation:
  - V362 proved bounded CNSS daemon start-only can execute and clean up
  - V363 confirms that CNSS alone still does not create the active Wi-Fi link surface
  - next blocker is HAL/service-manager/property/Binder readiness, not another blind CNSS retry
- next:
  - V364 candidate: no-scan/no-connect HAL/service-manager readiness gate
  - do not run AP scan/connect/credential/DHCP/routing before that gate


### V364. Wi-Fi HAL/Service-Manager Readiness Gate — BLOCKED PASS

- 계획: `docs/plans/NATIVE_INIT_V364_HAL_SERVICE_READINESS_GATE_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V364_HAL_SERVICE_READINESS_GATE_2026-05-20.md`
- evidence:
  - plan: `tmp/wifi/v364-hal-service-readiness-gate-plan-20260520/`
  - live: `tmp/wifi/v364-hal-service-readiness-gate-live-20260520/`
- boot image: 없음. v364는 host-side read-only readiness gate이며 native init version 변경 없음
- validation:
  - plan decision `hal-service-readiness-gate-plan-ready`
  - live decision `hal-service-readiness-blocked`
  - native baseline `A90 Linux init 0.9.61 (v319)`
  - `wlan*`/wiphy surface absent
  - Wi-Fi rfkill absent
  - CNSS process leak absent
- blockers:
  - current Binder devnodes absent
  - service-manager processes absent
  - mutable property runtime absent
  - linkerconfig visibility missing
- warnings/useful evidence:
  - service binary visibility partial: `servicemanager`, `hwservicemanager`, `wificond`
  - Wi-Fi VINTF metadata present, `61` matching lines
- interpretation:
  - V292/V320/V362/V363 prerequisites are useful but not enough for HAL/service start-only
  - next blocker is Android service runtime and private namespace readiness
- next:
  - V365 candidate: bounded Binder/property/linker namespace readiness repair or approval packet
  - do not run Wi-Fi HAL/service-manager, scan/connect/credential/DHCP/routing before that gate


### V365. Service Runtime Repair Packet — PASS

- 계획: `docs/plans/NATIVE_INIT_V365_SERVICE_RUNTIME_REPAIR_PACKET_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V365_SERVICE_RUNTIME_REPAIR_PACKET_2026-05-20.md`
- evidence:
  - plan: `tmp/wifi/v365-service-runtime-repair-packet-plan-20260520/`
  - initial live: `tmp/wifi/v365-service-runtime-repair-packet-live-20260520/`
  - corrected live: `tmp/wifi/v365-service-runtime-repair-packet-live-20260520-r2/`
- boot image: 없음. v365는 host-side packet builder이며 native init version 변경 없음
- validation:
  - plan decision `service-runtime-repair-packet-plan-ready`
  - corrected live decision `service-runtime-repair-packet-ready`
  - first live correctly exposed `/dev/block/sda29` node absence as a repair input gap
  - corrected script classifies `/proc/partitions` `sda29` major/minor `259:13` as temporary `mknodb` candidate
  - helper, real linkerconfig, real apex libraries config, private property root, system root, `servicemanager`, and `hwservicemanager` binaries are present
  - current Binder devnodes absent/clean, service-manager process absent/clean, CNSS process absent/clean, Wi-Fi link surface absent/clean
- next approval phrase:
  - `approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up`
- next:
  - V366 candidate: bounded temporary device-node + private property/linker repair smoke
  - do not run service-manager/HAL/scan/connect before V366 passes and a later separate approval packet exists


### V366. Guarded Runtime Repair Smoke — APPROVAL REQUIRED

- 계획: `docs/plans/NATIVE_INIT_V366_RUNTIME_REPAIR_SMOKE_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V366_RUNTIME_REPAIR_SMOKE_2026-05-20.md`
- evidence:
  - initial plan: `tmp/wifi/v366-runtime-repair-smoke-plan-20260520/`
  - corrected plan: `tmp/wifi/v366-runtime-repair-smoke-plan-20260520-r2/`
  - preflight: `tmp/wifi/v366-runtime-repair-smoke-preflight-20260520/`
  - no-approval run: `tmp/wifi/v366-runtime-repair-smoke-refusal-20260520/`
- boot image: 없음. v366은 host-side guarded smoke runner이며 native init version 변경 없음
- validation:
  - corrected plan decision `runtime-repair-smoke-plan-ready`
  - preflight decision `runtime-repair-smoke-preflight-ready`
  - no-approval run decision `runtime-repair-smoke-approval-required`
  - no-approval run performed no mutation steps: no temporary `/dev` node creation and no property lookup
  - safety refresh added `preexisting-temp-nodes` blocker; current live state is `present=[]`
  - live preflight confirmed helper/linkerconfig/property/system-root inputs and `/proc/partitions` `sda29` metadata `259:13`
  - post/preflight service-manager, CNSS, and Wi-Fi link surfaces remain clean/absent
- next approval phrase:
  - `approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up`
- next:
  - V366 approved smoke remains pending until exact phrase is supplied
  - even approved V366 is only temporary node creation, private property lookup, cleanup, and postflight cleanliness
  - do not run service-manager/HAL/scan/connect before V366 approved smoke passes and a later separate approval packet exists


### V367. Runtime Repair Smoke Gate Regression — PASS

- 계획: `docs/plans/NATIVE_INIT_V367_RUNTIME_REPAIR_SMOKE_REGRESSION_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V367_RUNTIME_REPAIR_SMOKE_REGRESSION_2026-05-20.md`
- evidence:
  - regression: `tmp/wifi/v367-runtime-repair-smoke-regression-20260520-010304/`
  - live no-approval refresh: `tmp/wifi/v367-v366-refusal-refresh-20260520-010326/`
- boot image: 없음. v367은 host-only regression + V366 runner ordering fix
- validation:
  - regression decision `runtime-repair-smoke-regression-pass`
  - live no-approval refresh decision `runtime-repair-smoke-approval-required`
  - exact approval + clean synthetic path reaches create/stat/property/cleanup calls
  - exact approval + preexisting vendor/binder node blocks before mutation calls
  - no live mutation, service-manager/HAL/scan/connect execution 없음
- next:
  - V366 approved live smoke remains pending until exact phrase is supplied
  - do not run service-manager/HAL/scan/connect before V366 approved smoke passes and a later separate approval packet exists


### V368. Runtime Repair Cleanup Approval Gate — PASS

- 계획: `docs/plans/NATIVE_INIT_V368_RUNTIME_REPAIR_CLEANUP_GATE_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V368_RUNTIME_REPAIR_CLEANUP_GATE_2026-05-20.md`
- evidence:
  - regression: `tmp/wifi/v368-runtime-repair-cleanup-gate-regression-20260520-010744/`
  - cleanup refusal: `tmp/wifi/v368-cleanup-refusal-live-20260520-010802/`
  - run refusal refresh: `tmp/wifi/v368-run-refusal-live-20260520-010802/`
- boot image: 없음. v368은 V366 host runner cleanup safety patch
- validation:
  - regression decision `runtime-repair-smoke-regression-pass`
  - cleanup refusal decision `runtime-repair-smoke-cleanup-approval-required` with `steps=[]`
  - run refusal decision `runtime-repair-smoke-approval-required`
  - no live mutation, service-manager/HAL/scan/connect execution 없음
- next:
  - V366 approved live smoke or cleanup remains pending until exact phrase is supplied
  - do not run service-manager/HAL/scan/connect before V366 approved smoke passes and a later separate approval packet exists


### V369. Runtime Repair Smoke Approval Packet — PASS

- 계획: `docs/plans/NATIVE_INIT_V369_RUNTIME_REPAIR_APPROVAL_PACKET_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V369_RUNTIME_REPAIR_APPROVAL_PACKET_2026-05-20.md`
- evidence:
  - approval packet: `tmp/wifi/v369-runtime-repair-smoke-approval-packet-final-20260520-011223/`
- boot image: 없음. v369는 V366 live smoke approval packet generator
- validation:
  - packet decision `runtime-repair-smoke-approval-packet-ready`
  - preflight `runtime-repair-smoke-preflight-ready`
  - run refusal `runtime-repair-smoke-approval-required`
  - cleanup refusal `runtime-repair-smoke-cleanup-approval-required` with `steps=0`
  - regression `runtime-repair-smoke-regression-pass`
  - generated run/cleanup commands pass `bash -n` and contain exact phrase + `--apply --assume-yes`
  - `live_execution_approved=false`, `device_mutations=false`
- next:
  - exact approval phrase can now be used with the generated command if operator accepts the V366 boundary
  - do not run service-manager/HAL/scan/connect before V366 approved smoke passes and a later separate approval packet exists


### V370. Runtime Repair Smoke Result Router — PASS

- 계획: `docs/plans/NATIVE_INIT_V370_RUNTIME_REPAIR_RESULT_ROUTER_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V370_RUNTIME_REPAIR_RESULT_ROUTER_2026-05-20.md`
- evidence:
  - route: `tmp/wifi/v370-runtime-repair-smoke-result-router-route-20260520-011726/`
  - regression: `tmp/wifi/v370-runtime-repair-smoke-result-router-regression-20260520-011726/`
- boot image: 없음. v370은 host-only result router
- validation:
  - current route decision `runtime-repair-smoke-router-awaiting-approval`
  - regression decision `runtime-repair-smoke-router-regression-pass`
  - awaiting/refusal/preexisting-blocker/pass-next-ready/cleanup-failed/unexpected cases PASS
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - exact approval phrase remains the only current blocker for V366 live smoke
  - if V366 smoke later passes, router target becomes separate service-manager start-only approval packet; still no HAL/scan/connect

### V371. Runtime Repair Smoke Live Executor — PASS

- 계획: `docs/plans/NATIVE_INIT_V371_RUNTIME_REPAIR_SMOKE_LIVE_EXECUTOR_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V371_RUNTIME_REPAIR_SMOKE_LIVE_EXECUTOR_2026-05-20.md`
- evidence:
  - approved run: `tmp/wifi/v371-runtime-repair-smoke-live-executor-run-20260520-012422/`
  - v366 live smoke: `tmp/wifi/v366-runtime-repair-smoke-live-approved/`
  - no-approval run refusal: `tmp/wifi/v371-runtime-repair-smoke-live-executor-run-refusal-20260520-012723/`
  - no-approval cleanup refusal: `tmp/wifi/v371-runtime-repair-smoke-live-executor-cleanup-refusal-20260520-012723/`
  - current plan route: `tmp/wifi/v371-runtime-repair-smoke-live-executor-plan-20260520-012723/`
- boot image: 없음. v371은 host-side live executor이며 native init version 변경 없음
- validation:
  - approved run decision `runtime-repair-smoke-live-executor-run-pass`
  - V366 live smoke decision `runtime-repair-smoke-pass`
  - result router decision `runtime-repair-smoke-router-service-runtime-next-ready`
  - run/cleanup without exact approval phrase both refuse before mutation
  - current plan route recognizes already-passed smoke as `runtime-repair-smoke-live-executor-current-next-ready`
  - postflight `status` and `selftest` return `rc=0/status=ok`, selftest `fail=0`
  - no service-manager/HAL/scan/connect/link-up execution
- next:
  - create separate service-manager start-only approval packet
  - keep Wi-Fi HAL start, scan/connect/link-up, credentials, DHCP, and routing blocked until later explicit plan/approval

### V372. Service-Manager Start-Only Approval Packet — PASS

- 계획: `docs/plans/NATIVE_INIT_V372_SERVICE_MANAGER_START_ONLY_APPROVAL_PACKET_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V372_SERVICE_MANAGER_START_ONLY_APPROVAL_PACKET_2026-05-20.md`
- evidence:
  - plan: `tmp/wifi/v372-service-manager-start-only-approval-packet-plan-20260520-013401/`
  - live read-only packet: `tmp/wifi/v372-service-manager-start-only-approval-packet-live-20260520-013344/`
- boot image: 없음. v372는 host-side approval packet generator이며 native init version 변경 없음
- validation:
  - plan decision `service-manager-start-only-approval-packet-plan-ready`
  - live read-only decision `service-manager-start-only-approval-packet-ready`
  - V371 live executor pass and V366 smoke pass are both checked
  - current native status/selftest clean with `fail=0`
  - `servicemanager` and `hwservicemanager` binary visibility checked
  - service-manager process surface, Wi-Fi link surface, and temporary Binder nodes clean
  - `live_execution_approved=false`, `device_mutations=false`
- next approval phrase:
  - `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up`
- next:
  - implement V373 fail-closed service-manager start-only smoke runner
  - do not start Wi-Fi HAL, scan/connect/link-up, credentials, DHCP, or routing

### V373. Service-Manager Start-Only Smoke Runner Scaffold — PASS / BLOCKED BEFORE MUTATION

- 계획: `docs/plans/NATIVE_INIT_V373_SERVICE_MANAGER_START_ONLY_SMOKE_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V373_SERVICE_MANAGER_START_ONLY_SMOKE_2026-05-20.md`
- evidence:
  - plan: `tmp/wifi/v373-service-manager-start-only-smoke-plan-20260520-013827/`
  - preflight: `tmp/wifi/v373-service-manager-start-only-smoke-preflight-20260520-013827/`
  - no-approval run: `tmp/wifi/v373-service-manager-start-only-smoke-refusal-20260520-013827/`
- boot image: 없음. v373은 host-side runner scaffold이며 native init version 변경 없음
- validation:
  - plan decision `service-manager-start-only-smoke-plan-ready`
  - preflight decision `service-manager-start-only-smoke-blocked`
  - no-approval run decision `service-manager-start-only-smoke-approval-required` with `steps=0`
  - preflight confirms V372 packet, native status/selftest, service-manager binaries, clean process surface, clean Wi-Fi link surface, and cleaned temporary Binder nodes
  - current blocker is `helper-service-manager-mode`: deployed `a90_android_execns_probe` does not yet advertise bounded service-manager start-only mode
  - `daemon_start_executed=false`, `device_mutations=false`
- next:
  - V374: add or design bounded service-manager start-only mode for `a90_android_execns_probe`
  - do not run service-manager live until helper mode and approval-gated runner both pass

### V374. Execns Service-Manager Start-Only Mode — PASS / DEPLOY PENDING

- 계획: `docs/plans/NATIVE_INIT_V374_EXECNS_SERVICE_MANAGER_MODE_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V374_EXECNS_SERVICE_MANAGER_MODE_2026-05-20.md`
- evidence:
  - built helper: `tmp/wifi/v374-a90_android_execns_probe-v12/a90_android_execns_probe`
  - source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- boot image: 없음. v374는 helper source/build update이며 native init version 변경 없음
- validation:
  - static ARM64 build PASS
  - no dynamic section PASS
  - marker `a90_android_execns_probe v12` PASS
  - strings include `service-manager-start-only`, `--allow-service-manager-start-only`, `system-servicemanager`, and `system-hwservicemanager`
  - artifact sha256 `fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918`
  - no `/cache/bin` deploy and no daemon execution in V374
- next:
  - V375 helper deploy/preflight packet: install v12 to `/cache/bin/a90_android_execns_probe`, verify remote marker/SHA-256, and rerun V373 preflight
  - service-manager live start remains blocked until deploy evidence and exact V373 approval are present

### V375. Execns Helper v12 Deploy Preflight — PASS

- 계획: `docs/plans/NATIVE_INIT_V375_EXECNS_HELPER_V12_DEPLOY_PREFLIGHT_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V375_EXECNS_HELPER_V12_DEPLOY_PREFLIGHT_2026-05-20.md`
- evidence:
  - plan: `tmp/wifi/v375-plan-smoke/`
  - preflight: `tmp/wifi/v375-preflight-20260520-015315/`
  - approved blocked run: `tmp/wifi/v375-approved-run-blocked-20260520-015737/`
  - serial fallback failure: `tmp/wifi/v375-deploy-serial-20260520-020309/`
  - serial fallback pass: `tmp/wifi/v375-deploy-serial2-20260520-020415/`
  - postdeploy V375 preflight: `tmp/wifi/v375-postdeploy-preflight-20260520-021126/`
  - postdeploy V373 preflight: `tmp/wifi/v375-v373-postdeploy-preflight-20260520-021126/`
- boot image: 없음. v375는 host-side helper deploy/preflight runner이며 native init version 변경 없음
- validation:
  - V375 runner plan PASS
  - Python compile PASS
  - local v12 helper SHA/marker/service-manager mode PASS
  - native `version`/`status`/`selftest` PASS
  - service-manager process surface clean PASS
  - Wi-Fi link surface clean PASS
  - first approved run blocked safely when NCM host IPv4 was absent
  - NCM-independent serial fallback added and validated through `appendfile` + `toybox uudecode -o`
  - remote helper SHA now matches `fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918`
  - remote helper usage now includes `a90_android_execns_probe v12`, `--allow-service-manager-start-only`, and `service-manager-start-only`
  - V373 post-deploy preflight decision `service-manager-start-only-smoke-approval-required`
  - repeated V375 post-deploy preflight decision `execns-helper-v12-deploy-preflight-ready`
  - V373 `helper-service-manager-mode` PASS
- required deploy phrase:
  - `approve v375 deploy execns helper v12 only; no daemon start and no Wi-Fi bring-up`
- next:
  - V373 service-manager start-only smoke can be run only with separate exact approval phrase
  - Wi-Fi HAL start and Wi-Fi bring-up remain blocked


### V376. Service-Manager Start-Only Live Runner — LIVE PASS / RUNTIME GAP

- 계획: `docs/plans/NATIVE_INIT_V376_SERVICE_MANAGER_START_ONLY_LIVE_RUNNER_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V376_SERVICE_MANAGER_START_ONLY_LIVE_RUNNER_2026-05-20.md`
- evidence:
  - plan: `tmp/wifi/v376-plan-20260520-021643/`
  - preflight: `tmp/wifi/v376-preflight-20260520-021643/`
  - no-approval run: `tmp/wifi/v376-refusal-20260520-021651/`
  - approved live run: `tmp/wifi/v376-approved-run-20260520-022612/`
- boot image: 없음. v376은 host-side service-manager start-only live runner이며 native init version 변경 없음
- validation:
  - Python compile PASS
  - plan decision `service-manager-start-only-live-plan-ready`
  - preflight decision `service-manager-start-only-live-preflight-ready`
  - no-approval run decision `service-manager-start-only-live-approval-required` with `steps=0`
  - native `version`/`status`/`selftest` PASS
  - remote helper v12 SHA/usage PASS
  - `servicemanager` and `hwservicemanager` binary visibility PASS
  - process surface, Wi-Fi link surface, and temporary Binder node preflight clean PASS
  - approved live decision `service-manager-start-only-live-runtime-gap`
  - both service-manager targets aborted with `SIGABRT` before observe window
  - first hard blocker: Binder driver `/dev/binder` unavailable inside helper namespace
  - postflight clean: `manager_processes=0`, `wifi_links=0`
  - `daemon_start_executed=true`, `wifi_bringup_executed=false`
- next:
  - classify/fix runtime gap before HAL start-only approval packet
  - Wi-Fi HAL start and Wi-Fi bring-up remain blocked


### V377. Service-Manager Start-Only Result Router — PASS / RUNTIME GAP ROUTED

- 계획: `docs/plans/NATIVE_INIT_V377_SERVICE_MANAGER_RESULT_ROUTER_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V377_SERVICE_MANAGER_RESULT_ROUTER_2026-05-20.md`
- evidence:
  - regression: `tmp/wifi/v377-service-manager-start-only-router-regression-20260520-022406/`
  - route: `tmp/wifi/v377-service-manager-start-only-router-route-20260520-022406/`
  - after-approved route: `tmp/wifi/v377-service-manager-start-only-router-after-approved-20260520-022647/`
- boot image: 없음. v377은 host-only result router이며 native init version 변경 없음
- validation:
  - Python compile PASS
  - regression decision `service-manager-start-only-router-regression-pass`
  - initial route decision `service-manager-start-only-router-awaiting-approval`
  - after-approved route decision `service-manager-start-only-router-runtime-gap`
  - `device_commands_executed=false`, `device_mutations=false`
- next:
  - V378 runtime-gap classifier/repair planning으로 진행
  - private Binder devnode namespace gap을 해결하기 전 HAL start-only approval packet 금지
  - Wi-Fi HAL start and Wi-Fi bring-up remain blocked


### V378. Service-Manager Runtime Gap Classifier — PASS

- 계획: `docs/plans/NATIVE_INIT_V378_SERVICE_MANAGER_RUNTIME_GAP_CLASSIFIER_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V378_SERVICE_MANAGER_RUNTIME_GAP_CLASSIFIER_2026-05-20.md`
- evidence:
  - regression: `tmp/wifi/v378-service-manager-runtime-gap-classifier-regression-20260520-023043/`
  - live classify: `tmp/wifi/v378-service-manager-runtime-gap-classifier-live-20260520-023043/`
  - current Binder metadata refresh: `tmp/wifi/v378-current-binder-devnode-feasibility-20260520-023057/`
- boot image: 없음. v378은 host-only classifier/read-only Binder metadata refresh이며 native init version 변경 없음
- validation:
  - Python compile PASS
  - classifier regression decision `service-manager-runtime-gap-classifier-regression-pass`
  - live classify decision `service-manager-runtime-gap-binder-devnode-required`
  - current Binder metadata decision `binder-devnode-plan-ready`
  - Binder candidates remain `/dev/binder c 10 81`, `/dev/hwbinder c 10 80`, `/dev/vndbinder c 10 79`
  - `device_mutations=false`, Wi-Fi bring-up 없음
- next:
  - V379 helper-private Binder devnode provisioning for service-manager start-only mode
  - HAL start-only approval packet remains blocked


### V379. Execns Private Binder Devnodes — LOCAL PASS

- 계획: `docs/plans/NATIVE_INIT_V379_EXECNS_PRIVATE_BINDER_DEVNODES_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V379_EXECNS_PRIVATE_BINDER_DEVNODES_2026-05-20.md`
- helper: `a90_android_execns_probe v13`
- artifact: `tmp/wifi/v379-a90_android_execns_probe-v13/a90_android_execns_probe`
- sha256: `9866c8f1e7c346906f4a400ee431ea35ed3880c157e5ee4e8b1757377dcfffa8`
- validation:
  - static ARM64 build PASS
  - required strings PASS
  - no dynamic section PASS
  - `git diff --check` PASS
  - host Python py_compile PASS
- scope:
  - local helper source/build only
  - no `/cache/bin` deploy
  - no daemon start
  - no Wi-Fi HAL start or Wi-Fi bring-up
- next:
  - V380 deploy v13 and rerun service-manager start-only preflight


### V380. Execns Helper V13 Deploy + Start-Only Live — PASS / RUNTIME GAP

- 계획: `docs/plans/NATIVE_INIT_V380_EXECNS_HELPER_V13_DEPLOY_LIVE_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V380_EXECNS_HELPER_V13_DEPLOY_LIVE_2026-05-20.md`
- evidence root: `tmp/wifi/v380-v13-deploy-and-live-20260520-024112/`
- deploy:
  - serial fallback `appendfile + uudecode`
  - remote SHA `9866c8f1e7c346906f4a400ee431ea35ed3880c157e5ee4e8b1757377dcfffa8`
  - daemon start 없음, Wi-Fi bring-up 없음
- live:
  - decision `service-manager-start-only-live-runtime-gap`
  - `system-servicemanager`: runtime gap, SIGABRT
  - `system-hwservicemanager`: start-only pass, clean stop
  - postflight clean
  - Wi-Fi bring-up 없음
- classification:
  - decision `service-manager-runtime-gap-property-runtime-required`
  - Binder private devnodes now present in namespace: `binder/hwbinder/vndbinder` mode `0666`
  - next blocker: `/dev/__properties__` and minimal `/data` runtime expectations
- next:
  - V381 private property/runtime materialization plan


### V381. Execns Service Property Runtime — LOCAL PASS

- 계획: `docs/plans/NATIVE_INIT_V381_EXECNS_SERVICE_PROPERTY_RUNTIME_PLAN_2026-05-20.md`
- 보고서: `docs/reports/NATIVE_INIT_V381_EXECNS_SERVICE_PROPERTY_RUNTIME_2026-05-20.md`
- helper: `a90_android_execns_probe v14`
- artifact: `tmp/wifi/v381-a90_android_execns_probe-v14/a90_android_execns_probe`
- sha256: `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7`
- validation:
  - static ARM64 build PASS
  - required strings PASS
  - no dynamic section PASS
  - `git diff --check` PASS
- scope:
  - local helper source/build only
  - no `/cache/bin` deploy
  - no daemon start
  - no Wi-Fi HAL start or Wi-Fi bring-up
- next:
  - V382 deploy v14 and rerun service-manager start-only with private property root and private-empty `/data`


### V382. Execns Helper V14 Deploy + Property Runtime Start-Only — READY / APPROVAL REQUIRED

- 계획: `docs/plans/NATIVE_INIT_V382_EXECNS_HELPER_V14_DEPLOY_LIVE_PLAN_2026-05-20.md`
- 준비 보고서: `docs/reports/NATIVE_INIT_V382_RUNTIME_PROFILE_WRAPPER_2026-05-20.md`
- 라우터 보고서: `docs/reports/NATIVE_INIT_V382_RESULT_ROUTER_2026-05-20.md`
- final readiness 보고서: `docs/reports/NATIVE_INIT_V382_FINAL_READINESS_2026-05-20.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py`
- live wrapper: `scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py`
- result router: `scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py`
- final readiness: `scripts/revalidation/wifi_v382_final_readiness.py`
- helper: `a90_android_execns_probe v14`
- artifact: `tmp/wifi/v381-a90_android_execns_probe-v14/a90_android_execns_probe`
- sha256: `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7`
- boundary:
  - deploy approval: `approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up`
  - live approval: `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up`
- scope:
  - deploy one helper binary to `/cache/bin/a90_android_execns_probe`
  - rerun service-manager start-only through the v382 live wrapper with private property root + private-empty `/data`
  - no Wi-Fi HAL start, scan, connect, DHCP, routing, or credential operation
- local readiness:
  - V382 live wrapper plan PASS
  - V382 live wrapper preflight blocked only by remote helper v14 not deployed
  - V382 result router regression PASS and no-approval route awaits exact live approval
  - V382 final readiness gate added; dirty-tree pre-commit run blocks as designed
  - property root visible and `private-empty` data profile included in planned argv
- next:
  - execute V382 only after explicit approval; if runtime gap remains, classify before HAL readiness

### V187. Harness Broker Backend — PASS

- 보고서: `docs/reports/NATIVE_INIT_V187_HARNESS_BROKER_BACKEND_2026-05-11.md`
- baseline device build: `A90 Linux init 0.9.59 (v159)`
- device flash: 없음. v187은 host harness backend integration이며 별도 native-init boot image 없음
- 구현:
  - `a90harness.device.DeviceClient`에 `backend=direct|broker` 추가
  - broker backend은 `A90B1` Unix socket으로 request id/client id/argv/timeout을 전달
  - direct backend은 기존 `run_cmdv1_command()` 경로 유지
  - `native_test_supervisor.py`에 `--device-backend broker`, `--broker-runtime-dir`, `--broker-socket` 옵션 추가
  - supervisor manifest에 `device_client` metadata 기록
- 남은 검증:
  - 없음
- 검증:
  - Python compile PASS
  - live broker-backed supervisor `smoke` PASS
  - live broker-backed supervisor `observe --max-cycles 1` PASS
  - broker option mixed-soak dry-run PASS
  - evidence: `tmp/a90-v187-broker.7GzqCq/`, `tmp/a90-v187-dry.yGivGM/`
- 다음 실행 항목: v188 broker audit/reporting or NCM/tcpctl backend selection

### Planned. v178-v184 Mixed Soak / Serverization Gate Cycle

- 로드맵: `docs/plans/NATIVE_INIT_V178_V184_MIXED_SOAK_SECURITY_ROADMAP_2026-05-09.md`
- v178 세부 계획: `docs/plans/NATIVE_INIT_V178_POST_SECURITY_BASELINE_PLAN_2026-05-09.md`
- baseline: `A90 Linux init 0.9.59 (v159)`
- versioning note: v178-v184는 device firmware bump가 아니라 v159 device 위 host harness / mixed-soak gate cycle이다
- 의도: Wi-Fi 연결과 서버화 전에 host/device 장시간 혼합 안정성, 네트워크 노출 안전성, 증거 수집 신뢰성을 검증 가능한 기준으로 만든다.
- 현재 증거:
  - v160-v169 개별 안정성 PASS/DEFERRED 정리와 v170-v177 host harness completion audit PASS는 보안 패치 전 historical baseline으로 유지한다.
  - F038-F044 host harness 보안 패치 완료: `0b8e9bc`, `c214478`, `952e572`, `fafa6d6`.
  - local targeted rescan: `docs/security/scans/SECURITY_FRESH_SCAN_F038_F044_2026-05-09.md`, PASS=27 WARN=1 FAIL=0.
  - v179 mixed-soak scheduler foundation PASS.
  - v180 CPU/memory workload profiles PASS.
  - v181 full NCM/TCP + storage mixed run PASS.
  - v182 failure classifier and interrupt-safe partial bundle PASS.
  - v183 8h pilot mixed soak PASS.
  - v184 24h+ readiness gate PASS.
- 계획 순서:
  - 완료: v178 Post-Security Harness Baseline
  - 완료: v179 Mixed Soak Scheduler Foundation
  - 완료: v180 CPU/Memory Workload Profiles
  - 완료: v181 NCM/TCP + Storage Workload Integration
  - 완료: v182 Failure Classifier + Recovery Policy
  - 완료: v183 8h Pilot Mixed Soak
  - 완료: v184 24h+ Serverization Readiness Gate
- guardrails: Wi-Fi enablement/rfkill write/module load/firmware mutation/public listener/watchdog open/destructive partition write 금지, ACM rescue 유지, evidence private/no-follow 유지.
- 다음 실행 항목: v185 Communication Broker Protocol Plan

### Planned. v170-v177 Host Test Harness Cycle

- 로드맵: `docs/plans/NATIVE_INIT_V170_V177_HARNESS_ROADMAP_2026-05-09.md`
- v170 계획: `docs/plans/NATIVE_INIT_V170_HARNESS_FOUNDATION_PLAN_2026-05-09.md`
- v171 계획: `docs/plans/NATIVE_INIT_V171_OBSERVER_API_PLAN_2026-05-09.md`
- v172 계획: `docs/plans/NATIVE_INIT_V172_MODULE_RUNNER_PLAN_2026-05-09.md`
- v173 계획: `docs/plans/NATIVE_INIT_V173_STORAGE_CPU_MODULES_PLAN_2026-05-09.md`
- v174 계획: `docs/plans/NATIVE_INIT_V174_USB_NCM_MODULES_PLAN_2026-05-09.md`
- v175 계획: `docs/plans/NATIVE_INIT_V175_UNIFIED_EVIDENCE_BUNDLE_PLAN_2026-05-09.md`
- v176 계획: `docs/plans/NATIVE_INIT_V176_LONG_RUN_SUPERVISOR_PLAN_2026-05-09.md`
- v177 계획: `docs/plans/NATIVE_INIT_V177_SAFETY_GATE_PLAN_2026-05-09.md`
- baseline: `A90 Linux init 0.9.59 (v159)`
- 의도: Wi-Fi baseline refresh 전에 테스트 실행자와 관찰자를 분리하고, 기존 host validators를 공용 하네스 위로 단계적으로 올린다.
- 현재 증거: v177 safety gate까지 PASS.
- 계획 순서:
  - 완료: v170 Harness Foundation
  - 완료: v171 Observer API
  - 완료: v172 Module Runner
  - 완료: v173 Storage/CPU Module Port
  - 완료: v174 USB/NCM Module Port
  - 완료: v175 Unified Evidence Bundle
  - 완료: v176 Long-Run Supervisor
  - 완료: v177 Safety Gate / Dry-Run Policy
- guardrails: observer는 read-only, serial command single-writer, side effect는 module에만 허용, evidence private/no-follow 유지.
- 다음 실행 항목: v184 24h+ Serverization Readiness Gate

### Planned. v162-v169 Stability Test Cycle

- 로드맵: `docs/plans/NATIVE_INIT_V160_V169_STABILITY_ROADMAP_2026-05-09.md`
- v160 계획: `docs/plans/NATIVE_INIT_V160_NCM_TCP_STABILITY_PLAN_2026-05-09.md`
- v161 계획: `docs/plans/NATIVE_INIT_V161_STORAGE_IO_INTEGRITY_PLAN_2026-05-09.md`
- v162 계획: `docs/plans/NATIVE_INIT_V162_PROCESS_CONCURRENCY_PLAN_2026-05-09.md`
- v163 계획: `docs/plans/NATIVE_INIT_V163_CPU_MEM_THERMAL_PLAN_2026-05-09.md`
- v164 계획: `docs/plans/NATIVE_INIT_V164_SCHED_LATENCY_PLAN_2026-05-09.md`
- v165 계획: `docs/plans/NATIVE_INIT_V165_USB_RECOVERY_PLAN_2026-05-09.md`
- v166 계획: `docs/plans/NATIVE_INIT_V166_NETWORK_THROUGHPUT_PLAN_2026-05-09.md`
- v167 계획: `docs/plans/NATIVE_INIT_V167_FS_EXERCISER_PLAN_2026-05-09.md`
- v168 계획: `docs/plans/NATIVE_INIT_V168_KSELFTEST_FEASIBILITY_PLAN_2026-05-09.md`
- v169 계획: `docs/plans/NATIVE_INIT_V169_FAULT_DEBUG_FEASIBILITY_PLAN_2026-05-09.md`
- 완료 감사: `docs/reports/NATIVE_INIT_V160_V169_COMPLETION_AUDIT_2026-05-09.md`
- baseline: `A90 Linux init 0.9.59 (v159)`
- 의도: Wi-Fi baseline refresh 전에 커널/PID1/SD/USB/NCM/helper lifecycle 안정성 기준선을 만든다.
- 현재 증거: v160-v169 stability cycle 완료. v159 idle longsoak 약 15.77시간 PASS, v160 TCP soak PASS, v161-v167 stability profiles PASS, v168/v169 feasibility PASS.
- 계획 순서: 완료
- guardrails: ACM rescue 유지, Wi-Fi enablement/partition write/watchdog open/active tracing 금지, host evidence private output 유지.
- 다음 실행 항목: v170-v177 Host Test Harness Cycle

### V158. Watchdog Read-only Feasibility — DONE

- 계획: `docs/plans/NATIVE_INIT_V158_WATCHDOG_FEASIBILITY_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V158_WATCHDOG_FEASIBILITY_2026-05-08.md`
- build: `A90 Linux init 0.9.58 (v158)`
- 의도: watchdog class/device/sysfs/cmdline 상태를 `/dev/watchdog*` open 없이 read-only로 수집
- 검증: real-device flash PASS, `watchdoginv full` PASS, `watchdog_feas_collect.py` PASS, integrated PASS, static checks PASS
- 다음 실행 항목: v159 Tracefs/Ftrace Feasibility

### V157. Pstore/Ramoops Feasibility — DONE

- 계획: `docs/plans/NATIVE_INIT_V157_PSTORE_FEASIBILITY_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V157_PSTORE_FEASIBILITY_2026-05-08.md`
- build: `A90 Linux init 0.9.57 (v157)`
- 의도: pstore/ramoops support, mount state, entry count, cmdline/module hint를 read-only로 수집
- 검증: real-device flash PASS, `pstore full` PASS, `pstore_feas_collect.py` PASS, integrated PASS, static checks PASS
- 다음 실행 항목: v158 Watchdog Read-only Feasibility

### V156. Thermal/Power Sensor Map — DONE

- 계획: `docs/plans/NATIVE_INIT_V156_THERMAL_POWER_SENSOR_MAP_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V156_THERMAL_POWER_SENSOR_MAP_2026-05-08.md`
- build: `A90 Linux init 0.9.56 (v156)`
- 의도: thermal zones, cooling devices, power_supply 속성을 장시간 안정성 판단용 read-only map으로 수집
- 검증: real-device flash PASS, `sensormap` PASS, `sensor_map_collect.py` PASS, integrated PASS, static checks PASS
- 다음 실행 항목: v157 Pstore/Ramoops Feasibility

### V155. Kernel Diagnostics Bundle — DONE

- 계획: `docs/plans/NATIVE_INIT_V155_KERNEL_DIAG_BUNDLE_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V155_KERNEL_DIAG_BUNDLE_2026-05-08.md`
- build: `A90 Linux init 0.9.55 (v155)`
- 의도: kernelinv/diag/longsoak/exposure/wifiinv/wififeas read-only evidence를 private host bundle로 통합
- 검증: real-device flash PASS, `kernel_diag_bundle.py` PASS, `kernel_inventory_collect.py` PASS, integrated PASS, static checks PASS
- 다음 실행 항목: v156 Thermal/Power Sensor Map

### V154. Kernel Capability Inventory — DONE

- 계획: `docs/plans/NATIVE_INIT_V154_KERNEL_INVENTORY_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V154_KERNEL_INVENTORY_2026-05-08.md`
- build: `A90 Linux init 0.9.54 (v154)`
- 의도: `/proc/config.gz`, filesystems, mounts, pstore, tracefs, watchdog, cgroup, thermal, power_supply, USB gadget 상태를 read-only inventory로 수집
- 검증: real-device flash PASS, `kernelinv full` PASS, host `kernel_inventory_collect.py` PASS, integrated PASS, static checks PASS
- 다음 실행 항목: v155 Kernel Diagnostics Bundle

### V153. Longsoak Security — DONE

- 계획: `docs/plans/NATIVE_INIT_V153_LONGSOAK_SECURITY_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V153_LONGSOAK_SECURITY_2026-05-08.md`
- build: `A90 Linux init 0.9.53 (v153)`
- 의도: F034-F037 longsoak export/helper/status/bundle 보안 이슈 완화
- 검증: real-device flash PASS, helper symlink PoC PASS, host bundle private/no-follow PASS, longsoak PASS, correlation PASS, classifier PASS, bundle PASS, integrated PASS, quick soak PASS, security scan PASS=21/WARN=1/FAIL=0
- 다음 실행 항목: v154 Kernel Capability Inventory 또는 장시간 long-soak 운영

### V152. Power/Thermal Trend — DONE

- 계획: `docs/plans/NATIVE_INIT_V152_POWER_THERMAL_TREND_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V152_POWER_THERMAL_TREND_2026-05-08.md`
- build: `A90 Linux init 0.9.52 (v152)`
- 의도: longsoak device JSONL에서 battery/power/CPU/GPU/memory/load first/last/min/max/delta/avg trend 산출
- 검증: real-device flash PASS, longsoak PASS, correlation PASS, trend-check PASS, classifier PASS, bundle PASS, integrated PASS, quick soak PASS, security scan PASS=17/WARN=1/FAIL=0
- 다음 실행 항목: 8h/24h long-soak 운영 또는 다음 기능개발 후보 선정

### V151. Long Soak Report Bundle — DONE

- 계획: `docs/plans/NATIVE_INIT_V151_LONG_SOAK_BUNDLE_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V151_LONG_SOAK_BUNDLE_2026-05-08.md`
- build: `A90 Linux init 0.9.51 (v151)`
- 의도: host/device longsoak evidence, disconnect classifier, live status transcript를 한 번에 묶는 handoff bundle 생성
- 검증: real-device flash PASS, longsoak PASS, correlation PASS, classifier PASS, bundle PASS missing=0 failed_commands=0, integrated PASS, quick soak PASS, security scan PASS=17/WARN=1/FAIL=0
- 다음 실행 항목: v152 Power/Thermal Trend

### V150. Host Disconnect Classifier — DONE

- 계획: `docs/plans/NATIVE_INIT_V150_HOST_DISCONNECT_CLASSIFIER_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V150_HOST_DISCONNECT_CLASSIFIER_2026-05-08.md`
- build: `A90 Linux init 0.9.50 (v150)`
- 의도: host 관점에서 serial bridge/cmdv1/NCM/longsoak evidence를 분리해 disconnect 원인 분류
- 검증: real-device flash PASS, classifier PASS classification=`serial-ok-ncm-down-or-inactive`, longsoak PASS, integrated PASS, quick soak PASS, security scan PASS=17/WARN=1/FAIL=0
- 다음 실행 항목: v151 Long Soak Report Bundle

### V149. Long Soak Supervisor — DONE

- 계획: `docs/plans/NATIVE_INIT_V149_LONG_SOAK_SUPERVISOR_PLAN_2026-05-08.md`
- 산출: `docs/reports/NATIVE_INIT_V149_LONG_SOAK_SUPERVISOR_2026-05-08.md`
- build: `A90 Linux init 0.9.49 (v149)`
- 의도: longsoak recorder health/stale 상태를 device selftest/status/bootstatus에 연결
- 검증: real-device flash PASS, short longsoak PASS, host/device correlation PASS, integrated PASS, quick soak PASS, security scan PASS=17/WARN=1/FAIL=0
- 다음 실행 항목: v150 Host Disconnect Classifier

## 완료: v128 Menu Subcommand Policy

계획 문서: `docs/plans/NATIVE_INIT_V128_MENU_SUBCOMMAND_POLICY_PLAN_2026-05-07.md`
보고서: `docs/reports/NATIVE_INIT_V128_MENU_SUBCOMMAND_POLICY_2026-05-07.md`

결과:

- v127의 F023 mitigation은 유지한다.
- 메뉴 표시 중에도 명확히 read-only인 status/query subcommand만 허용한다.
- `run`, `writefile`, `mountfs`, `mknod*`, service/network mutation, power command는 계속 차단한다.
- 실기 flash 후 `screenmenu` visible 상태에서 allowed/blocked command matrix를 검증했다.

## 완료: v129 Changelog Paging

계획 문서: `docs/plans/NATIVE_INIT_V129_CHANGELOG_PAGING_PLAN_2026-05-07.md`
보고서: `docs/reports/NATIVE_INIT_V129_CHANGELOG_PAGING_2026-05-07.md`

결과:

- 1차: 긴 메뉴 page를 selected-row viewport로 그려 `ABOUT / CHANGELOG` 잘림을 줄였다.
- 2차: changelog list/menu/detail이 `a90_changelog.c/h` 공통 table을 보게 했다.
- 3차: ABOUT/changelog detail 화면에 page count와 VOL page navigation을 추가했다.

## 완료: v130 Menu Hold Back

계획 문서: `docs/plans/NATIVE_INIT_V130_MENU_HOLD_BACK_PLAN_2026-05-07.md`
보고서: `docs/reports/NATIVE_INIT_V130_MENU_HOLD_BACK_2026-05-07.md`

결과:

- 긴 메뉴와 changelog menu에서 VOL key repeat(value=2)를 이동 입력으로 처리한다.
- VOLUP+VOLDOWN 조합을 physical back/hide shortcut으로 처리한다.
- ABOUT/changelog page footer에 hold/page/back hint를 반영했다.

## 완료: v131 Menu Hold Timer

보고서: `docs/reports/NATIVE_INIT_V131_MENU_HOLD_TIMER_2026-05-07.md`

결과:

- v130에서 드라이버 repeat 이벤트가 없으면 hold scroll이 동작하지 않는 문제를 수정했다.
- VOL key down 상태와 monotonic timer를 이용해 450ms 이후 120ms 간격으로 반복 이동한다.
- 실기에서 VOL long-hold continuous movement 정상 동작을 확인했다.
- VOL+DN physical back shortcut과 v128/v129 menu busy policy는 유지한다.

## 완료: v132 Changelog Cleanup

계획 문서: `docs/plans/NATIVE_INIT_V132_CHANGELOG_CLEANUP_PLAN_2026-05-07.md`
보고서: `docs/reports/NATIVE_INIT_V132_CHANGELOG_CLEANUP_2026-05-07.md`

결과:

- ABOUT/changelog legacy per-version enum/app/render route를 제거하고 shared changelog table 단일 경로로 정리했다.
- v132 changelog entry와 detail을 추가하고 최신 marker를 `0.9.32 v132 CHANGELOG CLEANUP`으로 갱신했다.
- host harness로 changelog page count, first entry, app route를 검증했다.
- 실기 flash 후 `status`, `selftest verbose`, `screenmenu` busy gate, `hide`, `run /bin/a90sleep 1`, 3-cycle native soak를 검증했다.

## 완료: v133 Changelog Series

계획 문서: `docs/plans/NATIVE_INIT_V133_CHANGELOG_SERIES_PLAN_2026-05-07.md`
보고서: `docs/reports/NATIVE_INIT_V133_CHANGELOG_SERIES_2026-05-07.md`

결과:

- ABOUT/changelog 첫 화면을 전체 버전 나열 대신 `0.9.x RECENT`, `0.8.x LEGACY`, older series 목록으로 분리했다.
- series 선택 후 해당 series의 버전 목록을 열고, 버전 선택 시 기존 detail renderer를 재사용한다.
- host harness로 series count, first series, first detail index mapping을 검증했다.
- 실기 flash 후 `status`, `selftest verbose`, `screenmenu` busy gate, `hide`, `run /bin/a90sleep 1`, 3-cycle native soak를 검증했다.

## 완료: v134 Network Exposure Guardrail

계획 문서: `docs/plans/NATIVE_INIT_V134_NETWORK_EXPOSURE_GUARDRAIL_PLAN_2026-05-07.md`
보고서: `docs/reports/NATIVE_INIT_V134_NETWORK_EXPOSURE_GUARDRAIL_2026-05-07.md`

결과:

- USB ACM, host bridge, NCM, tcpctl, rshell 노출 경계를 read-only snapshot으로 요약하는 `a90_exposure.c/h`를 추가했다.
- `exposure [status|verbose|guard]` 명령과 `status`/`bootstatus` compact summary를 추가했다.
- `diag`에 `[exposure]` 섹션을 추가하되 token value는 계속 `hidden`으로만 출력한다.
- 실기 flash 후 `cmdv1 version/status`, `exposure status|verbose|guard`, `bootstatus`, `diag`, `screenmenu`/`hide` 회귀를 검증했다.
- local targeted v134 rescan은 PASS=15/WARN=1/FAIL=0이다.

## 완료: v135 Policy Matrix

계획 문서: `docs/plans/NATIVE_INIT_V135_POLICY_MATRIX_PLAN_2026-05-07.md`
보고서: `docs/reports/NATIVE_INIT_V135_POLICY_MATRIX_2026-05-07.md`

결과:

- `a90_controller.c/h`에 menu-visible/power-page command policy matrix를 추가했다.
- `policycheck [status|run|verbose]` 명령을 추가했다.
- 실기 flash 후 `policycheck run`이 `cases=91 pass=91 fail=0 allowed=45 blocked=46`으로 통과했다.
- menu-visible bare `mountsd`, `netservice start`, `service start tcpctl`, `run`, `writefile`은 busy로 차단되고 `mountsd status`는 허용됨을 확인했다.
- local targeted v135 rescan은 PASS=16/WARN=1/FAIL=0이다.
- quick native soak는 PASS cycles=3 commands=14다.

## 완료: v136 Structure Audit 3

계획 문서: `docs/plans/NATIVE_INIT_V136_STRUCTURE_AUDIT_PLAN_2026-05-07.md`
보고서: `docs/reports/NATIVE_INIT_V136_STRUCTURE_AUDIT_2026-05-07.md`

결과:

- v136은 C 후보인 post-v135 structure audit로 진행했다.
- module ownership drift, duplicate policy logic, include-tree residue, PID1 growth hotspot을 점검했다.
- blocking 구조 결함은 없고, 가장 큰 후속 후보는 `v136/40_menu_apps.inc.c`의 auto-HUD/menu controller hotspot이다.
- 실기 flash 후 `selftest verbose`, `exposure guard`, `policycheck run`, `screenmenu`/`hide`, 3-cycle quick soak를 검증했다.
- local targeted v136 rescan은 PASS=16/WARN=1/FAIL=0이다.

## 완료: v137 Integrated Validation Matrix

계획 문서: `docs/plans/NATIVE_INIT_V137_INTEGRATED_VALIDATION_PLAN_2026-05-07.md`
보고서: `docs/reports/NATIVE_INIT_V137_VALIDATION_MATRIX_2026-05-07.md`

결과:

- v137은 B 후보인 integrated validation matrix / host harness expansion으로 진행했다.
- `scripts/revalidation/native_integrated_validate.py`를 추가했다.
- 기본 gate는 `version`, `status`, `bootstatus`, `selftest verbose`, `pid1guard verbose`, `exposure guard|verbose`, `policycheck run|verbose`, service/netservice/rshell 상태, storage/runtime, `diag summary`, `screenmenu`/`hide`를 포함한다.
- 실기 flash 후 integrated validation은 `PASS commands=24`로 통과했다.
- local targeted v137 rescan은 PASS=17/WARN=1/FAIL=0이다.
- quick native soak는 PASS cycles=3 commands=14다.

## 완료: v138 Release-candidate Extended Soak

계획 문서: `docs/plans/NATIVE_INIT_V138_EXTENDED_SOAK_PLAN_2026-05-08.md`
보고서: `docs/reports/NATIVE_INIT_V138_EXTENDED_SOAK_2026-05-08.md`

결과:

- v138은 release-candidate extended soak로 진행했다.
- `scripts/revalidation/native_rc_soak.py`를 추가했다.
- v137 72429초 long-uptime 상태에서 baseline 검증을 먼저 수행했다.
- 실기 flash 후 `native_integrated_validate.py`는 `PASS commands=24`로 통과했다.
- quick native soak는 `PASS cycles=3 commands=14`로 통과했다.
- RC soak는 `PASS commands=62 failures=0`로 통과했다.
- local targeted v138 rescan은 PASS=17/WARN=1/FAIL=0이다.

다음 실행 항목:

- v136 structure audit는 완료했다.
- v137 integrated validation matrix는 완료했다.
- v138 release-candidate extended soak는 완료했다.
- 다음 실행 항목은 v139 auto-HUD/menu controller cleanup 구현이다.
- v139 계획 문서: `docs/plans/NATIVE_INIT_V139_AUTOHUD_CONTROLLER_PLAN_2026-05-08.md`
- network-facing 기능 확장은 v138 RC soak와 v137 integrated validation gate를 모두 통과하는 상태에서만 진행한다.

## 완료: v145 Input Cancel Validation Harness

계획 문서: `docs/plans/NATIVE_INIT_V145_INPUT_CANCEL_VALIDATION_PLAN_2026-05-08.md`
보고서: `docs/reports/NATIVE_INIT_V145_INPUT_CANCEL_VALIDATION_2026-05-08.md`

결과:

- v145는 `waitkey`/`waitgesture` cancel 자동 검증 보강으로 진행했다.
- `scripts/revalidation/native_input_cancel_validate.py`를 추가했다.
- harness는 같은 bridge 연결에서 blocking `cmdv1` command를 시작하고 start marker 관찰 후 `q`를 보내 `rc=-125` cancel frame을 확인한다.
- 실기 flash 후 `waitkey 1`, `waitgesture 1`, `inputmonitor 0` q cancel, integrated validation, quick soak가 통과했다.
- local targeted v145 rescan은 PASS=17/WARN=1/FAIL=0이다.

다음 실행 항목:

- network/Wi-Fi 진입 전 fresh Codex Cloud scan 또는 post-v145 구조/보안 후보를 다시 선정한다.

## 완료: v144 Inputmonitor Foreground App API Split

계획 문서: `docs/plans/NATIVE_INIT_V144_INPUTMON_APP_PLAN_2026-05-08.md`
보고서: `docs/reports/NATIVE_INIT_V144_INPUTMON_APP_2026-05-08.md`

결과:

- v144는 `inputmonitor` foreground command loop split으로 진행했다.
- `stage3/linux_init/a90_app_inputmon.c/h`에 foreground hooks와 `a90_app_inputmon_run_foreground()`를 추가했다.
- `stage3/linux_init/v144/40_menu_apps.inc.c`는 HUD stop/restore lifecycle callback만 연결한다.
- 실기 flash 후 `inputmonitor 0` q cancel, `inputlayout`, integrated validation, quick soak가 통과했다.
- local targeted v144 rescan은 PASS=17/WARN=1/FAIL=0이다.

다음 실행 항목:

- v145는 `waitkey`/`waitgesture` cancel 자동 검증 보강으로 완료했다.

## 완료: v143 Input Command Handler API Split

계획 문서: `docs/plans/NATIVE_INIT_V143_INPUT_COMMAND_PLAN_2026-05-08.md`
보고서: `docs/reports/NATIVE_INIT_V143_INPUT_COMMAND_2026-05-08.md`

결과:

- v143은 input shell command handler split으로 진행했다.
- `stage3/linux_init/a90_input_cmd.c/h`를 추가해 `waitkey`, `waitgesture`, `inputlayout` command handler를 분리했다.
- `stage3/linux_init/v143/80_shell_dispatch.inc.c`는 새 input command API를 호출한다.
- 실기 flash 후 `inputlayout`, `hide`, `version`, integrated validation, quick soak가 통과했다.
- local targeted v143 rescan은 PASS=17/WARN=1/FAIL=0이다.

다음 실행 항목:

- v145 후보는 waitkey/waitgesture cancel 자동 검증 보강으로 진행한다.

## 완료: v142 Cutout Calibration App API Split

계획 문서: `docs/plans/NATIVE_INIT_V142_CUTOUT_APP_PLAN_2026-05-08.md`
보고서: `docs/reports/NATIVE_INIT_V142_CUTOUT_APP_2026-05-08.md`

결과:

- v142는 cutout calibration state/API split으로 진행했다.
- `stage3/linux_init/a90_app_displaytest.c/h`에 cutout default/clamp/reset/feed/draw API를 추가했다.
- `stage3/linux_init/v142/40_menu_apps.inc.c`와 `v142/80_shell_dispatch.inc.c`는 cutout 상태/렌더링을 새 API로 호출한다.
- 실기 flash 후 `displaytest safe`, `cutoutcal`, integrated validation, quick soak가 통과했다.
- local targeted v142 rescan은 PASS=17/WARN=1/FAIL=0이다.

다음 실행 항목:

- v143은 input shell command handler 정리로 완료했다.

## 완료: v141 LOG/NETWORK App Renderer Split

계획 문서: `docs/plans/NATIVE_INIT_V141_LOG_NETWORK_APP_PLAN_2026-05-08.md`
보고서: `docs/reports/NATIVE_INIT_V141_LOG_NETWORK_APP_2026-05-08.md`

결과:

- v141은 LOG/NETWORK summary renderer split으로 진행했다.
- `stage3/linux_init/a90_app_log.c/h`와 `stage3/linux_init/a90_app_network.c/h`를 추가했다.
- `stage3/linux_init/v141/40_menu_apps.inc.c`는 LOG/NETWORK 화면을 새 API로 호출한다.
- 실기 flash 후 `native_integrated_validate.py`, quick soak가 통과했다.
- local targeted v141 rescan은 PASS=17/WARN=1/FAIL=0이다.

다음 실행 항목:

- v142는 cutout calibration state/API 분리로 진행한다.

## 완료: v140 CPU Stress App Module Split

계획 문서: `docs/plans/NATIVE_INIT_V140_CPUSTRESS_APP_PLAN_2026-05-08.md`
보고서: `docs/reports/NATIVE_INIT_V140_CPUSTRESS_APP_2026-05-08.md`

결과:

- v140은 CPU stress screen app lifecycle/renderer split으로 진행했다.
- `stage3/linux_init/a90_app_cpustress.c/h`를 추가해 helper spawn/reap/stop, timeout cleanup, CPU stress 화면 렌더링을 분리했다.
- `stage3/linux_init/v140/40_menu_apps.inc.c`는 CPU stress app state를 새 API로 호출한다.
- v140 ramdisk에는 `/bin/a90_cpustress`와 `/bin/a90_rshell` helper를 포함했다.
- 실기 flash 후 `cpustress 3 2`, `native_integrated_validate.py`, quick soak가 통과했다.
- local targeted v140 rescan은 PASS=17/WARN=1/FAIL=0이다.

다음 실행 항목:

- v140 CPU stress app split은 완료했다.
- 다음 후보는 fresh Codex Cloud scan follow-up, network-facing 판단, 또는 남은 UI/app renderer split 재평가다.
- 장시간 soak는 사용자가 자거나 작업 중일 때 별도 실행한다.

## 완료: v139 Auto-HUD/Menu Controller Cleanup

계획 문서: `docs/plans/NATIVE_INIT_V139_AUTOHUD_CONTROLLER_PLAN_2026-05-08.md`
보고서: `docs/reports/NATIVE_INIT_V139_AUTOHUD_CONTROLLER_2026-05-08.md`

결과:

- v139는 auto-HUD/menu controller cleanup으로 진행했다.
- `stage3/linux_init/v139/40_menu_apps.inc.c`에 `struct auto_hud_state`와 helper 경계를 추가했다.
- `auto_hud_loop()`의 menu/app 전환, hold timer reset, draw dispatch, input routing 책임을 작은 helper로 정리했다.
- 실기 flash 후 `native_integrated_validate.py`는 `PASS commands=25`로 통과했다.
- quick native soak는 `PASS cycles=3 commands=14`로 통과했다.
- RC soak는 `PASS commands=62 failures=0`로 통과했다.
- local targeted v139 rescan은 PASS=17/WARN=1/FAIL=0이다.

다음 실행 항목:

- v139 auto-HUD/menu controller cleanup은 완료했다.
- 다음 후보는 longer RC soak, fresh Codex Cloud scan follow-up, 또는 network-facing 판단으로 다시 선정한다.
- network-facing 기능 확장은 v139 RC soak와 local security rescan이 green인 상태에서만 진행한다.

## 실행 큐

### V43. Boot Readiness Timeline — 완료

목표:

- 부팅 중 리소스가 언제 준비되는지 자동 기록한다.
- 화면/serial이 없어도 `/cache/native-init.log`로 원인을 추적할 수 있게 한다.

구현:

- boot step enum 또는 helper 추가
- 각 단계의 monotonic timestamp 기록
- `timeline` shell 명령 추가
- `/cache/native-init.log`에 동일 정보 기록

검증:

- `timeline` — PASS
- `logcat` replay — PASS
- `status` — PASS
- recovery 왕복 후 `/cache/native-init.log` 보존 확인은 별도 항목으로 유지

### V44. HUD Boot Progress/Error — 완료

목표:

- 부팅 화면에서 현재 단계와 마지막 에러를 직접 보이게 한다.

구현:

- boot timeline 정보를 HUD 상단/하단에 요약 표시
- 마지막 command result 또는 boot error를 짧게 표시
- 실패 시 검은 화면/정지처럼 보이지 않도록 error card 표시

검증:

- 정상 부팅 HUD에 `BOOT OK` 또는 현재 step 표시 — PASS
- `bootstatus`, `status`, `statushud`, `autohud 2` — PASS
- 고의 실패 가능한 display/sysfs 명령 후 HUD 복구 확인 — 보류

### V45. Log Preservation + Run Cancel Test — 완료

목표:

- `/cache/native-init.log`가 recovery 왕복 후 보존되는지 확인한다.
- `run` cancelable child wait를 실기 검증한다.

구현/준비:

- `/cache/bin` 또는 ramdisk에 안전한 static helper 준비
- long-running helper 실행 후 q/Ctrl-C cancel 확인
- recovery 재부팅 후 `cat /cache/native-init.log` 확인

검증:

- `run /bin/a90sleep 30` + q — PASS
- `last` — PASS
- `logcat` — PASS
- TWRP 왕복 후 log 보존 — PASS

### V46. Safe Storage / Partition Map Report — 완료

목표:

- 쓰기 가능한 안전 영역과 건드리면 안 되는 영역을 명확히 분리한다.

확인:

- `/cache`
- `/tmp`
- `/mnt/system` read-only
- `/data`는 보류
- `/efs`, modem, RPMB, keymaster 계열은 금지

산출:

- `docs/reports/NATIVE_INIT_STORAGE_MAP_2026-04-25.md`

결론:

- `/cache`는 native init log와 작은 도구를 둘 수 있는 1차 persistent safe write 영역
- `userdata`는 약 110 GiB 대용량 후보지만 Android FBE/user data와 엮여 있어 별도 백업/포맷 계획 전까지 보류
- `efs`, `sec_efs`, modem, persist, key/security, vbmeta, bootloader 계열은 do-not-touch
- block major/minor는 부팅마다 달라질 수 있으므로 by-name 또는 `/sys/class/block/<name>/dev` 기준으로 식별

### V47. On-screen Menu Draft — 완료

목표:

- serial 없이도 화면과 버튼만으로 최소 조작이 가능하게 한다.

구현:

- KMS 기반 screen menu 표시
- VOL+/VOL-/POWER 선택
- status/log/recovery/reboot/poweroff 우선
- `blindmenu`는 serial-only fallback으로 유지

검증:

- `menu` 화면 진입 — PASS
- q cancel 후 autohud 복구 — PASS
- 실제 버튼 이동/선택 — 수동 확인 대기
- recovery/reboot/poweroff 위험 동작 — 수동 확인 대기

산출:

- `docs/reports/NATIVE_INIT_V47_SCREEN_MENU_2026-04-25.md`

### V48. USB Gadget Map Report — 완료

목표:

- 현재 USB ACM serial 제어 채널을 기준점으로 고정한다.
- ADB와 USB networking 후보를 분리해 다음 실험 순서를 정한다.

확인:

- device-side configfs 구성은 `g1` + `acm.usb0` + `a600000.dwc3`
- host-side descriptor는 `04e8:6861`, CDC ACM control/data 2-interface
- host driver는 `cdc_acm`, 노드는 `/dev/ttyACM0`
- ADB는 `ffs.adb`/FunctionFS 경로가 있으나 `adbd` zombie와 `ep0 only`가 blocker
- USB networking은 ACM rescue channel 유지 후 두 번째 function으로 추가하는 방향

산출:

- `docs/reports/NATIVE_INIT_USB_GADGET_MAP_2026-04-25.md`

### V49. Toybox / Static Userland Candidate Review — 완료

목표:

- 모든 유틸을 native init 안에 재구현하지 않고, static ARM64 multi-call binary를 붙일 수 있는지 판단한다.
- USB networking probe 전에 `ip`/`ifconfig`/`route`/`nc`/`ps`/`dmesg`/`grep`/`tail` 계열 도구 확보 가능성을 확인한다.

확인:

- `run <path> [args...]`는 이미 static helper 실행, exit status, q/Ctrl-C cancel을 지원한다.
- 현재 `run` PATH는 `/cache:/cache/bin:/bin:/system/bin`이라 `/cache/bin` 기반 실험과 맞다.
- host build prerequisite 설치 후 `toybox 0.8.13` static ARM64 빌드가 성공했다.
- artifact는 `external_tools/userland/bin/toybox-aarch64-static-0.8.13`에 생성된다.
- artifact SHA256은 `92a0917579c76fec965578ac242afbf7dedc4428297fb90f4c9caf7f538a718c`다.
- `INTERP` segment와 dynamic section이 없어 static ELF 기준은 통과했다.
- 과거 `busybox-static:arm64` apt 확보 실패 기록이 있다.
- BusyBox는 GPLv2 배포 의무를 고려해야 하고, toybox는 Android 계열과 라이선스 측면에서 비교 후보가 된다.

산출:

- `docs/reports/NATIVE_INIT_USERLAND_CANDIDATES_2026-04-25.md`

실기 결과:

- `/cache/bin/toybox` 배치 완료
- SHA256 일치: `92a0917579c76fec965578ac242afbf7dedc4428297fb90f4c9caf7f538a718c`
- PASS:
  - `--help`
  - `uname -a`
  - `ls /proc`
  - `ps -A`
  - `ps -ef`
  - `dmesg --help`
  - `dmesg -s 1024`
  - `hexdump -C /proc/version`
  - `ifconfig -a`
  - `route -n`
  - `ip` usage
  - `netcat --help`
- 주의:
  - `ps` 단독은 `rc=1`; `ps -A`/`ps -ef` 사용
  - `netcat -h`는 `rc=1`; `netcat --help` 사용
  - `ip addr`/`ip link`는 interface를 출력하지만 `No such device`와 `rc=1`; USB network 추가 후 재확인

### V50. USB Reattach / NCM Probe — 완료

목표:

- USB gadget rebind 후 serial console이 stale fd에 묶이는 문제를 해결한다.
- ACM rescue channel을 유지한 상태에서 NCM function이 실제 host/device interface를 만드는지 확인한다.

구현:

- `init_v48`에서 `read_line()`을 `poll()` 기반으로 바꾸고 console reattach를 추가했다.
- `reattach`, `usbacmreset` 명령을 추가했다.
- `startadbd`/`stopadbd` rebind 뒤 console reattach를 호출한다.
- `serial_tcp_bridge.py`는 USB 재열거 시 serial device identity 변화를 감지해 fd를 다시 연다.
- `a90_usbnet` helper는 `status|ncm|rndis|probe-ncm|probe-rndis|off`를 제공한다.

실기 결과:

- `stage3/boot_linux_v48.img` 플래시 완료
- `version` → `A90 Linux init v48` 확인
- `usbacmreset` 후 serial console reattached 확인
- `run /cache/bin/a90_usbnet off` 후 약 3초 내 bridge `version` 복구 확인
- `probe-ncm` 중 host:
  - phone device에 `cdc_acm` + `cdc_ncm` composite interface 표시
  - `enx26eaa7b343d7` / `enx425f6b65a0cb` 형태 NCM interface 생성 확인
- `probe-ncm` 중 device:
  - toybox `ifconfig -a`에서 `ncm0` 확인
- rollback 후 ACM-only와 `version` 복구 확인

산출:

- `docs/reports/NATIVE_INIT_V48_USB_REATTACH_NCM_2026-04-25.md`

### V51~V52. HUD/Menu TUI Polish — 완료

목표:

- 부팅 후 TEST 화면에서 상태 화면과 버튼 메뉴로 자연스럽게 넘어간다.
- 화면 상단에 배터리, 전력, CPU/GPU 온도, 메모리, load를 읽기 쉽게 표시한다.
- VOL+/VOL-/POWER 조작 힌트와 메뉴 항목을 실기에서 보기 좋은 위치로 배치한다.

실기 결과:

- `A90 INIT BOOT OK CONSOLE`
- `BAT 100% FUL PWR ...`
- `CPU ... GPU ...`
- `MEM ... LOAD ...`
- `HIDE MENU`, `STATUS`, `LOG`, `RECOVERY`, `REBOOT`, `POWEROFF`
- footer `A90V52 UP ...`

### V53. Menu Busy Gate + Flash Auto-hide — 완료

목표:

- 화면 메뉴가 떠 있을 때 serial shell과 버튼 UI가 동시에 위험 명령을 실행하지 않게 한다.
- automation은 hang 대신 `[busy]`를 보고 `hide` 후 재시도할 수 있게 한다.

구현:

- `init_v53`에서 menu active state와 hide request를 `/tmp` 파일로 공유
- 메뉴 active 중 위험/장시간 명령은 `[busy]`로 즉시 차단
- `version`, `status`, `timeline`, `logcat` 등 관찰 명령은 허용
- `native_init_flash.py --from-native`는 `[busy]`를 보면 `hide` 후 `recovery` 재시도

실기 결과:

- `stage3/boot_linux_v53.img` SHA256 `44cb9ebb3cc65ab0b3316afe69592c8b7fa7a05a96c872dfd2a4f9f884d98046`
- local image SHA256, remote SHA256, boot partition prefix SHA256 일치
- `echo busytest` → `[busy] auto menu active; send hide/q or select HIDE MENU`
- `hide` 후 `echo afterhide` → `[done] echo`

산출:

- `docs/reports/NATIVE_INIT_V53_MENU_BUSY_2026-04-25.md`

### V54. NCM Persistent Link Validation — 완료

목표:

- ACM serial을 유지한 채 USB NCM persistent mode를 켠다.
- host `cdc_ncm` interface와 device `ncm0`가 동시에 살아 있는지 확인한다.
- NCM 위에서 실제 L3/TCP 통신이 가능한지 확인한다.

실기 결과:

- host: `04e8:6861` composite에 `cdc_acm` + `cdc_ncm` 동시 표시
- host interface: `enx6e0617d3b2a3`
- device helper: `f1 -> acm.usb0`, `f2 -> ncm.usb0`, `ncm.ifname: ncm0`
- device `ncm0`: `192.168.7.2/24`, `fe80::f83d:4bff:fe0f:b583/64`
- host `enx6e0617d3b2a3`: `192.168.7.1/24`
- IPv4 ping `192.168.7.2`: 3/3 PASS, 0% packet loss
- IPv6 link-local ping은 응답 확인
- host → device TCP:
  - host `nc -6 ... 2323`
  - device `/cache/bin/toybox netcat -l -p 2323`
  - payload `hello-from-host-over-ncm-ipv6` 수신 확인

산출:

- `docs/reports/NATIVE_INIT_V54_NCM_LINK_2026-04-25.md`

### V55. NCM Operations Helper — 완료

목표:

- NCM을 매번 수동 설정하지 않고 host helper로 재현 가능하게 켠다.
- device `ncm0`와 host `enx...`를 `192.168.7.2/24` ↔ `192.168.7.1/24`로 고정한다.
- toybox `netcat`의 serial stdin 충돌을 피하기 위해 전용 TCP helper로 양방향 payload를 검증한다.

구현:

- `scripts/revalidation/ncm_host_setup.py`
  - `setup|status|ping|off`
  - bridge `127.0.0.1:54321` 기준으로 `a90_usbnet ncm/status/off` 실행
  - `ncm.host_addr`를 파싱해 `/sys/class/net/*/address`에서 host interface 자동 탐지
  - host `sudo ip addr replace`, `ip link set up`, `ping` 검증 수행
- `stage3/linux_init/a90_nettest.c`
  - `listen <port> <timeout_sec> <expect>`
  - `send <host_ipv4> <port> <payload>`
- `scripts/revalidation/build_nettest_helper.sh`
  - static ARM64 `a90_nettest` 빌드

검증:

- local Python syntax check — PASS
- static ARM64 `a90_nettest` build — PASS
- `ncm_host_setup.py status` host interface 자동 탐지 — PASS
- `ncm_host_setup.py ping` 3/3, 0% loss — PASS
- static `a90_nettest` `/cache/bin` 배치와 SHA256 일치 — PASS
- host→device TCP payload — PASS
- device→host TCP payload — PASS
- 30초 ping stability 30/30, 0% loss — PASS
- rollback `off`는 작업 링크 유지를 위해 이번 pass에서는 실행하지 않음

산출:

- `docs/reports/NATIVE_INIT_V55_NCM_OPS_2026-04-25.md`

### V56. NCM TCP Control Helper — 완료

목표:

- USB NCM 위에서 serial bridge보다 빠른 작은 TCP 명령/응답 채널을 확보한다.
- serial bridge는 rescue/fallback으로 유지한다.

구현:

- `stage3/linux_init/a90_tcpctl.c`
  - `listen <port> <idle_timeout_sec> [max_clients]`
  - command: `help`, `ping`, `version`, `status`, `run`, `quit`, `shutdown`
  - `run`은 absolute path, stdin `/dev/null`, stdout/stderr TCP 반환, 10초 timeout
- `scripts/revalidation/build_tcpctl_helper.sh`
  - static ARM64 `a90_tcpctl` 빌드

검증:

- host-native protocol smoke test — PASS
- static ARM64 build — PASS
- `/cache/bin/a90_tcpctl` 배치와 SHA256 일치 — PASS
- TCP `ping`, `version`, `status` — PASS
- TCP `run /cache/bin/toybox uname -a` — PASS
- TCP `run /cache/bin/toybox ifconfig ncm0` — PASS
- TCP `shutdown` 후 serial `run` 종료 — PASS
- 이후 serial bridge `version`과 NCM ping 3/3 — PASS

산출:

- `docs/reports/NATIVE_INIT_V56_TCPCTL_2026-04-26.md`

### V57. TCP Control Host Wrapper — 완료

목표:

- `a90_tcpctl` launch/client/stop을 host script 하나로 반복 가능하게 만든다.
- smoke test로 NCM TCP control 채널을 빠르게 재검증한다.

구현:

- `scripts/revalidation/tcpctl_host.py`
  - `install`
  - `start`
  - `call`
  - `ping`, `version`, `status`
  - `run`
  - `stop`
  - `smoke`

검증:

- Python syntax/help — PASS
- `tcpctl_host.py smoke` — PASS
- TCP `ping`, `version`, `status`, `run`, `shutdown` — PASS
- serial `run` 종료와 bridge `version` — PASS
- NCM ping 3/3 — PASS

산출:

- `docs/reports/NATIVE_INIT_V57_TCPCTL_HOST_WRAPPER_2026-04-26.md`

### V58. TCP Control Soak — 완료

목표:

- USB NCM + `a90_tcpctl` 조합이 짧은 smoke를 넘어 일정 시간 반복 운용 가능한지 확인한다.
- serial bridge는 launch/rescue 채널로 유지하고, 실제 명령 왕복은 TCP control로 반복한다.

구현:

- `scripts/revalidation/tcpctl_host.py`
  - `soak`
  - 기본 300초, 10초 간격
  - TCP `ping` 매 사이클
  - TCP `status`와 `run /cache/bin/toybox uptime` 매 6사이클
  - host NCM ping 매 사이클
  - 종료 시 TCP `shutdown`, serial `[done] run`, bridge `version`, final NCM ping 검증

검증:

- Python syntax/help — PASS
- short soak 20초/4사이클 — PASS
- main soak 300초/30사이클 — PASS
- TCP ping 30/30 — PASS
- TCP status 5/5 — PASS
- TCP run uptime 5/5 — PASS
- host ping 30/30 — PASS
- `tcpctl: served=42 stop=1`, serial `[done] run (300509ms)` — PASS
- final NCM ping 3/3, 0% loss — PASS

남은 범위:

- 물리 USB unplug/replug 또는 UDC reset 이후 reconnect soak는 별도 항목으로 남긴다.

산출:

- `docs/reports/NATIVE_INIT_V58_TCPCTL_SOAK_2026-04-26.md`

### V59. AT Serial Noise Filter — 완료

목표:

- host NetworkManager/modem probe가 ACM serial에 던지는 unsolicited `AT` 계열 문자열을 shell 오류로 처리하지 않는다.
- filter는 host bridge가 아니라 native init shell 입력 경로에 넣어 device 단독 안정성을 높인다.

구현:

- `stage3/linux_init/init_v59.c`
  - `INIT_VERSION`을 `v59`로 갱신
  - `is_unsolicited_at_noise()` 추가
  - `AT`, `ATE0`, `AT+...`, `ATQ0 ...` 형태의 printable modem command line을 command dispatch 전에 무시
  - 무시한 line은 `/cache/native-init.log`에 `serial: ignored AT probe ...`로 기록

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v59.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v59 boot — PASS
- bridge `version` → `A90 Linux init v59` — PASS
- serial 입력 `AT`, `ATE0`, `AT+GCAP`, `ATQ0 V1 E1 S0=0 &C1 &D2 +FCLASS=0`, `version` — PASS
- 출력에 `unknown command: AT` 없음 — PASS
- `/cache/native-init.log`에 ignored AT probe 4건 기록 — PASS

산출:

- `docs/reports/NATIVE_INIT_V59_AT_NOISE_2026-04-26.md`

### V60. Opt-in Boot Netservice — 완료

목표:

- NCM/tcpctl을 부팅마다 수동 시작하지 않고 필요할 때만 자동 시작하는 service 정책으로 정리한다.
- default OFF를 유지해 serial bridge와 recovery 복구 경로를 보존한다.
- `/cache/native-init-netservice` flag가 있을 때만 boot-time NCM/tcpctl을 켠다.

구현:

- `stage3/linux_init/init_v60.c`
  - `INIT_VERSION`을 `v60`으로 갱신
  - `netservice [status|start|stop|enable|disable]` 추가
  - `enable`은 flag 생성 후 NCM/tcpctl 시작
  - `disable`은 flag 제거, tracked tcpctl 종료, `a90_usbnet off`, console reattach 수행
  - boot path에서 flag가 있으면 `/cache/bin/a90_usbnet ncm`, `ifconfig ncm0 192.168.7.2/24`, `a90_tcpctl listen 2325 3600 0` 실행
  - `/cache/native-init-netservice.log`에 helper 출력과 실패 원인 기록
- `scripts/revalidation/ncm_host_setup.py`
  - 이미 NCM이 active면 `a90_usbnet ncm` 재실행 없이 host/device IP와 ping만 검증

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v60.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v60 boot — PASS
- default OFF boot: `enabled=no`, `ncm0=absent`, `tcpctl=stopped` — PASS
- enabled flag boot auto-start: `enabled=yes`, `ncm0=present`, `tcpctl=running pid=544` — PASS
- host `enx0a2eb7a94b2f`에 `192.168.7.1/24` 설정 후 `192.168.7.2` ping 3/3 — PASS
- `tcpctl_host.py ping`, `status`, `run /cache/bin/toybox uptime` — PASS
- `netservice disable` rollback 후 `enabled=no`, `ncm0=absent`, `tcpctl=stopped` — PASS

산출:

- `stage3/linux_init/init_v60`
  - SHA256 `4a274b02f793be79872c4ff164dcead332b33e4f7cf281c35f1d59625774dd09`
- `stage3/ramdisk_v60.cpio`
  - SHA256 `f8b153804c561e26c784c713668a6e8e3dfb0cb10b83a9a72c659f1d8c46285c`
- `stage3/boot_linux_v60.img`
  - SHA256 `c57fbf4645790826fbd5e804ff605c25b95cffb4c5eb0ff9076202581e6e828a`
- `docs/reports/NATIVE_INIT_V60_NETSERVICE_2026-04-26.md`

### V60.1. Netservice UDC Reconnect Validation — 완료

목표:

- v60 `netservice stop/start`로 software UDC 재열거 후 ACM serial, NCM, TCP control이 복구되는지 확인한다.
- NCM 재열거마다 host `enx...` 이름이 바뀌는 문제를 운영 도구와 문서에 반영한다.

구현:

- `scripts/revalidation/netservice_reconnect_soak.py`
  - `status`, `once`, `soak` command 추가
  - `a90_usbnet status`의 `ncm.host_addr` MAC으로 현재 host interface 자동 탐지
  - `--manual-host-config`로 sudo 불가 환경에서 현재 `sudo ip ... dev <enx...>` 명령 출력 후 대기

검증:

- stale `enx0a2eb7a94b2f`에 host IP 설정 시 `Cannot find device` — 관찰됨
- 새 interface `enxba06f3efab0f`에 `192.168.7.1/24` 설정 — PASS
- `192.168.7.2` ping 3/3, 0% loss — PASS
- `tcpctl_host.py ping` — PASS
- `tcpctl_host.py status` — PASS
- `tcpctl_host.py run /cache/bin/toybox uptime` — PASS
- final `netservice stop`, `ncm0=absent`, `tcpctl=stopped`, bridge `version` v60 — PASS

발견:

- USB 재열거 중 host modem probe fragment `A` 또는 `ATAT...`가 serial output을 오염시킬 수 있음
- v59/v60 filter는 full `AT` line은 처리하지만 single `A` fragment는 아직 보강 필요

산출:

- `docs/reports/NATIVE_INIT_V60_RECONNECT_2026-04-26.md`

### V61. CPU/GPU Usage Percent HUD — 완료

목표:

- 기존 CPU/GPU 온도 표시 옆에 사용률 `%`만 먼저 추가한다.
- GPU clock/frequency 표시는 공간 확인 뒤 후순위로 둔다.

구현:

- `stage3/linux_init/init_v61.c`
  - `INIT_VERSION`을 `v61`로 갱신
  - `/proc/stat` aggregate delta 기반 CPU usage 계산
  - KGSL `/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage` 기반 GPU busy `%` 표시
  - `status`와 HUD row 2를 `CPU <temp> <usage> GPU <temp> <usage>` 형태로 변경

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v61.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v61 boot — PASS
- bridge `version` → `A90 Linux init v61` — PASS
- `status` → `thermal: cpu=35.1C 0% gpu=33.5C 0%` — PASS
- `statushud` redraw 후 `thermal: cpu=35.3C 12% gpu=33.6C 0%` — PASS
- final `autohud: running`, `netservice: disabled tcpctl=stopped` — PASS

산출:

- `stage3/linux_init/init_v61`
  - SHA256 `7fce8bac65af8cd997d7f150c0939b6e4fa757ea0ecfeb89e0213c3fa955f427`
- `stage3/ramdisk_v61.cpio`
  - SHA256 `2ce70282a001db47d42b900ccc0bfaf3aed7dee1528107048912bfbaab53d729`
- `stage3/boot_linux_v61.img`
  - SHA256 `40a33381be60ea8eaf91e7f09256d3d0de100c8959c3687a3b4aa95696c7cdb2`
- `docs/reports/NATIVE_INIT_V61_CPU_GPU_USAGE_2026-04-26.md`

### V62. CPU Stress Gauge Validation — 완료

목표:

- v61 CPU usage `%`가 실제 CPU 부하에서 변하는지 검증한다.
- `/dev/null`/`/dev/zero`가 없거나 regular file로 오염돼도 boot-time에 char device로 복구한다.

구현:

- `stage3/linux_init/init_v62.c`
  - `INIT_VERSION`을 `v62`로 갱신
  - `/dev/null` rdev `1:3`, `/dev/zero` rdev `1:5` 보정
  - `cpustress [sec] [workers]` 명령 추가
  - worker fork, timeout, q/Ctrl-C 취소 처리

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v62.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v62 boot — PASS
- bridge `version` → `A90 Linux init v62` — PASS
- `/dev/null` → `mode=0600`, `rdev=1:3` — PASS
- `/dev/zero` → `mode=0600`, `rdev=1:5` — PASS
- `cpustress 10 8` 전 `thermal: cpu=34.9C 0% gpu=33.3C 0%` — PASS
- `cpustress 10 8` 후 `thermal: cpu=36.3C 29% gpu=34.6C 0%` — PASS
- cooldown 후 `thermal: cpu=35.4C 0% gpu=33.7C 0%` — PASS

산출:

- `stage3/linux_init/init_v62`
  - SHA256 `016f67ec1bd713533ed8d2d12e5e5f7cd5709406ce6351fa0d22f30d0bcdfa33`
- `stage3/ramdisk_v62.cpio`
  - SHA256 `13ced5f0e0d97887fe84036b777cd5efdc97b0c81089261b9397f5da12169629`
- `stage3/boot_linux_v62.img`
  - SHA256 `8c422903226980855e23b75379a60b4ec3ec0a680c457b28adfa5417fdf870b1`
- `docs/reports/NATIVE_INIT_V62_CPUSTRESS_2026-04-26.md`

### V63. App Menu / CPU Stress Screen App — 완료

목표:

- 기존 단일 화면 메뉴를 앱 폴더 형태로 확장한다.
- LOG/NETWORK/CPU STRESS가 한 프레임만 보이고 사라지는 문제를 고친다.
- CPU stress는 버튼으로 5/10/30/60초를 선택하고, 실행 중 CPU 관련 정보를 전용 화면에 표시한다.

구현:

- `stage3/linux_init/init_v63.c`
  - `MAIN MENU` 아래 `APPS >`, `NETWORK >`, `POWER >` 계층 추가
  - `APPS / TOOLS / CPU STRESS` 시간 선택 메뉴 추가
  - `SCREEN_APP_LOG`, `SCREEN_APP_NETWORK`, `SCREEN_APP_CPU_STRESS` active app state 추가
  - CPU stress screen app에서 CPU 온도/사용률/load, online/present core, core frequency, memory, power, worker 수 표시
  - 자동 HUD 메뉴의 help/menu 간격과 안내 문구 밝기 조정

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v63.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v63 boot — PASS
- bridge `version` → `A90 Linux init v63` — PASS
- 자동 메뉴에서 `APPS >`, `TOOLS >`, `CPU STRESS >` 계층 표시 확인 — PASS
- `HIDE MENU`와 serial `hide` 경로 확인 — PASS

산출:

- `stage3/linux_init/init_v63`
  - SHA256 `062eb9a780c0fe71890e80d0c961b5b3016d3d35e0da19fa99e5289bbde04a00`
- `stage3/ramdisk_v63.cpio`
  - SHA256 `7b9d3f71f648e7f9765fc6c1827c66c0dcc422f714b1ec67a334f9cbca5f53ce`
- `stage3/boot_linux_v63.img`
  - SHA256 `99025fba4c17348057920eab06b7bd98a97b5cc5f6acff21190981288a0ad09d`
- `docs/reports/NATIVE_INIT_V63_APP_MENU_2026-04-26.md`

### V64. Custom Boot Splash — 완료

목표:

- 부팅 직후 큰 `TEST` 디버그 화면 대신 프로젝트 전용 boot splash를 표시한다.
- 이후 기존처럼 상태 HUD/menu로 자동 전환한다.

구현:

- `stage3/linux_init/init_v64.c`
  - `INIT_VERSION`을 `v64`로 갱신
  - `BOOT_SPLASH_SECONDS` 2초 유지
  - `kms_draw_boot_splash()` 추가
  - boot frame 로그를 `display-splash` timeline으로 기록
  - serial boot 안내를 `splash 2s -> autohud 2s`로 변경

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v64.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v64 boot — PASS
- bridge `version` → `A90 Linux init v64` — PASS
- `timeline` → `display-splash rc=0 ... boot splash applied` — PASS
- `status` → `boot: BOOT OK shell 3S`, `autohud: running` — PASS

산출:

- `stage3/linux_init/init_v64`
  - SHA256 `f80152f02db376080bdcae3600ce6daf03e64bc08e0e092a8ae3b9116ea7bde2`
- `stage3/ramdisk_v64.cpio`
  - SHA256 `8560785b5e2832d40913b3b0e91a90e633041809a788200ebb6aa875c12ed018`
- `stage3/boot_linux_v64.img`
  - SHA256 `aa628f70f09a62f704b9d2078aae888ad57d95349fcaf8d3af47d95a3ad864ca`
- `docs/reports/NATIVE_INIT_V64_BOOT_SPLASH_2026-04-26.md`

### V65. Splash Safe Layout — 완료

목표:

- v64 custom splash가 보이지만 일부 텍스트가 잘리는 문제를 해결한다.
- 긴 상태 문구와 footer가 1080px 폭과 라운드 코너/안전 여백을 넘지 않게 한다.

구현:

- `stage3/linux_init/init_v65.c`
  - `INIT_VERSION`을 `v65`로 갱신
  - splash 기본 scale 축소
  - 좌우 margin을 넓히고 row width를 계산
  - `kms_draw_text_fit()`으로 각 줄을 `shrink_text_scale()`에 통과
  - 상태 문구를 짧게 정리
  - footer 위치를 조금 더 위로 올리고 card 폭 안에서 축소

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v65.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v65 boot — PASS
- bridge `version` → `A90 Linux init v65` — PASS
- `status` → `boot: BOOT OK shell 3S`, `autohud: running` — PASS
- `timeline` → `display-splash rc=0 ... boot splash applied` — PASS

산출:

- `stage3/linux_init/init_v65`
  - SHA256 `2cb2b9e5e8d989cddb92f3c1ef93b8f4674ba4359408445b19af5745ddc2f373`
- `stage3/ramdisk_v65.cpio`
  - SHA256 `b8184bb241c52b0d99e9efbceed16ded50598a24068a359c8d8e3abf78f1c16f`
- `stage3/boot_linux_v65.img`
  - SHA256 `143acc7925b8ac0006d972ca463c1993f5306b63c5187e9c3007a34fa71ed7d4`
- `docs/reports/NATIVE_INIT_V65_SPLASH_SAFE_LAYOUT_2026-04-26.md`

### V66. About App / Versioning — 완료

목표:

- 공식 semantic version과 기존 `vNN` build tag를 함께 사용한다.
- 만든이 `made by temmie0214`를 splash, `version`, `status`, ABOUT app에 표시한다.
- 앱 메뉴에서 version, changelog, credits를 확인할 수 있게 한다.

구현:

- `stage3/linux_init/init_v66.c`
  - `INIT_VERSION "0.7.3"`
  - `INIT_BUILD "v66"`
  - `INIT_CREATOR "made by temmie0214"`
  - `INIT_BANNER "A90 Linux init 0.7.3 (v66)"`
  - `APPS / ABOUT` 메뉴 추가
  - `VERSION`, `CHANGELOG`, `CREDITS` 화면 추가
- `docs/overview/VERSIONING.md`
  - `MAJOR.MINOR.PATCH`와 `vNN` build tag 규칙 정리
- `CHANGELOG.md`
  - 공식 버전별 업데이트 로그 추가

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v66.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v66 boot — PASS
- bridge `version` → `A90 Linux init 0.7.3 (v66)` 및 `made by temmie0214` — PASS
- `status` → `creator: made by temmie0214`, `boot: BOOT OK shell 3S` — PASS
- `timeline` → `init-start ... A90 Linux init 0.7.3 (v66)` — PASS

산출:

- `stage3/linux_init/init_v66`
  - SHA256 `31a8c6e8da1f2ab07fe26a96d6fa78ba02a9cb43e6bc4ea3080220f4efb41715`
- `stage3/ramdisk_v66.cpio`
  - SHA256 `446b070e9df82b6368122ca190c27c3298a147eb778f70c9d08cc7e9bcf7e972`
- `stage3/boot_linux_v66.img`
  - SHA256 `320a325531b6e2ffc35c8165179396638c1c8af5ee4a59517f1074dc92b3eb08`
- `docs/reports/NATIVE_INIT_V66_ABOUT_VERSIONING_2026-04-26.md`

### V67. Changelog Detail Screens — 완료

목표:

- 휴대폰 세로 화면을 활용해 changelog 내용을 더 길게 표시한다.
- ABOUT 계열 화면의 version 글씨 크기를 작게 통일한다.
- `CHANGELOG`를 버전 목록으로 만들고, 선택한 버전의 상세 변경점을 보여준다.

구현:

- `stage3/linux_init/init_v67.c`
  - `INIT_VERSION "0.7.4"`
  - `INIT_BUILD "v67"`
  - `APPS / ABOUT / CHANGELOG >` submenu 추가
  - `0.7.4 v67`~`0.6.0 v62` 상세 화면 추가
  - ABOUT 계열 text scale compact화

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v67.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v67 boot — PASS
- bridge `version` → `A90 Linux init 0.7.4 (v67)` 및 `made by temmie0214` — PASS
- `status` → `creator: made by temmie0214`, `boot: BOOT OK shell 3S`, `autohud: running` — PASS
- `timeline` → `init-start ... A90 Linux init 0.7.4 (v67)` — PASS

산출:

- `stage3/linux_init/init_v67`
  - SHA256 `642da01258a4a43016e5362d74fb2c142a30c42001217c88fa2ae2fe8aa05e04`
- `stage3/ramdisk_v67.cpio`
  - SHA256 `55d2b9c0323e2642c9d7095a62d668b85774476fe5079a43113ef7a5b3e7b6b2`
- `stage3/boot_linux_v67.img`
  - SHA256 `8b087d08ecc5dd459ffd36c22c520f5de9fb2c3ddecee0c212bd4fece57f8623`
- `docs/reports/NATIVE_INIT_V67_CHANGELOG_DETAILS_2026-04-26.md`

### V68. HUD Log Tail / Changelog History — 완료

목표:

- 메뉴를 숨긴 상태에서도 `/cache/native-init.log` tail을 화면에서 확인한다.
- changelog detail 화면을 더 과거 버전까지 확장한다.

검증:

- bridge `version` → `A90 Linux init 0.7.5 (v68)` — PASS

산출:

- `stage3/linux_init/init_v68`
  - SHA256 `24dcfe9b2351c6cb16a1af6737b12c950e5f1972c82f6ede6855b6ec210d64c5`
- `stage3/ramdisk_v68.cpio`
  - SHA256 `c33b9853be5e6faeea1254d47aa8fb165ca44919ce12679ea9d38d487a3cb358`
- `stage3/boot_linux_v68.img`
  - SHA256 `bc0982cb67f966affbc3de2d1d00c4b6a2797e1f79c1267863a29091fd1ddb41`

### V69. Input Gesture Layout — 완료

목표:

- VOL+/VOL-/POWER 3버튼만으로 단일/더블/롱/조합 입력을 분리한다.
- 기존 단일 클릭 메뉴 조작은 유지한다.
- 위험한 `POWER long`은 직접 reboot/poweroff에 묶지 않는다.

구현:

- `stage3/linux_init/init_v69.c`
  - `INIT_VERSION "0.8.0"`
  - `INIT_BUILD "v69"`
  - `inputlayout` command 추가
  - `waitgesture [count]` command 추가
  - `screenmenu`/`blindmenu` gesture action 적용

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v69.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v69 boot — PASS
- bridge `version` → `A90 Linux init 0.8.0 (v69)` 및 `made by temmie0214` — PASS
- `inputlayout` → 단일/더블/롱/조합 mapping 출력 — PASS
- `status` → `creator: made by temmie0214`, `boot: BOOT OK shell 3S` — PASS
- `timeline` → `init-start ... A90 Linux init 0.8.0 (v69)` — PASS

산출:

- `stage3/linux_init/init_v69`
  - SHA256 `bf9a5cc337d8ae0ca705c027053a0e81e3d4436926e331e089952b8916a280e9`
- `stage3/ramdisk_v69.cpio`
  - SHA256 `28fbb2f9ae618086bc704a73529d3cb3c4ebac050052f6dbd396d51503508ada`
- `stage3/boot_linux_v69.img`
  - SHA256 `1a333b5ee8e1c73722b9165f569f17a3257119690fccba3ce160b952792252d8`
- `docs/reports/NATIVE_INIT_V69_INPUT_LAYOUT_2026-04-26.md`

### V70. Input Monitor App — 완료

목표:

- 물리 버튼 이벤트를 raw input과 gesture decoder 결과로 동시에 관찰한다.
- 버튼을 누른 순간, 뗀 순간, hold duration, event gap, decoded action을 화면/serial/log에 남긴다.

구현:

- `stage3/linux_init/init_v70.c`
  - `INIT_VERSION "0.8.1"`
  - `INIT_BUILD "v70"`
  - `TOOLS / INPUT MONITOR` app 추가
  - `inputmonitor [events]` command 추가
  - raw event 2줄 카드 표시와 DOWN/UP/REPEAT 색상 구분
  - 최신 gesture 판정 상단 대형 패널 표시
  - `waitgesture`와 같은 decoder helper 공유

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v70.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v70 boot — PASS
- bridge `version` → `A90 Linux init 0.8.1 (v70)` 및 `made by temmie0214` — PASS
- `status` → `creator: made by temmie0214`, `boot: BOOT OK shell 3S` — PASS
- `inputlayout` → v69 gesture mapping 유지 — PASS

산출:

- `stage3/linux_init/init_v70`
  - SHA256 `d7082127bbfeafd0508cf7a3b90079dc0f3f1b8b8238140cceb5dfe9063d7d12`
- `stage3/ramdisk_v70.cpio`
  - SHA256 `98ae190435469f2817d6d04fce076e643f2cb5f9e1fbafd69d9c865e1d1907b3`
- `stage3/boot_linux_v70.img`
  - SHA256 `5e3657ba14705bdee9cc772cb8916601bfe1a92f31122475c1115896e2a42cb1`
- `docs/reports/NATIVE_INIT_V70_INPUT_MONITOR_2026-04-26.md`

### V71. HUD/Menu Live Log Tail Panel — 완료

구현:

- `stage3/linux_init/init_v71.c`
  - `INIT_VERSION "0.8.2"`
  - `INIT_BUILD "v71"`
  - 공통 `kms_draw_log_tail_panel()` renderer 추가
  - hidden HUD와 auto HUD menu visible 상태에 `LIVE LOG TAIL` 표시
  - manual `screenmenu`도 공간이 있을 때 live log tail 표시
  - live log tail 제목/본문 간격, 줄 수, wrap 처리 개선
  - POWER 메뉴가 아닌 auto menu 상태에서는 일반 serial 명령 허용

검증:

- static ARM64 build — PASS
- bridge `version` → `A90 Linux init 0.8.2 (v71)` 및 `made by temmie0214` — PASS
- bridge `status` → `autohud: running` — PASS
- `screenmenu` framebuffer present 후 `q` cancel 및 HUD restore — PASS
- menu-active `ls /` 허용, `waitkey 1`/`recovery` 보호 차단 — PASS

### V72. Display Test Screen + Color Packing — 완료

구현:

- `stage3/linux_init/init_v72.c`
  - `INIT_VERSION "0.8.3"`
  - `INIT_BUILD "v72"`
  - `TOOLS / DISPLAY TEST`와 `displaytest` 명령 추가
  - 색상 팔레트, 폰트 scale ladder, wrap sample, safe-area/cutout grid 표시
  - display test 상단을 `TOP LEFT SLOT` / `PUNCH HOLE` / `TOP RIGHT SLOT`으로 분리 표시
  - `DRM_FORMAT_XBGR8888` framebuffer color packing 보정
  - on-device changelog `0.8.3 v72` 추가

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v72.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v72 boot — PASS
- bridge `version` → `A90 Linux init 0.8.3 (v72)` 및 `made by temmie0214` — PASS
- bridge `displaytest` → framebuffer present `1080x2400` — PASS
- bridge `autohud 2` 후 `status` → `autohud: running` — PASS

산출:

- `stage3/linux_init/init_v72`
  - SHA256 `3215710e0e5cc4038dea74b0f22575cbeda9e90625cb53b45f702db2b4f08619`
- `stage3/ramdisk_v72.cpio`
  - SHA256 `7e8cad648cec15d7dffe1cb9e8a2b2afa1aa297a01b9450234c26b1cd6ffcc41`
- `stage3/boot_linux_v72.img`
  - SHA256 `2f7e7927f1f22d540a37d7bafd7176730bae24bee418dfb667bfd6805cf0eebf`
- `docs/reports/NATIVE_INIT_V72_DISPLAY_TEST_2026-04-27.md`

### V73. Shell Protocol V1 + a90ctl Wrapper — 완료

구현:

- `stage3/linux_init/init_v73.c`
  - `INIT_VERSION "0.8.4"`
  - `INIT_BUILD "v73"`
  - `cmdv1 <command> [args...]` shell wrapper 추가
  - `A90P1 BEGIN` / `A90P1 END` framed result 추가
  - END record에 `seq`, `cmd`, `rc`, `errno`, `duration_ms`, `status` 포함
  - unknown command와 menu busy 결과도 rc/status로 frame 처리
  - on-device changelog `0.8.4 v73` 추가
- `scripts/revalidation/a90ctl.py`
  - bridge로 `cmdv1` 실행
  - text/JSON 결과 출력
  - `--allow-error`, `--hide-on-busy`, `--quiet`, `--verbose` 지원

검증:

- static ARM64 build — PASS
- `stage3/boot_linux_v73.img` marker 확인 — PASS
- native → TWRP → boot partition flash → v73 boot — PASS
- bridge `version` → `A90 Linux init 0.8.4 (v73)` 및 `made by temmie0214` — PASS
- bridge `cmdv1 status` → `A90P1 END ... rc=0 ... status=ok` — PASS
- bridge `cmdv1 nope` → `A90P1 END ... rc=-2 ... status=unknown` — PASS
- bridge `cmdv1 waitkey 1` while menu visible → `A90P1 END ... rc=-16 ... status=busy` — PASS
- `a90ctl.py status`, `--json --allow-error nope`, `--hide-on-busy status` — PASS

산출:

- `stage3/linux_init/init_v73`
  - SHA256 `7ce8063b6e343dd49ec8e1f2a0856936794bee761242ae6bd333ae1a96b51083`
- `stage3/ramdisk_v73.cpio`
  - SHA256 `dfb14b9a9ab5c48cd95175a0301c4ba8f737638639f2d77dc87af5613524c5df`
- `stage3/boot_linux_v73.img`
  - SHA256 `241e44ef70eb3dc187c8dd44c62c26943c42bd952c7d122374295463d67f159a`
- `docs/reports/NATIVE_INIT_V73_CMDV1_PROTOCOL_2026-04-27.md`

### Host Tooling. native_init_flash cmdv1 Verify — 완료

구현:

- `scripts/revalidation/a90ctl.py`
  - `run_cmdv1_command(host, port, timeout, command)` import용 helper 추가
  - 기존 CLI 동작 유지
- `scripts/revalidation/native_init_flash.py`
  - `--verify-protocol {auto,cmdv1,raw}` 추가
  - 기본 `auto`는 `cmdv1 version/status`의 `rc=0`, `status=ok` 확인
  - `A90P1 END`가 없을 때만 pre-v73 호환용 raw `version` 검증으로 fallback
  - `recovery`/`hide`/TWRP reboot 경로는 연결 종료 가능성이 있어 raw bridge 유지

검증:

- `python3 -m py_compile scripts/revalidation/a90ctl.py scripts/revalidation/native_init_flash.py` — PASS
- `native_init_flash.py --verify-only --expect-version "A90 Linux init 0.8.4 (v73)"` — PASS
- `native_init_flash.py --verify-only --verify-protocol raw --expect-version "A90 Linux init 0.8.4 (v73)"` — PASS
- `native_init_flash.py --verify-only --verify-protocol cmdv1 --expect-version "A90 Linux init 0.8.4 (v73)"` — PASS

### Host Tooling. NCM/tcpctl cmdv1 Adoption — 완료

구현:

- `scripts/revalidation/a90ctl.py`
  - reboot 직후 bridge listener가 먼저 열리고 ACM serial이 늦게 붙는 구간을 timeout 내 재시도
- `scripts/revalidation/ncm_host_setup.py`
  - `--device-protocol {auto,cmdv1,raw}` 추가
  - setup/status 쪽 짧은 device command는 `cmdv1` rc/status 우선
  - `off` rollback은 USB 재열거 가능성이 있어 raw bridge 유지
- `scripts/revalidation/netservice_reconnect_soak.py`
  - `--device-protocol {auto,cmdv1,raw}` 추가
  - bridge version/netservice status/usbnet status/ifconfig는 `cmdv1` rc/status 우선
  - `netservice start|stop`은 USB 재열거 가능성이 있어 raw bridge 유지
- `scripts/revalidation/tcpctl_host.py`
  - `--device-protocol {auto,cmdv1,raw}` 추가
  - install 후 chmod/sha256, smoke/soak bridge version은 `cmdv1` rc/status 우선
  - tcpctl listener/transfer streaming은 raw bridge 유지

검증:

- `python3 -m py_compile scripts/revalidation/a90ctl.py scripts/revalidation/ncm_host_setup.py scripts/revalidation/netservice_reconnect_soak.py scripts/revalidation/tcpctl_host.py` — PASS
- 세 host script `--help` import/argparse smoke — PASS
- mock helper로 `cmdv1` success와 `A90P1 END` 미검출 auto raw fallback — PASS

### V74. cmdv1x Argument Encoding — 완료

구현:

- `stage3/linux_init/init_v74.c`
  - `INIT_VERSION "0.8.5"`
  - `INIT_BUILD "v74"`
  - `cmdv1x <len:hex-utf8-arg>...` 추가
  - 기존 `cmdv1 <command> [args...]` compatibility 유지
  - malformed `cmdv1x` decode 실패도 `A90P1 END ... status=error`로 frame 처리
  - on-device changelog `0.8.5 v74 CMDV1 ARG ENCODING` 추가
- `scripts/revalidation/a90ctl.py`
  - `encode_cmdv1_line()` 추가
  - simple argv는 legacy `cmdv1`, whitespace/empty/`#` 시작 인자는 `cmdv1x` 자동 선택
  - `shell_command_to_argv()` 공유 helper 추가
- `scripts/revalidation/ncm_host_setup.py`
- `scripts/revalidation/netservice_reconnect_soak.py`
- `scripts/revalidation/tcpctl_host.py`
  - command string parsing은 `a90ctl.py` helper로 통일

검증:

- static ARM64 build — PASS
- `stage3/ramdisk_v74.cpio`, `stage3/boot_linux_v74.img` 생성 — PASS
- boot image marker strings `A90 Linux init 0.8.5 (v74)`, `A90v74`, `cmdv1x` — PASS
- host encoder smoke: `status` → `cmdv1`, `echo "hello world"` → `cmdv1x` — PASS
- Python py_compile + mock legacy/encoded selection + diff check — PASS
- native → TWRP → boot partition flash → v74 boot — PASS
- `native_init_flash.py stage3/boot_linux_v74.img --from-native --expect-version "A90 Linux init 0.8.5 (v74)"` — PASS
- `a90ctl.py --json status` → `rc=0`, `status=ok` — PASS
- `a90ctl.py --json echo "hello world"` → `cmdv1x ...`, `rc=0`, `status=ok` — PASS
- malformed direct `cmdv1x` → `rc=-22`, `status=error` — PASS

산출:

- `stage3/linux_init/init_v74`
  - SHA256 `7868795581cf7974b6c2f24af7dfea75399a429d163f6dc7700007b069bdd872`
- `stage3/ramdisk_v74.cpio`
  - SHA256 `90060ba7c2cd57ad3bb1c271ccafc9bc109fa57767d80747e03db02b8b08f92a`
- `stage3/boot_linux_v74.img`
  - SHA256 `e12839be90ad59e13c8289e2eab8d9441f8bfd2b907bd0f7f819ff65f581f1b4`
- `docs/reports/NATIVE_INIT_V74_CMDV1X_ARG_ENCODING_2026-04-27.md`

## 보류 큐

- ADB 안정화 재검토
- dropbear SSH
- Buildroot/rootfs 묶음
- Android framework 복구 시도

### Physical USB Reconnect. ACM/NCM/tcpctl — 완료

구현:

- `scripts/revalidation/physical_usb_reconnect_check.py`
  - v74 bridge 기준 version 확인
  - netservice가 꺼져 있으면 start 후 NCM ping/tcpctl 검증
  - `READY` 출력 후 실제 USB 케이블 unplug/replug를 기다림
  - replug 후 bridge version, NCM host interface, ping, tcpctl status/run을 재검증
  - script가 netservice를 직접 시작했다면 기본적으로 ACM-only 상태로 복구
- `scripts/revalidation/README.md`
  - 물리 케이블 reconnect 검증 사용법 추가

사용:

```bash
python3 ./scripts/revalidation/physical_usb_reconnect_check.py --manual-host-config
```

주의:

- 현재 sudo noninteractive가 막혀 있으므로 host `enx...` IP 설정은 사용자가 출력된 명령을 직접 실행해야 할 수 있다.

검증:

- `physical_usb_reconnect_check.py --manual-host-config ...` — PASS
- baseline 전 netservice disabled → runner가 netservice start — PASS
- baseline NCM ping 3/3, tcpctl ping/status/run — PASS
- 실제 케이블 unplug 감지: `/dev/ttyACM0` disappeared — PASS
- replug 후 bridge `A90 Linux init 0.8.5 (v74)` recovery — PASS
- replug 후 NCM host interface `enx0644eea6f44d` 복구 — PASS
- replug 후 NCM ping 3/3, tcpctl ping/status/run — PASS
- final ACM-only restore: `ncm0=absent`, `tcpctl=stopped` — PASS

산출:

- `docs/reports/NATIVE_INIT_V74_PHYSICAL_USB_RECONNECT_2026-04-27.md`

### V75. Quiet Idle Serial Reattach Logs — 완료

구현:

- `stage3/linux_init/init_v75.c`
  - `INIT_VERSION "0.8.6"`
  - `INIT_BUILD "v75"`
  - idle serial reattach interval을 `60s`로 완화
  - `reason=idle-timeout` 성공 request/ok 로그 억제
  - idle failure와 수동/non-idle reattach 로그는 유지
  - on-device changelog `0.8.6 v75 QUIET IDLE REATTACH` 추가

검증:

- static ARM64 build — PASS
- `stage3/ramdisk_v75.cpio`, `stage3/boot_linux_v75.img` 생성 — PASS
- boot image marker strings `A90 Linux init 0.8.6 (v75)`, `A90v75`, `0.8.6 v75` — PASS
- native → TWRP → boot partition flash → v75 boot — PASS
- `cmdv1 version/status` verify: `rc=0`, `status=ok` — PASS
- 70초 이상 idle 후 신규 `idle-timeout` 성공 로그 없음 — PASS
- 수동 `reattach`는 `reason=command` request/ok 로그 유지 — PASS

산출:

- `stage3/linux_init/init_v75`
  - SHA256 `840d1cd349b203dd912e3c99dd6b799acfc4fe2f0295c52bdf3f0e9cfe4df1fe`
- `stage3/ramdisk_v75.cpio`
  - SHA256 `af5abb98fdd3f49a767a75db8bda51bcbfea1a9ed75b9e1f6c4dd781c28eb072`
- `stage3/boot_linux_v75.img`
  - SHA256 `50f76a3a9e84ad13f19116e9b6e5b3a1ece6a91b177b81ae8cab1509109452a5`
- `docs/reports/NATIVE_INIT_V75_QUIET_IDLE_REATTACH_2026-04-27.md`

### V76. AT Fragment Serial Noise Filter — 완료

구현:

- `stage3/linux_init/init_v76.c`
  - `INIT_VERSION "0.8.7"`
  - `INIT_BUILD "v76"`
  - `is_unsolicited_at_fragment_noise()` 추가
  - 짧은 `A`/`T` only fragment를 shell command dispatch 전에 무시
  - 기존 full `AT...` probe filter와 `cmdv1`/`cmdv1x` 경로 유지
  - on-device changelog `0.8.7 v76 AT FRAGMENT FILTER` 추가

검증:

- static ARM64 build — PASS
- `stage3/ramdisk_v76.cpio`, `stage3/boot_linux_v76.img` 생성 — PASS
- boot image marker strings `A90 Linux init 0.8.7 (v76)`, `A90v76`, `0.8.7 v76` — PASS
- native → TWRP → boot partition flash → v76 boot — PASS
- `cmdv1 version/status` verify: `rc=0`, `status=ok` — PASS
- raw bridge input `A`, `T`, `AT`, `ATA`, `ATAT`, `AT+GCAP`, `version` — unknown command 없음, `version` 정상 — PASS
- log에 `ignored AT fragment`와 `ignored AT probe` 기록 확인 — PASS
- `cmdv1x` whitespace echo smoke — PASS

산출:

- `stage3/linux_init/init_v76`
  - SHA256 `053986f290d7e87a080515253ad7e1dfbabc73baa462a1e978fe58acb4b1f467`
- `stage3/ramdisk_v76.cpio`
  - SHA256 `06e1d300cd20deea918a86a3eb7413756ddc09ee0ed198f031bb3ceda1d3a0c5`
- `stage3/boot_linux_v76.img`
  - SHA256 `016b2d0c38f3acd1e0868fd5fa86805e52ef88c2e22fdb240dc071b1b39f4b68`
- `docs/reports/NATIVE_INIT_V76_AT_FRAGMENT_FILTER_2026-04-27.md`

### V77. Display Test, Cutout Calibration — 완료

구현:

- `stage3/linux_init/init_v77.c`
  - `INIT_VERSION "0.8.8"`
  - `INIT_BUILD "v77"`
  - display test를 4페이지로 분리
  - page 1: color/pixel
  - page 2: font/wrap
  - page 3: safe/cutout calibration reference
  - page 4: HUD/menu preview
  - `cutoutcal [x y size]` 명령 추가
  - `TOOLS > CUTOUT CAL` interactive app 추가
  - app 조작: VOL+/VOL- adjust, POWER field 변경, POWER long/double 또는 VOL+DN back
  - auto menu app에서 VOL+/VOL- page 이동, POWER back
  - `displaytest [0-3|colors|font|safe|layout]` 지원
  - on-device changelog `0.8.8 v77 DISPLAY TEST PAGES` 추가

검증:

- static ARM64 build — PASS
- `stage3/ramdisk_v77.cpio`, `stage3/boot_linux_v77.img` 생성 — PASS
- boot image marker strings `A90 Linux init 0.8.8 (v77)`, `A90v77`, `0.8.8 v77` — PASS
- native → TWRP → boot partition flash → v77 display/cutout baseline boot — PASS
- `cmdv1 version/status` verify: `rc=0`, `status=ok` — PASS
- `displaytest colors/font/safe/layout` 각각 `rc=0`, `status=ok` — PASS
- `cutoutcal`, `cutoutcal 540 80 49`, `displaytest safe` 재검증 — PASS

비고:

- SD workspace 기능은 버전 의미를 맞추기 위해 `0.8.9 (v78)`로 승격했다.

### V78. Ext4 SD Workspace + Mountsd — 완료

구현:

- `stage3/linux_init/init_v78.c`
  - `INIT_VERSION "0.8.9"`
  - `INIT_BUILD "v78"`
  - v77 display/cutout baseline 유지
  - SD 카드 `/dev/block/mmcblk0p1`을 `ext4` label `A90_NATIVE`로 포맷
  - `mountsd [status|ro|rw|off|init]` 명령 추가
  - SD workspace 표준 경로: `/mnt/sdext/a90`
  - workspace 하위 디렉터리: `bin`, `logs`, `tmp`, `rootfs`, `images`, `backups`
  - `status` 출력에 `mountsd` 상태 통합
  - on-device changelog `0.8.9 v78 SD WORKSPACE` 추가

검증:

- static ARM64 build — PASS
- `stage3/ramdisk_v78.cpio`, `stage3/boot_linux_v78.img` 생성 — PASS
- boot image marker strings `A90 Linux init 0.8.9 (v78)`, `A90v78`, `0.8.9 v78` — PASS
- SD ext4 포맷: `LABEL="A90_NATIVE"`, `TYPE="ext4"` — PASS
- `mountsd init`, workspace dir 생성, write/sync/read — PASS
- `mountsd ro/off/status`와 최종 `status` 통합 출력 — PASS
- `autohud 2` restore와 최종 status — PASS

산출:

- `stage3/linux_init/init_v78`
  - SHA256 `fc2b8f57482deddfe31885e8089e2047d7af08c3ac36414a1e644a2d43ed7274`
- `stage3/ramdisk_v78.cpio`
  - SHA256 `d1e37f098b9a15e2b00e016b882ec40b3fd68ce81f3c68d0a7c303e7a7958fd8`
- `stage3/boot_linux_v78.img`
  - SHA256 `2f57f29e623838601b664001b92bb4ac43e47e03eb0d9cb45bd86322ec52d099`
- `docs/reports/NATIVE_INIT_V78_SD_WORKSPACE_2026-04-29.md`

### V79. Boot-Time SD Health Check + Cache Fallback — 완료

구현:

- `stage3/linux_init/init_v79.c`
  - `INIT_VERSION "0.8.10"`
  - `INIT_BUILD "v79"`
  - boot splash에 cache/SD/storage/serial/runtime 진행 로그 표시
  - expected SD UUID `c6c81408-f453-11e7-b42a-23a2c89f58bc` 확인
  - `/mnt/sdext/a90/.a90-native-id` identity marker 확인/초기화
  - boot-time write/sync/read probe로 SD rw 검증
  - 검증 성공 시 `/mnt/sdext/a90`를 main runtime storage로 설정
  - 실패 시 `/cache` fallback과 HUD warning 표시
  - `storage` 명령과 `status` storage section 추가
  - `mountsd status`에 current/expected UUID match 표시 추가
  - on-device changelog `0.8.10 v79 BOOT SD PROBE` 추가

검증:

- static ARM64 build — PASS
- `stage3/ramdisk_v79.cpio`, `stage3/boot_linux_v79.img` 생성 — PASS
- boot image marker strings `A90 Linux init 0.8.10 (v79)`, `A90v79`, `0.8.10 v79`, expected UUID, SD probe splash lines — PASS

산출:

- `stage3/linux_init/init_v79`
  - SHA256 `c631667a18a55c91e829a24211b5425bdcad2c24c3d4ef7aef98a0745d9e4d03`
- `stage3/ramdisk_v79.cpio`
  - SHA256 `68cb4b6764c5d8a106a24f4b270e5e96bf5a266fa11926213a78640a02a50cf1`
- `stage3/boot_linux_v79.img`
  - SHA256 `1e7363085c3edb541b88b360c6e801eef6fcc67feb421b752bdc236c805b8318`
- `docs/reports/NATIVE_INIT_V79_BOOT_STORAGE_2026-04-29.md`

### V80. PID1 Source Layout Split — 완료

- `stage3/linux_init/init_v80.c`
  - `INIT_VERSION "0.8.11"`
  - `INIT_BUILD "v80"`
  - include 기반 entrypoint로 전환
- `stage3/linux_init/v80/*.inc.c`
  - `00_prelude`
  - `10_core_log_console`
  - `20_device_display`
  - `30_status_hud`
  - `40_menu_apps`
  - `50_boot_services`
  - `60_shell_basic_commands`
  - `70_storage_android_net`
  - `80_shell_dispatch`
  - `90_main`
- 의도:
  - PID1을 아직 여러 프로세스로 쪼개지 않고, 단일 static `/init` binary는 유지
  - static global/state를 유지해서 v79 behavior drift를 최소화
  - 다음 단계에서 helper/process 분리 후보를 더 안전하게 고르기 위한 구조 확보
- 검증:
  - static ARM64 build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v80.cpio`, `stage3/boot_linux_v80.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.11 (v80)`, `A90v80`, `0.8.11 v80 SOURCE MODULES` — PASS
  - TWRP flash and post-boot `cmdv1 version/status` — PASS
  - bridge regression: `storage`, `mountsd status`, `help`, `inputlayout`, `displaytest safe`, `statushud`, `logpath`, `timeline`, `autohud` — PASS
- 산출:
  - `stage3/linux_init/init_v80`
    - SHA256 `f8ad48229cc96cc9a580dbf54b6a5aad847499fa1b9ca5abc517523bbf34292a`
  - `stage3/ramdisk_v80.cpio`
    - SHA256 `8d8c4485ae2d65dfcfff3c867b75dba712fa45b28738dca665af1051b24c6fed`
  - `stage3/boot_linux_v80.img`
    - SHA256 `15a23e7485cc08e3eb46aa515ddc341ba2b14b115415b1216b805947f9612181`
  - `docs/reports/NATIVE_INIT_V80_SOURCE_MODULES_2026-04-29.md`

### V81. Config/Util True Base Modules — 완료

- `stage3/linux_init/a90_config.h`
- `stage3/linux_init/a90_util.c/h`
- 의도:
  - version/path/constant와 공통 파일/시간/errno helper를 실제 `.c/.h` API로 승격
  - PID1 include tree behavior drift를 최소화하고 다음 모듈 추출 기반 확보
- 검증:
  - static ARM64 multi-source build with `-Wall -Wextra` — PASS
  - TWRP flash and post-boot `cmdv1 version/status` — PASS
  - bridge regression: `storage`, `mountsd status`, `help`, `inputlayout`, `displaytest safe`, `statushud`, `logpath`, `timeline`, `autohud` — PASS
- 산출:
  - `docs/reports/NATIVE_INIT_V81_CONFIG_UTIL_2026-04-29.md`

### V82. Log/Timeline True API Modules — 완료

- `stage3/linux_init/a90_log.c/h`
- `stage3/linux_init/a90_timeline.c/h`
- `stage3/linux_init/init_v82.c`
- `stage3/linux_init/v82/*.inc.c`
- 의도:
  - native log path/state와 boot timeline array를 include tree 밖 실제 `.c/.h` API로 승격
  - console/shell/cmdproto, storage, KMS/HUD/menu, netservice는 v82에서 이동하지 않고 안정성 유지
- 검증:
  - static ARM64 multi-source build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v82.cpio`, `stage3/boot_linux_v82.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.13 (v82)`, `A90v82`, `0.8.13 v82 LOG TIMELINE API` — PASS
  - TWRP flash and post-boot `cmdv1 version/status` — PASS
  - bridge regression: `version`, `status`, `logpath`, `timeline`, `bootstatus`, `storage`, `mountsd status`, `displaytest safe`, `autohud 2` — PASS
- 산출:
  - `stage3/linux_init/init_v82`
    - SHA256 `56073411436ded0d75ce53ca2bdb70ca486201588d68dae4dff69029f34a5646`
  - `stage3/ramdisk_v82.cpio`
    - SHA256 `2d22fed414f101d0bd033754f127101730a6ad928ac7e6454e93587892cd3a4f`
  - `stage3/boot_linux_v82.img`
    - SHA256 `b023e1cf38c5fa1f0328030975189e99bcbb47a9715dadde1af0070badb6ab73`
  - `docs/reports/NATIVE_INIT_V82_LOG_TIMELINE_2026-04-29.md`

### V83. Console True API Module — 완료

- `stage3/linux_init/a90_console.c/h`
- `stage3/linux_init/init_v83.c`
- `stage3/linux_init/v83/*.inc.c`
- 의도:
  - `console_fd`, attach/reattach, readline, cancel polling, console write/printf를 실제 `.c/.h` API로 승격
  - shell dispatch와 `cmdv1/cmdv1x` framed protocol은 v83에서 이동하지 않고 다음 분리 후보로 보존
- 검증:
  - static ARM64 multi-source build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v83.cpio`, `stage3/boot_linux_v83.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.14 (v83)`, `A90v83`, `0.8.14 v83 CONSOLE API` — PASS
  - TWRP flash and post-boot `cmdv1 version/status` — PASS
  - bridge regression: `version`, `status`, `logpath`, `timeline`, `bootstatus`, `storage`, `mountsd status`, `displaytest safe`, `autohud 2` — PASS
  - console regression: `cat`, `logcat`, `run /bin/a90sleep 1`, `cpustress 3 2`, `watchhud 1 2`, q cancel, `reattach`, `usbacmreset` — PASS
- 산출:
  - `stage3/linux_init/init_v83`
    - SHA256 `0ae4f025d1c9bff5cb2bd89f42a15d2065c62eac18aa568cc13b9e8b0812e8e5`
  - `stage3/ramdisk_v83.cpio`
    - SHA256 `28d5cb735da2b3180df7f8aa100a3a1b47c5ec6f9870363a9f20b82d317cd878`
  - `stage3/boot_linux_v83.img`
    - SHA256 `1a9bdc7582485c95eee107753627e66aa4d2f53ed03bdb3039da18fab027c124`
  - `docs/reports/NATIVE_INIT_V83_CONSOLE_API_2026-04-29.md`
  - `docs/reports/NATIVE_INIT_V83_CONSOLE_SHELL_CMDPROTO_DEPENDENCY_MAP_2026-04-29.md`

### V84. Cmdproto True API Module — 완료

- `stage3/linux_init/a90_cmdproto.c/h`
- `stage3/linux_init/init_v84.c`
- `stage3/linux_init/v84/*.inc.c`
- 의도:
  - `cmdv1/cmdv1x` frame/status/decode 책임을 실제 `.c/.h` API로 승격
  - shell command table, busy gate, last result, dispatch는 v84 include tree에 보존
- 검증:
  - static ARM64 multi-source build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v84.cpio`, `stage3/boot_linux_v84.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.15 (v84)`, `A90v84`, `0.8.15 v84 CMDPROTO API` — PASS
  - TWRP flash and post-boot `cmdv1 version/status` — PASS
  - protocol regression: `cmdv1` ok/unknown/busy, malformed `cmdv1x`, whitespace argv — PASS
  - bridge regression: `logpath`, `timeline`, `bootstatus`, `storage`, `mountsd status`, `displaytest safe`, `autohud 2` — PASS
  - cancel regression: `run`, `cpustress`, `watchhud` q cancel — PASS
- 산출:
  - `stage3/linux_init/init_v84`
    - SHA256 `e52d034cbd3a741841e7be9ed45b8c9a54d5c2db491075fde022097374879886`
  - `stage3/ramdisk_v84.cpio`
    - SHA256 `8223b1c31d4ccca2521647feb9d50d864dd2332a260cc79f2272d5e74547763f`
  - `stage3/boot_linux_v84.img`
    - SHA256 `0a0be54d12489d7aa08437cb7e1aa3537448ddfed49393538a144e71f084bdcd`
  - `docs/reports/NATIVE_INIT_V84_CMDPROTO_API_2026-04-30.md`

### V85. Run/Service Lifecycle API Module — 완료

- `stage3/linux_init/a90_run.c/h`
- `stage3/linux_init/a90_service.c/h`
- `stage3/linux_init/init_v85.c`
- `stage3/linux_init/v85/*.inc.c`
- 의도:
  - `run`/timeout/cancel/reap/stop 책임을 실제 `.c/.h` API로 승격
  - `autohud`, `tcpctl`, `adbd` PID를 service registry 내부 static 상태로 관리
  - netservice 정책과 shell dispatch는 v85 include tree에 보존
- 검증:
  - static ARM64 multi-source build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v85.cpio`, `stage3/boot_linux_v85.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.16 (v85)`, `A90v85`, `0.8.16 v85 RUN SERVICE API` — PASS
  - TWRP flash and post-boot `cmdv1 version/status` — PASS
  - bridge regression: `logpath`, `timeline`, `bootstatus`, `storage`, `mountsd status` — PASS
  - runtime regression: `run`, `runandroid`, `cpustress`, `watchhud`, `autohud`, `stophud` — PASS
  - cancel regression: `run`, `cpustress`, `watchhud` q cancel — PASS
  - service regression: `startadbd`, stale PID status, `stopadbd`, `netservice status/start/stop` — PASS
  - NCM host ping은 host `sudo` IP 설정이 필요해 Codex 세션에서는 보류
- 산출:
  - `stage3/linux_init/init_v85`
    - SHA256 `ca227754279f8f23484dce6db4b0b8df9c6cb0412deec916be32dd9a028c31f2`
  - `stage3/ramdisk_v85.cpio`
    - SHA256 `5d35a08d472906b6ae9ad6e0dc0a364a6b1a08e42bc0de51674073901a19fc68`
  - `stage3/boot_linux_v85.img`
    - SHA256 `9e3da0ffd0616292b563c06acee9977de402db84f1de6994db0feb6cf6cf367e`
  - `docs/plans/NATIVE_INIT_V85_RUN_SERVICE_PLAN_2026-04-30.md`
  - `docs/reports/NATIVE_INIT_V85_RUN_SERVICE_API_2026-04-30.md`

### V86. KMS/Draw API Module — 완료

- `stage3/linux_init/a90_kms.c/h`
- `stage3/linux_init/a90_draw.c/h`
- `stage3/linux_init/init_v86.c`
- `stage3/linux_init/v86/*.inc.c`
- 의도:
  - DRM/KMS dumb-buffer 상태와 framebuffer drawing primitive를 실제 `.c/.h` API로 승격
  - HUD/menu/input/displaytest 정책은 v86 include tree에 보존해 behavior drift 최소화
  - v86 include tree의 direct `kms_state` / `struct kms_display_state` 접근 제거
- 검증:
  - static ARM64 multi-source build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v86.cpio`, `stage3/boot_linux_v86.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.17 (v86)`, `A90v86`, `0.8.17 v86 KMS DRAW API` — PASS
  - native bridge → TWRP flash → post-boot `cmdv1 version/status` — PASS
  - display regression: `kmsprobe`, `kmssolid`, `kmsframe`, `statushud`, `displaytest`, `cutoutcal`, `autohud` — PASS
  - blocking regression: raw `screenmenu` + q cancel, raw `inputmonitor 0` + q cancel — PASS
- 산출:
  - `stage3/linux_init/init_v86`
    - SHA256 `e3d5e777a3825fa2c5212ab8b7de2fda74b8ced05881b82d75a666fa58ef1e81`
  - `stage3/ramdisk_v86.cpio`
    - SHA256 `6d69aa340162c6a3279d2fa73a10452b50bb5956814da9bdc73524e85e06ebdd`
  - `stage3/boot_linux_v86.img`
    - SHA256 `ca9991061edd1a7a1f33e61ebdbd61df4be5ce7bd9e3d3c5d23351b0c03afbc3`
  - `docs/plans/NATIVE_INIT_V86_KMS_DRAW_PLAN_2026-04-30.md`
  - `docs/reports/NATIVE_INIT_V86_KMS_DRAW_API_2026-04-30.md`

### V87. Input API Module — PASS

- `stage3/linux_init/a90_input.c/h`
- `stage3/linux_init/init_v87.c`
- `stage3/linux_init/v87/*.inc.c`
- 의도:
  - 물리 버튼 open/close, key wait, gesture wait, decoder, menu action mapping을 실제 `.c/.h` API로 승격
  - menu/HUD/displaytest 정책은 v87 include tree에 보존해 behavior drift 최소화
  - `BOOT OK shell 3S` 형태의 절삭 시간을 `BOOT OK shell 4.0s` 형태의 0.1초 표기로 개선
- 검증:
  - static ARM64 multi-source build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v87.cpio`, `stage3/boot_linux_v87.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.18 (v87)`, `A90v87`, `0.8.18 v87 INPUT API` — PASS
  - old direct `key_wait_context` / `open_key_wait_context` / `wait_for_input_gesture` 구현 제거 — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - `bootstatus`의 `BOOT OK shell 4.0s` 0.1초 표기 — PASS
  - `logpath`, `timeline`, `storage`, `mountsd status`, `inputlayout`, `inputcaps event0/event3` — PASS
  - `kmsprobe`, `kmsframe`, `statushud`, `displaytest safe`, `cutoutcal`, `autohud 2` — PASS
  - `run /bin/a90sleep 1`, `cpustress 3 2`, `watchhud 1 2` — PASS
- 산출:
  - `stage3/linux_init/init_v87`
    - SHA256 `122db3f8a089667fecab864e9e63d5ab65961da774ad20196820d74d5e124bc0`
  - `stage3/ramdisk_v87.cpio`
    - SHA256 `5d6cc0825da26c3bb89b8b45741c06814df1933ce32902662577ecedb49dfdb6`
  - `stage3/boot_linux_v87.img`
    - SHA256 `ad93b1bf69586a468e6fafdcf2045d1c6192b01dae96f02bc6b7c0edddb6a970`
  - `docs/plans/NATIVE_INIT_V87_INPUT_API_PLAN_2026-04-30.md`
  - `docs/reports/NATIVE_INIT_V87_INPUT_API_2026-04-30.md`

### V88. HUD API Module — PASS

- `stage3/linux_init/a90_hud.c/h`
- `stage3/linux_init/init_v88.c`
- `stage3/linux_init/v88/*.inc.c`
- 의도:
  - boot splash, status HUD, boot summary, warning/status display, log tail panel을 `a90_hud.c/h`로 분리
  - `screenmenu`, `blindmenu`, app routing, displaytest, cutoutcal, inputmonitor 화면은 v88 include tree에 유지
  - `hud -> kms/draw/metrics/storage/timeline/log` 방향은 허용하고 `hud -> menu`, `input -> menu`, `draw -> hud` 순환은 금지
- 검증:
  - static ARM64 multi-source build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v88.cpio`, `stage3/boot_linux_v88.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.19 (v88)`, `A90v88`, `0.8.19 v88 HUD API` — PASS
  - old direct `kms_draw_status_overlay` / `kms_draw_log_tail_panel` / `kms_draw_boot_splash` 구현 제거 — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - `statushud`, `autohud 2`, `watchhud 1 2`, `displaytest safe`, `storage`, `mountsd status` — PASS
  - `screenmenu` 표시와 raw `q` cancel recovery — PASS
- 산출:
  - `stage3/linux_init/init_v88`
    - SHA256 `2897aacfe521eaeffd09cbaef05b0d42f102090f38e886a76d7e16e34e0e48cc`
  - `stage3/ramdisk_v88.cpio`
    - SHA256 `0d5875e70078a25a72c7682fcd5a056be9956ae20ee0e2186aca24f686357091`
  - `stage3/boot_linux_v88.img`
    - SHA256 `a8b7a79be3866533042d9fbf883587943c12d195eb3486289b15683317852a6a`
  - `docs/plans/NATIVE_INIT_V88_HUD_API_PLAN_2026-05-02.md`
  - `docs/reports/NATIVE_INIT_V88_HUD_API_2026-05-02.md`

### V89. Menu Control API + Nonblocking Screenmenu — PASS

- `stage3/linux_init/a90_menu.c/h`
- `stage3/linux_init/init_v89.c`
- `stage3/linux_init/v89/*.inc.c`
- 의도:
  - menu page/action/app enum, item/page table, menu state 이동을 `a90_menu.c/h`로 분리
  - `screenmenu`/`menu`를 shell 점유 foreground 명령에서 background HUD show request로 변경
  - `hide`/`hidemenu`/`resume`을 정식 command로 등록
  - `blindmenu`는 rescue foreground menu로 유지
- 검증:
  - static ARM64 multi-source build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v89.cpio`, `stage3/boot_linux_v89.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.20 (v89)`, `A90v89`, `0.8.20 v89 MENU CONTROL API` — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - `screenmenu` 즉시 반환 `rc=0/status=ok/duration_ms=0` — PASS
  - menu visible 중 `status`, `logpath`, `timeline`, `storage` 응답 — PASS
  - `hide`, `bootstatus`, `statushud`, `autohud 2`, `displaytest safe`, `cutoutcal`, `watchhud 1 2` — PASS
- 산출:
  - `stage3/linux_init/init_v89`
    - SHA256 `516d3b0c93104c00a0a5d9a8633cfe7041a75b7cfcf35871d65cb9ccbefe689f`
  - `stage3/ramdisk_v89.cpio`
    - SHA256 `2a702cfdbe82633407583137dc5871b1a0911565cea1f3fcc1cfe0141cd2628e`
  - `stage3/boot_linux_v89.img`
    - SHA256 `57a6b5b5a9091c5fe0339e5359ec34e68af00f040c64dfc902636aaedbc618ba`
  - `docs/reports/NATIVE_INIT_V89_MENU_CONTROL_API_2026-05-02.md`

### V90. Metrics API — PASS

- `stage3/linux_init/a90_metrics.c/h`
- `stage3/linux_init/init_v90.c`
- `stage3/linux_init/v90/*.inc.c`
- 의도:
  - 배터리/CPU/GPU/MEM/전력/uptime sysfs snapshot 책임을 `a90_metrics.c/h`로 분리
  - HUD는 metrics snapshot을 표시하는 renderer로 유지
  - `status`, status HUD, CPU stress 화면의 metric callsite를 `a90_metrics_*` API로 통일
- 검증:
  - static ARM64 multi-source build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v90.cpio`, `stage3/boot_linux_v90.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.21 (v90)`, `A90v90`, `0.8.21 v90 METRICS API` — PASS
  - old HUD metrics API 제거 확인 — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - `statushud`, `autohud 2`, `watchhud 1 2`, `screenmenu`, `hide`, `storage`, `mountsd status` — PASS
  - `cpustress 3 2`, `displaytest safe`, `cutoutcal` — PASS
- 산출:
  - `stage3/linux_init/init_v90`
    - SHA256 `106c1b7d28bf6d9d82042bc4f3588bc3045ec3e06534cdbc58213cf859e6f4c1`
  - `stage3/ramdisk_v90.cpio`
    - SHA256 `66a2988105ab97db31154ab8e10ed5f11331adfee64bedcd9e95f20d7847295b`
  - `stage3/boot_linux_v90.img`
    - SHA256 `0a968f4732a948e1994b4788d29e46e81d74c2dc4170417c4e4d198d6440beee`
  - `docs/reports/NATIVE_INIT_V90_METRICS_API_2026-05-02.md`

### V91. CPU Stress External Helper — PASS

- `stage3/linux_init/helpers/a90_cpustress.c`
- `stage3/linux_init/init_v91.c`
- `stage3/linux_init/v91/*.inc.c`
- 의도:
  - CPU stress worker fork를 PID1 내부에서 제거하고 `/bin/a90_cpustress` helper로 분리
  - shell `cpustress`와 menu CPU stress app이 `a90_run` 기반 helper 실행/stop/reap을 사용
  - cancel/timeout 시 process-group stop으로 helper worker tree를 함께 종료
- 검증:
  - static ARM64 helper/init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v91.cpio`, `stage3/boot_linux_v91.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.22 (v91)`, `A90v91`, `0.8.22 v91 CPUSTRESS HELPER` — PASS
  - v91 tree old PID1 `cpustress_worker`/PID array 직접 관리 제거 확인 — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - `run /bin/a90_cpustress 1 1`, `cpustress 3 2`, q cancel — PASS
  - `statushud`, `autohud 2`, `watchhud 1 2`, `screenmenu`, `hide`, menu-visible `status`, dangerous-command busy gate — PASS
- 산출:
  - `stage3/linux_init/init_v91`
    - SHA256 `886f267b26ce4198668f933dafafbe93b81a8aa6c9bbec05cc77958b76aaf65d`
  - `stage3/linux_init/helpers/a90_cpustress`
    - SHA256 `2130ddf1821c4331d491706636e0197b0f587a086f182e8745e5b41333a069bd`
  - `stage3/ramdisk_v91.cpio`
    - SHA256 `ebd8c61fbc45c36aaecc77d98c29c54e4beacabd8369cb56b54d90a10668cac1`
  - `stage3/boot_linux_v91.img`
    - SHA256 `a0f027375da3bdd92fc2a4f3d6ed1e6a7ff3963dfcc5961d699dcb829477607f`
  - `docs/reports/NATIVE_INIT_V91_CPUSTRESS_HELPER_2026-05-02.md`

### V92. Shell/Controller Cleanup — PASS

- `stage3/linux_init/a90_shell.c/h`
- `stage3/linux_init/a90_controller.c/h`
- `stage3/linux_init/init_v92.c`
- `stage3/linux_init/v92/*.inc.c`
- 의도:
  - shell command flags/types, last result, protocol sequence, command lookup/result formatting을 `a90_shell` API로 분리
  - auto-menu/power-page busy gate와 hide word policy를 `a90_controller` API로 분리
  - command handler body와 command table entry는 v92 include tree에 유지해 visibility risk를 낮춤
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v92.cpio`, `stage3/boot_linux_v92.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.23 (v92)`, `A90v92`, `0.8.23 v92 SHELL CONTROLLER API` — PASS
  - old direct shell helper removal 확인 — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - unknown command `status=unknown`, menu busy/power-page busy `status=busy` — PASS
  - `screenmenu`, menu-visible `status/logpath/timeline/storage`, `hide` — PASS
  - `cpustress 3 2`, `autohud 2`, `watchhud 1 2` — PASS
- 산출:
  - `stage3/linux_init/init_v92`
    - SHA256 `d2bffdd2111406a2c409a0a03f5605163e016f86cf775199856daf70cd8017f5`
  - `stage3/ramdisk_v92.cpio`
    - SHA256 `1cd524c1ece925b3d5d70b7ee19a7247f1a40c00aab24535f165911fde335880`
  - `stage3/boot_linux_v92.img`
    - SHA256 `817a6a9e2b6c7f1c64e28d972122cd4c3ab022a9430a74a0fbfbef9301079b23`
  - `docs/reports/NATIVE_INIT_V93_STORAGE_API_2026-05-02.md`
  - `docs/reports/NATIVE_INIT_V94_BOOT_SELFTEST_API_2026-05-03.md`

### V93. Storage API First Split — PASS

- `stage3/linux_init/a90_storage.c/h`
- `stage3/linux_init/init_v93.c`
- `stage3/linux_init/v93/*.inc.c`
- 의도:
  - boot storage state, SD workspace probe, `/cache` fallback, `storage`/`mountsd` command logic을 `a90_storage.c/h`로 분리
  - HUD/menu/shell dispatch/netservice가 storage 내부 상태를 직접 보지 않게 status snapshot API로 연결
  - netservice/USB gadget 정책은 v94 후보로 분리해 v93 리스크를 boot-critical storage에 한정
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v93.cpio`, `stage3/boot_linux_v93.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.24 (v93)`, `A90v93`, `0.8.24 v93 STORAGE API` — PASS
  - v93 tree old storage globals 제거 확인 — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - `storage`, `mountsd status`, `mountsd ro/rw/init/off`, `logpath`, `timeline`, `bootstatus` — PASS
  - `mountsd off` + `mountsd init` 후 SD log path 복귀 — PASS
  - `statushud`, `autohud 2`, `screenmenu`, `hide`, `netservice status` — PASS
- 산출:
  - `stage3/linux_init/init_v93`
    - SHA256 `1f013323161b90f1b308631e91a2bbd15fac20d1a86ee3c6990d3c1b1c92855c`
  - `stage3/ramdisk_v93.cpio`
    - SHA256 `6a176f9cdf16b98c6945e87f19d754ab8a7e0de5732b2f1b67c52200a3c068e6`
  - `stage3/boot_linux_v93.img`
    - SHA256 `d62e861dfec7826a85e37d5f80d9c3ac562e65aaf35f37400d1bdafd5ffc889d`
  - `docs/reports/NATIVE_INIT_V93_STORAGE_API_2026-05-02.md`

### V94. Boot Selftest API — PASS

- `stage3/linux_init/a90_selftest.c/h`
- `stage3/linux_init/init_v94.c`
- `stage3/linux_init/v94/*.inc.c`
- 의도:
  - boot-time non-destructive selftest로 모듈화 회귀를 빠르게 감지
  - log/timeline/storage/metrics/KMS/input/service/ACM configfs 상태만 조회
  - 실패는 warn-only로 기록하고 shell/HUD 진입은 유지
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v94.cpio`, `stage3/boot_linux_v94.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.25 (v94)`, `A90v94`, `0.8.25 v94 BOOT SELFTEST API` — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - boot selftest `pass=8 warn=0 fail=0 duration=39ms` — PASS
  - `bootstatus`, `selftest`, `selftest verbose`, `selftest run`, `timeline`, `logcat` — PASS
  - `storage`, `mountsd status`, `statushud`, `autohud 2`, `screenmenu`, `hide`, `netservice status` — PASS
- 산출:
  - `stage3/linux_init/init_v94`
    - SHA256 `c679e021a154643d1b84dfe955c56591cf4fc113d1cd5d6aea8b6c8581aa64bd`
  - `stage3/ramdisk_v94.cpio`
    - SHA256 `31a69d6463131587e48462e05a61c15966f7dc20daf7d0a1099117041164b6be`
  - `stage3/boot_linux_v94.img`
    - SHA256 `ecf0665bc47c9315edaeb46b38ffe0c64c4ff6b6498378292934d8c580753d98`
  - `docs/reports/NATIVE_INIT_V94_BOOT_SELFTEST_API_2026-05-03.md`

### V95. Netservice / USB Gadget API — PASS

- `stage3/linux_init/a90_usb_gadget.c/h`
- `stage3/linux_init/a90_netservice.c/h`
- `stage3/linux_init/init_v95.c`
- `stage3/linux_init/v95/*.inc.c`
- 의도:
  - USB configfs/UDC/ACM primitive를 USB gadget API로 분리
  - NCM/tcpctl start/stop/enable/disable policy를 netservice API로 분리
  - shell/status/menu/selftest는 status snapshot API를 통해 상태 조회
  - USB 재열거 명령은 raw-control friendly 동작 유지
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v95.cpio`, `stage3/boot_linux_v95.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.26 (v95)`, `A90v95`, `0.8.26 v95 NETSERVICE USB API` — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - boot selftest `pass=8 warn=0 fail=0 duration=39ms` — PASS
  - `bootstatus`, `selftest verbose`, `storage`, `mountsd status`, `statushud`, `autohud 2`, `screenmenu`, `hide` — PASS
  - `usbacmreset` after hide, bridge reconnect, `version` — PASS
  - `netservice start`, host NCM ping 3/3, `tcpctl_host.py ping/status/run` — PASS
  - `netservice enable` → reboot → `enabled=yes`, `ncm0=present`, `tcpctl=running` — PASS
  - `netservice disable`, `ncm0=absent`, `tcpctl=stopped`, bridge `version` — PASS
- 산출:
  - `stage3/linux_init/init_v95`
    - SHA256 `13390d59c7a1d4dd460d2e88b6424ddc1759bb79d80aadbd2fd48382faa34390`
  - `stage3/ramdisk_v95.cpio`
    - SHA256 `3d6080c15201766f725cc3adf4c434278f528ea4ab5776e6d759f56ea95c81e5`
  - `stage3/boot_linux_v95.img`
    - SHA256 `cab9b2466e3162ec429e2634728e793990fe8cafc217e3be6b2c9a2f684b5824`
  - `docs/reports/NATIVE_INIT_V95_NETSERVICE_USB_API_2026-05-03.md`

### V96. Structure Audit / Refactor Debt Cleanup — PASS

- `stage3/linux_init/init_v96.c`
- `stage3/linux_init/v96/*.inc.c`
- `stage3/linux_init/a90_console.c`
- `stage3/linux_init/a90_menu.c/h`
- 의도:
  - v95 모듈 분리 이후 중복/겹침/직접 path 접근/남은 lifecycle 중복을 감사
  - stale `A90v83` console reattach klog marker를 `INIT_BUILD` 기반 출력으로 정리
  - v96 ABOUT/changelog/menu entry 추가
  - SD runtime, BusyBox, remote shell, Wi-Fi 기능 추가는 v97+로 보류
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v96.cpio`, `stage3/boot_linux_v96.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.27 (v96)`, `A90v96`, `0.8.27 v96 STRUCTURE AUDIT` — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - boot selftest `pass=8 warn=0 fail=0 duration=39ms` — PASS
  - `bootstatus`, `selftest verbose`, `storage`, `mountsd status`, `statushud`, `autohud 2`, `screenmenu`, `hide`, `netservice status` — PASS
- 산출:
  - `stage3/linux_init/init_v96`
    - SHA256 `2cee558e62f840dd9337ec1852d49116f4ffff99092a35bddece90f9659e65be`
  - `stage3/ramdisk_v96.cpio`
    - SHA256 `f41140ae0c8ad45170adc2927a438c70b002985e1b8e0f493b5711998cc2fe61`
  - `stage3/boot_linux_v96.img`
    - SHA256 `e890a3f4ac3ae59f3bff7a7307551c0545189e664e272b120198eb3b3762dacf`
  - `docs/reports/NATIVE_INIT_V96_STRUCTURE_AUDIT_2026-05-03.md`

### V97. SD Runtime Root — PASS

- `stage3/linux_init/init_v97.c`
- `stage3/linux_init/v97/*.inc.c`
- `stage3/linux_init/a90_runtime.c/h`
- 의도:
  - `/mnt/sdext/a90`를 native runtime root로 격상
  - runtime directory contract `bin/etc/logs/tmp/state/pkg/run` 고정
  - SD가 없거나 unsafe이면 `/cache/a90-runtime` fallback 유지
  - helper deployment, BusyBox, remote shell, Wi-Fi는 v98+로 보류
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v97.cpio`, `stage3/boot_linux_v97.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.28 (v97)`, `A90v97`, `0.8.28 v97 SD RUNTIME ROOT` — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - boot selftest `pass=9 warn=0 fail=0 duration=37ms` — PASS
  - `runtime`, `bootstatus`, `selftest verbose`, `storage`, `mountsd status`, `statushud`, `autohud 2`, `screenmenu`, `hide`, `netservice status` — PASS
- 산출:
  - `stage3/linux_init/init_v97`
    - SHA256 `f0868caa0f6b4b2bbc086870facb93f72ac3983b064dc43991871d678e445c78`
  - `stage3/ramdisk_v97.cpio`
    - SHA256 `9bc749822729f29a6653d5d3b6eb60fcba0038ccb7162c359bada046bdff0473`
  - `stage3/boot_linux_v97.img`
    - SHA256 `e170ec5b3d3eed6ddeb753471feac077b8afa57e450ee4ea37df5219ba28bd5b`
  - `docs/reports/NATIVE_INIT_V97_SD_RUNTIME_ROOT_2026-05-03.md`

### V98. Helper Deployment / Package Manifest — PASS

- `stage3/linux_init/init_v98.c`
- `stage3/linux_init/v98/*.inc.c`
- `stage3/linux_init/a90_helper.c/h`
- `scripts/revalidation/helper_deploy.py`
- 의도:
  - v97 runtime root 위에 helper inventory와 manifest path를 정의
  - `helpers` command로 helper path/presence/mode/fallback 상태 노출
  - `cpustress`는 preferred helper path를 사용하되 ramdisk fallback 유지
  - device-side SHA256은 PID1에서 수행하지 않고 host-side manifest material로 보류
  - BusyBox, remote shell, Wi-Fi는 v99+로 보류
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v98.cpio`, `stage3/boot_linux_v98.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.29 (v98)`, `A90v98`, `0.8.29 v98 HELPER DEPLOY` — PASS
  - TWRP flash → post-boot `cmdv1 version/status` — PASS
  - boot selftest `pass=10 warn=0 fail=0 duration=41ms` — PASS
  - `helpers`, `helpers verbose`, `helpers path a90_cpustress`, `cpustress 3 2`, `helper_deploy.py status/manifest/verify` — PASS
  - `runtime`, `storage`, `mountsd status`, `statushud`, `autohud 2`, `screenmenu`, `hide`, `netservice status` — PASS
- 산출:
  - `stage3/linux_init/init_v98`
    - SHA256 `0d55f6b70d71eba4524790fa72d4276694512806bc515f878a10a0693f0beac3`
  - `stage3/ramdisk_v98.cpio`
    - SHA256 `9b578bd02a0df42534381694ebcfd77d9943e746be3eff998c123bcb9c03ee8a`
  - `stage3/boot_linux_v98.img`
    - SHA256 `c341bc56cfd881bceaf61cb6a30193329ee65f32d686979a236a2e3322039d2e`
  - `docs/reports/NATIVE_INIT_V98_HELPER_DEPLOY_2026-05-03.md`

### V99. BusyBox Static Userland Evaluation — PASS

- `stage3/linux_init/init_v99.c`
- `stage3/linux_init/v99/*.inc.c`
- `stage3/linux_init/a90_userland.c/h`
- `scripts/revalidation/build_static_busybox.sh`
- `scripts/revalidation/busybox_userland.py`
- 의도:
  - static ARM64 BusyBox를 SD runtime root의 optional userland로 평가
  - native PID1 shell은 유지하고 `busybox`/`toybox` wrapper command만 추가
  - BusyBox/toybox inventory를 `status`, `bootstatus`, `selftest`, `userland`에서 확인
  - remote shell/dropbear는 v100+로 보류
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - static BusyBox 1.36.1 build and SHA256 verification — PASS
  - `stage3/ramdisk_v99.cpio`, `stage3/boot_linux_v99.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.8.30 (v99)`, `A90v99`, `0.8.30 v99 BUSYBOX USERLAND` — PASS
  - native flash → post-boot `cmdv1 version/status` — PASS
  - boot selftest `pass=11 warn=0 fail=0 duration=39ms` — PASS
  - `userland`, `userland verbose`, `userland test busybox`, `busybox sh -c`, `busybox ls /proc`, `userland test toybox` — PASS
  - `runtime`, `helpers verbose`, `storage`, `mountsd status`, `statushud`, `autohud 2`, `screenmenu`, `hide`, `netservice status` — PASS
- 산출:
  - `stage3/linux_init/init_v99`
    - SHA256 `fce445e98690773aa8a26d024d9e07a110a703ef28b9cdd933dbdf4bb2b3558a`
  - `stage3/ramdisk_v99.cpio`
    - SHA256 `4f8daa03c24c864afd0be76a9bbf6d2c6d849dce7ece51f1d5fdca6e565047d6`
  - `stage3/boot_linux_v99.img`
    - SHA256 `8d51b9a8f48e96472be9949e607e5868f5a8f4cad60580f37930e459c8ee4eaf`
  - BusyBox binary
    - SHA256 `95fcbded9318a643e51e15bc5b0f2f5281996e0b82d303ce0af8f9acc9685e7c`
  - `docs/reports/NATIVE_INIT_V99_BUSYBOX_USERLAND_2026-05-03.md`

### V100. Remote Shell Prototype — PASS

- `stage3/linux_init/init_v100.c`
- `stage3/linux_init/v100/*.inc.c`
- `stage3/linux_init/helpers/a90_rshell.c`
- `scripts/revalidation/rshell_host.py`
- 의도:
  - verified USB NCM 위에 opt-in custom TCP remote shell 후보를 추가
  - token auth와 NCM-only bind로 최소 보안 경계를 둠
  - Dropbear/PTY/SSH key 정책은 v101+ 이후로 보류
  - ACM serial bridge를 rescue/control channel로 유지
- 검증:
  - static ARM64 init/helper build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v100.cpio`, `stage3/boot_linux_v100.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.9.0 (v100)`, `A90v100`, `0.9.0 v100 REMOTE SHELL`, `A90RSH1` — PASS
  - native flash → post-boot `cmdv1 version/status` — PASS
  - boot selftest `pass=11 warn=0 fail=0 duration=33ms` — PASS
  - `bootstatus`, `helpers verbose`, `userland`, `storage`, `mountsd status`, `stat /bin/a90_rshell` — PASS
  - host NCM ping `192.168.7.1` → `192.168.7.2`: `3/3` — PASS
  - `rshell_host.py exec 'echo A90_RSHELL_OK'` and `rshell_host.py smoke` — PASS
  - `rshell stop` leaves no `a90_rshell` process — PASS
  - `netservice stop` rollback restores ACM serial and reports `ncm0=absent`, `tcpctl=stopped` — PASS
- 산출:
  - `stage3/linux_init/init_v100`
    - SHA256 `073f80024682fbdc655a4b3e99a025ef1d045d3e3ddf5bb63e0ded97d55f5a54`
  - `stage3/linux_init/helpers/a90_rshell`
    - SHA256 `235d30bc6bc0b6254b8f1383697cf03bbd6760eaf42944b786510d835ebdf02d`
  - `stage3/ramdisk_v100.cpio`
    - SHA256 `a27217ece3bea98ce6f6bbf3a468d09ca50fade7d7b3efc05f1e28dea26ee79a`
  - `stage3/boot_linux_v100.img`
    - SHA256 `1d15bcba2999d0c46caec3d568ac937201c13a924dd09a1586719154c22abd0c`
  - `docs/reports/NATIVE_INIT_V100_REMOTE_SHELL_2026-05-03.md`

### V101. Minimal Service Manager — PASS

- `stage3/linux_init/init_v101.c`
- `stage3/linux_init/v101/*.inc.c`
- `stage3/linux_init/a90_service.c/h`
- 의도:
  - PID-only service registry를 metadata/status API로 확장
  - `service list/status/start/stop/enable/disable` 공통 operator view 추가
  - autohud/tcpctl/adbd/rshell의 실제 start/stop 구현은 기존 owner에 유지
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v101.cpio`, `stage3/boot_linux_v101.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.9.1 (v101)`, `A90v101`, `0.9.1 v101 SERVICE MANAGER` — PASS
  - native flash → post-boot `cmdv1 version/status` — PASS
  - `service list`, `service status autohud/tcpctl/rshell/adbd` — PASS
  - `service stop/start autohud` — PASS
  - unsupported `service enable autohud/adbd` returns `-EOPNOTSUPP` — PASS
  - `service enable/disable tcpctl`, NCM ping, `tcpctl_host.py ping/status`, ACM rollback — PASS
  - `service start/stop rshell`, `rshell_host.py smoke`, rshell flag disable, tcpctl rollback — PASS
  - `statushud`, `autohud 2`, `screenmenu`, `hide`, `cpustress 3 2`, `storage`, `mountsd status` — PASS
- 산출:
  - `stage3/linux_init/init_v101`
    - SHA256 `5921c53e5c6992bb20c3d2ee55e653dd793cb5d76bf020ccb4d3e9fc621e620c`
  - `stage3/ramdisk_v101.cpio`
    - SHA256 `2a72368840d4c531be28972bd99ff736953aa5160b40e4bc023e64fd3a870ff6`
  - `stage3/boot_linux_v101.img`
    - SHA256 `c5d4f970534d7b7ddc42083ec1b3b7cbc98d0f56a9c726a1932d27cdff266624`
  - `docs/reports/NATIVE_INIT_V101_SERVICE_MANAGER_2026-05-03.md`

### V102. Diagnostics / Log Bundle — PASS

- `stage3/linux_init/init_v102.c`
- `stage3/linux_init/v102/*.inc.c`
- `stage3/linux_init/a90_diag.c/h`
- `scripts/revalidation/diag_collect.py`
- 의도:
  - read-only `diag [summary|full|bundle|paths]` command 추가
  - version/bootstatus/selftest/storage/runtime/helpers/userland/service/network/rshell/log tail을 한 번에 수집
  - host-side serial-first collector로 회귀 증거를 텍스트 파일로 저장
  - Wi-Fi inventory와 NCM optional checks는 v103+로 분리
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v102.cpio`, `stage3/boot_linux_v102.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.9.2 (v102)`, `A90v102`, `0.9.2 v102 DIAGNOSTICS`, `diag [summary|full|bundle|paths]` — PASS
  - native flash → post-boot `cmdv1 version/status` — PASS
  - `diag`, `diag full`, `diag paths`, `diag bundle` — PASS
  - `diag_collect.py --out tmp/diag/v102-smoke.txt` — PASS
  - `diag_collect.py --device-bundle --boot-image stage3/boot_linux_v102.img --out tmp/diag/v102-bundle.txt` — PASS
  - `service list`, `storage`, `runtime`, `statushud`, `autohud 2`, `screenmenu`, `hide`, `cpustress 3 2` — PASS
- 산출:
  - `stage3/linux_init/init_v102`
    - SHA256 `49499e5da3c84ef50996655605e06d1f33cd514862aeb361a97411e9b9db154a`
  - `stage3/ramdisk_v102.cpio`
    - SHA256 `375110ae184997fcf5334704ed1a8f738a3088e7e150467e9fc995f01ff86780`
  - `stage3/boot_linux_v102.img`
    - SHA256 `aca7aef3077334eb4b7e0f61fdfa27943b8ca23736271b10dd414f8029d1c49d`
  - `docs/reports/NATIVE_INIT_V102_DIAGNOSTICS_2026-05-03.md`

## 지금 바로 진행할 항목

1. v185 Communication Broker Protocol Plan

   - 계획: `docs/plans/NATIVE_INIT_V185_COMMUNICATION_BROKER_PLAN_2026-05-11.md`
   - 최신 결과: v184 24h+ readiness gate PASS
   - 산출: `docs/reports/NATIVE_INIT_V184_24H_SERVERIZATION_READINESS_2026-05-11.md`
   - 다음 큰 주제는 통신 프로토콜/broker로 선택했다
   - 이유: 보안 스캔과 패치효과 확인은 병렬/대기 시간이 크고, Wi-Fi/server화 전에 raw bridge 공유 구조를 먼저 안정화해야 한다

2. v182-v184 Mixed Soak / Serverization Gate

   - v182 failure classifier PASS, v183 8h pilot PASS, v184 24h+ readiness gate PASS
   - Wi-Fi baseline refresh와 exposure hardening은 post-v184 roadmap에서 재개 여부를 결정한다

3. v186+ Broker Skeleton / Harness Integration

   - `A90B1` host-local broker skeleton은 `scripts/revalidation/a90_broker.py`로 시작했다
   - live ACM bridge smoke, concurrent read-only client, rebind block 검증은 PASS했다
   - observer/supervisor가 raw bridge를 직접 점유하지 않도록 broker backend을 추가했고 live smoke/observe PASS했다

4. v190+ Broker Mixed-Soak Gate 이후 Wi-Fi 재개

   - broker가 multi-client read-only, exclusive lock, reconnect/audit를 통과하면 Wi-Fi baseline refresh를 재개한다

### V106-V108. UI/App Architecture Split — DONE

- v106 계획: `docs/plans/NATIVE_INIT_V106_UI_APP_ABOUT_PLAN_2026-05-04.md`
  - 결과: `docs/reports/NATIVE_INIT_V106_UI_APP_ABOUT_2026-05-04.md`
  - 목표: ABOUT/version/changelog 화면 렌더링을 `a90_app_about.c/h`로 분리
  - 기준: `A90 Linux init 0.9.6 (v106)` / `0.9.6 v106 APP ABOUT API`
  - 성격: 구조 개선, 메뉴 UX 변경 없음
- v107 계획: `docs/plans/NATIVE_INIT_V107_UI_APP_DISPLAYTEST_PLAN_2026-05-04.md`
  - 결과: `docs/reports/NATIVE_INIT_V107_UI_APP_DISPLAYTEST_2026-05-04.md`
  - 목표: `displaytest`와 `cutoutcal` 렌더링을 `a90_app_displaytest.c/h`로 분리
  - 기준: `A90 Linux init 0.9.7 (v107)` / `0.9.7 v107 APP DISPLAYTEST API`
  - 성격: display/cutout 화면 동작 보존
- v108 계획: `docs/plans/NATIVE_INIT_V108_UI_APP_INPUTMON_PLAN_2026-05-04.md`
  - 결과: `docs/reports/NATIVE_INIT_V108_UI_APP_INPUTMON_2026-05-04.md`
  - 목표: input layout/monitor/wait UI를 `a90_app_inputmon.c/h`로 분리
  - 기준: `A90 Linux init 0.9.8 (v108)` / `0.9.8 v108 APP INPUTMON API`
  - 성격: 저수준 `a90_input.c/h` 유지, app UI만 분리
- 공통 검증:
  - static ARM64 build, marker strings, `git diff --check`, host Python `py_compile`
  - real-device flash 후 `version`, `status`, `bootstatus`, `selftest verbose`, `screenmenu`, `hide`
  - 각 app별 화면/입력 회귀와 3-cycle quick soak

### V105. Long-Run Soak / Recovery RC — PASS

- 계획: `docs/plans/NATIVE_INIT_V105_SOAK_RC_PLAN_2026-05-04.md`
- 산출: `docs/reports/NATIVE_INIT_V105_SOAK_RC_2026-05-04.md`
- `stage3/linux_init/init_v105.c`
- `stage3/linux_init/v105/*.inc.c`
- `scripts/revalidation/native_soak_validate.py`
- 의도:
  - v96-v104 stack을 recovery-friendly 안정 기준 후보로 검증
  - bounded host quick soak로 serial/service/runtime/diagnostics/UI command 반복 검증
  - Wi-Fi bring-up, rfkill write, module load/unload, firmware/vendor mutation 금지
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v105.cpio`, `stage3/boot_linux_v105.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.9.5 (v105)`, `A90v105`, `0.9.5 v105 SOAK RC` — PASS
  - native flash → post-boot `cmdv1 version/status` — PASS
  - required command regression set — PASS
  - `native_soak_validate.py --cycles 10 --sleep 2` 14-command cycle — PASS
  - final `status` and `service list` after soak — PASS
- 산출:
  - `stage3/linux_init/init_v105`
    - SHA256 `624242bafb44598feaddf636a60b64a996d44f5e05dc622f64b79518706a8209`
  - `stage3/ramdisk_v105.cpio`
    - SHA256 `6733a511a5cc8a5a79c09333510c0d1913219ed13e15b3a2cbd1e7550be27726`
  - `stage3/boot_linux_v105.img`
    - SHA256 `2dcda57156385c2d092a0865ea31bd7853399287df5633d39b08ae4b01d53338`
  - `docs/reports/NATIVE_INIT_V105_SOAK_RC_2026-05-04.md`

### V104. Wi-Fi Feasibility Gate — PASS

- 계획: `docs/plans/NATIVE_INIT_V104_WIFI_FEASIBILITY_PLAN_2026-05-04.md`
- 산출: `docs/reports/NATIVE_INIT_V104_WIFI_FEASIBILITY_2026-05-04.md`
- `stage3/linux_init/init_v104.c`
- `stage3/linux_init/v104/*.inc.c`
- `stage3/linux_init/a90_wififeas.c/h`
- 의도:
  - v103 read-only inventory를 기반으로 Wi-Fi bring-up 가능 여부를 deterministic gate로 판정
  - native default, mounted-system read-only 상태를 분리해 `baseline-required`/`no-go`/`go-read-only-only` 결정
  - Wi-Fi enablement, rfkill write, module load/unload, firmware/vendor mutation 금지
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v104.cpio`, `stage3/boot_linux_v104.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.9.4 (v104)`, `A90v104`, `0.9.4 v104 WIFI FEASIBILITY`, `wififeas [summary|full|gate|paths]` — PASS
  - native flash → post-boot `cmdv1 version/status` — PASS
  - `wififeas`, `wififeas gate`, `wififeas full`, `wififeas paths` — PASS
  - default native decision: `baseline-required` — PASS
  - `mountsystem ro` extended decision: `no-go` because Android-side candidates exist but WLAN/rfkill/module gates are missing — PASS
  - `diag`, `storage`, `runtime`, `service list`, `netservice status`, `statushud`, `autohud 2`, `screenmenu`, `hide`, `cpustress 3 2` — PASS
- 산출:
  - `stage3/linux_init/init_v104`
    - SHA256 `ac3220826e78782a7c4fa523b62d893bd3764d6df48b8d68e32065fe111cb802`
  - `stage3/ramdisk_v104.cpio`
    - SHA256 `0816ff76577702d28238e86ee32bdc9388646a5c5ca7ae685a544b937947029c`
  - `stage3/boot_linux_v104.img`
    - SHA256 `c1fe4f5fe6d569e8ff19ee73d2e6c3742948c605fa36c41c6beef9d1c86fe8eb`
  - `docs/reports/NATIVE_INIT_V104_WIFI_FEASIBILITY_2026-05-04.md`

### V103. Wi-Fi Read-Only Inventory — PASS

- 계획: `docs/plans/NATIVE_INIT_V103_WIFI_INVENTORY_PLAN_2026-05-04.md`
- 산출: `docs/reports/NATIVE_INIT_V103_WIFI_INVENTORY_2026-05-04.md`
- `stage3/linux_init/init_v103.c`
- `stage3/linux_init/v103/*.inc.c`
- `stage3/linux_init/a90_wifiinv.c/h`
- `scripts/revalidation/wifi_inventory_collect.py`
- 의도:
  - native init에서 보이는 WLAN, rfkill, firmware, module, vendor path를 read-only로 수집
  - Wi-Fi bring-up 전에 Android/TWRP/native init visibility 차이를 확인할 evidence format 준비
  - Wi-Fi enablement, rfkill write, module load/unload, firmware/vendor mutation 금지
- 검증:
  - static ARM64 init build with `-Wall -Wextra` — PASS
  - `stage3/ramdisk_v103.cpio`, `stage3/boot_linux_v103.img` 생성 — PASS
  - boot image marker strings `A90 Linux init 0.9.3 (v103)`, `A90v103`, `0.9.3 v103 WIFI INVENTORY`, `wifiinv [summary|full|paths]` — PASS
  - native flash → post-boot `cmdv1 version/status` — PASS
  - `wifiinv`, `wifiinv paths`, `wifiinv full` — PASS
  - default native inventory: no `wlan*`, no Wi-Fi rfkill, no WLAN/CNSS/QCA module match — PASS
  - `mountsystem ro` extended inventory: `/mnt/system/system/etc/init/wifi.rc`, `wificond.rc`, carrier Wi-Fi config candidates detected — PASS
  - `wifi_inventory_collect.py --native-only --boot-image stage3/boot_linux_v103.img` — PASS
  - `diag`, `storage`, `runtime`, `service list`, `netservice status`, `statushud`, `autohud 2`, `screenmenu`, `hide`, `cpustress 3 2` — PASS
- 산출:
  - `stage3/linux_init/init_v103`
    - SHA256 `9d1bac55549abb0e7aac2112896f66c362cc38dd1093212d4beb4bcb65c33a85`
  - `stage3/ramdisk_v103.cpio`
    - SHA256 `0758b63988b2edfb27cf2bc05da484dac099391bfc488f8a6c13aa976b7c61c4`
  - `stage3/boot_linux_v103.img`
    - SHA256 `dca3ee7ac77f366176d833b40450b0b1e3e55ebaf46ddc11c4d3a5f19454622b`
  - `docs/reports/NATIVE_INIT_V103_WIFI_INVENTORY_2026-05-04.md`

### V109. Post-v108 Structure Audit — DONE

- result: `docs/reports/NATIVE_INIT_V109_STRUCTURE_AUDIT_2026-05-04.md`
- build: `A90 Linux init 0.9.9 (v109)`
- artifacts: `stage3/linux_init/init_v109`, `stage3/ramdisk_v109.cpio`, `stage3/boot_linux_v109.img`
- validation: real-device flash PASS, cmdv1 version/status PASS, 3-cycle quick soak PASS
- next execution item: v110 app controller cleanup

### V110. App Controller Cleanup — DONE

- result: `docs/reports/NATIVE_INIT_V110_APP_CONTROLLER_CLEANUP_2026-05-04.md`
- build: `A90 Linux init 0.9.10 (v110)`
- artifacts: `stage3/linux_init/init_v110`, `stage3/ramdisk_v110.cpio`, `stage3/boot_linux_v110.img`
- validation: real-device flash PASS, controller busy gate PASS, 3-cycle quick soak PASS
- next execution item: v111 extended soak RC

### V111. Extended Soak RC — DONE

- result: `docs/reports/NATIVE_INIT_V111_EXTENDED_SOAK_RC_2026-05-04.md`
- build: `A90 Linux init 0.9.11 (v111)`
- artifacts: `stage3/linux_init/init_v111`, `stage3/ramdisk_v111.cpio`, `stage3/boot_linux_v111.img`
- validation: real-device flash PASS, 10-cycle extended soak PASS, final service/selftest PASS
- next execution item: v112 USB/NCM service soak

### V112. USB/NCM Service Soak — DONE

- result: `docs/reports/NATIVE_INIT_V112_USB_SERVICE_SOAK_2026-05-04.md`
- build: `A90 Linux init 0.9.12 (v112)`
- artifacts: `stage3/linux_init/init_v112`, `stage3/ramdisk_v112.cpio`, `stage3/boot_linux_v112.img`
- validation: real-device flash PASS, NCM ping PASS, `tcpctl_host.py ping/status/run` PASS, ACM rollback PASS, 3-cycle quick soak PASS
- next execution item: v113 runtime package layout

### V113. Runtime Package Layout — DONE

- result: `docs/reports/NATIVE_INIT_V113_RUNTIME_PACKAGE_LAYOUT_2026-05-04.md`
- build: `A90 Linux init 0.9.13 (v113)`
- artifacts: `stage3/linux_init/init_v113`, `stage3/ramdisk_v113.cpio`, `stage3/boot_linux_v113.img`
- validation: real-device flash PASS, runtime package paths PASS, helpers manifest path PASS, 3-cycle quick soak PASS
- next execution item: v114 helper deployment 2

### V114. Helper Deployment 2 — DONE

- result: `docs/reports/NATIVE_INIT_V114_HELPER_DEPLOY_2026-05-04.md`
- build: `A90 Linux init 0.9.14 (v114)`
- artifacts: `stage3/linux_init/init_v114`, `stage3/ramdisk_v114.cpio`, `stage3/boot_linux_v114.img`
- validation: real-device flash PASS, helpers manifest/plan PASS, helpers verify PASS, 3-cycle quick soak PASS
- next execution item: v115 remote shell hardening

### V115. Remote Shell Hardening — DONE

- result: `docs/reports/NATIVE_INIT_V115_RSHELL_HARDENING_2026-05-04.md`
- build: `A90 Linux init 0.9.15 (v115)`
- artifacts: `stage3/linux_init/init_v115`, `stage3/ramdisk_v115.cpio`, `stage3/boot_linux_v115.img`
- validation: real-device flash PASS, `rshell audit` PASS, invalid-token rejection PASS, NCM rshell smoke PASS, ACM rollback PASS, 3-cycle quick soak PASS
- next execution item: v116 diagnostics bundle 2

### V116. Diagnostics Bundle 2 — DONE

- result: `docs/reports/NATIVE_INIT_V116_DIAG_BUNDLE_2026-05-04.md`
- build: `A90 Linux init 0.9.16 (v116)`
- artifacts: `stage3/linux_init/init_v116`, `stage3/ramdisk_v116.cpio`, `stage3/boot_linux_v116.img`
- validation: real-device flash PASS, `diag full` PASS, `diag bundle` PASS, host `diag_collect.py` PASS, `rshell audit` PASS, 3-cycle quick soak PASS
- next execution item: v109-v116 completion audit

### V109-V116. Completion Audit — DONE

- result: `docs/reports/NATIVE_INIT_V109_V116_COMPLETION_AUDIT_2026-05-04.md`
- scope: v109 through v116 reports, commits, docs, artifacts, and validation evidence
- validation: latest docs point to v116, v109-v116 reports/commits present, real-device flash evidence recorded for every claimed boot image version
- next execution item: v121 PID1 guard


### V117. PID1 Slim Roadmap Baseline — DONE

- result: `docs/reports/NATIVE_INIT_V117_PID1_SLIM_ROADMAP_2026-05-05.md`
- build: `A90 Linux init 0.9.17 (v117)`
- roadmap: `docs/plans/NATIVE_INIT_V117_V122_ROADMAP_2026-05-05.md`
- artifacts: `stage3/linux_init/init_v117`, `stage3/ramdisk_v117.cpio`, `stage3/boot_linux_v117.img`
- validation: real-device flash PASS, selftest PASS, diag summary PASS, 3-cycle quick soak PASS
- next execution item: v118 shell metadata cleanup


### V118. Shell Metadata API — DONE

- result: `docs/reports/NATIVE_INIT_V118_SHELL_META_API_2026-05-05.md`
- build: `A90 Linux init 0.9.18 (v118)`
- artifacts: `stage3/linux_init/init_v118`, `stage3/ramdisk_v118.cpio`, `stage3/boot_linux_v118.img`
- validation: real-device flash PASS, `cmdmeta`/`cmdmeta verbose` PASS, unknown command framed result PASS, 3-cycle quick soak PASS
- next execution item: v119 menu routing cleanup


### V119. Menu Route API — DONE

- result: `docs/reports/NATIVE_INIT_V119_MENU_ROUTE_API_2026-05-05.md`
- build: `A90 Linux init 0.9.19 (v119)`
- artifacts: `stage3/linux_init/init_v119`, `stage3/ramdisk_v119.cpio`, `stage3/boot_linux_v119.img`
- validation: real-device flash PASS, menu/show/hide/display regression PASS, route helper static check PASS, 3-cycle quick soak PASS
- next execution item: v120 command group split


### V120. Command Group API — DONE

- result: `docs/reports/NATIVE_INIT_V120_COMMAND_GROUP_API_2026-05-05.md`
- build: `A90 Linux init 0.9.20 (v120)`
- artifacts: `stage3/linux_init/init_v120`, `stage3/ramdisk_v120.cpio`, `stage3/boot_linux_v120.img`
- validation: real-device flash PASS, `cmdgroups`/grouped `cmdmeta` PASS, representative command groups PASS, 3-cycle quick soak PASS
- next execution item: v121 PID1 guard


### V121. PID1 Guard — DONE

- result: `docs/reports/NATIVE_INIT_V121_PID1_GUARD_2026-05-05.md`
- build: `A90 Linux init 0.9.21 (v121)`
- artifacts: `stage3/linux_init/init_v121`, `stage3/ramdisk_v121.cpio`, `stage3/boot_linux_v121.img`
- validation: real-device flash PASS, `pid1guard` PASS, `status`/`bootstatus` summary PASS, 3-cycle quick soak PASS
- next execution item: v122 Wi-Fi inventory refresh


### V122. Wi-Fi Inventory Refresh — DONE

- result: `docs/reports/NATIVE_INIT_V122_WIFI_REFRESH_2026-05-05.md`
- build: `A90 Linux init 0.9.22 (v122)`
- artifacts: `stage3/linux_init/init_v122`, `stage3/ramdisk_v122.cpio`, `stage3/boot_linux_v122.img`
- validation: real-device flash PASS, `wifiinv refresh` PASS, `wififeas refresh` PASS, host native collector PASS, 3-cycle quick soak PASS
- conclusion: active Wi-Fi work remains blocked; kernel-facing WLAN/rfkill/module gates are still absent
- next execution item: post-v122 planning

### V117-V122. PID1 Slimdown and Wi-Fi Refresh Cycle — DONE

- roadmap: `docs/plans/NATIVE_INIT_V117_V122_ROADMAP_2026-05-05.md`
- baseline: `A90 Linux init 0.9.16 (v116)`
- completion audit: `docs/reports/NATIVE_INIT_V117_V122_COMPLETION_AUDIT_2026-05-05.md`
- planned sequence: v117 roadmap baseline, v118 shell metadata cleanup, v119 menu routing cleanup, v120 command group split, v121 PID1 guard, v122 Wi-Fi inventory refresh
- guardrails: no risky Wi-Fi bring-up, no partition writes, no automatic remote downloads, USB ACM serial remains rescue channel

### V109-V116. Post-v108 Stability and Runtime Cycle — DONE

- roadmap: `docs/plans/NATIVE_INIT_V109_V116_ROADMAP_2026-05-04.md`
- baseline: `A90 Linux init 0.9.8 (v108)`
- first execution item: v109 post-v108 structure audit — DONE
- next execution item: v117 planning
- completed through: v109-v116 completion audit
- guardrails: no risky Wi-Fi bring-up, no partition writes, USB ACM serial remains rescue channel
