# USB Subsystem

## Status

- FYG8 metadata closure: `STATIC_VERIFIED`.
- Stock Android DWC3/UDC/gadget path: `LIVE_BOUND` in V3420 recovery checks.
- Direct-PID1 module execution and bind sequence: `UNVERIFIABLE` after O3/O3F.

The current O3 minimal-ACM metadata plan contains 59 modules and
passes recursive hard dependency, softdep pre/post, stock-order, alias,
blocklist, and options parsing. This proves a static load plan only.

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
