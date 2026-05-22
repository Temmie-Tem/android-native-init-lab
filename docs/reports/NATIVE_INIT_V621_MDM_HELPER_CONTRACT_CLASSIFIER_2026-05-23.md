# Native Init V621 MDM Helper Contract Classifier Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_mdm_helper_contract_classifier_v621.py`
- evidence: `tmp/wifi/v621-mdm-helper-contract-classifier/`
- decision: `v621-mdm-helper-contract-same-boot-recapture-required`

## Scope

V621 is host-only. It reads existing V620, V614, V611, V431, and V297
evidence. It does not contact the device.

No device command, sysfs write, DSP boot-node write, daemon start,
service-manager start, Wi-Fi HAL start, scan/connect/link-up, credential, DHCP,
route change, or external ping was executed.

## Result

```text
decision: v621-mdm-helper-contract-same-boot-recapture-required
pass: True
reason: `vendor.mdm_helper` is the real Android service candidate and `vendor.mdm_launcher` is only a ro.baseband-gated oneshot wrapper, but existing mdm_helper boottime and service-notifier dmesg are from different Android captures. Live native start-only should wait for same-boot read-only timing or a stricter bounded proof plan.
next: V622 should collect Android same-boot mdm_helper/mdm_launcher boottime plus dmesg service-notifier/WLAN-PD/sysmon_esoc0 timing, then decide live start-only
```

## Evidence Matrix

| subject | classification | evidence | next |
| --- | --- | --- | --- |
| `vendor.mdm_launcher` | oneshot wrapper | present=yes; oneshot=yes; Android state=stopped; boottime=8075.768ms | do not treat as persistent daemon |
| `vendor.mdm_helper` | real Android service candidate | present=yes; disabled=yes; Android state=running; boottime=8323.251ms; fail_action=`cold_reset,s3_reset,panic` | needs same-boot timing or stricter bounded start-only proof |
| `ro.baseband` gate | satisfied in Android evidence | `ro.baseband=mdm`; `ro.boot.baseband=mdm`; script gate=yes; script starts helper=yes | native proof must provide equivalent property surface or direct helper argv |
| `wcnss-service` | not direct target | `start wcnss-service` reference=yes; service block=no | do not start `wcnss-service` by name |
| timing evidence | cross-boot | V611 `service_notifier_180=8.13522s`; V431 `mdm_launcher=8075.768ms`; V431 `mdm_helper=8323.251ms`; V431 dmesg=no | same-boot Android recapture is the clean next evidence step |

## Interpretation

The Android init contract is now narrower:

- `vendor.mdm_launcher` is only an Android init oneshot wrapper:
  `/vendor/bin/sh /vendor/bin/init.mdm.sh`
- `init.mdm.sh` reads `ro.baseband` and starts `vendor.mdm_helper` only for
  the expected modem baseband path.
- `vendor.mdm_helper` is the actual long-running disabled service:
  `/vendor/bin/mdm_helper`
- `wcnss-service` appears as a start reference but has no direct service block
  in the captured vendor init snapshot.

That makes `vendor.mdm_helper` the only credible Android init service candidate
for the next modem/QMI publication proof. However, the current timing evidence
is not from one Android boot:

```text
V611: service-notifier 180 first timestamp: 8.13522 s
V431: vendor.mdm_launcher boottime:        8075.768 ms
V431: vendor.mdm_helper boottime:          8323.251 ms
V431: dmesg timing in same evidence set:   missing
```

Therefore V621 cannot honestly claim that `mdm_helper` starts before or after
the first `service-notifier` publication. A native start-only proof would still
be premature because it could repeat another live experiment without knowing
whether Android uses `mdm_helper` as a pre-notifier trigger or as a later modem
health helper.

## Next Gate

Proceed to V622 as an Android same-boot read-only recapture:

1. capture `ro.boottime.vendor.mdm_launcher`,
   `ro.boottime.vendor.mdm_helper`, `init.svc.vendor.mdm_helper`, and
   `init.svc.vendor.mdm_launcher`;
2. capture the same boot's dmesg markers for `sysmon-qmi`,
   `service-notifier 180/74`, WLAN-PD, and `sysmon_esoc0`;
3. compare helper/launcher timing against first notifier publication;
4. only then decide whether a bounded native `vendor.mdm_helper` start-only
   proof is justified.

CNSS, service-manager, Wi-Fi HAL, scan/connect/link-up, credentials, DHCP,
route changes, and external ping remain blocked until the lower notifier/WLAN-PD
markers advance.
