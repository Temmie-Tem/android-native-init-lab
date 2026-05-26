# V981 Helper v165 Deploy

- generated: `2026-05-26`
- scope: deploy-only
- decision: `execns-helper-v165-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v981-execns-helper-v165-deploy/manifest.json`
- remote helper: `/cache/bin/a90_android_execns_probe`
- helper: `a90_android_execns_probe v165`
- helper sha256: `5d4bda053547e0f67ee39356dc5c156927860551bb94456a8421c16f531f1981`

## Summary

V981 deployed helper `v165` to the device for the next bounded Android service-window live proof.

The run replaced the previous remote helper and verified post-deploy parity:

- remote sha matches the expected `v165` artifact
- remote usage contract contains the Android service-window mode and allow flag
- native boot/selftest remained clean
- no service-manager or Wi-Fi link surface was active during replacement

## Deploy Result

- transfer method: `serial`
- command: `serial appendfile + uudecode`
- chunks written: `886/886`
- chunk size: `1850`
- max command line: `3888` bytes
- safe line limit: `3968` bytes
- line check: `pass`

## Guardrails

- deploy-only helper replacement
- no daemon start
- no service-manager start
- no CNSS/Wi-Fi HAL/wificond/supplicant start
- no `qcwlanstate`
- no `/dev/subsys_esoc0` open
- no eSoC ioctl
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v165_deploy_v981.py
python3 scripts/revalidation/native_wifi_helper_v165_deploy_v981.py preflight
python3 scripts/revalidation/native_wifi_helper_v165_deploy_v981.py --approval-phrase "approve v981 deploy execns helper v165 only; no daemon start and no Wi-Fi bring-up" --apply --assume-yes run
```

Result:

```text
decision: execns-helper-v165-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next

Rerun the bounded Android service-window live proof with helper `v165`.
