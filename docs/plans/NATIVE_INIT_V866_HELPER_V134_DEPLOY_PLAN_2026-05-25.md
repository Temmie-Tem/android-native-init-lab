# Native Init V866 Helper v134 Deploy Plan

## Goal

Deploy only helper `a90_android_execns_probe v134` to
`/cache/bin/a90_android_execns_probe` and prove checksum/version parity before
any PeripheralManager start-only proof.

## Inputs

- V865 helper artifact:
  `tmp/wifi/v865-execns-helper-v134-build/a90_android_execns_probe`
- expected sha256:
  `92792fb954de42825d328c047498c5291be803185d9897d22dd734fd9bd77582`
- wrapper:
  `scripts/revalidation/wifi_execns_helper_v134_deploy_preflight.py`
- target device build: `A90 Linux init 0.9.68 (v724)`

## Scope

1. Run plan/preflight for helper `v134`.
2. Deploy only `/cache/bin/a90_android_execns_probe` if the remote helper is
   stale.
3. Use serial transfer if NCM is unavailable.
4. Verify remote sha256 and helper usage marker after deploy.
5. Verify native health and actor-clean state after deploy.

## Hard Gates

- No `pm-service`, `pm-proxy`, `pm_proxy_helper`, `mdm_helper`, `ks`, CNSS,
  Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect/link-up, credentials,
  DHCP/routes, or external ping.
- No raw eSoC ioctl, GPIO write, sysfs/debugfs/subsystem write, module load,
  boot image write, or partition write.
- Device mutation is limited to the helper file and temporary serial staging
  files under `/cache`.

## Success Criteria

- Preflight passes with no blocker.
- Deploy result is pass or remote helper already current.
- Remote sha256 equals the V865 artifact sha256.
- Remote helper usage contains `a90_android_execns_probe v134` and the new
  `wifi-companion-peripheral-manager-init-contract-start-only` mode.
- Post-deploy selftest has `fail=0`.
- No gated Android/Wi-Fi actors are running and no Wi-Fi link is present.
