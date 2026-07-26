# USB Subsystem

## Status

- FYG8 metadata closure: `STATIC_VERIFIED`.
- Exact automatic role path: `ELF_SOURCE_DT_VERIFIED` in the deep USB RE.
- Stock Android DWC3/UDC/gadget and participating driver path: `LIVE_BOUND`.
- PDIC-to-Type-C-manager relay: `LIVE_OBSERVED`; the same-boot USB attach event
  through `usb_notifier_qcom` to DWC3 was `NOT_CAPTURED_THIS_BOOT`.
- Direct-PID1 module execution: `LIVE_VERIFIED` through all 59 P2.50 entries.
- Direct-PID1 bind sequence: `LIVE_VERIFIED` through SSUSB and the DWC3 child
  in P2.57; the following UDC singleton predicate failed, but it cannot prove
  whether the exact DWC3 UDC was present.
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
- P2.55 classifier execution: `LIVE_VERIFIED` through qnoc aggre1, then exact
  `0xa04` at qnoc mc_virt; rollback and final health passed.
- P2.56 qnoc focused analysis: `STRONG_STATIC_CAUSAL_HYPOTHESIS`; exact DT,
  shipped ELF, source, and plan converge on the omitted display-clock module,
  but `PART_DISPLAY`, intermediate binds, and the qnoc return code were not
  retained.
- P2.57 display-closure execution: `LIVE_VERIFIED` through DWC3 core stage
  `0x86`; UDC stage `0x87` recorded `ETIMEDOUT`, with exact rollback and final
  health.
- P2.58 UDC focused analysis: `H0_VERIFIED`; the gate incorrectly requires
  global UDC singleton cardinality although FYG8 normally has both
  `dummy_udc.0` and `a600000.dwc3`. DWC3 bind also precedes queued
  role/gadget work, and the shared deadline leaves its dwell ambiguous.
- P2.58A UDC observation repair: `H0_IMPLEMENTED_AND_STATIC_VERIFIED`; exact
  target membership and symlink identity replace global singleton cardinality,
  the stock two-UDC topology is an executable semantic fixture, and DWC3
  success starts one fresh five-second UDC dwell. The 60-module plan,
  checkpoint ABI, and kernel patch remain byte-identical to P2.57.

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
P2.57 proves the child bind but not the queued work's completion. The source
path establishes that UDC creation is scheduled automatically; it does not
make the child bind symlink a completion fence.

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

P2.43 resolves the direct dependency mismatch behind that boundary.
`af20000.rsc` is the display RSC, while the apps-RSC/GCC chain uses
`17a00000.rsc`. That replacement remains correct for reaching GCC.

P2.55/P2.56 later expose one indirect dependency that P2.43 did not include.
The USB-required `mc_virt` interconnect provider requires both apps and display
BCM voters unless the runtime `PART_DISPLAY` subset disables the latter. The
display voter is populated only after `af20000.rsc` probes, and that RSC is
held behind the omitted `dispcc-waipio.ko` clock supplier. Therefore the
earlier statement that the display module was irrelevant to the complete USB
chain is retired. The bounded correction adds the one stock clock module and
observes the display-clock/RSC/voter chain immediately before mc_virt; it does
not add a display stack or restore the old display-RSC gate ahead of the
apps-RSC/GCC chain. This is a strong static hypothesis pending a later live
repair result, not a permanent root-cause verdict.

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

## P2.57-P2.58A DWC3-To-UDC Frontier

P2.57 advances the direct-PID1 live frontier through the SSUSB parent and
DWC3 child. The retained result ends with DWC3 success at `0x86` and UDC-gate
`ETIMEDOUT` at `0x87`.

The gate's exact implementation counts all non-dot entries in
`/sys/class/udc` and passes only for `entries == 1 && exact == 1`. This is
incompatible with the stock-observed and candidate-compiled topology:
`CONFIG_USB_DUMMY_HCD=y` normally publishes `dummy_udc.0` alongside
`a600000.dwc3`. The desired two-entry state fails the predicate. P2.57
therefore does not establish that the exact DWC3 UDC was absent.

