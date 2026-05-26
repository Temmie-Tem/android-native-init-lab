# V978 Helper v164 Deploy

- generated: `2026-05-26`
- scope: deploy-only
- decision: `execns-helper-v164-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v978-execns-helper-v164-deploy/manifest.json`
- remote helper: `/cache/bin/a90_android_execns_probe`
- helper: `a90_android_execns_probe v164`
- helper sha256: `891f8363c09dbb8263a7e85fe30b47c0e8f0142ee99e04bbe94a34c10b46966e`

## Summary

V978 deployed helper `v164` to the device for the next bounded Android service-window live proof.

The run replaced the previous remote helper and verified post-deploy parity:

- remote sha matches the expected `v164` artifact
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
python3 -m py_compile scripts/revalidation/native_wifi_helper_v164_deploy_v978.py
python3 scripts/revalidation/native_wifi_helper_v164_deploy_v978.py preflight
python3 scripts/revalidation/native_wifi_helper_v164_deploy_v978.py --approval-phrase "approve v978 deploy execns helper v164 only; no daemon start and no Wi-Fi bring-up" --apply --assume-yes run
```

Result:

```text
decision: execns-helper-v164-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next

Rerun the bounded Android service-window live proof with helper `v164`.
