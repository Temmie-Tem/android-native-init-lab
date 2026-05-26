# V996 Helper v169 Deploy

- generated: `2026-05-26`
- scope: deploy-only helper update
- decision: `execns-helper-v169-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v996-execns-helper-v169-deploy/manifest.json`
- helper: `a90_android_execns_probe v169`
- helper sha256: `c47f0659178186d45cf5199fdad4d198f0c69b6998f2127ff420f9e0f0204a74`
- script: `scripts/revalidation/native_wifi_helper_v169_deploy_v996.py`

## Summary

V996 deployed helper `v169` to `/cache/bin/a90_android_execns_probe` and verified
remote sha/contract parity. The deploy used the existing serial-safe transfer
path:

```text
method=serial
chunk_size=1850
chunks=886
chunks_written=886
line_check_ok=True
```

No daemon or Wi-Fi bring-up action occurred.

## Results

| Item | Result |
| --- | --- |
| local helper v169 | PASS |
| native health before deploy | PASS |
| service-manager process surface clean | PASS |
| Wi-Fi link surface clean | PASS |
| remote helper v169 after deploy | PASS |
| approval gate | PASS |
| post-deploy bootstatus/selftest | PASS |

## Device Health

Post-deploy check:

```text
boot: BOOT OK shell 4.6s
selftest: pass=11 warn=1 fail=0
exposure: ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

## Guardrails

- helper deploy only
- no SELinux policy load
- no service-manager start
- no Wi-Fi HAL start
- no `wificond` start
- no daemon start
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no boot image or partition write

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v169_deploy_v996.py
python3 scripts/revalidation/native_wifi_helper_v169_deploy_v996.py preflight
python3 scripts/revalidation/native_wifi_helper_v169_deploy_v996.py \
  --approval-phrase "approve v996 deploy execns helper v169 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes run
python3 scripts/revalidation/a90ctl.py bootstatus
python3 scripts/revalidation/a90ctl.py selftest
```

Result:

```text
decision: execns-helper-v169-deploy-pass
pass: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next

V997 should run the current-boot SELinux refresh/domain proof. It should stop
before service-manager, HAL, `wificond`, scan/connect, credentials, DHCP, or
external ping.
