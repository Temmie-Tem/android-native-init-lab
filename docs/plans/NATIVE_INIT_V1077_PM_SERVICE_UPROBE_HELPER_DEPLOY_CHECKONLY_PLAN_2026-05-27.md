# Native Init V1077 PM Service Uprobe Helper Deploy Check-only Plan

## Goal

Deploy the V1076 PM-service uprobe helper to native v724 and prove that its
check-only/default modes do not write tracefs, attach BPF, run child commands,
or touch Wi-Fi state.

## Background

V1076 built `a90_pm_service_uprobe_counter v1076` as a static AArch64 helper.
Before any live uprobe registration, the reviewed artifact must be installed on
the device and verified in no-attach modes.

## Gate

- Add deploy/check-only runner:
  `scripts/revalidation/native_wifi_pm_service_uprobe_helper_deploy_checkonly_v1077.py`.
- Use NCM `tcpctl_host.py install` to deploy the helper to
  `/cache/bin/a90_pm_service_uprobe_counter`.
- Verify remote sha256 matches the V1076 local artifact.
- Run:
  - `/cache/bin/a90_pm_service_uprobe_counter --check-only`
  - `/cache/bin/a90_pm_service_uprobe_counter`
- Confirm device health with `netservice status` and `selftest`.

## Forbidden

- No `--allow-tracefs-write`.
- No `--allow-attach`.
- No `--allow-child-command`.
- No PM actor, service-manager, CNSS, Wi-Fi HAL, `mdm_helper`, or child command
  execution.
- No scan/connect/DHCP/route/external ping.
- No `/dev/esoc*`, `wlan.ko`, boot image, partition write, or reboot.

## Success Criteria

- NCM/tcpctl responds before deploy.
- Remote helper sha256 equals the V1076 artifact sha256.
- `--check-only` prints marker `a90_pm_service_uprobe_counter v1076` and:
  - `result=check-only`
  - `tracefs_write_attempted=0`
  - `attach_attempted=0`
  - `child_command_attempted=0`
- Default no-argument mode has the same no-attach behavior.
- Native selftest remains `fail=0`.

## Expected Decision Use

If V1077 passes, V1078 may run the first bounded active proof: explicit tracefs
mount/register/attach/cleanup around the PM observer, still without Wi-Fi HAL,
scan/connect, credentials, DHCP, route changes, or external ping.
