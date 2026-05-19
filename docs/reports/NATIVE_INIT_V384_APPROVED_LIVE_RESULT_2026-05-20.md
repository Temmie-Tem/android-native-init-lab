# Native Init v384 Approved Live Result

## Summary

- scope: approved v384 helper v15 deploy + service-manager ptrace-lite live capture.
- deployed helper: `/cache/bin/a90_android_execns_probe` v15, SHA256 `dfd543c02ccefbbbcf2fe0eb7ee168b40d40363927a63104c7aef0b9aed0bb16`.
- first approved full run: `tmp/wifi/v384-approved-full-20260520-042720`.
- fixed compact live run: `tmp/wifi/v384-approved-live-compact-20260520-044147`.
- Wi-Fi HAL start, scan, connect, DHCP, routing, credential use, and Wi-Fi bring-up were not executed.

## Host Tooling Fix

The first approved live attempt did not actually start the service-manager targets. The generated command contained 31 command tokens, while the native shell accepts at most 30 command args after `cmdv1` dispatch. The final `--allow-service-manager-start-only` token was truncated before `execve`, so the helper exited with:

```text
--capture-mode ptrace-lite requires --allow-service-manager-start-only
```

`scripts/revalidation/wifi_service_manager_start_only_live_runner.py` now compacts service-manager live commands when the command would exceed the native shell argv limit. The compact form drops only `--data-wifi-mode private-empty` for this service-manager-only smoke path, keeping `--property-root`, linkerconfig, apex libraries, Binder nodes, and `--allow-service-manager-start-only`. The resulting live command is 29 args.

A shell-wrapper approach was tested and rejected because `/cache/bin/toybox` does not provide a `sh` applet on this image.

## Live Result

Decision from `tmp/wifi/v384-approved-live-compact-20260520-044147/manifest.json`:

```text
service-manager-start-only-live-review-required
```

Observed targets:

| target | result | reason | exec | capture | postflight |
| --- | --- | --- | --- | --- | --- |
| `system-servicemanager` | `start-only-runtime-gap` | `child-exited-before-observe-window` | yes | exec + SIGABRT crash captured | helper safe |
| `system-hwservicemanager` | `start-only-reboot-required` | `process-not-proven-stopped` | yes | exec captured, observable until timeout | global clean, helper group proof failed |

The `servicemanager` path now has ptrace-lite crash evidence, including exec stop, SIGABRT stop, siginfo/register snapshots, `/proc/<pid>/status`, `/proc/<pid>/maps`, and mountinfo. stderr contains:

```text
libc: Fatal signal 6 (SIGABRT), code -1 (SI_QUEUE) in tid ... (servicemanager)
```

The `hwservicemanager` path remained observable until timeout and was terminated by the helper. The helper reaped the direct child, but `postflight_safe=0` because the process-group disappearance check was not proven inside the helper. The host-level postflight immediately after the run was clean.

## Safety Check After Live

Read-only post checks:

- `status`: rc=0, `selftest: pass=11 warn=1 fail=0`.
- `selftest`: rc=0, `fail=0`.
- process list: no `servicemanager`, `hwservicemanager`, or `vndservicemanager` process.
- `/proc/net/dev`: no `wlan*`, `swlan*`, `p2p*`, `wiphy*`, or `phy*` Wi-Fi link.
- NCM remained present; Wi-Fi bring-up remained false.

Evidence:

- `tmp/wifi/v384-post-live-status.json`
- `tmp/wifi/v384-post-live-selftest.json`
- `tmp/wifi/v384-post-live-ps.txt`
- `tmp/wifi/v384-post-live-netdev.txt`

## Interpretation

v384 achieved its main purpose for `servicemanager`: it captured the SIGABRT context instead of only reporting a runtime gap. The remaining blocker is now the helper lifecycle proof for bounded `hwservicemanager` start-only runs, not Wi-Fi bring-up.

The current helper marks the run `start-only-reboot-required` when the direct child is reaped but `kill(-pgid, 0)` still sees the process group. It does not attempt a final group kill after the direct child is already reaped, and it does not capture enough residual process-group evidence to identify the remaining member.

## Next Step

V385 should introduce `a90_android_execns_probe v16` with bounded residual process-group cleanup and evidence:

1. After direct child reap, if `kill(-pgid, 0)` still succeeds, send a final `SIGKILL` to the process group.
2. Capture process-group or candidate residual process evidence before and after that final kill.
3. Keep service-manager start-only bounded and fail-closed.
4. Keep Wi-Fi HAL start and Wi-Fi bring-up blocked.
5. Preserve the 30-arg compact command behavior or add a helper-side compact service-manager profile.
