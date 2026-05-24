# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Samsung Galaxy A90 5G (SM-A908N) — stock Android Linux kernel 4.14.190, custom static `/init` as PID 1, building a minimal embedded Linux console without Android userspace. Device flashed via TWRP, controlled over USB CDC ACM serial bridge.

- **Device**: SM-A908N, Android 12, Magisk 30.7, TWRP available
- **Current native build**: `A90 Linux init 0.9.68 (v724)` — `stage3/boot_linux_v724.img`
- **Known-good fallback**: `stage3/boot_linux_v48.img`
- **Active research cycle**: v748+ (non-bind ICNSS/QCA power-up trigger classification pending)
- **Versioning policy**: `docs/operations/VERSIONING_POLICY.md` — `vNNN` cycle ≠ device flash

## Versioning rules

Two independent axes:

| Axis | Format | Increments when |
|---|---|---|
| Native build | `MAJOR.MINOR.PATCH` (e.g. `0.9.60`) | boot image changes on device |
| Project cycle | `vNNN` (e.g. `v741`) | any plan/report/tooling milestone |

A new `vNNN` cycle does **not** imply a new device flash. Always state both in plans/reports.

## Build: native init binary

All native binaries must be **static aarch64**. Never use host gcc.

```bash
# Build init (run from stage3/linux_init/)
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra \
  -o init_vNNN init_vNNN.c a90_util.c a90_log.c ... a90_reaper.c

# Verify static
file init_vNNN
aarch64-linux-gnu-readelf -d init_vNNN | grep "no dynamic section"

# Build a helper (each has its own script)
scripts/revalidation/build_android_execns_probe_helper.sh [out-path]
scripts/revalidation/build_qrtr_ns_probe_helper.sh [out-path]
```

Build scripts all follow the same pattern: compile → strip → `file` check → `readelf -d` confirms no INTERP/dynamic section → print SHA256.

## Flash: device boot image

**Never use manual `adb shell dd`.** Use only:

```bash
# Flash from native init (bridge must be up, device running native init)
python3 scripts/revalidation/native_init_flash.py \
  stage3/boot_linux_vNNN.img --from-native

# Flash from TWRP
python3 scripts/revalidation/native_init_flash.py \
  stage3/boot_linux_vNNN.img --from-twrp
```

Boot image packaging uses `mkbootimg/` tools. See `NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md`.

## Bridge and device control

```bash
# Start serial bridge (must be running for all device operations)
python3 scripts/revalidation/serial_tcp_bridge.py --port 54321

# Send a single command
python3 scripts/revalidation/a90ctl.py version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py 'selftest verbose'
python3 scripts/revalidation/a90ctl.py --json version   # JSON output

# Adb shell quoting: multi-word commands require single quotes
adb shell 'su -c "cat /proc/mounts"'
```

Bridge listens at `127.0.0.1:54321`. `a90ctl.py` speaks cmdv1/A90P1 framed protocol.

**Key bridge behaviours:**
- `[busy]` response = on-screen menu is active → send `hide` first
- AT noise lines (`AT`, `ATE0`, `AT+...`) are silently ignored by native init (v59+)
- `netservice` is OFF by default; NCM/tcpctl auto-start only when `/cache/native-init-netservice` flag exists

## Host tooling architecture

```
scripts/revalidation/
├── a90ctl.py               # cmdv1 protocol client — primary device RPC
├── a90_kernel_tools.py     # shared evidence capture helpers (CommandCapture, repo_path, etc.)
├── native_init_flash.py    # authoritative flash tool
├── serial_tcp_bridge.py    # USB ACM ↔ TCP bridge
├── helper_deploy.py        # deploy static helper binaries to /cache/bin/
├── a90harness/
│   ├── evidence.py         # private file I/O (no-follow, 0600/0700 permissions)
│   ├── device.py           # DeviceClient abstraction
│   ├── runner.py           # test runner
│   └── ...
└── wifi_*/                 # Wi-Fi research experiment runners
    build_*/                # helper build scripts (one per helper)
```

