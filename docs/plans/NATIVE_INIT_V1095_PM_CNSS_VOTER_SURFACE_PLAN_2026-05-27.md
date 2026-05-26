# Native Init V1095 PM CNSS Voter Surface Plan

## Goal

Extend the V1094 provider-positive PM observer window by starting only
`cnss-daemon` after `pm-service` and `pm-proxy` have registered
`vendor.qcom.PeripheralManager`, then capture whether that first CNSS-side
client/voter causes `/dev/subsys_modem`, mdm3, WLFW service `69`, or `wlan0` to
advance.

## Scope

- Deploy and use `a90_android_execns_probe v206`.
- Keep the V490 SELinux policy-load precondition.
- Start only the service-manager trio, `pm_proxy_helper`, `pm-service`,
  `pm-proxy`, bounded `vndservice list` queries, and bounded `cnss-daemon`.
- Capture `after_cnss_daemon` fd matches for `pm-service` and
  `pm_proxy_helper` against `/dev/subsys_modem` and `/dev/vndbinder`.
- Capture `after_cnss_daemon` mdm3, `wlan0`, ICNSS, QRTR, and compact klog
  state.
- Use serial `a90ctl` for the long helper script because `a90_tcpctl run` has a
  10 second device-side timeout.

## Guardrails

- No `mdm_helper`.
- No Wi-Fi HAL, supplicant, hostapd, scan, connect, DHCP, route, credential use,
  or external ping.
- No `/dev/subsys_esoc0` open, eSoC ioctl, GPIO write, partition write, flash,
  or reboot unless cleanup is explicitly required.
- QRTR readback remains nameservice lookup/readback for services `69`, `74`,
  and `180`; no QMI payload is sent.
- `cnss-daemon` is allowed only after both PM provider queries are observed.

## Implementation

1. Add `--pm-observer-start-cnss-after-provider` to the PM observer mode.
2. Require `--pm-observer-continue-after-provider` when the CNSS voter flag is
   used.
3. Continue from the after-`pm-proxy` provider-positive query to
   `cnss-daemon`.
4. Capture `after_cnss_daemon` fd/lower-surface snapshots.
5. Add V1095 deploy/live wrappers for helper v206 and CNSS-voter decisions.

## Success Criteria

- Helper v206 deploy/preflight passes.
- V490 policy-load proof passes before the live gate.
- `vndservicemanager_readiness.ready=1`.
- `vendor.qcom.PeripheralManager` is observed after `pm-service`, `pm-proxy`,
  and `cnss-daemon` phases.
- `after_cnss_daemon` lower-surface snapshot has `begin=1` and `end=1`.
- Wi-Fi HAL/start/connect/link-up/credential/DHCP/external ping remain false.

## Decision Rules

- `mdm3_state=ONLINE`, `wlan0_exists=1`, or WLFW service `69` readback events
  mean lower-surface progress and the next gate should classify the transition.
- Any `/dev/subsys_modem` fd on `pm-service` or `pm_proxy_helper` means the PM
  fd contract advanced and the next gate should classify the post-fd lower
  blocker.
- Provider-positive with `cnss-daemon`, no PM subsystem fd, `mdm3=OFFLINING`,
  and no WLFW means `cnss-daemon` alone is not the missing PM voter trigger;
  the next gate should classify the missing CNSS request or lower eSoC trigger.
