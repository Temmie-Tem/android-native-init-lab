# Native Init V1325 — GPIO142 / Errfatal / PCIe Timing Observer Plan

- Date: 2026-05-31
- Cycle: `V1325` (project axis; no device flash implied)
- Native build: `A90 Linux init 0.9.68 (v724)` (unchanged)
- Type: source/build design plan for the next bounded observer
- Status: PLAN

## Goal

V1324 classified the current delta as a post-AP2MDM MDM2AP/PCIe response gap:
native reaches AP-side provider activity, but MDM2AP/GPIO142, MDM errfatal,
PCIe RC1/MHI, WLFW/BDF, and `wlan0` remain absent while Android receives them.

V1325 defines the next smallest observer that can answer one question without
jumping to Wi-Fi HAL/connect:

> During the bounded native `pm-service -> /dev/subsys_esoc0 -> mdm_subsys_powerup`
> window, do GPIO142/MDM status, GPIO53/MDM errfatal, PCIe RC1 state, or MHI
> surfaces transition at any point after GPIO135/AP2MDM activity?

## Current Gap

Existing helpers already sample broad response state, but not the exact next
needed timing contract:

| Existing evidence | What it proves | Missing for next decision |
| --- | --- | --- |
| V1318 critical trace | GPIO1270 soft-reset, GPIO135 high, GPIO141 activity, GPIO142 absent | compact per-phase GPIO142/errfatal/PCIe timing summary |
| V1324 classifier | post-AP2MDM MDM2AP/PCIe response gap | next live observer contract |
| helper v275 lower sequence summary | PM-service reaches `mdm_subsys_powerup`; GPIO142/MHI/WLFW stay absent | MDM errfatal IRQ count and first-transition timing fields |
| Android V852/V896 | positive GPIO142/PCIe/MHI/WLFW/`wlan0` path | native transition timing under same bounded path |

## Decision

Do **not** start Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external
ping. Do **not** write PMIC/GPIO/GDSC/eSoC state. The next practical unit should
be source/build-only support for a new compact timing sampler in
`a90_android_execns_probe`.

Recommended sequence:

1. **V1326 source/build support** — add helper `v276` mode
   `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler`.
2. **V1327 deploy-only** — deploy helper `v276` to `/cache/bin/a90_android_execns_probe`.
3. **V1328 bounded live** — run the sampler only with explicit reboot-cleanup
   contract, no Wi-Fi HAL/connect.

## V1326 Helper Contract

Add a new opt-in flag:

```text
--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler
```

Required parent gates:

- Requires `--pm-observer-late-per-proxy-response-sampler`.
- Requires existing late `per_proxy` / `mdm_helper` ordering used by V1313/V1318.
- Must fail closed unless explicit allow flags already required by the PM
  observer path are present.

Sampling behavior:

- Window: 120 samples at 50 ms (6 s), or reuse a named constant so V1328 can
  tune it without code churn.
- Output only compact summary fields, not per-sample bulk output.
- Read-only sources only:
  - `/proc/interrupts` lines for `mdm status` (GPIO142) and `mdm errfatal` (GPIO53)
  - PCIe RC1 sysfs: `current_link_state`, `link_state`, `power/runtime_status`,
    `debug/l23_rdy_poll_timeout` if readable
  - MHI bus/device counts and `/dev/mhi_0305_01.01.00_pipe_10` existence/fd count
  - `ks` process count
  - `wlan0`/WLFW/BDF/kmsg marker counts already used by lower samplers
  - optional debugfs pinctrl/TLMM line snapshots only if already mounted/readable;
    do not mount or write from this helper mode

Required output keys:

```text
mdm2ap_timing.mode=late-per-proxy-mdm2ap-errfatal-pcie-timing
mdm2ap_timing.sample_interval_ms=50
mdm2ap_timing.sample_count=N
mdm2ap_timing.pm_service_powerup_seen=0|1
mdm2ap_timing.gpio142_irq_initial=N
mdm2ap_timing.gpio142_irq_max=N
mdm2ap_timing.gpio142_irq_delta=N
mdm2ap_timing.gpio142_first_delta_sample=N|-1
mdm2ap_timing.errfatal_irq_initial=N
mdm2ap_timing.errfatal_irq_max=N
mdm2ap_timing.errfatal_irq_delta=N
mdm2ap_timing.errfatal_first_delta_sample=N|-1
mdm2ap_timing.pcie_rc1_transition_seen=0|1
mdm2ap_timing.pcie_rc1_first_transition_sample=N|-1
mdm2ap_timing.mhi_bus_max=N
mdm2ap_timing.mhi_pipe_seen=0|1
mdm2ap_timing.ks_process_max=N
mdm2ap_timing.wlfw_kmsg_max=N
mdm2ap_timing.wlan0_seen=0|1
mdm2ap_timing.safety_wifi_hal_start=0
mdm2ap_timing.safety_scan_connect=0
mdm2ap_timing.safety_credentials=0
mdm2ap_timing.safety_dhcp_route=0
mdm2ap_timing.safety_external_ping=0
mdm2ap_timing.safety_pmic_write=0
mdm2ap_timing.safety_gpio_request=0
mdm2ap_timing.safety_direct_esoc_ioctl=0
mdm2ap_timing.end=1
```

## V1328 Live Success / Failure Labels

| Label | Meaning | Next |
| --- | --- | --- |
| `v1328-mdm2ap-pcie-transition-observed` | GPIO142 or PCIe/MHI transitions appear | move toward CNSS/WLFW/BDF validation, still no Wi-Fi connect yet |
| `v1328-mdm2ap-errfatal-transition-observed` | MDM errfatal fires instead of status | classify crash/error path before retrying |
| `v1328-mdm2ap-pcie-silent-reboot-required` | no GPIO142/errfatal/PCIe/MHI transition and cleanup requires reboot | compare Android timing or lower provider prerequisites |
| `v1328-observer-incomplete` | sampler output truncated or missing end marker | reduce output / fix observer before interpreting hardware |

## Safety Contract

V1325 itself is documentation only. For V1326/V1327/V1328:

- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP/routes or external ping.
- No PMIC write.
- No userspace GPIO line request/hold.
- No direct eSoC ioctl/notify/BOOT_DONE from the new sampler.
- No GDSC write.
- No boot image write, flash, or partition write.
- Any future live sampler that can leave a holder in D-state must be explicitly
  reboot-bounded and must record post-reboot `selftest fail=0`.

## Validation For V1325

```bash
git diff --check
run the local secret-scan pattern without hard-coding credentials into docs
```

No device command is required for V1325 because it is a source/build design
plan. Device health may be checked separately as operational sanity, but it is
not part of this plan artifact.
