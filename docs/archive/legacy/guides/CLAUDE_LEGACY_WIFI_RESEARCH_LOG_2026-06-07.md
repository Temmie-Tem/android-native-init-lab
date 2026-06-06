# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Samsung Galaxy A90 5G (SM-A908N) — stock Android Linux kernel 4.14.190, custom static `/init` as PID 1, building a minimal embedded Linux console without Android userspace. Device flashed via TWRP, controlled over USB CDC ACM serial bridge.

- **Device**: SM-A908N, Android 12, Magisk 30.7, TWRP available
- **Current native build**: `A90 Linux init 0.9.68 (v724)` — `stage3/boot_linux_v724.img`
- **Known-good fallback**: `stage3/boot_linux_v48.img`
- **Active research cycle**: V1594/V1595 source-build + artifact sanity PASS. Helper `a90_android_execns_probe v295` adds `--allow-android-wifi-service-window-pm-first-route`; the V1594 test boot preserves V1591 firmware mounts but switches to PM-first ordering (`pm_proxy_helper`, `per_mgr`, `pm-proxy`, `mdm_helper`, `cnss-daemon`) with no Wi-Fi HAL/wificond before PM-service-owned `/dev/subsys_esoc0` observation, direct scoped trigger still disabled, and explicit `pm-service-owned-powerup-observed` / `pm-service-owned-powerup-missing` classification. Boot image `tmp/wifi/v1594-pm-first-lower-marker-test-boot/boot_linux_v1594_wifi_test.img` has sha256 `86ec9d6fbce5ac56e70815cac7aa1dc1a45aee1d5dd8a0fb53f81dc7c4d44417`; V1595 artifact sanity passed. Next gate: V1596 rollbackable live handoff of only this V1594 image, then rollback to v724/selftest. Keep credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan, platform bind/unbind, or unbounded boot image/partition write blocked.
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

Boot image packaging uses `workspace/public/src/third_party/mkbootimg/` tools. See `NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md`.

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

## Wi-Fi bring-up research state (v598–v895, active)

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
| v871 | bounded eSoC preflight attempt exposed helper v135 classification bug: mode was treated as service-manager/SELinuxfs runtime before reaching read-only ioctl body |
| v872 | helper v136 source/build-only: splits eSoC control preflight from service-manager/SELinuxfs classification while preserving private eSoC node materialization |
| v873 | helper v136 deploy-only: serial deploy to `/cache/bin/a90_android_execns_probe`; remote sha/version/mode pass, no actor start and no Wi-Fi bring-up |
| v874 | bounded eSoC read-only control preflight pass: `/dev/esoc-0` opened, `GET_STATUS`/`GET_ERR_FATAL` rc 0, `GET_LINK_ID` errno 22; no mutating ioctl or actor start |
| v875 | host-only eSoC state-machine classifier: selects helper-only CMD/REQ registration support as V876; no live contact or mutating ioctl |
| v876 | helper v137 source/build-only: adds fail-closed `wifi-companion-esoc-engine-register-preflight` mode and allow flag; no deploy or live ioctl |
| v877 | helper v137 deploy-only: serial deploy to `/cache/bin/a90_android_execns_probe`; remote sha/mode marker, selftest, actor-clean, and Wi-Fi-link-clean pass |
| v878 | bounded eSoC engine registration preflight: `REG_REQ_ENG` rc0, `REG_CMD_ENG` errno16/EBUSY; no `CMD_EXE`/`PWR_ON`, no actor start, cleanup and health pass |
| v879 | host-only CMD engine classifier: direct userspace `CMD_EXE` remains blocked; next is helper v138 source/build-only REQ-registered subsystem-hold support |
| v880 | helper v138 source/build-only: adds fail-closed REQ-registered subsystem-hold mode and repairs stale open errno reporting |
| v881 | helper v138 deploy-only: serial deploy pass; remote sha/mode marker, selftest, actor-clean, and Wi-Fi-link-clean pass; next is passive WAIT_FOR_REQ observer source build |
| v882 | helper v139 source/build-only: adds passive `ESOC_WAIT_FOR_REQ` observer child and reboot-required cleanup markers; no deploy or live eSoC ioctl |
| v883 | helper v139 deploy-only: serial deploy pass; remote sha/mode marker, selftest, actor-clean, and Wi-Fi-link-clean pass; next is bounded live REQ-registered subsystem-hold observer |
| v884 | REQ-registered subsystem-hold live gate: `REG_REQ_ENG rc0`, passive `ESOC_WAIT_FOR_REQ rc4 value1` = `ESOC_REQ_IMG`, `/dev/subsys_esoc0` remained D-state and recovery reboot restored health |
| v885 | host-only ESOC_REQ_IMG response classifier: V884 `WAIT_FOR_REQ rc4 value1` is request evidence, not ioctl failure; next is helper v140 semantic repair and guarded response scaffold |
| v886 | helper v140 source/build-only: repairs `WAIT_FOR_REQ` byte-count semantics, labels `ESOC_REQ_IMG`, and adds fail-closed response scaffold markers; no deploy or live notify |
| v887 | helper v140 deploy-only: serial chunk 3000 blocked safely before writes, chunk 1850 deploy passed; remote sha/mode marker verified, no live eSoC ioctl or Wi-Fi bring-up |
| v888 | host-only response gate classifier: choose `ESOC_IMG_XFER_DONE` first, then readiness-gated `ESOC_BOOT_DONE`; blind BOOT_DONE remains blocked |
| v889 | helper v141 source/build-only: adds fail-closed conditional response mode and allow flag; no deploy or live notify |
| v890 | helper v141 deploy-only: serial deploy pass; remote sha/mode marker, selftest, actor-clean, and Wi-Fi-link-clean pass; no live eSoC ioctl |
| v891 | bounded conditional response proof: first v141 attempt failed allowlist before live action; v142 rerun sent `ESOC_IMG_XFER_DONE`, `GET_STATUS` stayed 0, no `BOOT_DONE`, cleanup reboot pass |
| v892 | helper v142 allowlist repair/deploy: adds conditional response mode to global v235 allowlist; deploy-only pass |
| v893 | host-only post-image-done classifier: `IMG_XFER_DONE` is not a readiness setter; next blocker is MDM2AP status/ready transition |
| v894 | MDM2AP ready-surface classifier: `/proc/interrupts` exposes GPIO 142 `mdm status` as read-only observer; debugfs GPIO absent |
| v895 | MDM2AP IRQ snapshot proof: `IMG_XFER_DONE` sent, `GET_STATUS` stayed 0, GPIO142 `mdm status` IRQ count stayed 0; cleanup reboot pass |
| v896 | host-only Android contract classifier: Android reaches `mdm3=ONLINE`/WLFW/BDF/`wlan0` while `mdm_helper` and `ks` hold `/dev/esoc-0` |
| v897 | host-only native helper delta: helper lacked pre-subsys `mdm_helper`/`ks` image-contract mode and MHI pipe observation |
| v898 | helper v144 source/build-only: adds fail-closed `mdm_helper` before `/dev/subsys_esoc0` contract mode; no deploy/live action |
| v899 | helper v144 deploy-only: serial deploy pass; remote sha/mode marker, selftest, actor-clean, and Wi-Fi-link-clean pass |
| v900 | bounded live `mdm_helper`/`ks` contract: after v145 repair, `mdm_helper` observable, `/dev/subsys_esoc0` open child blocked, no `ks`/MHI/GPIO142 progress; cleanup reboot pass |
| v901 | helper v145 allowlist repair/deploy: adds mdm_helper/ks mode to global v235 allowlist and deploys repaired helper |
| v902 | helper v146 blocker capture: blocked child wchan=`mdm_subsys_powerup`, D-state stack captured, native `mdm_helper` did not hold `/dev/esoc-0`; cleanup reboot pass |
| v903 | helper v147 mdm_helper direct capture (no subsys trigger): mdm_helper observable, no `/dev/esoc-0`/MHI fd, no `ks`, `kernel` context; clean postflight without reboot |
| v904 | host-only Android/native parity classifier: Android runs `vendor_mdm_helper:s0` with esoc-0+ks+MHI; native stays `kernel` context; selected PM service observer as next path |
| v905–v1179 | PM service observer framework development: vndservice gate design, per_mgr/per_proxy ordering, SELinux domain probes; multiple helper versions (v200–v220) and script iterations |
| v1180 | live PASS: per_proxy starts within pph+247ms; per_mgr subsys_modem fd hold confirmed |
| v1181 | host-only: per_mgr self-exit race classified; per_proxy skipped when per_mgr exits before vndservice ready |
| v1182 | source/build: per-proxy-after-vndservice-provider mode added (helper v219) |
| v1183 | live FAIL: vndservice gate placed after per_proxy spawn — design bug; log-only |
| v1184 | host-only PASS: gate position + parse bug fixed |
| v1185 | live FAIL: gate timeout after fix; per_proxy_skipped=1 — per_mgr exits before gate |
| v1186–v1187 | host-only + live: per_mgr domain=`kernel` confirmed; grep-filter fix (helper v223) |
| v1188–v1190 | setcurrent SELinux domain fix iterations; precompiled policy load fix (helper v224–v225) |
| v1191 | live PASS: per_mgr domain=`u:r:vendor_per_mgr:s0` in 30ms with precompiled policy load |
| v1192 | host-only: per_mgr PM IPC confirmed; subsys_modem fd hold observed post-per_proxy |
| v1193 | helper v226 mdm_helper-before-cnss mode; live: subsys_esoc0 crash classified as expected reboot |
| v1194 | helper v228: subsys_esoc0 power-on trigger + stdout flush fix; v1194 live script |
| v1195–v1196 | live FAIL: SAMPLE_COUNT!=0 → /proc/maps serial flood → timeout before child_summary; data lost |
| v1197 | live FAIL: `--pm-observer-trigger-pcie-enumerate` writes to PCIe RC1 → kernel panic/reboot mid-run; tail -f fix needed |
| v1198 | live PASS: PCIe flag removed, `tail -f "$CHILD_LOG"` streaming fix (v1106 collector); 10 status entries captured; `sdx50m_toggle_soft_reset` at t=0ms; mdm_helper thread in `esoc_dev_ioctl` at t=0ms then `SyS_nanosleep`; `mdm_helper_fds=none`; GPIO 142 count=0; mdm3 OFFLINING; next is MHI observation + mdm_helper SELinux context probe |
| v1199–v1204 | PM service observer framework iterations: dep_flag timing via per_proxy pph+1-2s, pph+5s, pph+20s; all fail — pm-service always opens modem not esoc0 |
| v1205 | live PASS: per_proxy at pph+20s (timing confirmed); pm-service opens subsys_modem not subsys_esoc0; per_mgr_esoc0_any=False; tracefs uprobes hit_count=0; cnss_vndbinder_any=False; root cause: dep+0x40 = mss state ONLINE before per_mgr |
| v1206 | host/build: helper v244 adds `--pm-observer-defer-modem-holder-pph-ms`; Python script `native_wifi_pm_per_mgr_before_modem_holder_v1206.py` skips Python modem holder and defers to helper at pph+16s |
| v1207 | host-only PASS: three-way dep+0x40 comparison closes mss/mdm3 state as dep source; dep decision is made BEFORE per_proxy; V1205/V1206 identical mss/mdm3 at per_proxy time yet different dep → dep set earlier |
| v1208 | live PASS: helper v245 single 300ms pm_proxy_helper probe; pph alive=1 state=S wchan=SyS_nanosleep modem=1 esoc0=0; pph opens subsys_modem only (fd=3); ESOC GET_LINK_ID hypothesis closed |
| v1209 | live PASS: helper v246 multi-sample pph probe (300ms/1s/3s/5s); pph stays SyS_nanosleep modem=1 esoc0=0 across all samples; pph is pure subsys_modem pre-holder; dep+0x40 is internal to per_mgr, not delegated to pph |
| v1210 | live PASS: V1106 tracefs uprobes capture cnss-daemon pm_client_register peripheral='modem' (not 'SDX50M'); per_mgr opens only subsys_modem; subsys_esoc0/MDM never triggered; next: why cnss-daemon uses 'modem' not 'SDX50M' |
| v1211 | live PASS: libmdmdetect.so esoc_framework_supported() checks /dev/esoc* existence; /dev/esoc-0 absent in native (major=484 minor=0) → peripheral='modem'; /sys/bus/esoc/devices/esoc0/esoc_name=SDX50M confirmed; next: mknod /dev/esoc-0 c 484 0 before cnss-daemon → verify peripheral='SDX50M' |
| v1212 | live FAIL: /dev/esoc-0 already present in private namespace (EEXIST, pre-created by materialize_peripheral_manager_node_parity); cnss-daemon still uses peripheral='modem'; root cause: libmdmdetect esoc_framework_supported() checks /sys/class/esoc-dev/ not /dev/esoc-0 existence; /sys/class/esoc-dev/ absent from private chroot (not bind-mounted in PM observer mode) |
| v1213 | helper v248: bind-mount /sys/class/esoc-dev/ in materialize_rmt_modem_detect_surface(); deploy and verify peripheral='SDX50M' |
| v1214 | live FAIL: /sys/class/esoc-dev/ bound + /dev/esoc-0 chmod 0666; cnss-daemon still peripheral='modem'; esoc_framework_supported() check is not the real gate; V1215: disassemble libmdmdetect + cnss-daemon to find actual pm_client_register match logic |
| v1215 | host-only PASS: full disassembly of libmdmdetect.so + cnss-daemon; get_system_info() two-phase scan: esoc bus (SDX50M type=0) + msm_subsys "modem" (type=1); cnss-daemon first pm_client_register(type=1) -> modem; second call(type=0+"SDXPRAIRIE") -> SDX50M!=SDXPRAIRIE no match; fix: fake esoc_name="SDXPRAIRIE" bind mount |
| v1216 | live FAIL: helper v250 deploy PASS and fake esoc_name bind_rc=0/content=SDXPRAIRIE, but cnss-daemon still registered peripheral='modem'; per_mgr_esoc0_any=False, mdm_subsys_powerup_any=False, wlan0_up=False; next V1217 must prove exact libmdmdetect read path inside chroot before another PM/CNSS trigger |
| v1217 | live PASS: helper v252 readback-only proof confirmed direct platform esoc_name and /sys/bus/esoc/devices/esoc0/esoc_name both read SDXPRAIRIE inside the private namespace; /sys/class/esoc-dev opendir_rc=0 count=1; daemon/service-manager/HAL/scan/connect/credentials/DHCP/external-ping all 0; next V1218 bounded PM/CNSS observer must require cnss-daemon peripheral='SDXPRAIRIE' and per_mgr subsys_esoc0 |
| v1218 | live FAIL: helper v252 PM/CNSS observer kept positive SDXPRAIRIE readback, but cnss-daemon still registered only peripheral='modem'; no SDXPRAIRIE PM client, no persistent per_mgr subsys_esoc0 fd, no mdm_subsys_powerup/WLFW/wlan0; cleanup dmesg showed subsystem_put(esoc0) count:0 reference mismatch but selftest fail=0; next V1219 trace/classify cnss-daemon/libmdmdetect selection after get_system_info |
| v1219 | live FAIL: cnss-daemon/libmdmdetect trace proved second vote type=0 name=SDXPRAIRIE is called, but libmdmdetect output visible to that loop contains only type=1 name=modem; strcmp against SDXPRAIRIE is never reached; fake esoc_name removes the type-0 entry via supported-eSoC filtering; next V1220 host/build-only private cnss-daemon selection literal patch candidate |
| v1220 | host PASS: private cnss-daemon artifact patches only the single SDXPRAIRIE literal at 0x6cd4 to C string SDX50M; size unchanged, 4 byte deltas, output sha256 784fd7bd9b602d8e1f94c9ceef977845909f452611025c40fda589d0e57de5fd; next V1221 helper live gate to bind/execute private patched binary in namespace only |

### Safety additions (Wi-Fi research)

- `esoc0` raw open **blocked** — blocks in `__subsystem_get(esoc0)`, requires reboot
- No DSP boot node writes without explicit approval (V615 kernel warning incident)
- No `wlan.ko` load/unload without explicit approval
- `firmware_class.path` rollback value: `/vendor/firmware_mnt/image`
- `sda29` mount must be read-only in all proof windows
- Current Wi-Fi gate after V1220: helper live gate for private patched cnss-daemon.
  V1215 host-only PASS disassembled libmdmdetect.so + cnss-daemon and found:
  `get_system_info()` finds SDX50M (type=0) from esoc bus scan AND "modem" (type=1)
  from msm_subsys scan (`/sys/bus/msm_subsys/devices/subsys0/name="modem"` →
  `get_subsystem_info` fills esoc slot with type=1 name="modem"). cnss-daemon first
  `pm_client_register` call looks for type=1 → finds "modem" → peripheral='modem' →
  per_mgr opens subsys_modem. Second call looks for type=0 + strcmp with "SDXPRAIRIE"
  (hardcoded in cnss-daemon binary) → never matches SDX50M. V1216 tested a fake
  esoc_name file containing "SDXPRAIRIE" bound over the mdm3 platform esoc_name path;
  bind_rc was 0, but cnss-daemon still registered only `peripheral='modem'`.
  V1217 added helper v252 readback-only proof and confirmed both the direct
  platform path and `/sys/bus/esoc/devices/esoc0/esoc_name` read `SDXPRAIRIE`
  before daemon start, with `/sys/class/esoc-dev` enumerable. V1218 reran the
  bounded PM/CNSS observer with the same positive readback and still saw only
  `peripheral='modem'`, no `SDXPRAIRIE` PM client, no persistent per_mgr
  `/dev/subsys_esoc0`, no MDM/WLFW/`wlan0`. V1219 traced the selection path:
  second vote `type=0 name=SDXPRAIRIE` is called, but `get_system_info()` output
  visible to that loop contains only `type=1 name=modem`; `strcmp` against
  `SDXPRAIRIE` is never reached. The fake `esoc_name=SDXPRAIRIE` bind is
  rejected by libmdmdetect's supported-eSoC filtering before type-0 output is
  filled. V1220 created a host-only private `cnss-daemon` artifact that changes
  only the runtime selection literal from `SDXPRAIRIE` to real supported
  `SDX50M`; file size is unchanged and only four bytes differ. V1221 should add
  a helper live gate that uses that private binary inside the namespace without
  vendor partition writes, then requires type-0 PM registration and
  `per_mgr` `/dev/subsys_esoc0` evidence before any HAL/scan/connect work.
  Scripts: `native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210.py` (V1210 run),
  `native_wifi_cnss_daemon_peripheral_name_v1211.py` (V1211 run).
  Key V1198 findings: (1) subsys_esoc0 open triggers `sdx50m_toggle_soft_reset`;
  (2) mdm_helper in `esoc_dev_ioctl` at t=0ms (ESOC_REQ_IMG received); (3) GPIO 142
  stays 0; (4) mdm3 OFFLINING; subsys_esoc0 child blocks in `mdm_subsys_powerup`.
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
  Wi-Fi-link-clean pass. V871 then exposed a helper classification bug before
  the read-only ioctl body. V872 fixed that by splitting helper `v136` eSoC
  preflight from service-manager/SELinuxfs runtime classification, V873 deployed
  helper `v136`, and V874 proved `/dev/esoc-0` read-only control preflight:
  `GET_STATUS`/`GET_ERR_FATAL` returned rc `0`, `GET_LINK_ID` returned errno
  `22`, created nodes were cleaned up, selftest stayed fail0, and actor/Wi-Fi
  surfaces stayed clean. V875 then classified the eSoC state machine host-only and selected V876
  helper `v137` source/build-only CMD/REQ registration support. V876 added the
  fail-closed `wifi-companion-esoc-engine-register-preflight` mode and
  `--allow-esoc-engine-register-preflight` flag without deploy or live ioctl.
  V877 then deployed helper `v137` to `/cache/bin/a90_android_execns_probe` by
  serial appendfile/uudecode; remote sha/mode marker, selftest fail0,
  actor-clean, and Wi-Fi-link-clean passed. V878 ran the bounded live
  CMD/REQ registration preflight: `REG_REQ_ENG` returned rc `0`, `REG_CMD_ENG`
  returned errno `16` (`EBUSY`), helper fds closed, cleanup/selftest/actor-clean
  stayed good, and no `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`, `NOTIFY`,
  `/dev/subsys_esoc0` open, actors, or Wi-Fi bring-up occurred. Next is V879
  host-only classification of CMD engine ownership, eSoC client hooks, and the
  next safe subsystem-powerup guardrails. V879 classified direct userspace
  `CMD_EXE` as blocked because command-engine ownership was not acquired, while
  `REG_REQ_ENG rc0` makes a REQ-registered subsystem-open helper mode the next
  source/build-only candidate. V880 added helper `v138`, repaired stale
  successful-open errno reporting, and added fail-closed
  `wifi-companion-esoc-req-registered-subsys-hold-preflight` support. Static
  ARM64 build passed with sha256
  `2ac8c6730768f86a221722a6ff259e3a4617134221498bd1956a63980a22a9b5`; no
  deploy, device contact, live eSoC ioctl, `/dev/subsys_esoc0` open, actors, or
  Wi-Fi bring-up occurred. V881 deployed helper `v138` by serial appendfile;
  remote sha/mode marker, selftest fail0, actor-clean, and Wi-Fi-link-clean
  passed, with no live eSoC ioctl, no `/dev/subsys_esoc0` open, no actors, and
  no Wi-Fi bring-up. Follow-up source analysis corrects the next route:
  `CMD_ENG` ownership is not required for initial subsystem powerup, while
  `REG_REQ_ENG` is the important precondition, and SDX50M may not emit
  `ESOC_REQ_IMG`. V882 then added helper `v139` source/build-only passive
  `ESOC_WAIT_FOR_REQ` observer support and kill/reboot-required cleanup markers;
  static build passed with sha256
  `077ced65ae5b0b546ecdf3b1bb0c808d3ec34bfa2462516e6ceba170b18f23c5`, with no
  deploy, device contact, live eSoC ioctl, subsystem open, actors, or Wi-Fi
  bring-up. V883 then deployed helper `v139` by serial appendfile; remote
  sha/mode marker, selftest fail0, actor-clean, and Wi-Fi-link-clean passed,
  with no live eSoC ioctl, no `/dev/subsys_esoc0` open, no actors, and no
  Wi-Fi bring-up. Next is V884 bounded live REQ-registered subsystem-hold
  observer preflight: rely on `REG_REQ_ENG`, record passive
  `ESOC_WAIT_FOR_REQ`, and treat absent `ESOC_REQ_IMG` as diagnostic data rather
  than immediate failure. V884 then proved `REG_REQ_ENG` succeeds and
  `ESOC_WAIT_FOR_REQ` returns rc `4`, errno `0`, value `1`. Local OSRC maps this
  to copied `sizeof(u32)` plus `ESOC_REQ_IMG`, so SDX50M does emit the image
  request in this path. `/dev/subsys_esoc0` remained blocked in D-state because
  native did not answer the request with Android-equivalent image
  transfer/notify handling; recovery reboot restored native v724 health and
  selftest fail0. V885 then classified the request contract host-only:
  `WAIT_FOR_REQ rc=4 errno=0 value=1` is request evidence, local OSRC exposes
  `ESOC_IMG_XFER_DONE` and `ESOC_BOOT_DONE`, and the next gate is V886 helper
  `v140` source/build-only semantic repair plus guarded response scaffold. V886
  built helper `v140`; passive `WAIT_FOR_REQ` now treats copied `sizeof(u32)`
  byte counts as `request-observed`, labels value `1` as `ESOC_REQ_IMG`, and
  exposes fail-closed `ESOC_IMG_XFER_DONE`/`ESOC_BOOT_DONE` response scaffold
  markers without executing live notify. V887 then deployed helper `v140`;
  serial chunk `3000` failed line-safety before writes, chunk `1850` installed
  the helper, and remote sha/mode marker verification passed. Next is V888
  host-only response-gate classifier before any live `ESOC_NOTIFY`. V888 then
  classified the gate: respond to `ESOC_REQ_IMG` first with
  `ESOC_IMG_XFER_DONE`, poll `ESOC_GET_STATUS` or equivalent readiness, and
  send `ESOC_BOOT_DONE` only after readiness is proven. Next is V889 helper
  `v141` source/build-only conditional response mode. V889 then built helper
  `v141` with mode `wifi-companion-esoc-conditional-response-preflight` and
  allow flag `--allow-esoc-conditional-response-preflight`; no deploy or live
  notify occurred. V890 then deployed helper `v141` to
  `/cache/bin/a90_android_execns_probe` and verified remote sha/mode marker,
  selftest, actor-clean, and Wi-Fi-link-clean state without live eSoC ioctl.
  V891 initially failed before live eSoC action because helper `v141` omitted
  the conditional response mode from the global v235 allowlist. V892 repaired
  and deployed helper `v142`. The repaired V891 live proof observed
  `ESOC_REQ_IMG`, sent `ESOC_IMG_XFER_DONE` with rc `0`, then polled
  `ESOC_GET_STATUS` 87 times with value `0`; `ESOC_BOOT_DONE` was not sent.
  Cleanup reboot restored healthy native selftest. V893 then classified this as
  a post-image-done MDM2AP status/ready transition blocker: `IMG_XFER_DONE`
  schedules status checking but does not directly set ready. Next is a bounded
  readiness observer, not blind `BOOT_DONE` or actor/HAL start. V894 selected
  `/proc/interrupts` line `msmgpio-dc 142 Edge mdm status` as the read-only
  observer for that transition; debugfs GPIO is absent in current native boot.
  V895 built and deployed helper `v143`, then reran the guarded
  `IMG_XFER_DONE` flow with IRQ snapshots. `ESOC_REQ_IMG` was observed,
  `IMG_XFER_DONE` was sent, `GET_STATUS` stayed `0` for 86 polls, `BOOT_DONE`
  was not sent, and GPIO 142 `mdm status` IRQ count stayed `0` across 89
  phases. Cleanup reboot restored healthy selftest. Next is host-only Android
  `mdm_helper` / image-transfer contract classification before any new live
  mutating eSoC state-machine attempt. V896 then classified that contract
  host-only: Android reaches `mdm3=ONLINE`, WLFW/BDF/`wlan0`, and GPIO 142
  IRQ count `1` while `mdm_helper` plus `ks` hold `/dev/esoc-0`; `ks` uses
  `/dev/mhi_0305_01.01.00_pipe_10`, and `pm-service` holds
  `/dev/subsys_esoc0` plus `/dev/subsys_modem`. Existing Android dmesg/IRQ
  evidence was sufficient, so no Magisk module or new Android boot was needed.
  V897 then classified the native helper delta host-only: helper `v143` still
  has only old service-gated `mdm_helper` modes and lacks a distinct
  pre-subsys `mdm_helper`/`ks` image-contract mode, `/vendor/bin/ks`
  observation, `/dev/mhi_0305_01.01.00_pipe_10` visibility handling, and
  enforced `mdm_helper` before `/dev/subsys_esoc0` ordering. V898 then added
  helper `v144` source/build-only support for
  `wifi-companion-mdm-helper-ks-image-contract-preflight` with
  `--allow-mdm-helper-ks-contract-preflight`: the mode materializes eSoC/subsys
  nodes, starts `/vendor/bin/mdm_helper` before `/dev/subsys_esoc0`, observes
  `/vendor/bin/ks` and `/dev/mhi_0305_01.01.00_pipe_10`, and still blocks
  controller-side `REG_REQ_ENG`, `ESOC_NOTIFY`, and `BOOT_DONE`. Static ARM64
  build passed with sha256
  `c7b02320f143f57a837b5f1cf8af17258307439be3b8969dc33000735116ce4e`. V899
  then deployed helper `v144` to `/cache/bin/a90_android_execns_probe` by
  serial appendfile/uudecode (`788` chunks) and postdeploy preflight proved
  remote sha/mode parity, selftest fail0, service-manager-clean, and
  Wi-Fi-link-clean state. The first V900 live attempt then failed before live
  action because helper `v144` omitted the new mode from the global v235
  allowlist. V901 repaired this in helper `v145`, deployed it, and proved
  remote parity. Repaired V900 then started `/vendor/bin/mdm_helper`, observed
  it, and attempted `/dev/subsys_esoc0` only after that gate opened. The
  trigger child blocked and could not be reaped after TERM/KILL, so V900
  correctly classified `reboot-required`; cleanup reboot restored
  `selftest fail=0`. No `ks`, MHI pipe, GPIO 142 IRQ, `mdm3=ONLINE`, WLFW/BDF,
  or `wlan0` progress was observed. V902 then deployed helper `v146` and
  captured the blocked child: `wchan=mdm_subsys_powerup`, state `D`, stack
  `mdm_subsys_powerup -> __subsystem_get -> subsys_device_open -> ... ->
  SyS_openat`. It also showed native `mdm_helper` itself did not hold
  `/dev/esoc-0`; only tty, pipes, and one socket were visible. V903 then
  deployed helper `v147` and captured `mdm_helper` directly without opening
  `/dev/subsys_esoc0`: `mdm_helper` was observable but held no `/dev/esoc-0`,
  `/dev/subsys_esoc0`, or MHI pipe fd, spawned no `/vendor/bin/ks`, and
  postflight was clean without reboot. V904 then classified the Android/native
  parity gap host-only: Android runs `vendor.mdm_helper` as
  `u:r:vendor_mdm_helper:s0` after `vendor.per_mgr=running`, `pm-service` owns
  `/dev/subsys_esoc0` and `/dev/subsys_modem`, `mdm_helper` owns
  `/dev/esoc-0`, and `ks` reaches `/dev/mhi_0305_01.01.00_pipe_10`; native
  V903 direct `mdm_helper` stays in `kernel` context with tty/pipe/socket fds
  only. Next is V905 fail-closed runtime-input repair design around
  SELinux/init service context, `pm-service` ordering, properties, sockets, and
  environment before any subsystem-open retry. Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, and external ping remain blocked until lower
  readiness is proven.
  Keep Wi-Fi HAL, scan/connect, DHCP/routes, credentials, external ping, live
  direct userspace `CMD_EXE`/explicit userspace `PWR_ON`, `NOTIFY`, subsystem
  writes, GPIO/sysfs/debugfs writes, module load/unload, and boot image writes
  blocked. Do not start `mdm_helper`, `ks`, HAL, or scan/connect before a
  separate mutating eSoC state-machine gate.

## Docs structure

```
docs/plans/NATIVE_INIT_vNNN_*_PLAN_*.md   # per-cycle plan
docs/reports/NATIVE_INIT_vNNN_*_*.md      # per-cycle execution report
docs/operations/                           # runbooks, flash guide, versioning policy
docs/security/scans/                       # security scan results
```

Plans and reports are append-only historical records. Update `docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md` with cycle state after each completion.

## Latest native Wi-Fi state: V1221 (2026-05-31)

V1221 deployed helper `a90_android_execns_probe v253` and private artifact `/cache/bin/cnss-daemon.sdx50m` (`784fd7bd9b602d8e1f94c9ceef977845909f452611025c40fda589d0e57de5fd`). The bounded live gate passed as `v1221-sdx50m-per-mgr-esoc0`: private bind `rc=0`, CNSS PM registrations included `modem` and `SDX50M`, and dmesg showed `pm-service` reaching `__subsystem_get(): esoc0 count:0`. No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, or vendor partition write occurred. `mdm3` still remained `OFFLINING`; WLFW service 69/BDF/FW-ready/`wlan0` are still absent. Next gate should observe the post-`subsys_esoc0` power-up completion boundary before any Wi-Fi HAL or connect test.

## Latest native Wi-Fi state: V1224 (2026-05-31)

V1224 added `scripts/revalidation/native_wifi_mdm_helper_ks_mhi_parity_live_v1224.py` and ran the bounded private-CNSS `SDX50M` live path with lower-contract parsing. Result: `v1224-mdm-helper-esoc-present-ks-mhi-absent-crash` PASS. The native path now proves `mdm_helper` owns `/dev/esoc-0` and `pm-service` attempts `/dev/subsys_esoc0`, but `ks` and `/dev/mhi_0305_01.01.00_pipe_10` never appear before modem-down/crash markers. `mdm3` remains `OFFLINING`, WLFW/BDF/FW-ready/`wlan0` markers remain absent, and postflight health is clean: selftest `fail=0`, netservice stopped, no PM/CNSS/`mdm_helper`/`ks` actors left in `ps`. No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, flash, or partition write occurred. Next work is V1225: classify why native `mdm_helper` stays before Android's `ks`/MHI image-transfer path, focusing on eSoC ioctl/wchan state, MHI device creation, and Android timing around `ESOC_WAIT_FOR_REQ`, PCIe/MHI readiness, and `ks` spawn.

## Latest native Wi-Fi state: V1225 (2026-05-31)

V1225 added `scripts/revalidation/native_wifi_mdm_helper_wait_req_gap_classifier_v1225.py` and classified the V1224 lower evidence host-only. Result: `v1225-mdm-helper-post-wait-sleep-gap-classified` PASS. V1224 already proves `mdm_helper` owns `/dev/esoc-0` and `pm-service` enters `/dev/subsys_esoc0` at `mdm_subsys_powerup`, but `mdm_helper` threads are observed in `SyS_nanosleep`, not carrying a captured `ESOC_WAIT_FOR_REQ` value, and `ks`, `/dev/mhi_0305_01.01.00_pipe_10`, WLFW/BDF/FW-ready, and `wlan0` remain absent. V911/V1144 keep `ESOC_WAIT_FOR_REQ` as the earlier request-engine boundary, so the active blocker is the post-wait sleep/no-MHI branch. Next work is V1226: add a bounded lower-trace v2 live gate in the V1224 PM/CNSS path that traces `mdm_helper` syscall/returns from process start, captures the `ESOC_WAIT_FOR_REQ` result and subsequent open/exec/ioctl errors, and polls MHI pipe, MHI bus, PCIe link state, and `/vendor/bin/ks` before/after `pm-service` opens `/dev/subsys_esoc0`. Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, and partition writes blocked.

## Latest native Wi-Fi state: V1226 (2026-05-31)

V1226 added `scripts/revalidation/native_wifi_mdm_helper_lower_trace_v2_live_v1226.py` and reran the V1224 PM/CNSS path with helper `ptrace-lite` forced. Result: `v1226-ptrace-lite-perturbed-mdm-helper-window` PASS as an instrumentation-blocker classification. The broad capture mode changed the V1224 path: `mdm_helper` started but was not observable in the post-PM window, `pm-service` never attempted `/dev/subsys_esoc0`, `per_mgr` syscall tracing hit the stop limit, and no `mdm_helper` syscall or `ESOC_WAIT_FOR_REQ` record was captured. V1224 remains the valid behavioral baseline; V1227 should implement `mdm_helper`-only syscall tracing or compact helper-side `/dev/esoc-0`/`ESOC_WAIT_FOR_REQ` event capture without tracing earlier PM actors. No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, flash, or partition write occurred; postflight selftest remained fail0 and netservice was stopped.

## Latest native Wi-Fi state: V1227 (2026-05-31)

V1227 updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to v254 and added `--pm-observer-mdm-helper-only-syscall-trace`. Deploy wrapper `scripts/revalidation/wifi_execns_helper_v254_deploy_preflight_v1227.py` passed, and live runner `scripts/revalidation/native_wifi_mdm_helper_focused_trace_live_v1227.py` passed as `v1227-focused-ptrace-stops-mdm-helper-before-esoc`. The new flag successfully prevents earlier `per_mgr` syscall tracing, but pre-gate ptrace still stops `mdm_helper` before `/dev/esoc-0` opens: the observer sees `ptrace_stop`, fd count `0`, no selected syscall records, no `ESOC_WAIT_FOR_REQ`, no `ks`/MHI, and no WLFW/`wlan0`. V1228 should avoid pre-gate ptrace entirely by using delayed attach after `/dev/esoc-0` exists or compact non-ptrace helper-side eSoC event capture. No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, flash, or partition write occurred; postflight selftest remained fail0 and netservice was stopped.

## Latest native Wi-Fi state: V1228 (2026-05-31)

V1228 updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to v255 with non-ptrace early compact `/proc` sampling during the `mdm_helper` `/dev/esoc-0` polling window. Deploy wrapper `scripts/revalidation/wifi_execns_helper_v255_deploy_preflight_v1228.py` passed, and live runner `scripts/revalidation/native_wifi_mdm_helper_early_compact_trace_live_v1228.py` passed as `v1228-early-wait-for-req-observed-no-ks-mhi`. The native path now proves `mdm_helper` owns `/dev/esoc-0` and is blocked in `ioctl(ESOC_WAIT_FOR_REQ)` with `wchan=esoc_dev_ioctl`; `pm-service` attempts `/dev/subsys_esoc0`, but `ks`, `/dev/mhi_0305_01.01.00_pipe_10`, WLFW/BDF/FW-ready, and `wlan0` remain absent before modem-down/crash markers. The active blocker is the ESOC request/image-link handoff after `ESOC_WAIT_FOR_REQ`, specifically why native does not reach Android's `ks`/MHI transfer path. No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, flash, or partition write occurred; postflight selftest remained fail0 and netservice was stopped. V1229 should classify the `ESOC_WAIT_FOR_REQ` request/result contract and the missing `ks`/MHI transition.

## Latest native Wi-Fi state: V1229 (2026-05-31)

V1229 added `scripts/revalidation/native_wifi_esoc_wait_req_ks_mhi_contract_v1229.py` and classified the V1228/V891/V1199/V896 evidence host-only. Result: `v1229-esoc-wait-req-ks-mhi-contract-classified` PASS. V1228 proves the natural native path reaches `mdm_helper` in `ESOC_WAIT_FOR_REQ`; V891/V1199 prove bare `ESOC_REQ_IMG` plus `ESOC_IMG_XFER_DONE` does not create MHI readiness; V896 proves Android readiness includes the `mdm_helper` / `ks` / `/dev/mhi_0305_01.01.00_pipe_10` image-link contract. The active blocker is the request/image-link handoff around `ks`/MHI. V1230 should add source/build-only support for a bounded `mdm_helper` request-return / `ks` observer that preserves the V1228 non-ptrace path and keeps `ESOC_NOTIFY`, `ESOC_BOOT_DONE`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

## Latest native Wi-Fi state: V1233 (2026-05-31)

V1233 updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to `v257` and added `--pm-observer-mdm-helper-post-wait-req-branch-snapshot`. The source/build-only verifier `scripts/revalidation/native_wifi_mdm_helper_post_wait_req_branch_snapshot_support_v1233.py` passed as `v1233-post-wait-req-branch-snapshot-build-pass`. The static aarch64 helper `stage3/linux_init/helpers/a90_android_execns_probe_v257` has sha256 `66c3bc5a9cc0daa9a9a04fe7b98ebe2d7aa974798ed131adf82e5b314b2753e5`. This closes V1233 as an observability-only build: branch snapshots capture `mdm_helper` thread `wchan`, `/proc/<tid>/syscall`, selected syscall names/args/path strings, and `/dev/esoc-0`/MHI fd counts around the V1232 wait-return boundary. No device command, deploy, tracefs write, eSoC ioctl, PM/CNSS/`mdm_helper` start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, or partition write occurred. Next is V1234 deploy-only for helper `v257`, then V1235 bounded live branch snapshot.


## Latest native Wi-Fi state: V1234 (2026-05-31)

