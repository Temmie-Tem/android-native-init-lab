# Native Init V1706 CNSS WLFW Start Branch Static Classifier

## Summary

- Cycle: `V1706`
- Type: host-only cnss-daemon `wlfw_start` branch classifier
- Decision: `v1706-wlfw-start-branch-static-map-pass`
- Result: `PASS`
- Reason: V1705 proves wlfw_start entry but no worker entry; static branch map identifies the pre-worker pthread_create gate
- Evidence: `tmp/wifi/v1706-cnss-wlfw-start-branch-static`

## Basis

- V1703 decision: `v1703-cnss-wlfw-downstream-static-map-pass` pass `True` sha ok `True`
- V1705 decision: `v1705-wlfw-worker-thread-missing-after-wlfw-start-rollback-pass` pass `True` rollback `True`
- V1705 label: `wlfw-worker-thread-missing-after-wlfw-start`
- V1705 hits: `wlfw_start=1`, `wlfw_service_request=0`, `ind_register=0`, `cap=0`
- Legacy firmware-serve label: `firmware-not-requested`

## Branch Map

| Target | Offset | Meaning |
| --- | --- | --- |
| `entry` | `0xec00` | wlfw_start entry; already proven by V1702/V1705 |
| `cal_mutex_init_retcheck` | `0xec5c` | first pthread_mutex_init return check; failure logs cal_mutex init and exits before worker setup |
| `mutex_init_retcheck` | `0xec7c` | second pthread_mutex_init return check; failure exits before condition variables |
| `cond_init_retcheck` | `0xeca0` | first pthread_cond_init return check; failure exits before DMS/thread creation |
| `cond_rsp_init_retcheck` | `0xecc0` | second pthread_cond_init return check; failure exits before DMS/thread creation |
| `dms_initialize_call` | `0xecd4` | calls pthread_initialize_dms before creating wlfw_service_request worker |
| `dms_initialize_retcheck` | `0xecd8` | DMS initialization failure path skips wlfw_service_request pthread_create |
| `wlfw_worker_pthread_create_call` | `0xecf0` | attempts to create wlfw_service_request@0xd9fc |
| `wlfw_worker_pthread_create_retcheck` | `0xecf4` | pthread_create return check; success branches to Start done flag/log |
| `wlfw_worker_pthread_create_failure` | `0xecf8` | pthread_create returned nonzero; cleanup follows and worker never starts |
| `cleanup_after_preworker_failure` | `0xed0c` | shared cleanup after DMS init failure or worker pthread_create failure |
| `wlfw_worker_pthread_create_success` | `0xeda0` | pthread_create returned zero; if worker entry is still absent, scheduling/target mismatch must be checked |
| `wlfw_start_success_flag` | `0xedc0` | sets wlfw start done flag on success path |

## Pattern Checks

| Pattern | Present |
| --- | --- |
| `entry` | `True` |
| `log_starting` | `True` |
| `cal_mutex_init_retcheck` | `True` |
| `cal_mutex_init_fail_branch` | `True` |
| `mutex_init_retcheck` | `True` |
| `mutex_init_fail_branch` | `True` |
| `cond_init_retcheck` | `True` |
| `cond_init_fail_branch` | `True` |
| `cond_rsp_init_retcheck` | `True` |
| `cond_rsp_init_fail_branch` | `True` |
| `dms_initialize_call` | `True` |
| `dms_initialize_retcheck` | `True` |
| `wlfw_worker_thread_target` | `True` |
| `wlfw_worker_pthread_create_call` | `True` |
| `wlfw_worker_pthread_create_retcheck` | `True` |
| `wlfw_worker_pthread_create_failure` | `True` |
| `cleanup_after_preworker_failure` | `True` |
| `success_path` | `True` |
| `success_flag` | `True` |

## Failure / Status Strings

| Key | Offset | Text | Match |
| --- | --- | --- | --- |
| `wlfw_start` | `0x5ab9` | `wlfw_start` | `True` |
| `wlfw_start_starting_format` | `0x5f96` | `%s: Starting` | `True` |
| `start_done_format` | `0x3ee1` | `%s: Start done: %d` | `True` |
| `failed_create_thread` | `0x6865` | `Failed to create thread, ret %d` | `True` |
| `failed_init_cal_mutex` | `0x64b9` | `Failed to init cal_mutex, ret %d` | `True` |
| `failed_init_mutex` | `0x588d` | `Failed to init mutex, ret %d` | `True` |
| `failed_init_cond` | `0x4f23` | `Failed to init cond, ret %d` | `True` |
| `failed_init_cond_rsp` | `0x451f` | `Failed to init cond_rsp, ret %d` | `True` |
| `failed_destroy_cond_rsp` | `0x4f3f` | `Failed to destroy cond_rsp, ret %d` | `True` |
| `failed_destroy_cond` | `0x6333` | `Failed to destroy cond, ret %d` | `True` |
| `failed_destroy_mutex` | `0x6885` | `Failed to destroy mutex, ret %d` | `True` |
| `failed_destroy_cal_mutex` | `0x4a17` | `Failed to destroy cal_mutex, ret %d` | `True` |

## Interpretation

- `wlfw_start` logs `Starting` before any meaningful initialization, so a `wlfw_start` hit alone is not enough to prove worker creation.
- The primary gap is now narrowed to the pre-worker sequence inside `wlfw_start`: mutex/cond init, `pthread_initialize_dms`, or `pthread_create@0xecf0`.
- V1705 saw no `wlfw_service_request@0xd9fc` hit, so WLFW QMI/BDF remains downstream and should not be chased yet.
- The next bounded live unit should trace `0xecd4`, `0xecd8`, `0xecf0`, `0xecf8`, and `0xeda0` under the same internal-modem firmware-serve route.

## Next Gate

- Type: source/build-only helper expansion followed by one rollbackable branch uprobe live run.
- Route: reuse V1705 internal-modem firmware-serve route only.
- Labels: `wlfw-start-dms-init-failed-before-worker`, `wlfw-start-pthread-create-not-reached`, `wlfw-start-pthread-create-failed`, `wlfw-start-pthread-create-success-worker-missing`, `wlfw-start-worker-entry-reached`, `cnss-target-unavailable`.
- Forbidden: PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.
