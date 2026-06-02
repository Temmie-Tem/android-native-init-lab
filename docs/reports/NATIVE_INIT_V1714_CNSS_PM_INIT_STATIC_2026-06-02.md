# Native Init V1714 CNSS pm_init Static Classifier

## Summary

- Cycle: `V1714`
- Type: host-only `cnss-daemon` `pm_init@0xc39c` classifier
- Decision: `v1714-cnss-pm-init-static-map-pass`
- Result: `PASS`
- Reason: V1713 proves wlfw_start blocks inside pm_init; static map identifies get_system_info, pm_client_register, and pm_client_connect discriminators
- Evidence: `tmp/wifi/v1714-cnss-pm-init-static`

## Basis

- V1711 decision: `v1711-wlfw-start-prologue-static-map-pass` pass `True`
- V1713 decision: `v1713-wlfw-start-optional-pm-init1-call-no-return-rollback-pass` pass `True` rollback `True`
- V1713 label: `wlfw-start-optional-pm-init1-call-no-return`
- V1713 hits: `optional_pm_init1_call=1`, `optional_pm_init1_return=0`
- Legacy firmware-serve label: `firmware-not-requested`

## pm_init Map

| Target | Offset | Instruction | Meaning |
| --- | --- | --- | --- |
| `pm_init_entry` | `0xc39c` | `stp x29, x30, [sp, #-96]!` | function entry; V1713 proves wlfw_start blocks after calling this function |
| `pm_init_entry_log_call` | `0xc400` | `bl 0xa21c` | logs pm_init start with requested type |
| `pm_init_type_check` | `0xc404` | `cmp w19, #0x2` | rejects unsupported mdm type >= 2 |
| `pm_init_get_system_info_call` | `0xc444` | `bl get_system_info@plt` | reads modem/eSoC system info from libmdmdetect |
| `pm_init_system_info_ok` | `0xc470` | `ldr w3, [sp, #8]` | get_system_info succeeded and count is about to be logged/read |
| `pm_init_null_peripheral_branch` | `0xc49c` | `cbz x21, 0xc58c` | V1713 call uses x1=NULL, so this branch should enter the null-peripheral all-entry loop |
| `pm_init_null_peripheral_loop_entry` | `0xc58c` | `add x8, sp, #0x8` | null-peripheral path entry |
| `pm_init_null_loop_type_check` | `0xc5e0` | `ldur w8, [x26, #-4]` | iterates system-info entries looking for requested type |
| `pm_init_pm_client_register_call` | `0xc624` | `bl pm_client_register@plt` | registers peripheral manager client for matching entry |
| `pm_init_pm_client_register_retcheck` | `0xc628` | `cbnz w0, 0xc5b8` | detects pm_client_register return; failure loops to next entry |
| `pm_init_handle_load` | `0xc62c` | `ldr x19, [x20]` | loads pm client handle after registration success |
| `pm_init_pm_client_connect_call` | `0xc650` | `bl pm_client_connect@plt` | connects/votes to peripheral manager; likely live blocking candidate if register succeeds |
| `pm_init_pm_client_connect_retcheck` | `0xc654` | `mov w25, w0` | first proof that pm_client_connect returned |
| `pm_init_return_path` | `0xc554` | `ldr x8, [x28, #40]` | common return path |

## Pattern Checks

| Pattern | Present |
| --- | --- |
| `entry` | `True` |
| `start_log` | `True` |
| `type_check` | `True` |
| `get_system_info_call` | `True` |
| `system_info_ok_branch` | `True` |
| `null_peripheral_branch` | `True` |
| `null_path_entry` | `True` |
| `null_loop_type_check` | `True` |
| `pm_client_register_call` | `True` |
| `pm_client_register_retcheck` | `True` |
| `handle_load` | `True` |
| `pm_client_connect_call` | `True` |
| `pm_client_connect_retcheck` | `True` |
| `return_path` | `True` |

## Interpretation

- V1713 proves `wlfw_start` reaches `pm_init@0xc39c` and does not return from the first call.
- The call site uses the zero-argument path, so `pm_init` should eventually branch to the null-peripheral loop at `0xc58c` after `get_system_info` succeeds.
- The first concrete PM-client operations on that path are `pm_client_register@0xc624` and `pm_client_connect@0xc650`.
- Do not add PM/service-window actors until a bounded live probe proves whether this route blocks in `get_system_info`, `pm_client_register`, or `pm_client_connect`.

## Next Gate

- Type: source/build-only helper expansion followed by one rollbackable `pm_init` uprobe live run.
- Route: reuse V1713 internal-modem firmware-serve route only.
- Labels: `pm-init-get-system-info-blocked`, `pm-init-null-loop-not-reached`, `pm-init-register-call-no-return`, `pm-init-register-returned-no-connect`, `pm-init-connect-call-no-return`, `pm-init-connect-returned`, `cnss-target-unavailable`.
- Forbidden: adding PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.
