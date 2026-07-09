# USB Subsystem

## Status

- FYG8 metadata closure: `STATIC_VERIFIED`.
- Exact automatic role path: `ELF_SOURCE_DT_VERIFIED` in the deep USB RE.
- Stock Android DWC3/UDC/gadget and participating driver path: `LIVE_BOUND`.
- PDIC-to-Type-C-manager relay: `LIVE_OBSERVED`; the same-boot USB attach event
  through `usb_notifier_qcom` to DWC3 was `NOT_CAPTURED_THIS_BOOT`.
- Direct-PID1 module execution and bind sequence: `UNVERIFIABLE` after O3/O3F.

The current O3 minimal-ACM metadata plan contains 59 modules and
passes recursive hard dependency, softdep pre/post, stock-order, alias,
blocklist, and options parsing. This proves a static load plan only.

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

Current active work remains O0 stock `/dev/ttyGS0` to host `/dev/ttyACM0`, then
O1 stock-first-stage observation. No direct-PID1 USB candidate is authorized by
this map. The latest stock read-only evidence is maintained separately in
`stock-usb-runtime-topology.json`.
