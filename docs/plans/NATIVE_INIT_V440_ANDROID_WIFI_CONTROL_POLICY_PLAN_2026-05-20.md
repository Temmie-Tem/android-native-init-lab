# Native Init V440 Android Wi-Fi Control Policy Plan

Date: 2026-05-20

## Goal

V440 consumes V439 post-reenable evidence and chooses the next safe Wi-Fi
operating policy.  It is host-side only and does not touch the device.

V439 proved two facts:

- Android-managed Wi-Fi can auto-connect and expose `wlan0`
  route/DNS/connectivity after the framework setting is enabled.
- Cleanup disable can remove active route/DNS/connectivity exposure again.

V440 converts those facts into an explicit policy before any server exposure,
credential work, or explicit scan/connect gate.

## Scope

Allowed:

- load the latest or explicit V439 manifest;
- verify exposure, listener, cleanup, and rollback markers;
- select the next operating policy and blocked actions.

Not allowed:

- device commands or device mutations;
- Wi-Fi enable/disable;
- scan/connect, credentials, server exposure, routing mutation, or external
  packet probes.

## Implementation

- Selector: `scripts/revalidation/wifi_android_control_policy_v440.py`
  - finds the latest V439 live manifest by default;
  - checks `exposure_seen`, `listener_safe`, and `cleanup_contained`;
  - selects `contained-lab-default` when Android-managed Wi-Fi is functional,
    externally routed, and cleanup containment is proven.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_android_control_policy_v440.py

python3 scripts/revalidation/wifi_android_control_policy_v440.py \
  --out-dir tmp/wifi/v440-android-wifi-control-policy-plan-<ts> plan

python3 scripts/revalidation/wifi_android_control_policy_v440.py \
  --out-dir tmp/wifi/v440-android-wifi-control-policy-hostrun-<ts> run

git diff --check
```

## Expected Decisions

- `v440-android-wifi-policy-plan-ready`
- `v440-android-wifi-policy-contained-lab-default-pass`
- `v440-android-wifi-policy-cleanup-required`
- `v440-android-wifi-policy-extended-observation-pass`
- `v440-android-wifi-policy-reenable-needed-pass`
- `v440-android-wifi-policy-missing-v439`
- `v440-android-wifi-policy-v439-failed`

Any PASS decision must keep `device_commands_executed=False`,
`device_mutations=False`, and `wifi_bringup_executed=False`.

## Policy Default

If V439 proves auto-connect exposure plus cleanup containment, V440 should
select:

```text
contained-lab-default
```

Rules:

- default lab state is Wi-Fi disabled unless a bounded Wi-Fi test is active;
- Android-managed Wi-Fi may run only inside explicit exposure-aware test
  windows;
- cleanup disable should run after Android Wi-Fi exposure tests unless the next
  step explicitly requires continuous Wi-Fi;
- server exposure remains blocked until binding, ACL, authentication, and
  listener policy are explicit;
- explicit scan/connect remains blocked until credential handling and target
  network allowlisting are documented.

## Next Gate Rule

V441 should be chosen from one of two safe directions:

- exposure-aware read-only Wi-Fi stability observation; or
- explicit scan/connect credential and target allowlist design.

Serverization remains blocked.