Exact FYG8 source shows that child role-switch setup queues
`__dwc3_set_mode()` on `system_freezable_wq`. The DWC3 probe can return and
publish its bind symlink before that worker calls `dwc3_gadget_init()` and
`usb_add_gadget()`. Gadget-init failure logs an error but does not unbind the
core.

The P2.57 runtime also has no per-gate timestamp or UDC-specific deadline. A
late SSUSB bind during classifier grace activates a zero-wait downstream
drain.

P2.58A repairs both observation defects without changing the kernel contract.
It accepts the exact target plus unrelated peers, validates the target symlink
and basename, and gives only the DWC3-to-UDC boundary a fresh five-second
read-only dwell. The semantic oracle requires
`dummy_udc.0 + a600000.dwc3` to pass and rejects target absence, duplicate
target model input, wrong type, and wrong identity. The exact P2.57 plan,
checkpoint, and kernel patch receipts are pinned byte-for-byte; two independent
static AArch64 userspace links are reproducible.

This remains H0 evidence. A linked candidate audit must still prove reuse of
the exact qualified kernel Image before packaging. If a future corrected dwell
still fails, instrument only role-work entry and the PM/reset/gadget-init
return codes. Do not add modules, force role, or create configfs state.

## P2.76-P2.78 Post-Bind Frontier

P2.76 later proves the exact E3 path through configfs gadget construction,
`ttyGS0`, pre-bind banner queue, exact real UDC membership, and exact UDC bind.
It then times out at stage `0x8f` before exact `configured` plus `high-speed`.
The candidate boots without a boot loop, exact rollback and final health pass,
and the transaction closes. No host ACM bytes are accepted.

P2.77 rules out a direct external firmware-file dependency in the exact
60-module closure and establishes an asynchronous boundary between the
DWC3-MSM parent role callback and its queued peripheral-start work. It also
proves that stage `0x8e` includes a synchronous initial DWC3 pull-up request,
core soft reset, and RUN_STOP request. It does not prove host attach or
enumeration.

P2.78 corrects one stronger reading of the role evidence. The exact runtime
writes `peripheral` only when the first parent-mode read is `none` or `host`.
If it already reads `peripheral`, stage `0x8d` skips `mode_store()` and passes
after exact UDC membership. Exact FYG8 `mode_show()` reflects
`vbus_active`/`id_state`, not `drd_state`, `in_device_mode`, or completion of
the newly queued `sm_work`. P2.76 therefore does not prove that the explicit
forced-role bypass actually executed.

The P2.60 source contract proves the write token exists but not which runtime
branch takes it. The generic-arm64 P2.70 QEMU harness intentionally replaces
the Qualcomm role/UDC boundary. It remains authoritative for generic configfs
and ACM behavior but cannot close this semantic gap.

The exact stock rc remains a normal configfs composition with the UDC write
last. It contains no parent-mode, `dr_mode`, or `usb_role` write. Stock reaches
peripheral role through the Max77705/PDIC and notifier chain. That automatic
chain is not required if the explicit parent-mode callback is proved to run
and settle; P2.76 simply did not establish that precondition.

The exact initial UDC bind already traverses DWC3 core soft reset and RUN_STOP.
The generic UDC `soft_connect` attribute accepts `connect`/`disconnect`, but
its store callback discards the underlying reconnect return code. A successful
write is therefore non-proof. Treat a disconnect/reconnect only as a later,
isolated recovery experiment after state capture, not the next blind fix.

The next bounded discriminator records:

```text
initial parent mode
explicit role-write attempted/result
final parent mode
final UDC state/current_speed
optional one-shot DWC3 link_state
optional exact DWC3-MSM IPC marker bitmap
```

At the host, the P2.74 sidecar must produce a durable armed receipt after both
kernel and udev sources are live. Optional bounded usbmon can enrich reset and
descriptor analysis when attended root access is available, but kernel/udev
events remain the primary attach discriminator. Odin success is only a
physical-path positive control because Download mode uses different USB
firmware and controller state.

Do not add firmware, Max77705 modules, Android gadget daemons, a larger
composition, or a soft-connect retry before this discriminator. The current
open coordinates are:

```text
role write skipped
role write queued but parent work incomplete
parent started but host saw no attach
host began enumeration but reset/descriptors failed
```
