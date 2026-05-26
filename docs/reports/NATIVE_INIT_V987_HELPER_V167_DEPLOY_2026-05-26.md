# V987 Helper v167 Deploy

- generated: `2026-05-26`
- scope: deploy-only
- decision: `execns-helper-v167-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v987-execns-helper-v167-deploy/manifest.json`
- remote helper: `/cache/bin/a90_android_execns_probe`
- helper: `a90_android_execns_probe v167`
- helper sha256: `fa96337b9103a411d6e229fe9ada744a6ed7df296f3d986e5a9d00a861736626`

## Summary

V987 deployed helper `v167` to the device for the next bounded Android
service-window live proof.

The run replaced helper `v166` and verified post-deploy parity:

- remote sha matches the expected `v167` artifact
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
python3 -m py_compile scripts/revalidation/native_wifi_helper_v167_deploy_v987.py
python3 scripts/revalidation/native_wifi_helper_v167_deploy_v987.py preflight
python3 scripts/revalidation/native_wifi_helper_v167_deploy_v987.py --approval-phrase "approve v987 deploy execns helper v167 only; no daemon start and no Wi-Fi bring-up" --apply --assume-yes run
python3 scripts/revalidation/a90ctl.py bootstatus
```

Result:

```text
decision: execns-helper-v167-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

Post-deploy device status:

```text
boot: BOOT OK shell 4.6s
selftest: pass=11 warn=1 fail=0
```

## Next

Rerun the bounded Android service-window live proof with helper `v167` and
inspect `wificond` ptrace crash context.
