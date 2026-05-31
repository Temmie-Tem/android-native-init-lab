# V1251 PMIC Soft-reset Debugfs Preflight Live

- report: `docs/reports/NATIVE_INIT_V1251_PMIC_SOFT_RESET_DEBUGFS_PREFLIGHT_LIVE_2026-05-31.md`
- live runner: `scripts/revalidation/native_wifi_pmic_soft_reset_debugfs_preflight_live_v1251.py`
- helper: `/cache/bin/a90_android_execns_probe` (`a90_android_execns_probe v260`)
- evidence: `tmp/wifi/v1251-pmic-soft-reset-debugfs-preflight-live/manifest.json`
- result: `v1251-pmic-debugfs-native-reproduction-candidate`
- pass: `true`

## Scope

V1251 temporarily mounted debugfs only because it was absent before the run,
executed the existing fail-closed helper v260 PMIC soft-reset preflight, then
unmounted debugfs and verified postflight selftest. It did not perform a
PMIC/GPIO/debugfs/regulator write, eSoC ioctl, PM actor start, CNSS daemon start,
Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping,
reboot, flash, boot image write, or partition write.

## Findings

| Field | Value |
| --- | --- |
| `mounted_before` | `false` |
| `mounted_by_v1251` | `true` |
| `mounted_during` | `true` |
| `mounted_after` | `false` |
| `cleanup_ok` | `true` |
| Helper SHA/marker/mode | pass |
| Live helper result | `read-only-pass` |
| `debugfs_pinctrl_present` | `1` |
| `debugfs_regulator_present` | `1` |
| PMIC soft-reset line | `pin 7 (gpio9): (MUX UNCLAIMED) c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000:1270` |
| PCIe 1 GDSC line | `pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV` |
| PCIe 0 GDSC line | `pcie_0_gdsc 0 1 0 0mV 0mA 0mV 0mV` |
| `mdm3_state` | `OFFLINING` |
| GPIO142 IRQ count | `0` |
| `read_contract_ready` | `1` |
| `native_reproduction_candidate` | `1` |
| postflight selftest | `fail=0` |

## Interpretation

V1251 confirms that the V1250 `read-only-incomplete` classification was only a
missing debugfs surface. With debugfs temporarily mounted, the helper can read
the same native blocker surface observed in earlier debugfs classifiers:
PM8150L soft-reset GPIO remains mux-unclaimed, PCIe GDSC lines remain at `0mV`,
`mdm3` remains `OFFLINING`, and GPIO142 `mdm status` IRQ count remains `0`.

This is now a valid native reproduction candidate for the Android/native delta:
the read contract is complete and every zero-action marker remained true. The
next step is not a blind `/dev/subsys_esoc0` retry; it is a separate bounded
write-gate design for the minimal PMIC/power-surface repair, with explicit
source/plan review before any live mutation.

## Safety

All zero-action markers passed: `mutation_attempted=0`,
`write_gate_implemented=0`, `write_blocked=1`, `esoc_ioctl_executed=0`,
`pm_actor_executed=0`, `cnss_daemon_start_executed=0`,
`wifi_hal_start_executed=0`, `scan_connect_linkup=0`, `credentials=0`,
`dhcp_routing=0`, and `external_ping=0`.

## Next

V1252 should be source/plan-only first: define the bounded PMIC/power-surface
write gate, exact rollback/cleanup checks, and success/fail classifiers. No
PMIC/GPIO/debugfs/regulator write should be added until that gate is reviewed
and implemented fail-closed.
