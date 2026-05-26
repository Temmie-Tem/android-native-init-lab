# Native Init V997 Current-Boot SELinux Domain Proof Plan

## Goal

Refresh the current boot SELinux setup and prove the service-window critical
domains before another Android service-window retry.

V997 follows V994/V995/V996:

- V994 selected current-boot SELinux refresh before service-window retry.
- V995 added helper `v169` coverage for `wificond` and `vndservicemanager`.
- V996 deployed helper `v169`.

## Scope

1. Mount or verify `selinuxfs`.
2. Run V490 current-boot policy-load proof with helper `v169`.
3. Run V997 post-load domain proof for:
   - `u:r:servicemanager:s0`
   - `u:r:hwservicemanager:s0`
   - `u:r:vndservicemanager:s0`
   - `u:r:wificond:s0`
   - `u:r:hal_wifi_default:s0`
4. Stop before any Android service-window actor starts.

## Guardrails

- No service-manager, Wi-Fi HAL, `wificond`, CNSS daemon, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO write, sysfs write, or debugfs write.
- V490 may write the compiled policy once to `/sys/fs/selinux/load`.
- V997 itself must not load policy; it only proves post-load domain handoff.

## Success Criteria

- V401 `selinuxfs` mount PASS.
- V490 current-boot policy-load PASS.
- All five target domains match after static post-exec proof.
- Postflight process and Wi-Fi link surfaces remain clean.

## Next

If V997 passes, run one bounded Android service-window retry while current-boot
policy-load remains active. The retry must still block scan/connect,
credentials, DHCP/routes, external ping, and direct eSoC trigger.
