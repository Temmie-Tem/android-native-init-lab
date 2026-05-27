# V1129 Post-Policy Global Firmware Mount-only Plan

Date: `2026-05-27`

## Goal

Test whether global firmware visibility is the missing prerequisite behind the
V1128 `/dev/subsys_modem` `__subsystem_get` blocker, while preserving the
post-policy provider-positive CNSS PM path.

## Rationale

V1128 used helper-private firmware mounts. That repaired userspace
`pm-service`/CNSS PM flow after V490, but kernel `firmware_class.path` still
uses the global namespace. A blocked `open("/dev/subsys_modem")` can therefore
still be caused by missing global firmware visibility.

V1129 replays the same class of CNSS PM observer with global firmware mounts,
but without a global `/dev/subsys_modem` holder.

## Live Gate

1. Confirm native init is healthy.
2. Mount Android system read-only.
3. Run V401 selinuxfs mount proof.
4. Run V490 current-boot policy-load proof.
5. Start NCM/tcpctl for host transport.
6. Run V1121 firmware mount-only provider live gate with helper `v212`
   overrides and V1129 evidence paths.
7. Let the runner perform cleanup reboot.
8. Confirm post-reboot native health and no residual PM/service-manager/CNSS
   actors.
9. Classify the result host-only.

## Guardrails

- No global `/dev/subsys_modem` holder.
- No `/dev/subsys_esoc0` open.
- No eSoC ioctl/control.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credentials, DHCP/route, or external ping.
- No partition write, boot image write, or flash.
- Cleanup reboot is required after global firmware mount live testing.

## Success Criteria

V1129 passes diagnostically if:

- V401 and V490 pass;
- global firmware mount targets are visible;
- provider visibility is present;
- CNSS PM client register/connect returns `0x0`;
- Wi-Fi HAL, scan/connect, credentials, DHCP/route, external ping, and
  `/dev/subsys_esoc0` remain false;
- the result distinguishes one of:
  - global firmware mount-only advances mss/mdm3/WLFW; or
  - global firmware mount-only is insufficient and the first-opener/holder
    contract remains necessary.

## Expected Next

If global firmware mount-only remains insufficient, V1130 should combine the
post-policy provider-positive CNSS order with a bounded `/dev/subsys_modem`
first-opener contract, rather than moving to Wi-Fi HAL or scan/connect.
