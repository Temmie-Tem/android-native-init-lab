# V1235 mdm_helper Post-WAIT_FOR_REQ Branch Snapshot Live Gate

- date: `2026-05-31`
- result: `PASS`
- decision: `v1235-branch-snapshot-no-exec-no-ks-mhi`
- helper: `a90_android_execns_probe v257`
- live runner: `scripts/revalidation/native_wifi_mdm_helper_post_wait_req_branch_snapshot_live_v1235.py`
- evidence: `tmp/wifi/v1235-mdm-helper-post-wait-req-branch-snapshot-live/manifest.json`

## Purpose

V1232 proved `mdm_helper` leaves `ESOC_WAIT_FOR_REQ`, but no `ks` or MHI pipe
appears afterward. V1235 used the V1233 branch snapshot to inspect the immediate
post-return window without ptrace and without widening into Wi-Fi HAL or network
bring-up.

## Result

| Field | Value |
|---|---|
| `post_wait_req.transition_detected` | `1` |
| `post_wait_req.transition_sample` | `4` |
| `post_wait_req.ks_process_count` | `0` |
| `post_wait_req.mhi_pipe_exists` | `0` |
| `post_wait_req.mhi_pipe_fd_count` | `0` |
| branch emitted | `true` |
| branch phases | `36` |
| branch burst samples | `20` |
| branch `execve`/`execveat` count | `0` |
| branch `ioctl` count | `4` |
| branch dominant syscall | `nanosleep` (`68`) |
| branch dominant wchan | `SyS_nanosleep` (`68`) |
| max `/dev/esoc-0` fd count | `1` |
| max MHI pipe fd count | `0` |

The private transcript also shows the subsystem trigger child blocked in
`mdm_subsys_powerup`, while `mdm_helper` held `/dev/esoc-0` and remained in
`SyS_nanosleep`. No GPIO142, PCIe, MHI, `ks`, WLFW, BDF, or `wlan0` progress was
observed during the bounded window.

## Interpretation

V1235 closes the hypothesis that `mdm_helper` itself directly launches Android's
`ks` image-link path after `ESOC_WAIT_FOR_REQ` returns. In this native path it
returns to sleep and does not issue an `execve`/`execveat`; no MHI pipe appears.

The remaining blocker is no longer just the `mdm_helper` wait boundary. The next
useful classification is the Android runtime contract that causes `ks`/MHI image
linking or equivalent MDM3 power-up progress: likely service/property/env/init
context around `pm-service`/peripheral-manager rather than a direct
`mdm_helper` post-return exec branch.

## Safety

No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot
image write, or partition write occurred. Postflight selftest remained clean:
`pass=11 warn=1 fail=0`; netservice remained disabled/stopped.

## Next Gate

V1236 should classify the Android `ks` launch/runtime contract host-only first,
then choose the smallest live gate. Candidate inputs:

- Android `ks` parent/cmdline/SELinux context from existing Magisk/Android evidence.
- `pm-service`/peripheral-manager properties and binder request path that differ from the native path.
- Native evidence that direct subsystem child reaches `mdm_subsys_powerup` but no MHI/PCIe/GPIO142 progress follows.
