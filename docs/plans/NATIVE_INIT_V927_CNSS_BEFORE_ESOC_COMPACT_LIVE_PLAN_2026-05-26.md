# Native Init V927 CNSS-before-eSoC Compact Live Plan

## Goal

Run the V923 CNSS-before-eSoC live gate again with helper `v153` and compact
CNSS surface output. V927 is intended to preserve the final helper contract keys
that were at risk of stdout truncation in the full CNSS surface capture.

## Gate

- Use deployed `/cache/bin/a90_android_execns_probe` helper `v153`.
- Force `--cnss-surface-mode compact`.
- Permit only the V923 live actors:
  - `mountsystem ro`;
  - SELinuxfs mount/cleanup;
  - private property root;
  - `/vendor/bin/pm-service`;
  - `/vendor/bin/mdm_helper`;
  - `/vendor/bin/cnss_diag`;
  - `/vendor/bin/cnss-daemon -n -l`;
  - `/dev/subsys_esoc0` child open only if the WLFW precondition marker appears.

## Forbidden

- No service-manager start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP, route change, or external ping.
- No controller eSoC notify or BOOT_DONE spoofing.
- No module load/unload, boot image write, partition write, firmware mutation,
  GPIO write, sysfs write, or debugfs write.

## Success Criteria

- Local and remote helper hash, marker, and mode match helper `v153`.
- Helper output contains the CNSS-before-eSoC begin/end contract.
- Compact surface prevents final result loss from transcript truncation.
- Forbidden-action flags remain false.
- Device postflight is healthy or cleanup reboot restores health.

## Failure Criteria

- Remote helper mismatch.
- Missing explicit live flags.
- Forbidden action detected.
- Helper mode does not begin/end.
- Cleanup required but post-cleanup health cannot be verified.

## Command

```bash
python3 scripts/revalidation/native_wifi_mdm_helper_cnss_before_esoc_compact_live_v927.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-before-subsys-trigger-capture \
  --allow-cleanup-reboot \
  --assume-yes \
  run
```

## Next

- If WLFW precondition appears and `/dev/subsys_esoc0` trigger is clean, classify
  WLAN-PD, WLFW, BDF, and `wlan0` deltas before any Wi-Fi HAL or scan/connect.
- If WLFW precondition is still missing, classify the compact runtime namespace
  and CNSS actor surface instead of repeating full-output live runs.
