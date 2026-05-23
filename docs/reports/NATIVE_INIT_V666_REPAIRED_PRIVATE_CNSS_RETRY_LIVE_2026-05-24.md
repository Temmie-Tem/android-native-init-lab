# Native Init V666 Repaired Private CNSS Retry Live Report

- date: `2026-05-24 KST`
- status: `live-pass`; Wi-Fi external ping is **not** complete
- helper: `a90_android_execns_probe v109`
- runner: `scripts/revalidation/native_wifi_repaired_private_cnss_retry_v666.py`
- live evidence: `tmp/wifi/v666-repaired-private-cnss-retry-live/`
- decision: `v666-repaired-private-cnss-retry-binder-loop-persists`

## Scope

V666 combines the V665 repaired private property/runtime surface with the
V655-style service `74` gated `vndservicemanager` readiness and fresh
`cnss-daemon` retry path.

The live proof remains below Wi-Fi bring-up. It does not start the Wi-Fi HAL,
does not scan, does not connect or link up, does not run DHCP, does not change
routes, and does not perform an external ping.

## Prerequisites

Current-boot prerequisites were refreshed before V666 live:

| prerequisite | result |
| --- | --- |
| V641 clean DSP one-shot refresh | pass |
| V401 SELinuxfs runtime mount surface | pass |
| V490 native SELinux policy-load proof | pass |
| V666 preflight | ready |

Helper validation:

```text
helper sha256: eda3e88405d15cfa2b12ef3252cef3ff25ba23aae69aeb5075700fa147150030
```

## Live Result

The bounded live proof passed its safety contract:

| key | value |
| --- | --- |
| decision | `v666-repaired-private-cnss-retry-binder-loop-persists` |
| pass | `True` |
| device_mutations | `True` |
| daemon_start_executed | `True` |
| wifi_bringup_executed | `False` |
| external_ping_executed | `False` |
| private_runtime_ready | `True` |

Reboot cleanup completed successfully. The reboot command itself lost the
`A90P1 END` marker because the device restarted before the serial frame ended,
but the wrapper observed the device after reboot and classified cleanup as
healthy:

| cleanup key | value |
| --- | --- |
| version_seen | `True` |
| status_healthy | `True` |
| wait_sec | `32.337` |

## Positive Evidence

V666 proves that the private property/runtime surface is not the current
blocker:

| key | value |
| --- | --- |
| context_dev_properties_exists | `1` |
| context_dev_properties_access_r | `1` |
| context_dev_properties_access_x | `1` |
| property_service_shim_started | `1` |
| property_service_socket | `/dev/socket/property_service` |
| property_service_shim_postflight_safe | `1` |
| property_service_shim_request_count | `1` |

The lower modem/QRTR path also reached the expected pre-WLFW markers:

| marker | value |
| --- | --- |
| `mss_after_holder` | `ONLINE` |
| `mss_after_companion` | `ONLINE` |
| QRTR readiness RX | `1` |
| QRTR readiness TX | `1` |
| `sysmon-qmi` count | `4` |
| service-notifier count | `2` |
| service-notifier `180` | `1` |
| service-notifier `74` | `1` |

The service-manager/CNSS retry gate also executed as intended:

| gate | value |
| --- | --- |
| service `74` baseline count | `0` |
| service `74` final count | `1` |
| service `74` status | `open` |
| service `74` wait_ms | `16` |
| `vndservicemanager` observable | `1` |
| `vndservicemanager` ready | `1` |
| initial `cnss-daemon` observable | `1` |
| initial cleanup safe | `1` |
| retry `cnss-daemon` observable | `1` |
| retry postflight safe | `1` |

## Remaining Blocker

The retry still does not advance into WLFW, BDF download, firmware-ready, or
`wlan0` creation:

| marker | count |
| --- | --- |
| `cnss-daemon` netlink | `10` |
| `cnss-daemon` `cld80211` | `4` |
| binder ioctl unsupported | `2` |
| binder transaction failed | `1` |
| `cnss-daemon` binder transaction failed | `1` |
| kernel warning | `1` |
| QMI server connected | `0` |
| WLFW start | `0` |
| WLFW service request | `0` |
| WLAN-PD | `0` |
| BDF `regdb` | `0` |
| BDF `bdwlan` | `0` |
| WLAN firmware ready | `0` |
| `wlan0` | `0` |

The single kernel warning is the known `pm_qos_add_request` warning class seen
near service `74` in earlier evidence. V666 keeps it visible as an unresolved
attribution item instead of treating it as harmless.

## Interpretation

V666 lowers the likelihood that the blocker is private property path
materialization, private `/dev/__properties__` visibility, service `74`
publication, or `vndservicemanager` readiness. Those surfaces are now positive
in the same bounded run.

The remaining gap is after service-notifier `180/74` and before WLFW service
`69`, BDF download, firmware-ready, and `wlan0`. Fresh `cnss-daemon` retry still
reaches netlink/`cld80211`, but the run remains stuck with vendor binder
transaction `-22` and no WLFW markers.

## Follow-up Hypothesis

The current working hypothesis is that WLFW service `69` is published only
after the WLAN protection domain path causes the cnss2 kernel driver to power
on the QCA6390 WLAN coprocessor. Under this model, observing service-notifier
`180` from userspace does not prove that cnss2's internal `pd_notifier`
callback fired or that QCA6390 power-on progressed.

The next bounded gate should therefore move before another binder repair retry
and classify cnss2/WLAN-PD kernel progression:

```text
modem ONLINE
  -> service-locator can resolve WLAN-PD location
  -> service-notifier 180/74 appear
  -> cnss2 pd_notifier callback should fire
  -> QCA6390 power-on / WLFW boot should begin
  -> WLFW service 69 should appear
  -> BDF download / fw_ready / wlan0 should follow
```

Because V666 is already consumed by this live proof, assign that classifier to
V667.

## Next Gate

Plan V667 as a read-only or start-only cnss2/WLAN-PD classifier with these
constraints:

- inspect service-notifier `180/74` timing against `cnss`, `cnss2`,
  `server_arrive`, `pd_notifier`, `power_on`, WLFW, and PCIe/MHI dmesg markers;
- read `/sys/bus/msm_subsys/devices/` modem-related state without changing it;
- capture `/sys/bus/platform/drivers/cnss2/` and matching device sysfs nodes;
- do not write subsystem state, do not open `esoc0`, do not start Wi-Fi HAL,
  do not scan/connect, do not run DHCP, and do not external ping.

Suggested approval phrase for the next live runner:

```text
approve v667 cnss2 pd-notifier firing check and modem subsys state read; no Wi-Fi HAL start, no scan/connect, no DHCP, no external ping
```
