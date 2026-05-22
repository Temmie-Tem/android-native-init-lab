# Native Init V608 Helper V100 Baseline Replay Plan

- date: `2026-05-23 KST`
- status: `planned`
- target: verify whether helper v100 still reproduces the V598
  `service-notifier` `180` marker under the current native boot environment

## Context

V607 classified the strongest current gap as helper-version/runtime delta:

- V598 helper v100: no-service-manager baseline reached `service-notifier` `180`.
- V606 helper v102: same lower readiness/order/readback/timing did not reach
  `service-notifier` `180`.
- The local helper v100 artifact exists at
  `tmp/wifi/v592-a90_android_execns_probe-v100/a90_android_execns_probe`.

## Scope

V608 is a bounded live replay. It may deploy only the helper v100 artifact to
`/cache/bin/a90_android_execns_probe`, refresh V401/V490 current-boot
prerequisites, and run the V598 WLFW QRTR readback proof.

It must not start service-manager, Wi-Fi HAL, `wificond`, supplicant, or
hostapd. It must not write `qcwlanstate`, scan/connect/link-up, use
credentials, run DHCP, change routes, ping externally, flash boot images, or
write persistent partitions.

## Preconditions

1. Native version and status are healthy.
2. Serial bridge is available.
3. Local helper v100 SHA matches the wrapper expectation:
   `916b5c68a3357c79604db4532b457e30fcb9a70c99aaabb6f95519af138abd29`.
4. V401 selinuxfs mount proof passes on the current boot.
5. V490 SELinux policy-load proof passes on the current boot.
6. V598 runner preflight accepts helper marker `a90_android_execns_probe v100`.

## Execution Outline

1. Run helper v100 deploy preflight.
2. Deploy helper v100 with the exact deploy boundary.
3. Run V401/V490 current-boot prerequisites.
4. Run V598 preflight with helper v100 marker and SHA.
5. Run V598 bounded live proof with helper v100.
6. Reboot-clean and verify native status after the run.

## Success Criteria

V608 passes if it produces one of these explicit classifications:

- `v608-helper-v100-service-notifier-restored`
- `v608-helper-v100-service-notifier-still-missing`
- `v608-preflight-blocked`
- `v608-live-cleanup-review`

## Next Decision

- If helper v100 restores `service-notifier` `180`, compare helper v100/v102
  source/runtime deltas before further daemon ordering.
- If helper v100 does not restore it, treat the service-publication gap as
  nondeterministic or current-boot dependent and build a narrower post-sysmon
  observer before any Wi-Fi HAL or connection attempt.
