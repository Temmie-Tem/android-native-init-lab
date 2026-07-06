# S22+ Native-Init M5 USB-ACM Miss — Host-Only Root-Cause Analysis (2026-07-07)

Operator (Claude) host-only analysis, no device action. Explains why the M5
freestanding native-init USB-ACM bring-up flashed and ran (no bootloop, PID1
parked) but produced **no host ACM / no UDC enumeration**, using only artifacts
already in the workspace (vendor_boot ramdisk, Magisk boot-time capture, FYG8
kernel source, the vendor module files) plus one confirmatory web check.

## Verdict

The M5 module recipe was built from a **symbol-level `modules.dep` closure of
the USB *function* modules** (the 26-module "USB-first" bundle). That closure is
structurally incomplete: the drivers that actually power and clock the USB
controller/PHY, drive the PMIC/Type-C role stack, and provide the i2c/geni buses
are **probe-time platform dependencies** (DT/`softdep`), not symbol
dependencies, so they were never pulled in. Without them **`dwc3-msm` cannot
probe** (no regulators/clocks/PHYs) → `/sys/class/udc/a600000.dwc3` is never
created → the gadget can bind nothing → silent no-enumeration. This is a recipe
methodology gap, not a native-init/exec or packaging problem (M4T2/M4T3/M5 all
proved PID1 exec + freestanding runtime work).

## Evidence

### 1. The working gadget target (Magisk boot capture, normal Android)
- `sys.usb.controller` / `ro.boot.usbcontroller` = **`a600000.dwc3`** — the real UDC name.
- `/sys/class/udc/` contains **`a600000.dwc3`** and **`dummy_udc.0`**. Binding the
  gadget to `dummy_udc.0` "succeeds" but never enumerates on a host — the native
  init must **explicitly prefer `a600000.dwc3`**.
- `sys.usb.configfs=1`, `sys.usb.configured=configured` — the working path is a
  configfs gadget (`/config/usb_gadget/g1`), which the M5 init already replicates
  correctly (g1 → configs/b.1/f1 → function). The configfs structure is **not** the bug.

### 2. `dwc3_msm` probe-order dependency (vendor `modules.softdep`)
```
softdep dwc3_msm pre: phy-generic phy-msm-snps-hs phy-msm-snps-eusb2 phy-msm-ssusb-qmp eud  post: ucsi_glink
```
The M5 26-bundle had `phy-msm-ssusb-qmp` and `phy-msm-snps-eusb2` but was **missing
`phy-generic`, `phy-msm-snps-hs`, and `eud`**, and loaded **no `ucsi_glink`**. A
missing required PHY alone is sufficient to fail dwc3 probe.

### 3. Missing platform substrate (Android-loaded vs 26-bundle diff)
~45 role/platform modules Android loads for USB that the bundle omitted, including:
- Power/clock: `clk-rpmh`, `icc-rpmh`, `rpmh-regulator`, `gdsc-regulator`,
  `qti-fixed-regulator`, `stub-regulator`, `s2dos05/s2mpb02-regulator`.
- PMIC bus: `spmi-pmic-arb`, `qcom-spmi-pmic`, `qcom_rpmh`, `pmic_class`.
- i2c/geni buses: `msm-geni-se`, `i2c-msm-geni`, `qcom_i2c_pmic`, `i2c-gpio`.
- Type-C/PD role stack: `pmic_glink`, `altmode-glink`, `ucsi_glink`, `qcom_glink*`.
- PHY/USB-C: `phy-msm-snps-hs`, `phy-generic`, `fsa4480-i2c`, `repeater-i2c-eusb2`,
  `max77705_charger/fuelgauge`.
dwc3/PHY probe needs the regulators+clocks; the PMIC/Type-C role stack needs the
i2c/geni buses; none were present.

### 4. The authoritative fix already exists in-hand
The extracted **vendor_boot ramdisk contains all 441 vendor `.ko`** (every module
above, including `pmic_glink`, `ucsi_glink`, `dwc3-msm`, `phy-msm-snps-hs`,
`i2c-msm-geni`) plus the vendor's own ordered load lists:
- `modules.load` (140) — first-stage substrate (clk/regulator/pmic/i2c).
- **`modules.load.recovery` (446, ordered)** — the minimal set recovery uses to
  bring up USB/adb. Its USB section is the exact ordered recipe we need:
  `msm-geni-se → pmic_glink → altmode-glink → phy-msm-ssusb-qmp → phy-msm-snps-hs
  → phy-msm-snps-eusb2 → dwc3-msm → usb_f_* → usb_f_ss_acm → ucsi_glink →
  i2c-msm-geni → max77705_charger → usb_typec_manager → mfd/pdic_max77705 → …`

### 5. Role (peripheral) mechanism
`dwc3-msm` exports `dwc3_msm_usb_role_switch_set_role` / `dwc_msm_vbus_event` and
uses the kernel **USB role-switch** framework (`dev_attr_orientation`, etc.). Per
Qualcomm/AOSP docs, with `dr_mode=otg` dwc3 **defaults to peripheral** and the UDC
is activated on VBUS session. The `pmic_glink`/`ucsi_glink`/`altmode-glink` +
`max77705` stack (all in `modules.load.recovery`) is what detects cable attach and
drives the role — the same set that makes **recovery-mode adb** work over this
cable. If that PD path does not auto-fire under native init, the fallback is to
force peripheral via the role-switch sysfs (`/sys/class/usb_role/<sw>/role =
device`) or the dwc3 debugfs `mode`.

## Corrected recipe (for the next build unit, "M6")
1. Keep the freestanding raw-syscall PID1 runtime (proven).
2. Mount `/proc`,`/sys`,`/dev`,`/config`(configfs) (M5 already does this).
3. **Replay `modules.load.recovery` order** (all `.ko` sourced from the vendor_boot
   ramdisk we already hold), honoring `modules.softdep` (PHYs+`eud` before
   `dwc3-msm`, `ucsi_glink` after). This is observe-then-replicate done with the
   vendor's own ordered list instead of a hand-derived symbol closure.
4. After the chain, **bind the configfs gadget to `a600000.dwc3` specifically**
   (never `dummy_udc.0`).
5. If no host enumeration, **force peripheral** via `/sys/class/usb_role/*/role` =
   `device` before declaring a miss.
6. Only then park probing `/dev/ttyGS0`.

## Methodology lesson
Symbol-level `modules.dep` closure ≠ probe-time platform closure. For GKI vendor
module bring-up, the authoritative source is the vendor's own **`modules.load` /
`modules.load.recovery` order + `modules.softdep`**, not a dependency walk of the
leaf function modules.

## Discipline
Host-only; no device action, no secrets committed (no serials/keys). The M6 build
remains host-only; any live flash still needs a fresh SHA-pinned boot-only
`AGENTS.md` exception + attended operator ack + manual-download rollback.
