# Native Init v279 CNSS QCA6390 Start-Only Delta Report

## Summary

- status: PASS
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_cnss_qca6390_start_delta_observer.py`
- evidence: `tmp/wifi/v279-cnss-qca6390-start-delta-live-20260519-114525/`
- decision: `cnss-qca6390-no-driver-delta`
- daemon execution: bounded CNSS start-only through existing guarded runner
- packet transmission: none
- QMI payload: none
- sysfs writes: none from the observer

v279 ran the approved bounded CNSS start-only path and captured QCA6390/WLAN
state before and after. The daemon start-only runner passed and postflight was
clean, but QCA6390 driver-link and WLAN module-parameter state did not change.

## Live Findings

| field | before | after |
| --- | --- | --- |
| QCA6390 driver link | absent | absent |
| `wlan*` netdev | absent | absent |
| wiphy | absent | absent |
| Wi-Fi rfkill | absent | absent |
| WLAN param `fwpath` | empty | empty |
| WLAN param `country_code` | `(null)` | `(null)` |
| WLAN param `con_mode` | `0` | `0` |
| delta count | `0` | `0` |

Nested start-only runner result:

- decision: `start-only-pass`
- reason: `observed-until-timeout-clean-stop`
- daemon_start_executed: `True`
- postflight: clean

## Interpretation

- The v261 guarded CNSS start-only primitive remains safe: the helper can start,
  observe, stop, reap, and leave no target process behind.
- Start-only alone does not bind the QCA6390 platform node, does not change the
  selected WLAN module parameters, and does not expose `wlan*`, wiphy, or Wi-Fi
  rfkill readiness surfaces.
- The current blocker is therefore not simply “run `cnss-daemon` briefly”. The
  gap is likely earlier/lower in platform-driver lifecycle, device-tree/driver
  matching, or missing runtime control/event path. QMI payloads remain blocked.

## Guardrails Preserved

- no QRTR nameservice packet transmission
- no QMI request payload
- no Wi-Fi scan/connect/link-up
- no credentials, DHCP, routing, or Internet-facing exposure
- no `cnss_diag`, HAL, supplicant, wificond, hostapd, or hostapd-like service
- no ICNSS bind/unbind, rfkill unblock, driver override, recovery, ramdump, or
  assert controls
- no firmware path mutation, Android partition write, reboot, or remount

## Validation

Static:

- `python3 -m py_compile scripts/revalidation/wifi_cnss_qca6390_start_delta_observer.py scripts/revalidation/wifi_cnss_start_only_runner.py scripts/revalidation/wifi_qca6390_driver_param_classifier.py scripts/revalidation/a90ctl.py`: PASS
- `git diff --check`: PASS

Plan/preflight:

- `wifi_cnss_qca6390_start_delta_observer.py ... plan`: PASS,
  `cnss-qca6390-start-delta-plan-ready`
- `wifi_cnss_qca6390_start_delta_observer.py ... preflight`: PASS,
  `cnss-qca6390-start-delta-preflight-ready`

Live:

```bash
python3 scripts/revalidation/wifi_cnss_qca6390_start_delta_observer.py \
  --out-dir tmp/wifi/v279-cnss-qca6390-start-delta-live-20260519-114525 \
  --max-runtime-sec 10 \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

Result:

- decision: `cnss-qca6390-no-driver-delta`
- pass: `True`
- reason: `bounded start-only completed safely with no QCA driver or WLAN parameter delta`

Postflight:

- `version`: `A90 Linux init 0.9.60 (v261)`
- `status`: shell responsive, `selftest fail=0`, `netservice: disabled tcpctl=stopped`
- `pidof cnss-daemon`: rc `1`, process absent
- `/proc/net/dev`: `ncm0` present; no `wlan*` interface observed

## Note

One first postflight attempt used parallel `a90ctl` commands and hit the known
single-client bridge limitation. The same checks were then rerun sequentially
and passed.

## Next Step

v280 should avoid repeating the same start-only observation. Better candidates:

1. no-start CNSS/QCA6390 source and sysfs expectation comparison for why
   `qcom,cnss-qca6390` remains unbound;
2. read-only dmesg/kmsg/WLAN driver log extraction if accessible;
3. a separately planned QRTR/WLFW readback during start-only only if explicitly
   allowed and still without QMI payloads or Wi-Fi link actions.
