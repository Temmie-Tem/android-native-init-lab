# Native Init V788 Clean-DSP Lower Readback Plan

## Goal

Run one bounded stock-v724 gate that combines the now-proven clean-DSP
precondition with the current lower companion/CNSS-only readback path.

## Scope

- Arm only `/cache/native-init-sibling-fwssctl-v641`.
- Reboot back into stock `A90 Linux init 0.9.68 (v724)`.
- Refresh current-boot SELinux runtime prerequisites:
  - V401 SELinuxfs mount;
  - V490 policy-load proof.
- Run only the lower companion CNSS-only observer:
  - `qrtr-ns`;
  - `rmt_storage`;
  - `tftp_server`;
  - `pd-mapper`;
  - `cnss_diag`;
  - `cnss-daemon`.
- Capture QRTR, RPMSG, dmesg marker, process, and cleanup evidence.

## Hard Gates

- No custom kernel flash.
- No boot image or partition write.
- No `esoc0` open.
- No subsystem state write.
- No module load/unload or bind/unbind.
- No service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect, credential
  use, DHCP, route change, or external ping.
- Stop if a `pm_qos`, reference-count, esoc, or equivalent warning boundary
  appears.

## Success Criteria

V788 is successful if:

1. the inline clean-DSP proof passes in the same cycle;
2. V401 and V490 pass after the clean-DSP reboot;
3. the CNSS-only lower companion contract is observed and cleaned up;
4. the device returns to healthy v724 after cleanup;
5. the run classifies whether WLFW/service69, MHI/QCA6390, service-notifier, or
   only QRTR/sysmon progression is present.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_clean_dsp_lower_readback_v788.py
python3 scripts/revalidation/native_wifi_clean_dsp_lower_readback_v788.py plan
python3 scripts/revalidation/native_wifi_clean_dsp_lower_readback_v788.py run \
  --assume-yes \
  --allow-arm-clean-dsp \
  --allow-reboot \
  --allow-cleanup-umount \
  --allow-system-mount \
  --allow-selinuxfs-mount \
  --allow-policy-load \
  --allow-firmware-mounts \
  --allow-subsys-modem-holder \
  --allow-cnss-start-only \
  --allow-cleanup-reboot
```

## Expected Next Routing

- WLFW/service69 or `wlan0` appears: capture interface/BDF/fw-ready state before
  scan/connect.
- Service-notifier appears without WLFW: classify WLAN-PD-to-MHI/ICNSS gap.
- Warning boundary appears: stop, document, and do not widen live actions until
  the warning source is classified.
