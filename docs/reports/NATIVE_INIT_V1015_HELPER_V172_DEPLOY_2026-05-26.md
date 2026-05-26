# V1015 Helper v172 Deploy

- date: `2026-05-26`
- scope: deploy-only helper replacement
- decision: `execns-helper-v172-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v1015-execns-helper-v172-deploy/manifest.json`

## Summary

V1015 deployed `a90_android_execns_probe v172` to:

```text
/cache/bin/a90_android_execns_probe
```

No daemon, service-manager, Wi-Fi HAL, `wificond`, scan/connect, DHCP, route, or
external ping was executed.

## Deploy Evidence

| Item | Value |
| --- | --- |
| local artifact | `tmp/wifi/v1014-execns-helper-v172-build/a90_android_execns_probe` |
| expected sha256 | `0c9b6d34be91211255a1359198329405806092fb9b4eeb4f24d3089e878df54d` |
| transfer method | serial appendfile + uudecode |
| chunk size | `1850` |
| chunks written | `886` |
| line check | pass |
| remote sha | match |
| remote marker | `a90_android_execns_probe v172` |
| remote order token | `after-mdm-helper-esoc-fd-with-wifi-surface` |

## Health

Postflight remained healthy:

- bootstatus: `BOOT OK shell 4.3s`
- selftest: `pass=11 warn=1 fail=0`
- service-manager process surface: clean
- Wi-Fi link surface: clean
- remote helper contract: pass

## Transfer Note

The initial `--serial-chunk-size 3000` attempt was rejected before writing any
chunks because it exceeded the native console safe line limit. The successful
deploy used `--serial-chunk-size 1850`.

## Guardrails

- `daemon_start_executed=False`
- `wifi_bringup_executed=False`
- no service-manager/CNSS/Wi-Fi HAL/`wificond` live start
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no eSoC ioctl, subsystem open, notify, BOOT_DONE, GPIO/sysfs/debugfs write
- no boot image, partition, or firmware write

## Next

Proceed to V1016:

```text
bounded after-fd Wi-Fi surface matrix live gate
```

V1016 should run the new `after-mdm-helper-esoc-fd-with-wifi-surface` order with
strict timeout and cleanup, observe WLFW/BDF/`wlan0`, and still avoid
scan/connect until the lower Wi-Fi surface is proven.
