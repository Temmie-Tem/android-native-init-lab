# Native Init V2191 Kernel Control/Observe Limit Map (2026-06-11)

## Result

- decision: `v2191-kernel-capability-limit-classified`
- pass: `true`
- type: 디바이스 read-only capability census (native-init 경유). 플래시·파티션
  쓰기·재부팅·Wi-Fi 트리거 없음.
- 목표: 이 디바이스에서 **제어/관측 가능 경계(RKP 절단선)** 를 경험적으로 확정.
- 채널: native-init `0.9.261 (v2189-security-p0-stage-fix)` 시리얼 브리지 + a90ctl.
  복잡 read는 `run /bin/busybox sh -c '...'`. census 중 tracefs/debugfs를
  마운트(가역, pseudo-fs).

## 디바이스/커널 동일성 (stock 확정)

- `/proc/version`: `Linux version 4.14.190-25818860-abA908NKSU5EWA3 (dpi@SWDK6110)
  (clang version 10.0.7 for Android NDK ...) #2 SMP PREEMPT Thu Jan 12 2023`
- → **순수 Samsung production stock 커널**. V775 지문(stock=clang 10.0.7,
  custom-build=10.0.6)과 정확히 일치. 자체 빌드 커널 아님.
- 부팅 상태: `verifiedbootstate=orange`(부트로더 언락), `warranty_bit=1`(Knox 트립).
  (serialno/ap_serial 등 식별자는 본 문서에서 redaction)
- 로드된 커널 모듈: `/proc/modules` = 0개.

## 런타임 게이트 (read-only)

| 게이트 | 값 | 함의 |
| --- | --- | --- |
| `selinux/enforce` | **0 (permissive)** | native-init 컨텍스트는 SELinux 정책 구속 없음 |
| `/sys/kernel/security/lockdown` | **부재** | kernel lockdown LSM 없음 |
| `kernel/dmesg_restrict` | **0** | 커널 로그 read 가능 |
| `kernel/modules_disabled` | 0 | 모듈 로딩 행정 차단은 아님(서명이 벽, 아래) |
| `kernel/kptr_restrict` | **4** | kallsyms 주소 전부 `0` (심볼→주소 차단) |
| `kernel/perf_event_paranoid` | **3** | perf 커널 샘플링 제한(+ PERF_EVENTS_RESTRICT) |

→ 하드닝이 **런타임 LSM이 아니라 커널 BUILD config + RKP**에 박혀 있다. SELinux가
permissive여도 천장이 안 올라간다.

## 커널 config 사실 (`/proc/config.gz`)

OPEN(관측 가능):
- `CONFIG_BPF=y`, `CONFIG_BPF_SYSCALL=y`, `CONFIG_BPF_EVENTS=y`, `CONFIG_CGROUP_BPF=y`
  (단 `CONFIG_BPF_JIT` is not set → 인터프리터)
- `CONFIG_PERF_EVENTS=y`, `CONFIG_HAVE_PERF_EVENTS=y`
- `CONFIG_UPROBES=y`, `CONFIG_UPROBE_EVENTS=y`
- `CONFIG_FTRACE=y`, `CONFIG_KALLSYMS=y`, `CONFIG_KALLSYMS_ALL=y` (주소는 kptr=4로 가림)

CLOSED(빌드타임 차단):
- `# CONFIG_KPROBES is not set` → 임의 커널 함수 트레이싱 불가
- `# CONFIG_PROC_KCORE is not set`, `# CONFIG_DEVMEM is not set` → raw 커널 메모리 read 인터페이스 부재
- `# CONFIG_FUNCTION_TRACER is not set`, `# CONFIG_FTRACE_SYSCALLS is not set`
- `CONFIG_HIST_TRIGGERS` 부재 → ftrace 비-eBPF in-kernel 집계 없음
- `CONFIG_MODULES=y` + `CONFIG_MODULE_SIG=y` + **`CONFIG_MODULE_SIG_FORCE=y`**
  (`MODULE_SIG_HASH="sha512"`, `MODULE_SIG_KEY="certs/signing_key.pem"`) → 미서명 모듈 거부
