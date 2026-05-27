# V1128 Post-Policy Private Firmware CNSS PM Plan

Date: `2026-05-27`

## Goal

Replay the private-firmware CNSS PM observer after the V490 current-boot
SELinux policy load and classify whether the blocker moves beyond
`pm-service` provider registration.

## Rationale

V1127 proved that V490 changes `pm-service` Binder `addService()` from
`PERMISSION_DENIED (-1)` to `OK (0)` and restores
`vendor.qcom.PeripheralManager` visibility. The next useful gate is therefore
not another `addService` trace. It is the same private-firmware CNSS PM path
with V490 as an explicit precondition.

## Live Gate

1. Confirm native init v724 and selftest.
2. Mount Android system read-only.
3. Run V401 selinuxfs mount proof.
4. Run V490 native SELinux policy-load proof.
5. Start NCM/tcpctl only for host transport.
6. Run V1124 private-firmware PM observer live with CNSS daemon start allowed.
7. Capture post-pass process surface.
8. Cleanup reboot if any observer child is not proven stopped.
9. Classify the evidence host-only.

## Guardrails

- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credentials.
- No DHCP/route or external ping.
- No `/dev/subsys_esoc0` open.
- No partition write, boot image write, or flash.
- Tracefs writes are bounded to the V1124 observer and must be removed.
- Cleanup reboot is required if `pm_proxy_helper` or related observer actors
  remain unproven stopped.

## Success Criteria

V1128 passes diagnostically if:

- V401 and V490 pass;
- V1124 post-policy replay preserves private firmware mounts;
- `vndservicemanager` is ready and provider visibility is present;
- `cnss-daemon` reaches PM client register and connect with return `0x0`;
- PM server Binder side reaches register and connect with return `0x0`;
- Wi-Fi HAL, scan/connect, credentials, DHCP/route, and external ping remain
  false;
- the remaining blocker is classified as a lower modem/eSoC path rather than
  service-manager policy or PM register/connect;
- cleanup reboot returns the device to a clean native state.

## Expected Next

If V1128 reaches CNSS PM connect, V1129 should classify the lower
`/dev/subsys_modem` and `mdm3`/eSoC transition before attempting any Wi-Fi HAL
start or scan/connect gate.
