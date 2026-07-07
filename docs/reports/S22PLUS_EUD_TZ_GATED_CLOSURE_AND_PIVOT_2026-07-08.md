# S22+ EUD is TrustZone-Gated Off — Closure + Pivot (Host+Live Finding, 2026-07-08)

Operator (Claude) analysis of the Phase-B live dmesg + `eud.c` source + LWN
SM8450 EUD series + Samsung UART-jig websearch. Resolves *why* EUD does not
attach and what to do instead.

## Root cause — the secure EUD mode-manager write is denied by TrustZone

Phase-B live dmesg (device, on `echo 1 > /sys/module/eud/parameters/enable`):

```
msm-eud 88e0000.qcom,msm-eud: qcom_scm_io_writel failed with rc:-22
msm-eud 88e0000.qcom,msm-eud: qcom_scm_io_write  failed with rc:-22
```

`eud.c` shows `enable_eud()` does **two** writes:
1. `writel_relaxed(BIT(0), eud_reg_base + EUD_REG_CSR_EUD_EN)` — a plain EL1 MMIO
   write. This **succeeds** (that is why `enable` reads back 1).
2. `scm_io_write(eud_mode_mgr2_phys_base + …)` — a **secure (SCM/TrustZone)**
   write to the EUD **mode-manager** register, because that register is in a
   TZ-protected region EL1 cannot write directly. This **fails with rc:-22
   (EINVAL)**.

The mode-manager write is what actually routes the USB-C data path into the EUD
hub (the attach). LWN's SM8450 EUD series confirms the SM8450 attach needs HS-PHY
management + routing the **usb role-switch through EUD** — and the routing step is
the TZ-gated mode-manager write here. **Samsung's retail TrustZone refuses it**
(the EUD mode-manager phys address is not in the retail TZ io-write allowlist, or
EUD is qfprom-fuse-disabled). This matches Linaro's note that EUD works on dev
boards (HDK) and "some production devices" but not all.

## Verdict: EUD is closed on this retail S22+ (no EL1 workaround)

- The non-secure half enables; the **secure attach half is TZ-denied**. There is
  no EL1-side bypass — the register is only writable by TrustZone, and TZ says no.
- Bypassing would require a TrustZone/S-Boot exploit (Samsung RKP/KDP-hardened) =
  **out of scope**. So **EUD-COM console and EUD-SWD/JTAG are both closed** (both
  need the same attach).
- Long-shot only: debug_level HIGH (vs current MID) *might* change a TZ gate — one
  `*#9900#` toggle, near-zero cost to check — but a TZ io-write allowlist is not
  usually debug-level gated, so treat EUD as closed.

## Observability scorecard for the M18 fault (a CPU hang → warm reset)

| Channel | For M18's hang | Status |
|---|---|---|
| sec_debug/MID/RDX (post-mortem) | ✗ (panic-only; hang bypasses it) | proven by M18 no-hit |
| mainline ramoops | ✗ | vestigial here |
| EUD COM console + SWD/JTAG | ✗ | **TZ-gated off (this report)** |
| Samsung USB-C UART jig | △ live console *would* catch last line before hang | cheap (~$10 619k clip) but **uncertain on USB-C S22**; needs `console=ttyMSM0` (live is `console=null` + `nohyp_uart`) |
| Soldered UART test point | ✓ definitive | invasive |

The no-jig channels are now largely exhausted for a silent hang.

## Pivot — two-track, cheapest first

### Track B (free, do first): DTS-exact QMP-PHY dependency-closure substrate
Stop needing to *read* the fault; *prevent* it. The fault is the QMP USB PHY
touching an unpowered/unclocked register. The DTS declares exactly what that PHY
(and `dwc3@a600000`) needs. Host-only: enumerate the `usb_qmp_phy`/`dwc3` node's
**`vdda-*-supply` / `clocks` / `resets` / `power-domains`**, map each to its
provider module, and build a substrate that loads **exactly those providers in
dependency order**, then bind `a600000.dwc3` + force peripheral + park.
- **This has a clear SUCCESS signal that needs no console:** if the substrate is
  right, the PHY probes → dwc3 probes → **ACM enumerates (host sees `/dev/ttyGS0`)**.
  Success is unambiguous; only failure is blind.
- More surgical than M17/M18 (which loaded Android's whole first-stage set, not
  the PHY's exact declared closure). One attended flash.

### Track A (cheap backstop, order in parallel): Samsung USB-C UART jig
If Track B still bootloops, we need the live console after all. A ~$10 no-solder
Samsung UART clip (switchable 619k/523k/…) *may* route the debug UART to the
USB-C SBU pins; pair with `console=ttyMSM0`/earlycon on the boot candidate to
catch the last printk before the hang. Uncertain on USB-C S22 (mixed reports) —
order it as a backstop while Track B runs, don't block on it.

Soldered UART test point = last resort if both the jig and Track B fail.

## Recommendation
1. **Track B now** (host-only build of the DTS-exact QMP-PHY closure substrate;
   attended flash; success = ACM enumerates).
2. In parallel, **order the cheap Samsung USB-C UART clip** as the live-console
   backstop (accepts the USB-C uncertainty; only needed if B fails).
3. Keep sec_debug/MID for panic-class faults; do not burn more flashes trying to
   read the *hang* via MID/RDX/EUD.
4. Retire the EUD live-gate track (TZ-gated); keep the OpenOCD staging as dormant
   (only useful if a TZ path ever opens).

## Sources
- EUD device-side `scm_io_write` to eud_mode_mgr2: A90-tree `drivers/soc/qcom/eud.c`.
- LWN SM8450 EUD (HS-PHY + role-switch routing): https://lwn.net/Articles/984085/
- Linaro (dev-board vs production): https://www.linaro.org/blog/hidden-jtag-qualcomm-snapdragon-usb/
- Samsung UART resistor jig (619k/523k, USB-C uncertainty):
  https://github.com/Otus9051/uart-usb-jig , https://xdaforums.com/t/guide-usb-uart-on-galaxy-s-devices-2012-09-25.1901376/
