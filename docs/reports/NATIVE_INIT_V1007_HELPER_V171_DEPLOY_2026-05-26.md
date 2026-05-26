# V1007 Helper v171 Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| deploy-only run | `tmp/wifi/v1007-execns-helper-v171-deploy/manifest.json` | `execns-helper-v171-deploy-pass` |

V1007 deployed helper `v171` to `/cache/bin/a90_android_execns_probe` and
proved remote sha/contract parity. No daemon or Wi-Fi bring-up ran.

## Deployment

| Field | Value |
| --- | --- |
| method | `serial appendfile + uudecode` |
| chunk size | `1850` |
| chunks written | `886/886` |
| line check | `line_check_ok=True` |
| remote helper sha | `347f38ab24d67bf300bd6dccd033a081328ec5afdd711b49f3d0d2f9328cf3a1` |
| helper marker | `a90_android_execns_probe v171` |

The pre-deploy remote helper was not v171, so the approved run installed the
new artifact. Post-deploy checks confirmed `sha_match=True` and
`contract=True`.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v171_deploy_v1007.py
python3 scripts/revalidation/native_wifi_helper_v171_deploy_v1007.py \
  --out-dir tmp/wifi/v1007-execns-helper-v171-deploy-preflight \
  preflight
python3 scripts/revalidation/native_wifi_helper_v171_deploy_v1007.py \
  --out-dir tmp/wifi/v1007-execns-helper-v171-deploy \
  --approval-phrase "approve v1007 deploy execns helper v171 only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
git diff --check
```

Result:

```text
decision: execns-helper-v171-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## Postflight

Post-deploy checks remained clean:

- native health PASS;
- service-manager process count `0`;
- Wi-Fi link surface count `0`;
- remote helper sha/contract PASS.

## Guardrails

V1007 was deploy-only:

- no SELinux policy load;
- no Android service-window actor start;
- no `/dev/esoc-0` or `/dev/subsys_esoc0` open;
- no eSoC ioctl;
- no Wi-Fi scan/connect/link-up;
- no credential use;
- no DHCP/routes/external ping;
- no boot image or partition mutation.

## Next

Plan V1008 as the live current-boot fd-poll service-window gate:

1. refresh current-boot `selinuxfs`, V490 policy-load proof, and V997 domain
   proof because those are boot-ephemeral;
2. run helper `v171` service-window subsystem trigger capture;
3. inspect `android_wifi_service_window.fd_poll.*` and aggregate fd-poll markers;
4. keep the existing final `/dev/subsys_esoc0` trigger predicate fail-closed;
5. perform cleanup/reboot only if postflight cannot prove actor cleanup.
