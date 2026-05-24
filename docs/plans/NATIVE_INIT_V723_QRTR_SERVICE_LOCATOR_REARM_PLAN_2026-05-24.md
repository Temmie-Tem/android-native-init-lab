# Native Init V723 QRTR/Service-Locator Rearm Plan

- date: `2026-05-24 KST`
- scope: lower-only QRTR/service-locator rearm classifier
- runner: `scripts/revalidation/native_wifi_qrtr_servloc_rearm_v723.py`
- approval phrase: `approve v723 QRTR/service-locator late rearm proof only; no CNSS daemon, no service-manager, no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping`

## Goal

V720/V721 proved that a late native service-positive window can expose QRTR
service `180/74`, but it did not prove that the kernel CNSS2 SERVREG listener
was registered before the boot-time `servloc` timeout.

V723 tests the narrower question:

```text
If native boot already hit service-locator timeout, can a lower-only late
qrtr-ns/pd-mapper/rmt_storage/tftp_server window re-arm the path far enough to
produce WLAN-PD service 180/74 or CNSS2/WLFW progress?
```

## Method

1. Confirm current native baseline and helper v121 contract.
2. Prepare `/mnt/system/system` with `mountsystem ro`.
3. Ensure selinuxfs status is visible for the exec namespace helper.
4. Run helper v121 in `wifi-companion-android-order-post-sysmon-observer-start-only`.
5. Start only `qrtr-ns`, `pd-mapper`, `rmt_storage`, and `tftp_server`.
6. Capture dmesg before/after and classify the marker delta.

## Guardrails

Allowed:

- read-only `mountsystem ro`;
- selinuxfs mount for runtime surface visibility;
- helper private namespace setup and lower-only companion start;
- bounded postflight cleanup of the four lower companion processes.

Forbidden:

- `cnss-daemon`;
- `servicemanager`, `hwservicemanager`, or `vndservicemanager`;
- Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up;
- credential use;
- DHCP, route change, or external ping;
- `qcwlanstate` or WLAN driver-state writes;
- boot image or partition write.

## Decision Matrix

| condition | decision |
| --- | --- |
| helper does not expose v121/lower-only mode | block on helper deployment |
| helper starts anything above lower companion stack | stop and inspect scope break |
| service-locator reconnects but service `180/74` stays absent | late rearm is insufficient; move lower companion earlier in boot |
| service `180/74` appears but no WLFW/`wlan0` | continue with CNSS2 callback/power edge below HAL/connect |
| WLFW/BDF/fw-ready/`wlan0` appears | move to wlan0 readiness gate before scan/connect |

## Success Criteria

- `python3 -m py_compile` passes.
- `plan` and `preflight` produce manifests.
- approved live run records helper `order=qrtr_ns,pd_mapper,rmt_storage,tftp_server`.
- helper `all_postflight_safe=1`.
- manifest states no CNSS daemon, service-manager, Wi-Fi HAL, scan/connect,
  DHCP, external ping, or credential use occurred.

## Expected Next Gate

If V723 shows only `service_locator_new_server` without service `180/74`, V724
should be a boot-time one-shot proof that starts the lower QRTR companion set
before the kernel `servloc` timeout. That is the next meaningful gate before
revisiting CNSS2 callback, WLFW, HAL, or actual Wi-Fi connection.
