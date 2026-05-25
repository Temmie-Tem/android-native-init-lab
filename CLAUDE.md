# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Samsung Galaxy A90 5G (SM-A908N) — stock Android Linux kernel 4.14.190, custom static `/init` as PID 1, building a minimal embedded Linux console without Android userspace. Device flashed via TWRP, controlled over USB CDC ACM serial bridge.

- **Device**: SM-A908N, Android 12, Magisk 30.7, TWRP available
- **Current native build**: `A90 Linux init 0.9.68 (v724)` — `stage3/boot_linux_v724.img`
- **Known-good fallback**: `stage3/boot_linux_v48.img`
- **Active research cycle**: V867 proved helper `v134` PM init-contract markers execute, but `pm_proxy_helper` blocks in D-state and needs reboot cleanup; next is V868 host-only/read-only `pm_proxy_helper` and SELinux transition classification
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

## Wi-Fi bring-up research state (v598–v850, active)

Goal: bring up `wlan0` from native init without Android userspace.

### Confirmed architecture (SM8250/QCA6390)

- **Driver**: ICNSS core (`drivers/soc/qcom/icnss.c`, `drivers/soc/qcom/icnss_qmi.c`) plus QCACLD SNOC/PLD path — not the live `cnss2` PCIe/MHI path
- **ICNSS bootstrap**: ICNSS platform probe → QCACLD `pld_snoc_register_driver()` / `icnss_register_driver()` → WLFW service 69 on QRTR triggers `wlfw_new_server()` / `icnss_call_driver_probe()` → HDD probe/startup → BDF/FW-ready → `wlan0`
- **mss** is the internal modem path and can reach `ONLINE` in native lower-window tests, but this is not sufficient for WLFW publication
- **mdm3/eSoC** is the external SDX50M path from DTS (`qcom,mdm3`, `qcom,ext-sdx50m`, `ssctl-instance-id=<0x10>`, `sysmon-id=<0x14>`, AP/MDM GPIO handshake)
- **WLAN-PD/WLFW** publication is now gated on the mdm3/ext-sdx50m side advancing far enough to publish QRTR service 69
- **service-notifier 180/74** are side/recovery evidence, not direct ICNSS initial driver-probe triggers
- **wlan module**: static (`/sys/module/wlan` exists, not in `/proc/modules`)

### Companion stack (required, confirmed working)

Must run before cnss-daemon: `qrtr-ns → pd-mapper → rmt_storage → tftp_server`
Then: `cnss_diag → cnss-daemon`
Current CNSS-only ordering is confirmed with helper v122. Helper v123 added a
service `180` gated `mdm_helper` mode, but V745 live showed that marker is not
stable enough in every boot. Helper v124 added a `sysmon-qmi` gated
`mdm_helper` mode. V746 proved `mdm_helper` starts safely after `sysmon-qmi`,
but it does not advance mdm3/WLAN-PD/WLFW.

### Current blocker (V836)

V829 executed the exact bounded service-locator `GET_DOMAIN_LIST` QMI request
for `wlan/fw`:

```text
00 01 00 21 00 11 00 01 07 00 77 6c 61 6e 2f 66 77 10 04 00 00 00 00 00
```

The visible destination from V826 was service-locator `64/257`, node `1`, port
`16475`. V829 returned `msm/modem/wlan_pd` instance `180`, so the pd-mapper DB
empty hypothesis is closed.

V830 and V831 then sent a bounded service-notifier `REGISTER_LISTENER` request
for that returned domain against service-notifier `66/46081`. Both late-window
and early-window native probes registered successfully, but current state stayed
`uninit` and no state indication arrived. V832 therefore rejects duplicate
service-locator, listener timing, `boot_wlan`, `qcwlanstate`, CNSS ordering, and
`mdm_helper` retries.

V833 added a static Android-run helper and handoff wrapper for an Android
positive-control of the same `msm/modem/wlan_pd` service-notifier listener
query. Live V833 booted Android, ran the bounded listener request, and rolled
back to native v724. Android returned raw state `0x1fffffff`, which OSRC defines
as `SERVREG_NOTIF_SERVICE_STATE_UP_V01`.

This proves the listener payload/model is valid. Native V830/V831 `UNINIT`
therefore means native is genuinely missing the lower WLAN-PD state transition
before WLFW/service69, BDF, wiphy, and `wlan0`.

V834 was host-only and selected the next narrow native gate. It rejects repeating
V829 service-locator, V830/V831 listener timing, `boot_wlan`, `qcwlanstate`,
`mdm_helper`, custom diagnostic kernel flashing, service-manager, Wi-Fi HAL,
scan/connect, DHCP, routes, and external ping. The next selected gate is V835:
run the corrected service-notifier listener inside the best existing bounded
native lower window, the known-ASoC-warning clean-DSP/CNSS path from V792.

V835 live PASS executed that selected gate. Helper v128 was deployed, clean-DSP
inline proof passed, V401/V490 current-boot prep passed, and the lower companion
started `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon`.
Service-notifier `180/74` and the exact known ASoC warning were present, but the
corrected `msm/modem/wlan_pd` listener still returned `0x7fffffff` / `UNINIT`;
no indication arrived, WLFW service `69`, BDF, wiphy, and `wlan0` stayed absent,
and cleanup reboot restored healthy native v724. V836 should be host-only first:
classify the remaining Android-only WLAN-PD state-up contract after service
`180/74`; do not widen to HAL/scan/connect/DHCP/routes/external ping.

V836 host-only PASS compared V835 with Android V649. Android reaches WLFW about
`1.292s` and WLAN-PD about `2.361s` after service `74`, while native V835 has
service `180/74` and the exact known ASoC warning but no WLAN-PD `UP`, WLFW,
BDF, wiphy, or `wlan0`. V836 rejects an identical V835 replay, HAL/connect, and
`boot_wlan`/`qcwlanstate` retry. V837 should add timestamped listener
send/response/hold evidence relative to service `74` and hold through at least
the Android post-service74 WLAN-PD window, still below HAL/connect.

