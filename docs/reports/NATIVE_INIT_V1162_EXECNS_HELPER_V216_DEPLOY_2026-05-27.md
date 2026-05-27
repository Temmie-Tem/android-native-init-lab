# Native Init V1162 Execns Helper v216 Deploy Report

Date: `2026-05-27`

## Result

- Decision: `execns-helper-v216-deploy-pass`
- Pass: `true`
- Helper: `a90_android_execns_probe v216`
- Deploy wrapper: `scripts/revalidation/wifi_execns_helper_v216_deploy_preflight.py`
- Evidence: `tmp/wifi/v1162-execns-helper-v216-deploy/manifest.json`
- Summary: `tmp/wifi/v1162-execns-helper-v216-deploy/summary.md`
- Remote path: `/cache/bin/a90_android_execns_probe`
- SHA256: `b9518555ef53f8e721f8a057c8145085b3ba91899c34609c59cb1885e8b71241`

## Summary

V1162 deployed helper `v216` to `/cache/bin/a90_android_execns_probe` and
verified the remote SHA and usage output.  The first run with serial chunk size
`3000` failed before writing because the encoded cmdv1x line exceeded the native
console safety limit.  The retry used serial chunk size `1800` and completed.

## Deploy Details

| key | value |
| --- | --- |
| method | `serial appendfile + uudecode` |
| serial_chunk_size | `1800` |
| chunks_written | `960` |
| encoded_bytes | `1727624` |
| max_cmdv1_line_bytes | `3788` |
| safe_line_limit | `3968` |
| line_check_ok | `true` |

## Remote Verification

Executed after deploy:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 15 run /cache/bin/toybox sha256sum /cache/bin/a90_android_execns_probe
python3 scripts/revalidation/a90ctl.py --timeout 10 run /cache/bin/a90_android_execns_probe --help
```

Result:

```text
b9518555ef53f8e721f8a057c8145085b3ba91899c34609c59cb1885e8b71241  /cache/bin/a90_android_execns_probe
a90_android_execns_probe v216
--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd
```

## Safety

- Device mutation was limited to replacing `/cache/bin/a90_android_execns_probe`.
- No service-manager, PM actor, CNSS daemon, `mdm_helper`, Wi-Fi HAL,
  scan/connect, credential use, DHCP, route, external ping, partition write,
  flash, or reboot was executed by the deploy gate.
- NCM was unavailable, so the transfer used serial fallback.

## Next Gate

V1163 should run the bounded late `pm-proxy` live gate with helper `v216` and
classify whether `pm-service` reaches `/dev/subsys_esoc0`, MHI/`ks`, WLFW
service69, `mdm3`, or `wlan0`.
