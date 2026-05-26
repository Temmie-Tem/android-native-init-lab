# V1017 V1016 Android Lower Gap Classifier

- date: `2026-05-26`
- scope: host-only route classifier
- decision: `v1017-select-after-fd-upper-surface-subsys-window`
- pass: `True`
- evidence: `tmp/wifi/v1017-v1016-android-lower-gap-classifier/manifest.json`

## Summary

V1017 classifies the V1016 result as a circular WLFW gate candidate.

V1016 already has fd-positive lower state and upper userspace surface parity,
but the helper only opens `/dev/subsys_esoc0` after WLFW precondition. Android
evidence shows `/dev/subsys_esoc0` get occurs in the same narrow window as
`cnss-daemon wlfw_start`, and V968 preserves a full Android-positive
WLFW/BDF/FW-ready/`wlan0` chain.

Therefore the next unit should not be Magisk sampling first. The next unit
should add a bounded helper path that opens `/dev/subsys_esoc0` after
fd-positive upper-surface parity, with strict timeout and cleanup reboot.

## Key Evidence

| Item | Value |
| --- | --- |
| V1016 decision | `v1016-upper-surface-started-wlfw-missing-no-open` |
| V1016 fd predicate | `mdm_helper_esoc0_fd_seen=1` |
| V1016 upper actors | service-manager, Wi-Fi HAL legacy/ext, `wificond`, CNSS started |
| V1016 WLFW | missing |
| V1016 `/dev/subsys_esoc0` | not opened |
| V1000 `/dev/subsys_esoc0` get → `wlfw_start` | `7.762ms` |
| V968 `wlfw_start` → `/dev/subsys_esoc0` get | `52.646ms` |
| V968 positive chain | WLFW, BDF, FW-ready, `wlan0` present |

## Checks

All required V1017 checks passed:

- V1016 input present
- V1016 upper surface started
- V1016 `mdm_helper` fd-positive state proven
- V1016 WLFW missing and `/dev/subsys_esoc0` not opened
- V1016 guardrails clean
- Android V1000 WLFW chain present
- Android V1000 service-window chain present
- Android `/dev/subsys_esoc0` get near WLFW
- Android V968 full positive chain present
- GPIO transition gap is secondary
- V1016 report interpretation matches the machine evidence

The optional V1000 full-positive chain is missing because that capture was a
short no-scan/no-connect window. V968 supplies the full Android-positive
WLFW/BDF/FW-ready/`wlan0` chain.

## Selected Route

Proceed to V1018:

```text
helper v173 source/build support
after-mdm-helper-esoc-fd-with-wifi-surface-subsys-window
```

The V1018/V1019/V1020 sequence should be:

1. add helper `v173` support for the new order
2. deploy helper `v173`
3. run a bounded live gate that:
   - starts the same fd-positive upper-surface stack as V1016
   - opens `/dev/subsys_esoc0` only after that stack is up
   - captures WLFW/BDF/`wlan0` or D-state blocker evidence
   - performs cleanup reboot if a holder blocks

## Guardrails

Still forbidden:

- raw eSoC controller ioctl path
- GPIO/sysfs/debugfs write
- `IWifi.start`
- `qcwlanstate` write
- scan/connect/link-up
- credential use
- DHCP/route/external ping
- boot image or firmware mutation

Magisk early sampling is deferred until the scoped subsystem window still fails
and exact GPIO transition timing becomes necessary.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v1016_android_lower_gap_classifier_v1017.py
python3 scripts/revalidation/native_wifi_v1016_android_lower_gap_classifier_v1017.py
```

Result:

```text
decision: v1017-select-after-fd-upper-surface-subsys-window
pass: True
next: V1018 helper v173 source/build support for after-fd upper-surface scoped /dev/subsys_esoc0 window
```