Every experiment runner follows this pattern:
1. `plan` subcommand — validate manifests, no device calls
2. `preflight` subcommand — read-only live checks
3. `run`/`probe` subcommand — opt-in action, gated by explicit approval flags
4. Evidence written via `EvidenceStore` / `a90harness.evidence` helpers to `tmp/wifi/vNNN-*/`

All evidence output uses `write_private_*` helpers (no-follow, mode 0600). Never write evidence with plain `open()`.

## Native init source architecture

```
stage3/linux_init/
├── init_vNNN.c             # PID 1 entry + boot sequence, includes *.inc.c
├── vNNN/*.inc.c            # command dispatch shards (included by init_vNNN.c)
├── a90_config.h            # compile-time constants
├── a90_util.c/h            # base utilities
├── a90_log.c/h             # file logging (/mnt/sdext/a90/logs/ → /cache/ → /tmp/)
├── a90_shell.c/h           # serial shell loop + cmdv1 protocol
├── a90_kms.c/h             # DRM/KMS framebuffer
├── a90_hud.c/h             # status HUD renderer
├── a90_menu.c/h            # on-screen button menu
├── a90_reaper.c/h          # PID1 generic orphan/zombie reaper (v261+)
├── a90_netservice.c/h      # USB NCM + tcpctl lifecycle
├── a90_exposure.c/h        # network exposure guardrail
├── a90_wifiinv.c/h         # Wi-Fi read-only inventory
└── helpers/
    ├── a90_android_execns_probe.c  # private mount namespace + linker probe
    ├── a90_qrtr_ns_probe.c         # QRTR nameservice lookup helper
    └── ...
```

**Dependency direction**: `util/log/timeline` → `console/shell/run` → `hud/menu/input` → `netservice`. Upper layers never import lower layers.

**Module boundary**: each `a90_*.c/h` pair owns one domain. `init_vNNN.c` calls modules; modules do not call each other across domains.

## Safety invariants — never violate

- **No writes** to `/efs`, `/sec_efs`, modem, RPMB, keymaster, vbmeta, bootloader partitions
- **No generic ICNSS unbind/bind** — v214 incident caused ICNSS bind FAIL requiring reboot
- **Only accepted recovery**: reboot (v223 policy)
- **No persistent writes** to `/system`, `/vendor`, `/data`, `/apex` from experiment runners
- **No global bind mounts** — use `unshare(CLONE_NEWNS)` + private propagation in helpers
- **No Wi-Fi scan/connect/link-up/DHCP/routing** without separate explicit approval
- `cnss-daemon` live start requires `--allow-daemon-start --assume-yes`
- QRTR NS transmit requires `--allow-qrtr-ns-transmit --assume-yes`
- `firmware_class.path` rollback value: `/vendor/firmware_mnt/image` — restore after any experiment

## Experiment runner conventions

New `vNNN` experiment scripts must:
- Accept `plan`, `preflight`, `run` (or `probe`) subcommands
- Validate prerequisite manifests before any live action
- Write `manifest.json` with `decision=<label>` and `pass=True/False`
- Use `EvidenceStore` for all output under `tmp/wifi/vNNN-*/`
- Gate live action behind explicit `--allow-*` + `--assume-yes` flags
- Run `version`, `status`, `bootstatus`, `selftest verbose` as postflight regression

## Wi-Fi bring-up research state (v598–v773, active)

Goal: bring up `wlan0` from native init without Android userspace.

### Confirmed architecture (SM8250/QCA6390)

- **Driver**: ICNSS core (`drivers/soc/qcom/icnss.c`, `drivers/soc/qcom/icnss_qmi.c`) plus QCACLD SNOC/PLD path — not the live `cnss2` PCIe/MHI path
- **ICNSS bootstrap**: ICNSS platform probe → QCACLD `pld_snoc_register_driver()` / `icnss_register_driver()` → WLFW service 69 on QRTR triggers `wlfw_new_server()` / `icnss_call_driver_probe()` → HDD probe/startup → BDF/FW-ready → `wlan0`
- **WLAN-PD** (`msm/modem/wlan_pd`, instance 180) runs ON modem MPSS DSP — modem must be ONLINE for `wlanmdsp.mbn` to load and WLFW to appear
- **service-notifier 180/74** are side evidence, not direct ICNSS driver-probe triggers
- **wlan module**: static (`/sys/module/wlan` exists, not in `/proc/modules`)

