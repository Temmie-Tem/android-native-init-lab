# Native Init V1061 Global Firmware PM Full-Contract Plan

Date: `2026-05-27`

## Goal

Re-run the Android PM full-contract-with-modem-holder gate while keeping the
global firmware partitions mounted and a global `/dev/subsys_modem` holder open.

V1055 failed before the PM fd contract because the helper-private modem
pre-holder did not report success.  V1058 then showed the current native boot
had no global firmware mounts at the kernel `firmware_class.path`, while V1059
and V1060 proved that global firmware mounts plus a global modem holder restore
modem PIL readiness through QRTR TX and `sysmon-qmi`.  V1061 tests whether that
fixed lower prerequisite is enough for helper v180 to reach the PM fd contract.

## Method

1. Refresh current-boot SELinux prerequisites with V401, `mountsystem ro`, and V490.
2. Mount `apnhlos` and `modem` firmware partitions read-only in the global namespace.
3. Start a global `/dev/subsys_modem` holder and wait for QRTR RX.
4. Run helper v180 mode `wifi-companion-mdm-helper-cnss-service-manager-matrix` with order `after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder`.
5. Record PM fd contract, `mdm_helper` eSoC fd, service-manager/CNSS state, QRTR services, MHI/WLFW/BDF/`wlan0` markers, and cleanup by reboot.

## Success Criteria

- V1061 evidence is written under `tmp/wifi/v1061-global-firmware-pm-full-contract/`.
- Global firmware mount and modem blob visibility pass.
- Global `/dev/subsys_modem` holder opens and `mss` reaches `ONLINE`.
- Helper v180 reports the PM full-contract-with-modem-holder matrix.
- The runner classifies whether:
  - helper modem pre-holder is now confirmed;
  - `pm_proxy_helper` and `per_mgr` hold `/dev/subsys_modem`;
  - `mdm_helper` holds `/dev/esoc-0`;
  - WLFW/service69/MHI/BDF/`wlan0` appears.

## Hard Gates

- No Wi-Fi HAL, `wificond`, `IWifi.start`, `qcwlanstate`, scan/connect/link-up, credentials, DHCP/routes, or external ping.
- No eSoC controller ioctl, notify, BOOT_DONE spoofing, GPIO write, sysfs/debugfs write, module load/unload, firmware mutation, partition write, boot image write, or Android boot handoff.
- `/dev/subsys_esoc0` remains gated by the existing helper WLFW-precondition path.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_full_contract_global_firmware_v1061.py

python3 scripts/revalidation/native_wifi_pm_full_contract_global_firmware_v1061.py \
  --out-dir tmp/wifi/v1061-global-firmware-pm-full-contract \
  --v490-manifest tmp/wifi/v1061-v490-policy-load/manifest.json \
  --proof-id v1061-global-firmware-pm-full-contract \
  plan

python3 scripts/revalidation/native_wifi_pm_full_contract_global_firmware_v1061.py \
  --out-dir tmp/wifi/v1061-global-firmware-pm-full-contract \
  --v490-manifest tmp/wifi/v1061-v490-policy-load/manifest.json \
  --proof-id v1061-global-firmware-pm-full-contract \
  run
```
