# S22+ USB Subsystem Host Analysis — Who Needs What, and Where HS-Only ACM Breaks (2026-07-09)

Operator (Claude) host-only analysis of the FYG8 USB stack, from prebuilt `.ko`
`modinfo`/strings and the vendor_boot DTB. No device action. Goal: map the full
correlation (who/where/what/how/what-is-needed) before any more live flashes, so
the ACM path is designed, not bisected blindly.

## 1. The USB data path, bottom-up (DTB `a600000` controller)

```
ssusb@a600000  (qcom,dwc-usb3-msm  = the dwc3-msm glue/wrapper)
  clocks: core_clk iface_clk bus_aggr_clk utmi_clk sleep_clk   reset: core_reset
  └─ dwc3@a600000 (snps,dwc3 = the DesignWare core)
       dr_mode = "otg"                      ← must be forced peripheral for a gadget
       maximum-speed = "super-speed-plus"   ← our DTBO caps this to high-speed
       usb-phy = <&hsphy &ssphy>            ← BOTH phys wired in (the crux)
       ├─ hsphy@88e3000 (qcom,usb-hsphy-snps-femto = HighSpeed/USB2)
       │    vdd-supply + vdda18-supply + vdda33-supply   (3 regulators)
       │    clocks: ref_clk_src ref_clk     reset: phy_reset
       └─ ssphy@88e8000 (qcom,usb-ssphy-qmp-dp-combo = SuperSpeed, DP-shared)
            vdd-supply (+ refgen)           7 clocks: aux_clk pipe_clk pipe_clk_mux
            pipe_clk_ext_src ref_clk_src com_aux_clk ref_clk
            resets: global_phy_reset phy_reset   + LDO enables
```

**Key structural fact:** the `dwc3` node's `usb-phy` array wires **both** the HS
phy and the SS/QMP phy. Capping `maximum-speed` to `high-speed` (our M25 DTBO)
does **not** remove the SS phy from this array — so dwc3-msm still reaches for it.

## 2. Power/clock weight per PHY (from `.ko` strings + DTB)

| PHY | Regulators | Clocks | Resets | Weight |
| --- | --- | --- | --- | --- |
| `hsphy@88e3000` (HS femto) | vdd, vdda18, vdda33 | 2 | 1 | **light** |
| `ssphy@88e8000` (SS QMP-DP) | vdd + refgen + LDO enables | **7** | 2 | **heavy** |

`phy-msm-ssusb-qmp.ko` strings confirm the heavy path: `msm_ssusb_qmp_ldo_enable`,
`aux_clk/com_aux_clk/pipe_clk`, `global_phy_reset`, "Global reset of QMP DP combo
phy", `qcom,refgen-voltage-level`. If those rails/clocks are not up, it fails at
`msm_ssusb_qmp_ldo_enable` — **this is the M15 hang**. Even the HS eUSB2 path
(`phy-msm-snps-eusb2.ko`) needs a `vdd` regulator + `ref_clk` + a `repeater`
("eUSB2 PHY is not out of reset", "regulators are turned OFF").

**Implication:** any USB (even HS-only) needs the HS phy's 3 regulators up. Those
come from `rpmh-regulator` (now in our dependency-complete set) → likely
satisfiable. The SS phy's heavy rails are what we must *avoid*, not supply.

## 3. The module dependency graph (hard `depends:` + `softdep:`)

```
dwc3-msm  (the gadget controller)
  softdep pre : phy-generic phy-msm-snps-hs phy-msm-snps-eusb2
                phy-msm-ssusb-qmp  eud            ← wants the SS/QMP phy + EUD
  depends     : usb_notify_layer usb_f_ss_mon_gadget redriver qcom_ipc_logging
                clk-qcom if_cb_manager qc_usb_audio usb_typec_manager sec_class
                       │
                       └─ usb_typec_manager depends:
                            usb_notify_layer common_muic pdic_notifier_module
                            vbus_notifier abc sec_class
                              ├─ common_muic       depends: switch_class sec_class usb_notify_layer
                              └─ pdic_notifier_module depends: sec_class switch_class usb_notify_layer
  phy-msm-snps-eusb2 depends: usb_f_ss_mon_gadget qcom-scm repeater
  usb_f_ss_mon_gadget depends: usb_typec_manager usb_notify_layer
```

**Two hard truths from this graph:**
1. **`dwc3-msm` hard-depends on the entire Samsung TypeC/PD/MUIC tree**
   (`usb_typec_manager` → `common_muic` + `pdic_notifier_module` + `vbus_notifier`
   + `abc`) plus `qc_usb_audio`. You **cannot insmod `dwc3-msm` without loading
   all of them** (unresolved symbols otherwise). This tree talks to the USB-C
   PD/MUIC hardware (`max77705` PMIC/PD IC lives nearby) → **PMIC-adjacent =
   safety-sensitive.**
