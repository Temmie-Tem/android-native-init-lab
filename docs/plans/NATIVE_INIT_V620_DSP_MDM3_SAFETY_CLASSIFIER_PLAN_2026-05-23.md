# Native Init V620 DSP/MDM3 Safety Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v620`
- scope: host-only classifier
- target: classify why native reaches sibling `sysmon-qmi` but not
  `service-notifier`, while direct DSP boot-node writes trigger `pm_qos`
  warnings and leave `mdm3=OFFLINING`

## Background

V619 executed the Android-order lower companion sequence and proved that
ordering alone is not enough:

```text
qrtr_ns -> pd_mapper -> rmt_storage -> tftp_server
```

The observer reached QRTR RX/TX and modem/adsp/cdsp/slpi `sysmon-qmi`, but
`service-notifier 180/74`, WLAN-PD, WLFW, BDF, firmware-ready, and `wlan0`
remained absent. It also reproduced the direct DSP boot-node `pm_qos` warning
class.

## Guardrails

V620 must not:

- contact the device;
- write sysfs, `boot_wlan`, `qcwlanstate`, or DSP boot nodes;
- start companion daemons, CNSS, service-manager, Wi-Fi HAL, `wificond`,
  supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Inputs

- V619 live evidence:
  `tmp/wifi/v619-android-order-post-sysmon-observer-run/manifest.json`
- V615 live evidence:
  `tmp/wifi/v615-dsp-boot-20260523-015352/v615-live/`
- V616/V617/V618 classifier manifests
- Android lower-surface evidence from V611/V612/V521/V525/V526
- Vendor init snapshot from V614

## Checks

1. Compare Android/native `pm_qos_add_request` warning presence and call traces.
2. Compare Android/native timing for ADSP/CDSP/SLPI boot, modem `sysmon-qmi`,
   sibling `sysmon-qmi`, service-locator, service-notifier, and `mdm3`.
3. Explicitly test whether Android publishes service-notifier `180/74` before
   or after `sysmon_esoc0`; if `sysmon_esoc0` appears later, treat native
   `sysmon_esoc0=0` as a state delta rather than a proven first-notifier cause.
4. Determine whether `mdm3=OFFLINING` is the stronger blocker than companion
   order.
5. Classify `vendor.mdm_launcher`, `vendor.mdm_helper`, `wcnss-service`, and
   `boot_wlan` as:
   - pre-service-notifier candidate;
   - later WLAN-only candidate;
   - unsafe/write-only candidate;
   - or unsupported by current evidence.
6. Search the V614 vendor init snapshot for `mdm_helper`/`mdm_launcher`
   contract hints, including `ro.baseband`, Android init `start`, raw `esoc0`
   paths, and any visible `ioctl` hints. Absence of an init-visible raw/ioctl
   path means a live raw `esoc0` retry is not justified.
7. Cross-check adjacent postmarketOS/Qualcomm references only as supporting
   context:
   - SDM845 notes describe `rmtfs`, `pd-mapper`, and `tqftpserv` as required
     firmware/modem communication services for Wi-Fi firmware loading;
   - Debian/Fedora package metadata describes `tqftpserv` as a TFTP server over
     QRTR/AF_QIPCRTR for remote processors;
   - Debian `pd-mapper` ITP describes it as the Qualcomm Protection Domain
     mapper service that lets userspace access Wi-Fi/modem/sensor remote
     processors over QRTR;
   - upstream Linux `QCOM_PD_MAPPER` context shows a kernel-side PD mapper is
     tied to `NET`/`QRTR` and covers SM8150/SM8250-class Qualcomm targets, but
     this remains context rather than proof for the downstream Samsung kernel;
   - pmaports QRTR dependency discussions and SM8150/SM8250 package history can
     guide QRTR/mainline service-order expectations, but they are not direct
     evidence for Samsung vendor-kernel `mdm_helper`/`esoc0` semantics.
8. Produce a next live gate only if it avoids repeating direct DSP boot-node
   warnings.

## Explicit Hypothesis Additions

V620 should record these checks even if the final decision moves away from the
initial hypothesis:

- `sysmon_esoc0` missing check: Android V612 has `sysmon_esoc0=1`; native V619
  has `sysmon_esoc0=0`. Compare exact timestamp order against
  service-notifier `180/74` and WLAN-PD before treating it as causal.
- `mdm_helper` path check: if raw `esoc0` open is unsafe or unsupported by
  vendor init, classify whether Android uses `vendor.mdm_helper`,
  `vendor.mdm_launcher`, properties, or a binary-only ioctl path to move modem
  state.
- SM8150/pmaports context check: use Qualcomm mainline/pmaports material only
  for adjacent QRTR/firmware-service expectations, not as direct proof for this
  Samsung vendor kernel.
- Core hypothesis under test: `esoc0` SSCTL absence could block
  service-notifier publication. V620 must either support it with timing data or
  explicitly demote it to a later-state delta.

## Reference Scope

External references are background only. They may justify why QRTR,
`pd-mapper`, `tqftpserv`, and firmware-service ordering are worth checking, but
they must not override device-local Android/native timing evidence. A live
native gate still requires repo evidence that the target action is bounded,
cleanup-safe, and does not start CNSS/HAL or Wi-Fi bring-up prematurely.

## Success Criteria

V620 passes if it selects one of these outcomes using existing evidence:

- `v620-mdm3-trigger-gap-classified`
- `v620-direct-dsp-boot-unsafe-blocker`
- `v620-android-evidence-gap-needs-readonly-recapture`
- `v620-next-live-gate-ready`

Passing V620 does not authorize CNSS/HAL/Wi-Fi bring-up. If evidence is
insufficient, the next action should be Android read-only recapture, not another
native live write.
