# V901 Helper v145 Allowlist Repair and Deploy Plan

## Goal

Repair the helper global v235 allowlist gap found by the first V900 attempt,
then deploy the repaired helper as `v145`.

## Trigger

The first V900 live runner attempt failed before any live contract action:

- decision: `v900-step-failed`
- helper output: `arguments do not match v235 allowlist`
- cause: mode `wifi-companion-mdm-helper-ks-image-contract-preflight` existed
  in parser/usage, but was missing from the global v235 accepted mode list.

## Method

1. Bump helper marker to `a90_android_execns_probe v145`.
2. Add `wifi-companion-mdm-helper-ks-image-contract-preflight` to the global
   v235 mode allowlist.
3. Add `--allow-mdm-helper-ks-contract-preflight` to usage so remote usage
   evidence is complete.
4. Build a static ARM64 helper artifact.
5. Deploy only `/cache/bin/a90_android_execns_probe`.
6. Verify remote sha, marker, mode token, native health, actor-clean state, and
   Wi-Fi-link-clean state.

## Hard Gates

- Deploy-only write to `/cache/bin/a90_android_execns_probe`.
- No live eSoC ioctl.
- No `/dev/subsys_esoc0` open.
- No `mdm_helper` start.
- No `ks` start.
- No service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, boot image write, partition write, firmware
  mutation, GPIO/sysfs/debugfs write, module load/unload, reboot, or Wi-Fi
  link-up.

## Success Criteria

- Static ARM64 build succeeds and has no dynamic section.
- Artifact advertises `a90_android_execns_probe v145`.
- Artifact advertises mode
  `wifi-companion-mdm-helper-ks-image-contract-preflight`.
- Artifact advertises allow flag
  `--allow-mdm-helper-ks-contract-preflight`.
- Approved deploy returns `execns-helper-v145-deploy-pass`.
- Remote sha256 matches the local helper artifact.

## Next

After V901 deploy passes, rerun V900 bounded live proof with helper `v145`.
