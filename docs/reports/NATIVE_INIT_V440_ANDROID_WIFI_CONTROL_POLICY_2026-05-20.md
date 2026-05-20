# Native Init V440 Android Wi-Fi Control Policy Report

Date: 2026-05-20

## Summary

V440 added a host-side Android Wi-Fi control policy selector.  The host-run
passed with:

```text
decision: v440-android-wifi-policy-contained-lab-default-pass
pass: True
policy: contained-lab-default
reason: Android-managed Wi-Fi is functional and externally routed, while cleanup containment is proven
wifi_bringup_executed: False
```

V440 did not execute any device command.  It consumed V439 evidence and selected
a conservative default: keep Wi-Fi disabled in lab mode unless a bounded Wi-Fi
test explicitly needs Android-managed Wi-Fi.

## Implementation

- `scripts/revalidation/wifi_android_control_policy_v440.py`
  - loads the latest or explicit V439 manifest;
  - checks sample exposure, listener safety, and cleanup containment;
  - selects the Wi-Fi operating policy and blocked actions.

## Static Validation

```text
python3 -m py_compile scripts/revalidation/wifi_android_control_policy_v440.py

git diff --check
```

Both checks passed.

Plan and host-run evidence:

```text
tmp/wifi/v440-android-wifi-control-policy-plan-20260520-171835/
tmp/wifi/v440-android-wifi-control-policy-hostrun-20260520-171835/
```

## Input Evidence

V440 used the latest V439 live evidence:

```text
tmp/wifi/v439-android-wifi-post-reenable-handoff-live-20260520-170736/manifest.json
decision: v439-android-wifi-post-reenable-exposure-observed-cleanup-pass
pass: True
```

Evidence markers:

| Item | Value |
| --- | --- |
| `sample_count` | `7` |
| `enabled_seen` | `True` |
| `wifi_connected_seen` | `True` |
| `exposure_seen` | `True` |
| `first_exposure_phase` | `sample-000` |
| `listener_safe` | `True` |
| `cleanup_requested` | `True` |
| `cleanup_ok` | `True` |
| `cleanup_contained` | `True` |
| `wifi_disable_executed` | `True` |
| `wifi_bringup_executed` | `False` |

## Decision

Selected policy:

```text
contained-lab-default
```

Policy rules:

- default lab state is Wi-Fi disabled unless a bounded Wi-Fi test is active;
- Android-managed Wi-Fi may run only inside explicit exposure-aware test
  windows;
- cleanup disable must run after Android Wi-Fi exposure tests unless the next
  step needs continuous Wi-Fi;
- server exposure remains blocked until binding, ACL, authentication, and
  listener policy are explicit;
- explicit scan/connect remains blocked until credential handling and target
  network allowlisting are documented.

## Interpretation

Android-managed Wi-Fi is now proven functional, but it creates external network
exposure automatically through saved auto-connect.  The correct default is not
to leave Wi-Fi on casually.  Future Wi-Fi work should either be bounded
read-only exposure-aware observation or a carefully designed explicit
scan/connect gate.

## Next

Recommended next cycle: V441 planning.

Reasonable V441 candidates:

- exposure-aware Android Wi-Fi stability observation with cleanup; or
- credential/target allowlist design for explicit scan/connect.

Server exposure remains blocked.