### Companion stack (required, confirmed working)

Must run before cnss-daemon: `qrtr-ns → pd-mapper → rmt_storage → tftp_server`
Then: `cnss_diag → cnss-daemon`
Current CNSS-only ordering is confirmed with helper v122. Helper v123 added a
service `180` gated `mdm_helper` mode, but V745 live showed that marker is not
stable enough in every boot. Helper v124 added a `sysmon-qmi` gated
`mdm_helper` mode. V746 proved `mdm_helper` starts safely after `sysmon-qmi`,
but it does not advance mdm3/WLAN-PD/WLFW.

### Current blocker (V773)

```
mss: OFFLINING → ONLINE ✓  (read-only firmware mounts + subsys_modem holder)
QRTR RX/TX: present ✓
sysmon-qmi: present ✓
service-notifier 180: can open on current boot, but remains a side signal
mdm_helper after service180: starts safely but no lower progress
esoc0 surface: `/sys/bus/esoc/devices/esoc0` and `/sys/class/subsys/subsys_esoc0` visible with SDX50M/PCIe metadata, but `/dev/subsys_esoc0` absent and no esoc0 open/hold executed
QCA6390 platform device: exists but driver link missing
mdm3: stays OFFLINING
ICNSS-QMI/WLFW/service69/BDF/wlan0: absent
lower-window boot_wlan: write executes, but qcwlanstate stays OFF and no /dev/wlan/wiphy/wlan0
QCACLD/HDD init: boot_wlan reaches "wlan: Loading driver" and qcwlanstate char-device creation, but never reaches "wlan: driver loaded", ICNSS-QMI, FW-ready, BDF, wiphy, or wlan0
CNSS-before-boot_wlan ordering: cnss_diag and cnss-daemon start safely before boot_wlan, but the same HDD/qcwlanstate stall remains
HDD/PLD visibility: no explicit hdd_init/PLD/register-driver failure marker; need bounded instrumentation to distinguish pld_init vs hdd_init vs wlan_hdd_register_driver stall
Traceability: tracefs/debugfs support exists and target symbols are partially visible in kallsyms, but tracefs is not mounted and ftrace filter readiness is unproven
Ftrace result: tracefs mount/cleanup works, but function filter controls/target functions are unavailable; ftrace is not a usable HDD/PLD instrumentation route
Non-ftrace live observers: dynamic debug is not compiled in and has no control catalog; kprobes/kprobe_events are not configured; printk/dmesg exists but does not resolve the PLD/HDD/register-driver boundary
Android/native differential: Android proves QMI/BDF/FW-ready/wlan0, native proves HDD/qcwlanstate entry with success-marker absence, but existing dmesg lacks the pre-QMI PLD/HDD/register-driver boundary
Instrumentation feasibility: boot-image tooling and rollback artifacts are present, but exact local kernel/QCACLD/ICNSS source was initially absent; do not patch or flash instrumentation until source is acquired and verified
Source acquisition: exact Samsung OSRC source package is identified as SM-A908N_KOR_12_Opensource.zip for SM-A908N/A908NKSU5EWA3, source upload id 13272, and has now been staged locally
Source staging: kernel_build/ is prepared as ignored local staging; V760 verifier now reports live ICNSS/QCACLD target files present
Source handoff: V761 generated a private operator handoff script for manual OSRC download/staging and V760 rerun; browser open is opt-in via V761_OPEN_BROWSER=1, and kernel instrumentation remains blocked until V760 verifies target files
Source target verification: operator staged OSRC source; V760 now verifies live ICNSS/QCACLD target groups in Kernel.tar.gz (`qcacld_hdd_main`, `qcacld_hdd_driver_ops`, `qcacld_pld_snoc`, `icnss_core`, `icnss_qmi`). Source acquisition blocker is cleared for planning only; no patch/build/flash/live handoff yet.
Architecture correction: SM-A908N live evidence shows `18800000.qcom,icnss` bound and `/sys/bus/platform/drivers/cnss2` absent. V763 planning must target ICNSS/QMI/WLFW service-69 and PLD-SNOC callbacks, not CNSS2/MHI.
V764 service180 retry: helper v124 started `mdm_helper` under service180 gate, but mdm3/WLAN-PD/MHI/QCA6390/WLFW/BDF/wlan0 did not advance. This closes `mdm_helper` as the immediate lower trigger unless new evidence changes the service180/esoc model.
V765 source patch: generated review-only `A90V765` ICNSS/QCACLD log patch with 19 insertions across ICNSS QMI/core, PLD-SNOC, and QCACLD HDD loader/register/startup paths; no source mutation, build, boot image write, or device command executed.
V766 apply/build-readiness: fixed V765 patch formatting, applied the generated patch cleanly to a disposable extracted OSRC tree, verified 19 `A90V765` markers, and passed `r3q_kor_single_defconfig`; full kernel build is still gated on compatible Android/Samsung toolchain selection, with no boot image write or device command executed.
V767 full-build gate: staged ignored Android/Samsung toolchains and disposable host-build repairs, then compiled all five ICNSS/QCACLD instrumented target objects with all 19 `A90V765` markers preserved. Final `Image` packaging was blocked by Samsung post-link `RKP_CFP` Python2-only `instrument.py`, not by the Wi-Fi log patch. Runtime root cause remains a separate mdm_helper/esoc/mdm3/WLFW service-69 branch.
V768 mdm3/esoc classifier: host-only reconciliation closes repeat service180-gated `mdm_helper`, raw esoc0 open/hold, subsystem writes/bind/unbind, and blind `boot_wlan` retry as next steps under current evidence. The selected next gate is V769 RKP_CFP/Python2 packaging so the already-compiled ICNSS/QCACLD instrumentation can become a diagnostic image candidate.
V769 RKP_CFP packaging: bounded host repair passed. Disposable `scripts/rkp_cfp` Python3 compatibility repair now produces `Image` and `Image-dtb`, with all five ICNSS/QCACLD objects and all 19 `A90V765` markers preserved. No boot image write, flash, device command, service-manager/Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or external ping was executed.
V770 diagnostic boot staging: local-only repack passed. V769 `Image-dtb` was packaged with current v724 native-init ramdisk/header metadata into private tmp evidence; staged image is 4096-byte aligned, mode `0600`, contains the native-init marker and all 19 `A90V765` markers, and unpacks to a kernel hash matching V769 `Image-dtb`. No device command, partition write, flash, reboot, service-manager/Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or external ping was executed. Next gate is V771 diagnostic live handoff/flash/capture under rollback rules.
V771 diagnostic live handoff: TWRP flash/readback succeeded for the V770 image, but the phone did not return to native init after reboot and instead enumerated as Samsung Download mode (`04e8:685d`) with no ADB device. Treat this as `v771-instrumented-kernel-boot-failed-download-mode`. Do not retry the same V770 image as-is. Rollback is complete: TWRP flashed `stage3/boot_linux_v724.img`, native `version/status`, `bootstatus`, and `selftest` pass again. Next run a host-only boot incompatibility classifier before any further custom-kernel flash.
V772 boot incompatibility classifier: host-only classification points to missing appended DTB/FDT payloads. Known-good v724 kernel payload has three FDT blobs at offsets `48830500`, `49327831`, `49827440`; V770 diagnostic payload has zero FDT magic hits. Embedded config hashes match and the diagnostic payload preserves all 19 `A90V765` markers. Do not retry V770 as-is. Next gate is V773 local-only stock-DTB-tail append and repack verification.
V773 stock DTB tail repack: local-only PASS. The V769 instrumented payload plus stock v724 appended DTB tail repacks into `tmp/wifi/v773-stock-dtb-tail-repack/boot_linux_v773_icnss_diag_stockdtb.img`, with three FDT blobs, all 19 `A90V765` markers, native-init marker, 4096-byte alignment, mode `0600`, and unpack roundtrip hash pass.
V774 stock-DTB-tail live handoff: TWRP flash/readback succeeded for the V773 image, but native init did not verify after reboot. Unlike V771 Download mode, the device returned to or remained recoverable through TWRP/recovery, and rollback to `stage3/boot_linux_v724.img` completed. Current native `version/status` passes on `A90 Linux init 0.9.68 (v724)` with `BOOT OK shell 4.2s` and `selftest pass=11 warn=1 fail=0`. Do not retry V770 or V773 custom OSRC kernel artifacts as-is. Next gate is host-only V775 boot incompatibility classification; prefer stock-kernel runtime observability over further custom-kernel flashes.
V775 boot incompatibility postmortem: host-only PASS. The stock v724 and V773 diagnostic boot header args match and both payloads have three appended FDT blobs, so missing DTB is no longer the sole blocker. Remaining custom-kernel suspects are pre-DTB payload delta `+16` bytes, shifted FDT offsets, kernel provenance/toolchain delta, and coarse RKP/RTIC marker-count delta. Custom OSRC kernel flashing remains paused. Stock v724 observability route: kprobes/dynamic debug/function tracer unavailable; static tracepoints and BPF syscall are configured, so next gate is read-only tracepoint inventory, not another flash.
V776 tracepoint inventory: live stock-v724 PASS. Temporary tracefs mount/read/cleanup worked and cleanup left tracefs unmounted. `available_events` is readable with `1250` events and `153` broad candidates: ICNSS/WLAN/Wi-Fi `1`, QMI/QRTR/service `1`, subsystem/remoteproc `3`, network `39`, scheduler/workqueue/IRQ `109`. Focus candidates are `msm_pil_event:{pil_event,pil_notif,pil_func}`, `dfc:dfc_qmi_tc`, and `cfg80211:cfg80211_report_wowlan_wakeup`. No BPF attach, ftrace write, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, or partition write executed. Next gate V777 should inspect tracepoint format/field semantics before any BPF attach proof. Custom OSRC kernel flashing remains paused.
V777 tracepoint format classifier: live stock-v724 PASS. Selected tracepoints all have readable format files and event-specific fields: `msm_pil_event:pil_event(event_name,fw_name)`, `msm_pil_event:pil_notif(event_name,code,fw_name)`, `msm_pil_event:pil_func(func_name)`, `dfc:dfc_qmi_tc(dev_name,txq,enable)`, `cfg80211:cfg80211_report_wowlan_wakeup(wiphy/wakeup fields)`. No BPF attach, ftrace write, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, or partition write executed; tracefs cleanup passed. Next gate V778 should be one bounded idle BPF attach/read/detach feasibility proof for `msm_pil_event:pil_notif` only. No modem/Wi-Fi trigger and no custom kernel flash.
V778 BPF attach feasibility: live classifier PASS without attach. Target `msm_pil_event:pil_notif` remains suitable, but no `bpftool`/`bpftrace` exists on device. Device values: `perf_event_paranoid=3`, `unprivileged_bpf_disabled=0`, `/sys/kernel/tracing` exists, `/sys/kernel/debug/tracing` absent. Host has `aarch64-linux-gnu-gcc/strip/readelf` and BPF/perf headers, so V779 should be build-only minimal static aarch64 helper for this one tracepoint. No BPF attach, ftrace write, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, or partition write executed.
V779 BPF loader build: host build-only PASS. Added `stage3/linux_init/helpers/a90_bpf_trace_probe.c` and built `tmp/wifi/v779-bpf-loader-build/a90_bpf_trace_probe-aarch64-static`, size `597920`, sha256 `9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3`. Binary is static aarch64 with no `INTERP`, marker `a90_bpf_trace_probe v779`, default `--check-only`, and attach gated by explicit `--allow-attach`. No device command, deploy, BPF attach, ftrace write, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, or partition write executed. Next V780 should deploy helper and run only check-only/hash/version/default-no-attach proof; attach remains blocked.
V780 BPF loader deploy check-only: live stock-v724 PASS. Added `scripts/revalidation/native_wifi_bpf_loader_deploy_checkonly_v780.py`; serial deploy used `/cache/a90-runtime/bin` staging and installed `/cache/bin/a90_bpf_trace_probe`. Remote sha256 matched `9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3`. Both `--check-only` and default no-argument execution printed marker `a90_bpf_trace_probe v779`, `result=check-only`, and `attach_attempted=0`. No `--allow-attach`, BPF attach, ftrace control write, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, or partition write executed. Next V781 may be a separate bounded idle attach/detach proof for `msm_pil_event:pil_notif`.
V781 BPF idle attach: live stock-v724 PASS. Added `scripts/revalidation/native_wifi_bpf_idle_attach_v781.py`; tracefs was temporarily mounted/read/cleaned up, target `msm_pil_event:pil_notif` id was `595`, and `/cache/bin/a90_bpf_trace_probe --allow-attach --verbose` returned `bpf_prog_fd=3`, `result=attach-detach-pass`, `attach_attempted=1`. Status after remained `BOOT OK` with tracefs unmounted. No modem/WLAN trigger, Wi-Fi HAL/service-manager, scan/connect, credential use, DHCP/routes, external ping, module load/unload, sysfs bind/unbind, reboot, flash, or partition write executed. Next V782 can use this BPF observer around one bounded modem/WLAN state transition without Wi-Fi scan/connect or external networking.
V782 BPF counter boot_wlan: live stock-v724 PASS. Added `stage3/linux_init/helpers/a90_bpf_trace_counter.c` and `scripts/revalidation/native_wifi_bpf_counter_boot_wlan_v782.py`. After refreshing V401 SELinuxfs mount and V490 policy load, V782 attached a count-capable BPF program to `msm_pil_event:pil_notif` while running the V750 lower-window transition. BPF result was `attach-count-pass`, `event_count=8`; `mss` moved `OFFLINING -> ONLINE -> ONLINE`, QRTR RX/TX and `sysmon-qmi` appeared, and `boot_wlan` executed. `mdm3` stayed `OFFLINING`; QRTR service `69/74/180`, WLFW/BDF, wiphy, and `wlan0` stayed absent. Cleanup rebooted back to healthy v724 with tracefs unmounted. No Wi-Fi HAL/service-manager, scan/connect, credential use, DHCP/routes, external ping, `qcwlanstate ON`, module load/unload, sysfs bind/unbind, `esoc0`, boot image write, or partition write executed. Next V783 should classify Android vs native PIL notification names/codes or mdm3/WLAN-PD trigger evidence before any further live trigger.
V787 clean-DSP arm-only: live stock-v724 PASS. The existing V641 one-shot sibling FW SSCTL hook was armed and rebooted without custom kernel flash; ADSP/CDSP/SLPI all completed with `failures=0 timeouts=0`, no `pm_qos`/reference/esoc warning boundary, firmware mounts cleaned, and v724 health restored. It did not run CNSS/HAL/scan/connect.
V788 clean-DSP lower readback: live stock-v724 BLOCKED. Inline clean-DSP, V401 SELinuxfs mount, V490 policy load, firmware mounts, `subsys_modem` holder, and CNSS-only lower companion all ran below service-manager/HAL/scan/connect. `mss` reached `ONLINE`, `mdm3` stayed `OFFLINING`, QRTR RX/TX, `sysmon-qmi`, and service-notifier markers appeared, but no QRTR services `69/74/180`, MHI/QCA6390, WLFW/BDF, wiphy, or `wlan0` appeared. Stop widening because dmesg produced a new `pm_qos_add_request()` duplicate-request warning through `msm_asoc_machine_probe` deferred probe. Cleanup reboot restored healthy v724. Next V789 should be host-only warning attribution before any live retry.
```

