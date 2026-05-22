# Native Init V613 MDM3/ESOC Targeted Observer Live Report

- date: `2026-05-23 KST`
- run: `tmp/wifi/v613-mdm3-esoc-20260523-013228/`
- live evidence: `tmp/wifi/v613-mdm3-esoc-20260523-013228/v613-live/`
- runner: `scripts/revalidation/native_wifi_mdm3_esoc_targeted_observer_v613.py`
- result: bounded observation completed; native rollback verified

## Scope

V613 tested the V612 hypothesis that native Wi-Fi lower publication is blocked
below CNSS/HAL by the `mdm3/esoc0` side of the modem stack. The live run used:

- current-boot V401 selinuxfs mount proof: pass
- current-boot V490 SELinux policy-load proof: pass
- `subsys_modem` no-close holder: attempted and reached `mss=ONLINE`
- `subsys_esoc0` no-close holder: attempted, but open did not return
- companion window: `qrtr-ns`, `rmt_storage`, `tftp_server`, `pd-mapper`

The run did not start CNSS daemon, service-manager, Wi-Fi HAL, `wificond`,
supplicant, hostapd, scan/connect/link-up, credentials, DHCP, routes, or
external ping.

## Result

The original live manifest emitted:

```text
decision: v613-esoc-holder-not-opened
pass: False
reason: esoc holder did not report opened
```

The evidence shows a more precise classification:

```text
corrected classification: v613-esoc-open-blocked-no-publication
subsys_modem holder: opened
subsys_esoc0 holder: open reached kernel __subsystem_get(esoc0) but did not return
mss after modem holder: ONLINE
mdm3 after esoc holder: OFFLINING
mdm3 after companion: OFFLINING
kernel warning/reference mismatch: 0
native cleanup after reboot: healthy
```

The runner was updated after the live run so future manifests classify this
case as `v613-esoc-open-blocked-no-publication` instead of a generic holder
failure.

## Observed Markers

```text
qrtr_rx: 1
qrtr_tx: 1
sysmon_qmi modem: 1
service_notifier: 0
sibling sysmon slpi/cdsp/adsp/esoc0: 0
wlan_pd: 0
qmi_server_connected: 0
wlfw: 0
bdf: 0
wlan0: 0
```

Important kernel/userland events appeared in this order:

1. `subsys_modem` holder triggered modem PIL load.
2. `mss` reached `ONLINE`.
3. QRTR readiness `RX` appeared.
4. `subsys_esoc0` open entered the kernel `__subsystem_get(esoc0)` path.
5. Companion stack produced QRTR readiness `TX`.
6. `sysmon-qmi` connected to modem SSCTL.
7. `rmt_storage` served modem FS reads.
8. Service locator connected.
9. No sibling sysmon or service-notifier `180/74` appeared.

## Interpretation

V613 confirms that native can now reproduce the modem-side lower path up to:

```text
MSS ONLINE → QRTR RX/TX → sysmon modem SSCTL → rmt_storage/service-locator
```

The remaining Android/native delta is narrower:

```text
mdm3/esoc0 sibling publication → service-notifier 180/74 → WLAN-PD → WLFW/BDF/wlan0
```

Raw `subsys_esoc0` opening is not the right next trigger. It reaches the kernel
path but blocks without advancing `mdm3` to `ONLINE` or publishing sibling
services. Because V595 already showed raw `esoc0` close can cause reference
count mismatch, this path should not be repeated as an action primitive.

## Next Gate

Do not retry CNSS daemon, service-manager, Wi-Fi HAL, scan, or connect from this
state. The next useful step is a host-only Android/native comparison of the
`mdm3/esoc0` trigger path:

- Android init/service action that makes `mdm3` reach `ONLINE`
- sysfs or vendor service responsible for sibling sysmon publication
- timing between `sysmon-qmi` modem SSCTL and service-notifier `180/74`
- whether `esoc0` requires an ioctl/property/service path instead of raw open

Only after `mdm3=ONLINE` and service-notifier `180/74` are reproduced in native
should a CNSS-only gate be retried.
