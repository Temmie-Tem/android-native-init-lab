# USB Subsystem

## Status

- FYG8 metadata closure: `STATIC_VERIFIED`.
- Exact automatic role path: `ELF_SOURCE_DT_VERIFIED` in the deep USB RE.
- Stock Android DWC3/UDC/gadget and participating driver path: `LIVE_BOUND`.
- PDIC-to-Type-C-manager relay: `LIVE_OBSERVED`; the same-boot USB attach event
  through `usb_notifier_qcom` to DWC3 was `NOT_CAPTURED_THIS_BOOT`.
- Direct-PID1 module execution: `LIVE_VERIFIED` through all 59 P2.50 entries.
- Direct-PID1 bind sequence: `LIVE_VERIFIED` through `gcc-waipio`; the SSUSB
  parent timed out next. Child creation and UDC remain unproved.
- P2.43 RPMh dependency split: `H0_VERIFIED`; the P2.42 display-RSC gate is
  retired from the proposed USB contract. Its then-unknown replacement binds
  are superseded by P2.50 evidence.
- P2.44 provider-gate implementation: `H0_VERIFIED`; the 12-gate source and
  profile-3 transition model pass. Its live-unknown status is superseded by
  P2.50 evidence through GCC.
- P2.50 provider-gate execution: `LIVE_VERIFIED` through stage `0x83`
  (`gcc-waipio`); stage `0x84` (`a600000.ssusb`) recorded `ETIMEDOUT`.
- P2.51 SSUSB dependency audit: `H0_VERIFIED`; exact cause remains open, but
  missing module/GCC/redriver are ruled out and the next discriminator is
  bounded to supplier, PHY, internal-probe, and shared-deadline branches.

The current O3 minimal-ACM metadata plan contains 59 modules and
passes recursive hard dependency, softdep pre/post, stock-order, alias,
blocklist, and options parsing. This proves a static load plan only.

P2.40 derives an E2-specific order that starts with `qcom_hwspinlock`, preserves
the live-proven E1B five-module order, and then appends the remaining canonical
O3 entries. All 59 modules are unique, all 210 constraints pass, and the
reordered TSV SHA256 is
`fc8169da1036ae8ba76e81ffe6afb17d063d114735a427e858afeeaa82a2218e`.

P2.41 generates that exact table into the runtime, verifies the exact 59
shipped module files, and checks `/proc/modules` to EOF after every successful
insertion. Missing, duplicate, already-loaded, or foreign modules fail closed.
The eight bind predicates are separately observed under one global 20-second
deadline; no sysfs/configfs write is used.

The exact FYG8 automatic cable/role path is:

```text
pdic_max77705 -> usb_typec_manager -> usb_notifier_qcom
  -> usb_notify_layer set_host/set_peripheral -> dwc3-msm role events
```

This chain is backed by 21 ELF call relocations, the SHA-pinned Samsung
`usb_notify.c`, and all 11 g0q DT overlays. The DT has parent and child
`usb-role-switch` properties, `dr_mode = "otg"`, a Max77705 PDIC with role-swap
support, and a separate `samsung,usb-notifier` node. It has no direct
Max77705-to-DWC3 phandle or explicit extcon property for this path. Details and
the serial-redacted live sidecar are in `deep-usb-re/`.

The same exact `dwc3-msm.ko` also verifies the deliberate bypass used by O3:

```text
mode_store("peripheral") -> dwc3_msm_set_role(role=2)
  -> VBUS-active/role state -> ext-event -> OTG work
  -> start peripheral -> role switch + VBUS session + gadget connect
```

Thus the Samsung Max77705 notifier chain is required for stock automatic role
policy, but not after a successfully bound `dwc3-msm` receives the explicit
peripheral-mode request. Do not widen O3 with the five-module policy chain to
explain its no-USB result; that result remains unlocalized to an earlier or
downstream gate because no candidate phase readback was captured.

P2.40 also closes a narrower pre-write path. The exact FYG8 `dwc3-msm.ko`
successful probe queues its OTG state work at delay zero. The undefined-state
worker calls `dwc3_msm_core_init()`, which populates the DWC3 child. With the
exact DT's child `usb-role-switch` and `dr_mode = "otg"`, the built-in DWC3
role-switch setup defaults to peripheral, queues `dwc3_set_mode()`, and reaches
`dwc3_gadget_init()` plus `usb_add_gadget()`. Consequently E2 can observe the
child and exact UDC without writing the parent `mode` attribute or configfs.
This is source/ELF/DT closure only; direct-PID1 success remains a live unknown.

