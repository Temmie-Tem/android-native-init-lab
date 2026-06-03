# Native Init V1878 pcie1 Driver PM Path Selector

## Summary

- Cycle: `V1878`
- Type: host-only pcie1 driver PM path selector
- Decision: `v1878-no-safe-pcie1-driver-pm-userspace-path-host-pass`
- Label: `explicit-resource-gdsc-approval-needed`
- Result: PASS
- Reason: The source exposes targeted pcie1 client enumeration before PCI devices exist, but that path is the already-tested PM_ALL + root-bus scan path. The resume PM-control path requires an existing pci_dev, which the native route does not have. The remaining userspace debugfs surfaces are broad or explicitly forbidden, so a live driver-PM retry is not a new safe gate.
- Evidence: `tmp/wifi/v1878-pcie1-driver-pm-path-selector`

## Checks

| check | value |
|---|---:|
| `v1877_requires_source_selector_before_resource_gate` | `True` |
| `current_prereqs_still_absent` | `True` |
| `pcie1_dtsi_is_client_enumerated` | `True` |
| `only_clean_pre_enumeration_driver_entry_is_enumerate` | `True` |
| `pm_resume_path_requires_existing_pci_dev` | `True` |
| `debugfs_case_surfaces_are_broad_or_forbidden` | `True` |
| `previous_targeted_enumeration_did_not_create_downstream` | `True` |
| `host_only_no_live_mutation` | `True` |

## Evidence Chain

- V1877 selector: Decision: `v1877-clock-debug-surface-closed-pcie-resource-gate-needed-host-pass` / Label: `clock-debug-closed-resource-gdsc-or-driver-pm-next`
- V1877 preferred path: Preferred path: find a legitimate pcie1 driver PM/resource path that can be invoked without global PCI rescan, platform bind/unbind, forced RC1, fake ONLINE state, direct `/dev/subsys_esoc0`, PMIC/GPIO writes, or direct GDSC/regulator writes
- V1877 fallback: Fallback path: if static source cannot identify a safe driver PM path, stop for explicit approval before building any narrowly targeted pcie1 resource/GDSC write gate
- V1876 prereqs: mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- V1876 lower counts: max mdm-status/pci/mhi/ks: `0` / `0` / `0` / `0`
- V1549 targeted enumerate result: Decision: `v1549-low-overhead-confirms-pre-fail-gpio-gdsc-no-l0`
- V1549 trigger/downstream: | trigger mode | sysfs_client_enumerate | / | L0 / downstream | False / False |
- V1354 private-route observer: Decision: `v1354-current-route-pcie1-rc-stayed-off`
- DTS pcie1 node: pcie1: qcom,pcie@1c08000 {
- DTS pcie1 GDSC: gdsc-vdd-supply = <&pcie_1_gdsc>;
- DTS boot option/domain: qcom,boot-option = <0x1>; / linux,pci-domain = <1>;
- Driver enumerate entry: int msm_pcie_enumerate(u32 rc_idx)
- Driver enumerate action: ret = msm_pcie_enable(dev, PM_ALL);
- Driver sysfs enumerate: static DEVICE_ATTR(enumerate, 0200, NULL, msm_pcie_enumerate_store);
- Driver PM control entry: int msm_pcie_pm_control(enum msm_pcie_pm_opt pm_opt, u32 busnr, void *user,
- Driver PM control prerequisite: pr_err("PCIe: endpoint device is NULL\n");
- Driver debugfs broad case: dfile_case = debugfs_create_file("case", 0664,
- Driver keep-resources case: case MSM_PCIE_KEEP_RESOURCES_ON:

## Interpretation

The pcie1 device tree is intentionally client-enumerated (`qcom,boot-option = <0x1>`), so the clean pre-PCI userspace-visible driver entry is the targeted `debug/enumerate` sysfs path. That path calls `msm_pcie_enumerate()`, which enables PM_ALL and starts the PCI root-bus scan. V1549 already used that targeted enumerate path and still reached no L0/downstream with `pcie_1_gdsc` at zero.

`msm_pcie_pm_control()` is not usable as a new pre-enumeration path from native init: it requires an existing endpoint `pci_dev` user object and the current route has no PCI device, MHI bus, WLFW service, or `wlan0`. The remaining debugfs cases include rc selection, case dispatch, PERST mutation, keep-resources flags, and broad enable/enumeration actions, which overlap existing forbidden or already-tested surfaces.

Therefore V1878 does not select a live driver-PM retry. The next write-capable gate crosses the approval boundary: a narrowly targeted pcie1 resource/GDSC preflight must be explicitly approved before build or live use.

## Selected Next Gate

- Cycle: `V1879`
- Label: `pcie1-resource-gdsc-gate-explicit-approval-required`
- Type: `stop-before-build unless explicit approval is given`
- Approval boundary: Any helper or boot image containing a narrowly targeted pcie1 resource/GDSC write gate requires explicit approval before build or live use.
- If approved preflight: source/build-only first with fail-closed compile-time and runtime flags
- If approved preflight: single named pcie1 resource/GDSC target only; no PMIC/GPIO/PERST writes
- If approved preflight: no direct `/dev/subsys_esoc0`, fake ONLINE, eSoC notify, BOOT_DONE, forced RC1, PCI rescan, or platform bind/unbind
- If approved preflight: artifact sanity must reject Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping strings
- If approved preflight: live handoff still stops unless WLFW service 69 and `wlan0` become present
- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.

## Safety Scope

V1878 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC/regulator controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
