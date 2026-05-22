# Native Init V652 Service-74 Binder Parity Plan

- date: `2026-05-23 KST`
- cycle: `v652`
- scope: bounded live proof plan
- target: preserve the V644 service `74`-positive lower path while adding the
  minimal service-manager/binder runtime needed for `cnss-daemon` to continue
  into WLFW

## Background

V651 classified the current blocker:

```text
Android: service 74 -> CNSS netlink -> non-fatal genl failure -> WLFW -> WLAN-PD/QMI/BDF/wlan0
Native:  service 74 -> CNSS netlink/cld80211 -> binder -22 loop -> no WLFW
```

Older service-manager proofs are not sufficient by themselves:

- V601/V603 cleared `cnss-daemon` binder transaction failures, but those runs
  did not preserve service-notifier `74`.
- V604 changed ordering around CNSS and service-manager, but also failed to
  preserve service-notifier `180/74`.
- V644 is the first current evidence that service `180` and service `74`
  appear together under the clean-DSP state, but it intentionally did not start
  service-manager and therefore hit the `cnss-daemon` binder `-22` loop.

V652 should therefore combine only the necessary parts. The current helper v104
does not have an explicit "wait until service `74`, then start service-manager"
mode, so the first implementation uses the closest bounded primitive:
`wifi-companion-cnss-first-delayed-vnd-service-manager-start-only` under the
V641 clean-DSP/V644 preflight. The runner must classify service `74` regression
as its own valid result; if that happens, a later helper revision should add an
explicit service-publication gate.

```text
V641 clean-DSP state
  -> V644 lower path
    -> cnss_diag + cnss-daemon
      -> delayed minimal service-manager binder surface
        -> observe whether service 74 is preserved and WLFW advances
```

## Guardrails

V652 must not:

- write ADSP/CDSP/SLPI boot nodes directly;
- open or hold `esoc0`;
- write `boot_wlan`, `qcwlanstate`, or Wi-Fi driver-state sysfs nodes;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- flash boot images or write persistent partitions during the proof.

Allowed only if bounded and cleanup-safe:

- current-boot SELinux/runtime prerequisite refresh;
- firmware mount materialization already used by V644;
- `subsys_modem` holder;
- lower companion stack from V644;
- service-manager trio from V601/V603 after lower service publication;
- reboot cleanup if process cleanup cannot be proven local.

## Required Inputs

- V651 report and manifest:
  `docs/reports/NATIVE_INIT_V651_CNSS_WLFW_CONTINUATION_2026-05-23.md`
  and `tmp/wifi/v651-cnss-wlfw-continuation/manifest.json`
- V644 live evidence:
  `tmp/wifi/v644-live-20260523-071610/manifest.json`
- V601/V603/V604 service-manager reports:
  - `docs/reports/NATIVE_INIT_V601_SERVICE_MANAGER_BINDER_PROOF_2026-05-22.md`
  - `docs/reports/NATIVE_INIT_V603_QRTR_FIRST_SERVICE_MANAGER_LIVE_2026-05-22.md`
  - `docs/reports/NATIVE_INIT_V604_CNSS_FIRST_SERVICE_MANAGER_LIVE_2026-05-22.md`

## Implementation Shape

V652 is implemented as a new runner, not by widening V644 in place:
`scripts/revalidation/native_wifi_service74_binder_parity_v652.py`.

Recommended base:

- reuse `native_wifi_clean_dsp_cnss_wlfw_readback_v644.py` for the clean-DSP
  preflight and V644 marker accounting;
- reuse the V601/V603 service-manager command construction for copy-real
  linkerconfig and private binder service-manager startup;
- use helper v104's CNSS-first delayed service-manager mode as the first
  bounded implementation;
- classify service `74` regression separately so a later explicit wait-gate
  helper can be justified if needed;
- collect dmesg before/after, `ps`, QRTR readback, binder errors, WLFW markers,
  and postflight process cleanup.

The live sequence should be:

1. verify current native version is the V641 clean-DSP image;
2. verify V641 proof log says ADSP/CDSP/SLPI writes completed cleanly during
   boot, without repeating those writes;
3. refresh SELinux/runtime prerequisites if needed;
4. start the V644 lower stack using CNSS-first delayed service-manager ordering;
5. start only `servicemanager`, `hwservicemanager`, and `vndservicemanager`
   inside that bounded helper window;
6. start only `cnss_diag` and `cnss-daemon` as the CNSS userspace children;
7. classify whether service `74` is preserved after the delayed manager start;
8. observe for `wlfw_start`, `wlfw_service_request`, WLAN-PD, QMI server
   connected, BDF requests, firmware-ready, and `wlan0`;
9. cleanup by bounded process termination or reboot cleanup;
10. verify no Wi-Fi HAL, scan/connect, credential, DHCP, route, or external
    ping occurred.

## Success Labels

- `v652-service74-binder-parity-wlfw-advanced`
  - service `74` preserved;
  - binder transaction loop absent or reduced;
  - `wlfw_start` or WLFW service request appears.
- `v652-service74-binder-clean-wlfw-missing`
  - service `74` preserved;
  - binder failures cleared;
  - WLFW still missing.
- `v652-service74-regressed`
  - service `74` missing before service-manager starts.
- `v652-binder-loop-persists`
  - service `74` preserved;
  - binder `-22` loop remains.
- `v652-cleanup-review`
  - any manager/CNSS child remains, or postflight state is not safe.

## Advancement Rule

Only `v652-service74-binder-parity-wlfw-advanced` can move the project toward a
later Wi-Fi HAL or scan-only gate. Even then, credentials, association, DHCP,
route changes, and external ping remain blocked until native reaches WLFW/BDF
and a controlled scan/link gate is separately planned.
