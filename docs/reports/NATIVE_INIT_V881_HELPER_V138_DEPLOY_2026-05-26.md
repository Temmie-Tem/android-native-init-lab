# V881 Helper v138 Deploy-only Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| plan | `tmp/wifi/v881-execns-helper-v138-plan/manifest.json` | `execns-helper-v138-deploy-plan-ready` |
| preflight | `tmp/wifi/v881-execns-helper-v138-preflight/manifest.json` | `execns-helper-v138-deploy-preflight-ready` |
| deploy | `tmp/wifi/v881-execns-helper-v138-deploy-preflight/manifest.json` | `execns-helper-v138-deploy-pass` |

V881 deployed helper `v138` to `/cache/bin/a90_android_execns_probe`. It did
not execute live eSoC ioctls, did not open `/dev/subsys_esoc0`, did not start
Android actors, and did not bring up Wi-Fi.

## Deploy Details

| Item | Value |
| --- | --- |
| method | serial appendfile + uudecode |
| chunk size | `1850` |
| chunks written | `788` |
| encoded bytes | `1456699` |
| max cmdv1 line bytes | `3890` |
| safe line limit | `3968` |
| uses cmdv1x | `true` |

Remote helper:

```text
2ac8c6730768f86a221722a6ff259e3a4617134221498bd1956a63980a22a9b5  /cache/bin/a90_android_execns_probe
```

Usage output includes:

- `a90_android_execns_probe v138`
- `wifi-companion-esoc-req-registered-subsys-hold-preflight`
- `--allow-esoc-req-registered-subsys-hold-preflight`

Post-deploy health:

- `selftest` stayed `fail=0`.
- service-manager process hits: `0`.
- Wi-Fi netdev hits: `0`.
- helper execution without required mode returns rc `2`, which is expected for
  usage/allowlist output and was used only to verify marker strings.

## Interpretation

The helper on the device now supports the V880 REQ-registered subsystem-hold
preflight mode. However, operator-supplied source analysis after V881 narrows
the next useful observability gap:

- Initial `mdm_subsys_powerup()` needs the REQ engine, not userspace ownership
  of `CMD_ENG`; kernel-side eSoC code can call the power-on command internally.
- SDX50M may not emit an `ESOC_REQ_IMG` request because PCIe-based devices can
  boot from their own flash path rather than the older MDM9K Sahara-style image
  request loop.
- A future hold window should therefore log whether `ESOC_WAIT_FOR_REQ` ever
  produces a request while still keeping `NOTIFY`, explicit userspace
  `PWR_ON`, actors, HAL, scan/connect, and external networking blocked.

## Guardrails

- No live `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `PWR_ON`,
  `WAIT_FOR_REQ`, `NOTIFY`, or `/dev/subsys_esoc0` open in V881.
- No `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, service-manager trio, Wi-Fi
  HAL, scan/connect, credentials, DHCP/routes, or external ping.
- No boot image, partition, firmware, GPIO, sysfs, debugfs, module, or reboot
  action.

## Next

V882 should be helper `v139` source/build-only support for a passive
`ESOC_WAIT_FOR_REQ` observer inside the REQ-registered subsystem-hold proof.
Live subsystem-hold should wait until that observability is present.
