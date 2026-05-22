# Native Init V608 Helper V100 Baseline Replay Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- deploy evidence: `tmp/wifi/v608-helper-v100-20260523-002902/v100-deploy-run2/`
- V401 evidence: `tmp/wifi/v608-helper-v100-20260523-002902/v401-current/`
- V490 evidence: `tmp/wifi/v608-helper-v100-20260523-002902/v490-current/`
- preflight evidence: `tmp/wifi/v608-helper-v100-20260523-002902/v608-helper-v100-wlfw-preflight/`
- live evidence: `tmp/wifi/v608-helper-v100-20260523-002902/v608-helper-v100-wlfw-live/`

## Scope

V608 re-deployed the helper v100 artifact and replayed the V598
no-service-manager WLFW QRTR readback gate under the current native boot
environment.

It did not start service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd.
It did not write `qcwlanstate`, scan/connect/link-up, use credentials, run
DHCP, change routes, ping externally, flash boot images, or write persistent
partitions.

## Preconditions

```text
helper_v100_deploy: execns-helper-v100-deploy-pass
helper_v100_sha256: 916b5c68a3357c79604db4532b457e30fcb9a70c99aaabb6f95519af138abd29
v401_selinuxfs_decision: toybox-selinuxfs-mount-live-executor-run-pass
v490_policy_load_decision: v490-selinux-policy-load-proof-pass
v608_preflight_decision: v598-wlfw-readback-preflight-ready
```

The first deploy attempt was blocked by auto-menu `busy` before any chunk was
written. The successful replay uses `v100-deploy-run2`, where the remote helper
SHA and marker were verified as v100 before V401/V490/V598.

## Result

```text
decision: v608-helper-v100-service-notifier-still-missing
underlying_runner_decision: v598-wlfw-readback-empty
pass: True
wifi_bringup_executed: False
```

## Key Counts

```text
qrtr_rx: 1
qrtr_tx: 1
sysmon_qmi: 1
service_notifier_180: 0
wlan_pd: 0
qmi_server_connected: 0
wlfw: 0
bdf: 0
wlan_fw_ready: 0
wlan0: 0
binder_transaction_failed: 21
```

WLFW QRTR nameservice readback:

```text
send_attempted: 1
service_events: 0
end_of_list: 2
timeouts: 0
qmi_attempted: 0
```

## Timing

V608 reached the same lower modem boundary:

```text
qrtr: Modem QMI Readiness RX
qrtr: Modem QMI Readiness TX
sysmon-qmi modem SSCTL service
cnss_diag netlink
cnss-daemon netlink
```

The `service-notifier` `180` marker did not appear before CNSS, after CNSS, or
during cleanup. Binder failures still began only after `cnss-daemon` entered.

## Cleanup State

V608 used reboot cleanup. The reboot command lost the final END marker because
the device restarted, but post-reboot verification saw the expected native
version and healthy status.

```text
post_reboot_version_seen: true
post_reboot_status_healthy: true
selftest: pass=11 warn=1 fail=0
exposure_boundary: usb-local
```

## Interpretation

V607 treated helper v100/v102 as the strongest deterministic host-only delta.
V608 disproves that as a sufficient explanation: helper v100 no longer
reproduces the V598 `service-notifier` `180` marker under the current boot
state.

The blocker is now classified as a lower modem QMI service-publication
stability/precondition gap:

1. native reliably reaches QRTR RX/TX and modem `sysmon-qmi`;
2. WLFW service `69` remains absent from QRTR nameservice readback;
3. `service-notifier` `180` is not stable even with the helper version that
   produced it once;
4. binder failures are still downstream of the missing pre-CNSS publication
   window.

Direct Wi-Fi HAL, `qcwlanstate`, scan/connect, credentials, DHCP, routing, and
external ping remain premature.

## Next Gate

Recommended V609:

1. Add a no-CNSS post-sysmon observer mode.
2. Start only the lower companion layer needed for QRTR/sysmon publication:
   `qrtr-ns`, `rmt_storage`, `tftp_server`, and `pd-mapper`.
3. Hold `subsys_modem`, wait for QRTR RX/TX and modem `sysmon-qmi`, then observe
   service-notifier/QRTR for a bounded window before any CNSS daemon enters.
4. If `service-notifier` `180` appears, start CNSS only after the marker in a
   separate follow-up.
5. If it remains absent, compare Android/native lower modem publication
   preconditions instead of retrying Wi-Fi userspace.