Vendor firmware files (`wlanmdsp.mbn`, `bdwlan.bin`, `regdb.bin`) confirmed at `sda29` (isolated mount), NOT in default native `/vendor`.

V743 proved the service-74 gated `mdm_helper` mode did not start `mdm_helper`
because the gate stayed closed. V744 proved helper v122 still reproduces the
older CNSS-only service publication window. V745 deployed helper v123 and proved
the service `180` gate can stay closed even with QRTR TX and `sysmon-qmi`
present. V746 deployed helper v124 and proved `mdm_helper` can start after
`sysmon-qmi`, but lower markers still do not move. V764 later proved
`mdm_helper` can also start under service `180`, with the same no-lower-progress
result. V747 host-only classified
the QCA6390 child driver-link gap as **not a bind/unbind target**. V748
host-only then rejected `mdm_helper` retry, repeated CNSS/HAL start, vendor
namespace repair, and `wlan` module load as next candidates. The selected next
gate is a read-only non-bind ICNSS/QCA trigger capture for the transition
from ICNSS parent readiness to WLFW/BDF/`wlan0`. V749 then classified the
concrete control surfaces: current native has `boot_wlan` and `qcwlanstate=OFF`,
does not expose `fs_ready`, and still has no `/dev/wlan`, wiphy, or `wlan0`.
V508/V513 reject standalone `boot_wlan`/`qcwlanstate`. V750 then ran bounded
lower-window `boot_wlan`: firmware mounts, modem holder, QRTR RX/TX,
`sysmon-qmi`, lower companion, write, and reboot cleanup passed, but
`qcwlanstate` remained `OFF` and `/dev/wlan`/wiphy/`wlan0`/WLFW/service `69`/BDF
remained absent. V751 classified the source-level meaning: `boot_wlan` enters
QCACLD/HDD init and creates `qcwlanstate`, but the static WLAN driver never
reaches driver-loaded / ICNSS-QMI / firmware-ready. The next target is inside or
immediately before HDD/PLD/register-driver completion, not another `boot_wlan`
retry. V752 then started the six-child CNSS companion window through `cnss_diag`
and `cnss-daemon` before bounded `boot_wlan`; this also stayed at the same HDD
init/qcwlanstate boundary with no ICNSS-QMI, FW-ready, WLFW/BDF, wiphy, or
`wlan0`. The next gate must instrument HDD/PLD/register-driver prerequisites
rather than repeat CNSS plus `boot_wlan` ordering. V753 confirmed there is no
visible explicit `hdd_init`/PLD/register-driver failure marker in existing
evidence, so V754 should add source-backed observability for that exact boundary.
V754 found tracefs/kallsyms are plausible but not active: tracefs is not mounted
and `available_filter_functions` is not readable. V755 should be a bounded
tracefs mount/filter proof with cleanup and no `boot_wlan` trigger. V755 then
proved tracefs mount/cleanup works but `available_filter_functions`,
`set_ftrace_filter`, and `set_graph_function` are unavailable, so the ftrace
path should be closed for this blocker.

