# Native Init V688 PeripheralManager SELinux Context Repair Report

## Result

- decision: `v688-provider-start-gap-classified`
- pass: `true`
- helper marker: `a90_android_execns_probe v114`
- helper SHA256:
  `6de2ee5efc65441f18ee587f54b525c4006553cae54363c2e036aa21f976a5f4`
- build evidence: `tmp/wifi/v688-execns-helper-v114-build/a90_android_execns_probe`
- deploy evidence: `tmp/wifi/v688-execns-helper-v114-deploy-live/`
- live evidence:
  `tmp/wifi/v688-peripheral-manager-cnss-retry-orchestrated-live/`
- Wi-Fi HAL: not started
- scan/connect/DHCP/external ping: not executed

## Implementation

V688 changed the helper from v113 to v114 and removed the A90-invalid
PeripheralManager SELinux context assumption:

- removed `u:r:per_mgr:s0` from the explicit helper context allowlist;
- removed `/vendor/bin/pm-service` and `/vendor/bin/pm-proxy` service-default
  mapping to `u:r:per_mgr:s0`;
- preserved the provider/CNSS retry order and `system:system` no-capability
  identity contract.

The built v114 artifact is static and has no dynamic section:

```text
artifact: tmp/wifi/v688-execns-helper-v114-build/a90_android_execns_probe
size: 969K
sha256: 6de2ee5efc65441f18ee587f54b525c4006553cae54363c2e036aa21f976a5f4
file: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
dynamic section: none
```

## Deploy

NCM fast transfer was not available in this boot because the host could not
reach the expected device addresses. The helper deployed through the serial
fallback:

| item | value |
| --- | --- |
| decision | `execns-helper-v114-deploy-pass` |
| transfer | serial fallback |
| chunk_size | `1850` |
| chunks | `739` |
| daemon start | `false` |
| Wi-Fi bring-up | `false` |

## Live Proof

The orchestrator refreshed current-boot prerequisites and ran the bounded v114
proof:

```text
V641 clean-DSP reboot
  -> system ro mount
  -> V401 SELinuxfs surface
  -> V490 policy-load proof
  -> V688 helper live arm
  -> reboot cleanup
```

The lower path remained positive:

| marker | count |
| --- | ---: |
| service-notifier `180` | `1` |
| service-notifier `74` | `1` |
| `cnss-daemon` netlink | `10` |
| `cnss-daemon` `cld80211` | `4` |
| CNSS Binder transaction failed | `1` |
| Binder ioctl unsupported | `2` |

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

## Context Repair Evidence

V688 removed the V687 invalid `setexeccon` failure. Both provider children now
skip explicit service-default context selection because no valid A90 default is
known:

```text
wifi_hal_composite_child.per_mgr.selinux_exec.skipped=1
wifi_hal_composite_child.per_mgr.selinux_exec.reason=no-default-context-for-target
wifi_hal_composite_child.per_proxy.selinux_exec.skipped=1
wifi_hal_composite_child.per_proxy.selinux_exec.reason=no-default-context-for-target
```

The regression flag is false:

```text
context_repair_regressed=False
```

## New Blocker

After the context repair, the provider pair starts and is observable but exits
naturally before the observe window remains stable:

| child | start_order | observable | exit_code | signal | context action |
| --- | ---: | ---: | ---: | ---: | --- |
| `per_mgr` | `10` | `1` | `0` | `0` | skipped; no default context |
| `per_proxy` | `11` | `1` | `1` | `0` | skipped; no default context |
| `cnss_daemon_retry` | `12` | `1` | `-1` | `9` | cleanup kill |

The captured provider output points at property service/runtime integration, not
linker load failure:

```text
libc: Unable to set property "vendor.peripheral.SDX50M.state" to "OFFLINE": error code: 0x18
libc: Unable to set property "vendor.peripheral.modem.state" to "OFFLINE": error code: 0x18
libc: Access denied finding property "persist.log.tag.PerMgrSrv"
libc: Access denied finding property "log.tag.PerMgrSrv"
```

Therefore the next blocker is the PeripheralManager property service and
registration environment. The current private property shim is enough for the
previous Android userspace/CNSS phases but does not yet satisfy
`pm-service`/`pm-proxy`.

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

V689 should classify the PeripheralManager property surface before another
runtime retry:

1. compare Android property contexts and property values used by
   `pm-service`/`pm-proxy`;
2. inspect how Android init/property service allows
   `vendor.peripheral.*.state` writes;
3. decide whether the native private property shim needs context-aware
   `vendor.peripheral.*` support or whether the provider must run under a
   different proven domain;
4. retry provider/CNSS only after property denial `0x18` is removed.

Do not proceed to Wi-Fi HAL, credentials, scan/connect, DHCP, route changes, or
external ping until WLFW/BDF/`wlan0` advances.
