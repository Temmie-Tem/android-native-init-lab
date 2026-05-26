# Native Init V996 Helper v169 Deploy Plan

## Goal

Deploy helper `a90_android_execns_probe v169` to `/cache/bin/a90_android_execns_probe`
after V995 added `wificond` and `vndservicemanager` SELinux domain proof
coverage.

V996 is deploy-only. It must not run SELinux policy-load or any Android
service-window actor.

## Preconditions

- V995 helper build PASS.
- Local helper sha256:
  `c47f0659178186d45cf5199fdad4d198f0c69b6998f2127ff420f9e0f0204a74`
- Native bootstatus/selftest clean.
- No service-manager experiment process is running.
- No Wi-Fi link is active.

## Guardrails

- Deploy helper only.
- No SELinux policy load.
- No service-manager, Wi-Fi HAL, `wificond`, CNSS daemon, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO write, sysfs write, or debugfs write.

## Success Criteria

- Remote helper sha256 matches the V995 artifact.
- Remote helper usage exposes helper `v169` and the relevant
  `selinux-domain-proof` contract tokens.
- Post-deploy bootstatus/selftest remain clean.

## Next

If V996 passes, V997 should run a fresh current-boot SELinux proof gate:

1. refresh `selinuxfs`;
2. run current-boot V490 policy-load proof;
3. run an expanded post-load domain proof for service-manager trio plus
   `wificond`;
4. stop before any Android service-window actor starts.
