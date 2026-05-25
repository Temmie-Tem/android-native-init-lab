# Native Init V910 Helper v149 Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| helper `v149` deploy-only wrapper | `tmp/wifi/v910-execns-helper-v149-deploy-preflight/manifest.json` | `execns-helper-v149-deploy-pass` |

V910 deployed helper `v149` to `/cache/bin/a90_android_execns_probe` and
verified remote checksum/mode parity. No runtime-contract actor was started in
this unit.

## Deploy

| Field | Value |
| --- | --- |
| transfer | `serial` |
| chunks_written | `837` |
| encoded_bytes | `1546991` |
| line_check_ok | `True` |
| remote_sha256 | `b615aa127e130e8b285642b34992102fa6d0c15702479bc1265dd4c5f06dff49` |

Readback confirmed:

```text
b615aa127e130e8b285642b34992102fa6d0c15702479bc1265dd4c5f06dff49  /cache/bin/a90_android_execns_probe
a90_android_execns_probe v149
wifi-companion-mdm-helper-runtime-contract-capture
```

## Guardrails

- `daemon_start_executed=False`
- `wifi_bringup_executed=False`
- service-manager process surface clean
- Wi-Fi link surface clean
- no `mdm_helper`, `ks`, `pm-service`, or `pm_proxy_helper` actor start
- no live eSoC ioctl or controller `/dev/subsys_esoc0` open
- no Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, reboot,
  boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write,
  module load/unload, or Wi-Fi bring-up

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v149_deploy_preflight.py
python3 scripts/revalidation/wifi_execns_helper_v149_deploy_preflight.py plan
python3 scripts/revalidation/wifi_execns_helper_v149_deploy_preflight.py preflight
python3 scripts/revalidation/wifi_execns_helper_v149_deploy_preflight.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v910 deploy execns helper v149 only; no actor start, no daemon start and no Wi-Fi bring-up" \
  run
```

## Next

Run the bounded runtime-contract capture with helper `v149` to classify the
`/dev/esoc-0` fd stall using fdinfo and proc stall snapshots.
