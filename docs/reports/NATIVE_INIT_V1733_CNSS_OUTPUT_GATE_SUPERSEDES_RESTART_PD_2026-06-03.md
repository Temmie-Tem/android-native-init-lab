# Native Init V1733 CNSS Output Gate Supersedes Restart-PD Candidate

## Summary

- Cycle: `V1733`
- Type: host-only correction / stale WIP supersession
- Decision: `v1733-cnss-output-gate-supersedes-restart-pd-pass`
- Result: `PASS`

## Corrections Applied

- Retract the QCACLD-register premise: `boot_wlan` / QCACLD registration is not a WLFW server trigger. ICNSS driver registration waits for FW-ready and must not be added as a `wlfw_start` trigger.
- Treat native `wlfw_start_seen=0` in dmesg as a measurement artifact unless non-log control-flow evidence also misses `wlfw_start`. `cnss-daemon` logs through Android logging, and native kmsg visibility is not a reliable proof of control-flow absence.
- Stop adding PM/service-window actors for this branch. V1683/V1686 already falsified that path, and PM-service Binder `-22` is a known dead end.

## Superseded WIP

The uncommitted V1733 restart-PD host classifier was discarded. Its proposed next live step would have sent `QMI_SERVREG_NOTIF_RESTART_PD_REQ_V01`, which is an active modem-PD request rather than the requested read-only CNSS-output gate. It is not part of the active plan.

## Read-only Gate Status

The requested CNSS-output gate has already been run and reconciled by current evidence:

- V1725 ran the property/output visibility route with `persist.vendor.cnss-daemon.kmsg_logging=1` and `persist.vendor.cnss-daemon.debug_level=4`.
- V1725 label: `cnss-output-still-invisible`.
- V1727 and V1731 non-log evidence proves `cnss-daemon` reaches `wlfw_start`, starts `wlfw_service_request`, and creates the worker thread.
- V1731 late service-notifier listener reaches the endpoint but receives WLAN-PD `UNINIT`, no state-up indication, no WLFW service 69, and no `wlanmdsp` request.

## Fixed Label

- Label: `wlfw-start-reached-wlan-pd-uninit-downstream-block`
- Active blocker: modem-side WLAN-PD state-up / WLFW service 69 publication.

The missing native `wlfw_start` dmesg line is no longer treated as a blocker. The correct interpretation is that `cnss-daemon` reaches its WLFW start path and waits on a modem-side event that native still lacks.

## Next Direction

- Do not repeat output-visibility, PM/service-window actor, `boot_wlan`, restart-PD, eSoC/RC1, fake-ONLINE, or timing-window variants from this result.
- If a refresh is needed, rerun the V1725-style CNSS-output gate exactly once with the same read-only scope and labels.
- Otherwise, the next useful work is host-only classification of Android-good versus native evidence for what makes the internal modem move `msm/modem/wlan_pd` from `UNINIT` to `UP` and publish WLFW service 69.

## Safety Scope

This correction performed host-only documentation and WIP cleanup only. It did not contact the device, flash, reboot, send QMI payloads, start service-manager/PM actors, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
