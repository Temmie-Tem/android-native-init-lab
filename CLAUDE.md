# CLAUDE.md

This is the active agent guide for this repository. Keep it short and current.
For full history, read `docs/reports/`, `docs/overview/PROJECT_STATUS.md`, and
`docs/archive/legacy/guides/CLAUDE_LEGACY_WIFI_RESEARCH_LOG_2026-06-07.md`.

## Current Project State

- Device: Samsung Galaxy A90 5G `SM-A908N`, build `A908NKSU5EWA3`.
- Kernel: Samsung stock Android Linux `4.14.190`.
- Runtime goal: custom static `/init` as PID 1 on the stock Android kernel.
- Current verified boot/init baseline: `A90 Linux init 0.9.246 (v726-wifi-lifecycle)`.
- Current boot image: `workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img`.
- Previous verified transport baseline: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`.
- Known-good fallback: `workspace/private/inputs/boot_images/boot_linux_v48.img`.
- Current Wi-Fi status: native `wlan0` is proven to come up and bounded scan/connect/DHCP/ping evidence exists; baseline hardening and repeatability remain the active work.
- Next promoted baseline should use the next global run/build identity, e.g. `V2169`, native init `0.9.247`, build tag `v2169-wifi-lifecycle-baseline`.

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
| Structured run evidence | `tmp/wifi/runs/`, `tmp/logs/` |

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
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v724.py
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v725_fasttransport.py
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v726_wifi_lifecycle.py
```

Flash only through the checked flash helper:

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img --from-native
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