P2.41 closes the earlier private decompile gap by parsing the exact SHA-pinned
DTBO directly. All 11 entries require the same role-switch, OTG, MAX77705,
notifier, and UCSI topology and reject explicit `extcon` and
`role-switch-default-mode` properties. This remains static topology evidence,
not bind evidence.

P2.42 adds the first direct-PID1 live bind evidence. The exact profile-3 record
proves all 59 module insertions and prefix checks, then exact `hwspinlock`,
`smem`, and `cmd-db` bind symlinks. The next `rpmh` predicate timed out at
stage `0x7e`, item index 3, detail 110 (`ETIMEDOUT`). Downstream gates were not
reached. Exact rollback and final Android health passed.

P2.43 resolves the dependency mismatch behind that boundary. `af20000.rsc` is
the display RSC: it has no power domain and is held behind the omitted
`dispcc-waipio.ko` clock supplier. The USB-relevant RSC is `17a00000.rsc`,
which depends on the built-in PSCI `cluster-pd` provider and then creates the
RPMh clock/regulator providers consumed by GCC. Strict `fw_devlink` can defer
the display consumer before `rpmh_rsc_probe()`; this is a strong static
explanation, not a direct observation of the P2.42 runtime supplier state.
Adding the display module is explicitly out of scope.

## P2.42 Historical Gates

| Order | Gate | Provider | Required path | Direct-PID1 status |
|---:|---|---|---|---|
| 1 | `hwspinlock` | `qcom_hwspinlock` | `/sys/bus/platform/drivers/qcom_hwspinlock/soc:hwlock` | `LIVE PASS` in P2.42 |
| 2 | `smem` | `smem` | `/sys/bus/platform/drivers/qcom-smem/soc:qcom,smem` | `LIVE PASS` in P2.42 |
| 3 | `cmd-db` | `cmd_db` | `/sys/bus/platform/drivers/cmd-db/80860000.aop_cmd_db_region` | `LIVE PASS` in P2.42 |
| 4 | `rpmh` | `qcom_rpmh` | `/sys/bus/platform/drivers/rpmh/af20000.rsc` | `LIVE TIMEOUT` in P2.42 |
| 5 | `gcc-waipio` | `gcc_waipio` | `/sys/bus/platform/drivers/gcc-waipio/100000.clock-controller` | `NOT REACHED` in P2.42 |
| 6 | `ssusb` | `dwc3_msm` | `/sys/bus/platform/drivers/msm-dwc3/a600000.ssusb` | `NOT REACHED` in P2.42 |
| 7 | `dwc3-core` | built-in | `/sys/bus/platform/drivers/dwc3/a600000.dwc3` | `NOT REACHED` in P2.42 |
| 8 | `udc` | built-in | `/sys/class/udc/a600000.dwc3` | `NOT REACHED` in P2.42 |

The display-RSC row above is retained only as historical P2.42 evidence. It is
not a gate for a future USB candidate.

## P2.44 Implemented Provider Gates

P2.44 preserves the first three and last three historical gates, replaces the
`rpmh` plus `gcc-waipio` pair with this ordered six-predicate chain, and adds
no module:

| Order within chain | Gate | Required path | Direct-PID1 status |
|---:|---|---|---|
| 1 | `psci-domain` | `/sys/bus/platform/drivers/psci-cpuidle-domain/soc:psci` | `UNKNOWN` |
| 2 | `apps-rsc` | `/sys/bus/platform/drivers/rpmh/17a00000.rsc` | `UNKNOWN` |
| 3 | `apps-rpmh-clock` | `/sys/bus/platform/drivers/clk-rpmh/17a00000.rsc:qcom,rpmhclk` | `UNKNOWN` |
| 4 | `apps-rpmh-cxlvl` | `/sys/bus/platform/drivers/qcom,rpmh-regulator/17a00000.rsc:rpmh-regulator-cxlvl` | `UNKNOWN` |
| 5 | `apps-rpmh-mxlvl` | `/sys/bus/platform/drivers/qcom,rpmh-regulator/17a00000.rsc:rpmh-regulator-mxlvl` | `UNKNOWN` |
| 6 | `gcc-waipio` | `/sys/bus/platform/drivers/gcc-waipio/100000.clock-controller` | `UNKNOWN` |

