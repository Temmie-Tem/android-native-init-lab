# V1055 PM Full-Contract with Modem Holder v180 Plan

## Goal

Rerun the bounded PM full-contract-with-modem-holder live gate using deployed
helper `v180` to classify the V1053 plain-open fallback behavior.

## Preconditions

- V1054 deployed helper `v180` to `/cache/bin/a90_android_execns_probe`.
- Current boot must refresh SELinux state before actor exec:
  1. V401 selinuxfs mount
  2. `mountsystem ro`
  3. V490 policy-load proof using helper v180 sha
  4. PM SELinux domain proof over the four PM domains

## Inputs

- Live runner:
  `scripts/revalidation/native_wifi_pm_full_contract_with_modem_holder_live_v1055.py`
- Helper sha256:
  `f260583dc99cc65390ffb719ba0c2618cbbbc25a523f0b1e4fc0a07e93df9641`
- V1054 deploy evidence:
  `tmp/wifi/v1054-execns-helper-v180-deploy/manifest.json`

## Method

1. Verify helper v180 sha/marker.
2. Run current-boot SELinux preconditions.
3. Run order:
   `after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder`.
4. Inspect the new V1053 fields:
   - `modem_pre_holder_nonblock_errno`
   - `modem_pre_holder_plain_retry`
   - `modem_pre_holder_first_errno`
   - `modem_pre_holder_confirmed`
   - `pm_full_contract_seen`
5. Cleanup by reboot if any actor is not proven stopped.

## Hard Gates

No `ks`, MHI pipe transfer, Wi-Fi HAL, `wificond`, scan/connect, credentials,
DHCP/routes, external ping, controller eSoC notify, BOOT_DONE spoofing, boot
image write, partition write, firmware mutation, GPIO write, sysfs write, or
debugfs write. `/dev/subsys_esoc0` remains WLFW-precondition gated.

## Success Criteria

- Runtime-domain guard does not block PM actor exec domains.
- Matrix order is active.
- The nonblocking errno and plain retry outcome are recorded.
- Cleanup restores `bootstatus`/`selftest fail=0`.

## Next

If plain open blocks, stop treating this as a path/flag issue and classify the
missing Android first-opener/PIL precondition instead.