2. **`dwc3-msm`'s softdep explicitly wants `phy-msm-ssusb-qmp` (SS phy) + `eud`
   loaded first.** Running HS-only (QMP excluded) is genuinely off the stock
   path; the stock recipe assumes the SS phy is present and powered.

## 4. Where HS-only ACM breaks — and what M32/M33 already proved

- M33 `P12` (substrate suppliers + watchdog): survives. Clocks/regulators/
  `sec_debug`/`minidump`/`rpmh` layer is fine.
- M33 `P27` (+ SMMU + HS/eUSB2 PHY, **no dwc3**): survives. So the HS phy
  regulators/clocks come up — **HS PHY power is satisfiable under native init.**
- M32 (watchdog + full HS USB set **incl dwc3-msm + configfs ACM**): ~35 s hard
  hang → PMIC/PON watchdog bite. `P28` (add just `dwc3-msm`) is the untested
  decisive point.

Correlating with §1–§3, the leading cause is now well-supported: **`dwc3-msm`,
during probe, reaches the SS/QMP phy** (still wired in `usb-phy=<&hsphy &ssphy>`
and demanded by its softdep) and touches SS PHY control on **unpowered DP-combo
rails** (`PRI_SS_PHY_CTRL`, "failed to init SS PHY") → the same M15 hard hang,
now inside dwc3-msm rather than the standalone QMP module. Module bisection alone
cannot fix this: the SS-phy reach is wired in **DT**, not in the module list.

## 5. What is actually needed for HS-only ACM (the recipe this analysis implies)

Already in hand:
- Dependency-complete substrate (M28) ✓
- Watchdog managed so PID1 can stay alive (M31B) ✓
- HS phy regulators/clocks up (M33 P27) ✓

Still required, in order:
1. **DT change (DTBO), not a module change: remove the `ssphy` phandle from the
   `dwc3@a600000` `usb-phy` array** (drop the second entry `&ssphy@88e8000`), so
   dwc3-msm cannot reach the SS/QMP phy at all. Keep `maximum-speed=high-speed`.
   (Investigate `qcom,use-eusb2-phy` — the driver has that code path in strings,
   though it is not set in the stock DTB — as an alternative/companion knob.)
2. **Force peripheral, not otg**: `dr_mode` is `otg`; the gadget only needs
   device mode. Force `usb_role=device` (runtime, as the init already attempts)
   and/or set `dr_mode=peripheral` in the DTBO to keep dwc3 from host-side SS
   bring-up.
3. **Load `dwc3-msm`'s hard TypeC/PD dep tree** (`usb_typec_manager`,
   `common_muic`, `pdic_notifier_module`, `vbus_notifier`, `abc`, `switch_class`,
   `qc_usb_audio`, `redriver`, `if_cb_manager`, `usb_notify_layer`) — required to
   resolve symbols. **Safety watch:** these are PMIC/MUIC-adjacent; loading the
   drivers is allowed, but nothing here should be coerced into PMIC/charger
   register writes. If one of them hard-hangs on missing PD/charger hardware, it
   may need its own DT stub or exclusion — a second possible failure branch
   distinct from the SS phy.
4. Then `usb_f_ss_acm` gadget bind on `a600000.dwc3`, park, look for
   `/dev/ttyGS0`.

## 6. Recommendation

- **Do not keep bisecting the module list past `P28`.** Run `P28` once only to
  *confirm* `dwc3-msm` is the hang; the fix is not a module boundary.
- **Next build unit is a DTBO experiment**, not a module permutation: (a) sever
  the `ssphy` phandle from `dwc3.usb-phy` (+ keep HS cap), optionally (b)
  `dr_mode=peripheral`, then rerun the watchdog-managed HS ACM candidate.
- Treat the Samsung TypeC/PD/MUIC hard-dep tree as the **second** candidate hang
  site; if severing the SS phy does not clear the ~35 s bite, bisect *that* tree
  next (it is the only other thing dwc3-msm forces in), with PMIC-write safety
  held.

## Discipline

Host-only analysis; the DTBO phandle edit + any live test need a fresh
SHA-pinned boot+DTBO `AGENTS.md` exception + attended ack. No forbidden
partitions, no PMIC/regulator/GDSC/GPIO power writes (loading stock drivers and
editing a DT phandle are neither). Redact serials. Device is on the clean Magisk
baseline.
