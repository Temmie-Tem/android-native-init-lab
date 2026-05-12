# v203 Plan: Wi-Fi Read-Only Baseline Refresh

## Summary

v203 refreshes Wi-Fi evidence before any active bring-up attempt. The work is
host-side and read-only: collect native, mounted-system, and optional manual
Android/TWRP evidence, then produce a clear go/no-go/baseline-required decision.

The starting gate is the post-F055 live result: `wififeas gate` must execute
successfully and currently returns `baseline-required`. v203 does not change the
boot image, PID1, firmware, rfkill state, kernel modules, Android services, or
network exposure.

## Background

- v103/v104/v122 all showed no native `wlan*` interface, no Wi-Fi rfkill node,
  and no WLAN/CNSS/QCA module evidence.
- v202 kernel capability summary allowed a read-only Wi-Fi baseline refresh, not
  active bring-up.
- Android's Wi-Fi stack is service/HAL driven: Wi-Fi services run in System
  Service, communicate with the Wi-Fi HAL, and `wificond` talks to the driver
  through standard `nl80211` commands.
- Android exposes Vendor, Supplicant, and Hostapd Wi-Fi HAL surfaces; the
  Supplicant HAL fronts `wpa_supplicant`.
- Linux firmware lookup is driver/request based and uses firmware search paths
  such as `/lib/firmware/...` plus optional `firmware_class.path`.

References:

- <https://source.android.com/docs/core/connect/wifi-overview>
- <https://source.android.com/docs/core/connect/wifi-hal>
- <https://www.kernel.org/doc/html/v6.15/driver-api/firmware/fw_search_path.html>

## Scope

- Implement `scripts/revalidation/wifi_baseline_refresh.py`.
- Reuse existing safe primitives:
  - `a90ctl.py`
  - `wifi_inventory_collect.py`
  - `kernel_capability_summary.py`
  - private/no-follow evidence helpers from `a90_kernel_tools.py`
- Output under `tmp/wifi/v203-baseline/`:
  - command transcripts
  - `manifest.json`
  - `summary.md`
- Final report target:
  - `docs/reports/NATIVE_INIT_V203_WIFI_BASELINE_REFRESH_2026-05-13.md`

## Non-Goals

- Do not enable Wi-Fi.
- Do not run `rfkill unblock` or write any rfkill state.
- Do not run `ip link set wlan0 up`.
- Do not load or unload modules.
- Do not copy, patch, replace, or relocate firmware.
- Do not start Android Wi-Fi services, supplicant, hostapd, vendor daemons, or
  `svc wifi`.
- Do not expose Wi-Fi, NCM, broker, rshell, or tcpctl beyond the current trusted
  USB-local boundary.
- Do not mutate partitions, SD runtime state, service flags, firewall rules, or
  debug/tracing state.

## Collector Design

`wifi_baseline_refresh.py` is a host-side read-only collector with these
defaults:

```text
--out-dir tmp/wifi/v203-baseline-<UTC>
--bridge-host 127.0.0.1
--bridge-port 54321
--expect-version "A90 Linux init 0.9.59 (v159)"
--mount-system-ro
```

It should capture:

- Preflight:
  - `version`
  - `status`
  - `wififeas gate`
  - `kernel_capability_summary.py` output with `wifi_gate_ok=true`; if the
    default v201/v202 JSON inputs are missing, the collector automatically
    reruns the read-only source collectors into the v203 bundle
- Native Wi-Fi evidence:
  - `wifiinv full`
  - `wifiinv refresh`
  - `wififeas refresh`
  - read-only snapshots of `/sys/class/net`, `/sys/class/rfkill`,
    `/proc/modules`, and relevant kernel config evidence already produced by
    v197/v202 tooling.
- Mounted Android/system evidence:
  - `mountsystem ro`
  - `wifiinv full`
  - `wifiinv refresh`
  - `wififeas full`
  - candidate paths containing `wifi`, `wlan`, `qca`, `cnss`, `wcn`, `bdwlan`,
    `qwlan`, `wlanmdsp`, `wificond`, `supplicant`, or `hostapd`.
- Optional manual evidence slots:
  - Android booted `ip link`
  - Android/TWRP `lsmod`
  - Android/TWRP `dmesg` grep for `wlan|wifi|cnss|qca|wcn|firmware`

The collector must write private files only and must not print tokens or
sensitive runtime paths beyond the existing redaction policy.

## Decision Model

The report should emit one of these decisions:

- `baseline-required`: live gate ran, but native evidence is still incomplete or
  manual Android/TWRP comparison is missing.
- `no-go`: Android-side candidates exist, but kernel-facing gates remain absent
  or contradictory.
- `go-read-only-probe`: native evidence shows a plausible Wi-Fi kernel-facing
  gate, firmware/vendor paths are mapped, and the next step can be a separate
  controlled read-only `nl80211/iw` probe plan.

v203 must not output an active bring-up approval. Even `go-read-only-probe`
means "write a v204 probe plan", not "enable Wi-Fi".

## Validation

```bash
git diff --check

python3 -m py_compile \
  scripts/revalidation/wifi_baseline_refresh.py \
  scripts/revalidation/wifi_inventory_collect.py \
  scripts/revalidation/kernel_capability_summary.py \
  scripts/revalidation/a90_kernel_tools.py \
  scripts/revalidation/a90harness/evidence.py

python3 - <<'PY'
import sys
sys.path.insert(0, "scripts/revalidation")
import wifi_baseline_refresh
wifi_baseline_refresh.validate_no_active_wifi_commands()
print("wifi baseline command guard PASS")
PY

python3 scripts/revalidation/a90ctl.py wififeas gate

python3 scripts/revalidation/wifi_baseline_refresh.py \
  --out-dir tmp/wifi/v203-baseline
```

Static safety checks:

```bash
rg -n "rfkill unblock|ip link set .* up|insmod|rmmod|modprobe|svc wifi|cmd wifi set-wifi-enabled" \
  scripts/revalidation/wifi_baseline_refresh.py docs/reports/NATIVE_INIT_V203_WIFI_BASELINE_REFRESH_2026-05-13.md
```

Allowed matches are only in explicit forbidden-operation documentation or the
collector's forbidden-token guard lists. Terms such as `wpa_supplicant` and
`hostapd` may appear as read-only candidate path patterns, but must not appear
in active start/enable commands.

## Acceptance

- `wififeas gate` is captured live with `rc=0/status=ok`.
- `manifest.json` records source commands, output files, version match, Wi-Fi
  decision, missing gates, and any Android/vendor candidates.
- The run does not mutate Wi-Fi, rfkill, module, firmware, service, firewall,
  debug, storage, or boot state.
- The report clearly states whether v204 should remain blocked, request
  Android/TWRP manual baseline, or write a controlled read-only `nl80211/iw`
  probe plan.
