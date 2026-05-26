# V1003 Helper v170 Deploy Plan

## Goal

Deploy `a90_android_execns_probe v170` to `/cache/bin/a90_android_execns_probe`
after V1002 added the Android service-window scoped subsystem trigger capture
mode.

V1003 is deploy-only. It must not run SELinux policy-load, Android service
actors, `/dev/subsys_esoc0`, Wi-Fi HAL bring-up, scan/connect, credentials,
DHCP, routing, or external ping.

## Preconditions

- V1002 helper build PASS.
- Local helper sha256:
  `edbccfef2fd117c5264c140ff5b2f4cec5424c917151607cecc309268cd9c254`
- Native bootstatus/selftest clean.
- No service-manager experiment process is running.
- No Wi-Fi link is active.

## Guardrails

- Deploy helper only.
- No SELinux policy load.
- No service-manager, Wi-Fi HAL, `wificond`, CNSS daemon, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO write, sysfs write, debugfs write, or eSoC/subsystem
  trigger.

## Success Criteria

- Remote helper sha256 matches the V1002 artifact.
- Remote helper usage exposes helper `v170` and the new service-window subsystem
  trigger contract tokens.
- Post-deploy bootstatus/selftest remain clean.
- Transcript records no daemon start and no Wi-Fi bring-up.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v170_deploy_v1003.py
python3 scripts/revalidation/native_wifi_helper_v170_deploy_v1003.py plan
python3 scripts/revalidation/native_wifi_helper_v170_deploy_v1003.py preflight
python3 scripts/revalidation/native_wifi_helper_v170_deploy_v1003.py \
  --approval-phrase "approve v1003 deploy execns helper v170 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

## Next

If V1003 passes, V1004 should refresh current-boot SELinux proof, then run the
new service-window scoped subsystem trigger capture. V1004 must still block
scan/connect, credentials, DHCP/routing, and external ping.
