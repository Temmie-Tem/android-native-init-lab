# Native Init V687 PeripheralManager Live Proof Report

## Result

- status: `live-pass`; Wi-Fi external ping is **not** complete
- deploy evidence: `tmp/wifi/v687-execns-helper-v113-deploy-live-retry/`
- live evidence: `tmp/wifi/v687-peripheral-manager-cnss-retry-orchestrated-live/`
- deployed helper: `a90_android_execns_probe v113`
- deployed helper SHA256:
  `60ed7a14d3b33b2f700fb644fd1ccd7a037ac8d9c50db082fa0dea7646965ce9`
- corrected decision: `v687-provider-start-gap-classified`
- Wi-Fi HAL: not started
- scan/connect/DHCP/external ping: not executed

## Deploy

The first deploy attempt used serial chunk size `3000` and failed before any
chunk was written because the encoded `cmdv1x` line exceeded the console-safe
limit.

The wrapper default was corrected to serial chunk size `1850`, then deploy
passed:

| item | value |
| --- | --- |
| method | `serial` fallback |
| chunk_size | `1850` |
| chunks_written | `739` |
| max_cmdv1_line_bytes | `3888` |
| safe_line_limit | `3968` |
| post-deploy helper | v113 current |

NCM fast transfer was not available because the host NCM interface existed but
did not have `192.168.7.1/24`, and passwordless sudo was unavailable for setting
the address.

## Live Proof

The orchestrator refreshed the current-boot prerequisites, then ran the v113
PeripheralManager/CNSS retry proof:

```text
V641 clean-DSP reboot
  -> system ro mount
  -> V401 SELinuxfs surface
  -> V490 policy-load proof
  -> V687 helper live arm
  -> reboot cleanup
```

The lower gate reproduced the known positive path:

| marker | count |
| --- | ---: |
| service-notifier `180` | `1` |
| service-notifier `74` | `1` |
| `cnss-daemon` netlink | `10` |
| `cnss-daemon` `cld80211` | `4` |
| CNSS Binder transaction failed | `1` |
| kernel warning | `1` |

The downstream Wi-Fi markers remained absent:

| marker | count |
| --- | ---: |
| QMI server connected | `0` |
| WLFW start/request | `0` |
| WLAN-PD | `0` |
| BDF `regdb` | `0` |
| BDF `bdwlan` | `0` |
| WLAN firmware ready | `0` |
| `wlan0` | `0` |

## PeripheralManager Surface

The helper inserted the expected order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,
service74_gate,servicemanager,hwservicemanager,vndservicemanager,
vndservicemanager_ready,cnss_daemon_initial_cleanup,
per_mgr,per_proxy,cnss_daemon_retry
```

Both provider children became briefly observable and had FD summaries, but both
exited naturally before the observe window:

| child | start_order | observable | exit_code | signal | interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| `per_mgr` | `10` | `1` | `126` | `0` | runtime start gap |
| `per_proxy` | `11` | `1` | `126` | `0` | runtime start gap |
| `cnss_daemon_retry` | `12` | `1` | `-1` | `9` | cleanup kill after bounded window |

The child transcripts identify the first concrete provider blocker before
linker/runtime dependency probing:

```text
wifi_hal_composite_child.per_mgr.selinux_context_mode=service-defaults
wifi_hal_composite_child.per_mgr.selinux_exec.target_context=u:r:per_mgr:s0
wifi_hal_composite_child.per_mgr.selinux_exec.ok=0
wifi_hal_composite_child.per_mgr.selinux_exec.errno=22
wifi_hal_composite_child.per_mgr.selinux_exec.error=Invalid argument
wifi_hal_composite_child.per_proxy.selinux_context_mode=service-defaults
wifi_hal_composite_child.per_proxy.selinux_exec.target_context=u:r:per_mgr:s0
wifi_hal_composite_child.per_proxy.selinux_exec.ok=0
wifi_hal_composite_child.per_proxy.selinux_exec.errno=22
wifi_hal_composite_child.per_proxy.selinux_exec.error=Invalid argument
```

Targeted policy/file-context checks did not find an A90 process domain named
`per_mgr`; only the service-manager type `peripheral_service` was visible in
the captured policy surface. Therefore the helper's V686/V687 forced
`u:r:per_mgr:s0` service-default mapping is not valid on this device.

Therefore the corrected V687 interpretation is not "provider ready"; it is:

```text
service74/vndservicemanager/initial cleanup are positive
  -> pm-service/pm-proxy launch and become briefly observable
  -> both provider processes exit with 126
  -> fresh cnss-daemon retry still reaches Binder -22
  -> WLFW/BDF/wlan0 remain absent
```

## Guardrails

- no Wi-Fi HAL or wificond start;
- no supplicant or hostapd start;
- no scan/connect/link-up;
- no credential use;
- no DHCP, route change, or external ping;
- no sysfs subsystem state write;
- no `esoc0` open/hold;
- no boot image or partition write.

## Next Gate

V688 should repair or remove the invalid forced `u:r:per_mgr:s0`
service-default mapping before treating the provider failure as a linker or
runtime dependency gap. The useful next checks are:

1. skip explicit `setexeccon` for `pm-service`/`pm-proxy` unless a valid A90
   process domain is proven;
2. capture `pm-service`/`pm-proxy` child stderr/stdout and linker diagnostics
   after SELinux context selection no longer fails at `EINVAL`;
3. verify executable permissions, interpreter/linker path, and required shared
   libraries inside the private namespace;
4. compare Android init service contract against helper identity/context:
   `user system`, `group system`, and the actual A90 SELinux domain if one is
   discoverable;
5. only retry CNSS after the provider pair stays alive through the observe
   window.

Do not proceed to credentials, scan/connect, DHCP, route changes, or external
ping until WLFW/BDF/`wlan0` advances.
