# S22+ — Stop Observing the Fault, Avoid It: HS-Only USB2 ACM (M25 Operator Steer, 2026-07-08)

Operator (Claude) host-only steer, from the operator-user's structural push
("when init loads and doesn't bootloop, is there any functional/external channel
at all?"). No device action here. This is a **fault-avoidance** pivot, not another
observability attempt.

## Why pivot: observation is exhausted, but the fault is narrow

Five "read the fault" channels have now failed for the M18/M23 hang:
1. sec_debug/MID + RDX/`last_kmsg` — panic-only; the hang is a watchdog bite, not
   a panic. Empty.
2. Samsung `reset_summary`/`reset_klog` — `reset_reason=NPON` after recovery; the
   context is cleared by the download→rollback→boot chain (or the hang is too
   early for sec_debug to arm). Empty.
3. EUD (COM + SWD/JTAG) — TrustZone-gated (`scm_io_write` to the mode-manager
   `rc:-22`). Closed.
4. mainline ramoops — vestigial on this Samsung device.
5. M24 pmsg step-markers — pstore empty, no `A90_STEP:` retained (same
   early-boot / recovery-clear survival problem).

But the fault itself is **narrow and already localized**: M13 (no modules) parks;
only `phy-msm-ssusb-qmp` (M15) bootloops. So instead of struggling to *see* the
hang, **avoid the module that causes it** — which is possible because of what the
DT actually says about the USB hardware.

## The DT proves a clean structural sidestep (decoded from vendor_boot DTB)

```
dwc3@a600000   maximum-speed = super-speed-plus     ← currently tries USB3
hsphy@88e3000  qcom,usb-hsphy-snps-femto            ← HighSpeed / USB2 PHY (separate)
ssphy@88e8000  qcom,usb-ssphy-qmp-dp-combo          ← the QMP SuperSpeed PHY = M15's hang
```

- **`ssphy@88e8000` is a QMP-DP-combo** (shared with DisplayPort): heavy
  power/clock (aux_clk/pipe_clk/multiple resets/pinctrl) → that is why it hangs
  when its rails aren't up under a bare init.
- **`hsphy@88e3000` is a completely separate HS PHY** that M15 never implicated,
  and it is demonstrably working — normal ADB and EUD's non-secure path both run
  over it. (It even holds the `eud_enable_reg`, which is why EUD's plain CSR write
  succeeded while the secure SS/mode-manager write failed.)
- `ssusb@a600000` carries separate `ss_phy_irq` vs `dp_hs_phy_irq`/`dm_hs_phy_irq`
  → HS and SS are handled separately in the controller.

**A serial control channel (ACM) needs only HighSpeed (USB2, 480 Mbps).** A90's
serial bridge was USB2-class. USB3/SuperSpeed — and therefore the QMP PHY — is
**not required for the control channel at all.**

## M25 recipe (host-only build): HS-only USB2 ACM

From the M13 park floor:
1. **Cap dwc3 to HighSpeed** — override `dwc3@a600000` `maximum-speed`
   `super-speed-plus` → `high-speed` (DTBO overlay on the dtbo, the proven-working
   overlay path; or a dwc3 module param if the vendor glue honors one). With SS
   capped, dwc3 should not require/init the SS PHY.
2. **Load only the HS/USB2 bring-up set, EXCLUDING `phy-msm-ssusb-qmp`:**
   `phy-generic`, `phy-msm-snps-hs` (the femto HS phy) + the eUSB2 repeater if the
   HS path uses one, `dwc3-msm`, `usb_f_ss_acm` (ACM at HS), plus the minimal
   clock/regulator substrate the HS phy + dwc3 need (much lighter than the QMP's).
3. Bind the configfs gadget to **`a600000.dwc3`** only, force
   `/sys/class/usb_role/*/role=device`, **park**.
4. **Success signal = host enumerates `/dev/ttyGS0` (ACM)** — console-free,
   unambiguous. Failure = still bootloops or no ACM.

## Decision gate
- **ACM enumerates** ⇒ we have the A90-style bidirectional control channel with
  the QMP PHY never touched. The observability wall is bypassed and native-init
  iteration becomes cheap (interactive), exactly like A90. Proceed to build the
  command surface on ttyGS0.
- **Still bootloops** ⇒ the vendor dwc3-msm hard-requires the SS PHY even in HS
  mode, or the HS phy path itself needs more substrate. Then bisect the HS set
  from the M13 floor (park-vs-loop), and only then reconsider the UART clip.

## Honest caveat (one live test resolves it)
The single unknown is whether the vendor `dwc3-msm` allows HS-only (does not call
SS-phy ops unconditionally). Mainline dwc3 gates the SS phy on `maximum-speed`, so
it is architecturally supported; the `ss_phy_irq` vs HS-irq separation in the DT
is encouraging. One attended flash settles it, with a clean success signal (ACM)
that needs no console.

## Why this is the right card now
Every observation path failed because they all try to *see* a watchdog bite that
Samsung's panic-triggered machinery doesn't capture and that our recovery chain
clears. This card doesn't observe — it **removes the faulting module from the
path** and reaches the actual goal (USB-ACM control) over USB2. It is the most
structural, goal-directed unit available, and its success signal is the goal
itself.

## Discipline
Host-only build + dry-run; any live flash needs a fresh SHA-pinned boot-only (or
boot+dtbo) `AGENTS.md` exception + attended ack + manual-download rollback to the
pinned Magisk baseline. No forbidden partitions, no PMIC/power writes, redacted
logs (strip serials). MID stays set (harmless); the UART clip remains a backstop
only if M25 and its HS-set bisect both fail.
