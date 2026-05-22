# Native Init V652 Service-74 Binder Parity Live Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_service74_binder_parity_v652.py`
- evidence: `tmp/wifi/v652-service74-binder-parity-live-20260523-082200/`
- decision: `v652-service74-regressed`

## Scope

V652 tested the closest helper v104 primitive for combining the clean-DSP lower
path with a minimal service-manager binder surface:

```text
qrtr_ns -> rmt_storage -> tftp_server -> pd_mapper
  -> cnss_diag -> cnss-daemon
    -> servicemanager -> hwservicemanager -> vndservicemanager
```

The run did not write DSP boot nodes, did not open `esoc0`, did not start Wi-Fi
HAL, did not scan/connect/link-up, did not use credentials, did not run DHCP,
did not change routes, and did not ping externally.

## Prerequisites

| prerequisite | result | evidence |
| --- | --- | --- |
| V641 clean-DSP current boot | pass | timeline has `wifi-v641-fwssctl complete failures=0 timeouts=0`; ADSP/CDSP/DSPS RPMSG nodes visible |
| V401 SELinuxfs mount | pass | `tmp/wifi/v652-v401-selinuxfs-mount-run/` |
| V490 policy load | pass | `tmp/wifi/v652-v490-current-run/` |
| V652 preflight | pass | `tmp/wifi/v652-service74-binder-parity-preflight-ready/` |

## Result

```text
decision: v652-service74-regressed
pass: True
reason: service_notifier_180=0 service_notifier_74=0
next: do not widen scope; implement explicit service74-gated helper mode if delayed service-manager regresses lower publication
device_commands_executed: True
device_mutations: True
daemon_start_executed: True
service_manager_start_executed: True
wifi_bringup_executed: False
```

## Observations

| item | value |
| --- | --- |
| holder started | `True` |
| QRTR RX seen | `True` |
| helper result | `companion-window-pass` |
| all postflight safe | `True` |
| reboot cleanup | native version seen and status healthy |
| kernel warning | `0` |
| service-notifier `180` | `0` |
| service-notifier `74` | `0` |
| WLAN-PD | `0` |
| WLFW start/request | `0/0` |
| QMI server connected | `0` |
| BDF `regdb`/`bdwlan` | `0/0` |
| `wlan0` | `0` |

## Service-Manager Surface

| child | observable | cleanup signal | postflight safe |
| --- | --- | --- | --- |
| `servicemanager` | `1` | `15` | `1` |
| `hwservicemanager` | `1` | `15` | `1` |
| `vndservicemanager` | `1` | `15` | `1` |

The service-manager trio was started and cleaned inside the bounded helper
window, but the delayed ordering regressed the previously observed service
`180/74` publication path. `cnss-daemon` still reached netlink/`cld80211` and
produced binder transaction failures, but WLFW did not begin.

## Interpretation

V652 rules out the current helper v104 CNSS-first delayed service-manager mode
as the correct way to combine binder runtime with the V644 positive lower path.
The failure is not a crash, cleanup failure, kernel warning, or Wi-Fi bring-up
issue. It is an ordering/gating issue: service-manager must not be inserted
until after the lower path has actually published service `74`.

## Next Gate

Proceed to V653:

1. add a helper mode that waits for service-notifier `74` before starting the
   service-manager trio;
2. keep the same V641/V401/V490 preconditions;
3. stop and classify if service `74` does not appear within the bounded window;
4. only after service `74` is observed, start service-manager and observe WLFW;
5. keep Wi-Fi HAL, scan/connect, credentials, DHCP, route changes, and external
   ping blocked.