V1234 added `scripts/revalidation/wifi_execns_helper_v257_deploy_preflight_v1234.py` and deployed static helper `a90_android_execns_probe v257` (`66c3bc5a9cc0daa9a9a04fe7b98ebe2d7aa974798ed131adf82e5b314b2753e5`) to `/cache/bin/a90_android_execns_probe`. The deploy passed as `execns-helper-v257-deploy-pass`. NCM was not active, so transfer used cmdv1x serial fallback (`960` chunks, chunk size `1800`, line check pass). This was deploy-only: no daemon start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.

## Latest native Wi-Fi state: V1235 (2026-05-31)

V1235 added `scripts/revalidation/native_wifi_mdm_helper_post_wait_req_branch_snapshot_live_v1235.py` and ran the bounded non-ptrace branch snapshot with helper `v257`. Result: `v1235-branch-snapshot-no-exec-no-ks-mhi` PASS. `post_wait_req.transition_detected=1` at sample `4`; `ks_process_count=0`, MHI pipe path/fd count `0`, branch phases `36`, branch burst samples `20`, `execve`/`execveat=0`, dominant syscall `nanosleep` (`68`) and dominant wchan `SyS_nanosleep` (`68`). Private transcript shows the subsystem trigger child in `mdm_subsys_powerup`, `mdm_helper` holding `/dev/esoc-0`, and no GPIO142/PCIe/MHI/WLFW/BDF/`wlan0` progress. This closes the direct `mdm_helper` post-return exec hypothesis; V1236 should classify the Android `ks`/MHI runtime contract host-only before another live gate. Postflight selftest remained fail0 and netservice remained disabled/stopped.


## Latest native Wi-Fi state: V1236 (2026-05-31)

V1236 added `scripts/revalidation/native_wifi_android_ks_runtime_contract_classifier_v1236.py` and classified existing Android/native evidence host-only. Result: `v1236-ks-contract-is-pm-proxy-pm-service-trigger-not-mdm-helper-exec` PASS. Android evidence proves `mdm3=ONLINE`, WLFW/BDF/`wlan0`, GPIO142 IRQ `1`, `mdm_helper` `/dev/esoc-0`, `ks` `/dev/esoc-0`, `ks` MHI pipe, and `per_mgr` `/dev/subsys_esoc0`; timeline shows `per_proxy=8.824458s` before `pm_service_esoc0_get=9.491382s`. Native V1235 proves `mdm_helper` leaves `ESOC_WAIT_FOR_REQ` but `execve=0`, `ks=0`, MHI pipe/fd `0`, GPIO142 `0`, and direct child remains in `mdm_subsys_powerup`. No device command or mutation occurred. Next is V1237: bounded live gate with late `per_proxy` after `mdm_helper` holds `/dev/esoc-0`, retaining branch snapshot and no Wi-Fi HAL/connect/network actions.


## Latest native Wi-Fi state: V1237 (2026-05-31)

V1237 added `scripts/revalidation/native_wifi_late_per_proxy_branch_snapshot_live_v1237.py` and ran the bounded branch snapshot with the late `per_proxy` flag injected. Result: `v1237-direct-subsys-trigger-preempted-late-per-proxy` PASS. The helper output showed `late_per_proxy_after_mdm_helper_esoc_fd_requested=1`, `post_wait_req.transition_detected=1` at sample `4`, branch phases `36`, `execve=0`, `ks=0`, MHI pipe/fd `0`, and no Wi-Fi progress. The late actor block did not begin because the V1235-derived direct `/dev/subsys_esoc0` trigger path completed first. This closes the combined-trigger design: V1238 should split to a late-`per_proxy`-only live gate without the direct subsystem trigger, then observe `pm-service` `/dev/subsys_esoc0`, `ks`, MHI, GPIO142, PCIe RC1, WLFW service 69, BDF, and `wlan0`.


## Latest native Wi-Fi state: V1238 (2026-05-31)

V1238 added `scripts/revalidation/native_wifi_late_per_proxy_only_live_v1238.py` and ran the bounded late-`per_proxy`-only live gate. Result: `v1238-late-per-proxy-reached-pm-service-esoc0-reboot-required` PASS. Direct helper trigger and post-wait observer were absent. Late `per_proxy` started after `mdm_helper` held `/dev/esoc-0`; `pm-service` Binder then entered `openat("/dev/subsys_esoc0")` with `wchan=mdm_subsys_powerup`. No MHI pipe, `ks`, WLFW, BDF, or `wlan0` appeared and `mdm3` stayed `OFFLINING`; cleanup was not proven safe and the device returned cleanly to native init after reboot. Next is V1239 host-only classification of the lower `mdm_subsys_powerup` hardware response gap before any Wi-Fi HAL/connect attempt.


## Latest native Wi-Fi state: V1239 (2026-05-31)

V1239 added `scripts/revalidation/native_wifi_post_esoc0_powerup_gap_classifier_v1239.py` and classified Android/V1238 evidence host-only. Result: `v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw` PASS. Android and native both reach the `pm-service` `/dev/subsys_esoc0` / `mdm_subsys_powerup` entry, but only Android receives GPIO142 IRQ, PCIe RC1 L0, sysmon esoc0 SSCTL, MHI/`ks`, WLFW/BDF, and `wlan0`. Native V1238 remains `mdm3=OFFLINING`, WLFW `0`, `wlan0=false`, and reboot-required. Next V1240 should be a cleanup-safe SDX50M response-input classifier around GPIO142/AP2MDM/MDM2AP/PCIe RC1/PMIC/pinctrl; still no Wi-Fi HAL/connect.

## Latest native Wi-Fi state: V1295 (2026-05-31)

V1295 added `scripts/revalidation/native_wifi_dense_response_sampler_live_v1295.py` and ran the bounded dense no-write late-`per_proxy` response sampler with helper `v271`. Result: `v1295-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required` PASS. The child command included both sampler flags and helper output emitted dense metadata (`mode=late-per-proxy-dense-pinctrl-irq-pcie`, `sample_interval_ms=50`, `dense_sample_count=40`, `dense_window_ms=2000`), but the parsed sample set stopped at 14 phases (`pre_late_per_proxy` plus `late_per_proxy_poll_00`..`12`). PM-service still reached `/dev/subsys_esoc0`, while GPIO142 IRQ count, PCIe/MHI/WLFW/SDX50M kmsg markers, MHI pipe, and `wlan0` all stayed absent; `mdm3` stayed `OFFLINING`. Postflight native health is clean: `A90 Linux init 0.9.68 (v724)` and selftest `pass=11 warn=1 fail=0`. Next V1296 should be host-only and explain the dense-window early exit before any new live power/GPIO/eSoC/HAL/network action.

## Latest native Wi-Fi state: V1296 (2026-05-31)

V1296 added `scripts/revalidation/native_wifi_dense_window_early_exit_classifier_v1296.py` and classified the V1295 dense-window shortfall host-only. Result: `v1296-dense-window-limited-by-helper-stdout-cap` PASS. The raw transcript proves dense metadata was active (`40` samples at `50 ms`), but helper stdout hit `A90_EXECNS_STDOUT_END truncated=1 bytes=1048576` during `late_per_proxy_poll_13`; `response_sampler.end` is absent, while `A90_EXECNS_END rc=0` and cmdv1 `run rc=0 status=ok` are present. Therefore V1295 did not prove a 14-sample runtime stop; it proved the current verbose sampler exceeds the helper stdout cap before the full 40-sample window. Next V1297 should be source/build-only compact or file-backed dense sampling before rerunning live.

## Latest native Wi-Fi state: V1297 (2026-05-31)

V1297 updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to `v272` and added `--pm-observer-late-per-proxy-compact-response-sampler`. The source/build-only verifier `scripts/revalidation/native_wifi_compact_dense_response_sampler_support_v1297.py` passed as `v1297-compact-dense-sampler-build-pass`. The static aarch64 helper `stage3/linux_init/helpers/a90_android_execns_probe_v272` has sha256 `1344b4ac101aa0cde56a46f1274b2d01f25d11b424158d822bff71234a1e7885` and size `1319408`. This is observability-only: no device command, deploy, PMIC write, userspace GPIO line request/hold, direct eSoC ioctl, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, boot image write, or partition write occurred. Next is V1298 deploy-only for helper `v272`, then V1299 bounded compact dense response sampling.

## Latest native Wi-Fi state: V1298 (2026-05-31)

V1298 added `scripts/revalidation/wifi_execns_helper_v272_deploy_preflight_v1298.py` and deployed static helper `a90_android_execns_probe v272` (`1344b4ac101aa0cde56a46f1274b2d01f25d11b424158d822bff71234a1e7885`) to `/cache/bin/a90_android_execns_probe`. The deploy passed as `execns-helper-v272-deploy-pass`. NCM was not active, so transfer used cmdv1x serial fallback (`1010` chunks, chunk size `1800`, line check pass). Independent post-deploy commands confirmed remote sha, marker, and `--pm-observer-late-per-proxy-compact-response-sampler`; selftest remained `pass=11 warn=1 fail=0`. This was deploy-only: no daemon start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred. Next is V1299 bounded compact dense no-write response sampling.

## Latest native Wi-Fi state: V1299 (2026-05-31)

V1299 added `scripts/revalidation/native_wifi_compact_dense_response_sampler_live_v1299.py` and ran the bounded compact dense no-write late-`per_proxy` response sampler with helper `v272`. Result: `v1299-compact-dense-full-window-response-sampled-no-esoc0-trigger` PASS. The compact sampler completed the full window: mode `late-per-proxy-dense-compact-pinctrl-irq-pcie`, sample count `42`, phases `pre_late_per_proxy`, `late_per_proxy_poll_00..39`, `post_late_per_proxy`, `response_sampler.end=1`, and helper stdout `truncated=0 bytes=778235`. GPIO142 IRQ, PCIe/MHI/WLFW/SDX50M kmsg, MHI pipe, `ks`, and `wlan0` stayed absent; `mdm3` stayed `OFFLINING`. The original V1299 manifest said no `/dev/subsys_esoc0` trigger because `per_mgr_subsys_esoc0_count` stayed `0`; V1300 supersedes that interpretation and shows the transcript still contains `/dev/subsys_esoc0` / `mdm_subsys_powerup` evidence. Cleanup reboot restored healthy v724 with selftest `pass=11 warn=1 fail=0` and netservice disabled/stopped. No Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, PMIC write, GPIO line request/hold, direct eSoC ioctl, flash, boot image write, or partition write occurred.

## Latest native Wi-Fi state: V1300 (2026-05-31)

V1300 added `scripts/revalidation/native_wifi_compact_dense_esoc0_reachability_classifier_v1300.py` and classified V1295/V1299 evidence host-only. Result: `v1300-v1299-esoc0-reached-manifest-false-negative` PASS. V1299 has a full compact window (`42` samples, `response_sampler.end=1`, `truncated=0 bytes=778235`) and still contains `path.value=/dev/subsys_esoc0` twice plus `wchan=mdm_subsys_powerup` thirteen times. The V1299 manifest false negative came from fd-only compact classification: blocked opens do not produce visible completed fds, and repeated syscall/kmsg probes were intentionally removed to stay below the stdout cap. Next V1301 should be source/build-only and add a compact powerup-thread/path marker before another live response run. No device command, PM/CNSS actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, PMIC write, GPIO line request/hold, direct eSoC ioctl, flash, boot image write, or partition write occurred.

## Latest native Wi-Fi state: V1301 (2026-05-31)

V1301 updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to `a90_android_execns_probe v273` and added `scripts/revalidation/native_wifi_compact_powerup_marker_support_v1301.py`. Result: `v1301-compact-powerup-marker-build-pass` PASS. The static aarch64 helper `stage3/linux_init/helpers/a90_android_execns_probe_v273` built with sha256 `dd1d15a5ef01189526720814c50b007f6dc9a0f25e9239caf0e9da34c65b6b46` and size `1319408`; readelf shows no `INTERP` and no dynamic section. The compact sampler now emits per-sample `powerup_marker` fields for `pm-service` process/thread counts, `mdm_subsys_powerup` thread count, inferred `/dev/subsys_esoc0` reachability, first blocked thread metadata, and best-effort syscall path capture without ptrace. This was source/build-only: no deploy, device command, PM/CNSS actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, PMIC write, GPIO line request/hold, direct eSoC ioctl, flash, boot image write, or partition write occurred. Next is V1302 deploy-only for helper `v273`, then V1303 bounded compact dense live rerun requiring `powerup_marker` evidence.

## Latest native Wi-Fi state: V1302 (2026-05-31)

V1302 added `scripts/revalidation/wifi_execns_helper_v273_deploy_preflight_v1302.py` and deployed helper `v273` to `/cache/bin/a90_android_execns_probe`. Result: `execns-helper-v273-deploy-pass` PASS. NCM was inactive, so deploy used serial fallback with chunk size `1800`, `1010` chunks, `1817918` encoded bytes, and line check pass (`max_cmdv1_line_bytes=3788`, safe limit `3968`). Post-deploy sha confirmed `dd1d15a5ef01189526720814c50b007f6dc9a0f25e9239caf0e9da34c65b6b46`; helper usage reports `a90_android_execns_probe v273`. Native selftest remained `pass=11 warn=1 fail=0`, and service-manager preflight stopped at approval-required as expected. No PM/CNSS actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, PMIC write, GPIO line request/hold, direct eSoC ioctl, flash, boot image write, or partition write occurred. Next V1303 should run the bounded compact dense live sampler and require `powerup_marker` keys.

## Latest native Wi-Fi state: V1303 (2026-05-31)

V1303 added `scripts/revalidation/native_wifi_compact_powerup_marker_live_v1303.py` and reran the bounded compact dense late-`per_proxy` observer with helper `v273`. Result: `v1303-powerup-marker-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required` PASS. The compact sampler completed `42` samples and `powerup_marker` covered all `42` phases. It proved `pm-service` reached `/dev/subsys_esoc0` via `openat` and blocked in `mdm_subsys_powerup` (`max_powerup_thread_count=1`, `powerup_subsys_esoc0_inferred_seen=true`), while GPIO142/MHI/WLFW/`wlan0` remained absent (`max_mdm_status_count_total=0`, `max_mhi_bus_count=0`, `mhi_pipe_seen=false`, `wlan0_seen=false`). GPIO lines showed `gpio135 : out 0 16mA no pull` and `gpio142 : in  0 8mA no pull`; lineinfo confirmed kernel ownership and AP2MDM consumer without GPIO request. Debugfs was absent after cleanup, status/selftest stayed healthy, and netservice remained disabled. No Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, PMIC write, userspace GPIO request/hold, direct eSoC ioctl, flash, boot image write, or partition write occurred. Next V1304 should classify the AP2MDM/MDM2AP response boundary against Android-positive evidence.

## Latest native Wi-Fi state: V1304 (2026-05-31)

V1304 added `scripts/revalidation/native_wifi_ap2mdm_mdm2ap_response_classifier_v1304.py` and classified the AP2MDM/MDM2AP response boundary host-only. Result: `v1304-ap2mdm-assertion-visibility-gap-classified` PASS. V1303 already proves the trigger path (`pm-service` → `/dev/subsys_esoc0` → `mdm_subsys_powerup`), but all 42 sampled powerup phases still show GPIO135 low (`gpio135 : out 0 16mA no pull`) and GPIO142 low (`gpio142 : in  0 8mA no pull`), with MDM status count `0`, MHI bus count `0`, MHI pipe absent, and `wlan0` absent. Android-positive and eSoC reference evidence confirm that ext-sdx50m powerup should assert AP2MDM GPIO135 before MDM2AP/PCIe progress and that Android can reach WLAN-PD/WLFW/BDF/`wlan0`. This classifies the current blocker as an AP2MDM assertion/visibility boundary. V1305 should add tighter read-only AP2MDM/MDM2AP transition timing or classify the ext-mdm PMIC/pinctrl branch before any new live retry.

## Latest native Wi-Fi state: V1305 (2026-05-31)

V1305 added `scripts/revalidation/native_wifi_ap2mdm_transition_window_classifier_v1305.py` and classified the V1303 transition window host-only. Result: `v1305-ap2mdm-low-through-extended-powerup-window` PASS. V1303 observed `mdm_subsys_powerup` for `5013ms` across `42` powerup samples (`pre_late_per_proxy` through `post_late_per_proxy`), with sample deltas `67/122.268/133ms` min/avg/max. GPIO135 stayed `gpio135 : out 0 16mA no pull`, GPIO142 stayed `gpio142 : in  0 8mA no pull`, and MDM status, MHI bus, MHI pipe, `ks`, and `wlan0` stayed absent. This closes the simple sampler-cadence explanation. V1306 should classify the lower ext-mdm branch: PM8150L soft-reset pinctrl, PCIe GDSC/runtime power prerequisite, or branch-before-`mdm_do_first_power_on`.

## Latest native Wi-Fi state: V1306 (2026-05-31)

V1306 added `scripts/revalidation/native_wifi_ext_mdm_pmic_gdsc_branch_classifier_v1306.py` and compared V1305 native lower-window evidence against Android-positive PMIC/PCIe references. Result: `v1306-pmic-gdsc-prereq-gap-classified` PASS. Native remains in `mdm_subsys_powerup` for the extended window with PM8150L soft-reset `MUX UNCLAIMED`, PCIe1/PCIe0 GDSCs at `0mV`, AP2MDM/MDM2AP low, MDM status count `0`, MHI `0`, no MHI pipe, no `ks`, and no `wlan0`. Android-positive V1244 has PMIC GPIO9 configured and PCIe RC1 progress. The blocker is now below upper PM/CNSS delivery and aligned with an ext-mdm PMIC/GDSC prerequisite branch. V1307 should add focused no-write PMIC/GDSC transition sampling or classify exact safe init prerequisites before any lower mutation.

## Latest native Wi-Fi state: V1307 (2026-05-31)

V1307 updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to `a90_android_execns_probe v274` and added focused PMIC/GDSC transition sampler support. Result: `v1307-pmic-gdsc-transition-sampler-build-pass` PASS. New opt-in flag: `--pm-observer-late-per-proxy-pmic-gdsc-transition-sampler`; new response mode: `late-per-proxy-focused-pmic-gdsc-transition`; intended window: `80` samples at `50ms`. The focused output keeps `powerup_marker`, AP2MDM/MDM2AP target lines, PM8150L soft-reset source/line, PCIe0/PCIe1 GDSC source/line, PCI/MHI counts, MHI pipe, `ks`, `wlan0`, and safety zeros while dropping heavier kmsg/gpiochip detail. Built static aarch64 helper `stage3/linux_init/helpers/a90_android_execns_probe_v274` has sha256 `eb96072631ca38c3296f5da1756a93765e198e8fdd4dc010d087bc4b3b5fc180` and no dynamic section. No deploy or device command occurred. Next V1308 should deploy helper v274 only.

## Latest native Wi-Fi state: V1308 (2026-05-31)

V1308 added `scripts/revalidation/wifi_execns_helper_v274_deploy_preflight_v1308.py` and deployed helper `a90_android_execns_probe v274` to `/cache/bin/a90_android_execns_probe`. Result: `execns-helper-v274-deploy-pass` PASS. Remote helper sha256 is `eb96072631ca38c3296f5da1756a93765e198e8fdd4dc010d087bc4b3b5fc180`; native version remained `A90 Linux init 0.9.68 (v724)`; selftest remained `fail=0`; service-manager processes and Wi-Fi link surface were clean. NCM was inactive, so deploy used serial fallback. No daemon start or Wi-Fi bring-up occurred. Next V1309 should run the bounded no-write PMIC/GDSC transition sampler live and classify whether PM8150L soft-reset and PCIe GDSC remain unconfigured during the focused `mdm_subsys_powerup` window.

## Latest native Wi-Fi state: V1309 (2026-05-31)

V1309 added `scripts/revalidation/native_wifi_pmic_gdsc_transition_sampler_live_v1309.py` and ran the bounded focused PMIC/GDSC sampler live. Result: `v1309-focused-pmic-gdsc-partial-window-no-transition` PASS. The run produced `76` focused samples before helper stdout reached the existing `1MiB` cap. Evidence still proves the useful boundary: `pm-service` reached `/dev/subsys_esoc0`, a thread blocked in `mdm_subsys_powerup`, GPIO135 stayed `out 0`, GPIO142 stayed `in 0`, PM8150L soft-reset stayed `MUX UNCLAIMED`, PCIe0/PCIe1 GDSCs stayed at `0mV`, and MHI/`ks`/`wlan0` stayed absent. Debugfs was used read-only and unmounted during cleanup; post-run selftest remained `fail=0`. Next V1310 should either classify the exact safe lower prerequisite host-only or reduce sampler stdout to preserve full-window end markers.

## Latest native Wi-Fi state: V1310 (2026-05-31)

V1310 added `scripts/revalidation/native_wifi_lower_prereq_classifier_v1310.py` and classified the lower prerequisite host-only. Result: `v1310-static-surfaces-closed-dynamic-gdsc-sequence-blocker` PASS. V1276 closes PMIC GPIO9 out/high static shape, V1291 closes TLMM GPIO135/GPIO142 static shape, and V1309 reconfirms the `pm-service` `/dev/subsys_esoc0` → `mdm_subsys_powerup` boundary with PCIe0/PCIe1 GDSCs still at `0mV` and MHI/`ks`/`wlan0` absent. The active blocker is dynamic PCIe/GDSC/eSoC lower power sequencing after `mdm_subsys_powerup`. Next V1311 should add a stdout-reduced full-window lower-sequence summary sampler before considering any PMIC/GPIO/eSoC mutation gate.

## Latest native Wi-Fi state: V1311 (2026-05-31)

V1311 updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to `a90_android_execns_probe v275` and added stdout-reduced lower-sequence summary sampler support. Result: `v1311-lower-sequence-summary-sampler-build-pass` PASS. New opt-in flag: `--pm-observer-late-per-proxy-lower-sequence-summary-sampler`; response mode: `late-per-proxy-lower-sequence-summary`; intended window: `80` samples at `50ms`. The new output contract emits aggregate `response_summary.*` keys for powerup presence, MDM status, PCI/MHI/MHI pipe/`ks`/`wlan0`, PCIe0/PCIe1 GDSC, PMIC soft-reset, TLMM GPIO135/GPIO142, and safety zeros, avoiding the repeated per-sample output that truncated V1309. Built static aarch64 helper `stage3/linux_init/helpers/a90_android_execns_probe_v275` has sha256 `66e52e7507dd07bcb4071afd04bc60e51d1c6bb7b9cb7363205f1eb4f44d4677` and no dynamic section. No deploy or device command occurred. Next V1312 should deploy helper v275 only.

## Latest native Wi-Fi state: V1312 (2026-05-31)

V1312 added `scripts/revalidation/wifi_execns_helper_v275_deploy_preflight_v1312.py` and deployed helper `a90_android_execns_probe v275` to `/cache/bin/a90_android_execns_probe`. Result: `execns-helper-v275-deploy-pass` PASS. Remote helper sha256 is `66e52e7507dd07bcb4071afd04bc60e51d1c6bb7b9cb7363205f1eb4f44d4677`; native version remained `A90 Linux init 0.9.68 (v724)`; selftest remained `fail=0`; service-manager processes and Wi-Fi link surface were clean. NCM was inactive, so deploy used serial fallback. No daemon start or Wi-Fi bring-up occurred. Next V1313 should run the bounded lower-sequence summary sampler live and verify the full summary window completes without stdout truncation.

## Latest native Wi-Fi state: V1313 (2026-05-31)

V1313 added `scripts/revalidation/native_wifi_lower_sequence_summary_sampler_live_v1313.py` and ran the bounded lower-sequence summary sampler live. Result: `v1313-lower-sequence-full-window-no-transition` PASS. Helper stdout did not truncate; `response_summary.sample_count=81`; `response_summary.end=1`; `mdm_subsys_powerup` was seen with max powerup thread count `1`. The full window still showed max MDM status count `0`, PCI devices `0`, MHI bus `0`, MHI pipe fd count `0`, `ks` count `0`, `wlan0` absent, PCIe0/PCIe1 GDSCs at `0mV`, PMIC soft-reset pinmux `MUX UNCLAIMED`, GPIO135 `out 0`, and GPIO142 `in 0`. Safety markers stayed zero for GPIO line request, PMIC write, and direct eSoC ioctl; post-run selftest remained `fail=0`. Next V1314 should classify the exact safe dynamic GDSC/eSoC prerequisite.

## Latest native Wi-Fi state: V1314 (2026-05-31)

V1314 added `scripts/revalidation/native_wifi_dynamic_gdsc_esoc_prereq_classifier_v1314.py` and classified the exact safe dynamic prerequisite host-only. Result: `v1314-provider-internal-first-power-on-trace-gate-selected` PASS. V1314 confirms V1313's full-window no-transition result, keeps static PMIC/TLMM shape closed via V1276/V1291/V1310, and rejects direct PMIC/GPIO/GDSC/eSoC mutation. The selected next proof is provider-internal first-power-on event visibility using targeted tracefs static events for regulator/gpio/irq/clk/power/PIL. Next V1315 should preflight target tracefs event availability and formats; V1316 can then run the bounded event collector around the same late `per_proxy` PM-service path, still without Wi-Fi HAL/connect or lower writes.

## Latest native Wi-Fi state: V1315 (2026-05-31)

V1315 added `scripts/revalidation/native_wifi_tracefs_lower_event_preflight_v1315.py` and ran a bounded tracefs lower-event preflight. Result: `v1315-tracefs-lower-event-preflight-pass` PASS. Tracefs was mounted temporarily and unmounted during cleanup; `available_events` was readable with `1250` events. Target lower event groups all had readable formats: regulator `4/4`, gpio `2/2`, irq `2/2`, clk `4/4`, power `3/3`, and `msm_pil_event` `3/3`. No tracefs control write, PM-service trigger, PMIC/GPIO/GDSC/eSoC mutation, Wi-Fi HAL/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred. Post selftest passed. Next V1316 should run a bounded tracefs event collector around the existing late `per_proxy` PM-service path.

## Latest native Wi-Fi state: V1316 (2026-05-31)

V1316 added `scripts/revalidation/native_wifi_tracefs_lower_event_collector_live_v1316.py` and ran the bounded tracefs lower-event collector around the existing late `per_proxy` PM-service path. Result: `v1316-critical-first-power-on-events-captured` PASS. `pm-service` reached `/dev/subsys_esoc0` / `mdm_subsys_powerup`; tracefs result was `tracefs-uprobe-pass`; `18` selected lower events were enabled and disabled cleanly; counts were total `81174`, critical `3936`, noise `77238`, with group counts `regulator=2310`, `gpio=1582`, `msm_pil_event=44`, `power=0`, `irq=68124`, `clk=9114`. No Wi-Fi HAL/connect, credentials, DHCP/routes, external ping, PMIC write, GPIO line request/hold, direct eSoC ioctl, flash, boot image write, or partition write occurred. Next V1317 should classify captured trace lines by event content/device/timing and decide whether to narrow the collector to SDX50M-relevant regulator/GPIO/PIL events.

## Latest native Wi-Fi state: V1317 (2026-05-31)

V1317 added `scripts/revalidation/native_wifi_lower_trace_line_classifier_v1317.py` and classified the existing V1316 trace-line sample host-only. Result: `v1317-sample-background-noise-classified-next-critical-only-dump` PASS. The sample had `260` stored lines over about `0.035s`; only `10` were critical sample lines, with `0` SDX50M/PCIe/MHI/WLAN/CNSS target-keyword lines and `0` target GPIO `135`/`142`/`1270` lines. Critical samples were `ufs_phy_gdsc`, `pm8150l_l3`, and GPIO `96`; most saved lines were IRQ/clock/USB/UFS noise. No device command or tracefs write occurred. Next V1318 should run a narrower bounded live collector that drops broad IRQ/clock events and preserves more critical-only `regulator`, `gpio`, `power`, and `msm_pil_event` lines around the same late `per_proxy` PM-service path.

## Latest native Wi-Fi state: V1318 (2026-05-31)

V1318 added `scripts/revalidation/native_wifi_critical_lower_trace_collector_live_v1318.py` and ran the bounded critical-only lower tracefs collector live. Result: `v1318-target-critical-lines-captured` PASS. It captured `3920` critical events and preserved `2000` trace lines with target evidence: two `pil_notif` lines for `fw=esoc0`, five GPIO `1270` PMIC soft-reset lines, and two GPIO `135` AP2MDM lines showing `set 1` / output direction. GPIO `142` was absent (`0` lines) despite about `49.28s` of sample after GPIO135 high. No Wi-Fi HAL/connect, credentials, DHCP/routes, external ping, PMIC write, userspace GPIO request/hold, direct eSoC ioctl, flash, boot image write, or partition write occurred. Next V1319 should make GPIO135 assertion plus GPIO142/PCIe response absence the explicit blocker and classify whether Android has an additional response-enabling prerequisite.

## Latest native Wi-Fi state: V1319 (2026-05-31)

V1319 added `scripts/revalidation/native_wifi_gpio135_response_gap_classifier_v1319.py` and classified the GPIO135-to-GPIO142/PCIe gap host-only. Result: `v1319-gpio135-asserted-mdm2ap-pcie-response-absent` PASS. Native V1318 proves the lower eSoC sequence reaches `fw=esoc0` PIL notif, GPIO1270 soft-reset toggle, and GPIO135 high; GPIO142 remains `0`, PCI/MHI/MHI pipe are absent, `ks_count_window=0`, `mdm3` remains `OFFLINING`, and `wlan0` is absent. Android-positive references show GPIO142 IRQ `1`, PCIe RC1 lines `18`, PCIe L0 lines `2`, Android `ks`/MHI pipe present, WLFW/BDF true, and `wlan0` true. V1304's AP2MDM assertion/visibility gap is therefore superseded; next V1320 should classify the Android `mdm_helper`/`ks`/MHI image-transfer response contract as the likely post-GPIO135 prerequisite before any lower GPIO/PMIC/eSoC mutation.

## Latest native Wi-Fi state: V1320 (2026-05-31)

V1320 added `scripts/revalidation/native_wifi_mdm_helper_ks_mhi_contract_classifier_v1320.py` and classified the Android `mdm_helper`/`ks`/MHI image-link contract host-only. Result: `v1320-mdm-helper-ks-mhi-contract-selected` PASS. Native still has GPIO135 high but no GPIO142, MHI pipe, WLFW, or `wlan0`; current actor visibility has `mdm_helper=True`, PM-service eSoC trigger visibility, `ks_count_window=0`, and `mhi_pipe_seen=False`. Android-positive evidence has `mdm_helper` FD, `ks` FD, `/dev/mhi_0305_01.01.00_pipe_10`, GPIO142 IRQ `1`, PCIe RC1, WLFW, and `wlan0`. V1229/V896 negative controls show bare `ESOC_IMG_XFER_DONE` is insufficient. Next V1321 should be a fail-closed source/build gate that observes or reproduces the Android `mdm_helper`/`ks`/MHI image-link contract before any direct GPIO/PMIC/GDSC/eSoC mutation.

## Latest native Wi-Fi state: V1321 (2026-05-31)

V1321 added `scripts/revalidation/native_wifi_image_link_reconciliation_classifier_v1321.py` and reconciled V1320 with V1236-V1239 host-only. Result: `v1321-image-link-gate-covered-next-sdx50m-response-inputs` PASS. V1236 already classifies Android `ks`/MHI as `per_proxy -> pm-service Binder -> /dev/subsys_esoc0`, V1238 proves native late `per_proxy` reaches `pm-service` / `mdm_subsys_powerup`, and V1239 proves the remaining native gap is after that point and before GPIO142/PCIe/MHI/WLFW/`wlan0`. Therefore do not repeat the image-link gate as the primary next branch. V1322 should target SDX50M response inputs around `mdm_subsys_powerup` and GPIO135: read-only PCIe RC1, GPIO142 IRQ/state, regulator/pinctrl/GDSC, MHI surface, and cleanup-safe reboot boundary classification.

## Latest native Wi-Fi state: V1322 (2026-05-31)

V1322 added `scripts/revalidation/native_wifi_sdx50m_response_input_classifier_v1322.py` and classified the SDX50M response-input branch host-only. Result: `v1322-response-inputs-classified-next-provider-wait-cause` PASS. V1240 proves SDX50M metadata, GPIO142 IRQ, PCIe, and regulator surfaces are visible; V1287/V1291 demote static PMIC/TLMM shape as the shortest blocker; V1314 rejects direct PMIC/GPIO/GDSC/eSoC mutation; V1318 proves first-power-on trace reaches GPIO1270 soft-reset and GPIO135 high with regulator/GPIO/PIL events; V1319 proves GPIO142/PCIe/MHI/WLFW/`wlan0` remain absent after GPIO135 while Android-positive evidence has them. V1323 should classify the proprietary provider wait cause around `mdm_subsys_powerup`, GPIO142/MDM2AP, and `err_ready`: host/source first, then only bounded read-only or reboot-bounded live if needed.

## Latest native Wi-Fi state: V1323 (2026-05-31)

V1323 added `scripts/revalidation/native_wifi_provider_wait_cause_classifier_v1323.py` and classified the provider wait-cause branch host-only. Result: `v1323-provider-wait-cause-is-proprietary-powerup-response` PASS. Public Samsung OSRC `subsystem_restart.c` calls the board provider `powerup()` before `wait_for_err_ready()`, and the staged source does not contain the proprietary `mdm_subsys_powerup` body. V849/V918/V963 place the native block inside that proprietary ext-mdm path with stacks including `sdx50m_toggle_soft_reset`, `mdm4x_do_first_power_on`, `mdm_cmd_exe`, and `mdm_subsys_powerup`. V1318/V1319 show native reaches GPIO1270 soft-reset and GPIO135/AP2MDM activity but never receives GPIO142/MDM2AP, PCIe RC1/MHI, WLFW/BDF, or `wlan0`, while Android-positive evidence has them. V1324 should classify Android-vs-native provider response deltas around GPIO142, errfatal, soft-reset, and PCIe timing from host/source evidence first; only then design a bounded read-only or reboot-bounded live sampler.

V1324 plan is documented at `docs/plans/NATIVE_INIT_V1324_PROVIDER_RESPONSE_DELTA_PLAN_2026-05-31.md`. The planned classifier is host/source-only: read existing V1323/V1318/V1319/V1239/V1240/V1291/V852/V896 evidence, decide whether the existing record already proves a post-AP2MDM MDM2AP/PCIe response gap, and keep all live mutation, Wi-Fi HAL/connect, credentials, network, flash, PMIC/GPIO/GDSC/eSoC writes blocked.

## Latest native Wi-Fi state: V1324 (2026-05-31)

V1324 added `scripts/revalidation/native_wifi_provider_response_delta_classifier_v1324.py` and classified the Android-vs-native provider response delta host/source-only. Result: `v1324-delta-is-post-ap2mdm-mdm2ap-response-gap` PASS. Existing evidence now proves native reaches AP-side provider activity: GPIO1270 PMIC soft-reset lines, GPIO135/AP2MDM high, and GPIO141 AP2MDM_ERRFATAL-side activity. The native record still has GPIO142/MDM2AP IRQ `0`, MDM errfatal IRQ `0`, PCI/MHI/MHI pipe absent, WLFW/BDF absent, and `wlan0` absent. Android-positive V852/V896/V1239 evidence has GPIO142 IRQ, PCIe RC1/L0, MHI/ks, WLFW/BDF, and `wlan0`. V1325 should design the next small gate around GPIO142/MDM errfatal/PCIe timing as a bounded read-only or reboot-bounded sampler, or choose Android read-only timing recapture if exact Android ordering is still needed.


## Latest native Wi-Fi state: V1325 (2026-05-31)

V1325 added `docs/plans/NATIVE_INIT_V1325_GPIO142_ERRFATAL_PCIE_TIMING_OBSERVER_PLAN_2026-05-31.md`. The plan keeps the final Wi-Fi goal intact but chooses the next concrete unit as source/build-only helper support for a compact `mdm2ap_timing` sampler. The intended helper mode is `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler`, built on the existing late-`per_proxy` PM observer path, with compact fields for GPIO142 IRQ delta, MDM errfatal IRQ delta, PCIe RC1 transition, MHI bus/pipe, `ks`, WLFW, and `wlan0`. V1325 itself is documentation-only: no device command, helper deploy, PM actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC/eSoC write, flash, or partition write. Next is V1326 source/build support for helper `v276`.

## Latest native Wi-Fi state: V1326 (2026-05-31)

V1326 updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to `a90_android_execns_probe v276` and added `scripts/revalidation/native_wifi_mdm2ap_timing_sampler_support_v1326.py`. Result: `v1326-mdm2ap-timing-sampler-build-pass` PASS. New opt-in flag: `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler`; response mode: `late-per-proxy-mdm2ap-errfatal-pcie-timing`; intended window: `120` samples at `50ms`. The compact output emits aggregate `mdm2ap_timing.*` keys for GPIO142 IRQ delta, MDM errfatal IRQ delta, PCIe RC1 transition, MHI bus/pipe, `ks`, WLFW kmsg count, `wlan0`, and safety zeros. Built static aarch64 helper `stage3/linux_init/helpers/a90_android_execns_probe_v276` has sha256 `dad57e135d3b4f0db2f1f95ee04022a3f5610fdbd0ecc6b69c243883689ca66f` and no dynamic section. No deploy or device command occurred. Next V1327 should deploy helper v276 only.

## Latest native Wi-Fi state: V1327 (2026-05-31)

V1327 added `scripts/revalidation/wifi_execns_helper_v276_deploy_preflight_v1327.py` and deployed helper `a90_android_execns_probe v276` to `/cache/bin/a90_android_execns_probe`. Result: `execns-helper-v276-deploy-pass` PASS. NCM was inactive, so deploy used serial fallback. Manual post-deploy verification confirmed remote SHA256 `dad57e135d3b4f0db2f1f95ee04022a3f5610fdbd0ecc6b69c243883689ca66f`, helper marker `a90_android_execns_probe v276`, and the new `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler` flag. Native selftest remained `pass=11 warn=1 fail=0`; netservice remained disabled. No daemon start or Wi-Fi bring-up occurred. Next V1328 should run the bounded no-write `mdm2ap_timing` live sampler.

## Latest native Wi-Fi state: V1328 (2026-05-31)

V1328 added `scripts/revalidation/native_wifi_mdm2ap_timing_sampler_live_v1328.py` and ran the bounded no-write `mdm2ap_timing` sampler with helper v276. Result: `v1328-mdm2ap-timing-full-window-no-transition` PASS. The full `120 x 50ms` timing window saw `pm-service` enter `mdm_subsys_powerup` (`timing_pm_service_powerup_seen=true`, max powerup thread count `1`) but still showed GPIO142 IRQ delta `0`, MDM errfatal IRQ delta `0`, no PCIe RC1 transition, PCI/MHI max `0`, no MHI pipe, `ks` max `0`, WLFW kmsg max `0`, and `wlan0=false`. All timing safety markers were zero; post-run selftest remained `pass=11 warn=1 fail=0`. Next V1329 should classify the Android-only SDX50M response prerequisite before any PMIC/GPIO/eSoC mutation.

## Latest native Wi-Fi state: V1329 (2026-05-31)

