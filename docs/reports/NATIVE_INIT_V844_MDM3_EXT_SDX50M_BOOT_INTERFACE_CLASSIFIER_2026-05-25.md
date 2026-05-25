# Native Init V844 mdm3/ext-sdx50m Boot Interface Classifier Report

## Result

- decision: `v844-mdm3-ext-sdx50m-boot-interface-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_mdm3_ext_sdx50m_boot_interface_classifier_v844.py`
- evidence: `tmp/wifi/v844-mdm3-ext-sdx50m-boot-interface-classifier/`

## Scope

V844 was host-only. It did not contact the device, send QRTR/QMI payloads, open
`esoc0`, write GPIO/sysfs/debugfs, start service-manager, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP, change routes, ping externally, write
boot images, write partitions, or flash a custom kernel.

## Key Signals

| Signal | Value |
| --- | --- |
| DTS node | `qcom,mdm3` |
| Compatible | `qcom,ext-sdx50m` |
| Link info | `0305_01.01.00` |
| SSCTL instance | `<0x10>` / `16` |
| Sysmon id | `<0x14>` / `20` |
| AP→MDM status GPIO | `0x87` |
| MDM→AP status GPIO | `0x8e` |
| AP→MDM soft reset GPIO | present |
| ICNSS service-notifier behavior | non-DOWN notifications are not the initial boot trigger |
| ICNSS WLFW path | QRTR service 69 arrival via `wlfw_new_server()` |
| Native lower-window state | `mss=ONLINE`, `mdm3=OFFLINING` |
| Missing Wi-Fi markers | no WLFW, no BDF, no FW-ready, no `wlan0` |

## Interpretation

The previous model treated `msm/modem/wlan_pd` as the next state transition on
the internal MPSS path. The DTS/source evidence requires a narrower model:
`mdm3` is an external SDX50M/eSoC path with AP/MDM GPIO handshake and SSCTL
instance `16`. Native can bring the internal `mss` path to `ONLINE`, but the
external `mdm3` path remains `OFFLINING`; therefore WLFW service 69 never
appears and ICNSS never reaches BDF/FW-ready/`wlan0`.

Repeating service-notifier listener probes or broad `cnss-daemon` launcher
repairs is not the next useful step. The next useful gate is to classify the
safe read-only mdm3/ext-sdx50m eSoC boot interface surface before any write or
HAL/connect action.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm3_ext_sdx50m_boot_interface_classifier_v844.py
python3 scripts/revalidation/native_wifi_mdm3_ext_sdx50m_boot_interface_classifier_v844.py \
  --out-dir tmp/wifi/v844-plan-check \
  plan
python3 scripts/revalidation/native_wifi_mdm3_ext_sdx50m_boot_interface_classifier_v844.py \
  --out-dir tmp/wifi/v844-mdm3-ext-sdx50m-boot-interface-classifier \
  run
```

Result:

```text
decision: v844-mdm3-ext-sdx50m-boot-interface-selected
pass: True
device_commands_executed: False
esoc0_open_executed: False
gpio_write_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V845 should capture a read-only live mdm3/ext-sdx50m eSoC GPIO/sysfs surface
snapshot. Keep raw `esoc0` open, GPIO/sysfs writes, Wi-Fi HAL, scan/connect,
DHCP/routes, credentials, external ping, and boot-image work blocked.