The resulting full gate count is 12. With the existing profile-3 base, its
gate stages are `0x7b..0x86`, leaving terminal success at `0x8f`.

P2.50 live evidence advances this table through `gcc-waipio`. The first
unbound gate is now `ssusb` at `0x84`; the later `dwc3-core` and `udc` gates
were not reached.

## P2.51 SSUSB Frontier

The current 20-second timeout is shared by the entire 12-gate loop. It is not a
dedicated 20-second SSUSB wait, and no per-gate timestamp was retained.
SSUSB's actual dwell is therefore only bounded to `0..20` seconds.

Exact FYG8 DT plus same-build stock sysfs identify the stable parent providers:
GCC, USB3 GDSC, PDC, four qnoc devices, and EUD. The child adds HS/SS PHYs and
the SMMU. The exact module plan already carries their required modules.
Registration alone remains insufficient.

Strict `fw_devlink` can hold the parent before `dwc3_msm_probe()`. If suppliers
are resolved, the exact probe can still return on GDSC defer, mandatory
clock/IRQ/resource failures, either PHY lookup, or role setup. The exact module
contains these probe calls. It contains no active `extcon_*` call in the probe,
so EUD is currently classified as a firmware-link supplier rather than the
leading probe-internal branch.

The next bounded implementation keeps frontier stage `0x84`, reads
`waiting_for_supplier`, seven fixed parent-provider bind paths, and two PHY
bind paths, then records a structured `0xa00..0xaff` detail. If all are ready,
one SSUSB-only five-second grace separates late bind from stable internal
failure. That band is currently reserved/rejected, so P2.52 must define the
exact subset through the existing descriptor SoT and derive both kernel and
decoder acceptance. It adds no modules and no provider checkpoint stages.

P2.51b closes the lower graph below those two PHY binds. All four FYG8 vendor
DTBs agree:

```text
HS PHY:
  ref_clk_src -> apps RPMh clock
  ref_clk + reset -> GCC
  vdd/vdda18/vdda33 -> RPMh ldob5/ldoc1/ldob2

SS PHY:
  clocks + resets -> GCC and apps RPMh clock
  vdd/core -> RPMh ldob1/ldob6
  pinctrl-0 -> f000000.pinctrl
```

The Waipio TLMM path and five RPMh LDO wrapper paths are now branch-only
P2.52 classifier inputs at details `0xa08..0xa0d`. They are not new stages.
Their exact provider modules and recursive hard dependencies are already in
the 59-module plan.

The USB3 GDSC has no external clock/reset/interconnect/power-domain supplier.
Its `proxy-supply` points to itself, and matched OF source rejects that
self-link. Missing GDSC bind therefore remains an internal GDSC probe branch.
Exact HS/SS module ELF lacks both sysfs imports used by the matched source's
tuning branch, ruling out `CONFIG_USB_PHY_TUNING_QCOM` as this candidate's bind
blocker.

One source-visible asymmetry remains only as a conditional lead: HS removes a
registered PHY when later regulator setup fails, while SS registers before
regulator acquisition and has no failed-probe `usb_remove_phy()` path. This is
not live proof of a stale SS PHY. Follow it only if P2.52 proves every nested
provider bound while SS PHY remains absent.

A `finit_module` return code or `/proc/modules` name proves registration only.
The next gate advances only after its driver/device path exists. O3 PASS remains
a framed host/device ACM request-response plus device-reported bind state, not
enumeration or survival.

O0 stock control, O1.1 stock-first-stage control, O2 loader parity, the compact
retained carrier, E1A/E1B live foundations, P2.41 E2 source implementation,
P2.42/P2.46/P2.50 live boundaries, and the P2.48 derived validator are
complete. P2.51 closes the focused SSUSB dependency analysis, not the live
root cause. Do not retry E2 unchanged or infer downstream USB state. The
latest stock read-only evidence is maintained separately in
`stock-usb-runtime-topology.json`.
