# eSoC SDX50M provider — host-side static analysis & finite/infinite verdict (2026-06-01)

**Out-of-band host-only analysis (no vNNN cycle, no device writes).** Supersedes
the working model used through V1337 for the eSoC bring-up blocker. Read this
before continuing the eSoC/Wi-Fi track — it redirects the search.

## TL;DR
The ext-sdx50m eSoC **provider is built into the kernel and is only a thin
GPIO/ioctl handshake** — it does NOT bring up PCIe or MHI and does NOT enable any
modem power rail. The remaining native gap is therefore **FINITE / multi-subsystem,
not an infinite Android re-implementation**. Native already runs the provider
(`mdm_subsys_powerup`, GPIO135/PM8150L-GPIO9 toggled); the modem still never
asserts MDM2AP (GPIO142). The decisive missing prerequisites are below the
provider: **(1) PM8150L GPIO9 PON sequence parity, and (2) PCIe RC1 (`pcie1`)
power/refclk/PERST** for the SDX50M PCIe endpoint. Stop probing the upper eSoC
ioctl / image-transfer / `ks` / MHI layer — that is downstream of MDM2AP.

## How this was established (host-only)
- Parsed kallsyms from the stock kernel in `stage3/boot_linux_v724.img`
  (`bootunpack/kernel` = UNCOMPRESSED_IMG + raw arm64 Image). Clean decode:
  131,833 syms, names end exactly at token_table. Counts: pcie=109 (built-in),
  esoc=20 (core framework), **mhi=0, sdx=0**, and `mdm_subsys_powerup` etc. absent
  from core kallsyms (they are **static** functions in a built-in driver).
- The provider driver strings ARE in the image (file off ~38.06–38.07 MB):
  `mdm_subsys_powerup`, `mdm4x_do_first_power_on`, `sdx50m_toggle_soft_reset`,
  `sdx50m_power_down`, `mdm_wait_for_status_low`, plus the ioctl surface
  `ESOC_REG_REQ_ENG / ESOC_REG_CMD_ENG / ESOC_CMD_EXE / ESOC_WAIT_FOR_REQ /
  ESOC_NOTIFY / ESOC_GET_STATUS` (= `esoc_dev_ioctl`, the exact userspace
  contract the project has been driving).
- Provider vocabulary is **100% GPIO/reset/ioctl**: "Setting AP2MDM_STATUS = 1",
  "Queueing the request: ESOC_REQ_IMG", AP2MDM_SOFT_RESET, MDM_PMIC_PWR_STATUS
  (read), MDM2AP_STATUS, AP2MDM_ERRFATAL. **Zero** PCIe/MHI/GDSC/regulator
  mentions in the esoc driver.
- `/vendor/lib/modules` (local dump) loads only rmnet/rdbg — provider is NOT a
  vendor module; it is built-in. No device .ko pull was needed.

## DTS-confirmed hardware contract (OSRC)
`arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi` + `sm8150-sdx50m.dtsi` +
r3q overlay r03:
- `mdm3: qcom,mdm3` → `compatible = "qcom,ext-sdx50m"`, link-info `0305_01.01.00`,
  sysmon-id 20, ssctl-instance-id 0x10.
- GPIOs: ap2mdm-status = **TLMM 135**, mdm2ap-status = **TLMM 142**,
  ap2mdm-errfatal = TLMM 141, mdm2ap-errfatal = TLMM 53,
  **ap2mdm-soft-reset/PON = PM8150L GPIO9** (1.8V, comment "MDM PON control").
- **No regulator-supply / vdd / vph in the mdm3 node** → the AP's only modem
  power lever is PM8150L GPIO9 (PON). MDM_PMIC_PWR_STATUS is a *status read*, and
  is not even wired (`qcom,mdm-pmic-pwr-status` absent in r3q).
- `mhi_0: qcom,mhi@0` (`sm8150-mhi.dtsi`): `esoc-0 = <&mdm3>`, sits on **`pcie1`
  (`qcom,pcie@1c08000`)** which has `pcie1_sdx50m_wake` → **SDX50M is the PCIe
  endpoint on RC `pcie1`.** `&pil_modem { qcom,poff-depends-on = "esoc0"; }`.

## Why this reframes the blocker
The provider is a separate, thin component from PCIe and MHI (different
nodes/drivers, coupled only by the `esoc-0` phandle). It cannot be the thing that
"brings up Wi-Fi" — it just toggles GPIOs and waits for the modem. So:
- The provider running but MDM2AP staying low (native V1319/V1328) means **the
  modem (SDX50M) is not actually completing power-on/boot**, not that the
  handshake code is missing.
- Because the SDX50M is a **PCIe endpoint**, it needs the **RC side (`pcie1`)
  powered and clocked** (reference clock + PERST deassert) to boot its PCIe PHY
  and assert MDM2AP. Native evidence V1306 shows **`pcie1` GDSC at 0mV** (RC not
  powered). The eSoC provider does NOT power `pcie1`; that is the `msm_pcie`
  driver's job.
- PM8150L GPIO9 (PON) is toggled by native (V1276 GPIO9 high, V1318 GPIO1270
  soft-reset toggle), so the PON line is moving — but timing/hold/level parity
  vs the provider's `reset-time-ms` sequence is unverified.

## Verdict: FINITE (multi-subsystem), not infinite
Crossing the safety line, if chosen, targets a small enumerable set — not an
Android re-implementation:
1. **PM8150L GPIO9 PON** exact assert/hold sequence parity (provider already does
   this; verify native matches level+timing).
2. **`pcie1` (PCIe RC1) power-up** — GDSC/clock/PERST so the SDX50M EP gets its
   reference clock and can boot to MDM2AP. This is the strongest lead (V1306 0mV).
The eSoC ioctl / ESOC_REQ_IMG / `ks` / MHI / WLFW work is all **downstream of
MDM2AP** and should be paused until the modem actually powers on.

## Recommended next steps (read-only first)
- Classify `pcie1` (`qcom,pcie@1c08000`) RC power: GDSC, gcc clocks, PERST gpio,
  refclk, and whether native ever enables it (vs V1306 0mV). DTS power props are
  in `sm8150-pcie.dtsi`.
- Confirm PM8150L GPIO9 PON sequence: provider `sdx50m_toggle_soft_reset` /
  `mdm4x_do_first_power_on` level+`reset-time-ms` vs native's toggle.
- Only then consider a bounded, reboot-safe RC power-enable experiment (still
  below Wi-Fi HAL/scan/connect, DHCP/routes, external ping; no PMIC/GDSC writes
  until the read-only classification justifies a specific bounded action).

## Artifacts
- Verdict: `tmp/wifi/v1331-esoc-disasm/FINITE_VERDICT_FINAL.md`
- Driver strings: `tmp/wifi/v1331-esoc-disasm/esoc_strings.txt`
- kallsyms/disasm tools (committed): `scripts/analysis/esoc_final.py`,
  `find2.py`, `dbg_relbase.py`
- DTS: `kernel_build/.../dts/qcom/{sdx5xm-external-soc.dtsi,sm8150-sdx50m.dtsi,
  sm8150-mhi.dtsi,sm8150-pcie.dtsi}`, r3q overlay r03.