V1329 added `scripts/revalidation/native_wifi_android_only_sdx50m_prereq_classifier_v1329.py` and reconciled V1328 with Android-positive V852/V896/V1239 evidence. Result: `v1329-android-prereq-is-earlier-sdx50m-response-sequence` PASS. Native has late `per_proxy`, `mdm_helper` holding `/dev/esoc-0`, and `pm-service` entering `mdm_subsys_powerup`, but still has no GPIO142/MDM2AP response, no MDM errfatal IRQ, no PCIe RC1, no MHI/ks, no WLFW/BDF, and no `wlan0`. Android has GPIO142 IRQ, PCIe RC1/L0, `ks` on the MHI pipe, WLFW/BDF, and `wlan0`; existing evidence places PCIe L0 before the captured `pm-service` eSoC timestamp. Next V1330 should design a focused Android read-only timing recapture around earliest `per_mgr`/`per_proxy`, `mdm_helper`, GPIO142, PCIe RC1, and `ks`/MHI on one monotonic timeline before any native PMIC/GPIO/eSoC mutation.

## Latest native Wi-Fi state: V1330 (2026-05-31)

V1330 added `docs/reports/NATIVE_INIT_V1330_ANDROID_TIMING_RECAPTURE_PLAN_2026-05-31.md`. Result: `v1330-focused-android-readonly-timing-recapture-plan-ready` PASS. The next unit is V1331: extend the V622 Android handoff/collector pattern to recapture Android dmesg monotonic timestamps for `__subsystem_get(esoc0)`, GPIO142, PCIe RC1/L0, MHI, `ks`, WLFW/BDF, and `wlan0`, while keeping init property boottimes as a separately labelled clock source unless comparability is verified. The collector remains read-only; Android boot handoff is allowed only inside an explicit rollback wrapper. No Wi-Fi HAL/scan/connect, credentials, DHCP/routes, external ping, or lower native mutation.

## Latest native Wi-Fi state: V1331 (2026-05-31)

V1331 added `scripts/revalidation/native_wifi_android_sdx50m_timing_recapture_v1331.py` and `scripts/revalidation/android_sdx50m_timing_handoff_v1331.py`, then ran a bounded Android handoff with rollback to `stage3/boot_linux_v724.img`. Result: `v1331-android-wlfw-before-subsys-esoc0` PASS. The collector captured Android `wlfw_start` at `8.396410s`, captured `__subsystem_get(esoc0)` at `8.449943s`, BDF download at `9.513055s`, and `wlan0` at `14.772258s`; PCIe RC1/L0 and MHI pipe dmesg markers were not present in this run. Native rollback verified `A90 Linux init 0.9.68 (v724)` and selftest `pass=11 warn=1 fail=0`. Next V1332 should classify whether native is missing an earlier Android `cnss-daemon` WLFW request/provider state before the eSoC powerup path.

## Latest native Wi-Fi state: V1332 (2026-05-31)

V1332 added `scripts/revalidation/native_wifi_wlfw_before_esoc_classifier_v1332.py` and classified the Android-vs-native WLFW/eSoC ordering host-only. Result: `v1332-native-missing-early-wlfw-provider-state` PASS. Android V1331 has `wlfw_start=8.396410s`, `__subsystem_get(esoc0)=8.449943s`, `BDF=9.513055s`, and `wlan0=14.772258s`. Native V1328 starts `cnss_daemon` before `mdm_helper`/late `per_proxy` and reaches `mdm_subsys_powerup`, but records `timing_wlfw_kmsg_max=0`, `timing_mhi_bus_max=0`, `timing_ks_process_max=0`, and `wlan0=false`. Next V1333 should run a bounded native early-CNSS WLFW parity observer before per_proxy/eSoC trigger, capturing `cnss-daemon` stdout/stderr, properties, fds, and kmsg WLFW markers without Wi-Fi HAL/scan/connect.

## Latest native Wi-Fi state: V1333 (2026-05-31)

V1333 updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to `a90_android_execns_probe v277` and added `scripts/revalidation/native_wifi_early_cnss_observe_only_support_v1333.py`. Result: `v1333-early-cnss-observe-only-build-pass` PASS. The new helper gate `--subsys-trigger-gate observe-only` is valid for `wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture` and emits `cnss_before_esoc.observe_only_gate`, `cnss_before_esoc.wlfw_trigger_ready`, and `cnss_before_esoc.result=wlfw-precondition-observed-observe-only-no-open`. The static aarch64 helper `stage3/linux_init/helpers/a90_android_execns_probe_v277` built with sha256 `3a61125bd3e2bad9cda8dcac2df75184c3df369ada4a9a0010681c49788a6fd9`; `readelf` showed no `INTERP` and no dynamic section. No device command or deploy occurred in V1333. Next V1334 should deploy helper v277 only, then V1335 should run the bounded early-CNSS WLFW parity observer with `/dev/subsys_esoc0` kept closed even if WLFW appears.

## Latest native Wi-Fi state: V1335 (2026-05-31)

V1334 deployed helper `a90_android_execns_probe v277` (`3a61125bd3e2bad9cda8dcac2df75184c3df369ada4a9a0010681c49788a6fd9`) to `/cache/bin/a90_android_execns_probe`. V1335 added and ran `scripts/revalidation/native_wifi_early_cnss_wlfw_parity_observer_live_v1335.py`. Result: `v1335-native-early-cnss-no-wlfw-observe-only` PASS. The observer started `pm-service`, `mdm_helper`, `cnss_diag`, and `cnss-daemon -n -l`; `mdm_helper_esoc0_fd_seen=1`; `cnss_diag_started=1`; `cnss_daemon_started=1`; `surface_poll_count=32`; `observe_only_gate=1`; `wlfw_precondition_observed=0`; `wlfw_trigger_ready=0`; `subsys_esoc0_open_attempted=0`; `subsys_trigger.started=0`; `all_postflight_safe=1`; post-run selftest stayed `pass=11 warn=1 fail=0`. No service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO write, eSoC notify, BOOT_DONE, flash, boot image write, or partition write occurred. Next V1336 should classify the Android-only early WLFW provider/input rather than retrying the eSoC trigger.

## Latest native Wi-Fi state: V1336 (2026-05-31)

V1336 added `scripts/revalidation/native_wifi_android_pre_cnss_provider_classifier_v1336.py` and reconciled V1331, V1328, and V1335 host-only. Result: `v1336-pre-cnss-provider-order-gap` PASS. Android V1331 starts `pm_proxy_helper` at `5.813594s`, QRTR/RFS/pd-mapper companions by `7.064970s`, `per_mgr` at `6.987725s`, `per_proxy` at `7.848075s`, and `cnss_diag` at `7.975236s`, all before `cnss-daemon` at `8.222635s` and `wlfw_start` at `8.396410s`. V1335 observe-only omitted `pm_proxy_helper` and `per_proxy`; V1328 proved late `per_proxy` after CNSS/eSoC observation still leaves WLFW/BDF/MHI/ks/`wlan0` absent. Next V1337 should add a bounded Android-order pre-CNSS provider observe-only gate that starts the provider/companion chain before CNSS while keeping `/dev/subsys_esoc0` closed and forbidding Wi-Fi HAL/scan/connect.

## Latest native Wi-Fi state: HOST-ANALYSIS 2026-06-01 (out-of-band, not a vNNN cycle — READ THIS, it redirects the eSoC track)

A host-only static analysis of the stock kernel + DTS (full writeup:
`docs/reports/ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md`) reframes the eSoC
blocker. Key facts:

- The ext-sdx50m eSoC **provider is built into the kernel** (driver strings in the
  image; functions are static so absent from core kallsyms — clean decode of
  131,833 syms gives pcie=109, esoc=20, **mhi=0, sdx=0**). It is **only a thin
  GPIO/ioctl handshake**: `mdm_subsys_powerup` → `mdm4x_do_first_power_on` →
  `sdx50m_toggle_soft_reset`, sets AP2MDM_STATUS=1, toggles AP2MDM_SOFT_RESET,
  reads MDM_PMIC_PWR_STATUS, queues ESOC_REQ_IMG, waits MDM2AP_STATUS. The
  ESOC_REG_REQ_ENG/WAIT_FOR_REQ/NOTIFY ioctls the project has driven == this
  driver's `esoc_dev_ioctl`. **Zero PCIe/MHI/GDSC/regulator** references in the
  provider.