V837 live PASS added helper v129 timestamp fields and reran the V835 lower
window. Service `74` arrived at `86470.953 ms`, but the listener send was
`87084.000 ms`, about `613 ms` later. The listener then held for `15006 ms` and
closed `15619 ms` after service `74`, but it was not open at service `74`
publication time; response remained `UNINIT`, no indication arrived, and
WLFW/BDF/wiphy/`wlan0` stayed absent. Cleanup reboot restored healthy native
v724. V838 should make listener registration earlier or concurrent with
service-notifier publication before widening to service-manager/HAL/connect.

V838 live PASS added helper v130 `service-notifier-listener-only` and prearmed
the listener before the lower CNSS companion stack. The listener registered
about `637 ms` before service `74`, remained open through service `74` + `5s`,
and still received no WLAN-PD `UP` indication. This closes the simple timing
explanation. V839 host-only PASS then compared V833 Android positive-control,
V838, and V700 provider-first CNSS retry. It selected V840: combine
provider-first CNSS retry with the V838-style prearmed WLAN-PD listener, still
below Wi-Fi HAL, scan/connect, DHCP/routes, and external ping.

V840 live PASS combined provider-first service-manager/PeripheralManager, a
fresh CNSS retry, and a prearmed WLAN-PD listener. Native had service `180/74`,
CNSS netlink, and CLD80211 access, but still had no `wlfw_start`, WLAN-PD
indication, BDF, FW-ready, or `wlan0`. V841 host-only PASS compared that result
with Android V622 and the already closed V618/V746/V764 branches. Android V622
emits `cnss-daemon wlfw_start` about `1415.75 ms` after service `180`, before
WLAN-PD `UP` at `2427.362 ms`; `sysmon_esoc0` appears later at `4491.638 ms`.
Therefore `sysmon_esoc0` is not the next proven prerequisite. The next gate is
V842: classify the Android/native `cnss-daemon` pre-WLFW launch/runtime
contract, including argv/init service contract, properties, SELinux domain,
inherited fds, Binder/vndbinder context, child lifetime, and exit reason.

V842 host-only PASS compared V841/V840 with V704, V697, V525, and Android V622.
The broad launch contract is closed for the current blocker: Android and native
match the `cnss-daemon -n -l` command, `u:r:vendor_wcnss_service:s0` domain,
system uid/gid, expected groups, `CAP_NET_ADMIN`, vndbinder fd, and active
socket surface. Native `cnss-daemon` is alive/sleeping with four threads, but
never emits `wlfw_start`. The next gate is V843: capture the current-window
provider-first CNSS retry stall point with `wchan`, syscall, task status/stat,
optional stack, fd targets, socket inode mapping, and dmesg deltas before
cleanup.

V843 host-only PASS parsed the existing V840 cleanup-time stall snapshot.
Current-window retry `cnss-daemon` is alive in `do_sys_poll`, with worker
threads split between `do_sys_poll` and `futex_wait_queue_me`. CNSS user socket,
netlink, socket fd, and vndbinder surfaces are present, while `wlfw_start`,
WLAN-PD, BDF, FW-ready, and `wlan0` remain absent. The next gate is V844:
classify the source-backed ICNSS/WLFW event publication prerequisite before
any Wi-Fi HAL, scan/connect, DHCP/routes, credential, or external ping action.

V844 host-only PASS corrected the architecture model from DTS and ICNSS source.
`qcom,mdm3` is `qcom,ext-sdx50m` with AP/MDM GPIO handshake, SSCTL instance
`16`, and sysmon id `20`. ICNSS service-notifier UP is not the initial boot
trigger; WLFW still depends on QRTR service 69 arrival via `wlfw_new_server()`.
Existing native evidence has `mss=ONLINE`, `mdm3=OFFLINING`, and no WLFW/BDF/
FW-ready/`wlan0`. The next gate is V845: read-only live mdm3/ext-sdx50m eSoC
GPIO/sysfs surface classification. Keep raw `esoc0` open, GPIO/sysfs writes,
Wi-Fi HAL, scan/connect, DHCP/routes, credentials, external ping, and boot-image
work blocked.

V845 live read-only PASS captured the mdm3/ext-sdx50m surface on stock native
v724. mdm3/eSoC sysfs, `subsys_esoc0`, live devicetree compatible
`qcom,ext-sdx50m`, and AP/MDM GPIO properties are present; mdm3 remains
`OFFLINING`; `/sys/kernel/debug/gpio` is not readable; GPIO 135/142 are not
exported; raw `/dev/esoc*` and `/dev/subsys*` nodes are absent. Existing
writable candidates include `esoc_link`, `esoc_link_info`, `esoc_name`,
`subsys9/state`, and `subsys0/state`, but V845 performed no writes. The next
gate is V846: source-backed mdm3/eSoC state-control contract classification
before any bounded write or GPIO action. HAL/connect, credentials, DHCP/routes,
external ping, and boot-image work remain blocked.

V846 host-only PASS mapped V845 candidates to OSRC source. Direct
`/sys/.../subsys9/state` writes are rejected because `state` is
`DEVICE_ATTR_RO(state)` with no store path. Opaque `esoc_link`/`esoc_name`
writes and raw `/dev/esoc*` ioctls stay rejected. The source-backed userspace
boot contract is the subsystem char-device path: `subsys_device_open()` calls
`subsystem_get_with_fwname()` and `subsys_start()`, while release calls
`subsystem_put()`/`subsys_stop()`. V845 provides `subsys_esoc0` uevent
`major=236 minor=9 devname=subsys_esoc0` but no `/dev` node. The next gate is
V847: materialize only `/dev/subsys_esoc0` and run one bounded open/hold smoke
with watchdog, dmesg/state evidence, cleanup reboot, and postflight health.
Still no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
external ping, or boot-image work.

