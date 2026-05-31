# V1237 Late per_proxy Branch Snapshot Live Gate

- report: `docs/reports/NATIVE_INIT_V1237_LATE_PER_PROXY_BRANCH_SNAPSHOT_LIVE_2026-05-31.md`
- live runner: `scripts/revalidation/native_wifi_late_per_proxy_branch_snapshot_live_v1237.py`
- evidence: `tmp/wifi/v1237-late-per-proxy-branch-snapshot-live/manifest.json`

- decision: `v1237-direct-subsys-trigger-preempted-late-per-proxy`
- pass: `True`
- reason: late `per_proxy` was requested, but the direct `/dev/subsys_esoc0` post-wait trigger path completed first and the helper never reached the late `per_proxy` block.
- next_step: split V1238 into a late-`per_proxy`-only path without the direct subsystem trigger, or add helper support for late-`per_proxy` post-wait snapshots.

## Result

| field | value |
| --- | --- |
| helper | `a90_android_execns_probe v257` |
| helper sha256 | `66c3bc5a9cc0daa9a9a04fe7b98ebe2d7aa974798ed131adf82e5b314b2753e5` |
| post_wait emitted | `true` |
| post_wait sample count | `84` |
| transition detected | `1` |
| transition sample | `4` |
| branch emitted | `true` |
| branch phase count | `36` |
| branch `execve`/`execveat` count | `0` |
| branch `ioctl` count | `4` |
| dominant syscall | `nanosleep` (`67`) |
| dominant wchan | `SyS_nanosleep` (`67`) |
| `ks` process count | `0` |
| MHI pipe exists | `0` |
| MHI pipe fd count | `0` |
| late `per_proxy` requested | `1` |
| late `per_proxy` begin | `false` |
| direct path completed before late block | `true` |

## Interpretation

V1237 confirms that the live command injection was correct: the helper received
the late `per_proxy` request and the post-wait branch observer flags. The run
did not prove the late `per_proxy` actor path, because the V1235-derived direct
`/dev/subsys_esoc0` trigger remained in the same command. That direct trigger
entered the post-wait path first and the helper finished the branch snapshot
without reaching `pm_service_trigger_observer.late_per_proxy.begin=1`.

The evidence is therefore a useful ordering result, not a Wi-Fi progress result:
combining the direct subsystem trigger with late `per_proxy` masks the actor path
that V1236 identified as the Android-positive contract.

## Safety

No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot
image write, or partition write occurred. The run stayed within the bounded
PM/CNSS/mdm_helper observer scope and reused helper `v257`.

## V1238 Gate

V1238 should remove `--pm-observer-open-subsys-esoc0-after-mdm-helper-esoc` and
run a late-`per_proxy`-only live gate after `mdm_helper` holds `/dev/esoc-0`.
The observer should capture whether `pm-service` reaches `/dev/subsys_esoc0`,
whether `ks` and `/dev/mhi_0305_01.01.00_pipe_10` appear, and whether GPIO142,
PCIe RC1, WLFW service 69, BDF, or `wlan0` progress follows. Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, external ping, flash, boot image writes,
and partition writes remain blocked.
