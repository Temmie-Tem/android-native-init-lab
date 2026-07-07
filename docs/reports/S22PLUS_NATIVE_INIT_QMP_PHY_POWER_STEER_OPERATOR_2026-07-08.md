# S22+ Native-Init — QMP PHY Needs Power Before Probe (Operator Steer, 2026-07-08)

Operator (Claude) host-only steer. No device action. Corrects a methodology gap
in the M14/M15/M16 bisect so the next attended flash is decisive, not a repeat.

## What the bisect established (good)
- **M13** (freestanding init: mount `/proc`+`/sys`+`/dev`+`/config`, **no
  modules**) → **PARK**, operator-visually-confirmed no boot loop. This is a
  stable floor: init runtime + boot construction + configfs are all fine.
- **M15/M16** narrowed the reset to a single module: insmod of
  **`phy-msm-ssusb-qmp.ko`** (USB SuperSpeed QMP PHY) → **BOOTLOOP**.

## The methodology gap
M14/M15/M16 loaded the QMP PHY **naked — with zero power/clock substrate**
(verified: 0 regulator/clock/gdsc modules in those candidates). A Qualcomm QMP
USB PHY on probe must get its regulators (vdda-phy/vdda-pll), its ref/pipe
clocks, and its power domain (GDSC). With none of `rpmh-regulator`,
`gdsc-regulator`, `clk-rpmh`, `gcc-waipio`, `qcom_rpmh`, `cmd-db`, `qcom-scm`
loaded, the PHY's `regulator_get`/`clk_get` cannot resolve real supplies and the
probe either touches unpowered/unclocked PHY registers (→ async bus abort →
watchdog reset → bootloop) or asserts. **A naked PHY looping is expected and not
conclusive.** Continuing to flash naked-PHY variants (M16) just repeats a known
result and burns attended cycles.

## The decisive experiment (do this next, one flash)
From the **M13 park floor**, add, in `modules.load.recovery` order:
1. the **power/clock substrate**: `cmd-db`, `clk-rpmh`, `gcc-waipio`, `clk-qcom`,
   `icc-rpmh`, `icc-bcm-voter`, `qcom_rpmh`, `rpmh-regulator`, `gdsc-regulator`,
   `qti-fixed-regulator`, `qcom-scm`, `smem`, `socinfo` (+ `proxy-consumer` if
   present);
2. then **`phy-msm-ssusb-qmp`** (and the other PHYs `phy-generic`,
   `phy-msm-snps-hs`, `phy-msm-snps-eusb2`);
3. **park** (no reboot beacon). Signal = operator park-vs-loop.

Outcomes:
- **Parks** ⇒ the PHY just needed its power substrate; proceed to add `dwc3-msm`
  → park? then the max77705 i2c role chain + `usb_f_ss_acm` + role-force → check
  ACM. The path is open.
- **Still loops** ⇒ the QMP PHY faults **even when powered** — meaning it needs a
  specific rail/GDSC enabled or an RPMh vote that Android's userspace/clock
  framework performs and a bare init does not. Diagnosing which register/rail
  blind is impractical: the kernel prints the exact abort (unhandled fault,
  GDSC/clk/regulator name) to the **console**, which only **UART** exposes here
  (pstore is disabled). This is the concrete point the UART jig is worth its
  shipping time.

## One-change-per-flash discipline
Do not jump straight to the full substrate+PHY+dwc3+role stack (that reintroduces
the M7/M11/M12 confound). Add substrate-then-PHY as one step from the M13 floor;
if it parks, add dwc3 as the next step; then the role chain. Each step is
park-vs-loop by eye.

## Note on M7/M11/M12
Those had substrate AND USB modules and still looped, so it is possible the QMP
PHY faults even powered (the "still loops" branch above). If the substrate+PHY
test loops, treat that as confirmation and move to UART rather than further blind
subset permutations.

## Discipline
Host-only; no secrets. Any live flash needs a fresh SHA-pinned boot-only
`AGENTS.md` exception + attended ack + manual-download rollback. Device is on the
known-good Magisk baseline.
