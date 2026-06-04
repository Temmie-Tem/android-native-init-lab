# Native Init V2107 Transport Preflight

## Summary

- Cycle: `V2107`
- Decision: `v2107-transport-no-bridge-no-tty-permission-rollback-blocked`
- Label: `transport-no-bridge-no-tty-permission`
- Pass: `False`
- Reason: no bridge is listening, current user cannot open /dev/ttyACM0, and passwordless sudo is unavailable
- Evidence: `tmp/wifi/v2107-tftp-persist-parent-traverse-handoff`

## Matrix

| area | value | detail |
| --- | --- | --- |
| bridge | False | 127.0.0.1:54321 |
| tty | True | mode=crw-rw---- gid=dialout user_can_rw=False |
| sudo | False | sudo: interactive authentication is required |
| autostart | False | ok=False pid= |
| version | False |  |
| selftest | False |  |

## Interpretation

- V2107 did not enter the flash/test-boot path because command transport was not healthy enough to execute a rollbackable producer-window run.
- This is not WLAN evidence and must not be classified as a producer-side result.

## Validation

- `python3 -m py_compile scripts/revalidation/native_wifi_tftp_persist_parent_traverse_handoff_v2107.py`
- `git diff --check`

## Safety

- No flash, reboot, test boot, rollback, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, AP QMI send, `tftp_server` ptrace, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan, bind/unbind, PMIC/GPIO/GDSC/regulator write, or firmware/partition write was used.

## Next

- Grant `/dev/ttyACM0` access or passwordless sudo, then rerun V2107; the runner will autostart the patched V2110 bridge and proceed only after clean `version` and `selftest` framing.