### Key milestones

| cycle | result |
|---|---|
| v257 | cnss-daemon live start-only SUCCESS |
| v261 | init 0.9.60 flashed — PID1 orphan reaper added |
| v598 | service-notifier 180 first appearance |
| v644 | service-notifier 180/74 stable with service-74 gate |
| v653 | service-74 gated service-manager: 180/74 preserved |
| v724 | init 0.9.68 flashed — qrtr-ns boot hook; service-locator connects at 4.4s |
| v735 | live CNSS-only: mss ONLINE, cnss_diag+cnss-daemon started, WLFW/MHI still 0 |
| v738 | live modem/WLAN/MHI observer: mss ONLINE, mdm3 OFFLINING, MHI/WLFW/BDF/wlan0 still 0 |
| v740 | host-only mdm_helper contract: not first-trigger, but valid post-notifier candidate |
| v741 | helper v122 adds service74-gated mdm_helper start-only proof |
| v742 | helper v122 deployed to `/cache/bin/a90_android_execns_probe` |
| v743 | gated `mdm_helper` live: service-74 gate stayed closed, no HAL/connect |
| v744 | helper v122 CNSS-only comparison: QRTR TX/sysmon/service-notifier 180 reproduced, no MHI/WLFW/wlan0 |
| v745 | helper v123 deployed and live-tested: service180 gate stayed closed; no `mdm_helper`, no HAL/connect |
| v746 | helper v124 deployed and live-tested: sysmon gate opened and `mdm_helper` started, but no mdm3/MHI/WLFW/wlan0 progress |
| v747 | QCA6390 driver-link gap classified as not a bind/unbind target |
| v748 | host-only candidate matrix selects non-bind ICNSS/CNSS2/QCA WLFW trigger capture |
| v749 | read-only selector chooses lower-window `boot_wlan` proof; no HAL/connect |
| v750 | lower-window `boot_wlan` write succeeds but only control surface moves; no WLFW/BDF/wlan0 |
| v751 | `boot_wlan` enters HDD init but stalls before driver-loaded / ICNSS-QMI / FW-ready |
| v752 | CNSS companion before `boot_wlan` still stalls at HDD/qcwlanstate; next is HDD/PLD instrumentation |
| v753 | no explicit HDD/PLD/register-driver failure marker; V754 needs bounded instrumentation |
| v754 | tracefs/kallsyms plausible but unmounted; V755 needs bounded mount/filter proof |
| v755 | tracefs mount/cleanup works but no function filter target; route to non-ftrace instrumentation |
| v764 | service180-gated `mdm_helper` starts but no mdm3/WLFW/BDF/wlan0 lower progress |
| v765 | `A90V765` ICNSS/QCACLD log patch generated host-only |
| v766 | `A90V765` patch applies and defconfig passes in disposable OSRC tree |
| v767 | instrumented ICNSS/QCACLD objects compile; final Image blocked by RKP_CFP Python2 post-link |
| v768 | mdm_helper/esoc direct retry branch closed; route to RKP_CFP/Python2 packaging gate |
| v775 | V771/V774 custom OSRC kernel boot failures classified; custom-kernel flashing paused |
| v776 | stock v724 tracepoint inventory confirms static tracepoints remain usable |
| v781 | BPF idle attach/detach passes on `msm_pil_event:pil_notif` |
| v782 | BPF counter around lower-window `boot_wlan`: 8 PIL notifications counted, but no service 69/74/180, WLFW/BDF, or `wlan0` |
| v787 | stock-v724 clean-DSP arm-only proof passed with clean ADSP/CDSP/SLPI and no warning boundary |
| v788 | clean-DSP plus CNSS-only lower readback blocked by new `pm_qos_add_request` warning before any HAL/scan/connect |
| v783 | host-only Android/native gap classifier: first divergence is post-sysmon before service-notifier 74/180; native memshare/CMA failure at sysmon window becomes next read-only lead |
| v784 | live read-only memshare/CMA surface: client_4/CMA/reserved-memory present, idle CMA headroom exceeds V782 request sum, so next lead is client registration/timing or Android/native memshare behavior |
| v785 | host-only Android/native memshare delta: identical memshare/CMA failures are common/non-fatal; first native divergence is missing sibling sysmon (`slpi/adsp/cdsp`) and `mdm3=OFFLINING` |
| v786 | host-only clean-DSP/v724 gap classifier: stock v724 already contains the V641 one-shot sibling SSCTL hook/boot markers, but V782 did not arm or execute it; next is V787 arm-only stock-v724 clean-DSP proof |
| v787 | live stock-v724 clean-DSP arm-only proof: V641 one-shot passed, ADSP/CDSP/SLPI reached `status=0x0`, no warning boundary, firmware mounts cleaned; next is clean-DSP plus lower companion readback |

### Safety additions (Wi-Fi research)

- `esoc0` raw open **blocked** — blocks in `__subsystem_get(esoc0)`, requires reboot
- No DSP boot node writes without explicit approval (V615 kernel warning incident)
- No `wlan.ko` load/unload without explicit approval
- `firmware_class.path` rollback value: `/vendor/firmware_mnt/image`
- `sda29` mount must be read-only in all proof windows

## Docs structure

```
docs/plans/NATIVE_INIT_vNNN_*_PLAN_*.md   # per-cycle plan
docs/reports/NATIVE_INIT_vNNN_*_*.md      # per-cycle execution report
docs/operations/                           # runbooks, flash guide, versioning policy
docs/security/scans/                       # security scan results
```

Plans and reports are append-only historical records. Update `docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md` with cycle state after each completion.
