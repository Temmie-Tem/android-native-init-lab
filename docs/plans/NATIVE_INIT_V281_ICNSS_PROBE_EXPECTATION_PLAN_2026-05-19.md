# Native Init v281 ICNSS Probe Expectation Plan

## Summary

- target: v281 read-only ICNSS source/sysfs probe expectation comparator
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_icnss_probe_expectation.py`
- packet transmission: none
- daemon execution: none
- QMI payload: none
- sysfs/control writes: none

v280 proved that the live kernel does not use the CNSS2 model: `CONFIG_CNSS2=n`
and no `cnss2` platform driver directory exists. v281 pivots to the actual live
model: `icnss` core driver bound to `18800000.qcom,icnss`, with WLAN host-driver
readiness depending on ICNSS state, WLFW/QMI readiness, and host driver
registration.

## References

- Qualcomm ICNSS source shows the `icnss` platform driver, WLFW/QMI event
  handling, `icnss_register_driver()`, and delayed host-driver probe until
  firmware-ready or `SKIP_QMI`:
  https://android.googlesource.com/kernel/msm/+/c90c7feeca2f5839ad6824f816c0bd207602a2f4/drivers/soc/qcom/icnss.c
- Qualcomm SoC Kconfig describes `ICNSS`, `ICNSS_QMI`, and the driver's role in
  WLAN on/off control and PD restart notifications:
  https://android.googlesource.com/kernel/msm/+/15cf51a0f2ebde6529357685543e0b4170fb3b5c/drivers/soc/qcom/Kconfig
- Linux driver binding documentation defines the sysfs driver/device binding
  evidence used by this comparison:
  https://docs.kernel.org/driver-api/driver-model/binding.html

## Scope

Read-only captures:

- ICNSS platform node, `uevent`, modalias, driver, and driver-device link
- ICNSS module parameters: `quirks`, `dynamic_feature_mask`
- QCA6390 device-tree context and driver-link state
- WLAN module surface and selected params: `fwpath`, `con_mode`
- ICNSS/QCA6390 devicetree resource presence, including MSA memory indicators
- selected config keys from `/proc/config.gz`
- filtered kernel log tail for ICNSS/WLFW/WLAN/QMI messages
- process table and WLAN readiness surfaces

## Decision Model

Expected likely decision:

```text
icnss-core-bound-host-driver-waits-fw
```

This means:

- ICNSS core is bound to `18800000.qcom,icnss`;
- QCA6390 context exists but has no independent `driver` link;
- WLAN module sysfs exists;
- no `wlan*` netdev or wiphy appears;
- source model says host-driver probe can wait for firmware-ready/QMI state.

Alternative decisions:

- `icnss-wlan-readiness-visible`: WLAN netdev/wiphy appeared.
- `icnss-qca6390-driver-bound-no-readiness`: QCA6390 gets a driver link but no
  netdev/wiphy.
- `icnss-core-present-no-host-readiness`: ICNSS exists but WLAN host-driver
  surface is incomplete.
- `icnss-probe-expectation-incomplete`: required read-only evidence is missing.

## Guardrails

v281 must not:

- start `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, or hostapd
- transmit QRTR nameservice packets or QMI request payloads
- perform Wi-Fi scan/connect/link-up/credential/DHCP/routing
- write to sysfs/control paths, including rfkill, ICNSS bind/unbind,
  `driver_override`, recovery, ramdump, or assert controls
- mutate firmware paths or Android partitions
- reboot or remount

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_icnss_probe_expectation.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Live read-only:

```bash
python3 scripts/revalidation/wifi_icnss_probe_expectation.py \
  --out-dir tmp/wifi/v281-icnss-probe-expectation \
  run
```

Postflight:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox pidof cnss-daemon || true
python3 scripts/revalidation/a90ctl.py cat /proc/net/dev
```

## Acceptance

- v281 starts no daemon and sends no packets.
- ICNSS source expectation is explicit in the manifest and report.
- ICNSS binding, WLAN host-driver surface, config, and log evidence are captured.
- postflight remains clean: no `cnss-daemon`, no `wlan*` interface.
