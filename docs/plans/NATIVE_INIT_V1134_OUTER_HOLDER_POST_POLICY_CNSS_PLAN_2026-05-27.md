# Native Init V1134 Outer Holder Post-policy CNSS Plan

Date: `2026-05-27`

## Goal

Run the V1133-selected composite gate:

```text
outer global firmware + /dev/subsys_modem holder
  -> wait for mss ONLINE / QRTR RX
  -> run post-policy provider-positive CNSS PM observer with helper v213
  -> classify mdm3/WLFW/service69/wlan0 delta
```

This is the first retry after V1132 that avoids the closed helper-private
`/dev/subsys_modem` pre-holder path.

## Preconditions

Before live execution:

1. current native boot is healthy;
2. helper `a90_android_execns_probe v213` is deployed;
3. V401 selinuxfs runtime surface is mounted for the current boot;
4. V490 native SELinux policy-load proof has passed for the current boot;
5. no residual PM/service-manager/CNSS actors are present.

## Implementation

Add `scripts/revalidation/native_wifi_outer_holder_post_policy_cnss_live_v1134.py`.

The runner reuses:

- V1113 global firmware mount + outer `subsys_modem` holder window;
- V1121/V1131 PM observer no-pre-CNSS-`per_proxy` order;
- helper `v213`;
- current tracefs PM observer instrumentation.

The child command must include:

```text
--pm-observer-start-cnss-before-per-proxy
```

The child command must not include:

```text
--pm-observer-modem-pre-holder
--allow-pm-observer-modem-pre-holder
```

## Success Criteria

- global firmware mounts are visible;
- outer holder opens `/dev/subsys_modem`;
- `mss` reaches `ONLINE`;
- QRTR RX appears before PM observer start;
- `vndservicemanager` readiness and provider visibility remain true;
- CNSS PM register/connect return values are captured;
- forbidden surfaces remain false;
- cleanup reboot restores native health.

WLFW/service69/wlan0 advancement is a positive outcome, not required for the
runner itself to pass. If absent, the report must identify the next lower
blocker.

## Guardrails

Forbid:

- helper-private modem pre-holder;
- `/dev/subsys_esoc0` open;
- eSoC control ioctl;
- Wi-Fi HAL start;
- scan/connect/link-up;
- credential use;
- DHCP/route changes;
- external ping;
- partition writes;
- boot image writes;
- flash.

Cleanup boundary is reboot.
