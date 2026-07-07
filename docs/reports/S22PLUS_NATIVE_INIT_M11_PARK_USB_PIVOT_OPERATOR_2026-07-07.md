# S22+ Native-Init — Pivot to Park-Based USB Bring-Up (M11), Operator (2026-07-07)

Operator (Claude) host-only decision + recipe. Endorsed by the operator-user:
"get USB control first and stop the bootloop first." No device action here.

## Why stop the M10 reboot-beacon bisection

I disassembled the built freestanding-C discriminators (e.g. M10A2 getpid):
- the `_start` prologue is textbook-correct (`stp x29,x30,[sp,#-16]!; mov x29,sp;
  bl …; bl …; wfe`), stack stays 16-aligned, no stack-protector, `-fno-stack-
  protector` set;
- the `reboot("download")` argument setup is **byte-identical to the working
  M4T3** (`x0=0xfee1dead`, `x1=0x28121969`, `x2=0xa1b2c3d4`, `x3`→"download",
  `x8=142`).

So the C runtime and the reboot syscall are provably correct, yet M4T3
self-downloads while the C variants bootloop. That means **the
`reboot("download")` beacon is not a reliable observability primitive at bare
PID1** — identical correct code gives download-vs-loop nondeterministically. The
M10 line is bisecting noise, and each step costs one attended flash + manual
rollback. Stop it.

## New signal model (no reboot beacon)

Two real, reboot-beacon-free signals we already have:
1. **park vs bootloop** — operator's eyes (M5 parked; M6/M7 looped). Making the
   init PARK after bring-up turns "did a module reset the device" into a visible
   loop-vs-hang.
2. **ACM enumerates** — host sees `/dev/ttyGS0`. This is both the goal and the
   observation channel.

## The real question

M5 (26 USB-function modules) **parked, no ACM** (missing substrate). M7 (53
modules) **bootlooped** (substrate added, but something resets). So one of the
~27 modules M7 added over M5 causes the reset. Bisect that on the real goal with
the park-vs-loop signal — not the reboot beacon.

## M11 recipe (host-only build): park-based USB, leaner subset

Freestanding init (proven), mount `/proc`+`/sys`+`/dev`+`/config`, insmod the
subset in `modules.load.recovery` order honoring `modules.softdep`, bind the
configfs gadget to **`a600000.dwc3` only**, force `/sys/class/usb_role/*/role=
device`, then **PARK** (no reboot beacon).

Subset = M5's USB functions + genuine platform substrate + the **Samsung
max77705 i2c PD role chain**, first-attempt EXCLUDING the reset/complexity risks:

Keep (genuine USB substrate):
- clocks/power: `clk-rpmh`, `gcc-waipio`, `clk-qcom`, `clk-dummy`, `cmd-db`,
  `icc-rpmh`, `icc-bcm-voter`, `qcom_rpmh`, `rpmh-regulator`, `gdsc-regulator`,
  `debug-regulator`, `proxy-consumer`, `qti-fixed-regulator`
- soc/scm: `qcom-scm`, `smem`, `socinfo`, `sec_class`
- bus: `msm-geni-se`, `i2c-msm-geni`, `gpi`, `i2c-gpio`
- phy: `phy-generic`, `phy-msm-snps-hs`, `phy-msm-snps-eusb2`, `phy-msm-ssusb-qmp`
- usb: `dwc3-msm`, `usb_f_ss_acm` (+ the other `usb_f_*` M5 had)
- role (Samsung i2c PD): `mfd_max77705`, `pdic_max77705`, `usb_typec_manager`,
  `if_cb_manager`, `pdic_notifier_module`, `vbus_notifier`

Exclude first attempt (likely reset/complexity, not needed for the max77705
role path):
- Samsung debug/anomaly: `sec_debug`, `abc`, `minidump`, `icc-debug`
- glink/remote-subsystem: `pmic_glink`, `altmode-glink`, `ucsi_glink`,
  `qcom_glink`, `qcom_glink_smem`, `qcom_smd`, `pdr_interface`, `qmi_helpers`,
  `rproc_qcom_common`
- `eud` (force-peripheral fallback, but can itself perturb USB — add only if
  role-force fails)
- all watchdogs (already excluded)

Rationale: my USB-mechanism analysis showed the data role is driven by the
**max77705 PD IC over i2c**, not the QC glink/UCSI firmware path — so the glink
stack is droppable for peripheral bring-up, and it plus the Samsung debug/anomaly
modules are the most likely bare-init reset sources. `dwc3-msm` softdep only
requires the PHYs (kept) pre and `ucsi_glink` post (optional).

## Bisect logic (park-vs-loop, operator eyes)
- **Parks + ACM** ⇒ done: control channel up → A90-style interactive iteration.
- **Parks, no ACM** ⇒ substrate is safe; role/enum missing → add back the minimal
  role modules or enable EUD, one change per flash.
- **Still loops** ⇒ the reset module is inside the kept set (less likely); bisect
  the kept substrate (halve) — still park-vs-loop, no beacon.

## Bottom line
Prioritize the operator's stated goal: **stop the bootloop (park) and get USB
control (ACM)**, using visible park-vs-loop + host-ACM signals. Abandon the
reboot-download beacon — it is unreliable and the M10 bisection is chasing noise.
If two or three park-vs-loop flashes don't converge, that is the point the UART
jig is clearly worth its shipping time.

## Discipline
Host-only; no secrets. M11 build stays host-only; any live flash needs a fresh
SHA-pinned boot-only `AGENTS.md` exception + attended ack + manual-download
rollback. Device is on the known-good Magisk baseline.
