# V1049 PM Full-Contract with Modem Holder Plan

## Goal

Run a bounded live gate with helper `v178` to test the V1047 hypothesis:
opening `/dev/subsys_modem` in a modem pre-holder before `pm_proxy_helper` should
avoid the first-opener PIL block and allow the Android PM fd contract to form.

## Preconditions

- V1048 deployed helper `v178` to `/cache/bin/a90_android_execns_probe`.
- Current boot must refresh SELinux state before actor exec:
  1. V401 selinuxfs mount
  2. `mountsystem ro`
  3. V490 policy-load proof using helper v178 sha
  4. PM SELinux domain proof over the four PM domains

## Inputs

- Live runner:
  `scripts/revalidation/native_wifi_pm_full_contract_with_modem_holder_live_v1049.py`
- Helper sha256:
  `7df75c618f58d599ece1a6017f66040aff57badb8955a70e07de2a77a3561c75`
- V1048 deploy evidence:
  `tmp/wifi/v1048-execns-helper-v178-deploy/manifest.json`

## Method

1. Verify helper v178 sha/marker.
2. Run current-boot SELinux preconditions.
3. Run the matrix order:
   `after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder`.
4. Require `--require-android-selinux-exec-match` through the runtime-domain
   guard path.
5. Confirm these two gate outputs:
   - `modem_pre_holder_confirmed=1`
   - `pm_full_contract_seen=1`
6. Cleanup by reboot if any actor is not proven stopped.

## Hard Gates

- No `ks`, MHI pipe transfer, Wi-Fi HAL, `wificond`, scan/connect, credentials,
  DHCP/routes, external ping, controller eSoC notify, BOOT_DONE spoofing, boot
  image write, partition write, firmware mutation, GPIO write, sysfs write, or
  debugfs write.
- `/dev/subsys_esoc0` remains gated by WLFW precondition.

## Success Criteria

- Runtime-domain guard matches all required PM domains.
- `modem_pre_holder_confirmed=1`.
- `pm_full_contract_seen=1` with both `pm_proxy_helper` and `pm-service` holding
  `/dev/subsys_modem`.
- No forbidden Wi-Fi or eSoC action occurs.
- Cleanup restores `bootstatus`/`selftest fail=0`.

## Next

If pre-holder is not confirmed, classify whether the holder child opens the
wrong namespace path. If PM fd contract appears, proceed to post-PM-fd WLFW path
classification before any Wi-Fi HAL or scan/connect gate.
