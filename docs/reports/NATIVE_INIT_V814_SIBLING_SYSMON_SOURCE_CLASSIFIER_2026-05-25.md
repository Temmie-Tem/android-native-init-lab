# Native Init V814 Sibling Sysmon Source Classifier Report

## Result

- decision: `v814-source-routes-to-subsystem-sysmon-registration-snapshot`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_sibling_sysmon_source_classifier_v814.py`
- evidence: `tmp/wifi/v814-sibling-sysmon-source-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_sibling_sysmon_source_classifier_v814.py

python3 scripts/revalidation/native_wifi_sibling_sysmon_source_classifier_v814.py \
  --out-dir tmp/wifi/v814-sibling-sysmon-source-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_sibling_sysmon_source_classifier_v814.py run
```

V814 was host-only. It did not execute any device command.

## Evidence Summary

| Source | Anchors |
| --- | --- |
| `drivers/soc/qcom/service-notifier.c` | `service_notifier_new_server`, `send_notif_listener_msg_req`, `root_service_service_ind_cb`, `qmi_add_lookup`, `subsys_notif_register_notifier` |
| `include/soc/qcom/service-notifier.h` | `SERVREG_NOTIF_SERVICE_STATE_UP_V01`, `service_notif_register_notifier` |
| `drivers/soc/qcom/sysmon-qmi.c` | `sysmon_notifier_register`, `qmi_add_lookup`, `SSCTL_SERVICE_ID`, `sysmon_send_event`, `ssctl_new_server` |
| `drivers/soc/qcom/subsystem_restart.c` | `send_sysmon_notif`, `sysmon_send_event`, `qcom,sysmon-id`, `sysmon_notifier_register`, `sysmon_glink_register` |
| `include/linux/esoc_client.h` | `esoc_register_client_notifier`, `esoc_register_client_hook` |

## Classification

The source route matches the V813 evidence:

```text
subsystem registration / sysmon registration
  -> sysmon QMI lookup and subsystem event propagation
    -> service-notifier SERVREG listener registration/state indication
      -> service74/WLAN-PD/WLFW publication
```

So the next useful live step is not another userspace daemon, HAL, scan/connect,
or custom-kernel flash. It is a read-only snapshot of the stock-v724
subsystem/sysmon/service-locator registration surface that can explain why
native has `sysmon_modem` but lacks sibling sysmon and service74.

## Safety

- Host-only classifier; no device command executed.
- No custom kernel flash, boot image write, partition write, reboot, or
  bootloader handoff.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect/link-up, or
  credential use.
- No DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, driver override, or
  module load/unload.
- No Wi-Fi secret material was written to tracked output.

## Next

V815 should collect a read-only stock-v724 subsystem/sysmon/service-locator
registration snapshot before any new trigger. Candidate surfaces include
`/sys/bus/msm_subsys/devices/*`, subsystem names/states/crash counters,
available sysmon/service-notifier dmesg lines, service-locator/sysmon markers,
and read-only esoc metadata. It must still avoid `esoc0` open, subsystem state
writes, HAL, scan/connect, credentials, DHCP/routes, external ping, and custom
kernel flash.
