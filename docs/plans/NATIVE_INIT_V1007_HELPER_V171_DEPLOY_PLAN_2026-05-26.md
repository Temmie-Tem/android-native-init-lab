# V1007 Helper v171 Deploy Plan

## Goal

Deploy helper `v171` to `/cache/bin/a90_android_execns_probe` and prove remote
sha/contract parity without starting Android actors or Wi-Fi bring-up.

## Scope

1. Verify local V1006 helper artifact sha and strings.
2. Capture pre-deploy native health and exposure.
3. Serial-deploy only the helper binary.
4. Verify remote sha and usage contract.
5. Capture post-deploy health and confirm no service-manager/Wi-Fi actor/link
   surface was started.

## Guardrails

Allowed:

- serial file transfer to `/cache/bin/a90_android_execns_probe`;
- remote `chmod`/atomic install steps handled by the existing private deploy
  helper;
- read-only postflight commands.

Forbidden:

- SELinux policy load;
- Android service-window actor start;
- `/dev/esoc-0` or `/dev/subsys_esoc0` open;
- eSoC ioctl;
- Wi-Fi scan/connect/link-up;
- credential use;
- DHCP/routes/external ping;
- boot image or partition mutation.

## Success Criteria

V1007 passes if:

- remote helper sha is
  `347f38ab24d67bf300bd6dccd033a081328ec5afdd711b49f3d0d2f9328cf3a1`;
- remote usage contains `a90_android_execns_probe v171`;
- remote usage contains service-window trigger mode and fd-poll-capable contract
  strings;
- postflight bootstatus/selftest remain healthy;
- no Wi-Fi or actor surface is active.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v171_deploy_v1007.py
python3 scripts/revalidation/native_wifi_helper_v171_deploy_v1007.py preflight
python3 scripts/revalidation/native_wifi_helper_v171_deploy_v1007.py \
  --approval-phrase "approve v1007 deploy execns helper v171 only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
git diff --check
```
