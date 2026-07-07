# S22+ USB Peripheral Bring-Up Mechanism — Host-Only Static Analysis (2026-07-07)

Operator (Claude) host-only analysis of how the S22+ USB device (peripheral)
port comes up, derived entirely from the FYG8 DTS, vendor `.ko` symbol/string
analysis, the extracted DTB, and the working-Android capture — no device action.
Purpose: give M7 an explicit role/peripheral plan instead of blind flashing.

## The chain (static, end-to-end)

```
cable attach
 → max77705 PD IC (on i2c)          # DTS: max77705_pdic, compatible "maxim,max77705_pdic", support_pd_role_swap
 → PDIC_NOTIFY_ATTACH               # pdic_max77705.ko -> usb_typec_manager.ko (TCM)
 → TCM sets data role = device (UFP)
 → usb-role-switch = "device"       # DTS dwc3@a600000: usb-role-switch; wired to connector port-graph
 → dwc3-msm set_role(DEVICE)        # dwc3-msm.ko: usb_role_switch_register / dwc3_msm_usb_role_switch_set_role
 → dwc3 enters peripheral           # DTS dr_mode="otg" => default peripheral-capable, UDC active on VBUS session
 → UDC a600000.dwc3 active
 → configfs gadget bound to a600000.dwc3 enumerates on host
```

## Key facts and their sources
- **DTS `dwc3@a600000`**: `dr_mode = "otg"`, `usb-role-switch;`, `maximum-speed
  = "super-speed"`, linked by port-graph to a `connector`. So the role is set by
  a Type-C connector driver via the kernel USB role-switch framework; dwc3 with
  otg defaults to peripheral when role is NONE.
- **Role source is Samsung `max77705` PD IC on i2c** (`maxim,max77705_pdic`,
  `support_pd_role_swap`), bridged by `usb_typec_manager` (TCM) via
  `PDIC_NOTIFY_ATTACH/DETACH`. This is an **i2c-based** path (needs i2c bus +
  the max77705 mfd/pdic modules), **not** primarily the QC glink/firmware UCSI
  path — good for bare-init feasibility (no glink-to-PMIC-firmware dependency
  for basic UFP detection). A `ucsi` node is also present in DT but the Samsung
  data-role path runs through max77705/TCM.
- **dwc3-msm registers a usb_role_switch** (`usb_role_switch_register`,
  `dwc3_msm_usb_role_switch_set_role`) → there is a writable
  `/sys/class/usb_role/<sw>/role` to force the data role directly.
- **EUD** (`eud.ko`: `enable_eud`, `eud_config_port`, sysfs `enable`; DTS
  `qcom,msm-eud`; listed in `modules.softdep` as a dwc3_msm pre-dep) is a
  Qualcomm hardware USB-debugger block that can force the port into a
  peripheral/attached state, bypassing Type-C role negotiation.

## Three independent ways to reach peripheral (redundancy)
1. **Auto**: max77705 PD (i2c) detects the attached host and drives role=device
   through TCM → role-switch. Works driver-only (in-kernel notifier chain), if
   max77705 probes (needs i2c bus + its IRQ/regulator).
2. **Force role-switch**: write `device` to `/sys/class/usb_role/*/role` →
   `dwc3_msm_usb_role_switch_set_role(DEVICE)` directly, bypassing PD detection.
3. **EUD**: enable the EUD block to force peripheral attach.
Plus `dr_mode="otg"` means dwc3 is peripheral by default, so role=device + host
VBUS should enumerate.

## Residual runtime unknowns (not resolvable statically)
- Whether `max77705` completes probe under bare init (needs i2c-msm-geni +
  msm-geni-se up, its interrupt parent, and chip regulators) so the auto path's
  attach IRQ fires.
- Whether any of the role paths need a VBUS-session event that only arrives with
  a real cable + PD contract.
These are why redundancy matters: if auto (path 1) doesn't fire, M7 should try
path 2 (role-switch force) then path 3 (EUD) before declaring a miss.

## M7 recipe additions (on top of the watchdog-trimmed USB subset)
1. Ensure the role chain modules are in the subset: `i2c-msm-geni`, `msm-geni-se`,
   `mfd_max77705`, `pdic_max77705`, `usb_typec_manager`, `if_cb_manager`,
   `pdic_notifier_module`, `vbus_notifier`, plus `eud`.
2. After module load + gadget bind to `a600000.dwc3`, if no enumeration within a
   short window, **actively force peripheral**: write `device` to every
   `/sys/class/usb_role/*/role`; if still nothing, enable EUD.
3. Only then park probing `/dev/ttyGS0`.

## Bottom line
"How USB comes up" is now statically mapped end-to-end. The role source is an
i2c PD chip (bare-init friendly), and there are three independent force paths.
This removes most of the blind uncertainty from the M5/M6 era: M7 should reach a
stable park (watchdog trimmed) and has explicit, redundant routes to peripheral,
so the ACM channel is materially more likely than a blind attempt.

## Discipline
Host-only static analysis; no device action, no secrets. M7 build stays
host-only; any live flash needs a fresh SHA-pinned boot-only `AGENTS.md`
exception + attended ack + manual-download rollback.
