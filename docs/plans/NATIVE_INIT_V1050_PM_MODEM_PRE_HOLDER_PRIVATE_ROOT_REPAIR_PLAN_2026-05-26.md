# V1050 PM Modem Pre-Holder Private Root Repair Plan

## Goal

Repair the helper `v178` V1049 failure where the modem pre-holder returned
`ENOENT` even though the prepared private node existed at
`<temp_root>/dev/subsys_modem`.

## Evidence Basis

- V1049 live gate passed as a clean diagnostic but showed:
  - `private_node.subsys_modem.exists=1`
  - `modem_pre_holder_opened=0`
  - `modem_pre_holder_errno=2`
  - `pm_full_contract_seen=0`
- Source inspection showed the pre-holder child opened global
  `/dev/subsys_modem` without entering `paths->root`, while the materialized
  node only exists inside the helper private root.

## Method

1. Bump helper marker from `v178` to `v179`.
2. Add the missing flag/order text to usage output so deploy wrappers can verify
   the parser contract without relying only on sha equality.
3. In the modem pre-holder child, run `setsid()`, `chroot(paths->root)`, and
   `chdir("/")` before opening `/dev/subsys_modem`.
4. Emit explicit child diagnostics:
   - `modem_pre_holder_child_chroot`
   - `modem_pre_holder_path`
   - `modem_pre_holder_open_reported`
   - `modem_pre_holder_result_reported`
5. Confirm `modem_pre_holder_confirmed=1` only when the child explicitly reports
   open success and remains alive.
6. Build only; do not deploy or execute on-device in V1050.

## Hard Gates

No device contact, helper deploy, daemon start, subsystem open, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, external ping, sysfs write, GPIO write,
partition write, boot image write, or firmware mutation.

## Success Criteria

- Helper builds as static aarch64.
- `strings` confirms marker `a90_android_execns_probe v179`.
- `strings` confirms `--allow-pm-full-contract-with-modem-holder` and the new
  service-manager order are present in usage output.
- New pre-holder diagnostic strings are present.

## Next

V1051 should deploy helper `v179` only, then V1052 should rerun the bounded PM
full-contract-with-modem-holder live gate after the current-boot SELinux
preconditions are refreshed.
