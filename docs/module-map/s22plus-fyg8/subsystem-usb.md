# USB Subsystem

## Status

- FYG8 metadata closure: `STATIC_VERIFIED`.
- Exact automatic role path: `ELF_SOURCE_DT_VERIFIED` in the deep USB RE.
- Stock Android DWC3/UDC/gadget and participating driver path: `LIVE_BOUND`.
- PDIC-to-Type-C-manager relay: `LIVE_OBSERVED`; the same-boot USB attach event
  through `usb_notifier_qcom` to DWC3 was `NOT_CAPTURED_THIS_BOOT`.
- Direct-PID1 module execution and bind sequence: `UNVERIFIABLE` after O3/O3F.
- Direct-PID1 E2 source implementation: `H0_VERIFIED` by P2.41; live module
  execution, bind, child creation, and UDC remain unproved.

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

## Functional Gates

| Order | Gate | Provider | Required path | Direct-PID1 status |
|---:|---|---|---|---|
| 1 | `hwspinlock` | `qcom_hwspinlock` | `/sys/bus/platform/drivers/qcom_hwspinlock/soc:hwlock` | `UNVERIFIABLE` in direct PID1 |
| 2 | `smem` | `smem` | `/sys/bus/platform/drivers/qcom-smem/soc:qcom,smem` | `UNVERIFIABLE` in direct PID1 |
| 3 | `cmd-db` | `cmd_db` | `/sys/bus/platform/drivers/cmd-db/80860000.aop_cmd_db_region` | `UNVERIFIABLE` in direct PID1 |
| 4 | `rpmh` | `qcom_rpmh` | `/sys/bus/platform/drivers/rpmh/af20000.rsc` | `UNVERIFIABLE` in direct PID1 |
| 5 | `gcc-waipio` | `gcc_waipio` | `/sys/bus/platform/drivers/gcc-waipio/100000.clock-controller` | `UNVERIFIABLE` in direct PID1 |
| 6 | `ssusb` | `dwc3_msm` | `/sys/bus/platform/drivers/msm-dwc3/a600000.ssusb` | `UNVERIFIABLE` in direct PID1 |
| 7 | `dwc3-core` | built-in | `/sys/bus/platform/drivers/dwc3/a600000.dwc3` | `UNVERIFIABLE` in direct PID1 |
| 8 | `udc` | built-in | `/sys/class/udc/a600000.dwc3` | `UNVERIFIABLE` in direct PID1 |

A `finit_module` return code or `/proc/modules` name proves registration only.
The next gate advances only after its driver/device path exists. O3 PASS remains
a framed host/device ACM request-response plus device-reported bind state, not
enumeration or survival.

O0 stock control, O1.1 stock-first-stage control, O2 loader parity, the compact
retained carrier, E1A/E1B live foundations, and P2.41 E2 source implementation
are complete. The next unit is a separate reproducible Full-LTO build and
offline candidate closure. No direct-PID1 USB candidate is authorized by this
map. The latest stock read-only evidence is maintained separately in
`stock-usb-runtime-topology.json`.
