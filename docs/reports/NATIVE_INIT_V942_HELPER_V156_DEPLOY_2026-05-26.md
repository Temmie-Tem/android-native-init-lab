# V942 Execns Helper v156 Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| deploy-only live | `tmp/wifi/v942-execns-helper-v156-deploy/manifest.json` | `execns-helper-v156-deploy-pass` |

V942 deployed helper `v156` to `/cache/bin/a90_android_execns_probe` by serial
appendfile/uudecode. It did not start service-manager, CNSS, Wi-Fi HAL,
scan/connect, DHCP/routing, or external ping.

## Implementation

- Added deploy wrapper:
  `scripts/revalidation/native_wifi_helper_v156_deploy_v942.py`
- Local helper:
  `tmp/wifi/v941-execns-helper-v156-build/a90_android_execns_probe`
- Expected sha256:
  `ff5a87694bbb9c557aaaaacf61e1ceb0af9dffb3984d9f6887a2f93c8bceceb8`
- Required marker:
  `a90_android_execns_probe v156`

## Deploy

| Field | Value |
| --- | --- |
| method | `serial appendfile + uudecode` |
| chunk size | `1850` |
| chunks written | `837` |
| encoded bytes | `1547035` |
| line check | `ok` |
| cmdv1x | `true` |

The post-deploy checks report remote helper checksum/contract parity.

The inherited deploy base still renders some check names as
`local-helper-v154` / `remote-helper-v154`; V942 decision, wrapper constants,
marker, checksum, approval phrase, and report are for helper `v156`.

## Postflight

Manual postflight after deploy:

- `bootstatus`: `BOOT OK`, `selftest fail=0`.
- `selftest`: `pass=11 warn=1 fail=0`.
- `netservice status`: flag disabled, `ncm0` present, `tcpctl` stopped.

## Guardrails

- No service-manager start.
- No daemon start.
- No `pm-service`, `mdm_helper`, or `ks` start.
- No `/dev/subsys_esoc0` open.
- No eSoC ioctl.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP/route mutation.
- No external ping.
- No boot image or partition write.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v156_deploy_v942.py
python3 scripts/revalidation/native_wifi_helper_v156_deploy_v942.py plan
python3 scripts/revalidation/native_wifi_helper_v156_deploy_v942.py preflight
python3 scripts/revalidation/native_wifi_helper_v156_deploy_v942.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v942 deploy execns helper v156 only; no daemon start and no Wi-Fi bring-up" \
  run
```

## Next

V943 should run a bounded runtime-contract capture with helper `v156` and
classify the new `mdm_helper_queue_timing.*` evidence. Keep `/dev/subsys_esoc0`,
eSoC notifications, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, and
external ping blocked until that evidence is classified.
