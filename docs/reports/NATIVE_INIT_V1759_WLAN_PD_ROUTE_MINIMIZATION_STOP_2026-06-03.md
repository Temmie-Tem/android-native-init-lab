# Native Init V1759 WLAN-PD Route-minimization Stop

## Summary

- Cycle: `V1759`
- Type: host-only reclassification / track stop
- Decision: `v1759-route-minimization-superseded-by-v1753-firmware-request-diff`
- Result: PASS
- Active redirect label: `firmware-not-requested`
- Primary evidence: `docs/reports/NATIVE_INIT_V1753_WLAN_PD_FIRMWARE_REQUEST_DIFF_2026-06-03.md`

## Reclassification

The V1758/V1759 provider-visibility direction is superseded for the immediate
`wlan0` goal.  It can explain a CNSS PeripheralManager visibility gap, but it
does not answer the decisive modem-side question: Android asks `tftp_server` for
`wlanmdsp.mbn`, while the native SM route that reaches the WLFW worker does not.

V1753 already ran the required Android-good vs native firmware-request diff:

- Android-good captured `tftp_server` requests for `wlanmdsp.mbn`.
- Native V1736 SM route reached `wlfw_start`, `wlfw_service_request`, and WLFW
  worker creation.
- Native V1736 had `tftp_server` running, but `requested_wlanmdsp=0`.
- WLFW service 69 stayed absent and `wlan_pd` stayed `UNINIT`.

The fixed label is therefore `firmware-not-requested`.

## Active Blocker

The blocker is downstream of the WLFW worker and upstream of firmware serving:
the internal modem never starts `msm/modem/wlan_pd` and therefore never requests
`wlanmdsp.mbn`.

This is not currently a route-minimization, tracefs-plumbing, PM actor, QCACLD,
eSoC, RC1, or Wi-Fi HAL problem.

## Stop Conditions

Do not continue the following tracks for the current `wlan0` goal:

- PM/service-window actor expansion;
- V1759 provider-positive composition;
- route minimization or uprobe re-proof of the V1727/V1736 SM route;
- `boot_wlan` / QCACLD registration as a WLFW trigger;
- restart-PD request;
- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes;
- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Next Work

Hand back after this label.  The next cycle should be a separately approved
modem-side WLAN-PD autoload/request-trigger analysis, starting from why Android
causes a `wlanmdsp.mbn` TFTP request but the native SM route does not.
