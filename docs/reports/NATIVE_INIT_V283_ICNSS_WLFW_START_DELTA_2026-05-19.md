# Native Init v283 ICNSS/WLFW Start-Only Delta Report

## Summary

- plan: `docs/plans/NATIVE_INIT_V283_ICNSS_WLFW_START_DELTA_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_icnss_wlfw_start_delta_observer.py`
- evidence:
  `tmp/wifi/v283-icnss-wlfw-start-delta-live-20260519-123206/`
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- decision: `icnss-wlfw-start-no-readiness-delta`
- result: PASS

v283 ran a bounded CNSS start-only observation and compared ICNSS/WLFW
readiness surfaces before and after. The daemon was observable and reaped, but
there was no dmesg readiness delta, no sysfs/debugfs readiness candidate delta,
and no WLAN netdev/wiphy exposure.

## References Used

- Qualcomm ICNSS source shows firmware-ready indication handling and host-driver
  probe gating:
  https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/icnss.c
- Qualcomm ICNSS QMI source shows WLFW service connection state logging:
  https://android.googlesource.com/kernel/msm/+/79a5a3af469e5d38c649dbe3dc7340d96990fd68/drivers/soc/qcom/icnss_qmi.c
- Qualcomm ICNSS devicetree binding describes WLAN FW communication over QMI:
  https://android.googlesource.com/kernel/msm/+/157ab4a1b7d2bf3275a20ee90d855bec184d742e/Documentation/devicetree/bindings/cnss/icnss.txt
- Linux debugfs documentation is used to keep debugfs as non-stable,
  no-mount/no-write evidence unless explicitly planned:
  https://docs.kernel.org/filesystems/debugfs.html

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_icnss_wlfw_start_delta_observer.py \
  scripts/revalidation/wifi_icnss_wlfw_readiness_surface.py \
  scripts/revalidation/wifi_cnss_start_only_runner.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Result: PASS.

Plan gate:

```text
decision: icnss-wlfw-start-delta-plan-ready
pass: True
```

Preflight:

```text
decision: icnss-wlfw-start-delta-preflight-ready
pass: True
```

Live bounded run:

```text
decision: icnss-wlfw-start-no-readiness-delta
pass: True
reason: bounded start-only completed safely with no ICNSS/WLFW readiness delta
```

## Start-Only Observation

| field | value |
| --- | --- |
| nested runner decision | `start-only-pass` |
| helper result | `start-only-pass` |
| helper reason | `observed-until-timeout-clean-stop` |
| daemon start executed | `True` |
| child started | `True` |
| observed pid/pgid | `1077` / `1077` |
| reaped | `True` |
| postflight safe | `True` |

The helper captured live `/proc/<cnss-daemon>/status` while the child was
running, then stopped and reaped the process group.

## Before/After Delta

| field | before | after |
| --- | --- | --- |
| dmesg readiness lines | `0` | `0` |
| sysfs readiness candidates | `13` | `13` |
| debugfs readiness candidates | `0` | `0` |
| WLAN netdev | `False` | `False` |
| wiphy | `False` | `False` |
| delta count | `0` | `0` |

Comparison:

- `readiness_delta=False`
- `dmesg_readiness_delta=False`
- `sysfs_candidate_delta=False`
- `debugfs_candidate_delta=False`
- `postflight_readiness_visible=False`
- `postflight_process_clean=True`

## Postflight

Postflight after the observer:

- `version`: `A90 Linux init 0.9.60 (v261)`
- `status`: PASS, shell responsive, selftest `fail=0`
- `run /cache/bin/toybox pidof cnss-daemon`: rc `1`, no target daemon
- `cat /proc/net/dev`: baseline interfaces only; `ncm0` present; no `wlan*`

## Interpretation

- The validated start-only primitive can execute and cleanly reap
  `cnss-daemon`, but it does not create visible ICNSS/WLFW readiness state.
- No current no-scan evidence shows that `cnss-daemon -n -l` alone reaches the
  kernel firmware-ready path.
- Repeating the same serial-only start-only test is unlikely to add new
  evidence.
- If more live observation is needed, the next useful step should be a concurrent
  side-channel design using the already built broker/NCM control path, so that
  readiness/state probes can run while the serial command is occupied by the
  start-only helper.

## Guardrails Observed

- no QRTR nameservice packet transmission from the observer
- no direct QMI request payload from the observer
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no `cnss_diag`, HAL, supplicant, wificond, or hostapd
- no ICNSS bind/unbind, `driver_override`, rfkill unblock, recovery, ramdump, or
  assert controls
- no debugfs mount or write
- no reboot or remount

## Next Work

v284 should not be another serial-only repetition. Recommended next item:

```text
v284 CNSS concurrent side-channel observer feasibility
```

Scope:

- use NCM/tcpctl or harness broker as a second control path;
- run the bounded start-only helper on serial;
- concurrently sample read-only ICNSS/WLFW state and dmesg over the second path;
- keep QMI payloads, QRTR nameservice packet transmission, scan/connect/link-up,
  rfkill writes, ICNSS bind/unbind, and debugfs writes blocked.
