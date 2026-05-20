# Native Init V442 Wi-Fi Target Policy Report

Date: 2026-05-20

## Summary

V442 added a host-side Wi-Fi target and credential policy gate.  The host-run
passed with:

```text
decision: v442-wifi-target-policy-template-pass
pass: True
reason: V441 is ready; generated secret-free target policy template, but no private target policy was provided
wifi_bringup_executed: False
```

V442 did not execute any device command.  It consumed V441 evidence, generated a
secret-free target policy template, and confirmed that explicit scan/connect
must not proceed until a private untracked policy validates.

## Implementation

- `scripts/revalidation/wifi_android_target_policy_v442.py`
  - loads latest or explicit V441 manifest;
  - validates secret-free target policy JSON;
  - rejects raw SSID/BSSID/password/passphrase/PSK-like fields;
  - rejects placeholder `ssid_sha256`;
  - outputs a command template with env placeholders, not real values.
- `docs/operations/WIFI_TARGET_ALLOWLIST_V442.example.json`
  - provides a copyable structure for private local policy files;
  - intentionally contains a placeholder hash and is not live-ready.

## External References

- AOSP Android 13 `WifiShellCommand` documents `connect-network` parameters and
  the relevant flags: https://android.googlesource.com/platform/packages/modules/Wifi/+/refs/heads/android13-release/service/java/com/android/server/wifi/WifiShellCommand.java
- AOSP Wi-Fi network selection describes Android scan-result and saved-network
  selection behavior: https://source.android.com/docs/core/connect/wifi-network-selection
- Android Developers notes that accepted saved network configuration can trigger
  connection: https://developer.android.com/develop/connectivity/wifi/wifi-save-network-passpoint-config

## Static Validation

```text
python3 -m py_compile scripts/revalidation/wifi_android_target_policy_v442.py

git diff --check
```

Both checks passed.

Plan and host-run evidence:

```text
tmp/wifi/v442-android-wifi-target-policy-plan-20260520-174415/
tmp/wifi/v442-android-wifi-target-policy-hostrun-20260520-174415/
```

## Input Evidence

V442 used the latest V441 evidence:

```text
tmp/wifi/v441-android-wifi-exposure-stability-live-20260520-172446/manifest.json
decision: v441-android-wifi-exposure-stability-cleanup-pass
pass: True
```

Required V441 markers were present:

| Item | Value |
| --- | --- |
| `stable_all_samples` | `True` |
| `cleanup_contained` | `True` |
| `listener_safe` | `True` |
| `wifi_enable_executed` | `True` |
| `wifi_disable_executed` | `True` |
| `wifi_bringup_executed` | `True` |

## Policy Result

No private target policy was provided, so V442 produced:

```text
decision: v442-wifi-target-policy-template-pass
next_gate: create a private untracked V442 policy file before V443 explicit scan/connect preflight
```

Template evidence:

```text
tmp/wifi/v442-android-wifi-target-policy-hostrun-20260520-174415/target-policy.template.json
```

The tracked example policy was also validated and correctly rejected:

```text
tmp/wifi/v442-android-wifi-target-policy-example-reject-20260520-174432/
decision: v442-wifi-target-policy-review-required
issue: targets[0]: ssid_sha256 must be a real 64-char lowercase sha256, not a placeholder
```

## Contract For V443

V443 explicit scan/connect preflight may proceed only after a private policy
validates as `v442-wifi-target-policy-allowlist-ready`.

Minimum contract:

- read SSID from `A90_WIFI_SSID` and verify `sha256` before use;
- read PSK from `A90_WIFI_PSK` only for `wpa2`/`wpa3`;
- never write raw SSID, BSSID, password, passphrase, PSK, or target config key
  to evidence;
- use `cmd wifi connect-network` with autojoin disabled;
- cleanup by forgetting the network and disabling Wi-Fi;
- restore native v319;
- keep server exposure blocked.

## Interpretation

V442 closes the policy gap between “Wi-Fi is stable” and “it is safe to issue an
explicit scan/connect command.”  The next blocker is operator-provided private
target metadata, not code capability.

## Next

Recommended next cycle: V443 private-policy validation plus explicit
scan/connect preflight.

Do not run explicit scan/connect until a private untracked V442 policy is
available and validates.
