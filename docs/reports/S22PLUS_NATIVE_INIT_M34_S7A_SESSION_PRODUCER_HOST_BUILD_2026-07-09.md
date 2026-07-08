# S22+ M34 S7A Session-Producer Host Build

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: HOST BUILD COMPLETE. No live flash is authorized by this report.

## Boundary

This unit follows the consumed M34 S6 live gate and the read-only stock USB /
TypeC diff. It builds the next host-only S7A artifact; it does not flash,
reboot, write sysfs/configfs on a device, install a Magisk module, or touch any
partition.

## Candidate

S7A starts from S6:

- keep `ssusb/mode=peripheral`;
- keep the minimal ACM-only `ss_acm.0` configfs recipe;
- keep `soft_connect` disabled;
- add the stock max77705/PDIC/altmode session-producer module closure;
- add read-only TypeC/UDC snapshot markers before and after UDC bind.

Readback paths compiled into S7A:

```text
/sys/devices/platform/soc/a600000.ssusb/mode
/sys/devices/platform/soc/a600000.ssusb/speed
/sys/class/typec/port0/data_role
/sys/class/typec/port0/power_role
/sys/class/typec/port0/port_type
/sys/class/typec/port0-partner/uevent
/sys/class/udc/a600000.dwc3/state
/sys/class/udc/a600000.dwc3/current_speed
/sys/class/udc/a600000.dwc3/function
```

The firmware module filename is `qcom-i2c-pmic.ko`; stock `/proc/modules`
prints that module as `qcom_i2c_pmic`.

## Artifacts

Output directory:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_6/
```

Top-level manifest SHA256:

```text
fc61ca67c2d141e9e6a2e382c212fd8f06412ec0982367f8f89940cd49545a33
```

S7A hashes:

```text
AP.tar.md5  b533d8e218aa4842c941f86075ce770cf60a67a179939dd4d552d22767376267
boot.img    5e1a0758008651eb5a22b82fd91d4c2549ba756a4ed885779a0934688e129e49
/init       22e1f7e9346c61c876253a6e194d64d55adc3e24571ed2b10d76e4c09cef1914
modules     eb1ddfe7ac9a481b9dacae696c72b876e82d6e8ac4681772df825995a162001c
```

S7A Odin AP:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_6/S7A/odin4/AP.tar.md5
```

The AP contains exactly one Odin tar member, `boot.img.lz4`.

## Closure

S7A module count: `83`

S7A module-list size: `1340` bytes. The native-init parser buffer was expanded
from `1024` to `4096` bytes so the list cannot truncate.

New modules over S6:

```text
charger-ulog-glink.ko
altmode-glink.ko
qti-regmap-debugfs.ko
qcom-i2c-pmic.ko
sec_pm_log.ko
qcom-cpufreq-hw.ko
sched-walt.ko
kryo_arm64_edac.ko
memory_dump_v2.ko
sec_key_notifier.ko
sec_crashkey_long.ko
sec_debug_region.ko
sec_param.ko
sec_qc_dbg_partition.ko
sec_qc_summary.ko
sec_upload_cause.ko
sec_qc_upload_cause.ko
sec_qc_user_reset.ko
sec_qc_smem.ko
sec_qc_hw_param.ko
sb-core.ko
sec_pd.ko
sec-battery.ko
mfd_max77705.ko
spu_verify.ko
pdic_max77705.ko
max77705_charger.ko
max77705-fuelgauge.ko
```

Risk modules pulled by the full stock charger/fuelgauge dependency closure:

```text
memory_dump_v2.ko
sec_debug_region.ko
sec_param.ko
sec_qc_dbg_partition.ko
sec_qc_summary.ko
sec_upload_cause.ko
sec_qc_upload_cause.ko
sec_qc_user_reset.ko
```

This is intentionally recorded as manifest
`requires_s7a_specific_live_risk_review=true`. S7A is a correct full stock
closure build, not an automatically live-ready artifact.

## Validation

Commands passed:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py --force
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_s22plus_m34_runtime_gadget_split_build tests.test_s22plus_m34_s6_stock_softdep_live_gate
git diff --check
```

Unit tests:

```text
Ran 15 tests in 0.031s
OK
```

Negative string checks on S7A `/init`:

```text
high-speed absent
/sys/class/udc/a600000.dwc3/soft_connect absent
phase=ssusb_speed absent
```

## Next Gate

No S7A live flash is authorized. A live gate needs a fresh SHA-pinned
`AGENTS.md` exception for the exact S7A AP hash above and an explicit decision
about accepting the stock charger/fuelgauge-induced risk modules, or splitting
a narrower pre-charger S7A subcandidate before the full S7A artifact.
