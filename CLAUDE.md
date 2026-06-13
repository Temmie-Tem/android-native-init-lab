# CLAUDE.md

This is the active agent guide for this repository. Keep it short and current.
For full history, read `docs/reports/`, `docs/overview/PROJECT_STATUS.md`, and
`docs/archive/legacy/guides/CLAUDE_LEGACY_WIFI_RESEARCH_LOG_2026-06-07.md`.

## Current Project State

- Device: Samsung Galaxy A90 5G `SM-A908N`, build `A908NKSU5EWA3`.
- Kernel: Samsung stock Android Linux `4.14.190`.
- Runtime goal: custom static `/init` as PID 1 on the stock Android kernel.
- **Resident validated image (V2317): `A90 Linux init 0.9.281 (v2317-usb-product-rodata)`** — image `workspace/private/inputs/boot_images/boot_linux_v2317_usb_product_rodata.img`, SHA256 `a15558050fc038221420f99577bc18b03851e3ff5280afb61d535ae3ec4d3070`. Carries the full V2313–V2315 USB control surface, V2316 serial redaction/userspace configfs identity, and a product-only fixed-length kernel rodata patch (`SAMSUNG_Android` → `A90 Linux ARM`). Live validation: pinned boot-only flash/readback PASS, `version/status/selftest fail=0`, `usb status control.ok=1`, host descriptor now `iManufacturer=SAMSUNG`, `iProduct=A90 Linux ARM`, `iSerial=A90NATIVE001`, and `usb mass-storage expose`/`remove` smoke passed with NCM+ACM control returning. Manufacturer remains kernel-forced `SAMSUNG`; V2317 intentionally avoids the less-clean manufacturer rodata patch because the standalone `SAMSUNG` literal is merged with another kernel string suffix. **`A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`** (image `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`, SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`) remains the auto-rollback target and deeper fully-Wi-Fi-proven fallback.
- Previous promoted checkpoint: `A90 Linux init 0.9.280 (v2316-usb-linux-identity)` — image `workspace/private/inputs/boot_images/boot_linux_v2316_usb_linux_identity.img`, SHA256 `cf54ff0ae3cca4af31263140e588920296abecdb0ffb690a807b3d8b393f452a`. V2316 redacted the real USB serial to `A90NATIVE001` and proved host-visible `iManufacturer`/`iProduct` are kernel-forced while configfs strings remain userspace-controlled.
- Previous validated test artifact: `A90 Linux init 0.9.279 (v2315-usb-ms-persona)` — closed U3 and layer ① of the USB gadget runtime-control epic. `usb mass-storage expose` creates a bounded read-only 8 MiB `/cache` backing image, links `mass_storage.0` as aux `configs/b.1/f3`, preserves `ncm.usb0` (`f2`) and `acm.usb0` (`f1`) with `control.ok=1`, and enumerates on the host as a read-only USB disk; `usb mass-storage remove` unlinks the aux function, clears the LUN file, removes the host disk, and returns to control-only `control.ok=1`; final `selftest fail=0`.
- Previous WLAN-event artifact: `A90 Linux init 0.9.276 (v2312-e1-connect-event-closure)` — kept V2311's modularized nl80211/rtnetlink event monitors and added `wifi connect-event`, confirming `NL80211_CMD_CONNECT` correlation with carrier up without DHCP/routes/ping.
- Previous promoted artifact: `A90 Linux init 0.9.272 (v2254-wifi-detail-surface)`, image `workspace/private/inputs/boot_images/boot_linux_v2254_wifi_detail_surface.img` — adds read-only Wi-Fi detail surface on top of v2237.
- Known-good fallback: `workspace/private/inputs/boot_images/boot_linux_v48.img`.
- Baseline lineage (since the workspace reorg): `v726-wifi-lifecycle` → `v2169-transport-contract` → `v2174-wifi-urandom-connect` → `v2178-wifi-profile-autoconnect` → `v2182-hud-menu-cleanup` → `v2189-security-p0-stage-fix` → `v2232-service-object-fwclass-bridge` → `v2236-strict-wifi-connect` → `v2237-supplicant-terminate-poll` → `v2254-wifi-detail-surface` → `v2316-usb-linux-identity` → `v2317-usb-product-rodata`.
- Current Wi-Fi status: native `wlan0` connects end-to-end (associate → DHCP → external ping) on both bands, and Wi-Fi is now an on-device native-init command surface (`wifi status` / `wifi scan` / `wifi connect` / `wifi connect-event` / `wifi events` / `wifi netevents` / `wifi dhcp` / `wifi ping` / `wifi cleanup`; see `docs/operations/NATIVE_INIT_WIFI_LIFECYCLE_COMMANDS.md`). V2236 requires `wpa_state=COMPLETED` to reject stale carrier, V2237 replaces the blind post-`TERMINATE` sleep with bounded supplicant exit polling plus SIGKILL escalation, V2254 adds read-only route/default-DNS detail fields to `wifi status` and `screenapp wifi-status`, and V2312 closes the WLAN kernel-interface event epic by correlating nl80211 `CONNECT` with carrier up. Long idle/hold data-path stability remains separate follow-up evidence, not a blocker for the current baseline.
- Next promoted baseline should use the next global run/build identity, bump native init beyond `0.9.281`, and use a `vNNNN-purpose` build tag.
- **Phase status (2026-06-14):** the WLAN kernel-interface event epic is closed at V2312. USB gadget runtime control layer ① is closed at V2315: U1 (`usb status`) at V2313, U2 (`usb mass-storage add/remove`) at V2314, and U3 read-only mass-storage persona end-to-end at V2315. V2316 redacted the real device serial and proved host-visible mfg/product are Samsung-forced in the downstream kernel; V2317 validated the lowest-risk kernel-side product-only rodata patch, changing host `iProduct` to `A90 Linux ARM` while leaving `iManufacturer=SAMSUNG`. The boot-time userspace gadget identity is still written by the prebuilt `a90_usbnet` helper (bundled in the ramdisk from `workspace/private/inputs/external_tools/userland/bin/a90_usbnet-aarch64-static`), so changing `a90_usb_gadget.c`/`a90_usbnet.c` source still requires recompiling that prebuilt for userspace/configfs changes to take effect. Do not start adb-over-ffs layer ② or HID/BadUSB layer ③ without a new explicit goal. Kernel-observation reached exact KASLR slide (V2216 codeword-exact); ROPP full-stack symbolization needs the RKP-protected per-boot key = out of read-only scope. Kernel-security recon is also closed below.
- **Kernel-security recon phase CLOSED (2026-06-13).** Three n-day candidates triaged host-only, zero memory corruption triggered: FastRPC CVE-2024-43047 = vulnerable-in-source but **unreachable** (DSP rpmsg channel down under native init); Binder CVE-2023-20938/-21255 = **not vulnerable** (`is_failure`-keyed cleanup, balanced callers; over-decrement primitive absent); KGSL CVE-2023-33107 = primitive present + source-reachable but **runtime-open-blocked under native init + exploit-dev-gated**. Charter answer: EL1 via non-destructive n-day from this environment = **no**. Lesson confirmed ×3: *fix-marker absence ≠ exploitability*. v2237 remains the rollback target/deeper fallback. See `docs/reports/NATIVE_INIT_KERNEL_SECURITY_RECON_PHASE_CLOSE_CHECKPOINT_2026-06-13.md` (and V2284–V2308). No further kernel-security unit is chartered; reopen only per that report's criteria.

## Read First

- `docs/operations/WORKING_RULES.md` — top-level version/path/commit rules.
- `docs/operations/VERSIONING_POLICY.md` — run ID, init version, build tag, helper version, SHA axes.
- `docs/operations/WORKSPACE_STRUCTURE_AND_BOOTSTRAP.md` — canonical workspace layout and restore steps.
- `docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md` — flash and bridge procedure.
- `docs/operations/CLAUDE_NATIVE_INIT_RUNBOOK.md` — detailed operational runbook.
- `docs/reports/METHODS_TRIED_LEDGER_2026-06-04.md` — do-not-repeat ledger for Wi-Fi work.
- `docs/reports/WLAN_PD_PRODUCER_TRIGGER_DEEP_ANALYSIS_2026-06-04.md` — modem/WLAN-PD analysis boundary.

## Canonical Paths

Use workspace paths. Do not recreate old root payload trees.

| Purpose | Path |
| --- | --- |
| Active native-init source | `workspace/public/src/native-init/` |
| Active revalidation scripts | `workspace/public/src/scripts/revalidation/` |
| Shared Python harness | `workspace/public/src/harness/a90harness/` |
| Public boot tooling source | `workspace/public/src/third_party/mkbootimg/` |
| Historical source provenance | `workspace/public/archive/` |
| Boot image inputs/current rollback images | `workspace/private/inputs/boot_images/` |
| Firmware/vendor extracts | `workspace/private/inputs/firmware/` |
| Toolchains/external tools/kernel source | `workspace/private/inputs/` |
| Generated builds | `workspace/private/builds/` |
| Secrets | `workspace/private/secrets/` |
| Raw logs/device dumps/private archives | `workspace/private/raw-logs/`, `workspace/private/device-dumps/`, `workspace/private/archives/` |
| Structured Wi-Fi run evidence | `workspace/private/runs/wifi/` |
| Other structured run evidence | `tmp/wifi/runs/`, `tmp/logs/` |

Root `scripts/`, `stage3/`, `mkbootimg/`, `firmware/`, `kernel_build/`,
`toolchains/`, `external_tools/`, `backups/`, and `out/` are not active paths.
If an old script or document references them, migrate the active command before
using it for new baseline work.

## Version Rules

Keep these axes separate:

- Run ID: `VNNNN`, for project execution and reports.
- Native init version: `MAJOR.MINOR.PATCH`, visible on device and bumped only when the flashed artifact changes.
- Build tag: `vNNNN-purpose`, embedded in the boot/init baseline.
- Helper version: `helper-vNNN`, for helper binaries only.
- SHA256: final artifact identity.

Never use helper numbers as run IDs or boot image tags. If a new boot image SHA
becomes the rollback/test baseline, promote it under a new run/build identity.

## Common Commands

Start the serial bridge:

```bash
python3 workspace/public/src/scripts/revalidation/serial_tcp_bridge.py --port 54321
```

Query native init through the bridge:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py version
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
python3 workspace/public/src/scripts/revalidation/a90ctl.py 'selftest verbose'
```

Rebuild known boot-image baselines into private outputs:

```bash
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2169_transport_contract.py
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2174_wifi_urandom_connect.py
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2176_wifi_dhcp.py
```

Flash only through the checked flash helper:

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v2174_wifi_urandom_connect.img --from-native
```

Boot image pack/unpack tools live under:

```bash
workspace/public/src/third_party/mkbootimg/
```

## Safety Invariants

- Keep TWRP and at least one known-good boot image available before live work.
- Never write `/efs`, `/sec_efs`, modem partitions, RPMB, keymaster, vbmeta, or bootloader partitions.
- Do not write proprietary firmware/vendor extracts to tracked public paths.
- Do not commit boot images, firmware, ramdisks, compiled binaries, raw logs, credentials, DHCP leases, or unredacted MAC/BSSID/IP traces.
- Use `workspace/private/` for private, large, proprietary, or generated payloads.
- Promote only redacted, small, reproducible, or metadata-only state to `docs/`, `docs/artifacts/`, or `workspace/public/`.
- For Wi-Fi tests, keep credentials in env files under `workspace/private/secrets/`; do not log PSKs.
- Do not run Wi-Fi scan/connect/DHCP/ping unless the current task explicitly asks for that bounded validation.
- Do not revisit external SDX50M/eSoC/PCIe/MHI/GDSC/PMIC/GPIO paths for internal `wlan0` bring-up unless new evidence explicitly reopens them.

## Development Discipline

- Inspect `git status --short` before and after changes.
- Keep patches focused; do not repair unrelated historical docs unless the task is structural cleanup.
- Prefer `rg` for search and `git mv` for tracked moves.
- Use `apply_patch` for targeted edits.
- Validate touched Python with `python3 -m py_compile` where applicable.
- Run `git diff --check` before handoff or commit.
- Do not commit unless the user asks for a commit.
