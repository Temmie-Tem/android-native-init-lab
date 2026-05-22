# Native Init V620 DSP/MDM3 Safety Classifier Report

- date: `2026-05-23 KST`
- status: `classified/refined`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_dsp_mdm3_safety_classifier_v620.py`
- evidence: `tmp/wifi/v620-dsp-mdm3-safety-classifier-current-request-20260523/`
- decision: `v620-esoc0-notifier-causality-refined`

## Scope

V620 is host-only. It reads existing Android V611/V612 evidence, native
V615/V619 evidence, V616/V617/V618 classifier manifests, and static vendor init
evidence.

The current evidence manifest also exposes machine-readable aliases for the
requested additions: `requested_hypothesis_additions`, `timing_deltas_ms`,
`mdm_helper_path`, `evidence_matrix`, `android_timeline`, and
`native_timeline`.

No device command, sysfs write, DSP boot-node write, daemon start,
service-manager start, Wi-Fi HAL start, scan/connect/link-up, credential, DHCP,
route change, or external ping was executed.

## Result

```text
decision: v620-esoc0-notifier-causality-refined
pass: True
reason: Android publishes service-notifier after lower sysmon before sysmon_esoc0 appears, while V619 reproduces sibling sysmon under Android-order companion but leaves mdm3 OFFLINING, lacks service-notifier, and triggers pm_qos warnings. Missing sysmon_esoc0 is a later state delta, not a proven pre-notifier cause.
next: V621 should remain host-only and resolve vendor.mdm_helper/launcher ioctl/property timing before any bounded start-only proof
```

## Evidence Matrix

| subject | classification | evidence | next |
| --- | --- | --- | --- |
| service-notifier publication | kernel QMI callback gap | Android `180/74=1/1`; V619 `service_notifier=0`; Android `sysmon->180=53.927ms` | do not retry CNSS/HAL until lower QMI publication moves |
| mdm3/esoc0 state | state delta, not notifier prerequisite | Android `mdm3=ONLINE`, `sysmon_esoc0=1`; V619 `mdm3=OFFLINING`, `sysmon_esoc0=0`; Android `180->esoc0=4472.856ms` | do not claim `sysmon_esoc0` is required before service-notifier |
| `sysmon_esoc0` timing | not causal for first notifier | Android `sysmon_modem->180=53.927ms`; Android `180->esoc0=4472.856ms`; Android `wlan_pd->esoc0=2153.42ms` | focus next analysis on `mdm_helper`/launcher path and same-boot timing |
| direct DSP boot nodes | unsafe to repeat | Android `pm_qos=0`; V615 `pm_qos=23`; V619 `kernel_warning=21` | block direct ADSP/CDSP/SLPI boot-node observer retries |
| Android-order companion | falsified as root cause | V619 replayed `qrtr_ns,pd_mapper,rmt_storage,tftp_server`, `child_started=4`, but notifier stayed absent | do not spend another live cycle on companion order alone |
| CNSS/HAL/qcwlanstate | still too late | V619 `qmi_server_connected=0`, `wlfw=0`; Android service-notifier precedes WLAN-PD/QMI | no Wi-Fi bring-up attempt until notifier/WLAN-PD exists |
| `vendor.mdm_helper` / launcher | next host-only contract target | service block, launcher, and baseband gate are present in vendor init evidence | classify exact Android trigger/identity and ioctl/property path before any start-only proof |

## Interpretation

The proposed `sysmon_esoc0` prerequisite hypothesis is not supported by the
captured Android timing. In the Android V611 reference, service-notifier
`180/74` appears first, WLAN-PD/QMI follows, and `sysmon_esoc0` appears later:

```text
sysmon_modem -> service-notifier 180: 53.927 ms
service-notifier 180 -> WLAN-PD:       2319.436 ms
service-notifier 180 -> sysmon_esoc0:  4472.856 ms
WLAN-PD -> sysmon_esoc0:               2153.42 ms
```

Therefore native `sysmon_esoc0=0` is still a useful state delta, but it is not
the proven cause of the first missing service-notifier publication.

V619 still falsifies the companion-order hypothesis. Android-order lower
companion startup is observable and cleanup-safe, but it does not publish
service-notifier `180/74`.

The current blocker remains below CNSS/HAL:

```text
Android: sibling sysmon + service-notifier 180/74 + WLAN-PD/QMI + later sysmon_esoc0
Native:  sibling sysmon + no service-notifier + mdm3 OFFLINING + no sysmon_esoc0
```

## Causality Checks

| check | result | interpretation |
| --- | --- | --- |
| Android service-notifier before `sysmon_esoc0` | true | `sysmon_esoc0` is not a proven first-notifier prerequisite |
| Android WLAN-PD before `sysmon_esoc0` | true | `sysmon_esoc0` is later than the first lower WLAN path |
| Native missing service-notifier | true | lower QMI publication is still the active blocker |
| Native missing `sysmon_esoc0` | true | useful state delta, but not enough to justify raw `esoc0` retry |
| Native `mdm3=OFFLINING` | true | stronger unresolved state gap than companion order |
| Direct DSP warning present | true | direct ADSP/CDSP/SLPI boot-node retry remains blocked |
| `mdm_helper` init contract visible | true | valid next analysis target |
| Init-visible raw `esoc0` path | false | raw `esoc0` open is not justified by vendor init evidence |
| Init-visible `ioctl` hint | false | ioctl path remains a hypothesis requiring binary/behavioral analysis, not a live retry |

## Requested Hypothesis Additions

| item | observation | timing/context | classification |
| --- | --- | --- | --- |
| `sysmon_esoc0` absence | Android V612 has `sysmon_esoc0=1`; native V619 has `sysmon_esoc0=0` | Android `180->esoc0=4472.856ms`; Android `wlan_pd->esoc0=2153.42ms` | absence is real, but Android publishes first notifier before `esoc0` |
| `mdm_helper` ioctl/property path | V614 exposes `vendor.mdm_launcher` and `vendor.mdm_helper` contract | no init-visible raw `esoc0` path and no visible `ioctl` string | same-boot timing and binary/static inspection are required before any start-only proof |
| SM8150/pmaports context | QRTR, `pd-mapper`, `tqftpserv`, and `rmtfs` remain adjacent Qualcomm prerequisites | mainline packaging helps frame firmware-service ordering only | not direct proof of Samsung vendor-kernel `mdm_helper`/`esoc0` semantics |
| core hypothesis | `esoc0` SSCTL absence might block service-notifier publication | current Android timing shows service-notifier `180/74` precedes `sysmon_esoc0` | falsified as first-notifier cause; retained only as later-state delta |

## MDM Helper Path

Static vendor evidence shows:

- `vendor.mdm_launcher` is an Android init oneshot wrapper:
  `/vendor/bin/sh /vendor/bin/init.mdm.sh`
- `init.mdm.sh` reads `ro.baseband` and starts `vendor.mdm_helper` only for
  `mdm`/`mdm2`
- `vendor.mdm_helper` is the actual long-running disabled service:
  `/vendor/bin/mdm_helper`

This makes direct `esoc0` raw open less attractive as a next step. Android may
be using the `mdm_helper` service/property/ioctl path rather than an externally
visible raw fd-open path to move modem/MDM state. V621 should classify that
contract from existing Android/vendor evidence before any bounded start-only
proof.

The V614 vendor init snapshot proves the Android-init contract but does not show
a raw `esoc0` sysfs/device path or an explicit `ioctl` string. That means the
right next step is still host-only: compare same-boot Android boottime/dmesg,
inspect `mdm_helper` identity and static symbols if available, and only then
decide whether a bounded start-only proof is worth running.

## External References

These references are supporting context only; the V620 decision remains based
on repo-local Android/native timing evidence.

- postmarketOS SDM845 Wi-Fi notes:
  `https://wiki.postmarketos.org/wiki/SDM845_Mainlining`
  - public mirror/search snippets describe `rmtfs`, `pd-mapper`, and
    `tqftpserv` as required services for modem communication and Wi-Fi firmware
    loading on adjacent Qualcomm platforms.
