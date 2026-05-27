# Native Init V1138 Execns Helper v214 Deploy Report

Date: `2026-05-27`

## Result

- Decision: `execns-helper-v214-deploy-pass`
- Pass: `true`
- Deploy evidence: `tmp/wifi/v1138-execns-helper-v214-deploy-retry/manifest.json`
- Post-deploy preflight: `tmp/wifi/v1138-execns-helper-v214-postdeploy-preflight/manifest.json`
- Deployed helper marker: `a90_android_execns_probe v214`
- Expected helper SHA256:
  `4dd6dea42fddfc1b70732e5695323421a0abf505530ab2d437c6e5418a75638f`
- Deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v214_deploy_preflight.py`

## Summary

V1138 deployed helper `v214` to:

```text
/cache/bin/a90_android_execns_probe
```

The deployed helper contains the V1137 post-PM `mdm_helper`/eSoC observer mode:

```text
wifi-companion-post-pm-mdm-helper-esoc-observer
```

The post-deploy read-only preflight confirmed the remote helper is current:

```text
remote-helper-v214 pass deploy sha_match=True marker_mode=True
native-clean pass blocker status/selftest rc=0 fail=0 expected
service-manager-processes-clean pass blocker process_count=0
wifi-link-surface-clean pass blocker wifi_link_count=0
```

## Deploy Details

NCM was present on the device but the host did not have `192.168.7.1/24`
assigned to the A90 NCM interface, and noninteractive `sudo` was unavailable.
The deploy therefore used the serial fallback.

The first serial attempt used `--serial-chunk-size 3000` and correctly failed
before writing chunks because the encoded command line exceeded the native
console safe line limit:

```text
max_cmdv1_line_bytes=6188
safe_line_limit=3968
chunks_written=0
```

The successful retry used:

```text
--serial-chunk-size 1800
```

Successful deploy evidence:

```text
method=serial
chunk_size=1800
chunks=960
chunks_written=960
max_cmdv1_line_bytes=3788
safe_line_limit=3968
line_check_ok=True
```

Remote SHA after deploy:

```text
4dd6dea42fddfc1b70732e5695323421a0abf505530ab2d437c6e5418a75638f  /cache/bin/a90_android_execns_probe
```

## Safety

V1138 did not execute any Wi-Fi bring-up path.

- PM/CNSS live actors: not executed.
- service-manager/hwservicemanager/vndservicemanager start: not executed.
- `mdm_helper`: not started.
- Wi-Fi HAL/wificond/supplicant/hostapd: not started.
- Scan/connect/link-up: not executed.
- Credentials: not used.
- DHCP/route/external ping: not executed.
- Partition write/boot image write/flash/reboot: not executed.

The only intended device mutation was replacing `/cache/bin/a90_android_execns_probe`.

## Cleanup

During host path probing, native `netservice` was briefly started to test NCM.
It was stopped after deploy validation.

Final cleanup state:

```text
netservice: flag=/cache/native-init-netservice enabled=no
netservice: ncm0=absent tcpctl=stopped
selftest: pass=11 warn=1 fail=0
```

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v214_deploy_preflight.py

python3 scripts/revalidation/wifi_execns_helper_v214_deploy_preflight.py \
  --transfer-method serial \
  --serial-chunk-size 1800 \
  --approval-phrase 'approve v1138 deploy execns helper v214 only; no daemon start and no Wi-Fi bring-up' \
  --apply \
  --assume-yes \
  run

python3 scripts/revalidation/wifi_execns_helper_v214_deploy_preflight.py \
  --transfer-method serial \
  --serial-chunk-size 1800 \
  preflight
```

Post-deploy preflight result:

```text
decision: execns-helper-v214-deploy-preflight-ready
pass: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next

V1139 should be the first bounded live gate for:

```text
wifi-companion-post-pm-mdm-helper-esoc-observer
```

It should preserve the V1134 upper PM/CNSS success path, then start
`mdm_helper` only after CNSS in the same PM observer window and classify
`/dev/esoc-0`, `/dev/subsys_esoc0`, MHI pipe, `ks`, `mdm3`, service69, WLFW,
BDF, and `wlan0`.

Wi-Fi HAL, scan/connect, credentials, DHCP/route, and external ping remain
forbidden until lower publication advances.
