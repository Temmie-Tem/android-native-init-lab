# Native Init V867 PeripheralManager Init Contract Start-Only Plan

## Goal

Run the first bounded live proof of helper `v134`'s Android PeripheralManager
init-contract mode under Android node parity.

## Inputs

- deployed helper: `/cache/bin/a90_android_execns_probe`
- helper marker: `a90_android_execns_probe v134`
- helper sha256:
  `92792fb954de42825d328c047498c5291be803185d9897d22dd734fd9bd77582`
- V855 node parity evidence:
  `tmp/wifi/v855-esoc-node-parity-preflight/manifest.json`
- V860 property-clean replay evidence:
  `tmp/wifi/v860-pm-service-property-superset-replay-live/manifest.json`

## Scope

1. Verify helper `v134` is present remotely.
2. Mount system read-only and SELinuxfs surface as in previous proofs.
3. Materialize Android-equivalent `/dev/esoc-0`, `/dev/subsys_esoc0`, and
   `/dev/subsys_modem` nodes.
4. Run only
   `wifi-companion-peripheral-manager-init-contract-start-only`:
   - `vendor.per_proxy_helper /vendor/bin/pm_proxy_helper` oneshot;
   - `vendor.per_mgr /vendor/bin/pm-service` with `ioprio rt 4`;
   - property-gated `vendor.per_proxy /vendor/bin/pm-proxy`.
5. Capture runtime domain, ioprio result, fd links, postflight process state,
   node cleanup, and selftest.

## Hard Gates

- No `mdm_helper`, `ks`, CNSS, Wi-Fi HAL, wificond, supplicant, hostapd,
  scan/connect/link-up, credentials, DHCP/routes, or external ping.
- No raw eSoC ioctl, GPIO write, sysfs/debugfs/subsystem state write, module
  load, boot image write, or partition write.
- If any PM actor remains after cleanup, stop escalation and recover before any
  next live test.

## Success Criteria

- Helper mode executes and records init-contract markers.
- `per_mgr` ioprio `rt 4` is attempted and result recorded.
- `per_proxy` starts only after `init.svc.vendor.per_mgr=running` marker.
- All started actors are stopped or a cleanup blocker is explicitly classified.
- Device returns to v724 with selftest `fail=0` before any next candidate.
