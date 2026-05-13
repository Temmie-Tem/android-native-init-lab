# Native Init Task Queue (2026-04-25)

이 문서는 `A90 Linux init 0.9.59 (v159)` verified 이후 바로 실행할 작업 큐다.
큰 방향은 “보이는 부팅 → 복구 가능한 로그 → 단독 조작 → 작은 userland → USB networking” 순서다.

## 버전 표기 규칙

- numeric `MAJOR.MINOR.PATCH`는 native init / boot image의 canonical version이다.
  - 예: `A90 Linux init 0.9.59`, `0.9.59`
  - PID 1, ramdisk helper, boot image, device-visible native behavior가 바뀌고 실기기에 flash할 때만 증가시킨다.
- `v###`는 project execution cycle이다.
  - host tooling, security batch, 계획/보고서, long-soak/mixed-soak gate, documentation-only milestone에도 사용할 수 있다.
  - `v###`가 항상 boot image 또는 device flash를 의미하지 않는다.
- 모든 계획/보고서는 `Native build`, `Cycle label`, `Device flash`, `Host commit`을 분리해 적는다.
- 현재 기준 예:
  - Native build: `A90 Linux init 0.9.59`
  - Device build tag: `v159`
  - Cycle label: `v185` host protocol/broker design
  - Device flash: none
- 상세 규칙: `docs/operations/VERSIONING_POLICY.md`

## 현재 고정 기준점

- latest verified build: `A90 Linux init 0.9.59 (v159)`
- official version: `0.9.59`
- build tag: `v159`
- creator: `made by temmie0214`
- latest verified source: `stage3/linux_init/init_v159.c` + `stage3/linux_init/v159/*.inc.c` + `stage3/linux_init/helpers/a90_cpustress.c` + `stage3/linux_init/helpers/a90_rshell.c` + `stage3/linux_init/helpers/a90_longsoak.c` + `stage3/linux_init/a90_config.h` + `stage3/linux_init/a90_util.c/h` + `stage3/linux_init/a90_log.c/h` + `stage3/linux_init/a90_timeline.c/h` + `stage3/linux_init/a90_console.c/h` + `stage3/linux_init/a90_cmdproto.c/h` + `stage3/linux_init/a90_run.c/h` + `stage3/linux_init/a90_service.c/h` + `stage3/linux_init/a90_kms.c/h` + `stage3/linux_init/a90_draw.c/h` + `stage3/linux_init/a90_input.c/h` + `stage3/linux_init/a90_input_cmd.c/h` + `stage3/linux_init/a90_kernelinv.c/h` + `stage3/linux_init/a90_sensormap.c/h` + `stage3/linux_init/a90_pstore.c/h` + `stage3/linux_init/a90_watchdoginv.c/h` + `stage3/linux_init/a90_tracefs.c/h` + `stage3/linux_init/a90_hud.c/h` + `stage3/linux_init/a90_menu.c/h` + `stage3/linux_init/a90_metrics.c/h` + `stage3/linux_init/a90_shell.c/h` + `stage3/linux_init/a90_controller.c/h` + `stage3/linux_init/a90_storage.c/h` + `stage3/linux_init/a90_selftest.c/h` + `stage3/linux_init/a90_usb_gadget.c/h` + `stage3/linux_init/a90_netservice.c/h` + `stage3/linux_init/a90_pid1_guard.c/h` + `stage3/linux_init/a90_runtime.c/h` + `stage3/linux_init/a90_helper.c/h` + `stage3/linux_init/a90_userland.c/h` + `stage3/linux_init/a90_diag.c/h` + `stage3/linux_init/a90_exposure.c/h` + `stage3/linux_init/a90_wifiinv.c/h` + `stage3/linux_init/a90_wififeas.c/h` + `stage3/linux_init/a90_changelog.c/h` + `stage3/linux_init/a90_longsoak.c/h` + `stage3/linux_init/a90_app_about.c/h` + `stage3/linux_init/a90_app_cpustress.c/h` + `stage3/linux_init/a90_app_displaytest.c/h` + `stage3/linux_init/a90_app_inputmon.c/h` + `stage3/linux_init/a90_app_log.c/h` + `stage3/linux_init/a90_app_network.c/h`
- latest verified boot image: `stage3/boot_linux_v159.img`
- previous verified source-layout baseline: `stage3/linux_init/init_v80.c` + `stage3/linux_init/v80/*.inc.c`
- known-good fallback: `stage3/boot_linux_v48.img`
- local artifact retention: `v159` latest, `v158` rollback, `v48` known-good만 보존하고 나머지 ignored stage3 산출물은 정리 가능
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

### V211. Firmware Path / Vendor Layout Policy — PLAN

- 계획: `docs/plans/NATIVE_INIT_V211_FIRMWARE_PATH_POLICY_PLAN_2026-05-13.md`
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
- 다음 실행 항목:
  - v211 policy probe 구현
  - active Wi-Fi bring-up은 계속 blocked

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
