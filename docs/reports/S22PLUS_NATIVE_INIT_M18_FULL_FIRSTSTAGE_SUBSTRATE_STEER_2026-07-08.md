# S22+ Native-Init M18 — Full First-Stage Substrate + USB (Operator Steer, 2026-07-08)

Operator (Claude) host-only steer, operator-user chose "one more principled shot
before UART." No device action. This is the last principled blind attempt; if it
loops, the QMP PHY/dwc3 power-sequence wall is confirmed and UART is the path.

## Why M17 failed and why M18 is principled (not another guess)
M17 loaded a hand-picked ~14-module substrate (RPMh regulators + clocks + gdsc)
then the QMP PHY/dwc3 → bootloop. From the DTS, the QMP USB PHY's
`vdda_usb-0p9` rail resolves to a **PMIC LDO (alias L5B)**, and M17 loaded **no
SPMI/PMIC regulator path**, so the PHY's actual supply provider was absent. The
vendor **first-stage `modules.load` (140)** DOES contain that path
(`qcom-spmi-pmic`@78, `spmi-pmic-arb`@79, `regmap-spmi`@100, `pmic_class`@119,
`s2dos05/s2mpb02` regulators) plus the full clock/regulator/RPMh/geni substrate,
in the vendor's own order. So M18 = the complete Android first-stage power/clock
environment, not a hand-picked subset — this directly closes the M17 gap.

## M18 recipe (host-only build)
Freestanding init (proven), mount `/proc`+`/sys`+`/dev`+`/config`, then insmod:

1. **The vendor first-stage `modules.load` (140) in its own order, EXCLUDING
   only the reset/anomaly modules** a bare init cannot service:
   - watchdogs: `gh_virt_wdt`, `qcom_wdt_core`
   - Samsung debug/anomaly (can force reset/upload on conditions): `sec_debug`,
     `sec_debug_region`, `abc`, `minidump`
   - (optional, harmless logging — keep unless it perturbs: `sec_boot_stat`,
     `sec_log_buf`, `sec_arm64_ap_context`)
2. **Then the USB second-stage tail** (not in first-stage), in `modules.softdep`
   order: `phy-msm-snps-hs`, `phy-msm-snps-eusb2`, `phy-msm-ssusb-qmp`,
   `dwc3-msm`, `usb_f_ss_acm`, `i2c-msm-geni`, `mfd_max77705`, `pdic_max77705`,
   `usb_typec_manager`, `if_cb_manager`, `pdic_notifier_module`, `vbus_notifier`.
   (`phy-generic` is already in first-stage.)
3. Bind the configfs gadget to **`a600000.dwc3` only**, force
   `/sys/class/usb_role/*/role=device`, then **PARK** (no reboot beacon).

~141 modules total. All `.ko` are present in the vendor_boot ramdisk we hold.
Honor `modules.softdep` (`dwc3_msm pre: phys+eud`); load order = first-stage
order then the USB tail.

## Decision gate (this is the fork)
- **Parks** ⇒ the fault was the incomplete power substrate; the full first-stage
  brings the PHY up. Proceed: check ACM; if none, the max77705 role chain +
  role-force are already included, so add EUD or narrow role next. Path open,
  continue host-only.
- **Still loops** ⇒ the QMP PHY/dwc3 faults even with Android's complete
  first-stage power environment. That confirms the wall is a runtime
  power/clock/GDSC/RPMh-vote sequence that driver-loading alone doesn't
  reproduce, and it is not diagnosable blind (the kernel prints the exact abort —
  GDSC/clk/regulator name — to the console; pstore is disabled here). **Stop
  blind module permutation and move to UART**: the culprit is already localized
  to the USB QMP PHY/dwc3 block, so UART turns "guess-flash-repeat" into "read
  the abort, fix it" in one boot.

## Discipline
Host-only build + dry-run; any live flash needs a fresh SHA-pinned boot-only
`AGENTS.md` exception + attended ack + manual-download rollback. No forbidden
partitions. Device is on the known-good Magisk baseline. This is the agreed last
principled blind attempt before UART.