- `CONFIG_STRICT_KERNEL_RWX=y`, `CONFIG_STRICT_MODULE_RWX=y`, `CONFIG_RANDOMIZE_BASE=y`
- `CONFIG_SECURITY_PERF_EVENTS_RESTRICT=y`, `CONFIG_SECURITY_DEFEX=y`, `CONFIG_SECURITY_DSMS=y`

## 트레이싱/관측 표면

- filesystems 컴파일: pstore/tracefs/debugfs/cgroup/cgroup2/bpf 전부 `yes`.
  census 전 마운트 상태는 configfs만; tracefs(`/sys/kernel/tracing`)·
  debugfs(`/sys/kernel/debug`)는 본 census에서 마운트.
- `available_events` = **1456**. `available_tracers` = `nop`.
- **`raw_syscalls:` 존재** (FTRACE_SYSCALLS=n인데도) → eBPF로 전 syscall 관측 가능.
- 포인터 운반 tracepoint 패밀리 존재: `sched sock skb net cfg80211 clk regulator
  power signal workqueue` (+ 그 외).
- **a90 uprobe 이벤트 206개** (a90cnss=114, a90pmsrv=46, a90periph=25, a90libqmi=21):
  프로젝트가 유저스페이스 데몬(QMI/PM/CNSS)에 건 **uprobe 기반** 동적 이벤트.
  커널 정적 tracepoint 아님 — tracefs unmount/remount해도 커널 메모리에 지속.
- debugfs 노드(일부): `cld`, `cnss-prealloc`, `cnss_utils`, `WMI_SOC0_PDEV0`,
  `diag`, `clk`, `cmd_db`, `regulator`, `gpio`, `ufshc`, `dwc3`, `camera*`, `dri`,
  `f2fs`, `binder`, `bluetooth` … (WLAN/modem/clock/regulator 내부 read-only).

## eBPF 작동 증명 (기존 V781 재확인)

[V781](NATIVE_INIT_V781_BPF_IDLE_ATTACH_2026-05-25.md): `BPF_PROG_TYPE_TRACEPOINT`
프로그램 로드(prog_fd=3) + `perf_event_open`으로 `msm_pil_event:pil_notif`(id 595)
attach → `attach-detach-pass`. 로드는 `--verbose`(BPF log level)일 때 성공, 없으면
`errno=22`. → **bpf()가 이 디바이스에서 도달·작동**. SELinux permissive와 정합.

## 한계점 맵 (절단선)

관측 OPEN: uprobes(현역 206) · 정적 tracepoint 1456 · raw_syscalls · eBPF
(BPF_SYSCALL/EVENTS/CGROUP_BPF, JIT off) · debugfs(WLAN/modem/clk/regulator) ·
dmesg · procfs/sysfs/configfs.

관측 CLOSED: kprobes(임의 함수) · /proc/kcore·/dev/mem(raw 메모리) ·
kallsyms 주소(kptr=4+KASLR) · syscall tracepoint(개별) · function tracer ·
perf 커널 샘플링.

제어 OPEN: sysctl/sysfs/cgroup(7) write · pseudo-fs mount · tracefs 이벤트 제어 ·
**cgroup-BPF**(네트워크/소켓 정책).

제어 CLOSED: 커널 모듈 로딩(MODULE_SIG_FORCE) · 라이브 커널 패치(RKP+STRICT_RWX) ·
커스텀 커널(RKP/transform, V775) · DEFEX/DSMS.

**벽은 "커널 임의 코드 + 임의 쓰기"에 정확히 있다.** 그 아래 sanctioned
instrumentation 밴드는 넓게 열려 있고, RKP는 *쓰기*를 막지 *읽기*를 안 막는다.

## 합성(체인)으로 닫힌 것 우회 — 관측

마스터 체인:
```
tracepoint/uprobe/raw_syscalls 에 eBPF attach (V781로 작동 확인)
  → 이벤트 컨텍스트의 유효 포인터를 앵커로 (심볼 불필요)
  → bpf_probe_read 로 reachable 커널 구조체 walk (OSRC 소스 오프셋)
  → BPF map → 유저스페이스
```
회복되는 것:
- kcore/devmem 부재 → `bpf_probe_read`가 in-kernel read 프리미티브. RKP는 read
  비차단. **reachable 메모리 read 가능**.
