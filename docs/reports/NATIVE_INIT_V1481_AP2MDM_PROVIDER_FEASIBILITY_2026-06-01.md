# Native Init V1481 AP2MDM Provider Feasibility Classifier

## Summary

- Cycle: `V1481`
- Type: host-only classifier over V1480 evidence, Samsung OSRC GPIO source, DTS, and prior custom-kernel boot-incompatibility evidence
- Decision: `v1481-userspace-hold-closed-kernel-provider-not-live-feasible`
- Result: PASS
- Reason: V1480's `/sys/class/gpio` AP2MDM hold failed with `-16` (`EBUSY`) because GPIO135 is already requested by the kernel eSoC provider. A kernel-provider patch would be the direct way to alter this line's behavior, but the local Samsung OSRC custom-kernel boot path is not currently live-feasible because prior V771/V774-class handoffs failed before native init. Direct MMIO/pinctrl/GPIO register writes remain too broad for the current gate.

## Inputs

- V1480 classifier: `docs/reports/NATIVE_INIT_V1480_AP2MDM_HOLD_LIVE_CLASSIFIER_2026-06-01.md`
- Provider analysis: `docs/reports/ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md`
- GPIO sysfs source: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/gpio/gpiolib-sysfs.c`
- GPIO request source: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/gpio/gpiolib.c`
- eSoC DTS: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi`
- PCIe RC1 DTS: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi`
- Custom-kernel incompatibility: `docs/reports/NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_2026-05-25.md`

## V1480 Evidence Reconciled

V1480 reached the AP2MDM hold gate after the provider/AP2MDM set-high trace:

- gate: `trace_set_high=1 debug_gpio135_low=1`
- attempt: `export_rc=-16 exported=0 direction_high_rc=-125`
- cleanup: `release_rc=0 unexport_rc=0 result_rc=-16`
- downstream state: GPIO135/GPIO142 low, pcie1 off, no RC1/MHI/WLFW/BDF/FW-ready/`wlan0`

The failed export is therefore not an ambiguous test-boot bug. It is a kernel
ownership result.

## Source Finding: Why Sysfs Export Returns EBUSY

The GPIO sysfs export path first requests the line:

- `gpiolib-sysfs.c`: `export_store()` calls `gpiod_request(desc, "sysfs")` before `gpiod_export(desc, true)`.
- `gpiolib.c`: `__gpiod_request()` uses `test_and_set_bit(FLAG_REQUESTED, &desc->flags)`. If the line is already requested, it returns `-EBUSY`.

V1480's `export_rc=-16` matches this code path. GPIO135 is already requested by
the board/eSoC provider, so userspace cannot acquire and drive it through the
normal sysfs GPIO interface.

## DTS Finding: GPIO135 Belongs To The eSoC Provider

The staged Samsung OSRC DTS maps the line directly to `mdm3`:

- `qcom,ap2mdm-status-gpio = <&tlmm 135 0x00>`
- `qcom,mdm2ap-status-gpio = <&tlmm 142 0x00>`
- `qcom,ap2mdm-soft-reset-gpio = <&pm8150l_gpios 9 0>`
- active pinctrl: `pinctrl-1 = <&ap2mdm_active &mdm2ap_active>`

That makes the V1480 sysfs result expected: AP2MDM is not an unowned test line.
It is part of the proprietary `ext-sdx50m` provider contract.

## Rejected Next Actions

### Retry userspace GPIO hold

Rejected. V1480 already proves `/sys/class/gpio/export` fails at the request
stage with `EBUSY`. Repeating the same hold cannot drive GPIO135.

### Direct MMIO, pinctrl, or raw GPIO register writes

Rejected. This bypasses kernel GPIO ownership, pinctrl state, IRQ coupling, and
cleanup semantics. It is too broad for a recovery-safe Wi-Fi bring-up gate.

### Patch the eSoC provider in a custom kernel and flash it

Not selected for live work now. It is technically the direct layer for changing
AP2MDM behavior, but the local OSRC custom-kernel route is not boot-compatible
yet. V775 classifies that V773/V774 already had the stock DTB tail and matching
boot header metadata but still failed live boot, leaving Samsung production
transforms/metadata/toolchain deltas unresolved.

### Repeat only corrected RC1 debugfs case 11

Rejected as the primary next gate. Prior RC1 experiments already reached
LTSSM/probe-like progress without L0 while MDM2AP stayed silent. Repeating RC1
without resolving the provider/SDX50M response ambiguity is low value.

## Next Gate

V1482 should be host-only and should not build or flash a new image yet:

`v1482-android-ap2mdm-effective-level-reference-classifier`

Purpose:

1. Reconcile existing Android-positive evidence with V1470-V1480 native evidence.
2. Answer whether Android ever records GPIO135 high during the successful SDX50M/Wi-Fi boot path, or whether debugfs/readback can be low even when the provider has successfully triggered the modem.
3. Decide whether the next test boot should target AP2MDM timing, PCIe RC1 readiness, or another lower prerequisite.

Why this is the right next step:

- A new "Wi-Fi auto-start test boot" is useful only if it targets the correct
  lower gate.
- V1480 closes userspace AP2MDM override.
- V1481 closes kernel-provider patching as not currently live-feasible.
- Existing Android-positive captures may already show whether GPIO135 readback
  is a misleading signal or a real native-only failure.

## Safety Scope

V1481 is host-only. It performs no device command, no helper deployment, no
flash, no reboot, no Wi-Fi HAL, no scan/connect, no credential use, no
DHCP/routes, no external ping, no PMIC/GPIO/GDSC/eSoC write, no PCI rescan, and
no platform bind/unbind.

