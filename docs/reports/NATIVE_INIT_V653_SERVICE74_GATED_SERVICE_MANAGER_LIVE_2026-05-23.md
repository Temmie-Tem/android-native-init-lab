# Native Init V653 Service74-Gated Service-Manager Live Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner:
  `scripts/revalidation/native_wifi_service74_gated_service_manager_v653.py`
- evidence: `tmp/wifi/v653-service74-gated-live-20260523-085337/`
- decision: `v653-binder-loop-persists`

## Scope

V653 ran after helper v105 deployment, V641 clean-DSP one-shot preparation,
V401 SELinuxfs mount, and V490 native SELinux policy-load proof. The live proof
started lower companion/CNSS services and started the service-manager trio only
after the helper observed a fresh service-notifier `74` kernel marker.

V653 did not start Wi-Fi HAL, `wificond`, supplicant, or hostapd. It did not
scan/connect/link-up, use credentials, run DHCP, change routes, or ping
externally.

## Result

```text
decision: v653-binder-loop-persists
pass: True
service_notifier_180: 1
service_notifier_74: 1
cnss_binder_transaction_failed: 1
wlfw_start: 0
wlan_pd: 0
qmi_server_connected: 0
bdf_regdb: 0
bdf_bdwlan: 0
wlan0: 0
wifi_bringup_executed: False
```

The helper gate worked as intended:

```text
baseline_count_74: 0
final_count_74: 1
gate_status: open
wait_attempts: 1
wait_ms: 16
service_manager_started: 1
```

Service-manager cleanup was proven for all three children:

| child | observable | exited | signal | postflight_safe |
| --- | --- | --- | --- | --- |
| `servicemanager` | `1` | `1` | `15` | `1` |
| `hwservicemanager` | `1` | `1` | `15` | `1` |
| `vndservicemanager` | `1` | `1` | `15` | `1` |

Post-reboot cleanup returned to a healthy native shell:

```text
boot: BOOT OK
selftest: fail=0
exposure: ncm=absent tcpctl=stopped rshell=stopped
timeline_entries: 19/32
```

## Interpretation

V653 is a concrete improvement over V652:

- V652 delayed service-manager mode regressed service-notifier `180/74` to zero.
- V653 gated service-manager mode preserved fresh service-notifier `180/74`.
- The next blocker is not lower service `74` publication anymore; it is the
  `cnss-daemon` binder transaction failure after service-manager is present.

The remaining lower Wi-Fi path is still blocked before WLAN-PD/WLFW/BDF:

```text
service-notifier 180/74: present
cnss-daemon binder:      transaction failed -22
WLAN-PD/WLFW/BDF/wlan0: absent
```

The single `pm_qos_add_request` warning remains present in the same class as
V644 and should be treated as a guardrail for the next proof. Do not widen to
Wi-Fi HAL or scan/connect until the binder/runtime mismatch is classified.

## Next Gate

Proceed to a host-only V654 classifier before another live retry:

1. Compare V653 helper stderr, binder messages, service-manager children, and
   Android reference binder/service-manager state.
2. Classify whether the `-22` path is binder device namespace, service-manager
   context, property namespace, SELinux domain, or missing Android service
   registration.
3. Keep Wi-Fi HAL, scan/connect, credentials, DHCP, route changes, and external
   ping blocked until CNSS advances past binder into WLFW/WLAN-PD/BDF markers.
