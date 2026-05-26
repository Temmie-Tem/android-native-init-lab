# Native Init V1062 PM Contract Gap Classifier Report

Date: `2026-05-27`

## Summary

V1062 is a host-only classifier over existing V1024 Android-positive evidence
and V1061 native evidence.  No device command was executed.

Decision:

```text
v1062-per-mgr-fd-gap-plus-esoc-warning-classified
```

The comparison confirms that V1061 reaches the Android-positive prefix:

- helper modem pre-holder confirmed;
- `pm_proxy_helper` holds `/dev/subsys_modem`;
- `pm-service` is running as `u:r:vendor_per_mgr:s0`;
- `pm-proxy` is running;
- `mdm_helper` exposes `/dev/esoc-0`.

The missing native delta is specific: `pm-service`/`per_mgr` does not open
`/dev/subsys_modem`, while Android V1024 proves that it should.  V1061 also
emitted an eSoC reference-count warning during cleanup, so the next live retry
must be blocked until that warning path is understood.

## Evidence

Private evidence directory:

```text
tmp/wifi/v1062-pm-contract-gap-classifier/
```

Manifest:

```text
tmp/wifi/v1062-pm-contract-gap-classifier/manifest.json
```

Inputs:

```text
tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json
tmp/wifi/v1061-global-firmware-pm-full-contract/manifest.json
tmp/wifi/v1061-global-firmware-pm-full-contract/native/pm-full-contract-with-global-firmware.txt
tmp/wifi/v1061-global-firmware-pm-full-contract/native/dmesg-delta.txt
```

## Android Positive

| Item | Value |
| --- | --- |
| `pm_proxy_helper` `/dev/subsys_modem` fd | `true` |
| `pm-service` `/dev/subsys_modem` fd | `true` |
| `mdm_helper` `/dev/esoc-0` fd | `true` |
| WLFW chain | `true` |
| `wlfw_start` | `8.198751s` |
| `/dev/subsys_esoc0` get | `8.301226s` |
| `wlan0` | `15.215998s` |

## Native V1061

| Item | Value |
| --- | --- |
| helper modem pre-holder | `true` |
| `pm_proxy_helper` `/dev/subsys_modem` fd count | `1` |
| `per_mgr` `/dev/subsys_modem` fd count | `0` |
| PM full contract | `false` |
| `pm-proxy` | `true` |
| `mdm_helper` `/dev/esoc-0` fd | `true` |
| service-manager start | `false` |
| `/dev/subsys_esoc0` open | `false` |
| kernel warning count | `3` |

Native `pm-service` process surface:

```text
per_mgr_attr=u:r:vendor_per_mgr:s0
per_mgr_vndbinder_count=1
per_mgr_binder_count=0
per_mgr_hwbinder_count=0
pm_service_process_count=1
pm_proxy_count=1
pm_proxy_helper_count=0
property_sdx50m_state_offline=1
property_modem_state_offline=1
property_shutdown_list=3
```

## Interpretation

V1061 did not fail because of global firmware visibility, helper modem
pre-holder, `pm_proxy_helper`, `pm-proxy`, or `mdm_helper` fd visibility.  It
failed because the native `pm-service` process stayed vndbinder-only and did
not take `/dev/subsys_modem`.

The next blocker is therefore the `pm-service` trigger/input path:

- missing binder/vndbinder transaction from the Android PM stack;
- missing property/service state that causes `pm-service` to take the modem fd;
- timing mismatch between `pm_proxy_helper`, `pm-service`, and `pm-proxy`;
- cleanup mismatch around helper-held eSoC fd/reference count.

## Guardrails

- Host-only; no device command.
- No live retry, service-manager start, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, eSoC open/ioctl, sysfs/debugfs write, boot image write, partition write, firmware mutation, or Android handoff.

## Next

V1063 should stay host-only/source-only first.  It should inspect the Android
init rc/service contract and helper implementation around `pm-service` and
`pm-proxy` to determine which transaction or property transition makes Android
`pm-service` open `/dev/subsys_modem`.  The eSoC cleanup reference-count warning
must also be classified before another live repeat.