- kallsyms 0 → 심볼 대신 컨텍스트 포인터(sched→task_struct, sock/skb→net,
  cfg80211→wlan)를 앵커. 주소 leak 불필요.
- syscall tracepoint off → **raw_syscalls + eBPF로 전 syscall 회복**.
- kprobes 없음 → 진짜 손실(임의 함수 X). 정적 tracepoint+uprobe+raw_syscalls+
  유저스페이스 임의 uprobe 앵커로 보완.

## 합성 — 제어

- **sanctioned 반응 루프**: tracepoint/uprobe(관측) → PID1 로직 → sysfs/debugfs/
  sysctl write(반응). RKP-safe. (clk/regulator/power write는 hang 위험 → 가역·소단위)
- **cgroup-BPF**: 네트워크/소켓 정책을 커널 안에서 필터/리다이렉트/sockopt 강제.

어떤 체인도 못 뚫는 벽: 커널 코드/메모리 *쓰기*(RKP EL2 + verifier + STRICT_RWX) ·
모듈 서명 · 커스텀 커널.

## 탐사 전략 (합의)

서브시스템마다 일회성 프로브 금지. **엔진-first + 우선순위 sweep + catalog**:

- **A. Breadth 카탈로그**(read-only, **완료 → 부록 A**): tracepoint/debugfs/
  uprobe/sysfs 전수.
- **B. Generic 추출 엔진**(빌드 1회): V781/`a90_bpf_trace_counter.c` 기반 →
  `(tracepoint/uprobe, read-spec[ptr+offset+size], map)` 파라메트릭 helper.
  "임의 서브시스템 탐사"를 코드가 아니라 config로. 검증 = `sched:sched_switch`.
- **C. Depth, value×safety 순**: ① safe&high-info(sched, raw_syscalls) →
  ② 미션(cfg80211/cld/cnss, regulator/clk/power) → ③ 나머지.
- **D. Control, 마지막·bounded**: 반응 루프 + cgroup-BPF + debugfs/sysfs write(가역).

## 부록 A — Breadth 카탈로그 (전수, V2191 census)

전수 결과: tracepoint 그룹 **1456 이벤트 / ~110 그룹**, debugfs 최상위 **115 노드**,
`/proc/sys` 10 디렉터리 / **writable knob 2089개**. 도메인별 관측·제어 앵커:

