# Native Init V688 PeripheralManager SELinux Context Repair Plan

## Objective

V688 repairs the V687 blocker before another provider/CNSS retry. V687 proved
that forcing `pm-service` and `pm-proxy` into `u:r:per_mgr:s0` fails with
`setexeccon` `EINVAL` on A90. V688 must stop treating that borrowed context as
valid and rerun the same bounded provider proof with helper v114.

This is still not a Wi-Fi connect attempt. It must not start Wi-Fi HAL,
supplicant, hostapd, scan/connect, DHCP, route changes, credentials, or
external ping.

## Scope

Modify the helper and wrappers only:

1. bump helper marker to `a90_android_execns_probe v114`;
2. remove `u:r:per_mgr:s0` from the explicit SELinux context allowlist;
3. remove the service-default mapping for `/vendor/bin/pm-service` and
   `/vendor/bin/pm-proxy`;
4. preserve the existing `service74` gated order and identity contract:
   `system:system`, no supplemental groups, no Linux capabilities;
5. classify provider children after SELinux context selection is skipped as
   `no-default-context-for-target`, so the next blocker is real runtime/linker
   behavior rather than invalid context selection.

## Live Gate

The bounded live proof reuses the V687 order:

```text
qrtr_ns
  -> rmt_storage
  -> tftp_server
  -> pd_mapper
  -> cnss_diag
  -> cnss_daemon
  -> service74_gate
  -> servicemanager
  -> hwservicemanager
  -> vndservicemanager
  -> vndservicemanager_ready
  -> cnss_daemon_initial_cleanup
  -> per_mgr /vendor/bin/pm-service
  -> per_proxy /vendor/bin/pm-proxy
  -> cnss_daemon_retry
```

## Success Criteria

- helper source compiles for AArch64 static;
- built artifact has no dynamic section;
- built artifact contains `a90_android_execns_probe v114`;
- built artifact contains the provider/CNSS retry mode and provider targets;
- live provider child output no longer contains `selinux_exec.errno=22` for
  `pm-service` or `pm-proxy`;
- if provider children still exit, the decision records the next concrete
  runtime/linker/provider blocker;
- no Wi-Fi HAL, scan/connect, DHCP, routes, credentials, or external ping are
  executed.

## Failure Labels

| label | meaning |
| --- | --- |
| `v688-peripheral-manager-cnss-retry-blocked` | prerequisite failed before live mutation |
| `v688-context-repair-regressed` | helper still forces invalid `u:r:per_mgr:s0` or reports `EINVAL` |
| `v688-provider-start-gap-classified` | context repair worked, but provider still does not stay alive |
| `v688-provider-ready-no-wlfw-advance` | provider pair stayed alive but WLFW/BDF/`wlan0` did not advance |
| `v688-wifi-lower-layer-advanced` | WLFW/BDF/`wlan0` advanced without scan/connect |

## Next Gate

If V688 removes the SELinux context blocker and exposes a runtime/linker error,
the next unit should repair that concrete provider startup gap. If the provider
pair stays alive but WLFW remains absent, the next unit should classify the
PeripheralManager service registration and CNSS client interaction before any
Wi-Fi HAL or credential-bearing operation.
