# Native Init v281 ICNSS Probe Expectation Report

## Summary

- status: PASS
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_icnss_probe_expectation.py`
- evidence: `tmp/wifi/v281-icnss-probe-expectation/`
- decision: `icnss-core-bound-host-driver-waits-fw`
- packet transmission: none
- daemon execution: none
- QMI payload: none
- sysfs/control writes: none

v281 pivoted from the non-live CNSS2 model to the actual live ICNSS model. ICNSS
core is bound to `18800000.qcom,icnss`, WLAN host-driver sysfs surface exists,
and QCA6390 context is visible, but there is no firmware-ready/netdev/wiphy
readiness surface.

## Source Expectation

Primary sources used:

- Qualcomm ICNSS source: `icnss` platform driver, WLFW/QMI event handling,
  `icnss_register_driver()`, and host-driver probe delayed until firmware-ready
  or `SKIP_QMI`:
  https://android.googlesource.com/kernel/msm/+/c90c7feeca2f5839ad6824f816c0bd207602a2f4/drivers/soc/qcom/icnss.c
- Qualcomm SoC Kconfig: `ICNSS` and `ICNSS_QMI` roles in WLAN on/off control and
  PD restart notifications:
  https://android.googlesource.com/kernel/msm/+/15cf51a0f2ebde6529357685543e0b4170fb3b5c/drivers/soc/qcom/Kconfig
- Linux driver binding documentation:
  https://docs.kernel.org/driver-api/driver-model/binding.html

## Live Findings

| field | result |
| --- | --- |
| ICNSS compatible | `qcom,icnss` |
| ICNSS driver-device link | present |
| QCA6390 compatible | `qcom,cnss-qca6390` |
| QCA6390 driver link | absent |
| WLAN module sysfs | present |
| `wlan` in `/proc/modules` | absent |
| WLAN params | `fwpath=""`, `con_mode=0` |
| ICNSS params | `quirks=128`, `dynamic_feature_mask=1` |
| DT MSA memory indicators | `qcom,wlan-msa-memory` and `qcom,wlan-msa-fixed-region` present |
| `wlan*` netdev | absent |
| wiphy | absent |
| CNSS process table | clean |

Kernel config sample:

| key | value |
| --- | --- |
| `CONFIG_ICNSS` | `y` |
| `CONFIG_ICNSS_QMI` | `y` |
| `CONFIG_ICNSS_DEBUG` | `n` |
| `CONFIG_CNSS_UTILS` | `y` |
| `CONFIG_WLAN` | `y` |
| `CONFIG_QCA_CLD_WLAN` | `y` |
| `CONFIG_CNSS2` | `n` |

Kernel log read succeeded, but no current filtered ICNSS/WLFW/WLAN readiness
lines were present in the retained dmesg window.

## Interpretation

- The live kernel is using ICNSS, not CNSS2.
- QCA6390 being unbound is no longer the primary blocker by itself. In the ICNSS
  model, ICNSS core is the bound platform driver and the WLAN host driver
  surface can wait for firmware-ready/QMI state before probe creates netdev.
- The useful next evidence is not another generic daemon start-only run. It is a
  bounded, explicit observation of ICNSS/WLFW readiness state during start-only,
  or a read-only way to expose ICNSS internal state/debugfs without enabling
  Wi-Fi.

## Guardrails Preserved

- no daemon/service start
- no QRTR nameservice packet or QMI payload
- no Wi-Fi scan/connect/link-up
- no credentials, DHCP, routing, or Internet-facing exposure
- no `cnss_diag`, HAL, supplicant, wificond, or hostapd start
- no rfkill unblock, ICNSS bind/unbind, `driver_override`, recovery, ramdump, or
  assert controls
- no firmware path mutation, Android partition write, reboot, or remount

## Validation

Static:

- `python3 -m py_compile scripts/revalidation/wifi_icnss_probe_expectation.py scripts/revalidation/a90ctl.py`: PASS
- `git diff --check`: PASS

Live read-only:

```bash
python3 scripts/revalidation/wifi_icnss_probe_expectation.py \
  --out-dir tmp/wifi/v281-icnss-probe-expectation \
  run
```

Result:

- decision: `icnss-core-bound-host-driver-waits-fw`
- pass: `True`
- reason: ICNSS core is bound and WLAN host surface exists, but no
  firmware-ready/netdev surface is visible

Postflight:

- `version`: `A90 Linux init 0.9.60 (v261)`
- `status`: shell responsive, `selftest fail=0`, `netservice: disabled tcpctl=stopped`
- `pidof cnss-daemon`: rc `1`, process absent
- `/proc/net/dev`: `ncm0` present; no `wlan*` interface observed

## Next Step

v282 should plan an ICNSS/WLFW readiness-state observation:

- no-start first: identify safe read-only ICNSS debug/state surfaces, including
  whether debugfs can be mounted read-only or whether existing `/sys/kernel`
  links expose state;
- if no-start surfaces are insufficient, separately plan an explicit bounded
  start-only observation that captures ICNSS/QMI/WLFW readiness deltas without
  QMI request payloads, scan/connect/link-up, rfkill, or bind/unbind.
