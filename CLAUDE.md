# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Samsung Galaxy A90 5G (SM-A908N) — stock Android Linux kernel 4.14.190, custom static `/init` as PID 1, building a minimal embedded Linux console without Android userspace. Device flashed via TWRP, controlled over USB CDC ACM serial bridge.

- **Device**: SM-A908N, Android 12, Magisk 30.7, TWRP available
- **Current native build**: `A90 Linux init 0.9.68 (v724)` — `stage3/boot_linux_v724.img`
- **Known-good fallback**: `stage3/boot_linux_v48.img`
- **Active research cycle**: V1336 pre-CNSS provider order classifier PASS → V1337 Android-order pre-CNSS provider observe-only gate — Android reaches `wlfw_start` before captured `__subsystem_get(esoc0)`, while native starts `cnss_daemon` before the eSoC gate yet records no WLFW/BDF/MHI/ks/`wlan0`. V1336 ranked the missing input as Android's pre-CNSS PM/provider chain: `pm_proxy_helper`, QRTR/RFS/pd-mapper companions, `per_mgr`, `per_proxy`, and `cnss_diag` before `cnss-daemon`. Preserve hard exclusions: no PMIC write, userspace GPIO line request/hold, direct eSoC ioctl, direct GDSC write, blind eSoC notify/BOOT_DONE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash outside approved Android handoff/rollback, boot image write outside approved rollback, or partition write.
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
