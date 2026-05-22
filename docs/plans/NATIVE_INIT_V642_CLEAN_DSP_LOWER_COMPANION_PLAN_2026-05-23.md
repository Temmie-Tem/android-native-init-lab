# Native Init V642 Clean-DSP Lower Companion Plan

- date: `2026-05-23 KST`
- cycle: `v642`
- scope: bounded native live observer
- target: reuse V641's clean firmware-backed DSP state, then test whether the
  lower modem/QRTR companion path can advance toward `service-notifier` without
  repeating direct DSP boot-node writes

## Background

V641 moved the DSP side forward safely:

- ADSP/CDSP/SLPI firmware-backed boot-window writes returned `rc=0`;
- ADSP/CDSP/SLPI PIL reset/power-clock markers appeared;
- no V638-style `pm_qos_add_request` warning appeared;
- no `sysmon-qmi`, `service-notifier`, WLAN-PD, WLFW/BDF, or `wlan0` appeared.

That means the next blocker is no longer "can DSPs be booted cleanly?" but
"can the lower modem/QRTR companion stack publish the missing service-notifier
path while the DSP state is already clean?"

## Guardrails

V642 must not:

- write ADSP/CDSP/SLPI boot nodes;
- write `boot_wlan`, `qcwlanstate`, or other WLAN driver-state sysfs nodes;
- start CNSS, service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use Wi-Fi credentials, run DHCP, change routes, or ping
  externally;
- change the boot image or write boot partitions.

## Implementation

Add `scripts/revalidation/native_wifi_clean_dsp_lower_companion_v642.py`.

The runner reuses the V596 safe pieces:

1. verify current native version is `A90 Linux init 0.9.67 (v641)`;
2. verify current V490 policy-load manifest is fresh for this boot;
3. verify helper v104 is installed and exposes
   `wifi-companion-android-order-post-sysmon-observer-start-only`;
4. read-only verify V641 clean-DSP state from
   `/cache/native-init-sibling-fwssctl-v641.log` and current rpmsg devices;
5. mount firmware partitions read-only using the existing V584/V596 mount path;
6. hold only `subsys_modem` with reboot cleanup;
7. wait for QRTR RX before starting any companion process;
8. start only Android-order lower companion services:
   `qrtr_ns,pd_mapper,rmt_storage,tftp_server`;
9. capture mss/mdm3 state, rpmsg, `/proc/net/qrtr`, dmesg delta, and helper
   key/value output;
10. reboot back into v641 as cleanup boundary.

## Success Criteria

V642 passes as a diagnostic gate if one of these bounded classifications is
produced:

- `v642-service-notifier-advanced`: service-notifier appears without CNSS/HAL;
- `v642-lower-modem-readiness-only`: QRTR TX or `sysmon-qmi` advances but
  service-notifier remains missing;
- `v642-qrtr-rx-only`: QRTR RX is observed but companion does not advance lower
  readiness.

V642 fails if:

- V641 clean-DSP proof is missing or rpmsg state is not present;
- helper v104 is missing;
- current-boot V490 is stale or missing;
- a kernel warning appears;
- companion order is not exactly
  `qrtr_ns,pd_mapper,rmt_storage,tftp_server`;
- any QMI payload, CNSS/HAL/service-manager start, scan/connect, credential,
  DHCP, route, or external ping occurs.

## Next Gate

- If service-notifier appears, plan a bounded CNSS/WLFW observer with HAL and
  scan/connect still blocked.
- If only QRTR/sysmon advances, compare V642 against V619/V641 and classify
  the remaining lower publication trigger.
- If only QRTR RX appears, inspect modem-holder timing and companion stdout
  before retrying.
