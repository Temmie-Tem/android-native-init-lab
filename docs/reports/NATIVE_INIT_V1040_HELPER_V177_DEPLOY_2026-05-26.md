# V1040 Helper v177 Deploy

- date: `2026-05-26`
- scope: deploy-only live gate
- decision: `execns-helper-v177-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v1040-execns-helper-v177-deploy/manifest.json`
- remote helper: `/cache/bin/a90_android_execns_probe`
- remote sha256: `d71c7c87a7759eb8e2eb0058c2057e0e9348a4c6f572f48d6d9b2962053a4795`

## Summary

V1040 deployed helper `a90_android_execns_probe v177` to the native device.
The readback sha matches the V1039 static artifact, and remote usage confirms
the helper exposes the expected service-manager matrix and PM full-contract
order support.

No service-manager, CNSS actor, Wi-Fi HAL, `wificond`, scan/connect, DHCP,
routing, credentials, external ping, eSoC ioctl, subsystem open, GPIO/sysfs
write, boot-image write, or partition write was executed.

## Result

| Item | Result |
| --- | --- |
| preflight native health | pass |
| service-manager process surface | clean |
| Wi-Fi link surface | clean |
| first deploy attempt with `--serial-chunk-size 3000` | fail-closed before write, line-limit unsafe |
| retry with default chunk size `1850` | pass |
| chunks written | `886/886` |
| post-deploy remote sha | pass |
| post-deploy helper marker | `a90_android_execns_probe v177` |
| post-deploy native health | pass |
| daemon/Wi-Fi bring-up | not executed |

## Evidence

- manifest: `tmp/wifi/v1040-execns-helper-v177-deploy/manifest.json`
- summary: `tmp/wifi/v1040-execns-helper-v177-deploy/summary.md`
- install transcript: `tmp/wifi/v1040-execns-helper-v177-deploy/host/serial-install-helper.txt`
- post sha readback: `tmp/wifi/v1040-execns-helper-v177-deploy/native/post-sha-helper.txt`
- post usage readback: `tmp/wifi/v1040-execns-helper-v177-deploy/native/post-helper-usage.txt`
- post boot health: `tmp/wifi/v1040-execns-helper-v177-deploy/native/post-bootstatus.txt`

## Guardrails

- Deploy-only mutation: `/cache/bin/a90_android_execns_probe` replacement.
- No actor start, daemon start, service-manager start, Wi-Fi HAL, `wificond`,
  scan/connect/link-up, credential use, DHCP/routes, external ping, boot image
  write, partition write, firmware mutation, GPIO/sysfs/debugfs write, eSoC
  ioctl, or live `/dev/subsys_esoc0` open.
- The oversize chunk attempt failed before writing any chunk; the successful
  retry used the deploy helper's safe line-limit check.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v177_deploy_v1040.py
python3 scripts/revalidation/native_wifi_helper_v177_deploy_v1040.py preflight
python3 scripts/revalidation/native_wifi_helper_v177_deploy_v1040.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v1040 deploy execns helper v177 only; no daemon start and no Wi-Fi bring-up" \
  run
```

Live result:

```text
decision: execns-helper-v177-deploy-pass
pass: True
reason: helper v177 deployed or already current; no daemon or Wi-Fi bring-up executed
next: rerun the bounded PM full-contract live proof
```

## Next

V1041 should run the bounded PM full-contract live proof with helper `v177`.
The immediate question is whether `pm_proxy_helper` and `pm-service` now form
the Android-positive `/dev/subsys_modem` fd contract, or whether the new focused
PM fd/wchan snapshots identify the remaining blocker.
