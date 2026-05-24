# Native Init V718 CNSS2 PD-Notifier Current-Boot Hardening Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_cnss2_pd_notifier_readonly_v706.py`
- final evidence: `tmp/wifi/v718-cnss2-pd-notifier-readonly-hardened-narrow-20260524-104506/`
- latest pointer: `tmp/wifi/latest-v718-cnss2-pd-notifier-readonly-current.txt`
- decision: `v706-service180-absent-current-boot`
- status: `pass`

## Scope Result

The final live run remained read-only:

- `device_mutations=False`
- `daemon_start_executed=False`
- `wifi_hal_start_executed=False`
- `dhcp_or_external_ping_executed=False`

No Wi-Fi HAL, scan/connect, credential use, DHCP, route change, external ping,
sysfs write, `esoc0` open, boot image write, or partition write was executed.

## Harness Fix

The initial V718 replay exposed a classifier hygiene bug: an active native menu
caused all read-only steps to return `[busy]`, but the old runner interpreted
that as a legitimate service `180` absence.

The runner now:

- sends a bounded `hide` before read-only capture;
- records `busy_steps` and essential `failed_steps`;
- blocks interpretation if captures are busy or essential captures are
  incomplete;
- treats optional absent sysfs/proc paths as evidence rather than hard failure;
- avoids counting PMIC power-on and generic PCIe lines as QCA6390 power/MHI
  progress.

## Current-Boot Result

The hardened rerun captured a clean read-only surface:

| item | value |
| --- | --- |
| `busy_steps` | `[]` |
| `failed_steps` | `[]` |
| `firmware_class.path` | `/vendor/firmware_mnt/image` |
| `mss_state` | `OFFLINING` |
| `mdm3_state` | `OFFLINING` |
| `icnss_driver_dir_ok` | `True` |
| `cnss2_driver_dir_ok` | `False` |
| `icnss_device_ok` | `True` |
| `qca6390_device_ok` | `True` |
| `qca6390_runtime_status` | `unsupported` |
| `wlan0_visible` | `False` |
| `qrtr_service69_visible` | `False` |

Focused dmesg marker counts:

| marker | count |
| --- | ---: |
| `service_notifier_180` | `0` |
| `service_notifier_74` | `0` |
| `pd_notifier` | `0` |
| `icnss` | `5` |
| `cnss2` | `0` |
| `qca6390` | `0` |
| `power_on` | `0` |
| `mhi_pcie` | `0` |
| `icnss_qmi` | `0` |
| `wlfw_service` | `0` |
| `bdf` | `0` |
| `fw_ready` | `0` |
| `wlan0` | `0` |

## Interpretation

The user-provided causal chain is still the right model, but this current boot
is not at the service `180/74 -> kernel pd-notifier -> QCA6390 WLFW` decision
point. The hardened classifier shows service `180/74` is absent now and both
`mss` and `mdm3` are `OFFLINING`.

Therefore the next action is not another CNSS retry, Binder repair, Wi-Fi HAL
start, or scan/connect attempt. The next live gate should restore or reproduce
lower modem/WLAN-PD readiness in the same boot, then rerun the read-only
pd-notifier check while service `180/74` is actually present.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss2_pd_notifier_readonly_v706.py

python3 scripts/revalidation/native_wifi_cnss2_pd_notifier_readonly_v706.py \
  --out-dir tmp/wifi/v718-v706-plan-check plan

python3 scripts/revalidation/native_wifi_cnss2_pd_notifier_readonly_v706.py \
  --out-dir tmp/wifi/v718-v706-preflight-check preflight

python3 scripts/revalidation/native_wifi_cnss2_pd_notifier_readonly_v706.py \
  --out-dir tmp/wifi/v718-cnss2-pd-notifier-readonly-hardened-narrow-20260524-104506 \
  --approval '<approved V666/V706 read-only phrase>' \
  run
```

Results:

```text
v706-cnss2-pd-notifier-readonly-plan-ready
v706-cnss2-pd-notifier-readonly-preflight-ready
v706-service180-absent-current-boot
```

## Next Gate

V719 should be lower-readiness focused:

1. reproduce modem/WLAN-PD readiness in the same native boot without `esoc0`;
2. confirm service-notifier `180/74` is present;
3. immediately rerun the hardened V706 read-only check;
4. only if kernel pd-notifier/power/WLFW moves, proceed to wlan0 readiness.
