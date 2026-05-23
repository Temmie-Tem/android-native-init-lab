# Native Init V702 cnss2 Focus Surface Classifier Report

- date: `2026-05-24 KST`
- status: `host-only-pass`; Wi-Fi external ping is **not** complete
- classifier: `scripts/revalidation/native_wifi_cnss2_focus_surface_classifier_v702.py`
- evidence: `tmp/wifi/v702-cnss2-focus-surface-classifier/`
- decision: `v702-qca6390-platform-binding-gap-classified`

## Scope

V702 consumed existing V700/V701 evidence only. It did not contact the device,
mount filesystems, start daemons or service managers, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP, change routes, ping externally, write
sysfs/debugfs, or write boot images/partitions.

## Result

| check | result |
| --- | --- |
| V700/V701 input readiness | pass |
| cnss2 focus capture completeness | pass |
| `icnss` platform driver bound | finding |
| `qca6390` platform node visible | finding |
| `qca6390` driver symlink visible | no |
| `wlan0` and debug ICNSS visible | no |
| WLFW/BDF/`wlan0` progression | still zero |

## Key Evidence

Focus capture phases were complete:

```text
service74_open: icnss_driver=1 icnss_device=1 qca6390_device=1 net_class=1 wlan0=0 debug_icnss=0 value_captures=8
window:         icnss_driver=1 icnss_device=1 qca6390_device=1 net_class=1 wlan0=0 debug_icnss=0 value_captures=8
```

The `icnss` platform driver is bound:

```text
/sys/bus/platform/drivers/icnss:
  uevent
  bind
  unbind
  18800000.qcom,icnss

/sys/bus/platform/devices/18800000.qcom,icnss:
  uevent wakeup of_node iommu_group power driver driver_override subsystem ramdump modalias
```

The `qca6390` platform node is visible but has no `driver` entry:

```text
/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390:
  uevent of_node power driver_override subsystem modalias
```

Power/runtime values:

```text
icnss power/control=auto
icnss power/runtime_status=unsupported
qca6390 power/control=auto
qca6390 power/runtime_status=unsupported
```

Missing surfaces:

```text
/sys/class/net/wlan0: No such file or directory
/sys/kernel/debug/icnss: No such file or directory
WLFW marker=0
BDF marker=0
wlan0 marker=0
```

## Interpretation

V702 narrows the blocker further:

- the `icnss` parent platform driver is present and bound;
- the `qca6390` child/platform node is present;
- the captured `qca6390` node is not driver-bound during the provider-first
  retry window;
- there is no `wlan0`, debug ICNSS, WLFW, or BDF progression.

The next useful question is not scan/connect or Wi-Fi HAL. It is whether
Android shows a different `qca6390`/`icnss` binding surface after normal boot
and, if so, which Android init/service/kernel event causes the delta.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_cnss2_focus_surface_classifier_v702.py

python3 scripts/revalidation/native_wifi_cnss2_focus_surface_classifier_v702.py \
  --out-dir tmp/wifi/v702-cnss2-focus-surface-plan-check plan

python3 scripts/revalidation/native_wifi_cnss2_focus_surface_classifier_v702.py \
  --out-dir tmp/wifi/v702-cnss2-focus-surface-classifier run
```

Results:

```text
v702-cnss2-focus-surface-classifier-plan-ready
v702-qca6390-platform-binding-gap-classified
```

## Next Gate

Plan V703 as Android-vs-native qca6390/icnss binding reference comparison:

- capture Android `/sys/bus/platform/drivers/icnss`;
- capture Android `18800000.qcom,icnss` and `a0000000.qcom,cnss-qca6390`
  directory/link/value surfaces;
- compare them against the V700 native focus capture;
- do not write `bind`/`unbind`, start Wi-Fi HAL, scan/connect, DHCP,
  credentials, or external ping until the delta is proven.