- DTS (`sdx5xm-external-soc.dtsi`/`sm8150-sdx50m.dtsi`/`sm8150-mhi.dtsi`/r3q r03):
  `mdm3 = qcom,ext-sdx50m`; GPIOs ap2mdm-status=TLMM135, mdm2ap-status=TLMM142,
  errfatal TLMM141/53, **ap2mdm-soft-reset/PON = PM8150L GPIO9** ("MDM PON
  control", 1.8V). **No regulator-supply in mdm3** → AP's only modem-power lever
  is PM8150L GPIO9. `mhi_0` (`qcom,mhi@0`) has `esoc-0=<&mdm3>` and rides on
  **`pcie1` (`qcom,pcie@1c08000`)** with `pcie1_sdx50m_wake` → **SDX50M is the
  PCIe endpoint on RC `pcie1`.**

VERDICT: the gap is **FINITE / multi-subsystem, not an Android re-implementation**.
The provider already runs on native (mdm_subsys_powerup D-state, GPIO135 +
PM8150L GPIO9 toggled per V1276/V1318) yet MDM2AP (GPIO142) never asserts → the
**modem itself is not completing power-on**. Because SDX50M is a PCIe endpoint,
its boot needs the **`pcie1` RC powered/clocked (refclk + PERST)**; V1306 shows
`pcie1` GDSC at 0mV, and the provider does NOT power the RC (that's `msm_pcie`).

PIVOT: pause the upper eSoC-ioctl / ESOC_REQ_IMG / `ks` / MHI / CNSS-WLFW work
(V1337–V1352 track) — it is all **downstream of MDM2AP**. Next read-only targets:
(1) classify `pcie1` RC power (GDSC/clocks/PERST/refclk; does native ever enable
it vs V1306 0mV), and (2) verify PM8150L GPIO9 PON sequence/timing parity vs the
provider's `reset-time-ms`. Only then consider a bounded reboot-safe RC power
experiment. Keep all prior hard exclusions (no PMIC/GPIO/GDSC writes, no Wi-Fi
HAL/scan/connect/DHCP/routes/external ping) until the read-only classification
justifies a specific bounded action.

Update after V1354/V1355:
- V1354 live observer (`v1354-current-route-pcie1-rc-stayed-off`) reached
  `mdm_subsys_powerup`, but `pcie_1_gdsc` stayed `0mV`, pcie1 clkref/pipe stayed
  disabled, GPIO102/PERST stayed low, and no GPIO142/PCI/MHI/WLFW/wlan0
  transition appeared.
- V1355 host classifier (`v1355-pon-parity-closed-pcie1-rc-next`) closed PM8150L
  GPIO9/PON as the shortest blocker: DTS maps it to ext-sdx50m soft-reset,
  V1276 shows native/Android steady-state `out/high`, and V1318 captured a
  native GPIO1270 low/high pulse before GPIO135/AP2MDM. Next active design gate
  is a host-only bounded pcie1 RC enable plan, not PMIC GPIO9 write/hold or
  upper CNSS/WLFW retry.
- V1356 host-only design (`v1356-pcie1-rc-enable-design-ready-readonly-surface-next`)
  identifies `msm_pcie_enumerate(1)` as the correct kernel semantic operation,
  but no safe userspace entry is proven. `cnss/dev_boot enumerate` is only a
  candidate if a live read-only verifier proves it exists and maps to pcie1/RC1
  rather than generic RC0. The next cycle is V1357 live read-only surface
  verification; do not write `cnss/dev_boot`, bind platform drivers, rescan PCI,
  touch PMIC/GPIO/GDSC, start HAL, scan/connect, DHCP/routes, or external ping.
- V1357 live read-only verifier (`v1357-pcie1-platform-surface-only`) proves the
  pcie1 platform node exists and is bound to `pci-msm`, but debugfs is not
  mounted, `/sys/kernel/debug/cnss/dev_boot` is absent in that state, PCI/MHI
  remain empty, and no RC1-safe userspace enumerate surface is proven. The next
  gate is V1358 temporary-debugfs mount/cleanup read-only verification before
  deciding whether `cnss/dev_boot enumerate` is truly unavailable.
- V1358 temporary-debugfs verifier (`v1358-icnss-debugfs-only-no-cnss-dev-boot`)
  mounted debugfs, read the live Wi-Fi debugfs surface, and cleaned up. The
  live kernel exposes `/sys/kernel/debug/icnss/stats` only, not CNSS2
  `/sys/kernel/debug/cnss/dev_boot`; ICNSS stats are `State: 0x80(SSR
  REGISTERED)` with `SERVER_ARRIVE=0`, `FW_READY=0`, `REGISTER_DRIVER=0`.
  `cnss/dev_boot enumerate` is unavailable; next gate is host-only ICNSS/
  `pci-msm` userspace entry classification.
- V1359 host-only classifier (`v1359-no-safe-userspace-msm-pcie-enumerate-entry`)
  closes that branch: ICNSS source has only debugfs `stats`, no `dev_boot` or
  `boot_wlan`, and no `msm_pcie_enumerate`/`qcom,wlan-rc-num`/`qcom,pcie-parent`
  control path. CNSS2 `dev_boot` belongs to the wrong rc-num=0 branch, and the
  only live surface is already-bound `pci-msm`. Next gate is V1360 live
  read-only MHI platform surface verifier before any bind/rescan mutation.
- V1360 live read-only verifier (`v1360-mhi-surface-present-no-live-device`)
  found MHI topology in live DT, including `1c0b000` and `esoc-0`, plus MHI bus
  client drivers and pcie1 bound to `pci-msm`. It found no live MHI bus devices,
  no `/dev/mhi*`, and no PCIe link-up markers. Next gate is V1361 host-only MHI
  ownership/downstream classification; do not bind MHI client drivers, rescan
  PCI, or touch PMIC/GPIO/GDSC/eSoC notify paths from this evidence alone.
- V1361 host-only classifier (`v1361-mhi-surfaces-downstream-no-safe-mutation`)
  closes the MHI client-surface branch. OSRC shows `mhi_pci_probe()` requires an
  existing `pci_dev`, while live MHI bind files belong to client drivers that
  need existing `mhi_device` instances. MHI bind/debugfs surfaces cannot initiate
  SDX50M/pcie1 enumeration. Next gate is V1362 host-only `pci-msm`/pcie1
  mutation risk classification before any platform bind/rescan attempt.
- V1362 host-only classifier (`v1362-no-safe-userspace-pci-msm-mutation`) rejects
  the remaining userspace mutations. Platform unbind/bind for
  `1c08000.qcom,pcie` is only partially RC1-scoped and enters the proprietary
  `pci-msm` remove/probe lifecycle without timeout/rollback proof; generic
  `drivers_probe` and PCI rescan are not RC1-specific. Next gate is V1363
  host-only feasibility for a kernel-side `msm_pcie_enumerate(1)` shim.
- V1363 live read-only verifier (`v1363-pci-msm-debugfs-rc-control-candidate`)
  supersedes the shim-next branch. The live kernel exposes
  `/sys/kernel/debug/pci-msm/case` and `rc_sel`; reading `case` lists `11:
  ENUMERATE`, `26: OUTPUT PERST AND WAKE GPIO STATUS`, and PERST assert/deassert
  debug cases. No write was performed and debugfs was cleaned up. Next gate is
  V1364 host-only contract classification for `rc_sel` + `case=11` before any
  debugfs write.
- V1364 host-only classifier
  (`v1364-pci-msm-debugfs-contract-candidate-not-approved`) keeps enumerate
  blocked but identifies the first bounded live write candidate: `rc_sel=1`
  followed by `case=26` (`OUTPUT PERST AND WAKE GPIO STATUS`). This should only
  emit status and validate RC selection/observability; `case=11` enumerate,
  PERST assert/deassert cases, boot option, MMIO write cases, platform
  bind/unbind, PCI rescan, PMIC/GPIO/GDSC writes, and Wi-Fi bring-up remain
  excluded.
- V1365 bounded live proof (`v1365-case26-transport-reset-reboot-risk`) shows
  that the presumed status-only pci-msm debugfs write is not a safe stepping
  stone on this native path. `rc_sel=1` followed by `case=26` caused cmdv1
  transport loss before after-captures completed; the device later recovered
  normally, but the observation window was lost. Treat pci-msm `case` writes as
  unsafe until source/disassembly proves the selected case cannot reset or
  wedge the RC/control path. Do not attempt `case=11` enumerate from this
  evidence. Next gate is V1366 host-only pci-msm case-path classification; no
  live debugfs `case` write is selected.
- V1366 host-only classifier
  (`v1366-pci-msm-case-path-corrected-rc-selector-no-live-write`) corrects the
  `rc_sel` model: pci-msm source proves `rc_sel` is a bitmask, not an ordinal
  RC index. V1365 wrote `rc_sel=1`, which selects `BIT(0)`/RC0, not pcie1/RC1;
  pcie1 requires `rc_sel=2`. The same source shows `case=26` is intended as
  PERST/WAKE `gpio_get_value` readout, while `case=11` calls
  `msm_pcie_enumerate(dev->rc_idx)`. Because V1365 still lost transport, no
  corrected `rc_sel=2` live retry is approved yet. Next gate is V1367
  host-only corrected-RC1/reboot-safe design versus a kernel-side
  `msm_pcie_enumerate(1)` shim path.
- V1367 host-only design (`v1367-corrected-rc1-status-read-design-ready`)
  selects the narrowest next live gate: one corrected RC1 status-read proof,
  `rc_sel=2` then `case=26`, treated as reboot-risky and bounded. It still
  excludes `case=11` enumerate, PERST assert/deassert, MMIO write, boot option
  write, platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC direct writes, eSoC
  notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, DHCP/routes, external ping,
  flash, boot image write, and partition write. Success requires no transport
  loss, completed after-captures, no PCI/MHI/link-up transition, debugfs mount
  cleanup, and post-selftest `fail=0`; transport loss is a failure/recovery
  classification, not a pass.
- V1368 bounded live proof (`v1368-corrected-rc1-status-proof-clean`) validates
  the corrected RC1 debugfs status path. `rc_sel=2` then `case=26` emitted
  RC1 status without transport loss, PCI/MHI/link transition, or health
  regression; debugfs cleanup restored the original mount state and post
  selftest stayed `fail=0`. Dmesg reported RC1 PERST gpio102 value `0` and
  WAKE gpio104 value `0`. This proves the corrected selector is usable for
  readout, but still does not execute or approve `case=11` enumerate. Next
  gate is V1369 host-only enumerate-vs-shim decision.
- V1369 host-only decision (`v1369-select-corrected-debugfs-rc1-enumerate-design`)
  selects corrected debugfs `case=11` over a new kernel shim for the next
  bounded live proof. Rationale: V1368 proves `rc_sel=2` reaches RC1 cleanly,
  and pci-msm source shows `case=11` calls `msm_pcie_enumerate(dev->rc_idx)`,
  which performs `msm_pcie_enable(PM_ALL)` followed by PCI root-bus scan/add.
  V1370 may attempt only `rc_sel=2` then `case=11`, with no Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, PERST assert/deassert,
  PMIC/GPIO/GDSC direct writes, eSoC notify/`BOOT_DONE`, flash, boot image
  write, or partition write.
- V1370 bounded live proof (`v1370-corrected-rc1-link-training-no-l0-clean`)
  executed corrected `rc_sel=2` then `case=11`. The kernel reached RC1
  enumerate and transient pcie1 enable/link training: reset asserted/released,
  RC1 PHY ready, LTSSM poll active/compliance observed, then RC1 link
  initialization failed before L0. No PCI/MHI device appeared, steady regulator
  and clock snapshots returned unchanged, debugfs cleanup restored the original
  mount state, and post-selftest stayed `fail=0`. This parks Wi-Fi HAL/network
  work again; next gate is V1371 host-only classification of why RC1 stops in
  LTSSM poll/compliance versus Android's RC1 L0 path.
- V1371 host-only classifier
  (`v1371-endpoint-readiness-gap-after-rc1-power-proven`) compares V1370 native
  against Android V852 and pci-msm source. V1370 proves the AP-side pcie1 RC can
  run corrected enumerate, enable power/clocks/PERST, reach PHY-ready, release
  endpoint reset, and enter LTSSM. Android reaches L0 only after esoc0/provider
  startup; native V1370 did not hold the provider path and stops in
  poll/compliance before L0. The next gate is V1372: a bounded provider-held +
  delayed corrected-RC1 enumerate proof that matches Android ordering. Still no
  Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct
  PMIC/GPIO/GDSC writes, eSoC notify/`BOOT_DONE` spoof, flash, boot image write,
  or partition write.
- V1372 bounded live proof
  (`v1372-provider-held-still-no-l0-clean`) opened the ext-sdx50m provider path
  via `/dev/subsys_esoc0`, confirmed the holder in `mdm_subsys_powerup`, waited
  the Android-derived delay, then ran corrected `rc_sel=2` + `case=11`. RC1
  again reached PHY-ready and LTSSM poll active/compliance, then failed before
  L0. No GPIO142/MDM2AP assertion, PCI device, MHI node, WLFW marker, or `wlan0`
  appeared, and reboot cleanup returned native selftest `fail=0`. The next gate
  is V1373 host-only parity classification of why Android's provider/pm-service
  path makes the endpoint ready but raw provider-hold + RC1 enumerate does not.
- V1373 host-only classifier
  (`v1373-gap-is-android-participant-plus-rc1-combination`) closes the raw
  provider-holder branch. Existing evidence has separately tested: Android PM
  actors/`mdm_helper` without corrected RC1 enumerate (no native L0), corrected
  RC1 enumerate without PM actors (no L0), and raw provider-hold plus corrected
  RC1 enumerate without Android `mdm_helper`/`pm-service` context (no L0). The
  remaining narrow untested combination is Android participant parity
  (`mdm_helper` CMD_ENG/WAIT_FOR_REQ plus `pm-service` `/dev/subsys_esoc0`) with
  corrected `rc_sel=2` + `case=11`, still below Wi-Fi HAL/scan/connect/network.
- V1374 source/build-only support (`v1374-helper-v282-support-ready`) adds
  helper-side support for that narrow combination in `a90_android_execns_probe
  v282` (SHA256 `c1f4670536c37b068dd2f8ac807c0eb5416eb3f248857791002156c1f0195418`).
  The new `--pm-observer-late-per-proxy-corrected-rc1-enumerate` flag is gated
  by the late-`per_proxy` response sampler and MDM2AP timing sampler, waits
  until `pm-service` is observed with `/dev/subsys_esoc0`, then writes
  corrected `/sys/kernel/debug/pci-msm/rc_sel=2` and `case=11` from inside the
  same helper process. V1374 runs no device command. Next is V1375 deploy-only
  helper v282 preflight, then V1376 bounded live; Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC
  notify/`BOOT_DONE`, flash, boot image writes, and partition writes remain
  excluded.
- V1375 deploy-only preflight (`execns-helper-v282-deploy-pass`) installed
  helper v282 to `/cache/bin/a90_android_execns_probe`. NCM was inactive, so
  the wrapper used serial fallback; the first 3000-byte chunk attempt was
  rejected before transfer by line-safety checks, and the successful run used
  1800-byte chunks (`1061` chunks, max cmdv1 line `3786` <= safe limit `3968`).
  Post-deploy SHA matched
  `c1f4670536c37b068dd2f8ac807c0eb5416eb3f248857791002156c1f0195418`, helper
  usage showed `a90_android_execns_probe v282` and the corrected RC1 flag, and
  post selftest remained clean. No daemon start, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, flash, boot image write, or
  partition write occurred. Next is V1376 bounded live.
- V1376 bounded live (`v1376-corrected-rc1-not-triggered`) proved the v282
  trigger gate is wrong, not that the Android participant + corrected RC1 path
  failed. The child command contained the private CNSS, precondition, and
  corrected RC1 flags; debugfs mounted and cleaned up; timing captured
  `timing_pm_service_powerup_seen=True` with 120 samples and no GPIO142/PCI/MHI/
  WLFW/`wlan0`. However `corrected_rc1_enumerate.triggered=False` because v282
  waited for a `/dev/subsys_esoc0` fd count. In the real blocking path,
  `pm-service` is still inside `open("/dev/subsys_esoc0")` /
  `mdm_subsys_powerup`, so no fd exists yet. Next is a helper fix that gates
  corrected RC1 enumerate on `mdm_subsys_powerup`/powerup-thread observation,
  not fd ownership.
- V1377 source/build-only support (`v1377-helper-v283-powerup-gate-ready`)
  implements that fix in helper `a90_android_execns_probe v283` (SHA256
  `985eba4834b3b0324d886df39cecff9811ae183ea800119fdaea2d6ef8431a18`). The
  corrected RC1 trigger now accepts either the legacy fd gate or a positive
  `pm_service_powerup_thread_count`, and emits
  `gate_pm_service_powerup_thread_count` for evidence. Source/build checks
  passed without device commands. Next is V1378 deploy/preflight of helper
  v283, then V1379 bounded live rerun of the Android participant + corrected
  RC1 gate. Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  PMIC/GPIO/GDSC direct writes, eSoC notify/`BOOT_DONE`, flash, boot image
  write, and partition write remain excluded.
- V1378 deploy-only preflight (`execns-helper-v283-deploy-pass`) installed
  helper v283 to `/cache/bin/a90_android_execns_probe`. NCM was inactive, so
  `auto` transfer used serial fallback with the V1375-proven chunk size `1800`;
  transfer wrote `1061` chunks with max cmdv1 line size `3786` below the safe
  limit `3968`. Post-deploy SHA matched
  `985eba4834b3b0324d886df39cecff9811ae183ea800119fdaea2d6ef8431a18`, helper
  usage exposed `a90_android_execns_probe v283` and
  `gate_pm_service_powerup_thread_count`, and post selftest remained clean.
  No daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
  ping, flash, boot image write, or partition write occurred. Next is V1379
  bounded live rerun.
- V1379 bounded live (`v1379-corrected-rc1-ltssm-no-downstream-clean`) reran
  the Android participant + corrected RC1 path with helper v283. The corrected
  RC1 block triggered at `late_per_proxy_poll_00` with
  `gate_pm_service_powerup_thread_count=1`, `rc_sel_rc=0`, and `case_rc=0`.
  The timing sampler captured `timing_pcie_rc1_transition_seen=True` over
  `120` samples, but GPIO142 IRQ delta stayed `0`, PCI and MHI device counts
  stayed `0`, MHI pipe/`ks` stayed absent, WLFW kmsg count stayed `0`, and
  `wlan0` remained absent. Safety markers remained clear, debugfs cleanup
  completed, and post selftest stayed `fail=0`; netservice stayed disabled.
  Next is a host-only LTSSM/Android-participant gap classifier before any new
  live mutation or Wi-Fi HAL/network action.
- V1380 host-only classifier
  (`v1380-v1379-rc1-action-too-late-for-android-window`) compared V1379 dmesg
  timing against V1371 Android RC1 L0 timing. V1379 executed `case=11` about
  `4.123s` after `__subsystem_get(esoc0)`, while Android asserts RC1 about
  `0.255s` after `esoc0` and reaches L0 about `0.017s` after reset release.
  V1379 still reached PHY-ready and LTSSM poll/compliance, then failed before
  L0 with no GPIO142/PCI/MHI/WLFW/`wlan0`. The next change should be
  source/build-only helper v284 support: trigger corrected RC1 immediately
  when the powerup-thread gate becomes positive, then sample the post-enumerate
  window. No new live mutation is selected by V1380.
- V1381 source/build-only support (`v1381-helper-v284-immediate-corrected-rc1-ready`)
  bumps `a90_android_execns_probe` to v284 (SHA256
  `da1f8b65cbc3872f7ec31a368bd382720a399d3a785e50ae383c800632047b9f`). It adds
  `--pm-observer-late-per-proxy-immediate-corrected-rc1-enumerate`, requires
  the response and MDM2AP/PCIe timing samplers, emits an immediate-mode marker
  and monotonic write timestamp, and executes corrected RC1 enumerate as soon as
  `pm_service_powerup_thread_count > 0` or the legacy fd gate is observed. The
  old delayed path remains guarded for non-immediate runs. Next is V1382
  deploy/preflight, then V1383 bounded live timing test; no device command was
  run in V1381.
- V1382 deploy-only preflight (`execns-helper-v284-deploy-pass`) installed
  helper v284 to `/cache/bin/a90_android_execns_probe`. NCM was not reachable,
  so `auto` transfer used serial fallback with chunk size `1800`; transfer
  wrote `1061` chunks with max cmdv1 line size `3788` under the safe limit
  `3968`. Post-deploy SHA matched, helper usage printed the v284 marker and
  immediate corrected RC1 flag, V373 post-deploy preflight returned
  `service-manager-start-only-smoke-approval-required`, and post selftest stayed
  clean. No daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
  external ping, flash, boot image write, or partition write occurred. Next is
  V1383 bounded immediate corrected RC1 live gate.
- V1383 bounded live (`v1383-corrected-rc1-ltssm-no-downstream-clean`)
  ran helper v284 with the immediate corrected RC1 flag. The block triggered at
  `late_per_proxy_poll_00` with `gate_pm_service_powerup_thread_count=1`,
  `rc_sel_rc=0`, and `case_rc=0`. Dmesg shows RC1 TEST 11, reset assert, PHY
  ready, reset release, LTSSM poll/compliance, and link initialization failure
  before L0; `__subsystem_get(esoc0)` to RC1 assert was about `3.666s`, still
  much slower than Android's about `0.255s`. GPIO142 IRQ delta, PCI/MHI counts,
  MHI pipe/`ks`, WLFW, and `wlan0` all stayed absent. Safety markers remained
  clear, cleanup completed, and no Wi-Fi bring-up/network action occurred. Next
  is V1384 host-only timing/gap classification before another live mutation.
- V1384 host-only classifier (`v1384-immediate-flag-still-too-late-poll-entry-gap`)
  compares V1383, V1379, and Android timing. V1383 improved
  `esoc0`-to-RC1 assert by only about `0.456s` versus V1379 and remains about
  `14.38x` slower than Android (`3.666s` vs `0.255s`). The pci-msm debugfs
  write path itself is not the primary delay (`TEST 11` to assert about `20us`);
  the remaining gap is before the write, in late_per_proxy poll entry or
  per_proxy/Binder/powerup-thread ordering. Another live retry without
  reordering is low value. Next is V1385 source/build-only support for an
  earlier trigger or tighter first-observation instrumentation.
- V1385 source/build-only support (`v1385-helper-v285-prepoll-corrected-rc1-ready`)
  bumps `a90_android_execns_probe` to v285 (SHA256
  `09827b6f0301f077cd0beb4ed2ae9d48a63662d0ca34eff38245704f2f724cf4`). It adds
  `--pm-observer-late-per-proxy-prepoll-corrected-rc1-enumerate`, requires the
  response and MDM2AP/PCIe timing samplers, reports the new mode in observer
  headers, and adds a pre-poll loop after late `per_proxy` spawn. The pre-poll
  loop checks `/dev/subsys_esoc0` fd ownership or `pm_service_powerup_thread`
  every `1000us` for up to `500` iterations before the main sampler loop, then
  uses the existing corrected RC1 writer. No device command was run in V1385.
  Next is V1386 deploy/preflight, then V1387 bounded live timing test.
- V1386 deploy-only preflight (`execns-helper-v285-deploy-pass`) installed
  helper v285 to `/cache/bin/a90_android_execns_probe`. NCM was not reachable,
  so `auto` transfer used serial fallback with chunk size `1800`; transfer
  wrote `1061` chunks with max cmdv1 line size `3788` under the safe limit
  `3968`. Post-deploy SHA matched, helper usage printed the v285 marker and
  pre-poll corrected RC1 flag, V373 post-deploy preflight returned
  `service-manager-start-only-smoke-approval-required`, and post selftest stayed
  clean. No daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
  external ping, flash, boot image write, or partition write occurred. Next is
  V1387 bounded pre-poll corrected RC1 live gate.
- V1387 bounded live (`v1387-corrected-rc1-ltssm-no-downstream-clean`) ran
  helper v285 with the pre-poll corrected RC1 flag. The pre-poll block emitted
  `prepoll_triggered=true`, `poll_count=0`, `elapsed_ms=119`, and the corrected
  RC1 write fired from `late_per_proxy_prepoll_000` with
  `gate_pm_service_powerup_thread_count=1`, `rc_sel_rc=0`, and `case_rc=0`.
  Dmesg shows RC1 TEST 11, reset assert, PHY ready, reset release,
  poll-compliance, and link initialization failure before L0. The
  `__subsystem_get(esoc0)` to RC1 assert delta is still about `3.561s` versus
  Android's about `0.255s`; GPIO142 IRQ delta, PCI/MHI counts, MHI pipe/`ks`,
  WLFW, and `wlan0` all stayed absent. Safety markers remained clear and no
  Wi-Fi bring-up/network action occurred. Next is V1388 host-only timing and
  Android-participant classifier before any new live mutation.
- V1388 host-only classifier (`v1388-prepoll-gate-works-but-helper-enters-it-too-late`)
  reconciled V1387 with V1384, V1379/V1383, and Android V1371 timing. V1387
  proves the v285 pre-poll writer works (`late_per_proxy_prepoll_000`,
  `poll_count=0`, `rc_sel_rc=0`, `case_rc=0`), but it starts about `3.556s`
  after `__subsystem_get(esoc0)` and only improves V1383 by `0.106s`. The
  observer already saw `thread_sample index=1 ... wchan=mdm_subsys_powerup`
  before the late-`per_proxy` response-sampler block, so the next change must
  move corrected RC1 into that earlier observer phase. V1389 should be
  source/build-only helper v286 support; do not run another same-shape live
  RC1 mutation first.
- V1389 source/build-only support (`v1389-helper-v286-early-powerup-corrected-rc1-ready`)
  bumps `a90_android_execns_probe` to v286 and adds the opt-in
  `--pm-observer-early-powerup-corrected-rc1-enumerate` flag. The new path
  fires from the early observer phase on the first visible `pm-service`
  `mdm_subsys_powerup` gate, records early phase/timing/write-state markers,
  preserves legacy late/immediate/pre-poll paths unless explicitly selected,
  and fail-closes without falling back to a later RC1 write if the early gate is
  missing. Built helper sha256:
  `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`.
  No device command, deploy, live write, Wi-Fi bring-up/network action, flash,
  boot image write, or partition write occurred. Next is V1390 deploy/preflight
  helper v286, then V1391 bounded early-observer corrected RC1 live gate.
- V1390 deploy/preflight (`execns-helper-v286-deploy-pass`) installed helper
  v286 to `/cache/bin/a90_android_execns_probe` via serial appendfile +
  uudecode fallback. Remote sha256 matches
  `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`, usage
  prints the v286 marker and early-observer flag, native version remains
  `A90 Linux init 0.9.68 (v724)`, and post-deploy selftest remains
  `pass=11 warn=1 fail=0`. Device mutation was limited to replacing the helper
  under `/cache/bin`; no daemon start, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, flash, boot image write, or partition write
  occurred. Next is V1391 bounded early-observer corrected RC1 live gate.
- V1391 bounded live (`v1391-corrected-rc1-ltssm-no-downstream-clean`) ran the
  Android participant parity window with helper v286 and the early-observer
  corrected RC1 flag. The new gate fired (`corrected_phase=early_powerup_observer`,
  `early_triggered=True`, `gate_pm_service_powerup_thread_count=1`,
  `rc_sel_rc=0`, `case_rc=0`), but dmesg still shows `__subsystem_get(esoc0)` at
  `2283.617115s` and RC1 assert at `2287.221685s` (`3.605s` delta), then PHY
  ready, reset release, poll-compliance, and link failure before L0. GPIO142
  IRQ delta, PCI/MHI counts, MHI pipe/`ks`, WLFW, and `wlan0` all remained
  absent. Safety markers remained clear and no Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, flash, boot image write, or partition
  write occurred. This makes another external-helper RC1 timing retry low-value;
  next is V1392 test-boot design to move the timing-critical experiment into
  PID1/boot flow with a separate rollbackable boot image.
- V1392 host/source plan (`v1392-plan-wifi-test-boot-pid1-timing-path`) records
  the pivot to a separate Wi-Fi test boot image:
  `docs/plans/NATIVE_INIT_V1392_WIFI_TEST_BOOT_PLAN_2026-06-01.md`. The selected
  implementation path is to bundle the verified `a90_android_execns_probe`
  helper into the test ramdisk as `/bin/a90_android_execns_probe` and invoke it
  from PID1/boot flow, initially stopping at MDM2AP/RC1/MHI/WLFW/`wlan0`
  evidence before any credentialed scan/connect, DHCP/routes, or external ping.
  V1393 is source/build-only and must not flash.
- V1393 source/build-only (`v1393-wifi-test-boot-source-build-pass`) added
  `scripts/revalidation/build_native_init_wifi_test_boot_v1393.py`, build-time
  native identity overrides, and the compile-time `A90_WIFI_TEST_BOOT` PID1
  hook. The local artifact is staged at
  `tmp/wifi/v1393-wifi-test-boot/boot_linux_v1393_wifi_test.img` with manifest
  `tmp/wifi/v1393-wifi-test-boot/manifest.json`; boot SHA256 is
  `ebb4097db71dee77cdf7a26b671a1535a8e0afe1e53b4a23400af518d4d63048`. The
  ramdisk bundles `a90_android_execns_probe v286` at
  `/bin/a90_android_execns_probe`. No device command, flash, reboot, partition
  write, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
  occurred. Next is V1394 local artifact sanity verification before any V1395
  live handoff.
- V1394 local-only artifact sanity (`v1394-wifi-test-boot-artifact-sanity-pass`)
  added `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1394.py`
  and verified the exact V1393 staged artifact. Checks passed for manifest
  decision/SHA, base boot availability, static PID1/helper, ramdisk entries,
  boot markers, v724 header parity, kernel SHA parity, private artifact modes,
  and forbidden credential-like byte absence. No device command, flash, reboot,
  partition write, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping occurred. V1395 may now be planned as the first bounded live
  handoff, naming test image
  `tmp/wifi/v1393-wifi-test-boot/boot_linux_v1393_wifi_test.img` and rollback
  `stage3/boot_linux_v724.img`.
- V1395 bounded live handoff (`v1395-test-boot-provider-trigger-no-downstream-rollback-pass`)
  added `scripts/revalidation/native_wifi_test_boot_handoff_v1395.py`, flashed
  the V1393 test boot, verified `A90 Linux init 0.9.69 (v1393-wifitest)`,
  collected evidence, and rolled back to `A90 Linux init 0.9.68 (v724)`.
  Evidence showed PID1 spawned the ramdisk helper, `pm_proxy_helper` reached
  `subsys_modem`, and Binder reached `__subsystem_get: esoc0`; no RC1 L0,
  MHI, WLFW/BDF, or `wlan0` appeared, and `/sys/class/net/wlan0` was absent.
  V1395 did not scan/connect, use credentials, run DHCP/routes, or external
  ping. Next V1396 should repeat with a longer post-boot hold before evidence
  collection and rollback, because V1395 collected immediately after bridge
  verification while the helper window is `30s`.
- V1396 bounded live handoff (`v1396-test-boot-provider-trigger-no-downstream-rollback-pass`)
  reused the V1395 handoff runner with an explicit `40s` post-boot hold before
  collection and rollback:
  `docs/reports/NATIVE_INIT_V1396_WIFI_TEST_BOOT_HOLD_HANDOFF_2026-06-01.md`.
  The test boot again verified `A90 Linux init 0.9.69 (v1393-wifitest)`, reached
  the PID1-launched helper path, `subsys_modem`, and `__subsystem_get: esoc0`,
  then rolled back to healthy `A90 Linux init 0.9.68 (v724)`. No `PCIe RC1`,
  `LTSSM`, MHI, WLFW/BDF, or `wlan0` marker appeared after the hold; `wlan0`
  remained absent. This closes the V1395 short-window ambiguity. Next V1397
  should be source/build-only: improve the Wi-Fi test boot's per-boot logging
  by truncating/rotating `/cache/native-init-wifi-test-boot-v1393.log` or writing
  a dedicated helper transcript/summary so another live handoff can compare the
  PID1-launched helper's own keys against external-helper runs.
- V1397 source/build-only (`v1397-wifi-test-boot-logging-source-build-pass`)
  implements that logging cleanup:
  `docs/reports/NATIVE_INIT_V1397_WIFI_TEST_BOOT_LOGGING_SOURCE_BUILD_2026-06-01.md`.
  The PID1 hook now truncates the per-boot log, initializes a summary file, and
  spawns a non-blocking watcher that samples helper liveness, helper `wchan`,
  helper `/proc` status, `wlan0` presence, and log size after `35s`. The V1397
  artifact is `tmp/wifi/v1397-wifi-test-boot/boot_linux_v1397_wifi_test.img`
  (`sha256=8bb427c1567b1e4d466b17d5db72db3184132e7087ba0c6d2e5682f00ddeb376`),
  built as `A90 Linux init 0.9.70 (v1397-wifitest)`. The V1395 handoff runner
  now accepts configurable expected version/log/summary/dmesg parameters for a
  later V1397 live handoff. V1397 did not issue any device command, flash,
  reboot, partition write, Wi-Fi scan/connect, credential handling,
  DHCP/routes, or external ping. Next is V1398 local artifact sanity over the
  exact V1397 manifest before any live handoff.
- V1398 local-only artifact sanity (`v1398-wifi-test-boot-artifact-sanity-pass`)
  added `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1398.py`
  and verified the exact V1397 staged artifact:
  `docs/reports/NATIVE_INIT_V1398_WIFI_TEST_BOOT_ARTIFACT_SANITY_2026-06-01.md`.
  Checks passed for manifest decision, SHA values, static PID1/helper,
  ramdisk entries, boot markers, Wi-Fi test logging contract, v724 header/kernel
  parity, forbidden credential-like byte absence, and private artifact modes.
  V1398 did not issue any device command, flash, reboot, partition write,
  Wi-Fi scan/connect, credential handling, DHCP/routes, or external ping. The
  next live gate may flash only
  `tmp/wifi/v1397-wifi-test-boot/boot_linux_v1397_wifi_test.img`, expect
  `A90 Linux init 0.9.70 (v1397-wifitest)`, collect the V1397 log and summary,
  then roll back to `stage3/boot_linux_v724.img`.
- V1399 bounded live handoff (`v1399-test-boot-provider-trigger-no-downstream-rollback-pass`)
  flashed the V1397 test boot, held `45s`, collected the V1397 fresh log and
  summary, then rolled back to healthy v724:
  `docs/reports/NATIVE_INIT_V1399_WIFI_TEST_BOOT_LOGGING_HANDOFF_2026-06-01.md`.
  The fresh log starts with `log_reset` and has one spawn sequence; the summary
  watcher sampled after `35001ms` and found helper pid `545` still present but
  `State: Z (zombie)`. Dmesg still reached `subsys_modem` and
  `__subsystem_get: esoc0`, but no `PCIe RC1`, `LTSSM`, MHI, WLFW/BDF, or
  `wlan0` appeared; `wlan0` stayed absent. V1399 did not scan/connect, use
  credentials, run DHCP/routes, or external ping. Next V1400 should be
  source/build-only: run the helper under a non-blocking supervisor child that
  waits for helper exit and records exit status/duration/timeout/log summary
  without blocking PID1 long term.
- V1400 source/build-only (`v1400-wifi-test-boot-supervisor-source-build-pass`)
  implements that supervisor path:
  `docs/reports/NATIVE_INIT_V1400_WIFI_TEST_BOOT_SUPERVISOR_SOURCE_BUILD_2026-06-01.md`.
  PID1 now forks a non-blocking supervisor child in supervised builds; the
  supervisor spawns the helper, waits with a bounded `40s` timeout, and writes
  helper wait result, timeout state, raw wait status, exit code or signal,
  log size, and `wlan0` presence into the summary. The V1400 artifact is
  `tmp/wifi/v1400-wifi-test-boot/boot_linux_v1400_wifi_test.img`
  (`sha256=461d69cdf9d0680421dea9f77b3f444f028bb4c188a964bd6d7fd98142cdd27c`),
  built as `A90 Linux init 0.9.71 (v1400-wifitest)`. V1400 did not issue any
  device command, flash, reboot, partition write, Wi-Fi scan/connect,
  credential handling, DHCP/routes, or external ping. Next is V1401 local
  artifact sanity over the exact V1400 manifest before any live handoff.
- V1401 local-only artifact sanity (`v1401-wifi-test-boot-artifact-sanity-pass`)
  added `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1401.py`
  and verified the exact V1400 staged artifact:
  `docs/reports/NATIVE_INIT_V1401_WIFI_TEST_BOOT_ARTIFACT_SANITY_2026-06-01.md`.
  Checks passed for manifest decision, SHA values, static PID1/helper, ramdisk
  entries, boot markers, supervised-helper contract, v724 header/kernel parity,
  forbidden credential-like byte absence, and private artifact modes. V1401 did
  not issue any device command, flash, reboot, partition write, Wi-Fi
  scan/connect, credential handling, DHCP/routes, or external ping. The next
  live gate may flash only
  `tmp/wifi/v1400-wifi-test-boot/boot_linux_v1400_wifi_test.img`, expect
  `A90 Linux init 0.9.71 (v1400-wifitest)`, collect the V1400 log and summary,
  then roll back to `stage3/boot_linux_v724.img`.
- V1402 bounded live handoff (`v1402-test-boot-provider-trigger-no-downstream-rollback-pass`)
  flashed the V1400 supervised test boot, held `50s`, collected the V1400 log
  and summary, then rolled back to healthy v724:
  `docs/reports/NATIVE_INIT_V1402_WIFI_TEST_BOOT_SUPERVISOR_HANDOFF_2026-06-01.md`.
  The supervisor path worked: it recorded `helper_wait_rc=0`,
  `helper_timed_out=0`, `helper_status_raw=0`, and `helper_exit_code=0`.
  Dmesg still reached `subsys_modem` and `__subsystem_get: esoc0`, but no
  `PCIe RC1`, `LTSSM`, MHI, WLFW/BDF, or `wlan0` appeared; `wlan0` stayed
  absent. V1402 did not scan/connect, use credentials, run DHCP/routes, or
  external ping. Next V1403 should be source/build-only: make the helper/test
  boot summary emit a strict downstream-progress decision so provider-trigger
  diagnostics are not mistaken for Wi-Fi progress.
- V1403 host-only strict classifier (`v1403-test-boot-provider-trigger-no-downstream-wifi-progress-blocked`)
  updated `scripts/revalidation/native_wifi_test_boot_handoff_v1395.py` so
  test-boot handoff evidence now emits explicit Wi-Fi progress fields:
  `provider_trigger`, `rc1_progress`, `mhi_progress`, `wlfw_progress`,
  `bdf_progress`, `fw_ready_progress`, `wlan0_present`, `connect_ready`, and
  `final_decision`. It then reclassified the V1402 evidence in strict mode:
  `handoff_pass=true` but `wifi_progress_pass=false`, with final decision
  `provider-trigger-no-downstream`. Report:
  `docs/reports/NATIVE_INIT_V1403_STRICT_WIFI_PROGRESS_CLASSIFIER_2026-06-01.md`.
  No device command, flash, reboot, credential handling, Wi-Fi scan/connect,
  DHCP/routes, external ping, PMIC/GPIO/GDSC write, or eSoC notify/`BOOT_DONE`
  spoof was performed in V1403. Next work should target why the supervised
  provider trigger creates no RC1/MHI/WLFW downstream marker.
- V1404 source/build-only (`v1404-wifi-test-boot-debugfs-source-build-pass`)
  adds an opt-in `A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS=1` path to the rollbackable
  Wi-Fi test boot and stages
  `tmp/wifi/v1404-wifi-test-boot-debugfs/boot_linux_v1404_wifi_test.img`.
  This artifact keeps the supervised helper but prepares `/sys/kernel/debug`
  before spawn so the helper's existing corrected RC1 enumerate path can open
  `/sys/kernel/debug/pci-msm/rc_sel` and `case`. Local sanity passed for static
  init/helper, ramdisk entries, boot markers, v724 header/kernel parity,
  manifest contract, and forbidden credential-like byte absence. Report:
  `docs/reports/NATIVE_INIT_V1404_WIFI_TEST_BOOT_DEBUGFS_SOURCE_BUILD_2026-06-01.md`.
  V1404 issued no device command, flash, reboot, credential handling,
  Wi-Fi scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write,
  or eSoC notify/`BOOT_DONE` spoof. V1405 should independently sanity-check
  the exact artifact before any V1406 handoff.
- V1405 local-only artifact sanity (`v1405-wifi-test-boot-debugfs-artifact-sanity-pass`)
  adds `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1405.py`
  and verifies the exact V1404 artifact. Checks passed for V1404 manifest
  decision, static init/helper, ramdisk entries, boot markers, debugfs test-boot
  contract (`mount_debugfs=true`), v724 header/kernel parity, private modes,
  and forbidden credential-like byte absence. Report:
  `docs/reports/NATIVE_INIT_V1405_WIFI_TEST_BOOT_DEBUGFS_ARTIFACT_SANITY_2026-06-01.md`.
  No device command, flash, reboot, credential handling, Wi-Fi scan/connect,
  DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, or eSoC
  notify/`BOOT_DONE` spoof occurred. V1406 may run the rollbackable handoff of
  only `tmp/wifi/v1404-wifi-test-boot-debugfs/boot_linux_v1404_wifi_test.img`.
- V1406 rollbackable live handoff (`v1406-test-boot-rc1-ltssm-link-failed-no-l0-rollback-pass`)
  flashed only the V1404 debugfs-prepared test boot, held `65s`, collected
  V1404 log/summary/dmesg/`wlan0`, and rolled back to healthy v724. The V1404
  hook fixed the prior missing-debugfs issue: summary recorded
  `debugfs_mount_requested=1`, `debugfs_mounted_by_pid1=1`, and
  `debugfs_pci_msm_case_present=1`. Dmesg then showed `PCIe: TEST: 11`,
  RC1 PHY-ready, and LTSSM `DETECT_QUIET`/`POLL_ACTIVE`/`POLL_COMPLIANCE`, but
  ended in `PCIe RC1 link initialization failed (LTSSM_STATE:0x3)`. No
  MHI/WLFW/BDF/FW-ready/`wlan0` appeared and `connect_ready=false`. Report:
  `docs/reports/NATIVE_INIT_V1406_WIFI_TEST_BOOT_DEBUGFS_HANDOFF_2026-06-01.md`.
  The device was verified back on `A90 Linux init 0.9.68 (v724)` with selftest
  fail=0. Next V1407 should be host-only endpoint-readiness classification; do
  not scan/connect or use credentials.
- V1464 rollbackable live handoff (`v1464-test-boot-provider-trigger-no-downstream-rollback-pass`)
  flashed only the V1462 exact-provider tracepoint test boot, verified
  `A90 Linux init 0.9.86 (v1462-wifitest)`, collected the V1462 log/summary,
  exact-provider tracepoint window, dmesg markers, and `wlan0` state, then
  rolled back to healthy `A90 Linux init 0.9.68 (v724)` with selftest fail=0.
  The handoff reached the exact `__subsystem_get: esoc0` provider trigger but
  no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress appeared. Report:
  `docs/reports/NATIVE_INIT_V1464_WIFI_TEST_BOOT_EXACT_PROVIDER_TRACEPOINT_HANDOFF_2026-06-01.md`.
- V1465 host-only classifier (`v1465-pon-toggles-ap2mdm-absent-no-downstream`)
  classifies the V1464 exact-provider GPIO tracepoint evidence. Tracepoints
  prove GPIO1270/PON toggles low-high and GPIO141 goes low, while GPIO135/AP2MDM
  and GPIO142/MDM2AP never emit trace events. Endpoint snapshots keep GPIO135
  `out 0`, GPIO142 `in 0`, MDM status and PCIe wake IRQs at zero, pcie1 GDSC
  at `0mV`, and pcie1 clocks zero-enabled. No RC1/MHI/WLFW/BDF/FW-ready/`wlan0`
  progress appears, so this remains below Wi-Fi HAL/scan/connect readiness.
  Report: `docs/reports/NATIVE_INIT_V1465_PROVIDER_TRACEPOINT_CLASSIFIER_2026-06-01.md`.
  Next V1466 is host-only provider AP2MDM branch/source classification before
  any new live mutation.
- V1466 host-only classifier (`v1466-ap2mdm-branch-divergence-needs-pil-parity-test-boot`)
  reconciles V1464/V1465 with V1318 and source/static provider evidence. V1464
  proves the test boot reaches the PON side (`GPIO1270` low-high, about
  `180.115ms`) but records zero GPIO135/AP2MDM and zero GPIO142/MDM2AP events.
  V1318 proves an earlier native PM path captured `fw=esoc0` PIL notifications,
  PON trace, and GPIO135/AP2MDM high while still missing GPIO142. The current
  PID1 sampler lacks `msm_pil_event:pil_notif` parity, so V1467 should be
  source/build-only and add PIL notification tracepoint sampling to the
  exact-provider GPIO tracepoint test boot before any new live mutation.
  Report: `docs/reports/NATIVE_INIT_V1466_PROVIDER_AP2MDM_BRANCH_CLASSIFIER_2026-06-01.md`.
- V1467 source/build-only (`v1467-wifi-test-boot-exact-provider-pil-gpio-tracepoint-source-build-pass`)
  adds `A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER` to the
  rollbackable PID1 test-boot path. The V1467 artifact keeps the exact provider
  trigger, thread-state sampler, long endpoint window, and GPIO tracepoints,
  then additionally arms `msm_pil_event:pil_notif` and samples `fw=esoc0`
  trace lines under sampler marker
  `read-only-v1467-exact-provider-pil-gpio-tracepoint`. Built boot image:
  `tmp/wifi/v1467-wifi-test-boot-exact-provider-pil-gpio-tracepoint-sampler/boot_linux_v1467_wifi_test.img`
  (`sha256=e9fd747a483f9d5d22126ddda0f99c0a4b5b4b5343f20094d1d5d8cf3adb359e`),
  native init `0.9.87 (v1467-wifitest)`. Static init/helper verification,
  ramdisk entry verification, boot marker verification, and forbidden
  credential-like byte scan passed. V1467 issued no device command, flash,
  reboot, Wi-Fi HAL, scan/connect, DHCP/routes, external ping, or partition
  write. Report:
  `docs/reports/NATIVE_INIT_V1467_WIFI_TEST_BOOT_EXACT_PROVIDER_PIL_GPIO_TRACEPOINT_SOURCE_BUILD_2026-06-01.md`.
  V1468 should be local-only artifact sanity over the exact V1467 manifest.
- V1468 local-only artifact sanity (`v1468-wifi-test-boot-exact-provider-pil-gpio-tracepoint-artifact-sanity-pass`)
  verifies the exact V1467 manifest, boot image, static PID1/helper binaries,
  ramdisk entries, exact-provider PIL+GPIO tracepoint marker contract, absent
  retry/legacy/case-writer markers, v724 header/kernel parity, forbidden
  credential-like byte absence, private modes, and the V1467 contract
  (`provider_trigger_tracepoint_sampler=true`,
  `provider_trigger_pil_tracepoint_sampler=true`,
  `provider_trigger_thread_state=true`, `provider_trigger_exact_line=true`,
  `provider_trigger_long_window=true`, `rc1_watcher_delay_ms=0`,
  `rc1_retry_count=0`). V1469 may be a rollbackable live handoff for only the
  V1467 image, expecting `A90 Linux init 0.9.87 (v1467-wifitest)`, collecting
  the V1467 log, summary, RC1 watcher result, exact-provider PIL+GPIO
  tracepoint window result, expanded dmesg markers, and `wlan0` state, then
  rolling back to `stage3/boot_linux_v724.img` and verifying selftest fail=0.
  Report:
  `docs/reports/NATIVE_INIT_V1468_WIFI_TEST_BOOT_EXACT_PROVIDER_PIL_GPIO_TRACEPOINT_ARTIFACT_SANITY_2026-06-01.md`.
- V1469 rollbackable live handoff
  (`v1469-test-boot-provider-trigger-no-downstream-rollback-pass`) flashed only
  the V1467 exact-provider PIL+GPIO tracepoint test boot, collected the V1467
  log, summary, RC1 watcher/window results, dmesg markers, and `wlan0` state,
  then rolled back from native to `stage3/boot_linux_v724.img`; post-rollback
  selftest stayed healthy. The test boot reached both modem and esoc0 provider
  triggers, but no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress appeared. Report:
  `docs/reports/NATIVE_INIT_V1469_WIFI_TEST_BOOT_EXACT_PROVIDER_PIL_GPIO_TRACEPOINT_HANDOFF_2026-06-01.md`.
- V1470 host-only classifier
  (`v1470-ap2mdm-set-called-but-not-effective-no-mdm2ap-no-rc1`) classifies the
  V1469 evidence. It proves `fw=esoc0` PIL notification parity, PON low-high,
  and a GPIO135/AP2MDM set-high call about `306.356ms` after the esoc0 PIL
  start. The live readback samples still show zero GPIO135 high samples, zero
  GPIO142 high samples, zero MDM status IRQ increments, zero PCIe wake IRQ
  increments, and no RC1/MHI/WLFW/BDF/FW-ready/`wlan0`. Next gate: V1471
  host-only AP2MDM effective-level and pinctrl ownership classifier. Report:
  `docs/reports/NATIVE_INIT_V1470_PROVIDER_PIL_GPIO_CLASSIFIER_2026-06-01.md`.
- V1471 host-only classifier
  (`v1471-ap2mdm-active-pinctrl-present-effective-output-low`) reconciles V1470
  with OSRC DTS and tracepoint source. `gpio_direction: ... out (0)` is the
  tracepoint's error code, while `gpio_value: 135 set 1` is the actual AP2MDM
  set-high call. DTS maps GPIO135 to AP2MDM and includes active pinctrl
  (`gpio`, 16mA, bias disabled); V1469 live readback also shows that active
  config. The remaining gap is effective output/readback: GPIO135 stays sampled
  low, GPIO142/MDM2AP stays low, IRQs stay zero, and no RC1/MHI/WLFW/BDF
  /FW-ready/`wlan0` appears. Next gate: V1472 source/build-only extended AP2MDM
  effective-level sampler. Report:
  `docs/reports/NATIVE_INIT_V1471_AP2MDM_EFFECTIVE_LEVEL_CLASSIFIER_2026-06-01.md`.
- V1472 source/build-only test boot
  (`v1472-wifi-test-boot-effective-level-source-build-pass`) adds
  `A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EFFECTIVE_LEVEL_SAMPLER` to the
  rollbackable PID1 Wi-Fi test-boot path. The artifact keeps exact provider
  triggering, thread-state sampling, GPIO tracepoints, and PIL notification
  tracepoints, then extends provider-trigger samples through `3000ms` with
  dense points around the AP2MDM set-high window. It also emits full read-only
  endpoint/pinctrl/regulator/clock snapshots for provider samples at and after
  `250ms`. Built boot image:
  `tmp/wifi/v1472-wifi-test-boot-exact-provider-effective-level-sampler/boot_linux_v1472_wifi_test.img`
  (`sha256=2835568c31f9a9a25dac6e7830cdb51d666bdd050bf16646fa1518b8d7ed1e02`),
  native init `0.9.88 (v1472-wifitest)`. V1473 should be local-only artifact
  sanity over the exact V1472 manifest before any rollbackable live handoff.
  Report:
  `docs/reports/NATIVE_INIT_V1472_WIFI_TEST_BOOT_EFFECTIVE_LEVEL_SOURCE_BUILD_2026-06-01.md`.
- V1473 local-only artifact sanity
  (`v1473-wifi-test-boot-effective-level-artifact-sanity-pass`) verifies the
  exact V1472 manifest, base boot, static init/helper binaries, ramdisk entries,
  boot markers, absent retry/legacy/case-writer markers, v724 header/kernel
  parity, forbidden credential-like byte absence, private modes, and the
  effective-level sampler contract. V1474 may be a rollbackable live handoff
  for only the V1472 image, expecting `A90 Linux init 0.9.88 (v1472-wifitest)`,
  collecting the V1472 log, summary, RC1 watcher result, effective-level window
  result, expanded dmesg markers, and `wlan0` state, then rolling back to
  `stage3/boot_linux_v724.img` and verifying selftest fail=0. Report:
  `docs/reports/NATIVE_INIT_V1473_WIFI_TEST_BOOT_EFFECTIVE_LEVEL_ARTIFACT_SANITY_2026-06-01.md`.
- V1474 rollbackable live handoff
  (`v1474-test-boot-provider-trigger-no-downstream-rollback-pass`) flashed only
  the V1472 effective-level test image, verified
  `A90 Linux init 0.9.88 (v1472-wifitest)`, collected the V1472 log/summary,
  effective-level window, expanded dmesg markers, and `wlan0` state, then
  rolled back from native to healthy `A90 Linux init 0.9.68 (v724)` with
  selftest fail=0. The run reached the modem and esoc0 provider triggers and
  emitted the V1472 marker, but no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress
  appeared. Report:
  `docs/reports/NATIVE_INIT_V1474_WIFI_TEST_BOOT_EFFECTIVE_LEVEL_HANDOFF_2026-06-01.md`.
- V1475 host-only classifier
  (`v1475-effective-level-low-pcie1-off-through-extended-window`) classifies
  V1474 evidence. The extended sampler closes the short-window explanation:
  full snapshots covered provider samples at `250ms`, `300ms`, `320ms`,
  `350ms`, `400ms`, and `500ms`, with the last full snapshot completing at
  `56754ms` child elapsed because read-only debugfs snapshots are slow. Despite
  the AP2MDM set-high trace and mdm3 pinmux ownership, GPIO135 stayed sampled
  low, GPIO142 stayed low, pcie1 GDSC stayed `0mV`, pcie1 pipe clock stayed
  zero-enabled, and RC1/MHI/WLFW/BDF/FW-ready/`wlan0` stayed absent. Next gate:
  V1476 host-only lower-intervention design review before any write-based
  experiment. Do not proceed to Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, direct PMIC/GPIO/GDSC writes, blind eSoC
  notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind from this
  state. Report:
  `docs/reports/NATIVE_INIT_V1475_EFFECTIVE_LEVEL_LIVE_CLASSIFIER_2026-06-01.md`.
- V1476 host-only design gate
  (`v1476-select-ap2mdm-bounded-hold-test-boot-design`) selects the next
  rollbackable test-boot direction. Upper Wi-Fi actions are rejected because
  `wlan0` is absent. Repeating only corrected RC1 `rc_sel=2` + `case=11` is
  rejected as the next step because V1370/V1372/V1391/V1447 already reached
  LTSSM without L0 when MDM2AP stayed silent. Direct PON and unspecific
  GDSC/clock writes are also rejected. The selected path is V1477
  source/build-only support for an explicit AP2MDM bounded-hold test-boot mode:
  after the provider trigger and AP2MDM set-high trace, confirm GPIO135 still
  reads low, then attempt only a narrow bounded GPIO135 hold if the userspace
  line interface permits it, sample GPIO135/GPIO142/pcie1/LTSSM/MHI/WLFW
  /`wlan0`, release, and later use rollback handoff. V1476 itself ran no device
  command, build, flash, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
  external ping, PMIC/GDSC write, eSoC notify, global PCI rescan, platform
  bind/unbind, boot image write, or partition write. Plan:
  `docs/plans/NATIVE_INIT_V1476_LOWER_INTERVENTION_DESIGN_2026-06-01.md`.
- V1477 source/build-only test boot
  (`v1477-wifi-test-boot-ap2mdm-hold-source-build-pass`) adds a compile-time
  gated AP2MDM bounded-hold mode to the rollbackable PID1 Wi-Fi test-boot path.
  Built image:
  `tmp/wifi/v1477-wifi-test-boot-ap2mdm-hold/boot_linux_v1477_wifi_test.img`
  (`sha256=8fc89079ce7301a801d73153aee0ad7c7dd70cec55b9270b5ea48a64127bd577`),
  native init `0.9.89 (v1477-wifitest)`, init sha256
  `d48a6214a2de8f9799fbb3dad41717380f90e6b28cbcd1fb5e3fc50bf4c866e9`. The
  marker is `bounded-v1477-ap2mdm-hold-test`; it waits for the provider/AP2MDM
  set-high trace, confirms GPIO135 still reads low, attempts GPIO135 hold only
  through `/sys/class/gpio` if permitted, samples GPIO135/GPIO142/pcie1/LTSSM
  /MHI/WLFW/`wlan0`, then releases and unexports if exported. V1477 issued no
  device command, flash, reboot, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, or partition write. Next V1478 should be
  local-only artifact sanity before any rollbackable live handoff. Report:
  `docs/reports/NATIVE_INIT_V1477_WIFI_TEST_BOOT_AP2MDM_HOLD_SOURCE_BUILD_2026-06-01.md`.
- V1478 local-only artifact sanity
  (`v1478-wifi-test-boot-ap2mdm-hold-artifact-sanity-pass`) verifies the exact
  V1477 manifest, base boot, static init/helper binaries, ramdisk entries, boot
  markers, legacy marker absence, v724 header/kernel parity, forbidden
  credential-like byte absence, private modes, and AP2MDM hold contract. V1479
  may be a rollbackable live handoff for only the V1477 image, expecting
  `A90 Linux init 0.9.89 (v1477-wifitest)`, collecting V1477 log, summary, RC1
  watcher result, AP2MDM hold window result, expanded dmesg markers, and
  `wlan0` state, then rolling back to `stage3/boot_linux_v724.img` and
  verifying selftest fail=0. Report:
  `docs/reports/NATIVE_INIT_V1478_WIFI_TEST_BOOT_AP2MDM_HOLD_ARTIFACT_SANITY_2026-06-01.md`.
- V1479 rollbackable live handoff
  (`v1479-test-boot-provider-trigger-no-downstream-rollback-pass`) flashed only
  the V1477 AP2MDM hold test boot, verified
  `A90 Linux init 0.9.89 (v1477-wifitest)`, collected the V1477 log/summary,
  RC1 watcher/window result, dmesg markers, and `wlan0` state, then rolled back
  from native to healthy v724. The test reached the provider trigger and
  AP2MDM hold gate but still produced no RC1/MHI/WLFW/BDF/FW-ready/`wlan0`
  progress. Report:
  `docs/reports/NATIVE_INIT_V1479_WIFI_TEST_BOOT_AP2MDM_HOLD_HANDOFF_2026-06-01.md`.
- V1480 host-only classifier
  (`v1480-ap2mdm-userspace-hold-refused-busy-no-downstream`) classifies V1479.
  The AP2MDM hold gate saw the provider AP2MDM set-high trace and confirmed
  GPIO135 low, but `/sys/class/gpio` export for GPIO135 returned `-16`
  (`EBUSY`), so no userspace hold was applied (`exported=0`,
  `direction_high_rc=-125`). GPIO135/GPIO142 stayed low, pcie1 GDSC stayed off,
  and no downstream Wi-Fi markers appeared. Do not retry this exact userspace
  GPIO hold. Next gate: V1481 host-only kernel-provider feasibility review or
  another lower-prerequisite hypothesis that does not fight the kernel-owned
  GPIO line. Report:
  `docs/reports/NATIVE_INIT_V1480_AP2MDM_HOLD_LIVE_CLASSIFIER_2026-06-01.md`.
- V1481 host-only classifier
  (`v1481-userspace-hold-closed-kernel-provider-not-live-feasible`) reconciles
  V1480 with Samsung OSRC GPIO source and DTS. The sysfs export path calls
  `gpiod_request(desc, "sysfs")`; `__gpiod_request()` returns `-EBUSY` if the
  GPIO descriptor already has `FLAG_REQUESTED`. The DTS assigns GPIO135 to
  `qcom,ap2mdm-status-gpio` under `mdm3`, so V1480's `export_rc=-16` is the
  expected kernel-owned-line result. Retrying userspace GPIO hold is closed.
  Kernel-provider patching is the direct layer for changing AP2MDM behavior,
  but not currently live-feasible because the local Samsung OSRC custom-kernel
  route remains boot-incompatible from V771/V774/V775. Direct MMIO/pinctrl/GPIO
  writes and blind RC1 retries remain rejected. Next gate: V1482 host-only
  Android AP2MDM effective-level reference classifier before building another
  Wi-Fi auto-start test boot; decide whether GPIO135 readback is misleading or
  a real native-only response failure. Report:
  `docs/reports/NATIVE_INIT_V1481_AP2MDM_PROVIDER_FEASIBILITY_2026-06-01.md`.
- V1482 host-only classifier
  (`v1482-android-gpio135-low-not-primary-gate-next-auto-boot-supervisor`)
  reconciles the current GPIO/AP2MDM branch with Android-positive evidence.
  V914 shows Android can reach service-notifier, WLFW, WLAN-PD, BDF, and
  `wlan0` while post-boot lower diagnostics still show `subsys9=OFFLINING`,
  GPIO142 IRQ total `0`, no current `ks`, and no current MHI pipe. V1291 shows
  static GPIO parity between native and Android: GPIO135 `out 0 16mA no pull`
  and GPIO142 `in 0 8mA no pull`. Therefore GPIO135/GPIO142 low readback is
  not enough to justify another GPIO-hold cycle. Next gate: V1483
  source/build-only design for a rollbackable, credential-free Wi-Fi readiness
  test boot that automatically runs the Android-order provider/CNSS readiness
  chain at boot. Primary checkpoints should be WLFW, ICNSS/QMI or WLFW service
  progress, BDF, FW-ready, and `wlan0`; GPIO135/GPIO142/pcie1/MHI remain
  diagnostics. Do not use credentials, scan/connect, DHCP/routes, or external
  ping until `wlan0` exists. Report:
  `docs/reports/NATIVE_INIT_V1482_ANDROID_AP2MDM_REFERENCE_CLASSIFIER_2026-06-01.md`.
- V1483 plan
  (`v1483-plan-auto-readiness-test-boot-before-credentials`) defines the next
  implementation sequence for the user's dedicated Wi-Fi test boot direction.
  First add a compact helper readiness summary (`auto_readiness.*`) that tracks
  WLFW, ICNSS/QMI or WLFW service progress, BDF, FW-ready, `wlan0`, GPIO135/142,
  pcie1, MHI, `ks`, and safety zeros. Then build a rollbackable credential-free
  PID1 test image that automatically runs one Android-order provider/CNSS
  readiness route at boot. Keep scan/connect, credentials, DHCP/routes,
  external ping, direct PMIC/GPIO/GDSC writes, raw MMIO/pinctrl writes, blind
  eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, and custom
  OSRC kernel flash blocked. Next gate: V1484 source/build-only helper support
  for the compact readiness summary. Plan:
  `docs/plans/NATIVE_INIT_V1483_WIFI_AUTO_READINESS_TEST_BOOT_PLAN_2026-06-01.md`.
- V1484 source/build-only
  (`v1484-auto-readiness-helper-build-pass`) updates
  `a90_android_execns_probe` to v287 and adds
  `--pm-observer-auto-readiness-summary`. The flag requires the existing
  bounded mdm2ap timing sampler and emits `auto_readiness.*` keys for CNSS
  daemon/diag start, WLFW start/request, ICNSS/QMI, BDF, FW-ready, `wlan0`,
  GPIO142 IRQ delta, pcie1 state, MHI/pipe/`ks`, and safety zeros. Built helper:
  `stage3/linux_init/helpers/a90_android_execns_probe_v287`, sha256
  `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`, static
  aarch64 with no dynamic section. V1484 ran no device command or live action.
  Next gate: V1485 source/build-only PID1 test-boot wrapper that bundles helper
  v287 and passes the readiness summary flag. Report:
  `docs/reports/NATIVE_INIT_V1484_AUTO_READINESS_HELPER_SOURCE_BUILD_2026-06-01.md`.
- V1485 source/build-only
  (`v1485-wifi-auto-readiness-test-boot-source-build-pass`) builds the
  rollbackable credential-free auto-readiness test boot. The v1393 builder now
  expects helper v287 and supports
  `A90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR`; the PID1 test image passes
  `--pm-observer-auto-readiness-summary` and emits marker
  `auto-v1485-wifi-readiness-test`. Built image:
  `tmp/wifi/v1485-wifi-auto-readiness-test-boot/boot_linux_v1485_wifi_test.img`
  (`sha256=7d3a59fe5fe4cd683bd830491c5ccf7e5b3aea1271558b320f6fe7e76ad1ac23`),
  native init `0.9.90 (v1485-wifitest)`, init sha256
  `9eb11472596e316f4c993428b32cde263aa6a7baa29fdabff0f56c261efbee54`. V1485
  ran no device command or live action. Next gate: V1486 local-only artifact
  sanity over the exact manifest before any V1487 rollbackable live handoff.
  Report:
  `docs/reports/NATIVE_INIT_V1485_WIFI_AUTO_READINESS_TEST_BOOT_SOURCE_BUILD_2026-06-01.md`.
- V1486 local-only artifact sanity
  (`v1486-wifi-auto-readiness-artifact-sanity-pass`) verifies the exact V1485
  manifest and image. Checks passed for static init/helper binaries, ramdisk
  entries, boot markers, AP2MDM hold marker absence, auto-readiness contract,
  v724 header/kernel parity, forbidden credential-like byte absence, and private
  modes. Verified image:
  `tmp/wifi/v1485-wifi-auto-readiness-test-boot/boot_linux_v1485_wifi_test.img`
  (`sha256=7d3a59fe5fe4cd683bd830491c5ccf7e5b3aea1271558b320f6fe7e76ad1ac23`).
  Next gate: V1487 rollbackable live handoff for only the V1485 image, collect
  log/summary/focused dmesg/`wlan0`, then roll back to
  `stage3/boot_linux_v724.img` and verify selftest `fail=0`. Report:
  `docs/reports/NATIVE_INIT_V1486_WIFI_AUTO_READINESS_ARTIFACT_SANITY_2026-06-01.md`.
- V1487 rollbackable live handoff
  (`v1487-test-boot-provider-trigger-no-downstream-wifi-progress-blocked`)
  flashed only the V1485 auto-readiness test image, collected evidence, and
  rolled back to v724 successfully. The test boot reached
  `__subsystem_get: modem` and `__subsystem_get: esoc0`, but no PCIe RC1/LTSSM,
  MHI, WLFW, BDF, FW-ready, or `wlan0` marker appeared; `wlan0=absent`. PID1
  summary confirmed `auto_readiness_supervisor_requested=1` and
  `auto-v1485-wifi-readiness-test`, but the helper timed out
  (`helper_wait_rc=-110`, `helper_timed_out=1`) before buffered
  `auto_readiness.*` output was emitted. Next gate: V1488 should make the
  readiness result timeout-safe, either by sidecar persistence before helper
  cleanup can block or by PID1 synthesized readiness from focused dmesg/`wlan0`
  after the bounded helper timeout. Report:
  `docs/reports/NATIVE_INIT_V1487_WIFI_AUTO_READINESS_HANDOFF_2026-06-01.md`.
- V1488 source/build-only
  (`v1488-wifi-auto-readiness-timeout-safe-test-boot-source-build-pass`) adds
  PID1-synthesized `auto_readiness_pid1.*` keys so the V1485-style readiness
  evidence remains observable even when the helper times out before flushing
  buffered stdout. PID1 uses `SYSLOG_ACTION_READ_ALL` and `wlan0` sysfs state to
  classify modem/provider trigger, PCIe RC1/LTSSM, MHI, WLFW, ICNSS/QMI, BDF,
  FW-ready, and `wlan0`, while keeping Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, PMIC/GPIO/GDSC writes, and direct eSoC ioctl
  blocked. Built image:
  `tmp/wifi/v1488-wifi-auto-readiness-timeout-safe-test-boot/boot_linux_v1488_wifi_test.img`
  (`sha256=3d18c340e69f5f448be27fca370479e06b19bccb3a903a797ca3f5b0181eac32`),
  native init `0.9.91 (v1488-wifitest)`, init sha256
  `290b59d23fd29ca862a716992f34e3c753fdceb36fa69781531178003dc209ce`. Next
  gate: V1489 local artifact sanity over the exact V1488 manifest. Report:
  `docs/reports/NATIVE_INIT_V1488_WIFI_AUTO_READINESS_TIMEOUT_SAFE_SOURCE_BUILD_2026-06-01.md`.
- V1489 local-only artifact sanity
  (`v1489-wifi-auto-readiness-timeout-safe-artifact-sanity-pass`) verifies the
  exact V1488 manifest, static init/helper binaries, ramdisk entries, timeout-
  safe `auto_readiness_pid1.*` markers, AP2MDM hold marker absence, v724
  header/kernel parity, forbidden credential-like byte absence, and private
  artifact modes. Verified boot image:
  `tmp/wifi/v1488-wifi-auto-readiness-timeout-safe-test-boot/boot_linux_v1488_wifi_test.img`
  (`sha256=3d18c340e69f5f448be27fca370479e06b19bccb3a903a797ca3f5b0181eac32`).
  Next gate: V1490 rollbackable live handoff for only the V1488 image, collect
  V1488 log/summary/focused dmesg/`wlan0`, then roll back to v724 and verify
  selftest `fail=0`. Report:
  `docs/reports/NATIVE_INIT_V1489_WIFI_AUTO_READINESS_TIMEOUT_SAFE_ARTIFACT_SANITY_2026-06-01.md`.
- V1490 rollbackable live handoff
  (`v1490-timeout-safe-provider-trigger-no-downstream-manual-rollback-pass`)
  proved the V1488 timeout-safe PID1 summary works: syslog read succeeded,
  modem/provider trigger were seen, primary checkpoint was `provider-trigger`,
  and PCIe RC1, MHI, WLFW, ICNSS/QMI, BDF, FW-ready, and `wlan0` were all
  absent. The generic TWRP rollback path failed because recovery ADB never
  appeared after the native `recovery` command. Manual native rollback then
  succeeded by downloading the v724 image over NCM HTTP to
  `/cache/boot_linux_v724.img`, creating `/dev/block/sda24` for the boot
  partition (`259:8`), writing it, verifying the boot prefix sha256, rebooting,
  and confirming `A90 Linux init 0.9.68 (v724)` plus selftest `fail=0`. Next
  gate: V1491 should add an explicit native direct rollback fallback for future
  handoff runners before more test-boot flashes. Report:
  `docs/reports/NATIVE_INIT_V1490_WIFI_AUTO_READINESS_TIMEOUT_SAFE_HANDOFF_2026-06-01.md`.
- V1491 source-only safety update
  (`v1491-native-direct-rollback-fallback-source-pass`) updates the shared
  Wi-Fi test-boot handoff runner with `--native-direct-rollback-fallback`.
  When enabled, rollback first tries the generic TWRP route; if recovery ADB is
  unavailable, it can verify a pre-staged `/cache/boot_linux_v724.img`, create
  `/dev/block/sda24` (`259:8`) if missing, write the boot partition, verify the
  boot prefix sha256, reboot, and verify the expected rollback version through
  the serial bridge. V1491 performed no live mutation. Next gate: V1492 may run
  a bounded live handoff with this fallback after pre-staging the v724 rollback
  image on-device. Report:
  `docs/reports/NATIVE_INIT_V1491_NATIVE_DIRECT_ROLLBACK_FALLBACK_SOURCE_2026-06-01.md`.
- V1492 rollbackable live handoff
  (`v1492-test-boot-provider-trigger-no-downstream-wifi-progress-blocked`) adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1492.py` and reruns the
  V1488 timeout-safe auto-readiness test boot with
  `--native-direct-rollback-fallback` enabled. The on-device rollback image at
  `/cache/boot_linux_v724.img` matched the expected v724 sha256 before the run.
  Handoff and rollback passed through the generic from-native route, and the
  device returned to `A90 Linux init 0.9.68 (v724)` with selftest `fail=0`.
  The test boot again reached modem/provider trigger but produced no PCIe
  RC1/LTSSM, MHI, WLFW, ICNSS/QMI, BDF, FW-ready, or `wlan0`; strict Wi-Fi
  progress remains blocked. Next gate: do not materialize credentials or
  attempt scan/connect yet; add a narrower rollbackable test boot that captures
  RC1/MHI prerequisites during the same boot-time auto path. Report:
  `docs/reports/NATIVE_INIT_V1492_WIFI_AUTO_READINESS_NATIVE_ROLLBACK_HANDOFF_2026-06-01.md`.
- V1493 source/build-only
  (`v1493-wifi-auto-readiness-rc1-window-test-boot-source-build-pass`) adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1493.py` and builds a
  credential-free rollbackable test boot that keeps the V1488 timeout-safe
  auto-readiness path while enabling PID1 RC1 watcher and RC1 window sampler.
  Built image:
  `tmp/wifi/v1493-wifi-auto-readiness-rc1-window-test-boot/boot_linux_v1493_wifi_test.img`
  (`sha256=bc1a6484eb8786323b2a534b099839db32ad627d7688395265c63b647ed56c8e`),
  native init `0.9.92 (v1493-wifitest)`, init sha256
  `8dce5a6515fa427bb3bd2b89bceda518c989c9978b3bd42049e2ba9eb96d3347`, helper
  sha256 `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`.
  V1493 ran no device command or live action. Next gate: V1494 local artifact
  sanity over the exact V1493 manifest before another rollbackable live
  handoff. Report:
  `docs/reports/NATIVE_INIT_V1493_WIFI_AUTO_READINESS_RC1_WINDOW_SOURCE_BUILD_2026-06-01.md`.
- V1494 local-only artifact sanity
  (`v1494-wifi-auto-readiness-rc1-window-artifact-sanity-pass`) verifies the
  exact V1493 manifest and image. Checks passed for manifest decision, static
  init/helper, ramdisk entries, boot markers, AP2MDM-hold marker absence,
  v724 header/kernel parity, private artifact modes, forbidden credential-like
  byte absence, and the enabled RC1 watcher/window contract. V1494 ran no
  device command or live action. Next gate: V1495 rollbackable live handoff for
  only the V1493 image, collecting V1493 log/summary, RC1 watcher/window
  results, focused dmesg, and `wlan0`, then rolling back to v724 and verifying
  selftest `fail=0`. Report:
  `docs/reports/NATIVE_INIT_V1494_WIFI_AUTO_READINESS_RC1_WINDOW_ARTIFACT_SANITY_2026-06-01.md`.
- V1495 rollbackable live handoff
  (`v1495-test-boot-version-missing`) flashed the exact V1493 RC1-window test
  image and rolled back through the generic from-native route successfully. The
  V1493 image includes a PID1 watcher that may perform bounded pci-msm debugfs
  corrected RC1 enumerate writes (`rc_sel=2` + `case=11`) after the provider
  trigger, but V1495 did not collect post-trigger sidecars, so that in-boot
  watcher result is unproven for this run.
  Post-run validation confirmed v724 and selftest `fail=0`. The flash verifier
  reached the expected V1493 boot marker immediately after reboot, but after the
  100s hold all post-hold `cmdv1` evidence commands failed with missing END
  marker or bridge connection reset, so no V1493 log/summary/RC1-window files
  were collected. This is a communication-loss result, not Wi-Fi progress.
  Next gate: V1496 should isolate whether the enabled RC1 watcher/window path
  wedges the serial command loop, preferably with shorter/earlier collection or
  a PID1-persisted sidecar before attempting another long post-hold capture.
  Report:
  `docs/reports/NATIVE_INIT_V1495_WIFI_AUTO_READINESS_RC1_WINDOW_HANDOFF_2026-06-01.md`.
- V1496 rollbackable live handoff
  (`v1496-test-boot-downstream-progress-rollback-pass`) reran the same V1493
  RC1-window test image with a 10s hold. Evidence collection succeeded and
  rollback verified v724/selftest `fail=0`. In addition to flash/rollback, this
  run executed the test image's bounded pci-msm debugfs corrected RC1 enumerate
  (`rc_sel=2` + `case=11`) after the provider trigger. The lower path advanced beyond the
  previous provider-only blocker: `__subsystem_get: esoc0` was followed by
  `msm_pcie_enable: PCIe RC1 PHY is ready`, then LTSSM moved through
  `DETECT_QUIET` and `POLL_ACTIVE` but stalled at `LTSSM_POLL_COMPLIANCE`;
  `PCIe RC1 link initialization failed (LTSSM_STATE:0x3)`. No L0, MHI, WLFW,
  BDF, FW-ready, or `wlan0` appeared. GPIO142/MDM status IRQ stayed at `0`;
  focused samples showed GPIO102 out low, GPIO103 high/unclaimed `pci_e1`,
  GPIO104 low, GPIO135 low, and GPIO142 low through post-500ms. Next gate:
  V1497 should be host-only classification of this RC1 link failure against
  Android-good RC1 evidence before any bounded write experiment. Report:
  `docs/reports/NATIVE_INIT_V1496_WIFI_RC1_WINDOW_SHORT_HOLD_HANDOFF_2026-06-01.md`.
- V1497 host-only RC1 failure classifier
  (`v1497-auto-readiness-rc1-fail-reconciled-existing-endpoint-gap`) reconciles
  V1496 against V1371/V1379/V1432/V1448/V1461/V1475, the V1476 lower
  intervention design gate, and the V1481/V1482 AP2MDM closure. It confirms
  V1496 is not a new Wi-Fi connect-side blocker: corrected RC1 enumerate ran
  successfully and reached PHY/LTSSM, but the endpoint still failed before L0
  and no MHI/WLFW/BDF/FW-ready/`wlan0` appeared. Repeating GPIO135 sysfs hold or
  corrected RC1-only writes is rejected; continue from the V1482/V1496
  endpoint-readiness branch for the next source/build-only pre-L0 endpoint
  parity observer. Report:
  `docs/reports/NATIVE_INIT_V1497_AUTO_READINESS_RC1_FAILURE_CLASSIFIER_2026-06-01.md`.
- V1498 host-only `msm_pcie` TEST:11 static analysis
  (`v1498-msm-pcie-test11-enumerate-path-confirmed-endpoint-response-gap`)
  adds `scripts/revalidation/native_wifi_msm_pcie_test11_static_analysis_v1498.py`
  and parses V1496 evidence, local `sm8150-pcie.dtsi`/`sm8150-mhi.dtsi`/
  `sm8150-sdx50m.dtsi`, and public `pci-msm.c` reference source. The source
  maps TEST:11 to `MSM_PCIE_ENUMERATION`; that case calls
  `msm_pcie_enumerate()`, which calls `msm_pcie_enable(dev, PM_ALL)`. The local
  DTS contract binds RC1 to PERST GPIO102, WAKE GPIO104, `pcie_1` clocks/resets,
  RC bridge `17cb:0108`, MHI IDs `17cb:0305`..`17cb:0308`, and SDX50M
  `0305_01.01.00`. V1496 therefore reached the intended RC1 enable/link
  training path, and the remaining blocker is endpoint response before L0, not
  the debugfs case number or post-L0 firmware/MHI/WLFW. Next gate: V1499
  source/build-only pre-L0 endpoint parity observer for PERST/refclk/clock/GDSC
  and GPIO102/GPIO103/GPIO104/GPIO135/GPIO142 plus LTSSM timing. Report:
  `docs/reports/NATIVE_INIT_V1498_MSM_PCIE_TEST11_STATIC_ANALYSIS_2026-06-01.md`.
- V1499 source/build-only pre-L0 endpoint parity test boot
  (`v1499-wifi-auto-readiness-pre-l0-parity-test-boot-source-build-pass`) adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1499.py` and builds
  `A90 Linux init 0.9.93 (v1499-wifitest)` as a rollbackable credential-free
  image:
  `tmp/wifi/v1499-wifi-auto-readiness-pre-l0-parity-test-boot/boot_linux_v1499_wifi_test.img`
  (`sha256=cd974b855816c3debc9a9505b4d96dee44ba86b48665e35c2ca3376822fa43d8`).
  It keeps the V1493/V1496 PID1 provider-triggered corrected RC1 enumerate
  path (`rc_sel=2` + `case=11`) and enables micro + case-aligned micro endpoint
  sampling at 0/1/2/5/10/20/50/100/150ms after the case write, plus focused
  endpoint sampling for `pcie_1_gdsc`, PCIe1 clocks/refclk, GPIO102/PERST,
  GPIO103/CLKREQ, GPIO104/WAKE, GPIO135/AP2MDM, GPIO142/MDM2AP, pinmux/pinconf,
  interrupts, and RC1 link-state files. It also fixes the shared marker verifier
  so auto-readiness + case-aligned micro sampler combinations do not require
  the older read-only sampler-name string. V1499 performed no device command or
  live action. Next gate: V1500 local artifact sanity over the exact V1499
  manifest before any rollbackable live handoff. Report:
  `docs/reports/NATIVE_INIT_V1499_WIFI_AUTO_READINESS_PRE_L0_PARITY_SOURCE_BUILD_2026-06-01.md`.
- V1500 local-only artifact sanity
  (`v1500-wifi-auto-readiness-pre-l0-parity-artifact-sanity-pass`) adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1500.py` and
  verifies the exact V1499 manifest/image. Checks passed for manifest decision,
  v724 base boot presence, init/helper sha and static linkage, ramdisk entries,
  boot markers, AP2MDM-hold marker absence, pre-L0 parity contract, v724
  header/kernel parity, forbidden credential-like byte absence, and private
  output modes. V1500 performed no device command or live action. Next gate:
  V1501 rollbackable live handoff for only the V1499 image, collecting V1499
  log, summary, RC1 watcher result, pre-L0 parity result, focused dmesg, and
  `wlan0` state, then rolling back to v724 and verifying selftest. Report:
  `docs/reports/NATIVE_INIT_V1500_WIFI_AUTO_READINESS_PRE_L0_PARITY_ARTIFACT_SANITY_2026-06-01.md`.
- V1501 rollbackable live handoff
  (`v1501-test-boot-downstream-progress-rollback-pass`) adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1501.py`, flashes only
  the V1499 test image, collects the V1499 log/summary/RC1 watcher/pre-L0 parity
  result/focused dmesg/`wlan0` state, then rolls back to
  `stage3/boot_linux_v724.img`. Rollback succeeded from native and v724 selftest
  remained `fail=0`. The live evidence still classifies as
  `rc1-ltssm-link-failed-no-l0`: corrected RC1 enumerate writes succeed, RC1 PHY
  becomes ready, LTSSM reaches `POLL_COMPLIANCE`, L0 never appears, and no
  MHI/WLFW/BDF/FW-ready/`wlan0` appears. Report:
  `docs/reports/NATIVE_INIT_V1501_WIFI_PRE_L0_PARITY_HANDOFF_2026-06-01.md`.
- V1502 host-only V1501 evidence classifier
  (`v1502-pre-l0-parity-confirms-rc1-link-fail-with-endpoint-lines-low`) adds
  `scripts/revalidation/native_wifi_pre_l0_parity_classifier_v1502.py` and
  parses the V1501 handoff output. It confirms all nine case-aligned micro
  samples exist at 0/1/2/5/10/20/50/100/150ms after `case=11`; GPIO102/PERST
  stays `out 0`, GPIO103/CLKREQ stays `in 1`, GPIO104/WAKE stays `in 0`,
  GPIO135/AP2MDM stays `out 0`, GPIO142/MDM2AP stays `in 0`, GPIO104/GPIO142
  IRQ counts remain zero, PCIe1 link-state sysfs remains unreadable, and the
  200ms post sample shows `pcie_1_gdsc` plus PCIe1 focused clocks off while
  refgen remains available. Because the focused regulator/clock/GDSC fields are
  currently only sampled at 200ms, likely after link-failure cleanup, the next
  gate should either add dense focused regulator/clock/GDSC reads to each micro
  sample or capture an Android-good RC1 parity reference with the same fields.
  Report:
  `docs/reports/NATIVE_INIT_V1502_WIFI_PRE_L0_PARITY_CLASSIFIER_2026-06-01.md`.
- V1503 source/build-only dense pre-L0 parity test boot
  (`v1503-wifi-dense-pre-l0-parity-test-boot-source-build-pass`) adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1503.py` and builds
  `A90 Linux init 0.9.94 (v1503-wifitest)`:
  `tmp/wifi/v1503-wifi-dense-pre-l0-parity-test-boot/boot_linux_v1503_wifi_test.img`
  (`sha256=dbb0ee6feb6fa2640797d6bd9b1901b4e7c20af8cea1e0af4c7eaee8bc68d522`).
  It keeps the V1499 corrected RC1 enumerate path and adds
  `micro_focused_regulator`, `micro_focused_clk`, `micro_focused_debug_gpio`,
  `micro_focused_pinmux`, and `micro_focused_pinconf` reads to each
  case-aligned micro sample. Report:
  `docs/reports/NATIVE_INIT_V1503_WIFI_DENSE_PRE_L0_PARITY_SOURCE_BUILD_2026-06-01.md`.
- V1504 local-only artifact sanity
  (`v1504-wifi-dense-pre-l0-parity-artifact-sanity-pass`) adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1504.py` and
  verifies the exact V1503 image. Checks passed for manifest decision, static
  init/helper, ramdisk entries, boot markers, dense pre-L0 contract, v724
  header/kernel parity, forbidden credential-like byte absence, private modes,
  and AP2MDM-hold marker absence. Next gate: V1505 rollbackable live handoff
  for only the V1503 image, collect dense pre-L0 parity evidence, roll back to
  v724, and verify selftest `fail=0`. Report:
  `docs/reports/NATIVE_INIT_V1504_WIFI_DENSE_PRE_L0_PARITY_ARTIFACT_SANITY_2026-06-01.md`.
- V1505 rollbackable live handoff
  (`v1505-test-boot-downstream-progress-rollback-pass`) adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1505.py`, boots only the
  V1503 dense pre-L0 image, collects V1503 log/summary/RC1 watcher/dense
  pre-L0 parity result/focused dmesg/`wlan0`, then rolls back to v724 from
  native. Rollback succeeded and v724 selftest remained `fail=0`. Progress
  still classifies as `rc1-ltssm-link-failed-no-l0`: RC1 reaches PHY/LTSSM,
  L0 is absent, and no MHI/WLFW/BDF/FW-ready/`wlan0` appears. Report:
  `docs/reports/NATIVE_INIT_V1505_WIFI_DENSE_PRE_L0_PARITY_HANDOFF_2026-06-01.md`.
- V1506 host-only V1505 evidence classifier
  (`v1506-dense-pre-l0-captures-off-state-but-overruns-micro-window`) adds
  `scripts/revalidation/native_wifi_dense_pre_l0_parity_classifier_v1506.py`.
  It confirms dense focused fields are readable and remain in the blocked
  state: `pcie_1_gdsc` off, PCIe1 clocks off, refgen available, GPIO102/103/104/
  135/142 expected, GPIO142 IRQ zero, and no L0/MHI/WLFW/BDF/FW-ready/`wlan0`.
  It also proves the V1503 exact-match approach is too slow for micro timing:
  the nominal `1ms` sample starts around `1007ms`, with max sample elapsed about
  `12564ms`. Next gate: V1507 source/build-only batched per-file micro sampler
  so each debugfs file is scanned at most once per sample. Report:
  `docs/reports/NATIVE_INIT_V1506_WIFI_DENSE_PRE_L0_PARITY_CLASSIFIER_2026-06-01.md`.
- V1507 source/build-only batched pre-L0 parity test boot
  (`v1507-wifi-batched-pre-l0-parity-test-boot-source-build-pass`) adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1507.py` and extends
  the shared V1393 builder/C hook with
  `--wifi-test-rc1-micro-batched-focused-endpoint-sampler` /
  `A90_WIFI_TEST_BOOT_RC1_MICRO_BATCHED_FOCUSED_ENDPOINT_SAMPLER`. The image
  `tmp/wifi/v1507-wifi-batched-pre-l0-parity-test-boot/boot_linux_v1507_wifi_test.img`
  (`sha256=d3e92460ff1d68a80a99c8b7dbb5b0997ea88c53e120b8e507671e16d5bee8b4`)
  uses `A90 Linux init 0.9.95 (v1507-wifitest)`, keeps corrected RC1 enumerate,
  and scans each debugfs file at most once per micro sample for focused
  regulator/clock/GPIO/pinmux/pinconf needles. V1507 performed no device
  command or live action. Next gate: V1508 local artifact sanity over the exact
  V1507 manifest. Report:
  `docs/reports/NATIVE_INIT_V1507_WIFI_BATCHED_PRE_L0_PARITY_SOURCE_BUILD_2026-06-01.md`.
- V1508 local-only artifact sanity passes with
  `v1508-wifi-batched-pre-l0-parity-artifact-sanity-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1508.py` and
  verifies the exact V1507 test image, native-init marker, helper marker,
  ramdisk entries, batched pre-L0 contract, private modes, v724 header/kernel
  parity, and forbidden credential-like byte absence. V1508 performed no
  device command or live action. Report:
  `docs/reports/NATIVE_INIT_V1508_WIFI_BATCHED_PRE_L0_PARITY_ARTIFACT_SANITY_2026-06-01.md`.
- V1509 rollbackable live handoff passes with
  `v1509-test-boot-downstream-progress-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1509.py`, boots only the
  V1507 batched pre-L0 image, collects the V1507 log/summary/RC1 watcher/
  batched pre-L0 parity result/focused dmesg/`wlan0`, then rolls back to v724
  from native. Rollback succeeded and v724 selftest stayed `fail=0`. Progress
  remains `rc1-ltssm-link-failed-no-l0`: RC1 reaches PHY/LTSSM and link
  failure, but L0/MHI/WLFW/BDF/FW-ready/`wlan0` remain absent. Report:
  `docs/reports/NATIVE_INIT_V1509_WIFI_BATCHED_PRE_L0_PARITY_HANDOFF_2026-06-01.md`.
- V1510 host-only V1509 evidence classifier passes with
  `v1510-batched-pre-l0-improves-sampling-but-source-timestamps-needed`. It
  adds `scripts/revalidation/native_wifi_batched_pre_l0_parity_classifier_v1510.py`.
  The batched reads preserve the blocked pre-L0 state: `pcie_1_gdsc` off,
  PCIe1 clocks off, refgen available, GPIO102/103/104/135/142 expected,
  GPIO142 IRQ zero, and no L0/MHI/WLFW/BDF/FW-ready/`wlan0`. Timing improved
  over V1505, but source begin/end timestamps are missing; the first sample
  starts at case+0ms while the second starts at about `148ms`, after the
  ~`114.8ms` link-fail marker. Next gate: V1511 source/build-only
  source-timestamped batched sampler or a narrower critical-source sampler.
  Report:
  `docs/reports/NATIVE_INIT_V1510_WIFI_BATCHED_PRE_L0_PARITY_CLASSIFIER_2026-06-01.md`.
- V1511 source/build-only source-timestamped pre-L0 test boot
  (`v1511-wifi-source-timestamped-pre-l0-test-boot-source-build-pass`) adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1511.py` and extends
  the shared V1393 builder/C hook with
  `--wifi-test-rc1-micro-source-timestamped-sampler` /
  `A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER`. The image
  `tmp/wifi/v1511-wifi-source-timestamped-pre-l0-test-boot/boot_linux_v1511_wifi_test.img`
  (`sha256=9a3ff92c488f41f77ce4fdb1fee403229ea12e408fb5b86773c945623d074e57`)
  uses `A90 Linux init 0.9.96 (v1511-wifitest)`, keeps corrected RC1 enumerate
  and V1507 batched reads, and emits `source_timing=begin/end` plus
  `source_duration_ms` around each micro source read. V1511 performed no live
  device command. Report:
  `docs/reports/NATIVE_INIT_V1511_WIFI_SOURCE_TIMESTAMPED_PRE_L0_SOURCE_BUILD_2026-06-01.md`.
- V1512 local-only artifact sanity passes with
  `v1512-wifi-source-timestamped-pre-l0-artifact-sanity-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1512.py` and
  verifies the exact V1511 image, static init/helper, ramdisk entries, source
  timestamp contract, v724 header/kernel parity, private modes, and forbidden
  credential-like byte absence. Report:
  `docs/reports/NATIVE_INIT_V1512_WIFI_SOURCE_TIMESTAMPED_PRE_L0_ARTIFACT_SANITY_2026-06-01.md`.
- V1513 rollbackable live handoff passes with
  `v1513-test-boot-downstream-progress-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1513.py`, boots only the
  V1511 source-timestamped image, collects V1511 log/summary/RC1 watcher/source
  timing result/focused dmesg/`wlan0`, then rolls back to v724 from native.
  Rollback succeeded and v724 selftest stayed `fail=0`. Progress remains
  `rc1-ltssm-link-failed-no-l0`. Report:
  `docs/reports/NATIVE_INIT_V1513_WIFI_SOURCE_TIMESTAMPED_PRE_L0_HANDOFF_2026-06-01.md`.
- V1514 host-only V1513 evidence classifier passes with
  `v1514-source-timing-identifies-clk-summary-overrun`. It adds
  `scripts/revalidation/native_wifi_source_timing_classifier_v1514.py`.
  The first sample starts at case+0ms and fast sources finish before link fail,
  but full `clk_summary` spans roughly `35ms` to `149ms`, crossing the
  ~`114.9ms` link-fail marker. Next gate: V1515 source/build-only
  critical-source pre-L0 sampler that avoids full `clk_summary` in the first
  link-fail window. Report:
  `docs/reports/NATIVE_INIT_V1514_WIFI_SOURCE_TIMING_CLASSIFIER_2026-06-01.md`.
- V1515 source/build-only critical-source pre-L0 test boot
  (`v1515-wifi-critical-source-pre-l0-test-boot-source-build-pass`) adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1515.py` and extends
  the shared V1393 builder/C hook with
  `--wifi-test-rc1-micro-critical-fast-endpoint-sampler` /
  `A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER`. The image
  `tmp/wifi/v1515-wifi-critical-source-pre-l0-test-boot/boot_linux_v1515_wifi_test.img`
  (`sha256=b2578c7bec6565ae051d7101e8e6074890f8151b99767ed4ac27f2aa69df9b78`)
  uses `A90 Linux init 0.9.97 (v1515-wifitest)`, keeps corrected RC1 enumerate
  and source timing, skips full `clk_summary`, and emits
  `micro_critical_regulator` / `micro_critical_pinmux`. Report:
  `docs/reports/NATIVE_INIT_V1515_WIFI_CRITICAL_SOURCE_PRE_L0_SOURCE_BUILD_2026-06-01.md`.
- V1516 local-only artifact sanity passes with
  `v1516-wifi-critical-source-pre-l0-artifact-sanity-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1516.py` and
  verifies the exact V1515 image, critical-source contract, private modes, and
  forbidden credential-like byte absence. Report:
  `docs/reports/NATIVE_INIT_V1516_WIFI_CRITICAL_SOURCE_PRE_L0_ARTIFACT_SANITY_2026-06-01.md`.
- V1517 rollbackable live handoff passes with
  `v1517-test-boot-downstream-progress-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1517.py`, boots only the
  V1515 critical-source image, collects V1515 log/summary/RC1 watcher/critical
  timing result/focused dmesg/`wlan0`, then rolls back to v724 from native.
  Rollback succeeded and v724 selftest stayed `fail=0`. Progress remains
  `rc1-ltssm-link-failed-no-l0`. Report:
  `docs/reports/NATIVE_INIT_V1517_WIFI_CRITICAL_SOURCE_PRE_L0_HANDOFF_2026-06-01.md`.
- V1518 host-only V1517 evidence classifier passes with
  `v1518-critical-source-first-window-pre-fail-confirmed`. It adds
  `scripts/revalidation/native_wifi_critical_source_timing_classifier_v1518.py`.
  Selected first-window sources complete by about `30ms` after `case=11`,
  before the ~`114.9ms` link-fail marker; GPIO135/GPIO142 remain low,
  `pcie_1_gdsc` remains `0mV`, and no L0/MHI/WLFW/BDF/FW-ready/`wlan0`
  appears. Report:
  `docs/reports/NATIVE_INIT_V1518_WIFI_CRITICAL_SOURCE_TIMING_CLASSIFIER_2026-06-01.md`.
- V1519 host-only Android-good/native-fail comparator passes with
  `v1519-android-good-native-fail-compared-matched-rc1-source-capture-needed`.
  It adds
  `scripts/revalidation/native_wifi_android_good_native_fail_critical_comparison_v1519.py`.
  Existing Android-good evidence proves GPIO142 IRQ, PCIe L0, WLFW/BDF, and
  `wlan0`, but GPIO135/GPIO142 low readback is not discriminating because the
  Android-good static snapshot also shows those lines low. Next gate: V1520
  Android-good matched critical-source RC1 timeline for pcie1 GDSC/clock,
  refclk, PERST/reset, and normal RC1 path before any native mutation. Report:
  `docs/reports/NATIVE_INIT_V1519_ANDROID_GOOD_NATIVE_FAIL_CRITICAL_SOURCE_COMPARISON_2026-06-01.md`.
- V1520 rollbackable Android handoff passes with
  `v1520-handoff-adb-sampler-missed-pre-l0-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_android_rc1_early_critical_source_sample_v1520.py`
  and `scripts/revalidation/android_rc1_early_critical_source_handoff_v1520.py`.
  Android reached WLFW/BDF/`wlan0`, but the earliest plain ADB sampler sample
  began at uptime `13.85s`, after WLFW `8.433089s` and BDF `9.561577s`, so
  early ADB cannot capture the RC1 pre-L0 critical-source window. Rollback to
  native v724 completed and selftest remained `fail=0`. Next gate: V1521
  earlier Android boot hook, likely a temporary Magisk `post-fs-data` read-only
  sampler, before any native mutation. Report:
  `docs/reports/NATIVE_INIT_V1520_ANDROID_RC1_EARLY_CRITICAL_SOURCE_HANDOFF_2026-06-01.md`.
- V1521 rollbackable Android Magisk post-fs-data handoff passes with
  `v1521-magisk-postfs-pre-lower-window-rollback-pass`. It adds
  `scripts/revalidation/android_rc1_magisk_postfs_sampler_handoff_v1521.py`,
  installs a temporary read-only Magisk module from Android `su`, collects early
  Android-good post-fs-data samples, captures host dmesg before cleanup, removes
  the module/evidence, reboots recovery, and restores `stage3/boot_linux_v724.img`.
  The sampler starts at uptime `5.72s`, brackets the first lower Wi-Fi marker
  with samples before/after WLFW `8.585121s`, and records BDF at `9.673077s` and
  `wlan0` at `14.843021s`; rollback verifies native v724 and selftest remains
  `fail=0`. The important interpretation is negative: Android-good pre/post
  lower samples still report GPIO135/GPIO142 low, GPIO142 IRQ count `0`, and
  `pcie_1_gdsc` `0mV`, so those debugfs/interrupt/regulator snapshots alone are
  not discriminating. V1522 should compare V1521 Android-good samples directly
  against V1518/V1517 native pre-fail samples, then move to `msm_pcie` TEST:11
  vs normal-path static/callgraph analysis if the source comparison does not
  explain why native TEST:11 reaches `POLL_COMPLIANCE` but no L0. Report:
  `docs/reports/NATIVE_INIT_V1521_ANDROID_RC1_MAGISK_POSTFS_HANDOFF_2026-06-01.md`.
- V1522 host-only Android/native RC1 source parity classifier passes with
  `v1522-sampled-sources-nondiscriminating-msm-pcie-static-needed`. It adds
  `scripts/revalidation/native_wifi_android_native_rc1_source_parity_classifier_v1522.py`
  and compares V1521 Android-good pre/post lower samples against V1518/V1517
  native pre-fail samples. V1521 proves Android-good WLFW/BDF/`wlan0`, while
  V1518/V1517 prove native `rc1-ltssm-link-failed-no-l0`; nevertheless the
  sampled GPIO/debugfs/interrupt/regulator fields overlap: GPIO135/GPIO142 low,
  GPIO142 IRQ count `0`, and `pcie_1_gdsc` `0mV` are visible in Android-good and
  native-fail windows. This closes those sampled sources as root-cause evidence.
  V1523 should classify `msm_pcie` corrected TEST:11 vs Android normal-path
  static/callgraph semantics and list operations TEST:11 lacks before any new
  native mutation. Report:
  `docs/reports/NATIVE_INIT_V1522_ANDROID_NATIVE_RC1_SOURCE_PARITY_CLASSIFIER_2026-06-01.md`.
- V1523 host-only `msm_pcie` TEST:11 vs normal-path static/callgraph classifier
  passes with `v1523-test11-shares-enable-normal-trigger-readiness-gap`. It
  adds
  `scripts/revalidation/native_wifi_msm_pcie_test11_vs_normal_path_classifier_v1523.py`
  and compares the corrected TEST:11 path with the public `pci-msm.c` normal
  entry points and local SM8150 PCIe DTS. TEST:11 is not missing the common
  AP-side enable sequence: debugfs TEST:11, sysfs/client enumeration,
  endpoint-wake work, and non-deferred probe all converge on
  `msm_pcie_enumerate() -> msm_pcie_enable(PM_ALL)`. Local pcie1 has
  `qcom,boot-option=<0x1>`, so probe-time enumeration is intentionally skipped.
  The blocker therefore moves to pre-enumerate endpoint readiness/trigger
  semantics that Android satisfies and native TEST:11 does not. V1524 should
  classify Android-good and native-fail evidence for endpoint wake IRQ/GPIO104,
  sysfs/client caller, or vendor client request before another native mutation.
  Report:
  `docs/reports/NATIVE_INIT_V1523_MSM_PCIE_TEST11_VS_NORMAL_PATH_CLASSIFIER_2026-06-02.md`.
- V1524 host-only endpoint-trigger attribution classifier passes with
  `v1524-trigger-attribution-pivots-to-esoc-mhi-pm-resume`. It adds
  `scripts/revalidation/native_wifi_endpoint_trigger_attribution_classifier_v1524.py`
  and compares V852 Android-good RC1 evidence, V1521 Android-good sampled
  IRQ/dmesg evidence, V1517 native TEST:11 failure evidence, local
  `mhi_arch_qcom.c`, and public `pci-msm.c`. Android-good initial RC1 is not
  observed as debugfs TEST:11, while native V1517 is explicitly TEST:11 and
  fails before L0. Existing Android-good GPIO104 wake IRQ evidence is
  contradictory enough that endpoint wake cannot be treated as the proven
  initial trigger. The new source-supported candidate is eSoC/MHI PM-resume:
  `mhi_arch_esoc_ops_power_on()` calls
  `msm_pcie_pm_control(MSM_PCIE_RESUME, ...)`, which dispatches to
  `msm_pcie_pm_resume()` and reaches `msm_pcie_enable(PM_PIPE_CLK | PM_CLK |
  PM_VREG)` before `mhi_pci_probe()`. V1525 should compare the MHI/eSoC
  PM-resume path against TEST:11 `PM_ALL` semantics before any new live
  mutation. Report:
  `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md`.
- V1525 host-only MHI PM-resume position classifier passes with
  `v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger`. It adds
  `scripts/revalidation/native_wifi_mhi_pm_resume_position_classifier_v1525.py`
  and validates the V1524 eSoC/MHI PM-resume candidate against local
  `mhi_arch_qcom.c`, local `mhi_qcom.c`, public `pci-msm.c`, V852 Android-good
  dmesg, and V1517 native TEST:11 failure evidence. The MHI/eSoC
  `MSM_PCIE_RESUME` path is real, but it requires an existing `pci_dev`:
  `mhi_arch_esoc_ops_power_on()` reads `mhi_dev->pci_dev`, pci-msm casts the
  caller to `struct pci_dev`, and pci-msm validates it against `pcidev_table`.
  The eSoC hook is registered from MHI PCI init/probe, so it cannot be the
  operation that creates the first PCI device or first L0. It explains later
  Android RC1 resume cycles, not the missing native first-L0 transition. V1526
  should capture or classify the Android-only first-L0 trigger below Wi-Fi
  connect: endpoint wake IRQ timing, pci-msm sysfs/client enumerate, or another
  kernel caller. Report:
  `docs/reports/NATIVE_INIT_V1525_MHI_PM_RESUME_POSITION_CLASSIFIER_2026-06-02.md`.
- V1526 host-only Android initial RC1 trigger capture design passes with
  `v1526-android-initial-rc1-trigger-capture-design-ready`. It adds
  `scripts/revalidation/android_initial_rc1_trigger_capture_design_v1526.py`
  and defines the V1527 capture contract. Fixed points: Android V852 has
  `esoc0` at `8.541440s`, first RC1 assert at `8.796369s`, and first L0 at
  `8.820231s` without a debugfs TEST marker; native V1517 uses explicit
  TEST:11 and fails before L0; V1525 closes MHI PM-resume as first-L0 trigger.
  V1521's temporary Magisk post-fs-data handoff starts early enough
  (`5.72s`) but its IRQ snapshots stayed zero, so V1527 should extend that
  rollbackable Android-good handoff with raw `/dev/kmsg` or `dmesg -w` capture
  plus high-cadence GPIO104/GPIO142 `/proc/interrupts` and debug GPIO samples.
  Success labels: raw kmsg caller found, endpoint wake before L0, mdm status
  before/during L0, or opaque kernel caller requiring tracefs. Report:
  `docs/reports/NATIVE_INIT_V1526_ANDROID_INITIAL_RC1_TRIGGER_CAPTURE_DESIGN_2026-06-02.md`.
- V1527 rollbackable Android initial RC1 trigger handoff source/plan passes with
  `v1527-handoff-plan-ready`. It adds
  `scripts/revalidation/android_initial_rc1_trigger_handoff_v1527.py` and
  generates
  `docs/reports/NATIVE_INIT_V1527_ANDROID_INITIAL_RC1_TRIGGER_HANDOFF_2026-06-02.md`.
  The runner reuses the proven V1521 Magisk/rollback handoff engine, but
  installs a V1527 temporary post-fs-data sampler that captures raw
  `/dev/kmsg` or `dmesg -w` plus high-cadence GPIO104/GPIO142 interrupt,
  debug GPIO, and pcie1 state samples. Plan mode verified the full
  Android-boot handoff/rollback step list without mutating the device. Live
  execution remains a separate explicit gate and must keep the hard exclusions:
  no Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping,
  PMIC/GPIO/GDSC writes, blind eSoC notify, PCI rescan, or platform bind/unbind.
- V1528 host-only V1527 evidence escalation classifier passes with
  `v1528-route-to-android-tracefs-event-capture`. V1527 live evidence proves
  Android-good WLFW/BDF/`wlan0` and native rollback, but raw kmsg contains zero
  RC1/LTSSM lines, GPIO104/GPIO142 IRQ totals remain zero, and GPIO135/GPIO142
  debugfs levels remain low during the successful lower Wi-Fi window. Treat
  those sources as nondiscriminating for this blocker. Next gate: V1529 should
  reuse the rollbackable Android handoff and capture bounded tracefs events
  around the `pm-service`/`subsys_esoc0` window. Report:
  `docs/reports/NATIVE_INIT_V1528_V1527_EVIDENCE_TRACEFS_ESCALATION_2026-06-02.md`.
- V1529 rollbackable Android tracefs RC1 event handoff passes with partial
  evidence and native rollback: `v1529-tracefs-event-partial-rollback-pass`.
  It adds `scripts/revalidation/android_tracefs_rc1_event_handoff_v1529.py`
  and captures bounded tracefs events under the V1521/V1527 Android
  boot/Magisk/native-rollback harness. Android-good lower markers recur:
  `wlfw_start=43.208627s`, `subsys_esoc0=43.367958s`, BDF at `44.452551s`,
  FW-ready at `49.369675s`, and `wlan0=49.864980s`. Tracefs adds modem PIL
  notifications at `40.820s..41.328s`, `icnss_driver_event_work=40.836714s`,
  and `pm-service` exec at `41.922287s`; no eSoC/SDX50M PIL notification
  appears. IRQ trace events were removed from the final runner after the first
  broad run proved too noisy. The run remains partial because the module `done`
  marker was not observed before pull, but rollback passed and the evidence is
  usable. Next gate: V1530 should classify this trace against native no-L0 and
  design a narrower targeted observer rather than rerunning broad workqueue
  capture.
  Report:
  `docs/reports/NATIVE_INIT_V1529_ANDROID_TRACEFS_RC1_EVENT_HANDOFF_2026-06-02.md`.
- V1530 host-only Android tracefs vs native no-L0 classifier passes with
  `v1530-android-tracefs-confirms-opaque-initial-rc1-trigger`. It adds
  `scripts/revalidation/native_wifi_android_tracefs_native_no_l0_classifier_v1530.py`
  and reconciles V1529 Android tracefs evidence against V1496/V1517 native
  no-L0 references plus V1523/V1525 source classifiers. V1529 proves
  Android-good lower progress and captures modem PIL notifications,
  `icnss_driver_event_work`, `pm-service` exec, WLFW/BDF/FW-ready, and `wlan0`,
  while still exposing no eSoC/SDX50M `pil_notif` and no RC1/LTSSM text. Native
  V1496/V1517 stay fixed at `rc1-ltssm-link-failed-no-l0`, and V1523/V1525
  already rule out missing TEST:11 AP-side enable semantics and MHI PM-resume
  as first-L0 triggers. Next gate: V1531 should be a targeted Android/source
  classifier for `icnss_driver_event_work`, `pm-service` Binder
  `subsystem_get`, and pci-msm initial enumerate callsites before any new
  native mutation.
  Report:
  `docs/reports/NATIVE_INIT_V1530_ANDROID_TRACEFS_NATIVE_NO_L0_CLASSIFIER_2026-06-02.md`.
- V1531 host-only targeted trace/source classifier passes with
  `v1531-targeted-trace-source-classifies-visible-signals-not-trigger`. It adds
  `scripts/revalidation/native_wifi_targeted_trace_source_classifier_v1531.py`
  and maps V1529/V1530 evidence against local ICNSS source, pm-service binary
  strings, and the available pci-msm source copy. ICNSS source confirms
  `icnss_driver_event_work` is a shared dispatcher for SERVER_ARRIVE, FW_READY,
  REGISTER_DRIVER, and other events, so the existing workqueue execute trace
  cannot identify the event type by itself. pm-service is confirmed as the
  proprietary `vendor.qcom.PeripheralManager` Binder/QMI voter actor, and
  pci-msm TEST:11, wake IRQ work, sysfs enumerate, and probe paths all converge
  on `msm_pcie_enumerate`; native still reaches enable/LTSSM and fails before
  L0. Next gate: V1532 should design/capture a bounded Android tracefs reference
  with `workqueue_queue_work` + execute pairing and pm-service Binder
  `subsystem_get` timing, without broad IRQ tracing or any Wi-Fi connect path.
  Report:
  `docs/reports/NATIVE_INIT_V1531_TARGETED_TRACE_SOURCE_CLASSIFIER_2026-06-02.md`.
- V1532 rollbackable Android targeted tracefs queue-pair handoff passes with
  `v1532-targeted-tracefs-partial-rollback-pass`. It adds
  `scripts/revalidation/android_targeted_tracefs_queue_pair_handoff_v1532.py`
  and extends the V1521/V1529 Android handoff module to enable only sched exec,
  workqueue queue/activate/execute, PIL, and printk console tracefs events. The
  live run flashed the known Android boot image, installed the temporary Magisk
  sampler, captured Android-good lower Wi-Fi progress, pulled partial evidence,
  removed the temporary module, and restored native v724. The restore path now
  uses `native_init_flash.py --verify-protocol selftest` to avoid recording
  sensitive `version`/`status` text in new handoff evidence. Report:
  `docs/reports/NATIVE_INIT_V1532_ANDROID_TARGETED_TRACEFS_QUEUE_PAIR_HANDOFF_2026-06-02.md`.
- V1533 host-only V1532 queue-pair classifier passes with
  `v1533-icnss-queue-pair-is-hdd-register-path-not-first-l0-trigger`. It adds
  `scripts/revalidation/native_wifi_v1532_queue_pair_classifier_v1533.py` and
  proves the queued `icnss_driver_event_work` item is from
  `/vendor/bin/hw/macloader` during WLAN driver load, executes about 0.012 ms
  later, and precedes pm-service `subsys_esoc0`, QMI server, BDF, FW-ready, and
  `wlan0`. This closes the visible ICNSS workqueue line as a first-L0 lead.
  Next gate: V1534 should target the pm-service Binder/QMI voter path that opens
  `subsys_esoc0` and the immediate pci-msm first-L0 path, not firmware/MHI or
  ICNSS workqueue. Report:
  `docs/reports/NATIVE_INIT_V1533_V1532_QUEUE_PAIR_CLASSIFIER_2026-06-02.md`.
- V1534 host-only PM route first-L0 focus classifier passes with
  `v1534-current-pm-route-supersedes-old-gap-first-l0-focus`. It adds
  `scripts/revalidation/native_wifi_pm_route_first_l0_focus_classifier_v1534.py`
  and reconciles the older PM dependency/actionability branch with the current
  lower route. V1178 remains useful history for late-`per_proxy` dependency
  ordering, but V1343/V1345 already prove current SDX50M registration,
  `per_mgr_esoc0`, and `mdm_subsys_powerup`; V1496/V1517 move the active
  failure down to RC1 LTSSM progress with no L0; V1523 proves TEST:11 shares the
  core pci-msm enumerate/enable path with normal callers; V1525 and V1533 close
  MHI PM-resume and ICNSS workqueue as first-L0 leads. Next gate: V1535 should
  focus on endpoint readiness/trigger semantics around `msm_pcie_enumerate`
  rather than PM registration or firmware/MHI. Report:
  `docs/reports/NATIVE_INIT_V1534_PM_ROUTE_FIRST_L0_FOCUS_CLASSIFIER_2026-06-02.md`.
- V1535 host-only first-L0 trigger candidate classifier passes with
  `v1535-first-l0-candidates-narrowed-to-client-enumerate-or-endpoint-readiness`.
  It adds
  `scripts/revalidation/native_wifi_first_l0_trigger_candidate_classifier_v1535.py`
  and reconciles V1496/V1517 native no-L0 evidence, V1523 pci-msm source, V1525
  MHI PM-resume closure, V1533 ICNSS workqueue closure, and Android V852/V1527/
  V1529/V1532 references. Closed immediate leads: old PM gap, MHI PM-resume,
  visible ICNSS workqueue, probe-time enumeration, and blind TEST:11 timing
  retry. Remaining AP-side empirical check is targeted sysfs/client enumerate;
  if it also fails before L0, focus moves to endpoint electrical/readiness
  around PERST/refclk/reset/SDX50M response. Next gate: V1536 source/build-only
  rollbackable test-boot variant using targeted pci-msm sysfs/client enumerate,
  no global PCI rescan or platform bind/unbind, and no Wi-Fi HAL/scan/connect/
  credentials/DHCP/routes/external ping. Report:
  `docs/reports/NATIVE_INIT_V1535_FIRST_L0_TRIGGER_CANDIDATE_CLASSIFIER_2026-06-02.md`.
- V1536/V1537 sysfs/client enumerate test-boot preparation passes. V1536 adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1536.py` plus the
  PID1 compile flag `A90_WIFI_TEST_BOOT_RC1_SYSFS_CLIENT_ENUMERATE`, changing
  the first-L0 trigger write from debugfs TEST:11 to
  `/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate`. It builds
  `tmp/wifi/v1536-wifi-sysfs-client-enumerate-test-boot/boot_linux_v1536_wifi_test.img`
  with SHA256
  `9a8f10f9ae3cf6247faa49e78baa2fa9de5ce2539380893c8b7a777923b4e527`.
  V1537 adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1537.py` and
  passes with `v1537-wifi-sysfs-client-enumerate-artifact-sanity-pass`. The
  base test-boot handoff now uses `native_init_flash.py --verify-protocol
  selftest` to avoid recording rollback version/status text in new flash
  verifier output. Next gate: V1538 rollbackable live handoff for only the V1536
  test image, collect log/summary/RC1 watcher/sysfs-client result/focused dmesg/
  `wlan0`, then roll back to v724 and verify selftest `fail=0`. Reports:
  `docs/reports/NATIVE_INIT_V1536_WIFI_SYSFS_CLIENT_ENUMERATE_SOURCE_BUILD_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1537_WIFI_SYSFS_CLIENT_ENUMERATE_ARTIFACT_SANITY_2026-06-02.md`.

## Latest native Wi-Fi state: V1538/V1539 (2026-06-02)

V1538 ran the rollbackable V1536 sysfs/client enumerate test boot and passed
with `v1538-test-boot-downstream-progress-rollback-pass`. The PID1 writer used
`trigger_mode=sysfs_client_enumerate`, wrote
`/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate` with `sysfs_rc=0`,
collected focused RC1/window/dmesg evidence, and rolled back to native v724
with selftest verification. The evidence shows RC1 assert/release, PHY ready,
LTSSM poll active/compliance, and `PCIe RC1 link initialization failed
(LTSSM_STATE:0x3)`, with no L0, MHI, WLFW, BDF, FW-ready, `wlan0`, or connect
readiness.

V1539 added
`scripts/revalidation/native_wifi_sysfs_enumerate_result_classifier_v1539.py`
and classified V1538 host-only. Result:
`v1539-sysfs-client-enumerate-closes-ap-side-trigger-no-l0` PASS. This closes
the remaining AP-side caller semantics branch from V1535: targeted
sysfs/client enumerate reaches the same fixed native failure as prior RC1
enumerate paths. Next gate is V1540 host-only endpoint-readiness/electrical
classification around PERST/refclk/GDSC/reset/GPIO135/GPIO142/SDX50M response.
Do not return to firmware/MHI/WLFW/Wi-Fi HAL/scan/connect/credentials/DHCP/
routes/external ping until native RC1 L0 and PCI enumeration exist.

## Latest native Wi-Fi state: V1540 (2026-06-02)

V1540 added
`scripts/revalidation/native_wifi_endpoint_readiness_classifier_v1540.py` and
classified V1538/V1539 against the local DTS and `pci-msm.c` source. Result:
`v1540-endpoint-readiness-gap-after-sysfs-enumerate` PASS. The source contract
shows RC1 uses GPIO102 PERST, GPIO104 WAKE, `pcie_1_gdsc`, `pm8150l_l3`,
`pm8150_l5`, clkref/refgen/pipe clocks, and SDX50M/MHI endpoint `17cb:0305`
via `esoc0`; the eSoC side uses AP2MDM GPIO135, MDM2AP GPIO142, and PM8150L
GPIO9 PON. `msm_pcie_enable()` order is PERST assert, vregs/clocks/PHY/pipe,
PHY-ready wait, PERST release, LTSSM enable, and link polling. Native V1538
reaches that sequence but stops at `POLL_COMPLIANCE`/no L0 with GPIO142 IRQ
`0`, no MHI/WLFW/BDF/FW-ready/`wlan0`; Android-good V852 reaches L0/current
GEN/WLFW/BDF/`wlan0`. Next gate is V1541 source/build-only endpoint electrical
observer design for PERST/refclk/GDSC/CLKREQ/WAKE/AP2MDM/MDM2AP in the exact
RC1 link-training window. Do not repeat enumerate retries or move to
firmware/MHI/WLFW/connect-side work until native L0 and PCI enumeration exist.

## Latest native Wi-Fi state: V1541-V1544 (2026-06-02)

V1541-V1543 built and ran a rollbackable endpoint-electrical observer test
boot. V1541 adds
`scripts/revalidation/build_native_init_wifi_test_boot_v1541.py`, producing
`tmp/wifi/v1541-endpoint-electrical-observer-test-boot/boot_linux_v1541_wifi_test.img`
with init `A90 Linux init 0.9.99 (v1541-wifitest)` and helper marker
`a90_android_execns_probe v287`. V1542 adds
`scripts/revalidation/native_wifi_endpoint_electrical_artifact_sanity_v1542.py`
and passes artifact sanity. V1543 adds
`scripts/revalidation/native_wifi_endpoint_electrical_handoff_v1543.py` and
passes the live handoff/rollback with progress decision
`rc1-ltssm-link-failed-no-l0`.

V1544 adds
`scripts/revalidation/native_wifi_endpoint_electrical_result_classifier_v1544.py`
and classifies the V1543 evidence with
`v1544-endpoint-electrical-confirms-no-l0-gpio-gdsc-zero-clk-postfail` PASS.
The sysfs/client enumerate writer succeeds and reaches RC1 assert, PHY-ready,
PERST release, LTSSM poll active/compliance, then
`PCIe RC1 link initialization failed (LTSSM_STATE:0x3)`. GPIO104/WAKE and
GPIO142/MDM2AP stay low with zero IRQ count, GPIO135 remains low in captured
debug GPIO samples, `pcie_1_gdsc` is observed at 0mV, and no MHI/WLFW/BDF/
FW-ready/`wlan0` marker appears. Focused `clk_summary` lines show disabled
pcie1 clocks after capture, but `clk_summary` is too slow for a definitive
sub-120ms pre-fail clock-state proof. Next gate: V1545 should be a host/source
classifier or test-boot design for a low-overhead pre-fail endpoint-state
observer that avoids full `clk_summary` reads in the critical RC1 window. Do
not repeat enumerate-only experiments or move to firmware/MHI/WLFW/connect-side
work until native RC1 L0 and PCI enumeration exist.

## Latest native Wi-Fi state: V1545-V1547 (2026-06-02)

V1545 adds
`scripts/revalidation/native_wifi_low_overhead_observer_design_v1545.py` and
passes with `v1545-low-overhead-observer-design-ready`. It classifies V1544
against the PID1 source and existing build wrappers. The key decision is that
the next observer should reuse the sysfs/client enumerate route while removing
`micro_focused_endpoint_sampler` from the critical case-aligned micro loop,
because `micro_focused_clk` reads full `clk_summary` and is too slow for the
sub-120ms no-L0 window. The existing critical-fast sampler already emits
`micro_critical_clk_summary_skipped=1` and reads only interrupts, debug GPIO,
link-state files, regulator summary, and pinmux in the micro loop.

V1546 adds `scripts/revalidation/build_native_init_wifi_test_boot_v1546.py`
and builds
`tmp/wifi/v1546-low-overhead-endpoint-observer-test-boot/boot_linux_v1546_wifi_test.img`
with init `A90 Linux init 0.9.100 (v1546-wifitest)`. V1547 adds
`scripts/revalidation/native_wifi_low_overhead_artifact_sanity_v1547.py` and
passes with `v1547-low-overhead-artifact-sanity-pass`. The V1546 image keeps
sysfs/client enumerate, case-aligned micro sampling, source timestamps, and
`micro_critical_fast_endpoint_sampler`; it removes micro-focused and batched
clock readers from the critical loop. Next gate: V1548 rollbackable live
handoff for only the V1546 image, then classify whether fast sources finish
before the RC1 link-fail marker and whether GPIO/GDSC/link-state evidence
changes relative to V1543. Keep all connect-side and direct PMIC/GPIO/GDSC
write exclusions until native RC1 L0 and PCI enumeration exist.

## Latest native Wi-Fi state: V1548-V1549 (2026-06-02)

V1548 adds `scripts/revalidation/native_wifi_low_overhead_handoff_v1548.py`
and passes the rollbackable live handoff for the V1546 test image with
`v1548-test-boot-downstream-progress-rollback-pass`. The progress decision is
still `rc1-ltssm-link-failed-no-l0`: sysfs/client enumerate succeeds, RC1
reaches PHY-ready and LTSSM poll active/compliance, then fails before L0; no
MHI/WLFW/BDF/FW-ready/`wlan0` marker appears. Rollback to v724 verifies with
selftest.

V1549 adds
`scripts/revalidation/native_wifi_low_overhead_result_classifier_v1549.py` and
passes with `v1549-low-overhead-confirms-pre-fail-gpio-gdsc-no-l0`. This closes
the V1543 slow-`clk_summary` ambiguity: the critical loop now emits
`micro_critical_clk_summary_skipped=1`, has no `micro_focused_clk`, and still
captures pre-fail interrupt/GPIO/link-state/regulator/pinmux sources. Before
the RC1 link-fail timestamp, GPIO104/WAKE and GPIO142/MDM2AP remain low with
zero IRQ, GPIO135/AP2MDM remains low in debug GPIO, and `pcie_1_gdsc` is still
reported as 0mV. Next gate: V1550 should be host/source analysis of pcie1
power-domain and debugfs regulator semantics, specifically why `msm_pcie`
reaches PHY/LTSSM while `regulator_summary` still reports `pcie_1_gdsc` as
0mV. Do not run another enumerate retry or move to firmware/MHI/WLFW/connect
work until that semantics gap is classified.

## Latest native Wi-Fi state: V1550 (2026-06-02)

V1550 adds
`scripts/revalidation/native_wifi_pcie1_power_domain_semantics_classifier_v1550.py`
and passes with
`v1550-pcie1-gdsc-summary-is-not-power-proof-tracefs-needed`. It is host-only:
no device command, tracefs write, reboot, flash, partition write, Wi-Fi HAL,
scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC
write, global PCI rescan, or platform bind/unbind occurred. V1550 reconciles
V1549 against `pci-msm.c`, `regulator/core.c`, `gdsc-regulator.c`, and SM8150
DTS. Source shows `msm_pcie_enumerate()` calls `msm_pcie_enable(PM_ALL)` and
the path requests `regulator_enable(dev->gdsc)` for `gdsc-vdd =
<&pcie_1_gdsc>` before PHY/LTSSM. `regulator_summary` prints use/open/bypass
plus `_regulator_get_voltage()/1000`; the qcom GDSC regulator exposes
enable/disable/is_enabled but no voltage getter/list operation, so
`pcie_1_gdsc ... 0mV` is not a physical-voltage proof. The leading `0`
use-count remains a real timing question because source should enable GDSC and
link-fail cleanup should disable it. Next gate: V1551 should capture bounded
targeted tracefs regulator/clk/gpio events around the existing
sysfs-client-enumerate window, using V1315-proven event availability, and
still avoid direct PMIC/GPIO/GDSC writes, global PCI rescan, platform
bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external
ping until native RC1 L0 and PCI enumeration exist.

## Latest native Wi-Fi state: V1551 (2026-06-02)

V1551 adds
`scripts/revalidation/native_wifi_pcie1_tracefs_enumerate_live_v1551.py` and
passes with `v1551-pcie1-gdsc-enable-captured-no-l0`. It is a bounded live
tracefs observer around the already-proven pcie1 sysfs-client enumerate path:
it enables only selected regulator/clk/gpio static tracefs events, writes once
to the pcie1 enumerate endpoint, disables the events, captures filtered trace
lines and dmesg, then verifies post selftest. It does not start Wi-Fi HAL,
scan/connect, use credentials, configure DHCP/routes, external-ping, directly
write PMIC/GPIO/GDSC, issue eSoC notify/BOOT_DONE spoof, global PCI rescan,
platform bind/unbind, flash, or partition-write.

The result closes the V1550 timing gap. Tracefs captures `pcie_1_gdsc`
`regulator_enable` and `regulator_enable_complete`, later matching disable
events, plus pcie1 clock/refgen/pipe clock enable activity and GPIO102
PERST-style toggles during the RC1 attempt. The RC1 path still fails before
L0: no MHI, WLFW/BDF/FW-ready, or `wlan0` marker appears. GPIO104/WAKE,
GPIO135/AP2MDM, and GPIO142/MDM2AP do not appear in the target trace window.
Next gate: classify PERST/refclk/endpoint response after confirmed RC1
power-domain enable. Do not move to firmware/MHI/WLFW/connect work until
native RC1 L0 and PCI enumeration exist.

## Latest native Wi-Fi state: V1552 (2026-06-02)

V1552 adds
`scripts/revalidation/native_wifi_rc1_endpoint_response_tracefs_v1552.py` and
passes with `v1552-ap-side-power-refclk-perst-confirmed-endpoint-silent-no-l0`.
It extends V1551 with `irq_handler_entry/exit` tracefs events and before/after
`/proc/interrupts` snapshots for `msm_pcie_wake`, `mdm status`, and
`mdm errfatal`, while keeping the same bounded pcie1 sysfs-client enumerate
trigger and the same no-HAL/no-connect/no-direct-write guardrails.

The result confirms the active blocker below the AP-side RC1 enable sequence.
During the failed RC1 attempt, tracefs captures `pcie_1_gdsc` enable/disable,
PM8150L voltage requests, pcie1 refclk and pipe-clock enable/disable, and
GPIO102/PERST assert-release-assert timing. The endpoint stays silent: no
GPIO104/WAKE, GPIO142/MDM2AP, or MDM errfatal trace line appears, and the
corresponding IRQ deltas remain zero. RC1 still fails before L0 with no MHI,
WLFW/BDF/FW-ready, or `wlan0`. Next gate: classify why SDX50M remains silent
after PERST release despite confirmed AP-side RC1 power/refclk/PERST activity;
firmware/MHI/WLFW/connect work remains parked until native RC1 L0 and PCI
enumeration exist.

## Latest native Wi-Fi state: V1553 (2026-06-02)

V1553 adds
`scripts/revalidation/native_wifi_endpoint_silence_next_gate_v1553.py` and
passes with `v1553-next-gate-android-good-power-trace-reference`. It is
host-only and reconciles V1552 with the prior PM/eSoC route, sysfs-enumerate,
Android-good tracefs, and MHI-position classifiers. It performs no device
command, tracefs/sysfs/debugfs write, Wi-Fi HAL, scan/connect, credential use,
DHCP/routes, external ping, PMIC/GPIO/GDSC write, flash, or partition write.

The fixed point is now explicit: native AP-side RC1 power/refclk/PERST is
proven, endpoint IRQs stay silent, V1496 already showed provider+RC1 still no
L0, V1530/V1534/V1540 keep Android-good and PM-route context intact, and MHI
PM-resume remains downstream of first PCI enumeration. Therefore another blind
native sysfs/debugfs enumerate retry is not the next move. Next gate: V1554
should capture an Android-good bounded tracefs reference for regulator, clk,
gpio, and irq events around the successful first-L0/lower-Wi-Fi window, then
compare it against V1552 before any new native mutation.

## Latest native Wi-Fi state: V1554 (2026-06-02)

V1554 adds
`scripts/revalidation/android_good_power_trace_reference_handoff_v1554.py`
and runs a rollbackable Android-good tracefs reference attempt using a
temporary Magisk post-fs-data module.  Native rollback completed and v724
selftest remained healthy.  The persisted run is classified as
`v1554-target-trace-captured-lower-missing-review`, not as an Android-good
reference pass.

The useful result is a negative boundary.  The module captured bounded target
tracefs evidence, including AP2MDM/GPIO135 set-high and repeated `refgen`
regulator activity, but Android did not reach BDF, FW-ready, or `wlan0` before
rollback.  Only `cnss-daemon wlfw_start` appeared.  Therefore this run must
not be compared against V1552 as a successful Android-good lower path.  Next
gate: reduce the Android-good observer to console/dmesg plus minimal GPIO/IRQ
trace and a longer hold, then reintroduce regulator/clk tracefs only after the
good lower path is preserved.  Firmware/MHI/WLFW/connect work remains parked
until native RC1 L0 and PCI enumeration exist.

## Latest native Wi-Fi state: V1555 (2026-06-02)

V1555 adds
`scripts/revalidation/android_good_minimal_trace_reference_handoff_v1555.py`
and updates the shared V1521 handoff engine to retry transient
`adb shell` closure while waiting for Android boot-complete before installing
the temporary module.  The live run passes with
`v1555-android-good-minimal-trace-reference-pass`; native rollback completes
and v724 selftest remains healthy.

This is the Android-good reference V1554 did not preserve.  With only
GPIO/IRQ tracefs plus filtered dmesg, Android reaches WLFW start, BDF downloads
for `regdb.bin` and `bdwlan.bin`, FW-ready, and `wlan0`.  The captured
GPIO/IRQ target also shows the positive endpoint-response signals missing from
native V1552: GPIO135/AP2MDM set-high, GPIO102/PERST activity, IRQ252
`msm_pcie_wake`, IRQ290 `mdm status`, and GPIO142 becoming high after mdm
status.  Timing caveat: retained RC1 L0/MHI excerpts are late relative to the
first lower-Wi-Fi markers, so the next gate should compare stable signal
deltas rather than assume that late L0 is the first enabling L0.  Next gate:
V1556 host-only comparator between V1555 Android-good minimal trace and V1552
native endpoint-silent evidence.

## Latest native Wi-Fi state: V1556 (2026-06-02)

V1556 adds
`scripts/revalidation/native_wifi_v1555_vs_v1552_endpoint_signal_comparator_v1556.py`
and passes host-only with
`v1556-stable-gap-android-endpoint-signals-native-zero`.  It compares existing
V1552 native endpoint-silent evidence with the V1555 Android-good minimal
trace reference and performs no device command or mutation.

The stable delta is now fixed.  Native V1552 already proves AP-side pcie1
power/refclk/pipe-clock/PERST activity, but endpoint response is zero:
GPIO104/pcie wake is absent, GPIO142/MDM2AP is absent, IRQ252 and IRQ290 deltas
stay zero, and no L0 appears.  Android-good V1555, under the lower-impact
observer, preserves lower Wi-Fi and shows the missing positive endpoint
signals: GPIO135/AP2MDM activity, GPIO102/PERST activity, IRQ252
`msm_pcie_wake`, IRQ290 `mdm status`, and GPIO142 high after mdm status.  The
late retained RC1 L0/MHI excerpts in V1555 remain a timing caveat, so the next
gate should act on stable signal presence/absence rather than claim first-L0
ordering.  Next gate: V1557 should either run a native provider+minimal
endpoint hold aligned to V1555's positive signals, or first capture a dmesg-only
Android timing clarifier if first-L0 ordering is required.

## Latest native Wi-Fi state: V1557 (2026-06-02)

V1557 adds
`scripts/revalidation/native_wifi_endpoint_long_hold_handoff_v1557.py` and
passes rollbackable live test boot with
`v1557-native-long-hold-endpoint-still-silent-no-l0-rollback-pass`. It reuses
the V1493 Wi-Fi test boot artifact, holds the native provider/RC1 path for
280 seconds, collects bounded below-connect evidence, and rolls back to native
v724. The post-run selftest remains healthy.

The result removes the "delayed endpoint response" hypothesis for this route:
provider and modem triggers are present and RC1 progresses far enough to hit
the known link-failed/no-L0 state, but MHI/WLFW/BDF/FW-ready/`wlan0` remain
absent and endpoint-positive signals stay zero (`msm_pcie_wake`, `mdm status`,
`mdm errfatal`, GPIO104, GPIO142, and GPIO135 high all absent). Do not run
more long-hold retries on the same V1493/V1496 path. Next gate: compare the
Android-good pre-endpoint/pre-IRQ sequence against the native provider-driven
path, focusing on why Android produces GPIO104/GPIO142/IRQ252/IRQ290 while the
native AP-side power/refclk/PERST path remains endpoint-silent.

## Latest native Wi-Fi state: V1558 (2026-06-02)

V1558 adds
`scripts/revalidation/native_wifi_post_v1557_next_gate_classifier_v1558.py`
and passes host-only with
`v1558-next-gate-android-pre-endpoint-sequence-classifier`. It combines V1523
`msm_pcie` TEST:11 static analysis, V1552 native endpoint-silent tracefs,
V1555 Android-good minimal trace, V1556 endpoint comparator, and V1557 native
long-hold evidence.

The selected next gate is now fixed: do not repeat same-path V1493/V1496
long-hold or blind pci-msm TEST:11 timing retries. Firmware/MHI/WLFW remains
downstream. V1559 should compare the Android-good pre-endpoint/pre-IRQ sequence
against the native provider-driven path: provider/esoc0 timing, GPIO135/AP2MDM,
GPIO102/PERST, pcie1 refclk/pipe/GDSC, GPIO104/WAKE + IRQ252, GPIO142/MDM2AP +
IRQ290, and only then first L0/PCI/MHI ordering if the evidence can prove it.

## Latest native Wi-Fi state: V1559 (2026-06-02)

V1559 adds
`scripts/revalidation/native_wifi_android_pre_endpoint_order_classifier_v1559.py`
and passes host-only with
`v1559-ap2mdm-before-bdf-gap-endpoint-order-caveat`. It extracts earliest
comparable timings from existing V1552, V1555, and V1557 evidence.

The earliest currently ordered Android-good discriminator is
GPIO135/AP2MDM: it appears after `esoc0` get and before BDF download. Native
still proves AP-side pcie1 GDSC/refclk/pipe/PERST activity, but produces no
GPIO135/AP2MDM, GPIO104/WAKE, GPIO142/MDM2AP, IRQ252, IRQ290, L0, MHI, WLFW,
BDF, FW-ready, or `wlan0`. V1559 also clarifies that retained V1555 IRQ252,
IRQ290, and L0 excerpts are late relative to the first retained `wlan0` lines;
they prove Android can produce endpoint-positive signals, but they must not be
used as first-L0 ordering proof. Next gate: V1560 should focus on the AP2MDM
assertion/effective-level gap before BDF and explain why native provider/RC1
does not assert GPIO135/AP2MDM despite AP-side pcie1 readiness.

## Latest native Wi-Fi state: V1560 (2026-06-02)

V1560 adds
`scripts/revalidation/native_wifi_android_order_vs_native_route_classifier_v1560.py`
and passes host-only with
`v1560-android-wlfw-before-ap2mdm-native-route-lacks-wlfw`. It compares the
ordered Android-good lower sequence against the current native V1496/V1557
auto-readiness route.

This refines V1559: Android-good reaches `cnss-daemon wlfw_start` and
`wlfw_service_request` before `esoc0`, AP2MDM/BDF, FW-ready, and `wlan0`.
Native V1496/V1557 sees `cnss-daemon` generic netlink traffic and reaches
`esoc0`, then the forced RC1 enumerate diagnostic fails before L0, but native
never emits `wlfw_start`, BDF, FW-ready, or `wlan0`. The next unit should
therefore compare Android vs native `cnss-daemon` WLFW start/request contracts
(invocation, properties, sockets, service-manager context) before any new live
connect-side action. Keep forced RC1 enumerate diagnostic-only until the WLFW
start/request contract is reproduced.

## Latest native Wi-Fi state: V1561 (2026-06-02)

V1561 adds
`scripts/revalidation/native_wifi_wlfw_contract_rebase_classifier_v1561.py`
and passes host-only with
`v1561-current-wlfw-contract-rebases-v966-service-window-next`. It reconciles
the older V966 Android WLFW attribution with current V1560/V1496/V1557
evidence.

The classification fixes the current branch: Android-good evidence reaches
`cnss-daemon wlfw_start`/`wlfw_service_request` before `/dev/subsys_esoc0`,
BDF, FW-ready, and `wlan0`; the current native v1393 Wi-Fi test boot is still
hardwired to `wifi-companion-post-pm-mdm-helper-esoc-observer`, which reaches
generic `cnss-daemon` netlink and PM/eSoC observer surfaces but never emits
`wlfw_start`. The helper already contains bounded
`wifi-companion-android-wifi-service-window-start-only` and
`wifi-companion-android-wifi-service-window-subsys-trigger-capture` modes with
service-window-only allow flags and explicit scan/connect guardrails.

Next gate: V1562 should be source/build-only route selection, not live connect.
Either make the native Wi-Fi test boot select the existing Android Wi-Fi
service-window start-only mode, or build an equivalent bounded helper runner.
Success means the artifact contains the service-window mode plus
`--allow-android-wifi-service-window` and no scan/connect, credential,
DHCP/route, external-ping, PMIC/GPIO/GDSC write, blind eSoC notify, global PCI
rescan, or platform bind/unbind path. The live follow-up should first look for
`wlfw_start`/`wlfw_service_request`, not credentials or external connectivity.

## Latest native Wi-Fi state: V1562 (2026-06-02)

V1562 updates `stage3/linux_init/v724/90_main.inc.c` and
`scripts/revalidation/build_native_init_wifi_test_boot_v1393.py` so the v1393
Wi-Fi test boot helper route is selectable at build time. The default remains
`wifi-companion-post-pm-mdm-helper-esoc-observer`; the new
`--wifi-test-helper-mode android-service-window-start-only` build route compiles
PID1 to launch `wifi-companion-android-wifi-service-window-start-only` with
`--allow-android-wifi-service-window`.

Source/build validation passes with
`v1562-android-wifi-service-window-test-boot-source-build-pass`. Artifact:
`tmp/wifi/v1562-android-wifi-service-window-test-boot/boot_linux_v1393_wifi_test.img`
with boot sha256
`3b927f60b81caaf60f01ea5fcf23cccc56d68cbc58edaf5db6e7993f5cad262d`.
The service-window PID1 binary contains the service-window mode and allow flag,
does not contain the post-PM observer route flags, and rejects service-window
combinations with RC1/provider/auto-readiness options. A backcompat source-build
smoke also passes for the default post-PM observer branch.

Next gate: V1563 can be a rollbackable live handoff using the V1562 artifact.
The only target is `cnss-daemon wlfw_start`/`wlfw_service_request` evidence under
the Android service-window route. Still do not use credentials, scan/connect,
DHCP/routes, external ping, PMIC/GPIO/GDSC writes, blind eSoC notify, global PCI
rescan, or platform bind/unbind.

## Latest native Wi-Fi state: V1563 (2026-06-02)

V1563 adds
`scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1563.py` and passes
local-only artifact sanity with
`v1563-android-wifi-service-window-artifact-sanity-pass`. It verifies the V1562
service-window test boot artifact, header/kernel parity, static ELF properties,
ramdisk entries, private output modes, credential-byte absence, service-window
boot markers, and PID1 route contract.

The verified artifact is still
`tmp/wifi/v1562-android-wifi-service-window-test-boot/boot_linux_v1393_wifi_test.img`
with boot sha256
`3b927f60b81caaf60f01ea5fcf23cccc56d68cbc58edaf5db6e7993f5cad262d`.
The sanity manifest is
`tmp/wifi/v1563-android-wifi-service-window-artifact-sanity/manifest.json` and
contains `pass=true`, making it suitable for the shared rollbackable handoff
runner preflight.

Next gate: V1564 should perform the rollbackable live handoff of only this
artifact, expect `A90 Linux init 0.9.69 (v1562-service-window)`, collect the
service-window log/summary/dmesg/`wlan0` state, roll back to v724, and classify
only `wlfw_start`/`wlfw_service_request` progress. Do not use credentials,
scan/connect, DHCP/routes, or external ping.

## Latest native Wi-Fi state: V1564 (2026-06-02)

V1564 adds
`scripts/revalidation/native_wifi_test_boot_handoff_v1564.py` and performs a
rollbackable live handoff of the V1562 Android Wi-Fi service-window test boot.
The handoff itself is healthy: the device boots
`A90 Linux init 0.9.69 (v1562-service-window)`, the PID1 supervisor launches
`wifi-companion-android-wifi-service-window-start-only`, the helper exits with
code 0, rollback to `stage3/boot_linux_v724.img` succeeds, and post-rollback
selftest passes.

Strict Wi-Fi progress is still blocked with
`v1564-test-boot-no-downstream-wifi-progress-blocked`. Focused dmesg captures
`cnss_diag`, `cnss-daemon`, and `wificond` generic netlink/binder activity, but
there is no `wlfw_start`, `wlfw_service_request`, ICNSS-QMI, BDF/regdb,
FW-ready, MHI, RC1, or `wlan0` marker; the explicit `wlan0` check reports
absent. This removes the candidate that simply switching PID1 from the post-PM
observer route to Android Wi-Fi service-window start-only is sufficient.

Next gate: classify why the service-window helper exits cleanly without
producing the Android-good WLFW request contract. Compare helper output,
service-manager context, properties, sockets, and process environment against
Android-good service-window evidence. Do not proceed to credentials,
scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, blind eSoC
notify, global PCI rescan, or platform bind/unbind.

## Latest native Wi-Fi state: V1565 (2026-06-02)

V1565 adds
`scripts/revalidation/native_wifi_service_window_gap_classifier_v1565.py` and
passes host-only with
`v1565-select-service-window-subsys-trigger-capture-build`. It reconciles V1564
with the older V998/V1001 service-window chain.

The fixed conclusion is: V1564 was a valid rollbackable proof of the
`android-service-window-start-only` test boot route, but that route produced no
WLFW/downstream progress. V998 already showed that a repaired full
service-window actor set could be clean and still have no WLFW when
`/dev/subsys_esoc0` was not attempted. V1001 selected the scoped
service-window subsystem trigger as the next useful route. Current sources now
support that route at build time via
`android-service-window-subsys-trigger-capture` and
`--allow-android-wifi-service-window-subsys-trigger-capture`.

Next gate: V1566 should be source/build-only. Build a Wi-Fi test boot artifact
using `android-service-window-subsys-trigger-capture`, verify the PID1 argv
contains both Android service-window allow flags, and verify the artifact still
excludes credentials, scan/connect, DHCP/routes, external ping, blind
notify/BOOT_DONE, global PCI rescan, and platform bind/unbind. Do not rerun
start-only and do not attempt credentialed Wi-Fi connect yet.

## Latest native Wi-Fi state: V1566 (2026-06-02)

V1566 builds the next Wi-Fi test boot artifact and adds
`scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1566.py`.
Source/build plus local artifact sanity pass with
`v1566-service-window-subsys-trigger-artifact-sanity-pass`.

The generated artifact is
`tmp/wifi/v1566-android-wifi-service-window-subsys-trigger-test-boot/boot_linux_v1393_wifi_test.img`
with boot sha256
`4b2cd6b0fe07c5826c0c3865b5fd60fff37a3d3a9437f5998312b7103cc11a65`.
It boots `A90 Linux init 0.9.69 (v1566-service-window-subsys-trigger)` and
selects `wifi-companion-android-wifi-service-window-subsys-trigger-capture`.
The sanity verifier confirms both Android service-window allow flags are in the
PID1 argv, the start-only/post-PM observer/forced-RC1/private-CNSS/connect
flags are absent from the PID1 route, static init/helper binaries are present,
boot header/kernel parity with v724 is preserved, and no credential,
scan/connect, DHCP/route, external-ping, flash, or partition-write action is
recorded by the source/build manifest.

Next gate: V1567 can perform a rollbackable live handoff of only this V1566
image, collect helper log/summary, focused dmesg, trigger-window fields, and
`wlan0` state, then roll back to v724. The target is WLFW/BDF/FW-ready/`wlan0`
progress and trigger-window classification. Do not use credentials,
scan/connect, DHCP/routes, external ping, blind eSoC notify/`BOOT_DONE`, global
PCI rescan, or platform bind/unbind.

## Latest native Wi-Fi state: V1567 (2026-06-02)

V1567 adds
`scripts/revalidation/native_wifi_test_boot_handoff_v1567.py` and performs the
rollbackable live handoff of the V1566 service-window subsystem-trigger test
boot.  The image boots, the PID1 supervisor launches
`wifi-companion-android-wifi-service-window-subsys-trigger-capture`, the helper
exits normally with `helper_exit_code=0` and `helper_timed_out=0`, and rollback
to `stage3/boot_linux_v724.img` succeeds.

Strict Wi-Fi progress still blocks with
`v1567-test-boot-no-downstream-wifi-progress-blocked` and final decision
`no-provider-no-downstream`: no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` marker appears.
Focused dmesg shows generic `cnss_diag`, `cnss-daemon`, and `wificond` activity,
but no downstream Wi-Fi bring-up marker.

The important new finding is an evidence-path gap.  The helper source emits
`android_wifi_service_window.*`, `cnss_before_esoc.*`, and `subsys_trigger.*`
contract fields, but the persisted PID1 log contains only supervisor lifecycle
lines.  Therefore V1567 cannot classify whether `/dev/subsys_esoc0` was
attempted, skipped by the mdm-helper eSoC-fd predicate, or attempted without
provider/RC1 progress.

Next gate: V1568 should be source/build-only.  Repair the V1393/V1566 test-boot
evidence path so the service-window helper contract output is persisted in a
private result artifact or equivalent PID1-captured stdout/stderr log, then
sanity-check the artifact before any live rerun.  Still do not use credentials,
scan/connect, DHCP/routes, external ping, blind eSoC notify/`BOOT_DONE`, global
PCI rescan, or platform bind/unbind.

## Latest native Wi-Fi state: V1568 (2026-06-02)

V1568 repairs the service-window evidence path and builds the next rollbackable
test-boot artifact.  `a90_android_execns_probe` is bumped to v288 and accepts
`--result-output-path`, writing the final helper `STDOUT`/`STDERR` buffers to a
private `0600`/`O_NOFOLLOW` result file.  The V1393 PID1 test-boot path now
passes `/cache/native-init-wifi-test-boot-v1393-helper.result` and records that
path and size in the test summary.

The source/build artifact passes local sanity with
`v1568-service-window-subsys-trigger-result-artifact-sanity-pass`.  It uses
`wifi-companion-android-wifi-service-window-subsys-trigger-capture`, includes
both Android service-window allow flags plus `--result-output-path`, preserves
boot header/kernel parity with v724, uses static init/helper binaries, and
keeps credentials, scan/connect, DHCP/routes, external ping, blind
eSoC notify/`BOOT_DONE`, global PCI rescan, and platform bind/unbind out of
scope.

Artifact:
`tmp/wifi/v1568-service-window-subsys-trigger-result-test-boot/boot_linux_v1393_wifi_test.img`
with boot sha256
`0bf402cf31ce53e4e6a8d365d4b105cb31ec8e58b484c9a681872c62c87279a4`.
Helper v288 sha256 is
`ecc889253d8de7b8afdc09721ca780ea28d839fec00b5cb16380c6b7fd419c5b`.

Next gate: V1569 can perform a rollbackable live handoff of only this V1568
image, collect the normal log, summary, focused dmesg, `wlan0`, and the new
helper result file, then roll back to v724.  The primary target is not
credentialed Wi-Fi connect yet; it is classifying whether `/dev/subsys_esoc0`
was attempted, predicate-skipped, or attempted without RC1/MHI/WLFW/`wlan0`
progress.

## Latest native Wi-Fi state: V1569 (2026-06-02)

V1569 performs the rollbackable live handoff of the V1568 result-output test
boot and rolls back cleanly to v724.  Strict Wi-Fi progress is still blocked
with `v1569-test-boot-no-downstream-wifi-progress-blocked`, but the new helper
result file resolves the prior evidence gap.

The helper result artifact is present and complete:
`/cache/native-init-wifi-test-boot-v1393-helper.result` is collected at
`563961` bytes and contains `A90_EXECNS_RESULT_FILE_BEGIN` plus
`android_wifi_service_window.begin=1`.  The helper enters
`guarded-subsys-trigger-capture`, starts all 14 planned service-window actors,
and records final result
`subsys-trigger-not-attempted-no-mdm-helper-esoc-fd` with reason
`service-window-gate-did-not-see-dev-esoc-0`.

The important classification is:
`mdm_helper_esoc0_fd_count=0`, `subsys_trigger_gate_open=0`,
`subsys_trigger_start_attempted=0`, `subsys_trigger_started=0`, and
`subsys_esoc0_open_attempted=0`.  Focused dmesg still shows only generic
`cnss_diag`, `cnss-daemon`, and `wificond` activity, with no provider/RC1/MHI/
WLFW/BDF/FW-ready/`wlan0` marker.

Current blocker for this route is therefore before RC1/LTSSM: native
service-window userspace starts `mdm_helper`, but `mdm_helper` never acquires
`/dev/esoc-0`, so the scoped `/dev/subsys_esoc0` trigger is correctly not
attempted.  Next gate should be V1570 host-only or source/build-only:
compare the Android-good `mdm_helper` launch contract against native
service-window launch and add a bounded mdm-helper fd acquisition classifier if
needed.  Do not move to credentials/connect, DHCP/routes, external ping,
firmware/MHI deep dive, or RC1 retry until the mdm-helper `/dev/esoc-0` fd
predicate is satisfied or deliberately replaced by a reviewed gate.

## Latest native Wi-Fi state: V1570 (2026-06-02)

V1570 adds a host-only mdm-helper fd-gate classifier and passes with
`v1570-select-mdm-helper-launch-contract-delta`.  It consumes V1569 plus the
older Android/reduced-native references and confirms the active service-window
route is blocked before RC1/LTSSM.

Key checks all pass: V1569 handoff/rollback was clean, V1569 helper result was
complete, V1569 had `mdm_helper_esoc0_fd_count=0` and
`subsys-trigger-not-attempted-no-mdm-helper-esoc-fd`, Android V1158 proves
`mdm_helper` opens `/dev/esoc-0`, reduced native V1228 proves native
`mdm_helper` can hold `/dev/esoc-0` and reach `ESOC_WAIT_FOR_REQ`, and V1008/
V1009 show this is the same known service-window negative delta.

Next gate: V1571 should be source/build-only.  Add a service-window
`mdm_helper` launch-contract comparator that records the native
service-window `mdm_helper` argv/env/properties/dev-node/context and compares it
against the known positive mdm-helper modes.  Do not retry RC1, firmware/MHI,
credentials/connect, DHCP/routes, or external ping until the mdm-helper
`/dev/esoc-0` fd predicate is satisfied or a new reviewed bounded gate replaces
that predicate.

## Latest native Wi-Fi state: V1571 (2026-06-02)

V1571 completes the source/build-only service-window `mdm_helper` launch
contract comparator and passes local artifact sanity with
`v1571-mdm-helper-launch-contract-artifact-sanity-pass`.

The helper is bumped to `a90_android_execns_probe v289` and records
`android_wifi_service_window.mdm_helper_launch_contract` snapshots in the
service-window route.  The comparator captures planned and post-spawn
`mdm_helper` target/argv/env/identity/SELinux/dev-node/fd state, records the
known `pm_proxy`/`pm_proxy_helper` absence delta, and does not change the
service-window actor order or any lower eSoC/PCIe action.

Artifact:
`tmp/wifi/v1571-mdm-helper-launch-contract-test-boot/boot_linux_v1393_wifi_test.img`
with boot sha256
`d5fc21430720868d3836f6bb6b7b811348cfadb3596bdc3274a7aef84f0b6392`.
Helper v289 sha256 is
`264d3ba7215330ea08a080ade27f0b19c3b888e74ee783dda08a5a22a2aa463a`.

Next gate: V1572 can perform a rollbackable live handoff of only this V1571
image, collect the private helper result file, classify whether the
service-window `mdm_helper` launch contract explains the missing `/dev/esoc-0`
fd, and roll back to v724.  Still do not move to credentials/connect,
DHCP/routes, external ping, firmware/MHI deep dive, or RC1 retry until the
mdm-helper `/dev/esoc-0` fd predicate is satisfied or a new reviewed bounded
gate replaces that predicate.

## Latest native Wi-Fi state: V1572-V1574 (2026-06-02)

V1572 performed the rollbackable V1571 live handoff and rolled back cleanly,
but exposed a test-artifact defect rather than a new Wi-Fi result: the v289
helper exited by signal 11 and PID1 collected a stale helper result file whose
`result_file_version` was still `a90_android_execns_probe v288`.  Treat V1572
as crash/stale-result evidence only.

V1573 fixes that evidence path.  PID1 now unlinks the stale
`/cache/native-init-wifi-test-boot-v1393-helper.result` before each test boot,
and the helper is bumped to `a90_android_execns_probe v290`; the large
service-window launch-contract formatter is split into bounded append calls.
The V1573 artifact passes local sanity with
`v1573-mdm-helper-launch-contract-crashfix-artifact-sanity-pass`.  Artifact:
`tmp/wifi/v1573-mdm-helper-launch-contract-crashfix-test-boot/boot_linux_v1393_wifi_test.img`
with boot sha256
`ea028a2c0c96241a9e1a558cfa39af631924ee428672004f410218b8e15c893a`;
helper v290 sha256 is
`ecc9b3ad1fd5a3644e8fed1a54e57befb92641c33ff1f2c2c6d77a4087109518`.

V1574 then performs the rollbackable V1573 live handoff and rolls back to v724
successfully.  The helper no longer crashes (`helper_status_raw=0`,
`helper_exited=1`, `helper_exit_code=0`, `helper_signaled=0`) and the collected
result is fresh (`result_file_version=a90_android_execns_probe v290`).  The
launch-contract classifier confirms the active service-window delta:
`planned.compare.pm_proxy_absent_delta=1`,
`after_mdm_helper_spawn.compare.pm_proxy_absent_delta=1`,
`after_mdm_helper_spawn.fd.esoc0=0`,
`after_mdm_helper_spawn.fd.subsys_esoc0=0`,
`after_mdm_helper_spawn.fd.subsys_modem=0`,
`mdm_helper_esoc0_fd_count=0`, `subsys_trigger_gate_open=0`,
`subsys_trigger.started=0`, final result
`subsys-trigger-not-attempted-no-mdm-helper-esoc-fd`.

Current conclusion: the active Wi-Fi test boot is blocked before the prior RC1
path because service-window `mdm_helper` is started without the Android-good
`pm_proxy`/`pm_proxy_helper` launch contract and never acquires `/dev/esoc-0`.
Next gate should not retry RC1, firmware/MHI, credentials/connect,
DHCP/routes, or external ping.  The next bounded step should either add the
missing `pm_proxy`/`pm_proxy_helper` launch contract in source/build-only form
or write a host-only contract diff proving which `pm-service` Binder request is
required to make `mdm_helper` hold `/dev/esoc-0`.

## Latest native Wi-Fi state: V1575-V1586 (2026-06-02)

V1575-V1586 closes the service-window PM proxy contract and firmware mount
prerequisite loop.  The helper is now `a90_android_execns_probe v292` with
sha256 `922654100570c2f7c898c11053775418c0c4881e714e5fdb22e9a274acbbde8c`.

Key progression:

- V1576 proved the PM proxy contract route was selected, but the helper private
  namespace lacked `/dev/esoc-0`, `/dev/subsys_esoc0`, and `/dev/subsys_modem`,
  so `subsys-trigger-not-attempted-no-mdm-helper-esoc-fd` remained correct.
- V1578 fixed private devnode materialization for service-window modes.  The
  helper observed `/dev/esoc-0` and `/dev/subsys_esoc0`, `mdm_helper` held
  `/dev/esoc-0`, and the scoped `/dev/subsys_esoc0` trigger started.  This
  moved the blocker from devnode/fd parity to modem firmware visibility.
- V1580 and V1582 showed the first firmware-mount implementation failed before
  helper launch because `/vendor` is a symlink and the attempted mount targets
  resolved into read-only `/mnt/system/vendor` paths.
- V1584 showed a hybrid vendor overlay must not require `/vendor/bin`,
  `/vendor/lib64`, or `/vendor/etc` in the global namespace; those paths are
  provided by the helper's private `sda29` vendor namespace, not by PID1's
  global `/vendor`.
- V1586 passes as `v1586-test-boot-downstream-progress-rollback-pass`.  The
  test boot mounts firmware read-only through a firmware-only global `/vendor`
  overlay, launches the service-window PM proxy contract, collects a fresh
  helper result (`758102` bytes), and rolls back cleanly to v724.

Important V1586 evidence:

- `firmware mounts prepare rc=0` and `firmware_mounts_requested=1`.
- `provider_trigger=True`, `modem_trigger=True`,
  `helper_result_subsys_open_attempted=1`,
  `helper_result_subsys_trigger_started=1`,
  `helper_result_mdm_helper_esoc0_fd_count=1`.
- Dmesg shows `pm_proxy_helper` opening `subsys_modem`, modem PIL loading, and
  `subsys-pil-tz ... modem: Brought out of reset`.
- `cnss_diag` and `cnss-daemon` reach cld80211/netlink; the classifier records
  `wlfw_progress=True` via `icnss_qmi` markers.
- Still absent: RC1/L0 markers, MHI markers, BDF/regdb, FW-ready, and `wlan0`.
  The final progress decision is `firmware-progress-no-wlan0`.

Current conclusion: the active route has advanced past the old global firmware
mount and devnode/fd blockers.  It is not connect-ready.  The next bounded gate
should preserve V1586 firmware mount parity and add focused lower markers for
RC1/MHI/WLFW request/state transitions, without credentials, scan/connect,
DHCP/routes, external ping, blind eSoC notify/`BOOT_DONE`, PMIC/GPIO/GDSC direct
writes, global PCI rescan, or platform bind/unbind.

## Latest native Wi-Fi state: V1587 (2026-06-02)

V1587 adds
`scripts/revalidation/native_wifi_lower_marker_next_gate_classifier_v1587.py`
and passes host-only as `v1587-v1586-current-lower-marker-gate-required`.
It reconciles the user's V1496 RC1 framing with the current repo state:
V1496 remains a valid forced-RC1 `no L0` failure, but V1535 already completed
the `msm_pcie` static/first-L0 candidate classification and V1560 already
showed Android's lower route reaches `wlfw_start` while native forced-RC1 does
not.  V1586 is therefore the active route to preserve.

V1587 reclassifies the next unit as a source/build-only focused lower-marker
sampler.  It must keep the V1586 firmware overlay and helper private vendor
namespace intact while compactly sampling process lifetimes, fd counts,
subsystem states, RC1/LTSSM, runtime MHI, QRTR/WLFW, BDF, FW-ready, and
`wlan0`.  Do not proceed to credentials, scan/connect, DHCP/routes, external
ping, blind eSoC notify/`BOOT_DONE`, PMIC/GPIO/GDSC direct writes, global PCI
rescan, or platform bind/unbind.  Report:
`docs/reports/NATIVE_INIT_V1587_LOWER_MARKER_NEXT_GATE_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1588-V1589 (2026-06-02)

V1588 updates `a90_android_execns_probe` to v293 and adds compact
`android_wifi_service_window.lower_marker` sampling to the V1586 service-window
route.  The sampler records process liveness/fd maxima, subsystem state,
RC1/LTSSM transition state, runtime MHI bus/pipe, `ks`, CNSS/WLFW request
markers, BDF, FW-ready, and `wlan0` without per-sample verbose dumps.  The
source/build artifact passes with
`v1588-service-window-lower-marker-test-boot-source-build-pass`; boot image:
`tmp/wifi/v1588-service-window-lower-marker-test-boot/boot_linux_v1588_wifi_test.img`
with sha256 `f85761a2dfe6e4b08b3f7b3cde6a9e4bdaef9f02f2f6383aaa659cbf4d52f0d5`.
Artifact sanity passes as
`v1588-service-window-lower-marker-artifact-sanity-pass`.

V1589 flashes only that V1588 image, collects the log/summary/helper
result/dmesg/`wlan0` state, and rolls back from native to v724.  Post-rollback
`version` reports `A90 Linux init 0.9.68 (v724)` and `selftest` reports
`fail=0`.  V1589 passes as
`v1589-test-boot-downstream-progress-rollback-pass`, but final progress remains
`firmware-progress-no-wlan0`.

Important V1589 lower-marker facts:

- `pm_proxy_helper_alive_seen=1`, `pm_proxy_helper_subsys_modem_fd_max=1`.
- `per_mgr_alive_seen=0`, `per_mgr_subsys_modem_fd_max=-1`.
- `pm_proxy_alive_seen=1`, `mdm_helper_alive_seen=1`,
  `mdm_helper_esoc0_fd_max=1`.
- scoped trigger child is alive and later captured in `mdm_subsys_powerup`, but
  `trigger_child_subsys_esoc0_fd_max=0` and `global_subsys_esoc0_fd_max=0`.
- `pcie_rc1_transition_seen=0`, `mhi_bus_max=0`, `mhi_pipe_seen=0`,
  `ks_process_max=0`, `wlfw_start_kmsg_max=0`,
  `wlfw_service_request_kmsg_max=0`, `bdf_kmsg_max=0`,
  `fw_ready_kmsg_max=0`, `wlan0_seen=0`.
- lower-marker checkpoint is `cnss-netlink-only`.

Current blocker: the project has progressed past firmware mount, private
devnode, PM proxy helper, `mdm_helper` `/dev/esoc-0`, and scoped
`/dev/subsys_esoc0` trigger start.  The remaining active gap is that
`pm-service` is not alive in the lower-marker window and the explicit trigger
child, not Android's PM-service Binder thread, is the process stuck in
`mdm_subsys_powerup`.  Next work should classify `pm-service` exit/lifetime and
the missing PM-service-owned powerup contract, not credentials/connect.
Reports:
`docs/reports/NATIVE_INIT_V1588_SERVICE_WINDOW_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md`,
`docs/reports/NATIVE_INIT_V1588_SERVICE_WINDOW_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md`,
and
`docs/reports/NATIVE_INIT_V1589_SERVICE_WINDOW_LOWER_MARKER_HANDOFF_2026-06-02.md`.

## Latest native Wi-Fi state: V1590 (2026-06-02)

V1590 adds
`scripts/revalidation/native_wifi_pm_service_lifetime_route_classifier_v1590.py`
and passes host-only as
`v1590-route-current-service-window-loses-pm-service-owned-powerup`.
It compares current V1589 lower-marker evidence against the older positive
PM-service-owned route references V1238 and V1303.

V1590 confirms the current V1588/V1589 service-window ordering is not the right
lower route to repeat as-is:

- V1589 current route: `per_mgr_alive_seen=0`, `per_mgr_child_exit_code=0`,
  `pm_proxy_child_exit_code=1`, `global_subsys_esoc0_fd_max=0`,
  `pm_service_powerup_seen=0`, and `dmesg_pm_service_esoc0_get=0`.
- The live `mdm_subsys_powerup` stack in V1589 belongs to the scoped helper
  trigger child, not PM-service.
- V1238 remains a positive route reference:
  `pm_service_actor_esoc0_attempt=True` and
  `post_pm_fd_esoc0_count=1`.
- V1303 remains a positive route reference:
  `powerup_subsys_esoc0_inferred_seen=True`,
  `max_powerup_thread_count=1`, `powerup_first_path_values=/dev/subsys_esoc0`,
  and `powerup_first_wchans=mdm_subsys_powerup`.

Next work: V1591 should be source/build-only and derive a
firmware-mount-preserving late-`per_proxy`-only service-window test boot with
lower-marker sampling, no direct scoped trigger, and explicit PM-service
lifetime/exit markers.  Do not proceed to credentials, scan/connect,
DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC
notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind.  Report:
`docs/reports/NATIVE_INIT_V1590_PM_SERVICE_LIFETIME_ROUTE_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1591 (2026-06-02)

V1591 implements the V1590-selected route as source/build-only tooling.
`a90_android_execns_probe` is bumped to v294 and adds
`--allow-android-wifi-service-window-late-per-proxy-only`.  In Android
service-window mode this keeps the PM proxy contract and lower-marker sampler,
but moves `pm-proxy` after the mdm_helper/CNSS window and disables the direct
scoped helper `/dev/subsys_esoc0` trigger child.

Source build passes as
`v1591-late-per-proxy-lower-marker-test-boot-source-build-pass`:

- boot image:
  `tmp/wifi/v1591-late-per-proxy-lower-marker-test-boot/boot_linux_v1591_wifi_test.img`
- boot sha256:
  `ef917e0f6dc65530b93ecd808598098c8b8cf94897cc5b518eca026829823466`
- init: `A90 Linux init 0.9.102 (v1591-late-per-proxy-lower-marker)`
- helper marker: `a90_android_execns_probe v294`
- helper sha256:
  `01b059f894b62a3b4eef3f01065dbad62dcc20f443feb0509c883a37608dbbc7`

Artifact sanity passes as
`v1591-late-per-proxy-lower-marker-artifact-sanity-pass`.  The verifier checks
static init/helper binaries, boot/header/kernel parity, ramdisk entries, helper
v294/late-`per_proxy` markers, lower-marker strings, private file modes, and
forbidden credential-like byte absence.  No device command, flash, reboot,
scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC write,
blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or
partition write occurred.

Next work: V1592 rollbackable live handoff of only the V1591 image, collect
log/summary/helper result/dmesg/`wlan0`, then roll back to v724 and verify
selftest `fail=0`.  Reports:
`docs/reports/NATIVE_INIT_V1591_LATE_PER_PROXY_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1591_LATE_PER_PROXY_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md`.

## Latest native Wi-Fi state: V1592 (2026-06-02)

V1592 adds `scripts/revalidation/native_wifi_test_boot_handoff_v1592.py` and
runs the rollbackable live handoff for the V1591 late-`per_proxy` image.  The
live handoff itself succeeds: the test image boots as
`A90 Linux init 0.9.102 (v1591-late-per-proxy-lower-marker)`, evidence is
collected from `/cache/native-init-wifi-test-boot-v1591.*`, rollback from
native succeeds, post-rollback version is v724, and selftest remains
`fail=0`.

Strict reclassification hardens the old handoff classifier: an
`icnss_qmi: Fail to send Shutdown req` line is shutdown/error evidence, not
WLFW progress.  Only `icnss_qmi: QMI Server Connected` is counted as an ICNSS
QMI connection marker.  With that correction, V1592 is blocked as
`v1592-test-boot-no-downstream-wifi-progress-blocked` even though
handoff/rollback passed.

V1592 evidence summary:

- `modem_trigger=True`, but `provider_trigger=False`.
- No RC1/LTSSM, MHI, WLFW, BDF, FW-ready, or `wlan0` marker is present.
- Helper mode is `guarded-pm-proxy-contract-late-per-proxy-lower-marker`.
- `late_per_proxy_only=1`, direct `/dev/subsys_esoc0` trigger is disabled, and
  `mdm_helper` holds `/dev/esoc-0`.
- `pm_proxy` exits `1`; `per_mgr` exits `0`; `pm_full_contract_seen=0`.
- Helper result is `subsys-trigger-start-failed` with reason
  `service-window-gate-opened-but-trigger-child-did-not-start`.

Next work: classify the late `pm_proxy` exit path and `per_mgr` lifetime in
the full service-window route.  The next useful cycle should be host-only or
source/build-only first: parse V1592 helper output for `pm_proxy`/`per_mgr`
failure context, compare with V1238/V1303 positive late-`per_proxy` evidence,
and only then design a bounded live gate that preserves the PM-service-owned
`/dev/subsys_esoc0` route.  Do not proceed to credentials, scan/connect,
DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC
notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or unbounded
boot-image/partition writes.  Report:
`docs/reports/NATIVE_INIT_V1592_LATE_PER_PROXY_LOWER_MARKER_HANDOFF_2026-06-02.md`.

## Latest native Wi-Fi state: V1593 (2026-06-02)

V1593 adds
`scripts/revalidation/native_wifi_pm_proxy_per_mgr_lifetime_classifier_v1593.py`
and classifies the V1592 failure host-only against V1238/V1303.  It passes as
`v1593-late-per-proxy-regressed-before-pm-service-owned-powerup`.

V1593 current-route finding:

- V1592 handoff/rollback is clean, but strict Wi-Fi progress is blocked before
  lower hardware: `modem_trigger=True`, `provider_trigger=False`, and no
  RC1/MHI/WLFW/BDF/FW-ready/`wlan0`.
- `pm-proxy` starts as `/vendor/bin/pm-proxy`, preexec passes, SELinux exec and
  current-context setup report `ok=1`, then the child exits `1`.
- `pm-service` starts as `/vendor/bin/pm-service`, but the first fd match for
  `/dev/subsys_modem` already fails with `No such file or directory`; final
  `per_mgr` observable is `0`, exit code is `0`, and `pm_full_contract_seen=0`.
- The V1592 order is the full service-window order:
  `... wifi_hal_legacy,wifi_hal_ext,per_mgr,cnss_diag,wificond,mdm_helper,cnss_daemon,pm_proxy_late ...`.

Positive-route references:

- V1238 order is stripped and PM-first:
  `... pm_proxy_helper,per_mgr,vndservice_query,per_proxy_deferred,cnss_daemon,mdm_helper,late_per_proxy ...`,
  with no Wi-Fi HAL/wificond before the PM-service-owned route.
- V1238 reaches PM-service `/dev/subsys_esoc0`; V1303 confirms
  `/dev/subsys_esoc0` + `mdm_subsys_powerup` through compact powerup markers.

Next work: V1594 should be source/build-only and make the test-boot route
match the V1238/V1303 PM-service-owned boundary before any new lower-layer
mutation.  Keep V1591 firmware mount parity, keep direct scoped
`/dev/subsys_esoc0` trigger disabled, do not start Wi-Fi HAL/wificond before
the PM-service powerup observation, and add explicit `pm-proxy`/`per_mgr`
stderr/exit/lifetime diagnostics.  Still no credentials, scan/connect,
DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC
notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or unbounded
boot-image/partition writes.  Report:
`docs/reports/NATIVE_INIT_V1593_PM_PROXY_PER_MGR_LIFETIME_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1594/V1595 (2026-06-02)

V1594 implements the V1593-selected source/build route.  Helper
`a90_android_execns_probe` is bumped to v295 and adds
`--allow-android-wifi-service-window-pm-first-route`.  The new test boot keeps
V1591 firmware mount parity and the private vendor namespace, but changes the
service-window child order to PM-first:

`servicemanager,hwservicemanager,vndservicemanager,pm_proxy_helper,per_mgr,pm_proxy,mdm_helper,cnss_daemon,pm-first-lower-marker-no-direct-trigger-no-wifi-hal`

This route intentionally does not start Wi-Fi HAL or `wificond` before
PM-service-owned `/dev/subsys_esoc0` observation, keeps the direct scoped
`/dev/subsys_esoc0` trigger disabled, and classifies the PM boundary as either
`pm-service-owned-powerup-observed` or
`pm-service-owned-powerup-missing`.

V1594 source build passes as
`v1594-pm-first-lower-marker-test-boot-source-build-pass`:

- boot image:
  `tmp/wifi/v1594-pm-first-lower-marker-test-boot/boot_linux_v1594_wifi_test.img`
- boot sha256:
  `86ec9d6fbce5ac56e70815cac7aa1dc1a45aee1d5dd8a0fb53f81dc7c4d44417`
- init: `A90 Linux init 0.9.103 (v1594-pm-first-lower-marker)`
- helper marker: `a90_android_execns_probe v295`
- helper sha256:
  `8c26d83b1055bdf50f50086d3518a04ecbaea1195d0c01ed265f619d742c8f1d`

V1595 artifact sanity passes as
`v1595-pm-first-lower-marker-artifact-sanity-pass`.  It verifies static
init/helper binaries, boot/header/kernel parity, ramdisk entries, PM-first
route strings, service-window PM proxy contract, firmware mounts, helper v295,
lower-marker strings, private file modes, and forbidden credential-like byte
absence.

Next work: V1596 rollbackable live handoff of only the V1594 image, collect
log/summary/helper result/dmesg/`wlan0`, then roll back to v724 and verify
selftest `fail=0`.  Still no credentials, scan/connect, DHCP/routes, external
ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI
rescan, platform bind/unbind, or unbounded boot-image/partition writes.
Reports:
`docs/reports/NATIVE_INIT_V1594_PM_FIRST_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1595_PM_FIRST_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md`.

## Latest native Wi-Fi state: V1596 (2026-06-02)

V1596 adds `scripts/revalidation/native_wifi_test_boot_handoff_v1596.py` and
runs the rollbackable live handoff for the V1594 PM-first lower-marker image.
The handoff/rollback path is clean: the V1594 image boots, evidence is
collected from `/cache/native-init-wifi-test-boot-v1594.*`, rollback from
native restores v724, and post-rollback selftest remains `fail=0`.

Strict Wi-Fi progress remains blocked as
`v1596-test-boot-no-downstream-wifi-progress-blocked`.  The key result is that
the stripped PM-first route still does not reproduce the Android-good
PM-service-owned `/dev/subsys_esoc0` path:

- `modem_trigger=True`, but `provider_trigger=False`.
- No RC1/LTSSM, MHI, WLFW, BDF, FW-ready, or `wlan0` marker is present.
- Helper mode is `guarded-pm-proxy-contract-pm-first-lower-marker`.
- `pm_first_route=1`, `late_per_proxy_only=1`, and the direct scoped
  `/dev/subsys_esoc0` trigger remains disabled.
- `pm_proxy_helper` is alive during lower-marker sampling and holds
  `/dev/subsys_modem`; `mdm_helper` is alive and holds `/dev/esoc-0`.
- `pm-service`/`per_mgr` exits `0` before it is observable in the lower-marker
  window; `pm-proxy` exits `1`; `pm_full_contract_seen=0`.
- Helper result is `pm-service-owned-powerup-missing` with reason
  `pm-first-route-did-not-reach-dev-subsys-esoc0-mdm-subsys-powerup`.

This keeps the active blocker above SDX50M/eSoC/RC1 hardware.  V1596 did not
reach the provider powerup boundary, so RC1/PERST/refclk, MHI, WLFW, BDF, and
`wlan0` analysis remains downstream of the current failure.

Next work: V1597 should be source/build-only and reproduce the V1238/V1303
positive route more exactly: keep the stripped no-HAL/no-wificond service
window, but move `pm-proxy` back to the late/deferred position after the CNSS
and `mdm_helper` setup, preserve `pm_proxy_helper` and `per_mgr`, and add
focused `pm-proxy`/`pm-service` exit/lifetime diagnostics.  Do not proceed to
credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct
writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind,
or unbounded boot-image/partition writes.  Report:
`docs/reports/NATIVE_INIT_V1596_PM_FIRST_LOWER_MARKER_HANDOFF_2026-06-02.md`.

## Latest native Wi-Fi state: V1597/V1598 (2026-06-02)

V1597 implements the V1596-selected source/build route.  Helper
`a90_android_execns_probe` is bumped to v296 and adds
`--allow-android-wifi-service-window-pm-first-late-per-proxy-route`.  The new
test boot keeps V1591 firmware mount parity, private devnodes, and the helper
private vendor namespace, but changes the stripped service-window order to
match the V1238/V1303 positive boundary more closely:

`servicemanager,hwservicemanager,vndservicemanager,pm_proxy_helper,per_mgr,cnss_daemon,mdm_helper,pm_proxy_late,pm-first-late-per-proxy-lower-marker-no-direct-trigger-no-wifi-hal`

This route intentionally does not start Wi-Fi HAL or `wificond`, keeps the
direct scoped `/dev/subsys_esoc0` trigger disabled, starts `pm-proxy` only in a
late/deferred position after CNSS/`mdm_helper` setup, and classifies the PM
boundary as either `pm-service-owned-powerup-observed` or
`pm-service-owned-powerup-missing`.

V1597 source build passes as
`v1597-pm-first-late-per-proxy-lower-marker-test-boot-source-build-pass`:

- boot image:
  `tmp/wifi/v1597-pm-first-late-per-proxy-lower-marker-test-boot/boot_linux_v1597_wifi_test.img`
- boot sha256:
  `68f25e21cb09a7420a9e7876b05e1455d25eaeec3d6ac8c37a3d7e649cf425f3`
- init: `A90 Linux init 0.9.104 (v1597-pm-first-late-per-proxy-lower-marker)`
- helper marker: `a90_android_execns_probe v296`
- helper sha256:
  `36e964fc3d160de9cca8c105c4e36a16d47569800b478dba8d4ca2a176d4f850`

V1598 artifact sanity passes as
`v1598-pm-first-late-per-proxy-lower-marker-artifact-sanity-pass`.  It
verifies static init/helper binaries, boot/header/kernel parity, ramdisk
entries, PM-first late-per-proxy route strings, service-window PM proxy
contract, firmware mounts, helper v296, lower-marker strings, private file
modes, and forbidden credential-like byte absence.

Next work: V1599 rollbackable live handoff of only the V1597 image, collect
log/summary/helper result/dmesg/`wlan0`, then roll back to v724 and verify
selftest `fail=0`.  Still no credentials, scan/connect, DHCP/routes, external
ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI
rescan, platform bind/unbind, or unbounded boot-image/partition writes.
Reports:
`docs/reports/NATIVE_INIT_V1597_PM_FIRST_LATE_PER_PROXY_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1598_PM_FIRST_LATE_PER_PROXY_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md`.

## Latest native Wi-Fi state: V1599 (2026-06-02)

V1599 adds `scripts/revalidation/native_wifi_test_boot_handoff_v1599.py` and
runs the rollbackable live handoff for the V1597 PM-first late-`pm-proxy`
lower-marker image.  The handoff/rollback path is clean: the V1597 image boots,
evidence is collected from `/cache/native-init-wifi-test-boot-v1597.*`, rollback
from native restores v724, and post-rollback selftest remains `fail=0`.

Strict Wi-Fi progress remains blocked as
`v1599-test-boot-no-downstream-wifi-progress-blocked`.  The V1238/V1303-inspired
late route still does not reach PM-service-owned `/dev/subsys_esoc0`:

- `modem_trigger=True`, but `provider_trigger=False`.
- No RC1/LTSSM, MHI, WLFW, BDF, FW-ready, or `wlan0` marker is present.
- Helper mode is `guarded-pm-proxy-contract-pm-first-late-per-proxy-lower-marker`.
- Order is `pm_proxy_helper,per_mgr,cnss_daemon,mdm_helper,pm_proxy_late` after
  service managers; Wi-Fi HAL/`wificond` and the direct scoped
  `/dev/subsys_esoc0` trigger are disabled.
- `pm_proxy_helper_subsys_modem_initial_count=0`, but lower-marker sampling later
  sees `pm_proxy_helper_subsys_modem_fd_max=1`.
- `per_mgr` exits `0` before it is observable; `pm-proxy` exits `1`;
  `pm_full_contract_seen=0`.
- `mdm_helper` holds `/dev/esoc-0`; `cnss-daemon` reaches cld80211 netlink only.
- Helper result is `pm-service-owned-powerup-missing` with reason
  `pm-first-late-per-proxy-route-did-not-reach-dev-subsys-esoc0-mdm-subsys-powerup`.

New interpretation: route ordering alone is not enough.  The next likely race is
that `per_mgr` starts before `pm_proxy_helper` has actually obtained
`/dev/subsys_modem`; the fixed 300 ms post-PPH settle window records count `0`,
while the later lower-marker window records count `1`.  Starting `per_mgr` too
early can explain why it exits before PM full contract and before `pm-proxy`
can drive PM-service-owned `/dev/subsys_esoc0`.

Next work: V1600 should be source/build-only and add a bounded
`pm_proxy_helper` fd gate before spawning `per_mgr`: poll for
`/dev/subsys_modem` on `pm_proxy_helper` with a short timeout, record first-seen
time/sample count, and only then continue `per_mgr`, CNSS/`mdm_helper`, and late
`pm-proxy`.  If the gate times out, classify as `pm-proxy-helper-modem-fd-missing`
instead of racing into `per_mgr`.  Still no credentials, scan/connect,
DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC
notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or unbounded
boot-image/partition writes.  Report:
`docs/reports/NATIVE_INIT_V1599_PM_FIRST_LATE_PER_PROXY_LOWER_MARKER_HANDOFF_2026-06-02.md`.

## Latest native Wi-Fi state: V1600/V1601 (2026-06-02)

V1600 implements the V1599-selected source/build route.  Helper
`a90_android_execns_probe` is bumped to v297 and adds a bounded
`--allow-android-wifi-service-window-pph-modem-fd-gate`.  The V1600 image keeps
V1591 firmware mount parity, private devnodes, and the helper private vendor
namespace, but waits for `pm_proxy_helper` to hold `/dev/subsys_modem` before
spawning `per_mgr`:

`servicemanager,hwservicemanager,vndservicemanager,pm_proxy_helper,pph-modem-fd-gate,per_mgr,cnss_daemon,mdm_helper,pm_proxy_late,pm-first-late-per-proxy-pph-gate-lower-marker-no-direct-trigger-no-wifi-hal`

If the PPH fd gate times out, the helper classifies the run as
`pm-proxy-helper-modem-fd-missing` before starting `per_mgr`.  If the gate
passes, the route continues to the same PM-service-owned powerup classifier used
by V1599.  Wi-Fi HAL/`wificond`, direct scoped `/dev/subsys_esoc0`, credentials,
scan/connect, DHCP/routes, and external ping remain disabled.

V1600 source build passes as
`v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot-source-build-pass`:

- boot image:
  `tmp/wifi/v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot/boot_linux_v1600_wifi_test.img`
- boot sha256:
  `be60778022ce772194ad156eeecf4c3cffe81c4e25514559a4c3d2fb6a627504`
- init: `A90 Linux init 0.9.105 (v1600-pm-first-late-per-proxy-pph-gate-lower-marker)`
- helper marker: `a90_android_execns_probe v297`
- helper sha256:
  `230e502bbe8ee87e7dd9d53b587a35346b3a241d368922472caccf6ca2ff43dc`

V1601 artifact sanity passes as
`v1601-pm-first-late-per-proxy-pph-gate-lower-marker-artifact-sanity-pass`.  It
verifies static init/helper binaries, boot/header/kernel parity, ramdisk
entries, PPH-gated route strings, service-window PM proxy contract, firmware
mounts, helper v297, lower-marker strings, private file modes, and forbidden
credential-like byte absence.

Next work: V1602 rollbackable live handoff of only the V1600 image, collect
log/summary/helper result/dmesg/`wlan0`, then roll back to v724 and verify
selftest `fail=0`.  The key live discriminator is whether
`pph_modem_fd_gate_seen=1`; if not, the route is blocked before `per_mgr`.  If
yes but PM-service-owned powerup is still missing, the next blocker is
`per_mgr`/`pm-proxy` contract after a proven PPH modem fd.  Still no
credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct
writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind,
or unbounded boot-image/partition writes.  Reports:
`docs/reports/NATIVE_INIT_V1600_PM_FIRST_LATE_PER_PROXY_PPH_GATE_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1601_PM_FIRST_LATE_PER_PROXY_PPH_GATE_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md`.

## Latest native Wi-Fi state: V1602 (2026-06-02)

V1602 adds `scripts/revalidation/native_wifi_test_boot_handoff_v1602.py` and
runs the rollbackable live handoff for the V1600 PPH-gated image.  The
handoff/rollback path is clean: the V1600 image boots, evidence is collected
from `/cache/native-init-wifi-test-boot-v1600.*`, rollback from native restores
v724, and post-rollback selftest remains `fail=0`.

Strict Wi-Fi progress remains blocked as
`v1602-test-boot-no-downstream-wifi-progress-blocked`.  The new PPH fd gate
works, but PM-service-owned `/dev/subsys_esoc0` still does not occur:

- `pph_modem_fd_gate=1`, `pph_modem_fd_gate_seen=1`.
- `pph_modem_fd_gate_first_seen_ms=301`, `pph_modem_fd_gate_samples=7`, final
  count is `1`.
- After the proven PPH gate, `per_mgr` still exits `0` before observation;
  `per_mgr_subsys_modem_initial_count=-1` and final
  `per_mgr_subsys_modem_fd_count=-1`.
- `pm-proxy` starts but exits `1`; `pm_full_contract_seen=0`.
- `mdm_helper` holds `/dev/esoc-0`; `cnss-daemon` reaches cld80211 netlink only.
- `modem_trigger=True`, `provider_trigger=False`; no RC1/LTSSM, MHI, WLFW, BDF,
  FW-ready, or `wlan0` marker is present.
- Helper result is `pm-service-owned-powerup-missing` with reason
  `pm-first-late-per-proxy-route-did-not-reach-dev-subsys-esoc0-mdm-subsys-powerup`.

New interpretation: the PPH race hypothesis is closed.  The blocker is now
`per_mgr`/`pm-service` startup itself after a proven `pm_proxy_helper`
`/dev/subsys_modem` fd.  `per_mgr` exits cleanly before it can hold
`/dev/subsys_modem`; therefore RC1/PERST/refclk, MHI, WLFW, BDF, and `wlan0`
remain downstream and should not be expanded yet.

Next work: V1603 should be host/source-only first and classify why
`/vendor/bin/pm-service` exits `0` immediately in the native service-window:
collect or add focused `per_mgr` startup diagnostics around argv/env, working
directory, required socket/property/service-manager dependencies, stdout/stderr,
exit timing, and early fd/open attempts.  Do not proceed to credentials,
scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind
eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or unbounded
boot-image/partition writes.  Report:
`docs/reports/NATIVE_INIT_V1602_PM_FIRST_LATE_PER_PROXY_PPH_GATE_LOWER_MARKER_HANDOFF_2026-06-02.md`.

## Latest native Wi-Fi state: V1603 (2026-06-02)

V1603 adds
`scripts/revalidation/native_wifi_pm_service_exit_classifier_v1603.py` and
performs the host-only classification requested by the V1602 handoff.  It
passes as `v1603-pph-gate-passed-per-mgr-exit-before-contract`.

The classification fixes the current boundary:

- V1602 handoff evidence is present and rollback-safe.
- The PPH fd gate is closed: `pph_modem_fd_gate_seen=1`,
  first seen at `301ms`, final count `1`, and
  `pm_proxy_helper_subsys_modem_fd_count=1`.
- `/vendor/bin/pm-service` still exits `0` before it is observable in the
  sampling window; it never holds `/dev/subsys_modem`.
- `pm-proxy` exits `1`.
- `pm_full_contract_seen=0`, `subsys_esoc0_open_attempted=0`, and
  `mdm_subsys_powerup` is absent.
- RC1, MHI, WLFW, BDF, FW-ready, and `wlan0` remain downstream and absent.

Interpretation: the blocker is not the PPH race and not currently
RC1/PERST/refclk or firmware/MHI/WLFW.  The immediate missing contract is
`per_mgr`/`pm-service` startup survival after a proven `pm_proxy_helper`
`/dev/subsys_modem` fd.  V1604 should be source/build-only and add a tight
`per_mgr` startup sampler: 10-20ms cadence from spawn until exit or one second,
record first observable time, exit time, exit code, signal, cwd, cmdline, wchan,
fd links, `/dev/subsys_modem`, `/dev/vndbinder`, `/dev/hwbinder`, binder/socket
surface, and stderr/stdout diagnostics.  The existing PPH gate and all
scan/connect/credential/DHCP/external-ping guardrails remain required.

Report:
`docs/reports/NATIVE_INIT_V1603_PM_SERVICE_EXIT_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1604/V1605 (2026-06-02)

V1604 adds the source/build-only next gate selected by V1603.  The helper is
bumped to `a90_android_execns_probe v298` and the V1600 route is preserved with
one added diagnostic flag:
`--allow-android-wifi-service-window-per-mgr-startup-trace`.

V1604 source build passes as
`v1604-per-mgr-startup-trace-test-boot-source-build-pass`:

- boot image:
  `tmp/wifi/v1604-per-mgr-startup-trace-test-boot/boot_linux_v1604_wifi_test.img`
- boot sha256:
  `eb8d1dc11656a8380180b96239d9fe9c8ba160f55f1ca3ff34a8552a6438cca8`
- init: `A90 Linux init 0.9.106 (v1604-per-mgr-startup-trace)`
- helper marker: `a90_android_execns_probe v298`
- helper sha256:
  `6a56b15650fe5c7785a878e7f86ade8e9c323e33cfb8c049952388022592d898`

The startup trace is bounded and read-only: after the proven PPH modem-fd gate,
it samples `per_mgr` every `20ms` for `1s`, recording liveness, state, cmdline,
cwd, wchan, exit timing, and fd counts for `/dev/subsys_modem`,
`/dev/subsys_esoc0`, binder nodes, sockets, and `/dev/socket`.  It does not
start Wi-Fi HAL/`wificond`, scan/connect, credentials, DHCP/routes, external
ping, direct scoped `/dev/subsys_esoc0`, PMIC/GPIO/GDSC writes, blind eSoC
notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind.

V1605 artifact sanity passes as
`v1605-per-mgr-startup-trace-artifact-sanity-pass`.  It verifies static
init/helper binaries, ramdisk entries, boot/header/kernel parity, route
contract, V1604 startup-trace markers, forbidden credential-like byte absence,
and private modes.

Next work: V1606 rollbackable live handoff of only the V1604 image.  Collect
helper result/startup trace/lower markers/dmesg/`wlan0`, roll back to
`stage3/boot_linux_v724.img`, and verify selftest `fail=0`.  The key result is
whether `per_mgr_startup_trace` catches a very short-lived fd/open/binder
surface before the clean exit.  Reports:
`docs/reports/NATIVE_INIT_V1604_PER_MGR_STARTUP_TRACE_SOURCE_BUILD_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1605_PER_MGR_STARTUP_TRACE_ARTIFACT_SANITY_2026-06-02.md`.

## Latest native Wi-Fi state: V1606/V1607 (2026-06-02)

V1606 runs the rollbackable live handoff for the V1604 per-mgr startup trace
image.  The handoff/rollback path is clean: V1604 boots, evidence is collected,
rollback from native restores v724, and post-rollback selftest remains
`fail=0`.  Strict Wi-Fi progress is still blocked as
`v1606-test-boot-no-downstream-wifi-progress-blocked`.

The lower Wi-Fi state remains unchanged:

- `modem_trigger=True`, `provider_trigger=False`.
- `rc1_progress=False`, `mhi_progress=False`, `wlfw_progress=False`.
- `bdf_progress=False`, `fw_ready_progress=False`, `wlan0_present=False`.
- Helper result remains `pm-service-owned-powerup-missing`.

V1607 classifies the new V1606 startup trace and passes as
`v1607-per-mgr-exits-before-any-contract-fd`.  This is the current blocker:

- PPH fd gate still passes: first seen at `301ms`, final count `1`, and
  `pm_proxy_helper_subsys_modem_fd_count=1`.
- `pm-service` sample count is `51` at `20ms` intervals.
- `pm-service` is alive at `0ms`, last alive at `20ms`, child-done at `21ms`,
  and gone by `41ms`.
- It exits cleanly with `exit_code=0`, `signal=0`.
- Max fd counts are all zero for `/dev/subsys_modem`, `/dev/subsys_esoc0`,
  `/dev/vndbinder`, `/dev/hwbinder`, `/dev/binder`, sockets, and
  `/dev/socket`.
- First sample shows cmdline `/vendor/bin/pm-service`, cwd under the private
  root, and wchan `wait_on_page_bit_killable`; the next sample is already a
  zombie.

Interpretation: `pm-service` is exiting before any PM contract fd, binder
registration, or eSoC trigger surface is opened.  The active blocker is now a
pre-contract startup/branch exit inside `/vendor/bin/pm-service`; retrying
RC1/PERST/refclk, firmware/MHI/WLFW, or Wi-Fi HAL work is downstream and should
remain parked.

Next work: V1608 should be source/build-only and add a bounded pm-service
early-exit cause tracer around only `/vendor/bin/pm-service`, preferably
ptrace/exit or uprobe/openat/exit focused enough to capture the syscall/library
branch that leads to `exit(0)`.  It must not ptrace `mdm_helper`, trigger
eSoC/RC1, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, external ping, write PMIC/GPIO/GDSC, spoof eSoC notify/`BOOT_DONE`,
global PCI rescan, or platform bind/unbind.  Reports:
`docs/reports/NATIVE_INIT_V1606_PER_MGR_STARTUP_TRACE_HANDOFF_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1607_PER_MGR_STARTUP_TRACE_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1608/V1609 (2026-06-02)

V1608 implements the source/build-only next gate selected by V1607.  The helper
is bumped to `a90_android_execns_probe v299` and the V1604 route is preserved:
PM-first late `per_proxy`, PPH modem-fd gate, lower-marker capture, and no
Android Wi-Fi HAL/scan/connect path.  The only added diagnostic is a bounded
`per_mgr`-only early-exit tracer:

- `--capture-mode ptrace-lite`
- `--allow-android-wifi-service-window-per-mgr-early-exit-trace`
- syscall/exit records under `pm_service_trigger_observer.syscall.per_mgr.*`
- child trace summaries under `android_wifi_service_window.child.per_mgr.*`

V1608 source build passes as
`v1608-per-mgr-early-exit-trace-test-boot-source-build-pass`:

- boot image:
  `tmp/wifi/v1608-per-mgr-early-exit-trace-test-boot/boot_linux_v1608_wifi_test.img`
- boot sha256:
  `6eb8f218b2bc7a7cfdd7c2f27cba290643149e0de4631de89574c9ac255cf076`
- init: `A90 Linux init 0.9.107 (v1608-per-mgr-early-exit-trace)`
- helper marker: `a90_android_execns_probe v299`
- helper sha256:
  `c5ecbd41c06943f88c88f32fbdacdcd28d5d46c62fbcceb159de4f269619389b`

V1609 local artifact sanity passes as
`v1609-per-mgr-early-exit-trace-artifact-sanity-pass`.  It verifies static
init/helper binaries, ramdisk entries, helper/init route markers, V1608
ptrace-lite markers, boot/header/kernel parity, forbidden credential-like byte
absence, and private modes.

Interpretation: the active branch is still the V1607 pre-contract
`/vendor/bin/pm-service` early-exit blocker, but the next live artifact is now
ready to capture the selected syscall/exit cause instead of only process
liveness/fd samples.  Lower SDX50M/eSoC/RC1, firmware/MHI/WLFW, and Wi-Fi HAL
work remain downstream until `pm-service` stays alive long enough to open or
register the expected PM surfaces.

Next work: V1610 should be a rollbackable live handoff of only the V1608 image.
Collect helper result, `pm_service_trigger_observer.syscall.per_mgr.*`,
`android_wifi_service_window.child.per_mgr.*`, lower markers, dmesg, and
`wlan0`; then roll back to `stage3/boot_linux_v724.img` and verify selftest
`fail=0`.  Still no `mdm_helper` ptrace, direct scoped `/dev/subsys_esoc0`,
Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI
rescan, or platform bind/unbind.  Reports:
`docs/reports/NATIVE_INIT_V1608_PER_MGR_EARLY_EXIT_TRACE_SOURCE_BUILD_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1609_PER_MGR_EARLY_EXIT_TRACE_ARTIFACT_SANITY_2026-06-02.md`.

## Latest native Wi-Fi state: V1610/V1611 (2026-06-02)

V1610 runs the rollbackable live handoff for the V1608 per-mgr early-exit trace
image.  The handoff itself is safe and complete: V1608 boots, evidence is
collected, rollback from native restores v724, and post-rollback selftest
remains `fail=0`.  Strict Wi-Fi progress is still blocked as
`v1610-test-boot-no-downstream-wifi-progress-blocked`.

V1610 lower-state summary:

- rollback: `from-native`, `ok=True`.
- progress decision: `modem-trigger-no-downstream`.
- `provider_trigger=False`, `rc1_progress=False`, `mhi_progress=False`,
  `wlfw_progress=False`, `bdf_progress=False`, `fw_ready_progress=False`,
  `wlan0_present=False`.
- helper result file was captured, size `529757` bytes.
- PPH modem fd gate remains closed: `pm_proxy_helper_subsys_modem_fd_count=1`.
- `mdm_helper_esoc0_fd_count=1`, but `per_mgr_subsys_modem_fd_count=0`,
  `pm_full_contract_seen=0`, and `subsys_esoc0_open_attempted=0`.

V1611 classifies the new V1610 evidence and passes as
`v1611-ptrace-lite-intrusive-stop-limit-no-exit-cause`.  This is the current
blocker for the `pm-service` branch:

- `per_mgr_early_exit_trace=1`, `child.per_mgr.traced=1`.
- `pm-service` stayed in `ptrace_stop` for the full startup sampler window:
  `last_alive_ms=1000`, `first_gone_ms=-1`, `first_child_done_ms=-1`.
- The tracer recorded only one selected syscall:
  `faccessat('/dev/urandom')`, `ret=0`.
- The tracer hit the syscall stop limit:
  `syscall_stop_count=128`, `syscall_trace_stop_limited=1`,
  `trace_disable_reason=stop-limit`.
- No PM contract fd appeared: max `/dev/subsys_modem` and
  `/dev/subsys_esoc0` counts stayed `0`.

Interpretation: V1608/V1610 ptrace-lite is intrusive for `/vendor/bin/pm-service`.
It did not prove the natural V1607 early-exit cause; it changed the process
behavior by holding the target stopped.  Do not infer lower SDX50M/eSoC/RC1
state from this run.  The useful evidence is that syscall ptrace must be
retired for this branch.

Next work: V1612 should be source/build-only and replace ptrace-lite with
non-stopping evidence for the same pre-contract `pm-service` blocker: stdout/
stderr tails, service-manager/property/socket namespace snapshots, vendor
init/env comparison, and host-only dependency/string analysis.  Still no
`pm-service` syscall ptrace, `mdm_helper` ptrace, direct scoped
`/dev/subsys_esoc0`, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes,
external ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`,
global PCI rescan, or platform bind/unbind.  Reports:
`docs/reports/NATIVE_INIT_V1610_PER_MGR_EARLY_EXIT_TRACE_HANDOFF_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1611_PER_MGR_EARLY_EXIT_TRACE_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1612-V1615 (2026-06-02)

V1612 implements the V1611 branch correction: retire `pm-service`
`ptrace-lite` and keep the same PM-first late `per_proxy` PPH-gated route with
non-stopping context capture.  The helper is bumped to
`a90_android_execns_probe v300`; the added flag is
`--allow-android-wifi-service-window-per-mgr-nonstop-context-trace`.

V1612 source build passes as
`v1612-per-mgr-nonstop-context-test-boot-source-build-pass`:

- boot image:
  `tmp/wifi/v1612-per-mgr-nonstop-context-test-boot/boot_linux_v1612_wifi_test.img`
- boot sha256:
  `0c2d70855faeb841d9622e4dd87df0f4b13b532abc4cf83047f2a988ec73ece8`
- init: `A90 Linux init 0.9.108 (v1612-per-mgr-nonstop-context)`
- helper marker: `a90_android_execns_probe v300`
- helper sha256:
  `f6915085d26e8505d4407c810e4e0cc7729e435cf42c132091d5dd8ca8826373`

V1613 artifact sanity passes as
`v1613-per-mgr-nonstop-context-artifact-sanity-pass`.  V1614 then runs the
rollbackable live handoff for the V1612 image.  The handoff/rollback path is
clean: V1612 boots, evidence is collected, rollback from native restores v724,
and post-rollback selftest remains `fail=0`.  Strict Wi-Fi progress remains
blocked as `v1614-test-boot-no-downstream-wifi-progress-blocked`.

V1615 classifies V1614 evidence and passes as
`v1615-natural-pm-service-exit-after-offline-property-writes`.  This is the
current blocker:

- `pm-service` is not ptraced: `child.per_mgr.traced=0`.
- Natural early exit is reproduced: state `D` at `0ms`, state `Z` at `20ms`,
  reaped/gone by `41ms`, exit code `0`.
- No PM contract fd appears: `/dev/subsys_modem=0`, `/dev/subsys_esoc0=0`,
  `pm_full_contract_seen=0`, `subsys_esoc0_open_attempted=0`.
- Property shim sees exactly three requests:
  `hwservicemanager.ready=true`, `vendor.peripheral.SDX50M.state=OFFLINE`, and
  `vendor.peripheral.modem.state=OFFLINE`.
- Lower Wi-Fi remains absent: no provider trigger, RC1, MHI, WLFW, BDF,
  FW-ready, or `wlan0`.

Interpretation: this branch is no longer an RC1/MHI/WLFW problem.  The active
blocker is the peripheral-manager launch/property contract that makes
`/vendor/bin/pm-service` exit cleanly after publishing SDX50M/modem OFFLINE and
before opening binder or `/dev/subsys_modem`.

Next work: V1616 should be host-only plus source/build-only
`pm-service` dependency/launch-contract classification.  Focus on
`/vendor/bin/pm-service` strings/readelf/needed-libs, Android vendor init
service stanza, user/group/seclabel/capabilities/environment, and Android-good
property values consumed by peripheral manager.  If needed, build a bounded
property-contract variant that exposes initial peripheral properties without
ptrace.  Still no `pm-service` syscall ptrace, `mdm_helper` ptrace, direct
scoped `/dev/subsys_esoc0`, Wi-Fi HAL start, scan/connect, credentials,
DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC
notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind.  Reports:
`docs/reports/NATIVE_INIT_V1612_PER_MGR_NONSTOP_CONTEXT_SOURCE_BUILD_2026-06-02.md`,
`docs/reports/NATIVE_INIT_V1613_PER_MGR_NONSTOP_CONTEXT_ARTIFACT_SANITY_2026-06-02.md`,
`docs/reports/NATIVE_INIT_V1614_PER_MGR_NONSTOP_CONTEXT_HANDOFF_2026-06-02.md`,
and
`docs/reports/NATIVE_INIT_V1615_PER_MGR_NONSTOP_CONTEXT_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1616 (2026-06-02)

V1616 added
`scripts/revalidation/native_wifi_pm_service_launch_contract_classifier_v1616.py`
and passed host-only as
`v1616-pm-service-clean-exit-is-offline-system-info-contract-gap`.

The classifier combines V1614/V1615 runtime evidence with V862 Android init
contract data, V1073 extracted `pm-service` binary metadata, V1081 stripped
binary early-path analysis, and Android-good property evidence.  It fixes the
current blocker more precisely:

- native `pm-service` is not being killed by ptrace or cleanup; it exits
  naturally with code `0`, signal `0`, alive only through `20ms`, gone by
  `41ms`.
- native `pm-service` never reaches persistent IPC or PM ownership:
  `/dev/vndbinder=0`, socket fd `0`, `/dev/subsys_modem=0`,
  `/dev/subsys_esoc0=0`, `pm_full_contract_seen=0`.
- native `pm-service` only publishes
  `hwservicemanager.ready=true`,
  `vendor.peripheral.SDX50M.state=OFFLINE`, and
  `vendor.peripheral.modem.state=OFFLINE`.
- Android-good evidence keeps `vendor.per_mgr` and `vendor.per_proxy`
  `running`, with `vendor.peripheral.SDX50M.state=ONLINE`,
  `vendor.peripheral.modem.state=ONLINE`, and
  `vendor.peripheral.shutdown_critical_list=SDX50M modem `.
- static binary evidence proves `pm-service` has a persistent server path:
  Binder, QMI CSI/CCI, `libmdmdetect`, `libperipheral_client`,
  `get_system_info`, `property_set`, `qmi_csi_register`, and
  `vendor.qcom.PeripheralManager` are present.
- current helper source already models the older init-contract gaps: `ioprio rt
  4`, `per_proxy_helper`, `init.svc.vendor.per_mgr=running`, shutdown-critical
  property allowlist, and OFFLINE property allowlist.

Interpretation: this is not a lower RC1/MHI/WLFW problem in the current route.
`pm-service` is making an OFFLINE-only system-info/peripheral-state decision
before it reaches Binder/QMI server setup.  The active blocker is the
`libmdmdetect`/`get_system_info` input surface around `pm-service` startup.

Next work: V1617 should be source/build-only and non-ptrace.  Add a bounded
`pm-service` system-info surface capture around startup that records exactly
what `libmdmdetect` can see in the private namespace:
`/sys/bus/msm_subsys/devices`, `/sys/bus/esoc/devices`,
`/sys/class/esoc-dev`, `/dev/subsys_*`, `/dev/esoc-*`, `/dev/vndbinder`,
private property root, and service-manager sockets.  Do not reintroduce
`pm-service` syscall ptrace, `mdm_helper` ptrace, direct scoped
`/dev/subsys_esoc0`, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes,
external ping, PMIC/GPIO/GDSC writes, blind eSoC notify/`BOOT_DONE`, global PCI
rescan, or platform bind/unbind.  Report:
`docs/reports/NATIVE_INIT_V1616_PM_SERVICE_LAUNCH_CONTRACT_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1617 (2026-06-02)

V1617 is source/build-only and passes as
`v1617-pm-service-system-info-surface-test-boot-source-build-pass`.  It bumps
`a90_android_execns_probe` to v301 and builds
`A90 Linux init 0.9.109 (v1617-pm-service-system-info-surface)`.

Artifact summary:

- manifest:
  `tmp/wifi/v1617-pm-service-system-info-surface-test-boot/manifest.json`
- boot image:
  `tmp/wifi/v1617-pm-service-system-info-surface-test-boot/boot_linux_v1617_wifi_test.img`
- boot SHA256:
  `7d9b60862a8eab04e0a0fe35b929ace255f0de669412a0cbe6262f6f0495419d`
- init SHA256:
  `1cd6967d597a73e6b99b762f32e67fcaba11436c0b2697c1be10a4626ff209f6`
- helper marker: `a90_android_execns_probe v301`
- helper SHA256:
  `1b870e4244ba2794ee30bc113d6aa421f66dfea55a9c116139978b1b4b9e787e`

Helper delta:

- adds
  `--allow-android-wifi-service-window-per-mgr-system-info-surface`.
- preserves the PM-first late-per-proxy PPH-gated lower-marker route.
- keeps the non-ptrace `per_mgr` startup/context branch.
- captures read-only `pm_service_system_info_surface.*` snapshots before and
  after `per_mgr` startup tracing.

The captured surface is limited to private namespace visibility for
`/sys/bus/msm_subsys/devices`, `/sys/bus/esoc/devices`,
`/sys/class/esoc-dev`, `/dev/subsys_*`, `/dev/esoc-*`, binder nodes, private
property root, and service-manager sockets.  It does not perform
`pm-service` syscall ptrace, `mdm_helper` ptrace, direct scoped
`/dev/subsys_esoc0` actor open, Wi-Fi HAL start, scan/connect, credentials,
DHCP/routes, external ping, PMIC/GPIO/GDSC writes, blind eSoC
notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, flash, reboot, or
partition write.

Next gate: V1618 local artifact sanity over the V1617 manifest, then V1619
rollbackable live handoff if V1618 passes.  Report:
`docs/reports/NATIVE_INIT_V1617_PM_SERVICE_SYSTEM_INFO_SURFACE_SOURCE_BUILD_2026-06-02.md`.

## Latest native Wi-Fi state: V1618 (2026-06-02)

V1618 is local-only artifact sanity and passes as
`v1618-pm-service-system-info-surface-artifact-sanity-pass`.

It verifies the V1617 manifest and boot artifact:

- boot image:
  `tmp/wifi/v1617-pm-service-system-info-surface-test-boot/boot_linux_v1617_wifi_test.img`
- boot SHA256:
  `7d9b60862a8eab04e0a0fe35b929ace255f0de669412a0cbe6262f6f0495419d`
- helper marker: `a90_android_execns_probe v301`
- helper SHA256:
  `1b870e4244ba2794ee30bc113d6aa421f66dfea55a9c116139978b1b4b9e787e`

Checks passed: manifest decision, base boot existence, static init/helper,
ramdisk entries, boot/helper/init markers, route contract, header/kernel parity,
forbidden credential-like byte scan, and private output modes.

V1618 performed no live command, flash, reboot, boot partition write, partition
write, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI
rescan, or platform bind/unbind.

Next gate: V1619 rollbackable live handoff to flash only the V1617 image,
collect `pm_service_system_info_surface.*` evidence, roll back to
`stage3/boot_linux_v724.img`, and verify selftest `fail=0`.  Report:
`docs/reports/NATIVE_INIT_V1618_PM_SERVICE_SYSTEM_INFO_SURFACE_ARTIFACT_SANITY_2026-06-02.md`.

## Latest native Wi-Fi state: V1619/V1620 (2026-06-02)

V1619 rollbackable live handoff flashed the V1617 image, collected
`pm_service_system_info_surface.*` evidence, rolled back from native, and
verified v724/selftest after rollback.  Handoff/rollback pass is `True`, but
strict Wi-Fi progress is `False`; the decision is
`v1619-test-boot-no-downstream-wifi-progress-blocked`.

V1620 host-only classification passes as
`v1620-pm-service-offline-decision-despite-visible-esoc-surface`.

New evidence:

- private namespace has `/dev/subsys_modem`, `/dev/subsys_esoc0`,
  `/dev/esoc-0`, binder nodes, `/dev/socket/property_service`,
  `/sys/bus/msm_subsys`, `/sys/bus/esoc`, and `/sys/class/esoc-dev`.
- system-info snapshot sees `subsys0=modem ONLINE`,
  `subsys9=esoc0 OFFLINING`, and `esoc0=SDX50M PCIe 0305_01.01.00`.
- `/vendor/bin/pm-service` still exits naturally with code `0`, signal `0`,
  before opening binder, sockets, `/dev/subsys_modem`, or
  `/dev/subsys_esoc0`.
- property shim sees only:
  `hwservicemanager.ready=true`,
  `vendor.peripheral.SDX50M.state=OFFLINE`, and
  `vendor.peripheral.modem.state=OFFLINE`.
- `/dev/__properties__` is absent inside the private namespace, even though
  `/mnt/sdext/a90/private-property-v317/v535/dev/__properties__` exists on the
  device.

Branch correction: missing core dev/sysfs nodes are no longer the likely
reason for the `pm-service` OFFLINE-only decision.  The next direct fix is to
make the android service-window mode materialize the existing private property
root, then retest whether `libmdmdetect`/`get_system_info` still chooses the
OFFLINE-only path.

Next gate: V1621 source/build-only property-root materialization repair for
`wifi-companion-android-wifi-service-window-*` modes.  Keep blocked: Wi-Fi HAL
start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC
writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform
bind/unbind, and direct scoped `/dev/subsys_esoc0` actor opens.  Reports:
`docs/reports/NATIVE_INIT_V1619_PM_SERVICE_SYSTEM_INFO_SURFACE_HANDOFF_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1620_PM_SERVICE_SYSTEM_INFO_SURFACE_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1621/V1622 (2026-06-02)

V1621 source/build-only repairs private property-root materialization for
android service-window modes and passes as
`v1621-pm-service-property-root-test-boot-source-build-pass`.

The helper change is minimal: `a90_android_execns_probe` v302 now treats
`wifi-companion-android-wifi-service-window-*` plus
`--allow-android-wifi-service-window` plus `--property-root` as a valid private
property materialization path.  This should make the existing remote directory
`/mnt/sdext/a90/private-property-v317/v535/dev/__properties__` visible as
`/dev/__properties__` inside the helper private namespace.

V1622 local artifact sanity passes as
`v1622-pm-service-property-root-artifact-sanity-pass`.

Artifact summary:

- boot image:
  `tmp/wifi/v1621-pm-service-property-root-test-boot/boot_linux_v1621_wifi_test.img`
- boot SHA256:
  `52a56bc02787f2f72c44fad60aae6d8e4ca619135393798425e9d802f7d1c635`
- init: `A90 Linux init 0.9.110 (v1621-pm-service-property-root)`
- init SHA256:
  `0e951f5839fd450610cad6e6026bd243ab87c178fd9e4c339b7d1f1977afe700`
- helper marker: `a90_android_execns_probe v302`
- helper SHA256:
  `09732d4469d963e3c14ecb50f6f01341e92adfd3370c614d2ce779a71510230c`

V1622 verifies manifest decision, base boot existence, static init/helper,
ramdisk entries, boot/helper/init route markers, route contract,
header/kernel parity, forbidden credential-like byte absence, and private
modes.

Next gate: V1623 rollbackable live handoff.  It should flash only the V1621
image, verify `/dev/__properties__` appears in
`pm_service_system_info_surface.*`, reclassify whether `pm-service` still exits
through the OFFLINE-only path, roll back to `stage3/boot_linux_v724.img`, and
verify selftest `fail=0`.  Reports:
`docs/reports/NATIVE_INIT_V1621_PM_SERVICE_PROPERTY_ROOT_SOURCE_BUILD_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1622_PM_SERVICE_PROPERTY_ROOT_ARTIFACT_SANITY_2026-06-02.md`.

## Latest native Wi-Fi state: V1623/V1624 (2026-06-02)

V1623 rollbackable live handoff flashed the V1621 property-root test image,
collected service-window evidence, rolled back from native, and verified v724
selftest after rollback.  Handoff/rollback passes, but strict Wi-Fi progress
remains absent; the decision is
`v1623-test-boot-no-downstream-wifi-progress-blocked`.

V1624 host-only classification passes as
`v1624-property-root-materialized-shutdown-critical-list-blocked`.

New evidence:

- `/dev/__properties__` is now visible and captured in the private namespace,
  proving the V1621 property-root materialization repair worked.
- `subsys0=modem ONLINE`, `subsys9=esoc0 OFFLINING`, and `esoc0=SDX50M`
  remain visible before `pm-service` startup.
- `pm-service` exits naturally with code `0`, signal `0`, still before opening
  binder, sockets, `/dev/subsys_modem`, or `/dev/subsys_esoc0`.
- property requests now include denied
  `vendor.peripheral.shutdown_critical_list` writes for `SDX50M ` and
  `SDX50M modem `, while OFFLINE state writes are allowed.
- no downstream RC1, MHI, WLFW, BDF, FW-ready, or `wlan0` progress appears.

Branch correction: missing `/dev/__properties__` is no longer the immediate
blocker.  The next direct fix is to enable the already-supported
`vendor.peripheral.shutdown_critical_list` values for android service-window
mode only, then rebuild and retest whether `pm-service` advances to IPC or PM
fd ownership.

Next gate: V1625 source/build-only property-shim allowlist repair for
`wifi-companion-android-wifi-service-window-*` modes.  Keep blocked: Wi-Fi HAL
start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC
writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform
bind/unbind, and direct scoped `/dev/subsys_esoc0` actor opens.  Reports:
`docs/reports/NATIVE_INIT_V1623_PM_SERVICE_PROPERTY_ROOT_HANDOFF_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1624_PM_SERVICE_PROPERTY_ROOT_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1625/V1626 (2026-06-02)

V1625 source/build-only repairs the property shim allowlist for android
service-window mode and passes as
`v1625-pm-service-shutdown-list-test-boot-source-build-pass`.

The helper change is minimal: `a90_android_execns_probe` v303 now enables the
existing `vendor.peripheral.shutdown_critical_list` allowlist for
`wifi-companion-android-wifi-service-window-*` modes when
`--allow-android-wifi-service-window` is set.  The accepted values remain
`SDX50M ` and `SDX50M modem ` only.

V1626 local artifact sanity passes as
`v1626-pm-service-shutdown-list-artifact-sanity-pass`.

Artifact summary:

- boot image:
  `tmp/wifi/v1625-pm-service-shutdown-list-test-boot/boot_linux_v1625_wifi_test.img`
- boot SHA256:
  `8a9370fe4ed60f30eed044bd7b6d79d428106033856934b7d27c9e102939757b`
- init: `A90 Linux init 0.9.111 (v1625-pm-service-shutdown-list)`
- init SHA256:
  `f20fb78c5e0891b593cc2f22e828c99ed380282b4a02f4725b24f2fbefd93642`
- helper marker: `a90_android_execns_probe v303`
- helper SHA256:
  `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`

V1626 verifies manifest decision, base boot existence, static init/helper,
ramdisk entries, boot/helper/init route markers, route contract,
header/kernel parity, forbidden credential-like byte absence, and private
modes.

Next gate: V1627 rollbackable live handoff.  It should flash only the V1625
image, verify `vendor.peripheral.shutdown_critical_list` requests are accepted
by the property shim, reclassify whether `pm-service` advances to IPC or PM fd
ownership, roll back to `stage3/boot_linux_v724.img`, and verify selftest
`fail=0`.  Reports:
`docs/reports/NATIVE_INIT_V1625_PM_SERVICE_SHUTDOWN_LIST_SOURCE_BUILD_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1626_PM_SERVICE_SHUTDOWN_LIST_ARTIFACT_SANITY_2026-06-02.md`.

## Latest native Wi-Fi state: V1627/V1628 (2026-06-02)

V1627 rollbackable live handoff flashed the V1625 shutdown-list test image,
collected service-window evidence, rolled back from native, and verified v724
selftest after rollback.  Handoff/rollback passes, but strict Wi-Fi progress
remains absent; the decision is
`v1627-test-boot-no-downstream-wifi-progress-blocked`.

V1628 host-only classification passes as
`v1628-shutdown-list-accepted-pm-service-still-exits-before-ipc`.

New evidence:

- property shim starts with `allow_peripheral_shutdown_list=1`.
- `vendor.peripheral.shutdown_critical_list` writes for `SDX50M ` and
  `SDX50M modem ` are accepted with success results.
- `/dev/__properties__` remains materialized and captured in the private
  namespace.
- `subsys0=modem ONLINE`, `subsys9=esoc0 OFFLINING`, and `esoc0=SDX50M`
  remain the system-info surface visible before `pm-service` startup.
- `pm-service` still exits naturally with code `0`, signal `0`, before opening
  binder, sockets, `/dev/subsys_modem`, or `/dev/subsys_esoc0`.
- no downstream RC1, MHI, WLFW, BDF, FW-ready, or `wlan0` progress appears.

Branch correction: property-root materialization and shutdown-critical-list
allowlisting are now closed as immediate blockers.  The next useful work is not
a lower-layer retry; it is a host-only dependency classifier for the remaining
`pm-service` early-exit branch, using the accepted property sequence, captured
runtime surface, Android-good `vendor.per_mgr` lifecycle, and older V857-V860
property-contract results.

Next gate: V1629 host-only `pm-service` early-exit dependency classifier.  It
should determine whether the next minimal experiment is private read-only
system-info parity modelling, init-property lifecycle modelling, or a different
missing IPC/service-manager surface.  Keep blocked: Wi-Fi HAL start,
scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes,
blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, and
direct scoped `/dev/subsys_esoc0` actor opens.  Reports:
`docs/reports/NATIVE_INIT_V1627_PM_SERVICE_SHUTDOWN_LIST_HANDOFF_2026-06-02.md`
and
`docs/reports/NATIVE_INIT_V1628_PM_SERVICE_SHUTDOWN_LIST_CLASSIFIER_2026-06-02.md`.

## Latest native Wi-Fi state: V1629 causality reconciliation (2026-06-02)

V1629 host-only causality reconciliation passes as
`v1629-pm-service-causality-reconciled-lower-sdx50m-gate`.

This supersedes the V1628 next-gate wording above.  The out-of-band causality
handoff is accepted: `pm-service` taking the OFFLINE system-info branch is an
effect of the real `subsys9=esoc0=OFFLINING` hardware state, not the lower
Wi-Fi blocker.  The fake-ONLINE/system-info branch is rejected because it would
advance an upper layer on false state and then hit the already-proven
`/dev/subsys_esoc0` → `mdm_subsys_powerup` → MDM2AP block.

Fixed points kept by V1629:

- V1496/V1497 fixed the low-level failure as
  `rc1-ltssm-link-failed-no-l0`.
- V1498/V1523 prove TEST:11 reaches the common RC1 enumerate/enable path; the
  core AP-side PCIe enable sequence is not the missing operation.
- V1552 proves AP-side pcie1 GDSC/refclk/pipe/PERST activity while the endpoint
  remains silent: no GPIO104/WAKE, no GPIO142/MDM2AP, no MDM status IRQ, and no
  L0.
- V1621-V1628 repaired property-root and shutdown-critical-list handling, but
  that track does not make the modem boot.

Next gate: V1630 host-only lower-layer classifier/design.  Compare
Android-good and native-fail evidence for AP2MDM, PM8150L GPIO9/PON,
MDM2AP/GPIO142 IRQ, RC1 PHY/LTSSM/L0, MHI, WLFW/BDF/FW-ready, and `wlan0`.
Reject fake ONLINE system-info, pm-service property chasing, blind TEST:11
retry, PMIC/GPIO/GDSC direct writes, eSoC notify/`BOOT_DONE` spoof, Wi-Fi HAL
start, scan/connect, credentials, DHCP/routes, and external ping.  Report:
`docs/reports/NATIVE_INIT_V1629_PM_SERVICE_CAUSALITY_RECONCILIATION_2026-06-02.md`.

## Latest native Wi-Fi state: V1630-V1632 natural-path MDM2AP observation (2026-06-02)

V1630/V1631 prepared and locally verified the fixed natural-path MDM2AP
observation artifact.  The test boot is `A90 Linux init 0.9.112
(v1630-natural-mdm2ap)` with `a90_android_execns_probe v303`; it is scoped to
natural `__subsystem_get(esoc0)` -> `mdm_subsys_powerup` observation only.

V1632 ran the one rollbackable live handoff and rolled back successfully to
`stage3/boot_linux_v724.img`.  Post-rollback verification returned `A90 Linux
init 0.9.68 (v724)` and selftest `fail=0`.

Final corrected V1632 decision:
`v1632-natural-path-observation-incomplete`.

Captured evidence shows the natural provider path ran: esoc0 provider trigger,
provider thread in `sdx50m_toggle_soft_reset`, `fw=esoc0`, GPIO1270/PON low then
high, and GPIO135/AP2MDM set high.  Short-window samples kept GPIO142/MDM2AP low
and mdm status IRQ counts at zero; errfatal also stayed zero in the captured
window.  No forced RC1 `TEST: 11`, LTSSM/RC1, MHI, WLFW, BDF, FW-ready, or
`wlan0` appeared.

Important correction: the initial V1632 wrapper over-classified generic
`GPIO142` / `mdm status` strings as `mdm2ap-responds`.  The classifier is now
strict: `mdm2ap-responds` requires GPIO142 high or a positive IRQ delta.  The
current evidence does not prove a response.

The required V1326-style `mdm2ap_timing.*` IRQ-delta helper output was not
collected because the helper result file was absent and the supervisor timed
out.  Treat V1632 as incomplete evidence, not as `mdm2ap-silent-natural-path`.
Do not auto-run another timing/window variant.  Next work requires explicit
direction: either repair bounded natural-path evidence capture first, or define
a separately approved modem-rail/PMIC gate.

Report:
`docs/reports/NATIVE_INIT_V1632_NATURAL_PATH_MDM2AP_OBSERVATION_HANDOFF_2026-06-02.md`.

## Latest native Wi-Fi state: V1633 MDM2AP IRQ summary capture repair (2026-06-02)

V1633 source/build-only is complete:
`v1633-natural-path-mdm2ap-irq-summary-source-build-pass`.

Purpose: repair the V1632 evidence gap without another live run.  V1632 showed
natural provider/PON/AP2MDM evidence, but helper timeout meant the required
`mdm2ap_timing.*` IRQ-delta block was not written.  V1633 moves that specific
MDM2AP discriminator into PID1's provider window result.

Artifact:
`tmp/wifi/v1633-natural-path-mdm2ap-irq-summary-test-boot/boot_linux_v1633_natural_mdm2ap_irq_summary.img`
with boot SHA256
`cec663be484b15245200e2409cdd863f7976b204e064613295546b8a9a316691`.
Init marker: `A90 Linux init 0.9.113 (v1633-natural-mdm2ap-irq-summary)`.

New behavior: after natural provider detection, PID1 collects initial MDM2AP
GPIO142 and mdm errfatal IRQ counts, then samples `/proc/interrupts` read-only
for 120 samples at 50 ms and appends `mdm2ap_timing.gpio142_irq_delta`,
`mdm2ap_timing.errfatal_irq_delta`, first-delta sample indexes, and safety-zero
markers directly into `/cache/native-init-wifi-test-boot-v1633-natural-window.result`.

No live command or flash was performed for V1633.  Next safe unit is V1634 local
artifact sanity.  A future live handoff should use only the V1633 image, roll
back to v724, verify selftest `fail=0`, and classify with the strict V1632 logic.
Do not proceed to modem-rail/PMIC writes automatically.
