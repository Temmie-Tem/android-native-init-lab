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

## Wi-Fi bring-up research state (v598–v749, active)

Goal: bring up `wlan0` from native init without Android userspace.

### Confirmed architecture (SM8250/QCA6390)

- **Driver**: `drivers/net/wireless/cnss2/` (PCIe/MHI path) — NOT icnss (that is SDM845/AHB)
- **cnss2 bootstrap**: probe → `power_on_device()` → `mhi_sync_power_up()` → QCA6390 boots → WLFW service 69 on QRTR → BDF → wlan0
- **WLAN-PD** (`msm/modem/wlan_pd`, instance 180) runs ON modem MPSS DSP — modem must be ONLINE for `wlanmdsp.mbn` to load and WLFW to appear
- **service-notifier 180/74** are side evidence, not cnss2 triggers
- **wlan module**: static (`/sys/module/wlan` exists, not in `/proc/modules`)

### Companion stack (required, confirmed working)

Must run before cnss-daemon: `qrtr-ns → pd-mapper → rmt_storage → tftp_server`
Then: `cnss_diag → cnss-daemon`
Current CNSS-only ordering is confirmed with helper v122. Helper v123 added a
service `180` gated `mdm_helper` mode, but V745 live showed that marker is not
stable enough in every boot. Helper v124 added a `sysmon-qmi` gated
`mdm_helper` mode. V746 proved `mdm_helper` starts safely after `sysmon-qmi`,
but it does not advance mdm3/WLAN-PD/MHI/WLFW.

### Current blocker (V749)

```
mss: OFFLINING → ONLINE ✓  (read-only firmware mounts + subsys_modem holder)
QRTR RX/TX: present ✓
sysmon-qmi: present ✓
service-notifier 180: not stable
mdm_helper after sysmon: starts safely but no lower progress
QCA6390 platform device: exists but driver link missing
mdm3: stays OFFLINING
MHI/QCA6390/WLFW/BDF/wlan0: absent
```

Vendor firmware files (`wlanmdsp.mbn`, `bdwlan.bin`, `regdb.bin`) confirmed at `sda29` (isolated mount), NOT in default native `/vendor`.

V743 proved the service-74 gated `mdm_helper` mode did not start `mdm_helper`
because the gate stayed closed. V744 proved helper v122 still reproduces the
older CNSS-only service publication window. V745 deployed helper v123 and proved
the service `180` gate can stay closed even with QRTR TX and `sysmon-qmi`
present. V746 deployed helper v124 and proved `mdm_helper` can start after
`sysmon-qmi`, but lower markers still do not move. V747 host-only classified
the QCA6390 child driver-link gap as **not a bind/unbind target**. V748
host-only then rejected `mdm_helper` retry, repeated CNSS/HAL start, vendor
namespace repair, and `wlan` module load as next candidates. The selected next
gate is a read-only non-bind ICNSS/CNSS2/QCA trigger capture for the transition
from ICNSS parent readiness to WLFW/BDF/`wlan0`. V749 then classified the
concrete control surfaces: current native has `boot_wlan` and `qcwlanstate=OFF`,
does not expose `fs_ready`, and still has no `/dev/wlan`, wiphy, or `wlan0`.
V508/V513 reject standalone `boot_wlan`/`qcwlanstate`; the next live gate is
therefore lower-window `boot_wlan` observe only.

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
| v747 | host-only QCA6390 driver-binding delta: child unbound confirmed; bind/unbind remains blocked |

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
