# Native Init V1877 Power Clock Gate Selector

## Summary

- Cycle: `V1877`
- Type: host-only pcie1 power/clock gate selector
- Decision: `v1877-clock-debug-surface-closed-pcie-resource-gate-needed-host-pass`
- Label: `clock-debug-closed-resource-gdsc-or-driver-pm-next`
- Result: PASS
- Reason: V1876 confirms the current private SDX50M route still stops at a pcie1 power/clock snapshot gap, while V1663-V1673 already closed the bounded clock-debug vote path. The next safe unit must be source/build-only and select a legitimate pcie1 driver PM resource path, or stop for explicit approval before any narrowly targeted resource/GDSC write.
- Evidence: `tmp/wifi/v1877-power-clock-gate-selector`

## Checks

| check | value |
|---|---:|
| `v1876_current_route_confirms_power_clock_gap` | `True` |
| `v1662_establishes_android_native_power_vote_gap` | `True` |
| `v1663_authorized_only_narrow_clock_debug_first` | `True` |
| `v1673_closes_clock_debug_surface` | `True` |
| `v1549_and_v1354_carry_forward_no_l0_gdsc_zero` | `True` |
| `v1252_rejects_broad_power_writes_without_separate_gate` | `True` |
| `host_only_no_live_mutation` | `True` |

## Evidence Chain

- V1876 latest route: Decision: `v1876-lower-input-power-clock-snapshot-gap-rollback-pass`
- V1876 lower contract: contract label: `lower-input-power-clock-snapshot-gap`
- V1876 safety guards: guard read-only/no-esoc0/no-rc/no-pci/no-hal: `True` / `True` / `True` / `True` / `True`
- V1876 lower counts: max mdm-status/pci/mhi/ks: `0` / `0` / `0` / `0`
- V1876 Wi-Fi prereqs: mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- V1662 power diff: Decision: `v1662-android-native-power-diff-power-vote-gap-pass` / Label: `power-vote-gap`
- V1662 pcie1 GDSC gap: | pcie_1_gdsc | 1 | 0 | android index=256 uptime=250.62 |  | 0 | 0 |
- V1662 refgen gap: | gcc_pcie1_phy_refgen_clk | 1 | 0 | 1 | 0 | 100000000 | 19200000 |
- V1663 first gate: Decision: `v1663-pcie1-clock-vote-gate-plan-ready`
- V1663 allowed surface: Allowed writes: targeted `/sys/kernel/debug/clk/<target>/rate` and `/sys/kernel/debug/clk/<target>/enable` only.
- V1673 clock-debug result: Decision: `v1673-clock-vote-surface-failed` / Reason: bounded direct clock write attempts ran, but all enable writes failed (success_count=0, failure_count=10, cleanup_failure_count=0)
- V1673 counts: `success_count`: `0` / `failure_count`: `10`
- V1673 safety: `safety_zero`: `True` / `forbidden_seen`: `False`
- V1549 historical no-L0: Decision: `v1549-low-overhead-confirms-pre-fail-gpio-gdsc-no-l0`
- V1354 private-route power observer: Decision: `v1354-current-route-pcie1-rc-stayed-off`
- V1252 write-gate boundary: no direct PCIe GDSC enable

## Interpretation

V1876 updates the current-route evidence after the private SDX50M mount: PM-service registration and return-path still work, but the lower publication remains absent. The read-only sampler observed the pcie1 GDSC line while mdm-status, PCI, MHI, `ks`, WLFW service 69, and `wlan0` all stayed at zero/absent. That keeps Wi-Fi HAL, scan/connect, DHCP/routes, and ping below the safe gate.

V1662 identified the Android-good versus native pcie1 resource gap, but it explicitly did not authorize a write gate. V1663 then limited the first authorized live proof to targeted clock-debug leaf writes only. V1673 ran that bounded proof, all enable writes failed, safety stayed clean, and the report closed clock-debug as a practical pcie1 power-vote mechanism. Repeating clock-debug timing, readiness, or direct-write variants would not add a new source.

The remaining actionable gap is therefore not a connectivity problem yet. It is a pcie1 lower-resource path problem before MHI/WLFW publication. The next unit must select and build from source first, then either use a legitimate pcie1 driver PM/resource path or stop for explicit approval before any narrowly targeted resource/GDSC write.

## Selected Next Gate

- Cycle: `V1878`
- Label: `pcie1-driver-pm-resource-path-source-selector`
- Type: `source/build-only first; no live mutation`
- Preferred path: find a legitimate pcie1 driver PM/resource path that can be invoked without global PCI rescan, platform bind/unbind, forced RC1, fake ONLINE state, direct `/dev/subsys_esoc0`, PMIC/GPIO writes, or direct GDSC/regulator writes
- Fallback path: if static source cannot identify a safe driver PM path, stop for explicit approval before building any narrowly targeted pcie1 resource/GDSC write gate
- Fail-closed check: source selector must prove the candidate call path and all write surfaces before any boot image change
- Fail-closed check: artifact sanity must reject Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping strings
- Fail-closed check: live handoff remains forbidden until WLFW service 69 and `wlan0` prerequisites are present or a separate lower-resource gate is approved
- Fail-closed check: direct PMIC/GPIO/GDSC writes remain forbidden unless explicitly approved for a narrow, named gate
- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.

## Safety Scope

V1877 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC/regulator controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
