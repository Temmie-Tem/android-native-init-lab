# Native Init V1484 Auto-readiness Helper Source/build

## Summary

- Cycle: `V1484`
- Type: source/build-only helper support
- Decision: `v1484-auto-readiness-helper-build-pass`
- Result: PASS
- Helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- Helper binary: `stage3/linux_init/helpers/a90_android_execns_probe_v287`
- Helper marker: `a90_android_execns_probe v287`
- Helper SHA256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`

## Change

V1484 adds a compact readiness summary flag:

```text
--pm-observer-auto-readiness-summary
```

The flag is intentionally summary-only. It does not introduce a new child
start path, HAL action, scan/connect action, credential handling, network route,
eSoC notify, GPIO write, PMIC write, PCI rescan, or platform bind/unbind.

It currently derives `auto_readiness.*` from the existing bounded
`mdm2ap_timing` sampler used by the current Wi-Fi test route. The flag requires
`--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler`, so it cannot
run without the existing bounded observation window.

## Output Contract

The helper now emits:

```text
auto_readiness.begin=1
auto_readiness.mode=current-route-boot-readiness
auto_readiness.sample_interval_ms=...
auto_readiness.sample_count=...
auto_readiness.cnss_daemon_started=0|1
auto_readiness.cnss_diag_started=0|1
auto_readiness.wlfw_start_seen=0|1
auto_readiness.wlfw_service_request_seen=0|1
auto_readiness.icnss_qmi_seen=0|1
auto_readiness.bdf_seen=0|1
auto_readiness.fw_ready_seen=0|1
auto_readiness.wlan0_seen=0|1
auto_readiness.primary_checkpoint=...
auto_readiness.gpio142_irq_delta=...
auto_readiness.pcie_rc1_transition_seen=0|1
auto_readiness.pcie_current_link_state_last=...
auto_readiness.pcie_link_state_last=...
auto_readiness.pcie_runtime_status_last=...
auto_readiness.pcie1_gdsc_last=...
auto_readiness.pcie1_pipe_clk_last=...
auto_readiness.mhi_bus_max=...
auto_readiness.mhi_pipe_seen=0|1
auto_readiness.mhi_pipe_fd_max=...
auto_readiness.ks_process_max=...
auto_readiness.safety_wifi_hal_start=0
auto_readiness.safety_scan_connect=0
auto_readiness.safety_credentials=0
auto_readiness.safety_dhcp_route=0
auto_readiness.safety_external_ping=0
auto_readiness.safety_pmic_write=0
auto_readiness.safety_gpio_request=0
auto_readiness.safety_direct_esoc_ioctl=0
auto_readiness.end=1
```

`auto_readiness.primary_checkpoint` reuses the existing CNSS/WLFW checkpoint
classifier:

- `cnss-not-started`
- `cnss-netlink-only`
- `wlfw-start-no-qmi`
- `qmi-no-bdf`
- `bdf-no-fw-ready`
- `fw-ready-no-wlan0`
- `wlan0-present`

## Verification

Executed:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh \
  stage3/linux_init/helpers/a90_android_execns_probe_v287
file stage3/linux_init/helpers/a90_android_execns_probe_v287
sha256sum stage3/linux_init/helpers/a90_android_execns_probe_v287
readelf -d stage3/linux_init/helpers/a90_android_execns_probe_v287
strings stage3/linux_init/helpers/a90_android_execns_probe_v287 | rg \
  "a90_android_execns_probe v287|auto_readiness|pm-observer-auto-readiness-summary"
```

Observed:

- ELF: `ELF 64-bit LSB executable, ARM aarch64`
- linking: statically linked
- dynamic section: absent
- marker `a90_android_execns_probe v287`: present
- `--pm-observer-auto-readiness-summary`: present
- `auto_readiness.*` strings: present

The compiler emitted existing format-truncation warnings in old
`pm_observer_trigger_mdm_power_on` path code. V1484 did not introduce those
warnings and did not change that path's behavior.

## Safety Scope

V1484 is source/build-only. It performs no device command, no helper deployment,
no flash, no reboot, no Wi-Fi HAL, no scan/connect, no credential use, no
DHCP/routes, no external ping, no PMIC/GPIO/GDSC/eSoC write, no PCI rescan, and
no platform bind/unbind.

## Next

V1485 should add a rollbackable PID1 test-boot wrapper that bundles helper v287
and passes `--pm-observer-auto-readiness-summary` in the automatic boot-time
readiness route. V1485 remains source/build-only; V1486 should perform local
artifact sanity before any V1487 live handoff.