| 도메인 | tracepoint 그룹(이벤트수) | debugfs 노드 / sysctl |
| --- | --- | --- |
| **WLAN** | `cfg80211`(162), `a90cnss`(114, uprobe) | `cld cnss-prealloc cnss_utils icnss ieee80211 wlan wlan0 wifi-aware0 p2p0` / sysctl `ath_pktlog` |
| **Modem 데이터패스** | `rmnet`(16) `dfc`(11) `ipa`(9) `xdp`(5) `wda`(3) `rndis_ipa`(3) | `ipa ipa_usb mhi mhi_netdev qrtr gsi pci-msm uether_rndis usb_diag` |
| **Power/Clock/Thermal** | `power`(32) `clk`(17) `thermal`(12) `msm_low_power`(10) `msm_bus`(10) `regulator`(7) `rpmh`(4) `rpm`(4) `lmh`(1) | `clk regulator opp pm_genpd pm_qos lmh_monitor lpm_stats cmd_db sleep_time suspend_stats max77705-regs charger-pca9468` |
| **Scheduler/MM** | `sched`(62) `kmem`(35) `writeback`(30) `vmscan`(16) `compaction`(14) `oom`(8) `migrate`(3) `process_reclaim`(2) `almk`(2) `lowmemorykiller`(1) | `sched_debug sched_features memblock extfrag show_mem_notifier` |
| **Storage/FS** | `ext4`(102) `f2fs`(70) `jbd2`(16) `block`(18) `ufs`(13) `mmc`(16) `scsi`(5) `android_fs`(6) `filelock`(10) `filemap`(4) | `f2fs mmc0 1d84000.ufshc block bdi` |
| **GPU/Display/Camera/Audio** | `kgsl`(79) `msm_vidc_events`(16) `sde_rotator`(12) `camera`(13) `asoc`(13) `sde`(10) `v4l2`(6) `vb2`(4) `drm`(3) `mdss_pll`(3) | `kgsl npu sde_rotator0 sde_rsc0 dri drm_dp display_driver ss_dsi_panel_* camera_* msm_vidc afe_loopback asoc msm_apr_debug` |
| **USB** | `xhci-hcd`(38) `gadget`(24) `dwc3`(15) | `a600000.dwc3 usb usb_gsi usb_diag uether_rndis ipa_usb 88e2000.hsphy` |
| **Core/IPC/Bus** | `binder`(31) `random`(15) `timer`(13) `regmap`(15) `iommu`(12) `bpf`(12) `irq`(9) `cgroup`(9) `spi`(7) `i2c`(4) `spmi`(5) `workqueue`(4) `ipi`(3) `rcu`(1) `printk`(1) | `binder ipc_logging tracing gpi_dma sps iommu ion dma_buf regmap pinctrl gpio gpiomux pwm` |
| **Net 스택** | `net`(11) `skb`(4) `sock`(2) `fib`(3) `bridge`(4) `udp`(1) `napi`(1) `qdisc`(1) `fib6`(1) `mdio`(1) | sysctl `net` (서브트리) |
| **Security/TEE/PIL** | `msm_pil_event`(3) `sec_debug`(4) `scm`(4) `ras`(4) | `tzdbg trustonic_tee diag ras hyp 관련` |
| **syscall/proc** | `raw_syscalls`(2) `task`(2) `signal`(2) `pagefault`(6) `pagemap`(2) `namei`(1) `emulation`(1) | — |
| **기타 uprobe(현역)** | `a90pmsrv`(46) `a90periph`(25) `a90libqmi`(21) | — |

`/proc/sys` 최상위: `abi ath_pktlog crypto debug dev fs kernel net user vm`
(제어 노브 2089개 writable). `available_tracers=nop`(function/graph tracer 부재).

미션 직결: **WLAN(cfg80211 162 + icnss/cld/wlan debugfs)** 과 **modem
데이터패스(ipa/mhi/qrtr/rmnet)**, **power/clk(regulator/cmd_db/rpmh)** 가 가장
두꺼운 관측면 — 과거 추적 타깃과 정확히 겹친다. 제어 노브(ath_pktlog 등)도 동거.

## Safety

- device 명령: read-only 열람 + pseudo-fs mount(tracefs/debugfs, 가역)만.
- partition write/flash/reboot: 없음. Wi-Fi scan/connect/DHCP/route/ping: 없음.
- credential 사용: 없음. 식별자(serialno/MAC/IP): 본 문서 redaction.
- BPF attach: 본 census에서 신규 attach 안 함(V781 기존 증거 참조).

## Next

- V2192: generic 추출 엔진 설계/빌드(Phase B), `sched`로 검증 후 미션 서브시스템.
  → **완료**: [V2192 Parametric eBPF Trace Extractor](NATIVE_INIT_V2192_BPF_TRACE_EXTRACT_2026-06-11.md)
  (Tier-1/Tier-2 read × sample/freq/stream 온디바이스 검증, 체인 확장 분석).
- census 후 마운트한 tracefs/debugfs는 후속 관측에 유지(원하면 umount).

## 참조

- [V775 boot-incompat postmortem](NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_2026-05-25.md) — stock 커널 지문, 커스텀 커널 RKP/transform 벽.
- [V781 BPF idle attach](NATIVE_INIT_V781_BPF_IDLE_ATTACH_2026-05-25.md) — eBPF tracepoint attach 작동 증명.
- 외부: Samsung Knox RKP(read 비차단, write/page-table secure-world), Project Zero
  "Lifting the HyperVisor", kasld(주소 발견 기법), android_bpftrace(arm64 eBPF 실증).
