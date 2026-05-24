# Native Init V733 Holder Lower Companion Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_holder_lower_companion_v733.py`
- evidence target: `tmp/wifi/v733-holder-lower-companion/`
- prerequisites:
  - V731 `v731-firmware-mounted-modem-holder-qrtr-rx-pass`
  - V732 `v732-cnss2-mhi-holder-window-cnss2-gap-classified`
  - current-boot V401 SELinuxfs mount
  - current-boot V490 SELinux policy load

## Goal

Extend V732 by adding only the lower companion/TFTP runtime inside the
firmware-mounted `subsys_modem` holder window.

The test determines whether the missing post-QRTR-RX progression is restored by
the minimal lower stack:

```text
qrtr-ns -> rmt_storage -> tftp_server -> pd-mapper
```

## Scope

Allowed:

- mount `/vendor/firmware_mnt` and `/vendor/firmware-modem` read-only;
- open only a temporary `subsys_modem` holder;
- start only lower companion/TFTP processes in a bounded helper namespace;
- observe dmesg, `/proc/net/qrtr`, `/proc/net/dev`, process state, and cleanup;
- reboot at the end as the cleanup boundary.

Forbidden:

- no `esoc0`;
- no subsystem state writes;
- no module load/unload;
- no `cnss_diag` or `cnss-daemon`;
- no service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- no scan/connect, credential use, DHCP, route change, external ping, boot image
  write, or partition write.

## Success Classes

| class | criteria |
| --- | --- |
| `wlfw-advance` | WLFW/service `69`, BDF, or `wlan0` appears without forbidden actions |
| `mhi-advance` | MHI/QCA6390 appears but WLFW/service `69` does not |
| `sysmon-advance` | QRTR TX/sysmon returns but service-notifier/WLFW/service `69` remains absent |
| `blocked` | helper contract, firmware mount, holder, forbidden action, warning, or cleanup gate fails |

## Validation Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_holder_lower_companion_v733.py

python3 scripts/revalidation/native_wifi_holder_lower_companion_v733.py \
  --out-dir tmp/wifi/v733-holder-lower-companion-plan plan

python3 scripts/revalidation/a90ctl.py --timeout 60 mountsystem ro

python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v733-v401-current-run \
  --approval-phrase 'approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run

python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v733-v490-current-run \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --helper-sha256 547232ddb352740bb7a7f1d0f9116162584e34a536b9d9b77869ed8d838e7c89 \
  --approval-phrase 'approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run

python3 scripts/revalidation/native_wifi_holder_lower_companion_v733.py \
  --out-dir tmp/wifi/v733-holder-lower-companion run
```
