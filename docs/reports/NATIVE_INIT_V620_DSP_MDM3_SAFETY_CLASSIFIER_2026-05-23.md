# Native Init V620 DSP/MDM3 Safety Classifier Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_dsp_mdm3_safety_classifier_v620.py`
- evidence: `tmp/wifi/v620-dsp-mdm3-safety-classifier/`
- decision: `v620-mdm3-trigger-gap-classified`

## Scope

V620 is host-only. It reads existing Android V611/V612 evidence, native
V615/V619 evidence, and V616/V617/V618 classifier manifests.

No device command, sysfs write, DSP boot-node write, daemon start,
service-manager start, Wi-Fi HAL start, scan/connect/link-up, credential, DHCP,
route change, or external ping was executed.

## Result

```text
decision: v620-mdm3-trigger-gap-classified
pass: True
reason: Android publishes service-notifier after lower sysmon with mdm3/esoc0 online, while V619 reproduces sibling sysmon under Android-order companion but leaves mdm3 OFFLINING, lacks esoc0 sysmon, and triggers pm_qos warnings. The remaining gap is lower mdm3/esoc0 QMI service publication, not CNSS/HAL or companion order.
next: V621 should remain host-only and resolve vendor.mdm_helper/launcher/wcnss-service trigger contracts before any bounded start-only proof
```

## Evidence Matrix

| subject | classification | evidence | next |
| --- | --- | --- | --- |
| service-notifier publication | kernel QMI callback gap | Android `180/74=1/1`; V619 `service_notifier=0`; Android `sysmon->180=53.927ms` | do not retry CNSS/HAL until lower QMI publication moves |
| mdm3/esoc0 state | strong pre-service-notifier blocker | Android `mdm3=ONLINE`, `sysmon_esoc0=1`; V619 `mdm3=OFFLINING`, `sysmon_esoc0=0` | resolve `mdm_helper`/launcher/`wcnss-service` trigger path before live writes |
| direct DSP boot nodes | unsafe to repeat | Android `pm_qos=0`; V615 `pm_qos=23`; V619 `kernel_warning=21` | block direct ADSP/CDSP/SLPI boot-node observer retries |
| Android-order companion | falsified as root cause | V619 replayed `qrtr_ns,pd_mapper,rmt_storage,tftp_server`, `child_started=4`, but notifier stayed absent | do not spend another live cycle on companion order alone |
| CNSS/HAL/qcwlanstate | still too late | V619 `qmi_server_connected=0`, `wlfw=0`; Android service-notifier precedes WLAN-PD/QMI | no Wi-Fi bring-up attempt until notifier/WLAN-PD exists |
| `vendor.mdm_helper` / launcher | next host-only contract target | service block, launcher, and baseband gate are present in vendor init evidence | classify exact Android trigger/identity before any start-only proof |

## Interpretation

V619 falsifies the remaining companion-order hypothesis. Android-order lower
companion startup is observable and cleanup-safe, but it does not publish
service-notifier `180/74`.

The strongest current blocker is below CNSS/HAL:

```text
Android: sibling sysmon + mdm3 ONLINE + sysmon_esoc0 + service-notifier 180/74
Native:  sibling sysmon + mdm3 OFFLINING + no sysmon_esoc0 + no service-notifier
```

The `service-notifier` event remains best treated as a kernel/QMI publication
callback, not a userspace `cnss-daemon` trigger. Direct ADSP/CDSP/SLPI boot-node
retries are blocked because both V615 and V619 reproduced `pm_qos_add_request`
warnings around `msm_asoc_machine_probe`.

## Next Gate

Proceed to V621 as another host-only contract classifier:

1. resolve `vendor.mdm_helper`, `vendor.mdm_launcher`, and `wcnss-service`
   trigger timing from Android/vendor init evidence;
2. identify whether any candidate can be tested without direct DSP boot-node
   writes;
3. only then design a bounded start-only proof with no CNSS/HAL/scan/connect.

Wi-Fi bring-up remains blocked until `service-notifier` / WLAN-PD / WLFW / BDF
markers advance under native init.
