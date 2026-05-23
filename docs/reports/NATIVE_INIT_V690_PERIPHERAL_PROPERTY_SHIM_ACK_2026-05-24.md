# Native Init V690 Peripheral Property Shim Ack Report

## Result

- decision: `v690-provider-post-property-start-gap-classified`
- pass: `true`
- helper marker: `a90_android_execns_probe v115`
- helper SHA256:
  `60d8ca3c5e652b4f68c519613f10fb91c582a49cb3187ba301f29d5c7027c2fb`
- build evidence: `tmp/wifi/v690-execns-helper-v115-build/a90_android_execns_probe`
- deploy evidence: `tmp/wifi/v690-execns-helper-v115-deploy-live/`
- live evidence:
  `tmp/wifi/v690-peripheral-manager-cnss-retry-orchestrated-live/`
- Wi-Fi HAL: not started
- scan/connect/DHCP/external ping: not executed

## Implementation

V690 implements the V689 exact private property-service shim candidate in helper
v115:

```text
vendor.peripheral.SDX50M.state=OFFLINE
vendor.peripheral.modem.state=OFFLINE
```

The acknowledgement is local to the helper-owned private property-service
socket in the bounded namespace. It does not write global Android properties.

The built artifact is static and has no dynamic section:

```text
artifact: tmp/wifi/v690-execns-helper-v115-build/a90_android_execns_probe
size: 969K
sha256: 60d8ca3c5e652b4f68c519613f10fb91c582a49cb3187ba301f29d5c7027c2fb
file: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
dynamic section: none
```

## Deploy

The helper deployed through serial fallback:

| item | value |
| --- | --- |
| decision | `execns-helper-v115-deploy-pass` |
| chunk_size | `1850` |
| chunks | `739` |
| daemon start | `false` |
| Wi-Fi bring-up | `false` |

## Live Proof

The exact property ack contract held:

| name | value | allowed | result |
| --- | --- | ---: | --- |
| `hwservicemanager.ready` | `true` | `1` | `0x00000000` |
| `vendor.peripheral.SDX50M.state` | `OFFLINE` | `1` | `0x00000000` |
| `vendor.peripheral.modem.state` | `OFFLINE` | `1` | `0x00000000` |

The previous V688 blocker disappeared:

```text
Unable to set property ... error code: 0x18
```

was not observed in the V690 provider transcript.

The lower Wi-Fi path still did not advance:

| marker | count |
| --- | ---: |
| service-notifier `180` | `1` |
| service-notifier `74` | `1` |
| `cnss-daemon` netlink | `10` |
| `cnss-daemon` `cld80211` | `4` |
| QMI server connected | `0` |
| WLFW start/request | `0` |
| BDF `regdb`/`bdwlan` | `0` |
| WLAN firmware ready | `0` |
| `wlan0` | `0` |

## New Blocker

The provider pair still exits before the observe window:

| child | start_order | observable | exit_code | signal |
| --- | ---: | ---: | ---: | ---: |
| `per_mgr` | `10` | `1` | `0` | `0` |
| `per_proxy` | `11` | `1` | `1` | `0` |
| `cnss_daemon_retry` | `12` | `1` | `-1` | `9` |

The remaining transcript is now property-read context/log-tag noise plus
provider runtime/registration behavior, not the `vendor.peripheral.*.state`
write failure:

```text
Access denied finding property "persist.log.tag.PerMgrSrv"
Access denied finding property "log.tag.PerMgrSrv"
Access denied finding property "persist.log.tag.PerMgrProxy"
Access denied finding property "log.tag.PerMgrProxy"
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

V691 should classify the post-property provider exit:

1. determine whether `pm-service` exit code `0` is normal parent/daemon
   behavior or actual service termination;
2. verify whether a child process or Binder registration exists after the
   parent exits;
3. classify `pm-proxy` exit code `1` with its remaining stdout/stderr and
   Binder/service registration surface;
4. only then decide whether the remaining property-read context denials need
   more private property-area materialization.

Do not start Wi-Fi HAL, use credentials, scan/connect, DHCP, route changes, or
external ping until WLFW/BDF/`wlan0` advances.
