# Native Init V603 QRTR-First Service-Manager Proof Plan

- date: `2026-05-22 KST`
- status: `planned`; helper v101 preparation
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v101_deploy_preflight.py`

## Objective

Test the V602 ordering hypothesis without starting Wi-Fi HAL or attempting
network bring-up.

V598 proved that native can reach QRTR TX, modem `sysmon-qmi`, and
service-notifier `180` when the modem companion stack starts before
service-manager, but `cnss-daemon` then hits binder transaction failures.

V601 proved that adding service-manager clears those binder transaction
failures, but it loses service-notifier `180`. V603 therefore needs a bounded
hybrid order:

```text
qrtr-ns
  -> rmt_storage
  -> tftp_server
  -> pd-mapper
  -> servicemanager
  -> hwservicemanager
  -> vndservicemanager
  -> cnss_diag
  -> cnss-daemon
```

The proof is only useful if it preserves both earlier advances:

- V598's lower QRTR/sysmon/service-notifier `180` path;
- V601's service-manager/binder-clean runtime.

## Implementation

1. Add helper mode
   `wifi-companion-qrtr-first-vnd-service-manager-start-only`.
2. Keep `subsys-hold-open-proof` and existing companion modes intact.
3. Delay service-manager start until after `qrtr-ns` has a short lower-modem
   publication window.
4. Delay CNSS start until after `vndservicemanager` has been spawned.
5. Build a static ARM64 helper artifact and verify the required mode/order
   strings.
6. Add a V603 deploy/preflight wrapper that installs only
   `/cache/bin/a90_android_execns_probe` when explicitly approved.

## Live Preconditions

Before running a V603 live proof on a fresh native boot:

1. Mount Android system/vendor/runtime materials read-only.
2. Mount SELinuxfs if absent.
3. Load native SELinux policy with the already bounded V490 path.
4. Verify helper v101 is present on the device.
5. Verify `/vendor/firmware_mnt` and `/vendor/firmware-modem` are mounted.
6. Hold only `subsys_modem`; do not open or hold `esoc0`.

## Guardrails

- No boot image write.
- No persistent partition write.
- No daemon autostart outside the bounded helper window.
- No service-manager run unless the exact V603 live gate is selected.
- No Wi-Fi HAL, `wificond`, supplicant, or hostapd start.
- No `qcwlanstate` write.
- No scan/connect/link-up.
- No credential, DHCP, route, or external ping.
- Reboot cleanup remains the expected post-run cleanup path for modem holder
  experiments.

## Success Criteria

Preparation succeeds when:

- helper source contains the new QRTR-first mode;
- local static helper artifact reports `a90_android_execns_probe v101`;
- local static helper artifact contains the QRTR-first order string;
- deploy wrapper plan/preflight refuses mutation without the exact V603 deploy
  phrase;
- documentation and index entries are committed.

The later live proof succeeds only if:

- `service_notifier_180 > 0`;
- `binder_transaction_failed == 0`;
- QRTR TX and `sysmon-qmi` remain present;
- cleanup leaves no residual companion/service-manager processes.

## Failure Classification

- `service_notifier_180=0` with binder clean: service-manager still suppresses
  lower QMI publication timing; delay/order needs adjustment.
- `binder_transaction_failed>0` with service-notifier `180`: service-manager
  was too late or not visible to `cnss-daemon`.
- `service_notifier_180>0` and binder clean but no WLFW service `69`: next gap
  is service-registry/WLFW publication, not qcwlanstate or Wi-Fi HAL.
- WLFW service `69`, BDF, FW-ready, or `wlan0` appears: only then prepare the
  next bounded Wi-Fi HAL or driver-state gate.

## Next Gate

V603 live proof should run after helper v101 deploy and current-boot runtime
refresh. It must not scan, connect, use credentials, run DHCP, alter routing,
or ping externally.