V847 live bounded PASS materialized `/dev/subsys_esoc0` from V845 uevent
`236:9`, started one background open/hold, captured state/dmesg, removed the
node, and reboot-cleaned back to healthy v724. The open reached
`__subsystem_get: esoc0 count:0` and changed `fw_name` to `esoc0`, but did not
report `holder.opened=1` inside the bounded window. mdm3 stayed `OFFLINING`;
MHI/PCIe, WLFW/BDF/FW-ready/`wlan0`, warning, panic, and fatal markers stayed
absent in the focused output. Next gate is V848 host-only: classify the
`subsys_esoc0` open-block boundary below `subsystem_get()` and before MHI/WLFW
before any retry, longer hold, HAL/connect, DHCP/routes, credentials, external
ping, or boot-image work.

V848 host-only PASS classified the V847 block. `subsys_device_open()` enters
`subsystem_get_with_fwname()`/`__subsystem_get()`, then `subsys_start()` calls
the provider `powerup()` hook and later `wait_for_err_ready()`. V847 proves the
entry point and `fw_name` update but not open success, MHI/PCIe, WLFW/BDF, or
`wlan0`. The branch is now provider `powerup()` GPIO/IRQ handshake versus
`wait_for_err_ready()` completion wait. Defconfig enables ESOC/ESOC_DEV/
ESOC_CLIENT/ESOC_MDM_4x/ESOC_MDM_DRV, but the staged OSRC tree lacks the eSoC
MDM provider source, so V849 must sample the blocked holder task's `wchan`,
stack/status/syscall, read-only `/sys/module` eSoC surface, mdm3 state, and
focused dmesg rather than doing a blind longer hold or widening to GPIO writes,
raw eSoC ioctls, HAL/connect, DHCP/routes, credentials, external ping, or
boot-image work.

V849 live bounded PASS captured the missing task wait state. The
`subsys_esoc0` holder does not reach `wait_for_err_ready()` and does not
progress to MHI/WLFW. Its `wchan` is `mdm_subsys_powerup`, task state is
`D (disk sleep)`, and stack is `mdm_subsys_powerup -> __subsystem_get ->
subsys_device_open`. mdm3/subsys9 remains `OFFLINING`; WLFW/BDF/FW-ready/
`wlan0` remains absent. Cleanup reboot restored healthy v724. Current blocker
is now inside proprietary ext-mdm provider power-up, before SDX50M publishes
WLFW service 69. Next gate is V850 host-only/read-only: classify
`mdm_subsys_powerup` provider surface from V849 evidence, live sysfs/module
surface, available symbols, and Android reference behavior. Still no GPIO/sysfs
write, raw eSoC ioctl, MHI write, HAL/connect, DHCP/routes, credentials,
external ping, or boot-image work.

V850 host-only PASS correlated V849 with Android V591 and DTS. Android can
bring mdm3 `ONLINE` and WLAN-PD present, while native blocks in
`mdm_subsys_powerup`. DTS maps mdm3 to `qcom,ext-sdx50m`, AP2MDM status GPIO
`0x87`, MDM2AP status GPIO `0x8e`, SSCTL instance `0x10`, and sysmon id
`0x14`. ESOC MDM configs are enabled but the staged OSRC tree lacks provider
source, so no GPIO/sysfs/raw-eSoC/MHI write is justified. V851 should capture
read-only live provider surface: filtered kallsyms, interrupts, platform
driver/sysfs/of_node/power state, eSoC sysfs, msm_subsys state, readable
GPIO/debug/pinctrl if available, and focused ext-mdm dmesg.

