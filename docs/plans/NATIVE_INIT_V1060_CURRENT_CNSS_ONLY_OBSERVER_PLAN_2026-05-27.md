# Native Init V1060 Current CNSS-only Observer Plan

Date: `2026-05-27`

## Goal

Run the current-build CNSS-only observer after refreshing the current-boot
SELinux and firmware-mount prerequisites.  The goal is to determine whether
the validated lower path can progress from modem PIL readiness into CNSS,
WLFW, MHI, BDF, or `wlan0`, without crossing into service-manager, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, or external ping.

## Inputs

- Current native v724 boot over the ACM bridge.
- Helper `/cache/bin/a90_android_execns_probe` v180:
  `f260583dc99cc65390ffb719ba0c2618cbbbc25a523f0b1e4fc0a07e93df9641`.
- V1059 firmware mount refresh:
  `docs/reports/NATIVE_INIT_V1059_FIRMWARE_MOUNT_REFRESH_2026-05-27.md`.
- Existing lower-window references:
  - `tmp/wifi/v731-firmware-mounted-modem-holder/manifest.json`
  - `tmp/wifi/v732-cnss2-mhi-holder-window/manifest.json`
  - `tmp/wifi/v734-current-post-sysmon-route/manifest.json`

## Method

1. Mount SELinuxFS with the bounded V401 toybox-backed executor.
2. Mount Android system read-only with `mountsystem ro`.
3. Load Android split SELinux policy through the V490 policy-load proof using helper v180.
4. Run `native_wifi_current_cnss_only_observer_v735.py` as V1060 with helper v180 and the refreshed V490 manifest.
5. In the live window, mount firmware partitions, open the modem holder, start only the lower companion set, then start `cnss_diag` and `cnss-daemon`.
6. Observe dmesg, QRTR readback, MHI/WLFW/BDF/wlan markers, and cleanup by reboot.

## Success Criteria

- V401 SELinuxFS mount proof passes.
- V490 policy-load proof passes without init reexec, daemon start, Wi-Fi HAL start, or Wi-Fi bring-up.
- V1060 writes private evidence under `tmp/wifi/v1060-current-cnss-only-observer/`.
- The observer records:
  - firmware mount and modem blob visibility;
  - `/dev/subsys_modem` holder open result;
  - lower companion/CNSS-only contract result;
  - QRTR service 69 readback result;
  - `qrtr_rx`, `qrtr_tx`, `sysmon_qmi`, service-notifier, WLAN-PD, MHI, WLFW, BDF, and `wlan0` markers.

## Hard Gates

- No service-manager start.
- No Wi-Fi HAL start.
- No `wificond`, supplicant, scan/connect/link-up, credentials, DHCP/routes, or external ping.
- No `/dev/subsys_esoc0` open, eSoC ioctl, GPIO write, sysfs/debugfs write, module load/unload, firmware mutation, partition write, boot image write, or Android boot handoff.

## Validation

```bash
python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v1060-v401-selinuxfs \
  --approval-phrase "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run

python3 scripts/revalidation/a90ctl.py mountsystem ro

python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v1060-v490-policy-load \
  --helper-sha256 f260583dc99cc65390ffb719ba0c2618cbbbc25a523f0b1e4fc0a07e93df9641 \
  --approval-phrase "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run

python3 scripts/revalidation/native_wifi_current_cnss_only_observer_v735.py \
  --out-dir tmp/wifi/v1060-current-cnss-only-observer \
  --helper-sha256 f260583dc99cc65390ffb719ba0c2618cbbbc25a523f0b1e4fc0a07e93df9641 \
  --helper-marker "a90_android_execns_probe v180" \
  --v490-manifest tmp/wifi/v1060-v490-policy-load/manifest.json \
  --proof-id v1060-current-cnss-only-observer run
```
