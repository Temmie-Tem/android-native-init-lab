# V1005 V1004 fd Gap Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v1005-v1004-fd-gap-classifier/manifest.json` | `v1005-select-service-window-mdm-helper-fd-poll-support` |

V1005 selects helper `v171` source/build work. The next native gate should add
repeated `mdm_helper` `/dev/esoc-0` fd polling inside the Android service-window
before any `/dev/subsys_esoc0` trigger is allowed.

## Evidence Checks

| Check | Result |
| --- | --- |
| Android V1000 service-window positive lower timing | PASS |
| Android V1000 `mdm_helper` holds `/dev/esoc-0` | PASS |
| Android V1000 GPIO 135/142 identity visible | PASS |
| Native V911 `mdm_helper` can hold `/dev/esoc-0` and wait in `ESOC_WAIT_FOR_REQ` | PASS |
| Native V1004 full actor set observed | PASS |
| Native V1004 fd gate stayed closed | PASS |
| Native V1004 `mdm_helper` SELinux exec domain correct | PASS |
| Native V1004 forbidden-action guard clean | PASS |

## Android Timing Baseline

V1000 Android dmesg still provides the current lower timing baseline:

| Delta | Value |
| --- | ---: |
| `mdm_helper` start → `cnss-daemon` start | `7.125ms` |
| `mdm_helper` start → `/dev/subsys_esoc0` get | `170.463ms` |
| `cnss-daemon` start → `/dev/subsys_esoc0` get | `163.338ms` |
| `/dev/subsys_esoc0` get → `wlfw_start` | `7.762ms` |
| `wlfw_start` → WLAN-PD | `1013.789ms` |
| WLAN-PD → ICNSS QMI | `2.52ms` |

The V1000 Android capture did not need BDF or `wlan0` to prove this lower path:
the important sequence is service-window actors, `/dev/subsys_esoc0` get,
`wlfw_start`, WLAN-PD, and ICNSS QMI.

## V1004 Native Gap

V1004 reached the actor set but not the fd predicate:

```text
child_started: 14
mdm_helper_pid: 701
mdm_helper_esoc0_fd_count: 0
subsys_trigger_start_attempted: 0
subsys_esoc0_open_attempted: 0
decision: v1004-mdm-helper-esoc-fd-missing-no-trigger
```

This is not evidence that `/dev/subsys_esoc0` should be opened blindly. It shows
the current predicate is too coarse: it performs one post-spawn fd scan after the
full service-window setup instead of recording whether `mdm_helper` ever opens
`/dev/esoc-0` during the critical first ~170ms window.

## Interpretation

The immediate blocker is now narrower than "Android dmesg unknown":

- Android already proves the lower timing and `mdm_helper` fd condition.
- V911 already proves native `mdm_helper` can hold `/dev/esoc-0` in a reduced
  runtime-contract path.
- V1004 proves the full repaired service-window does not expose that fd at the
  single post-spawn gate.

Therefore the next aligned change is observability, not a wider trigger:
helper `v171` should repeatedly poll `mdm_helper` fd state from immediately
after `mdm_helper` spawn through `cnss-daemon` spawn and the early service
window. Only if the fd is observed should any later live unit consider the
existing guarded `/dev/subsys_esoc0` trigger.

## Guardrails

V1005 was host-only:

- no device command;
- no Android boot or ADB command;
- no actor start;
- no `/dev/esoc-0` or `/dev/subsys_esoc0` open;
- no eSoC ioctl;
- no Wi-Fi scan/connect/link-up;
- no credential use;
- no DHCP/routes/external ping;
- no boot image, partition, firmware, GPIO, sysfs, or debugfs mutation.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v1004_fd_gap_classifier_v1005.py
python3 scripts/revalidation/native_wifi_v1004_fd_gap_classifier_v1005.py
git diff --check
```

Result:

```text
decision: v1005-select-service-window-mdm-helper-fd-poll-support
pass: True
route: source-build-helper-v171-mdm-helper-fd-poll
```

## Next

Plan V1006 as source/build-only helper `v171` support:

1. add service-window `mdm_helper` fd polling immediately after the
   `mdm_helper` child starts;
2. keep polling through `cnss-daemon` start and before the existing trigger
   decision;
3. record first-seen poll index, elapsed time, fd count, and whether the fd was
   transient or persistent;
4. keep `/dev/subsys_esoc0` trigger blocked in V1006 itself;
5. preserve no scan/connect, no credentials, no DHCP/routes, and no external
   ping.
