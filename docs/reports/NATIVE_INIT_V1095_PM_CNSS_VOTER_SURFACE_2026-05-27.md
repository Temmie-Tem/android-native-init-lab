# Native Init V1095 PM CNSS Voter Surface Report

## Summary

V1095 passed. The PM observer now continues past `pm-service` provider
registration, starts `pm-proxy`, verifies the provider remains visible, starts a
bounded `cnss-daemon`, and captures the lower surface again. The result is still
mdm3/WLFW negative.

Decision:

```text
v1095-cnss-voter-no-pm-fd-mdm3-still-offline
```

This closes the hypothesis that `cnss-daemon` alone, after PM provider
registration and `pm-proxy`, creates the missing PM `/dev/subsys_modem` voter or
advances mdm3/WLFW. The current blocker remains below the PM provider surface.

## Evidence

| item | path |
| --- | --- |
| helper source | `stage3/linux_init/helpers/a90_android_execns_probe.c` |
| deploy wrapper | `scripts/revalidation/wifi_execns_helper_v206_deploy_preflight.py` |
| live wrapper | `scripts/revalidation/native_wifi_pm_cnss_voter_surface_live_v1095.py` |
| helper artifact | `tmp/wifi/v1095-execns-helper-v206-build/a90_android_execns_probe` |
| deploy evidence | `tmp/wifi/v1095-execns-helper-v206-deploy/manifest.json` |
| live evidence | `tmp/wifi/v1095-pm-cnss-voter-surface-live/manifest.json` |
| V490 evidence | `tmp/wifi/v490-native-selinux-policy-load-proof/manifest.json` |

## Result

```text
helper: a90_android_execns_probe v206
sha256: 7920eeb353e1d6f09ded42efc84e7a8549fdb407cdd8236307422ebf2a9108e4
vndservicemanager_ready: True
vndservice_provider_seen: True
after_per_mgr_query: True
after_per_proxy_query: True
after_cnss_daemon_query: True
post_provider_surface_present: True
post_provider_mdm3_state: OFFLINING
post_provider_wlfw_service69_seen: False
pm_service_subsys_modem_seen: False
pm_proxy_helper_subsys_modem_seen: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

The after-`cnss-daemon` fd snapshot returned:

```text
pm_service_trigger_observer.after_cnss_daemon.per_mgr_subsys_modem_count=0
pm_service_trigger_observer.after_cnss_daemon.pm_proxy_helper_subsys_modem_count=0
pm_service_trigger_observer.after_cnss_daemon.per_mgr_vndbinder_count=1
pm_service_trigger_observer.after_cnss_daemon.pm_proxy_helper_vndbinder_count=0
```

The after-`cnss-daemon` lower surface returned:

```text
pm_service_trigger_observer.post_provider_surface.after_cnss_daemon.mdm3_state=OFFLINING
pm_service_trigger_observer.post_provider_surface.after_cnss_daemon.mdm3_crash_count=0
pm_service_trigger_observer.post_provider_surface.after_cnss_daemon.mdm3_firmware_name=esoc0
pm_service_trigger_observer.post_provider_surface.after_cnss_daemon.qcwlanstate_exists=0
pm_service_trigger_observer.post_provider_surface.after_cnss_daemon.wlan0_exists=0
```

All three provider queries exited cleanly:

```text
wifi_vndservice_query.pm_observer_after_per_mgr_probe.result=query-exit-zero
wifi_vndservice_query.pm_observer_after_per_proxy_probe.result=query-exit-zero
wifi_vndservice_query.pm_observer_after_cnss_daemon_probe.result=query-exit-zero
```

`cnss-daemon` reached the expected netlink path and resolved `cld80211`, but did
not create PM subsystem fd progress or WLFW service `69`.

## Implementation Notes

- `a90_android_execns_probe v206` adds
  `--pm-observer-start-cnss-after-provider`.
- The flag is fail-closed: it requires
  `--pm-observer-continue-after-provider` and is valid only in
  `wifi-companion-pm-service-trigger-observer` mode.
- The helper starts `cnss-daemon` only after provider-positive PM queries are
  already observed.
- The V1095 live wrapper allows `cnss-daemon_start_executed=1` but continues to
  fail closed on Wi-Fi HAL, scan/connect, DHCP, route, credential use, and
  external ping.

## Safety

- No Wi-Fi HAL, scan/connect/link-up, DHCP, route, credential use, or external
  ping executed.
- No `mdm_helper` executed.
- No eSoC open/ioctl, GPIO write, partition write, flash, or reboot executed in
  the passing run.
- QRTR readback used nameservice lookup/readback only and sent no QMI payload.
- Device remained healthy: post-run `selftest` reported `fail=0`; `netservice`
  stayed USB-local.

## Interpretation

The V1071-era `pm-service exit 255` and BPF/uprobe route is not the active
blocker for the current path. V1092 through V1095 prove that the provider can
be registered, can remain visible through `pm-proxy`, and can coexist with a
bounded `cnss-daemon`, but the PM stack still does not produce a
`/dev/subsys_modem` fd or advance mdm3/WLFW.

Candidate next checks:

1. Classify whether `cnss-daemon` is actually issuing a PeripheralManager
   request in this namespace or only reaching the `cld80211` netlink surface.
2. Compare Android-good PM/eSoC timing against the V1095 provider-positive,
   CNSS-positive, no-fd window.
3. Keep V1095 as the upper-layer precondition; do not expand to Wi-Fi HAL or
   scan/connect until mdm3/WLFW moves.

## Validation

Executed:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v1095-execns-helper-v206-build/a90_android_execns_probe
python3 -m py_compile scripts/revalidation/native_wifi_pm_cnss_voter_surface_live_v1095.py scripts/revalidation/wifi_execns_helper_v206_deploy_preflight.py scripts/revalidation/native_wifi_pm_post_provider_surface_live_v1093.py
python3 scripts/revalidation/wifi_execns_helper_v206_deploy_preflight.py --approval-phrase "approve v1095 deploy execns helper v206 only; no daemon start and no Wi-Fi bring-up" --apply --assume-yes run
python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py --expect-version "A90 Linux init 0.9.68 (v724)" --helper-sha256 7920eeb353e1d6f09ded42efc84e7a8549fdb407cdd8236307422ebf2a9108e4 --approval-phrase "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up" --apply --assume-yes run
python3 scripts/revalidation/native_wifi_pm_cnss_voter_surface_live_v1095.py --helper-sha256 7920eeb353e1d6f09ded42efc84e7a8549fdb407cdd8236307422ebf2a9108e4 --helper-marker "a90_android_execns_probe v206" --local-helper tmp/wifi/v1095-execns-helper-v206-build/a90_android_execns_probe --helper-timeout-sec 18 --toybox-timeout-sec 120 --allow-mountsystem-ro --allow-selinuxfs-mount --allow-pm-service-trigger-observer --allow-cleanup-reboot --assume-yes run
python3 scripts/revalidation/a90ctl.py --timeout 12 bootstatus
python3 scripts/revalidation/a90ctl.py --timeout 12 selftest
python3 scripts/revalidation/a90ctl.py --timeout 12 netservice status
```

Result:

```text
decision: v1095-cnss-voter-no-pm-fd-mdm3-still-offline
pass: True
selftest: fail=0
```
