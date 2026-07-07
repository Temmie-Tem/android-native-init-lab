# S22+ Native-Init M6 Bootloop — Operator Postmortem + M7 Hypothesis (2026-07-07)

Operator (Claude) host-only postmortem answering the M6 incident report's stop
rule ("do not repeat M6 without a hypothesis stronger than 'replay more
modules'"). No device action.

## Hypothesis (stronger than "replay more modules"): watchdog-induced reset

M5 (26-module USB-function bundle, **no watchdog module**) → PID1 **parked**, no
reboot. M6 (full `modules.load.recovery`, **446 modules**) → **bootloop**. The
behavior changed from park to reset, so the expanded set introduced a
reset-causing driver. The most reset-causing modules in that set are literally
watchdog drivers, loaded near the very front of the recovery order:

```
recovery pos  5: gh_virt_wdt.ko
recovery pos  6: qcom_wdt_core.ko
(also pos 39 gh_virt_wdt, 84 qcom_wdt_core, 213 qcom_soc_wdt, 350 sec_qc_qcom_wdt_core)
```

In recovery mode these load safely because Android's recovery userspace opens
and **pets `/dev/watchdog`**. Our bare freestanding park-init pets nothing → the
hardware/virtual watchdog bites → reset → **fast bootloop**. This cleanly
explains M6's park→loop regression versus M5 and is directly actionable.

Secondary risk in the same 446-set: ~37 non-USB subsystem modules (display
clocks `dispcc-*`, `cfg80211`/WLAN, `thermal_pause`, sensors, crypto, GPU) that
probe into a bare no-Android environment and can `BUG()`/panic. Trimming to the
USB subset removes all of these at once, so the fix is robust even if the first
reset was not the watchdog specifically.

## Root of the over-correction

The prior operator steer (commit `1893babe`) said "replay `modules.load.recovery`
order." That was right about *order and completeness of the USB substrate* but
wrong to imply the **whole** list. `modules.load.recovery` is the entire recovery
boot module set, not a USB-only list. The correct target is the **USB-bring-up
subset, in recovery order, minus unserviceable modules (watchdogs first)**.

## M7 recipe (host-only build)

Load, in `modules.load.recovery` order, ONLY:
- the USB substrate + chain the M6 manifest already located as
  `required_recovery_module_positions` (clk-rpmh@8, gcc-waipio@9, icc-rpmh@10,
  rpmh-regulator@15, gdsc-regulator@33, phy-generic@59, msm-geni-se@132,
  pmic_glink@198, altmode-glink@201, eud@210, phy-msm-ssusb-qmp@259,
  phy-msm-snps-hs@260, phy-msm-snps-eusb2@261, dwc3-msm@262, usb_f_ss_acm@273,
  ucsi_glink@274, i2c-msm-geni@285, usb_typec_manager@379, mfd_max77705@401,
  pdic_max77705@405), plus
- their genuine `modules.dep` transitive dependencies (so nothing they need is
  missing), still ordered by their recovery-list position.

Then apply an explicit **exclude/blocklist** (never insmod under bare init):
- all watchdog modules: `gh_virt_wdt`, `qcom_wdt_core`, `qcom_soc_wdt`,
  `sec_qc_qcom_wdt_core`;
- non-USB subsystems not on the required/dep path: display (`dispcc-*`, `msm_drm`,
  panel), WLAN (`cfg80211`, wlan), thermal, sensors, GPU, camera, audio/`snd`.

Keep the rest of the M6 design that was already correct: freestanding runtime,
mount proc/sys/dev/configfs, bind the configfs gadget to **`a600000.dwc3`
only** (never `dummy_udc.0`), then force `/sys/class/usb_role/*/role=device` if
no enumeration, then park probing `/dev/ttyGS0`.

If the watchdog hypothesis is right, M7 should return to a **stable park** (no
fast loop); if it then also exposes `/dev/ttyGS0`/ACM, the control channel is
finally up. If M7 parks but still no ACM, the failure has moved downstream to
role/UDC and is now debuggable one module at a time within a non-looping boot.

## Blind-debug note

pstore/last_kmsg retained no M6 marker (ramoops disabled), so on-device phase
markers remain invisible. M7's park-vs-loop is still an eye-observable signal.
If M7 also loops, the watchdog exclude was insufficient and the next unit should
bisect the required subset (halve the module count) rather than add more — or
this is the point where the UART jig earns its cost.

## Discipline
Host-only postmortem; no secrets. M7 build stays host-only; any live flash needs
a fresh SHA-pinned boot-only `AGENTS.md` exception + attended ack + manual
download rollback. Device is on the known-good Magisk baseline after M6 rollback.
