# Native Init V616 Post-Sibling-Sysmon Service-Notifier Classifier Report

- date: `2026-05-23 KST`
- runner: `scripts/revalidation/native_wifi_post_sibling_sysmon_classifier_v616.py`
- evidence: `tmp/wifi/v616-post-sibling-sysmon-service-notifier-classifier/`
- decision: `v616-post-sibling-sysmon-service-notifier-gap-classified`
- status: pass; host-only; no device command and no Wi-Fi bring-up attempted

## Scope

V616 compares existing Android V611, V599, V614, and native V615 evidence after
V615 proved that ADSP/CDSP/SLPI boot-node writes can publish sibling
`sysmon-qmi`.

The run did not contact the device, write sysfs, write `boot_wlan`, start CNSS,
start service-manager, start Wi-Fi HAL, scan/connect/link-up, use credentials,
run DHCP, change routes, or ping externally.

## Result

```text
decision: v616-post-sibling-sysmon-service-notifier-gap-classified
pass: True
reason: V615 reproduced sibling sysmon and service-locator after
        ADSP/CDSP/SLPI boot nodes, but service-notifier 180/74 remained absent
        and kernel warnings=23; direct boot-node retry is blocked
next: host-only classify Android init trigger after sibling sysmon; inspect
      wcnss-service/mdm_helper/boot_wlan dependencies before any live action
```

## Android Reference

Android V611 reaches the full lower publication chain:

```text
sysmon modem/slpi/cdsp/adsp
  → service-locator
    → service-notifier 180/74
      → WLAN-PD
        → QMI Server Connected
          → BDF regdb.bin/bdwlan.bin
            → WLAN FW ready / wlan0
```

Relevant Android timings:

| delta | ms |
| --- | ---: |
| `sysmon_modem → service_locator` | `38.830` |
| `sysmon_modem → service_notifier_180` | `53.927` |
| `service_locator → service_notifier_180` | `15.097` |
| `service_notifier_180 → service_notifier_74` | `1.466` |
| `service_notifier_180 → WLAN-PD` | `2319.436` |
| `WLAN-PD → QMI Server Connected` | `2.404` |

## Native V615

V615 reproduced more than V613:

```text
ADSP/CDSP/SLPI PIL
  → modem PIL
    → QRTR RX/TX
      → sysmon modem/slpi/cdsp/adsp
        → service-locator
```

But it did not advance beyond service-locator:

| marker | native V615 |
| --- | ---: |
| `service_notifier_180` | `0` |
| `service_notifier_74` | `0` |
| `wlan_pd` | `0` |
| `qmi_server_connected` | `0` |
| `bdf_regdb` / `bdf_bdwlan` | `0 / 0` |
| `wlan_fw_ready` | `0` |
| `wlan0` | `0` |

Native V615 timing:

| delta | ms |
| --- | ---: |
| `QRTR TX → sysmon_modem` | `1.028` |
| `sysmon_modem → rmt_storage_ready` | `314.360` |
| `sysmon_modem → service_locator` | `731.950` |
| `sysmon_modem → service_notifier_180` | missing |
| `service_locator → service_notifier_180` | missing |

## Safety Finding

V615 emitted `23` `pm_qos_add_request` kernel warnings during the direct
ADSP/CDSP/SLPI boot-node path. No `esoc0` reference-count warning was observed,
but direct boot-node retry is not acceptable as the next step until the warning
source is understood.

## Vendor Init Hints

The existing V614 vendor init snapshot shows Android has more surrounding
control flow than V615 reproduced:

- `write /sys/kernel/boot_adsp/boot 1`
- `write /sys/kernel/boot_cdsp/boot 1`
- `write /sys/kernel/boot_slpi/boot 1`
- `wcnss-service` start on `vold.decrypt=trigger_restart_framework`
- `vendor.mdm_launcher` and `vendor.mdm_helper`
- `boot_wlan` ownership/permission setup
- `qrtr-ns`, `rmt_storage`, `tftp_server`, and `pd-mapper`
- later `cnss_diag` and `cnss-daemon`

V615 intentionally reproduced only the DSP boot nodes plus the no-CNSS
companion stack. It did not reproduce `wcnss-service`, `vendor.mdm_launcher`,
`vendor.mdm_helper`, or any `boot_wlan` write.

## Interpretation

The remaining blocker is no longer basic firmware mount parity, modem PIL,
QRTR readiness, modem `sysmon-qmi`, or sibling `sysmon-qmi`. The current
native gap is:

```text
sibling sysmon-qmi + service-locator
  → missing service-notifier 180/74
```

Because service-notifier is a kernel/QMI callback path, this does not look like
a missing standalone userspace daemon. It is more likely a missing Android init
trigger sequence or a lower kernel/QMI registration precondition after sibling
DSP publication.

## Next Gate

Do not retry CNSS daemon, service-manager, Wi-Fi HAL, scan/connect, external
ping, or direct DSP boot-node writes from this state. The next useful cycle
should stay host-only/read-only and classify the Android trigger after sibling
`sysmon-qmi`, especially:

1. `wcnss-service` and `qcom-c_main-sh` behavior;
2. `vendor.mdm_launcher` / `vendor.mdm_helper` role and baseband gate;
3. whether `boot_wlan` is a required pre-service-notifier trigger or only a
   later WLAN driver trigger;
4. the source of V615 `pm_qos_add_request` warnings.
