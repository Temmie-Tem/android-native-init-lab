# Native Init V667 cnss2/WLAN-PD Notifier Classifier Report

- date: `2026-05-24 KST`
- status: `host-only-pass` plus current device read-only capture
- script: `scripts/revalidation/native_wifi_cnss2_pd_notifier_classifier_v667.py`
- plan evidence: `tmp/wifi/v667-cnss2-pd-notifier-plan/`
- host-only evidence: `tmp/wifi/v667-cnss2-pd-notifier-classifier/`
- current read-only evidence: `tmp/wifi/v667-cnss2-pd-notifier-current-readonly-plus/`
- decision: `v667-cnss2-pd-notifier-gap-classified`

## Scope

V667 classifies the gap left by V666. V666 proved private property/runtime,
service `74`, `vndservicemanager`, and fresh `cnss-daemon` retry surfaces, but
still did not reach WLFW service `69`, BDF download, firmware-ready, or `wlan0`.

V667 does not write sysfs, open `esoc0`, start daemons, start service-manager,
start Wi-Fi HAL, scan/connect, run DHCP, change routes, or perform an external
ping.

## Result

V667 host-only classification passed:

| key | value |
| --- | --- |
| decision | `v667-cnss2-pd-notifier-gap-classified` |
| pass | `True` |
| device_commands_executed | `False` |
| device_mutations | `False` |
| wifi_bringup_executed | `False` |
| external_ping_executed | `False` |

Current device read-only capture also passed:

| key | value |
| --- | --- |
| decision | `v667-cnss2-pd-notifier-gap-classified` |
| pass | `True` |
| device_commands_executed | `True` |
| device_mutations | `False` |
| wifi_bringup_executed | `False` |
| external_ping_executed | `False` |

## V666 Timeline Classification

The V666 evidence is positive through service-notifier `180/74`:

| marker | count | first timestamp |
| --- | --- | --- |
| QRTR readiness RX | `1` | `190.841403` |
| QRTR readiness TX | `1` | `193.359020` |
| `sysmon-qmi` | `4` | `193.360146` |
| service-notifier `180` | `1` | `194.775148` |
| service-notifier `74` | `1` | `194.775328` |
| `cnss-daemon` netlink | `10` | `195.195884` |
| `cnss-daemon` `cld80211` | `4` | `195.195971` |
| `cnss-daemon` binder transaction `-22` | `1` | `195.360586` |

But the expected cnss2/WLAN-PD progression markers are absent:

| marker | count |
| --- | --- |
| cnss2/icnss runtime marker | `0` |
| cnss2 server-arrive marker | `0` |
| cnss2 `pd_notifier` / WLAN-PD marker | `0` |
| cnss2/QCA6390 power-on marker | `0` |
| PCIe/MHI runtime marker after service `74` | `0` |
| QMI server connected | `0` |
| WLFW start | `0` |
| WLFW service `69` | `0` |
| BDF `regdb` | `0` |
| BDF `bdwlan` | `0` |
| WLAN firmware ready | `0` |
| `wlan0` | `0` |

Key deltas:

| delta | ms |
| --- | --- |
| service `180` to service `74` | `0.18` |
| service `74` to `pm_qos` warning | `4.815` |
| service `74` to `cnss-daemon` netlink | `420.556` |
| service `74` to cnss2 server-arrive | `None` |
| service `74` to cnss2 `pd_notifier` | `None` |
| service `74` to cnss2 power-on | `None` |
| service `74` to WLFW | `None` |

## Current Read-only Surface

The current post-cleanup native state confirms the relevant platform surfaces
exist, but they are not actively progressed after the V666 cleanup reboot:

| surface | observation |
| --- | --- |
| `/sys/bus/platform/drivers/icnss` | present and bound to `18800000.qcom,icnss` |
| `/sys/bus/platform/devices/18800000.qcom,icnss` | present with driver, `ramdump`, power, wakeup, and `of_node` entries |
| `/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390` | present with `of_node`, power, and uevent entries |
| `/sys/class/net/wlan0` | absent |
| modem/adsp/slpi/cdsp/esoc0 subsystem states | `OFFLINING` in current idle state after cleanup reboot |

Filtered current dmesg shows early boot `icnss` platform probe and PCIe setup
surface, but no post-service-notifier WLFW/BDF/`wlan0` progression.

## Interpretation

V667 separates two things that were previously easy to conflate:

```text
userspace/QRTR-visible service-notifier 180/74 publication
  !=
cnss2 kernel WLAN-PD callback and QCA6390 power/WLFW progression
```

The evidence says V666 reached service-notifier `180/74`, but no cnss2
`pd_notifier`, QCA6390 power-on, PCIe/MHI progression, WLFW service `69`, BDF,
firmware-ready, or `wlan0` marker followed. Therefore another binder-only
`cnss-daemon` retry is unlikely to be the shortest next step.

## Next Gate

Plan V668 around the actual kernel progression gap:

- capture richer read-only cnss/icnss/QCA6390 sysfs attributes before and
  during the known service `74` positive window;
- keep service `74` gate if a live window is needed, but add focused cnss2
  marker capture around the gate;
- classify whether the missing edge is `pd_notifier` callback, QCA6390 power,
  PCIe/MHI, WLFW QRTR service `69`, or firmware/BDF download;
- continue blocking Wi-Fi HAL, scan/connect, DHCP, routes, credentials, and
  external ping until WLFW/BDF/`wlan0` evidence advances.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss2_pd_notifier_classifier_v667.py
python3 scripts/revalidation/native_wifi_cnss2_pd_notifier_classifier_v667.py --out-dir tmp/wifi/v667-cnss2-pd-notifier-plan plan
python3 scripts/revalidation/native_wifi_cnss2_pd_notifier_classifier_v667.py --out-dir tmp/wifi/v667-cnss2-pd-notifier-classifier run
python3 scripts/revalidation/native_wifi_cnss2_pd_notifier_classifier_v667.py --out-dir tmp/wifi/v667-cnss2-pd-notifier-current-readonly-plus --capture-current-readonly run
git diff --check
```

The resource-safe changed-file secret scan passed over only the V667 script and
documentation changes.