- Debian `tqftpserv` package:
  `https://packages.debian.org/bookworm/tqftpserv`
  - describes `tqftpserv` as a TFTP server over QRTR for communication with
    remote processors such as Wi-Fi, modem, and sensors.
- Fedora `tqftpserv` package:
  `https://packages.fedoraproject.org/pkgs/tqftpserv/tqftpserv/`
  - identifies the AF_QIPCRTR transport and upstream
    `https://github.com/linux-msm/tqftpserv`.
- Debian `pd-mapper` ITP:
  `https://groups.google.com/g/linux.debian.devel/c/gZWi4_ca9yw`
  - describes `pd-mapper` as the Qualcomm Protection Domain mapper service for
    userspace access to Wi-Fi/modem/sensor remote processors over QRTR.
- pmaports QRTR dependency issue:
  `https://gitlab.com/postmarketOS/pmaports/-/issues/863`
  - frames `pd-mapper`/`tqftpserv` as QRTR-adjacent services and notes that
    mainline kernels may provide QRTR in-kernel.
- pmaports SM8150/SM8250 history:
  `https://gitlab.com/postmarketOS/pmaports/-/merge_requests/3019`
  and `https://gitlab.com/postmarketOS/pmaports/-/merge_requests/5608`
  - confirms adjacent mainline Qualcomm work and evolving service packaging,
    but does not provide a direct Samsung vendor-kernel
    `mdm_helper`/`esoc0` recipe.
- Linux `QCOM_PD_MAPPER` kernel config:
  `https://cateee.net/lkddb/web-lkddb/QCOM_PD_MAPPER.html`
  - shows the upstream kernel-side Protection Domain Mapper depends on
    `NET`/`QRTR` and covers SM8150/SM8250-class Qualcomm targets. This supports
    the QRTR/PD-mapper framing, but it is still not proof that this downstream
    Samsung vendor kernel has an equivalent in-kernel mapper path.

The external material therefore supports the QRTR/firmware-service framing, but
it does not justify raw `esoc0` access or a live `mdm_helper` start without
device-local proof.

## Next Gate

Proceed to V621 as another host-only contract classifier:

1. compare same-boot or existing Android timing for `vendor.mdm_launcher`,
   `vendor.mdm_helper`, service-notifier, WLAN-PD, and `sysmon_esoc0`;
2. classify whether `mdm_helper` can be tested as a bounded start-only proof
   without direct DSP boot-node writes;
3. keep `wcnss-service`, CNSS/HAL, `boot_wlan`, scan/connect, credentials, and
   external ping blocked until service-notifier/WLAN-PD or WLFW/BDF markers
   advance under native init.
