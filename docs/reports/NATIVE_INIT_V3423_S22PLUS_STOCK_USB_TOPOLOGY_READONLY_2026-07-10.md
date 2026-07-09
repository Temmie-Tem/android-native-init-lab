# V3423 S22+ Stock USB Topology Read-Only Capture

## Verdict

`PASS-STOCK-TOPOLOGY-PARTIAL; DWC3 AND MAX77705 TYPE-C LIVE-BOUND; ROLE PROPAGATION UNVERIFIABLE`.

The operator-requested normal Android reboot completed before this unit. It
restored the malformed `/dev/null` baseline to character device `1:3`, mode
`0666`, size zero, with SELinux label `u:object_r:null_device:s0`. Android then
reached boot-complete with the exact FYG8 identity, Magisk root, and the pinned
known-booting boot SHA256:

```text
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

After that reboot, the V3423 collector performed only read operations. The
collector itself did not flash, reboot, insert a module, control a service,
write sysfs/configfs, or write a partition.

## Artifacts

```text
workspace/public/src/scripts/revalidation/s22plus_stock_usb_topology_readonly.py
tests/test_s22plus_stock_usb_topology_readonly.py
docs/module-map/s22plus-fyg8/stock-usb-runtime-topology.json
workspace/private/runs/s22plus_stock_usb_topology_readonly_20260709T232540Z/
```

The published JSON is serial-redacted. The private command capture is retained
for audit but is also redacted before disk write. The static module-map
generator preserves this live sidecar without incorporating it into the
firmware-derived artifact manifest.

## Live Findings

The stock Android path is functionally present:

```text
host USB ID                         04e8:6860
USB connected/configured           true/true
Type-C mode                         UFP
power role                          sink
data role                           device
supported modes                     dual
sys.usb.controller                  a600000.dwc3
parent platform driver              msm-dwc3
child platform driver               dwc3
ssusb role-switch object            observed
dwc3 role-switch object             observed
ssusb current role                   device
UDC state                            configured
gadget UDC                           a600000.dwc3
Type-C port provider                 max77705-usbc
Type-C data/power/port roles         device/sink/dual
DR-daemon/adbd baseline              running
```

The host-observed interface set was
`:060101:020201:0a0000:ff4003:ff4201:`. The live `/proc/modules` capture also
showed `dwc3_msm`, `sec_log_buf`, and `sec_debug` loaded.

This establishes the stock `a600000.ssusb -> a600000.dwc3` device path as
`LIVE_BOUND`, both role-switch objects as `LIVE_OBSERVED`, and the live Type-C
`port0` provider as `max77705-usbc`:

```text
/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0
/sys/bus/platform/drivers/max77705-usbc
```

It does not by itself prove the callback/notifier path that propagates a
Max77705 role event into the `msm-dwc3` role switch.

## Observation Boundary

The initial Android shell-domain reads were denied for extcon, Type-C, UDC,
role-value, and gadget-UDC surfaces. The collector was then tightened to use
Magisk `su -c` for those same fixed read-only operations. The final capture has
no read denials and records all of these live values.

The visible extcon class contains only these providers:

```text
soc:qcom,msm-ext-disp extcon0
soc:qcom,msm-ext-disp extcon1
88e0000.qcom,msm-eud extcon2
```

The visible `a600000.ssusb` supplier links include clocks, GDSC,
interconnects, EUD, interrupt-controller, and regulator suppliers. No direct
Max77705 supplier link was observed. The Type-C class independently proves the
Max77705 port provider, but neither the extcon list nor the devlinks prove how
that provider reaches the DWC3 role callback. Notifier and role-switch consumer
relationships need not appear as device links.

Therefore these conclusions remain explicit:

```text
stock_dwc3_device_path = LIVE_BOUND
role_switch_objects    = LIVE_OBSERVED
max77705_typec_port    = LIVE_BOUND
max77705_to_dwc3_role_propagation = UNVERIFIABLE
extcon_attachment      = UNVERIFIABLE
direct_pid1_path       = UNVERIFIABLE
```

## Collector Correction

The first collector invocation stopped before running any device command: it
redacted the ADB serial before using it for target selection. Selection now
keeps the raw serial only in memory and redacts command arguments and outputs
before persistence. A second parser correction accepts the `dumpsys usb`
`key :value` form and falls back to the observed `of_node` symlink when needed.
The final collector uses 25 fixed read-only commands, statically rejects shell
metacharacters in root-read commands, and passed all required stock checks.

## Validation

```text
collector fixed-device-command contract = PASS
collector unit tests                     = 6/6 PASS
collector/map/O2 regression tests         = 25/25 PASS
exact FYG8/Magisk boot SHA read           = PASS
published/private serial leakage scan     = PASS
result                                    = pass-stock-topology-partial
```

## Next Bound

The next host-only discriminator is deeper static RE of the exact FYG8
`dwc3-msm` and `max77705*` modules plus the matching DT nodes. It must identify
extcon/notifier consumers and producers, role callbacks, and any phandle wiring
without converting symbol-name proximity into a proven runtime edge. The live
sidecar then supplies the board-specific bound-state half of that comparison.

O0 remains the first functional control-plane proof: a framed, sequenced
`/dev/ttyGS0` to host `/dev/ttyACM0` roundtrip with bounded DR-daemon ownership
handoff and restoration. This topology capture does not itself satisfy O0.
