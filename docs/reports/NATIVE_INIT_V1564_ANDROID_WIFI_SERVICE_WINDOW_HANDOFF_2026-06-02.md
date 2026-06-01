# Native Init V1564 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1564`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1564-test-boot-no-downstream-wifi-progress-blocked`
- Result: BLOCKED
- Reason: test boot ran and rollback verified, but strict Wi-Fi progress markers were absent
- Evidence: `tmp/wifi/v1564-android-wifi-service-window-handoff`
- Handoff/rollback pass: `True`
- Rollback attempt: `from-native`
- Strict Wi-Fi progress mode: `True`
- Wi-Fi progress pass: `False`
- Progress decision: `no-provider-no-downstream`

## Progress Classification

- `provider_trigger`: `False`
- `rc1_progress`: `False`
- `rc1_l0`: `False`
- `rc1_link_failed`: `False`
- `mhi_progress`: `False`
- `wlfw_progress`: `False`
- `bdf_progress`: `False`
- `fw_ready_progress`: `False`
- `wlan0_present`: `False`
- `connect_ready`: `False`
- `debugfs_pci_msm_case_present`: `None`
- `helper_timed_out`: `0`
- `pid1_rc1_watcher_requested`: `0`
- `pid1_rc1_watcher_result_summary`: `None`
- `pid1_rc1_watcher_result_file`: ``
- `pid1_rc1_window_sampler_requested`: `0`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: ``
- `pid1_rc1_window_sample_count`: `0`
- `pid1_rc1_window_has_post_500ms`: `False`

## Live Evidence

- Test boot flash and verify completed with `A90 Linux init 0.9.69 (v1562-service-window)`.
- The PID1 supervisor launched `wifi-companion-android-wifi-service-window-start-only`; the helper exited normally with `helper_exit_code=0` and `helper_timed_out=0`.
- Focused dmesg showed `cnss_diag`, `cnss-daemon`, and `wificond` generic netlink/binder activity, proving the service-window route executed far enough to start the selected userspace components.
- No `wlfw_start`, `wlfw_service_request`, ICNSS-QMI, BDF/regdb, FW-ready, MHI, RC1, or `wlan0` progress marker was captured.
- `wlan0` was explicitly absent after the 65 second post-boot hold.
- Rollback to `stage3/boot_linux_v724.img` completed and post-rollback selftest passed.

## Interpretation

V1564 removes one candidate: merely switching the test boot from the
post-PM observer route to the Android Wi-Fi service-window start-only route
does not reproduce the Android-good `cnss-daemon wlfw_start` /
`wlfw_service_request` contract.  The route launches and exits cleanly, but it
does not trigger the lower provider/RC1/WLFW path.

This keeps credentials, scan/connect, DHCP/routes, and external ping out of
scope.  The current gap is still below Wi-Fi connection logic: native userspace
can start the service-window components, but the Android-good WLFW request path
is not reproduced.

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation included flashing the test boot image, any bounded
in-boot actions declared by that test image's artifact contract, and
rolling back to `stage3/boot_linux_v724.img`. If enabled, native direct
rollback may restore the boot partition from a pre-staged `/cache`
rollback image when recovery ADB is unavailable.

## Images

- Test image: `tmp/wifi/v1562-android-wifi-service-window-test-boot/boot_linux_v1393_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat `no-provider-no-downstream` as diagnostic evidence, not Wi-Fi bring-up
progress.  Next gate should classify why the service-window helper exits cleanly
without producing `wlfw_start` / `wlfw_service_request`: compare helper stdout,
service-manager context, properties, sockets, and process environment against
the Android-good service-window evidence. Do not proceed to scan/connect,
credentials, DHCP/routes, or external ping until at least WLFW/BDF/FW-ready or
`wlan0` progress is proven.
