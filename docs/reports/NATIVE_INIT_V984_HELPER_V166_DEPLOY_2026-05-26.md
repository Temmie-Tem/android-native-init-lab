# V984 Helper v166 Deploy

- generated: `2026-05-26`
- scope: deploy-only
- decision: `execns-helper-v166-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v984-execns-helper-v166-deploy/manifest.json`
- remote helper: `/cache/bin/a90_android_execns_probe`
- helper: `a90_android_execns_probe v166`
- helper sha256: `f184d79c1e6a72b12a8db5f51310cc82599fa1fed9a7cdde3c9814732a7621a8`

## Summary

V984 deployed helper `v166` to the device for the next bounded Android service-window live proof.

The run replaced the previous remote helper and verified post-deploy parity:

- remote sha matches the expected `v166` artifact
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
python3 -m py_compile scripts/revalidation/native_wifi_helper_v166_deploy_v984.py
python3 scripts/revalidation/native_wifi_helper_v166_deploy_v984.py preflight
python3 scripts/revalidation/native_wifi_helper_v166_deploy_v984.py --approval-phrase "approve v984 deploy execns helper v166 only; no daemon start and no Wi-Fi bring-up" --apply --assume-yes run
```

Result:

```text
decision: execns-helper-v166-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next

Rerun the bounded Android service-window live proof with helper `v166`.
