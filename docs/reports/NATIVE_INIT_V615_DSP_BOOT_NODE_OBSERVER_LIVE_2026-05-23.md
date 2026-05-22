# Native Init V615 DSP Boot-Node Observer Live Report

- date: `2026-05-23 KST`
- run: `tmp/wifi/v615-dsp-boot-20260523-015352/`
- preflight evidence: `tmp/wifi/v615-dsp-boot-20260523-015352/v615-preflight/`
- live evidence: `tmp/wifi/v615-dsp-boot-20260523-015352/v615-live/`
- runner: `scripts/revalidation/native_wifi_dsp_boot_node_observer_v615.py`
- result: bounded observation completed; native rollback verified; no Wi-Fi bring-up attempted

## Scope

V615 tested the V614 conclusion that Android reaches lower Wi-Fi publication
only after booting the sibling DSP surfaces before the modem-side QRTR/sysmon
window. The live run used:

- current-boot V401 selinuxfs mount proof: pass
- current-boot V490 SELinux policy-load proof: pass
- firmware mount parity for modem/APNHLOS surfaces
- writes only to `/sys/kernel/boot_adsp/boot`, `/sys/kernel/boot_cdsp/boot`,
  and `/sys/kernel/boot_slpi/boot`
- `subsys_modem` no-close holder
- no-CNSS companion window: `qrtr-ns`, `rmt_storage`, `tftp_server`,
  `pd-mapper`
- reboot cleanup

The run did not write `/sys/kernel/boot_wlan/boot_wlan`, start CNSS daemon,
service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect,
credentials, DHCP, routes, or external ping.

## Result

The device-side live sequence completed and reboot cleanup returned to a healthy
native v319 state. The host runner then failed while building the live manifest
because V615 referenced `base.step_ok`, which is not exported by the V596 base
module. The runner has been fixed to use a local `step_ok` helper for future
V615 manifests.

Existing evidence still classifies the live result:

```text
classification: v615-unsafe-kernel-warning
boot_nodes_written: adsp=True cdsp=True slpi=True
mss after holder: ONLINE
mss after companion: ONLINE
mdm3 after companion: OFFLINING
QRTR RX/TX: present
modem sysmon-qmi: present
sibling sysmon-qmi: adsp=1 cdsp=1 slpi=1
service-notifier 180/74: 0
WLAN-PD/WLFW/BDF/wlan0: 0
kernel warnings: present
```

## Observed Markers

```text
adsp_pil: 1
cdsp_pil: 1
slpi_pil: 1
adsp_sysmon: 1
cdsp_sysmon: 1
slpi_sysmon: 1
qrtr_rx: 1
qrtr_tx: 1
sysmon_qmi: 4
service_notifier_180: 0
service_notifier_74: 0
wlan_pd: 0
qmi_server_connected: 0
wlfw: 0
bdf: 0
wlan_fw_ready: 0
wlan0: 0
```

The important dmesg sequence was:

1. ADSP, CDSP, and SLPI PIL loads completed.
2. The modem PIL load completed.
3. QRTR readiness `RX` and `TX` appeared.
4. `sysmon-qmi` connected to modem, SLPI, CDSP, and ADSP SSCTL services.
5. No service-notifier `180/74`, WLAN-PD, WLFW, BDF, firmware-ready, or
   `wlan0` marker appeared.
6. The kernel emitted repeated `pm_qos_add_request` warnings during the DSP
   boot-node path.

## Interpretation

V615 proves the boot-node hypothesis was partially correct:

```text
ADSP/CDSP/SLPI boot nodes → sibling sysmon-qmi
```

However, it does not reproduce Android's next lower publication step:

```text
sibling sysmon-qmi → service-notifier 180/74 → WLAN-PD → WLFW/BDF/wlan0
```

The direct boot-node sequence also triggered kernel warnings, so this action
primitive is not safe to repeat as the next live step. The service-notifier gap
is now more precise: native can publish sibling SSCTL services, but the
service-notifier instances still do not appear.

## Next Gate

Do not retry CNSS daemon, service-manager, Wi-Fi HAL, scan, connect, or direct
DSP boot-node writes from this state. The next useful step is a host-only
classifier against Android and vendor init evidence:

- identify what Android does between sibling `sysmon-qmi` publication and
  service-notifier `180/74`
- compare service-locator/service-notifier dependencies and init ordering
- determine whether an additional vendor service, property, ioctl, or notifier
  registration path is required after sibling DSP boot
- classify the `pm_qos_add_request` warning source before any further live
  boot-node experiment