```text
servloc:64:257;ssctl:43:4098;servnotif:66:18945,46081;wlfw:69:1
```

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
V789 V788 warning classifier: host-only PASS. V788 is the only compared run with the warning (`kernel_warning=5`; V733/V735/V787 all `0`). Warning context is service-notifier `180/74` -> ADSP/APR audio -> duplicate `msm_asoc_machine_probe` -> `pm_qos_add_request()` duplicate request in deferred probe; WLFW/BDF/wiphy/`wlan0` remain absent. Next live gate should be narrower than V788: clean-DSP + current V401/V490 + lower-only companion readback, omitting `cnss_diag` and `cnss-daemon`.
V790 clean-DSP lower-only: live stock-v724 BLOCKED. CNSS was omitted, but lower-only (`qrtr-ns,rmt_storage,tftp_server,pd-mapper`) still reproduced the same `pm_qos_add_request()` duplicate warning after service-notifier `180/74` and ADSP/APR audio deferred probe. `mss` reached `ONLINE`; `mdm3` stayed `OFFLINING`; no MHI/QCA6390/WLFW/BDF/wiphy/`wlan0`. Cleanup reboot restored healthy v724. Do not repeat lower companion live until V791 host-only compares V790/V788/V787/V733 and chooses a narrower isolation path.
V812 mdm3/WLAN-PD/service69 observer: live stock-v724 PASS. Current-boot V401 SELinuxfs mount, V490 policy load, firmware mounts, `subsys_modem` holder, and lower companion/CNSS diagnostic stack completed below service-manager/HAL/scan/connect. `mss` stayed `ONLINE`, QRTR RX/TX and `sysmon-qmi` were present, but `mdm3` stayed `OFFLINING` and service-notifier/WLAN-PD/WLFW/service69/BDF/wiphy/`wlan0` remained absent. Cleanup reboot restored healthy v724. Next gate is post-sysmon mdm3/WLAN-PD service-publication precondition isolation, not qcwlanstate, service-manager, HAL, scan/connect, or custom-kernel flash.
V813 post-sysmon classifier: host-only PASS. V812 confirms current sysmon-without-service69, V785 demotes memshare/CMA as a sole blocker, and V626/V783 show Android publishes sibling sysmon plus service74/WLAN-PD/WLFW while native lacks sibling sysmon/service74/WLFW. Next gate is V814 sibling sysmon/service-publication precondition isolation below HAL/connect, with custom-kernel flashing still paused.
V814 sibling sysmon source classifier: host-only PASS. Samsung OSRC source maps service-notifier to SERVREG QMI listener/state indication and sysmon to subsystem registration/QMI lookup. This confirms the next useful step is a read-only stock-v724 subsystem/sysmon/service-locator registration snapshot, not userspace daemon/HAL/connect retry or custom-kernel flash.
V815 subsystem/sysmon snapshot: live stock-v724 read-only PASS. Idle native has msm_subsys surface present, modem/mss `OFFLINING`, mdm3/esoc0 `OFFLINING`, esoc sysfs present, ICNSS platform present, service-locator timeout markers, and no runtime service-notifier/service74/WLAN-PD/WLFW/BDF/`wlan0`. Static devicetree/sysfs WLAN strings are separated from runtime marker counts. Next gate is V816 idle-vs-trigger delta classification using V815 and V812 evidence.
V816 idle-vs-trigger delta classifier: host-only PASS. Idle has modem/mdm3 `OFFLINING` and no runtime service publication. V812 lower trigger advances mss/QRTR/sysmon, but mdm3 remains `OFFLINING` and service74/WLAN-PD/WLFW/service69/BDF/`wlan0` remain absent. Next gate is V817 in-window read-only sampling of V815 surfaces around the existing lower trigger, not HAL/connect or custom-kernel flash.
V817 in-window sysmon sampler: live stock-v724 PASS. Current-boot V401/V490 refresh, firmware mounts, `subsys_modem` holder, and lower companion/CNSS diagnostic stack ran below service-manager/HAL/scan/connect. In-window snapshots show mss `OFFLINING -> ONLINE -> ONLINE`, QRTR readiness and `sysmon-qmi` appear, but mdm3 stays `OFFLINING` and service74/WLAN-PD/WLFW/service69/BDF/`wlan0` remain absent. Cleanup reboot restored healthy v724. Next gate V818 should isolate mdm3/esoc0 service-locator/sysmon registration state without `esoc0` open, HAL/connect, or custom-kernel flash.
V818 mdm3/esoc registration classifier: host-only PASS. V817 proves the live lower window advances mss/QRTR/sysmon but not mdm3/service publication; V798 removes missing modem PIL notifications as the active blocker; V795 removes holder-only retry; V817 evidence shows esoc sysfs/class surfaces but no `/dev/esoc*` or `/dev/subsys*` node. Next gate V819 is a bounded read-only mdm3/esoc0 service-locator/sysmon registration catalogue below service-manager/HAL/connect.
V819 mdm3/esoc registration catalogue: live stock-v724 PASS. Wrapped V817 still passes: mss moves `OFFLINING -> ONLINE -> ONLINE`, mdm3 remains `OFFLINING`, and WLAN-PD/WLFW remain absent. Added read-only catalogue shows esoc/mdm3 sysfs surfaces exist, but debugfs service surfaces are missing, global `/proc/net/qrtr` is missing, and per-process QRTR catalogue sections are empty. Cleanup reboot restored healthy v724. Next gate V820 should inspect helper/per-process QRTR namespace state and service-locator visibility without HAL/connect.
V820 QRTR namespace classifier: host-only PASS. V819 evidence shows QIPCRTR protocol visibility and working helper AF_QIPCRTR readback, while `/proc/net/qrtr`/debugfs visibility remains absent and WLFW service69 publication remains empty. This demotes procfs/debugfs absence to a visibility limitation rather than proof of QRTR failure. Custom OSRC kernel flashing remains paused under the V775 postmortem. Next gate V821 should run an in-helper QRTR nameservice matrix for service-locator/service-notifier/WLAN-PD/WLFW candidates without QMI payload, service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
V821 QRTR nameservice matrix: live stock-v724 PASS. Helper v125 added `--qrtr-readback-matrix` and was deployed below HAL/connect. The V817 lower window still passes, AF_QIPCRTR lookup/delete sends work for service-locator `64/1`, service-notifier `66/74`, service-notifier `66/180`, WLFW `69/0`, and WLFW `69/1`, but all five cases return only end-of-list with `service_events=0`. No QMI payload, service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, `esoc0`, module load/unload, boot image write, partition write, or custom-kernel flash executed. Cleanup reboot restored healthy v724. Next gate V822 should classify why kernel sysmon/service-locator dmesg appears while userspace AF_QIPCRTR nameservice publication stays clean-empty.
V822 sysmon nameservice gap classifier: host-only PASS. OSRC source shows service-locator is `64/1`, service-notifier is `66/<instance>`, WLFW is `69/0`, but `sysmon-qmi.c` looks up SSCTL service `0x2b` version `2` with `desc->ssctl_instance_id`. The r3q board DTS sets mdm3 `qcom,ssctl-instance-id=<0x10>`, so V821 did not query the actual sysmon SSCTL nameservice path. Next gate V823 should reuse helper v125 and add `ssctl:43:16` to the no-QMI matrix before any QMI payload, service-manager, Wi-Fi HAL, scan/connect, credential, DHCP/routes, external ping, or custom-kernel flash.
V823 SSCTL nameservice matrix: live stock-v724 PASS. Helper v125 was reused/redeployed and the V817 lower window still passes. Expanded no-QMI AF_QIPCRTR matrix covered service-locator `64/1`, SSCTL `43/16`, service-notifier `66/74`, service-notifier `66/180`, WLFW `69/0`, and WLFW `69/1`; all six lookup/delete sends returned rc `0`, no timeout, no QMI payload, but all returned end-of-list with `service_events=0`. Runtime dmesg counters still show after-companion `service_locator=5` and `sysmon_qmi=1`, while mdm3 stays `OFFLINING` and service-notifier/WLFW/BDF/wlan0 stay absent. Cleanup reboot restored healthy v724. Next V824 should classify kernel QMI client visibility versus userspace AF_QIPCRTR nameservice visibility before any wider trigger.
V824 QRTR encoded instance classifier: host-only PASS. Samsung OSRC `qmi_interface.c` shows `qmi_send_new_lookup()` sends QRTR nameservice instance as `svc->version | svc->instance << 8`; V823 mostly queried raw instance IDs. The next encoded no-QMI matrix is `servloc:64:257;ssctl:43:4098;servnotif:66:18945,46081;wlfw:69:1`. No bridge/device command, QRTR socket, QMI payload, service-manager, Wi-Fi HAL, scan/connect, credential, DHCP/routes, external ping, boot image write, partition write, or custom-kernel flash executed. Next V825 should run that encoded-instance matrix below HAL/connect before any wider trigger.
V825 QRTR encoded matrix: live stock-v724 PASS. Helper v125 was redeployed by serial fallback and V817 lower window completed with cleanup reboot. Encoded no-QMI matrix `servloc:64:257;ssctl:43:4098;servnotif:66:18945,46081;wlfw:69:1` completed all five lookup/delete cases with no timeout and no QMI payload. Service events appeared for `servloc 64/257` and `servnotif 66/46081`; `ssctl 43/4098`, `servnotif 66/18945`, and `wlfw 69/1` remained empty. Next V826 should capture nameservice event payload details before any QMI payload, HAL/connect, credentials, DHCP/routes, external ping, or custom-kernel flash.
V826 QRTR event detail classifier: host-only PASS. Existing V825 annotated evidence contains NEW_SERVER payloads: `servloc 64/257` at node `1` port `16475`, and `servnotif 66/46081` at node `0` port `2`. Empty events confirm no `ssctl 43/4098`, no `servnotif 66/18945`, and no `wlfw 69/1` publication in that lower window. No bridge/device command, QRTR socket, QMI payload, service-manager, Wi-Fi HAL, scan/connect, credential, DHCP/routes, external ping, boot image write, partition write, or custom-kernel flash executed. Next V827 should classify service-notifier 180 continuation versus SSCTL/WLFW absence.
V827 service-notifier continuation classifier: host-only PASS. OSRC source maps ICNSS continuation as `get_service_location("ICNSS-WLAN", "wlan/fw")` -> service-locator `GET_DOMAIN_LIST` on service `64/257` -> `service_notif_register_notifier()` for returned domains -> service-notifier `REGISTER_LISTENER`/state indication -> WLFW `69/1`. V826's visible service-notifier `66/46081` is therefore only the root notifier endpoint, not WLAN-PD UP or WLFW readiness. No bridge/device command, QRTR socket, QMI payload, service-manager, Wi-Fi HAL, scan/connect, credential, DHCP/routes, external ping, boot image write, partition write, or custom-kernel flash executed. Next V828 should derive the bounded service-locator domain-list payload for `wlan/fw`.
V828 service-locator domain-list payload derivation: host-only PASS. Derived QMI request bytes for `GET_DOMAIN_LIST wlan/fw`: `00 01 00 21 00 11 00 01 07 00 77 6c 61 6e 2f 66 77 10 04 00 00 00 00 00`. Destination remains service-locator `64/257` node `1` port `16475`. No bridge/device command, QRTR socket, QMI payload, service-manager, Wi-Fi HAL, scan/connect, credential, DHCP/routes, external ping, boot image write, partition write, or custom-kernel flash executed. Next V829 should implement a bounded no-HAL live probe that sends only this request and parses response TLVs.
V829 service-locator domain-list probe: live stock-v724 PASS. Helper v126 queried service-locator `64/257` node `1` port `16475` with the V828 `GET_DOMAIN_LIST wlan/fw` request and received QMI success `result=0 error=0`; the returned domain list contains `msm/modem/wlan_pd` instance `180`. Cleanup reboot restored healthy v724. No service-manager, Wi-Fi HAL, scan/connect, credential, DHCP/routes, external ping, boot image write, partition write, or custom-kernel flash executed. Next V830 should derive a bounded service-notifier `REGISTER_LISTENER` proof for `msm/modem/wlan_pd` instance `180`.
V830 service-notifier listener probe: live stock-v724 PASS. Helper v127 queried service-notifier `66/46081` node `0` port `2` and sent only the bounded `REGISTER_LISTENER` request for `msm/modem/wlan_pd`. The endpoint returned QMI success `result=0 error=0`, but current state was `0x7fffffff` / `uninit`; no state indication arrived, so no ACK was sent. Cleanup reboot restored healthy v724. No service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, `esoc0`, module load/unload, boot image write, partition write, or custom-kernel flash executed. Next V831 should classify why WLAN-PD remains uninitialized despite successful service-locator and service-notifier registration.
V831 early service-notifier listener probe: live stock-v724 PASS. Helper v128 moved the service-notifier listener to the early lower companion window, kept the endpoint lookup bounded to `10s`, and kept the listener open for the bounded indication window. Service-notifier `66/46081` again accepted `REGISTER_LISTENER` for `msm/modem/wlan_pd` with QMI success `result=0 error=0`, but current state remained `0x7fffffff` / `uninit` and no state indication arrived. Cleanup reboot restored healthy v724. No service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, `esoc0`, module load/unload, boot image write, partition write, or custom-kernel flash executed. Next V832 should focus on the Android-only `mdm3=ONLINE` / WLAN-PD-UP trigger contract, not listener timing.
V837 timestamped listener hold: live stock-v724 PASS. Helper v129 proved the current lower-window listener placement is too late: service `74` arrived at `86470.953 ms`, listener send was `87084.000 ms`, and the listener was not open at service `74`; it then held for `15006 ms`, response stayed `UNINIT`, no indication arrived, and no WLFW/BDF/wlan0 appeared. No service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, `esoc0`, module load/unload, boot image write, partition write, or custom-kernel flash executed. Next V838 should make listener registration earlier or concurrent with service-notifier publication.
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
| v789 | host-only V788 warning attribution; next gate is lower-only clean-DSP replay without CNSS |
| v790 | lower-only clean-DSP replay also reproduces `pm_qos_add_request`, so CNSS is not required for the warning |
| v783 | host-only Android/native gap classifier: first divergence is post-sysmon before service-notifier 74/180; native memshare/CMA failure at sysmon window becomes next read-only lead |
| v784 | live read-only memshare/CMA surface: client_4/CMA/reserved-memory present, idle CMA headroom exceeds V782 request sum, so next lead is client registration/timing or Android/native memshare behavior |
| v785 | host-only Android/native memshare delta: identical memshare/CMA failures are common/non-fatal; first native divergence is missing sibling sysmon (`slpi/adsp/cdsp`) and `mdm3=OFFLINING` |
| v786 | host-only clean-DSP/v724 gap classifier: stock v724 already contains the V641 one-shot sibling SSCTL hook/boot markers, but V782 did not arm or execute it; next is V787 arm-only stock-v724 clean-DSP proof |
| v787 | live stock-v724 clean-DSP arm-only proof: V641 one-shot passed, ADSP/CDSP/SLPI reached `status=0x0`, no warning boundary, firmware mounts cleaned; next is clean-DSP plus lower companion readback |
| v809 | host-only source mapping: qcwlanstate `OFF` is a status mirror for QCACLD not reaching `DRIVER_MODULES_ENABLED`; next boundary is PLD/ICNSS register-to-WLFW/FW_READY |
| v810 | host-only register/probe mapping: PLD/SNOC/ICNSS register is async, while QCACLD probe is gated by WLFW/service69 -> ICNSS-QMI -> `FW_READY`; next is WLFW publication preconditions |
| v811 | host-only WLFW precondition mapping: Android reaches mdm3 ONLINE + WLAN-PD/WLFW/BDF/wlan0, while native keeps mdm3 OFFLINING and service69 clean-empty; next is below-HAL mdm3/WLAN-PD/service69 observer |
| v812 | live stock-v724 observer reaches mss ONLINE + QRTR/sysmon but mdm3 remains OFFLINING and service69/WLFW/BDF/wlan0 stay absent; next is post-sysmon mdm3/WLAN-PD service publication |
| v813 | host-only post-sysmon classifier selects sibling sysmon/service-publication prerequisites as the next blocker; custom-kernel flashing remains paused |
| v814 | host-only source classifier maps service-notifier/sysmon to kernel registration paths; next is read-only stock-v724 subsystem/sysmon/service-locator snapshot |
| v815 | live read-only idle snapshot captures modem/mdm3 OFFLINING baseline and no runtime service74/WLAN-PD/WLFW; next is idle-vs-trigger delta classifier |
| v816 | host-only idle-vs-trigger delta: lower trigger advances mss/sysmon only; mdm3 and service-publication stay blocked |
| v817 | live in-window sampler: lower window advances mss/QRTR/sysmon but mdm3 remains OFFLINING and service74/WLAN-PD/WLFW stay absent; next is mdm3/esoc0 registration isolation |
| v818 | host-only registration classifier: V817/V798/V795 close holder-only, PIL, HAL/connect, and custom-kernel retry paths; next is bounded read-only mdm3/esoc0 registration catalogue |
| v819 | live read-only registration catalogue: esoc/mdm3 sysfs exists, but debugfs service surfaces, global `/proc/net/qrtr`, and per-process QRTR sections are absent; next is helper/per-process QRTR namespace inspection |
| v820 | host-only QRTR namespace classifier: QIPCRTR/AF_QIPCRTR readback works, but procfs/debugfs visibility is absent and service69 publication is still empty; next is in-helper nameservice matrix |
| v821 | live helper v125 nameservice matrix: AF_QIPCRTR lookup works for service-locator/service-notifier/WLFW candidates, but all return end-of-list with service publication 0; next is sysmon dmesg vs userspace nameservice gap classification |
| v822 | host-only source/evidence classifier: sysmon-qmi uses SSCTL service `43` instance `16`, which V821 did not query; next is V823 no-QMI matrix extension with `ssctl:43:16` |
| v823 | live helper v125 SSCTL matrix: `ssctl:43:16` also returns end-of-list with publication 0; next is kernel QMI client visibility vs userspace AF_QIPCRTR nameservice semantics |
| v824 | host-only QRTR encoded-instance classifier: kernel `qmi_add_lookup()` encodes instances as `version | instance << 8`; next is encoded no-QMI matrix `servloc:64:257;ssctl:43:4098;servnotif:66:18945,46081;wlfw:69:1` |
| v825 | live encoded matrix: service publication is visible for `servloc 64/257` and `servnotif 66/46081`; next is no-QMI event-detail capture |
| v826 | host-only event detail classifier: visible events are `servloc 64/257 node=1 port=16475` and `servnotif 66/46081 node=0 port=2`; next is service-notifier 180 continuation classification |
| v827 | host-only continuation classifier: service-notifier 180 is only a control endpoint; ICNSS still needs service-locator `wlan/fw` domain-list and notifier registration |
| v828 | host-only payload derivation: exact `GET_DOMAIN_LIST wlan/fw` QMI request bytes derived; next is bounded no-HAL live probe |
| v829 | live service-locator probe: `GET_DOMAIN_LIST wlan/fw` returns `msm/modem/wlan_pd` instance `180`; pd-mapper empty-domain blocker closed |
| v830 | host-only service-notifier request derivation selects bounded `REGISTER_LISTENER msm/modem/wlan_pd` |
| v831 | live service-notifier listener probe succeeds but reports current state `uninit`; no HAL/connect |
| v833 | Android positive-control proves the same listener model can report WLAN-PD `UP` |
| v835 | native lower-window replay still reports `uninit` with service74/180 present; ordering/model/timing-as-placed blockers narrowed |
| v837 | timestamped listener hold proves the listener opened about `613ms` after service74; next is concurrent prearm |
| v838 | concurrent prearmed listener registers about `637ms` before service74, stays open through service74+5s, and still receives no WLAN-PD `UP`; timing blocker ruled out |
| v839 | host-only classifier selects provider-first CNSS retry plus prearmed WLAN-PD listener as V840 |
| v840 | provider-first service-manager/PeripheralManager + CNSS retry with prearmed WLAN-PD listener still reports `UNINIT`; no WLFW/BDF/wlan0 |
| v841 | host-only classifier selects `cnss-daemon` pre-WLFW launch/runtime contract as V842; `sysmon_esoc0` is not the current prerequisite |
| v842 | host-only classifier closes coarse CNSS launch contract and selects current-window CNSS stall snapshot as V843 |
| v843 | host-only classifier confirms current retry `cnss-daemon` waits in poll/futex with CNSS socket/netlink surfaces; selects V844 event-source prerequisite classification |
| v844 | host-only classifier identifies mdm3/ext-sdx50m eSoC boot interface as the WLFW publication prerequisite |
| v845 | live read-only mdm3/eSoC surface snapshot: mdm3 OFFLINING, eSoC/sysfs present, raw device nodes absent |
| v846 | host-only state-control contract selects bounded `subsys_esoc0` char-open over sysfs/GPIO writes |
| v847 | bounded `subsys_esoc0` open reaches `__subsystem_get(esoc0)` but does not complete; no MHI/WLFW/wlan0 |
| v848 | host-only classifier narrows the block to provider `powerup()` versus `wait_for_err_ready()` |
| v849 | live wait-state sampler captures holder in `mdm_subsys_powerup` D-state; no MHI/WLFW/BDF/wlan0 |
| v850 | host-only classifier selects proprietary ext-mdm provider surface and preserves PMIC/GPIO hints |
| v851 | live read-only provider snapshot: mdm3 OFFLINING, surrounding symbols visible, `mdm_subsys_powerup` not exposed in idle kallsyms |
| v852 | Android handoff positive-control: mdm3/mss ONLINE, real eSoC/subsys nodes, WLAN-PD/BDF/wlan0 present, rollback to native v724 verified |
| v853 | Android actor handoff: `mdm_helper`/`ks` hold `/dev/esoc-0`, `pm-service` holds `/dev/subsys_esoc0` and `/dev/subsys_modem`; rollback to native v724 verified |
| v854 | host-only actor parity classifier rejects blind repeats and selects V855 native Android node/ueventd parity preflight before actor open/ioctl |
| v855 | native node parity preflight materializes `/dev/esoc-0`, `/dev/subsys_esoc0`, and `/dev/subsys_modem`, confirms no holders, cleans up, and preserves health |
| v856 | pm-service node-parity start-only reaches service managers plus `pm-service`/`pm-proxy`, but no subsystem fd hold; next is narrow `vendor.peripheral.shutdown_critical_list` property-contract replay |
| v857 | pm-service property-contract replay allows the observed shutdown-critical-list values but still has no subsystem fd hold; next is property-info context delta for pm-service/pm-proxy read keys |
| v858 | pm-service/pm-proxy property-context delta maps 8 V857 residual keys and deploys the private property root update without daemon start |
| v859 | V858 target denials are gone, but new vndservicemanager/ServiceManager/PerMgrLib property denials remain; no subsystem fd hold yet |
| v860 | V858/V859/V677 property superset drops property denials to zero; pm-service still has no `/dev/subsys_esoc0` or `/dev/subsys_modem` fd hold |
| v861 | helper v133 accepts `vendor_per_mgr` exec targets for `pm-service`/`pm-proxy`, but runtime `attr/current` stays `kernel`; still no subsystem fd hold |
| v862 | Android init contract classifier: `vendor.per_mgr` has `ioprio rt 4`, `vendor.per_proxy` is property-started, and Android starts `vendor.per_proxy_helper`; next is read-only `pm_proxy_helper.rc` capture |
| v863 | live read-only `pm_proxy_helper.rc` capture: `vendor.per_proxy_helper /vendor/bin/pm_proxy_helper`, `class core`, `system:system`, `disabled`, `oneshot`, started at `post-fs-data`; current `sda29` dev is `259:13` |
| v864 | host-only helper-support classifier: current helper has runtime domain/fd capture but lacks `pm_proxy_helper`, `per_proxy_helper` SELinux mapping, `ioprio rt 4`, `init.svc.vendor.per_mgr=running`, and shutdown-stop contract support |
| v865 | helper v134 source/build-only: adds `pm_proxy_helper`, `per_proxy_helper` SELinux mapping, `per_mgr` `ioprio rt 4`, `init.svc.vendor.per_mgr=running` proxy gate, and shutdown-stop markers; static ARM64 build passes |
| v866 | helper v134 deploy-only: serial 1850-byte chunk deploy to `/cache/bin/a90_android_execns_probe`; remote sha/version/mode, selftest, and actor-clean state pass |
| v867 | PM init-contract start-only: mode/ioprio/lifecycle markers execute, but runtime domains stay `kernel`, no subsystem fd hold appears, and `pm_proxy_helper` remains D-state until native reboot cleanup |
| v868 | PM/eSoC contract classifier: `pm_proxy_helper` alone is closed; local A90 OSRC requires `/dev/esoc-0` CMD/REQ engine preflight (`ESOC_REG_REQ_ENG=7`, `ESOC_REG_CMD_ENG=8`) before another `/dev/subsys_esoc0` hold |
| v869 | helper v135 source/build-only: adds `wifi-companion-esoc-control-preflight`, local eSoC UAPI markers, `--allow-esoc-control-preflight`, and fail-closed markers with static ARM64 build pass |
| v870 | helper v135 deploy-only: serial deploy to `/cache/bin/a90_android_execns_probe`; remote sha/version/mode, selftest, actor-clean, and Wi-Fi-link-clean pass |

