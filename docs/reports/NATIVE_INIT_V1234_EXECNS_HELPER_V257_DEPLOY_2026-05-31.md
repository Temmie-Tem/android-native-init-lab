# V1234 Execns Helper v257 Deploy

- date: `2026-05-31`
- result: `PASS`
- decision: `execns-helper-v257-deploy-pass`
- helper: `a90_android_execns_probe v257`
- sha256: `66c3bc5a9cc0daa9a9a04fe7b98ebe2d7aa974798ed131adf82e5b314b2753e5`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v257_deploy_preflight_v1234.py`
- evidence: `tmp/wifi/v1234-execns-helper-v257-deploy/manifest.json`

## Purpose

V1233 produced helper `v257` with the bounded `post_wait_branch.*` snapshot.
V1234 deployed that exact static helper to `/cache/bin/a90_android_execns_probe`
for the next bounded live gate.

## Result

The deploy completed by serial fallback because NCM was not active at preflight.
The serial path used cmdv1x-safe append chunks and verified the remote helper
after install.

| Field | Value |
|---|---|
| transfer method | `serial` |
| chunks | `960` |
| chunk size | `1800` |
| encoded bytes | `1727624` |
| line check | `pass` |
| remote helper | `v257` |

## Safety

This was deploy-only. It wrote `/cache/bin/a90_android_execns_probe` but did not
start service-manager, PM/CNSS actors, `mdm_helper`, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, flash, boot image write, or partition
write.

Post-deploy checks remained clean:

- native version: `A90 Linux init 0.9.68 (v724)`
- selftest/status: `fail=0`
- service-manager process surface: clean
- Wi-Fi link surface: clean

## Next Gate

V1235 should run the bounded branch snapshot live gate using helper `v257`.
