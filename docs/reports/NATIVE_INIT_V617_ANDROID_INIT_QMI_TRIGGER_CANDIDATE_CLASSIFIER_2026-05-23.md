# Native Init V617 Android Init/QMI Trigger Candidate Classifier Report

- date: `2026-05-23 KST`
- runner: `scripts/revalidation/native_wifi_android_init_trigger_candidate_v617.py`
- evidence: `tmp/wifi/v617-android-init-trigger-candidate-classifier/`
- decision: `v617-qmi-service-registration-trigger-gap-classified`
- status: pass; host-only; no device command and no Wi-Fi bring-up attempted

## Scope

V617 compares existing Android V521/V611 evidence with native V615/V616
evidence. The goal is to decide whether the next action should retry userspace
Wi-Fi daemons or keep narrowing the lower QMI service-registration path.

The run did not contact the device, write sysfs, write `boot_wlan`, start any
daemon, start service-manager, start Wi-Fi HAL, scan/connect/link-up, use
credentials, run DHCP, change routes, or ping externally.

## Result

```text
decision: v617-qmi-service-registration-trigger-gap-classified
pass: True
reason: Android publishes service-notifier 180/74 immediately after sysmon and
        before CNSS/HAL, while V615 replays qrtr/rmt_storage/tftp_server/
        pd_mapper and reaches sibling sysmon/service-locator without notifier;
        sysmon_to_service_notifier_180=49.029ms, rfs_unreplayed=True
next: V618 should host-only classify rfs_access/service-locator/QMI-publication
      dependencies and only then design a bounded no-HAL observer
```

## Timing Delta

Android V521 shows the lower registration path is early:

| delta | ms |
| --- | ---: |
| `sysmon_modem → service_notifier_180` | `49.029` |
| `sysmon_modem → service_notifier_74` | `60.042` |
| `service_notifier_180 → service_notifier_74` | `11.013` |
| `service_notifier_180 → rmt_storage_ready` | `46.219` |
| `service_notifier_180 → cnss_diag_start` | `781.452` |
| `service_notifier_180 → WLAN-PD` | `2362.373` |
| `WLAN-PD → QMI Server Connected` | `2.095` |

Native V615 still stops before service-notifier:

| delta | ms |
| --- | ---: |
| `sysmon_modem → service_locator_fail` | `21.528` |
| `sysmon_modem → rmt_storage_ready` | `314.360` |
| `sysmon_modem → service_locator` | `731.950` |
| `sysmon_modem → service_notifier_180` | missing |

## Candidate Matrix

| candidate | classification | evidence |
| --- | --- | --- |
| QMI service registration | strong gap | Android publishes notifier `180/74`; native sibling sysmon is present but notifier is absent |
| `rfs_access` | medium candidate | Android init starts `rfs_access`; V615 companion order is only `qrtr_ns,rmt_storage,tftp_server,pd_mapper` |
| `rmt_storage`/`tftp_server`/`pd_mapper` | already replayed | V615 started all three and still captured no service-notifier |
| `wcnss-service` | weak/unproven | vendor init has a start reference, but Android props/processes show no running service |
| `vendor.mdm_helper`/`vendor.mdm_launcher` | weak/unproven | service definitions exist, but Android props/processes in the current capture do not prove runtime use |
| `boot_wlan`/`qcwlanstate` | blocked | write-only/later trigger path; V615 already produced `23` `pm_qos_add_request` warnings |
| CNSS daemon/HAL | too late | Android service-notifier appears before `cnss_diag`, `cnss-daemon`, WLAN-PD, and HAL-dependent bring-up |

## Interpretation

The user-provided hypothesis is consistent with the evidence: service-notifier
is best treated as a kernel/QMI callback that reacts to lower service
registration, not as a direct effect of `cnss-daemon` or HAL startup.

Therefore the current native gap is:

```text
sibling sysmon-qmi + service-locator
  → missing QMI service registration/service-notifier 180/74
```

The most useful next work is not another CNSS/HAL retry. It is a host-only
classifier for Android's `rfs_access` and service-locator/QMI-publication
dependencies, then a bounded no-HAL live observer only if the contract is
explicit.

## Next Gate

Proceed with V618 as a host-only/read-only classifier for:

1. exact `rfs_access` service definition, domain, binary, sockets, and Android
   runtime presence;
2. whether `rfs_access` participates in service-locator or QMI publication;
3. whether V615's delayed service-locator plus missing notifier can be explained
   by the unreplayed `rfs_access` path;
4. the minimum bounded observer contract if live testing becomes justified.