### Safety additions (Wi-Fi research)

- `esoc0` raw open **blocked** — blocks in `__subsystem_get(esoc0)`, requires reboot
- No DSP boot node writes without explicit approval (V615 kernel warning incident)
- No `wlan.ko` load/unload without explicit approval
- `firmware_class.path` rollback value: `/vendor/firmware_mnt/image`
- `sda29` mount must be read-only in all proof windows
- Current Wi-Fi gate after V857: Android proves the stock kernel/hardware can
  bring mdm3/mss `ONLINE`, publish WLAN-PD, download BDF, and create `wlan0`,
  and it identifies the lower actors: `mdm_helper`/`ks` hold `/dev/esoc-0`,
  while `pm-service` holds `/dev/subsys_esoc0` and `/dev/subsys_modem`.
  Native can materialize and clean up Android-equivalent `/dev/esoc-0`,
  `/dev/subsys_esoc0`, and `/dev/subsys_modem` nodes, and can start
  service-manager trio plus `pm-service`/`pm-proxy` under that node parity.
  However, native `pm-service` did not prove `/dev/subsys_esoc0` or
  `/dev/subsys_modem` fd holds even after the observed
  `vendor.peripheral.shutdown_critical_list` values were allowed by the private
  property shim. V858 then added the service-specific `pm-service`/`pm-proxy`
  property-context delta, V859 proved those target denials are gone, and V860
  merged the V858/V859/V677 property sets into one private superset. V860 replay
  has `property_denials.total=0` but still no `/dev/subsys_esoc0` or
  `/dev/subsys_modem` fd hold from `pm-service`. V861 added helper-side
  `vendor_per_mgr` exec targets for `pm-service`/`pm-proxy`; the target writes
  were accepted, but runtime `attr/current` remained `kernel`, `pm-service`
  exited `0`, `pm-proxy` exited `1`, and subsystem fd holds were still absent.
  V862 then classified Android init lifecycle gaps: `vendor.per_mgr` has
  `ioprio rt 4`, `vendor.per_proxy` is disabled and starts only after
  `init.svc.vendor.per_mgr=running`, shutdown stops `vendor.per_proxy`, and
  Android starts `vendor.per_proxy_helper` from `pm_proxy_helper.rc`. V863 then
  captured that rc read-only: `vendor.per_proxy_helper` runs
  `/vendor/bin/pm_proxy_helper`, `class core`, `user system`, `group system`,
  `disabled`, `oneshot`, and starts from `on post-fs-data`. Current `sda29`
  major/minor is `259:13`; do not reuse older hardcoded `259:22`.
  V864 then classified helper support host-only. Runtime domain and fd capture
  primitives already existed, but the helper still lacked `pm_proxy_helper`
  child modelling, `/vendor/bin/pm_proxy_helper` SELinux mapping,
  `vendor.per_mgr` `ioprio rt 4`, `init.svc.vendor.per_mgr=running` lifecycle,
  and explicit shutdown-stop semantics for `vendor.per_proxy`. V865 added those
  pieces to helper `v134` and built a static ARM64 artifact; the post-build
  classifier now shows all source support markers present. V866 then deployed
  helper `v134` to `/cache/bin/a90_android_execns_probe` by serial 1850-byte
  chunks and proved the remote sha, usage marker, new mode token, selftest, and
  actor-clean state. The remaining gaps are live evidence questions: runtime
  `attr/current` previously stayed `kernel`, and `pm-service` has not yet
  proved `/dev/subsys_esoc0` or `/dev/subsys_modem` fd holds. The next gate is
  V867 then ran the bounded PM init-contract mode. The helper markers executed:
  `pm_proxy_helper`, `per_mgr` `ioprio rt 4`, `init.svc.vendor.per_mgr=running`,
  property-gated `per_proxy`, and shutdown-stop markers were observed. However
  runtime domains still read `kernel`, no subsystem fd hold appeared, and
  `pm_proxy_helper` remained in `Ds` state until a native reboot cleanup. The
  next gate is V868 host-only/read-only classification of `pm_proxy_helper`
  blocking behavior and SELinux transition semantics. V868 then tied the
  D-state to the missing `/dev/esoc-0` CMD/REQ engine side of the Android eSoC
  contract and closed `pm_proxy_helper`-alone retries. V869 then added helper
  `v135` with a source/build-only `wifi-companion-esoc-control-preflight` mode
  and fail-closed markers. The next candidate is V870 deploy-only for helper
  `v135` with checksum/version/mode proof and post-deploy health. V870 deployed
  helper `v135` successfully; remote sha/mode marker, selftest, actor-clean, and
  Wi-Fi-link-clean pass. The next candidate is V871 bounded live eSoC control
  preflight, limited to node visibility and read-only eSoC status ioctls. Keep
  Wi-Fi HAL, scan/connect, DHCP/routes, credentials, external ping, live
  `ESOC_PWR_ON`, subsystem writes, GPIO/sysfs/debugfs writes, module
  load/unload, and boot image writes blocked. Do not start `mdm_helper`, `ks`,
  HAL, or scan/connect before a separate mutating eSoC state-machine gate.

## Docs structure

```
docs/plans/NATIVE_INIT_vNNN_*_PLAN_*.md   # per-cycle plan
docs/reports/NATIVE_INIT_vNNN_*_*.md      # per-cycle execution report
docs/operations/                           # runbooks, flash guide, versioning policy
docs/security/scans/                       # security scan results
```

Plans and reports are append-only historical records. Update `docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md` with cycle state after each completion.
