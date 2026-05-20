# Native Init V442 Wi-Fi Target Policy Plan

Date: 2026-05-20

## Goal

V442 turns the V441 Android-managed Wi-Fi stability proof into a safe preflight
contract for future explicit scan/connect work.

V441 proved that Android-managed Wi-Fi can stay connected and externally routed
for a bounded window, and that cleanup disable restores containment.  The next
risk boundary is not basic Wi-Fi availability; it is target selection and
credential handling.

## External Reference Basis

- AOSP Android 13 `WifiShellCommand` documents `cmd wifi connect-network
  <ssid> open|owe|wpa2|wpa3 [<passphrase>]` and flags such as `-d`, `-p`,
  `-b`, and `-r`.
- AOSP Wi-Fi network selection explains that Android evaluates scan results and
  saved configurations to select/connect networks.
- Android Developers documentation notes that adding/saving network
  configurations can trigger connection to saved networks.

References:

- https://android.googlesource.com/platform/packages/modules/Wifi/+/refs/heads/android13-release/service/java/com/android/server/wifi/WifiShellCommand.java
- https://source.android.com/docs/core/connect/wifi-network-selection
- https://developer.android.com/develop/connectivity/wifi/wifi-save-network-passpoint-config

## Scope

Allowed:

- load V441 live evidence;
- validate a secret-free target policy file;
- generate a private evidence template for the operator;
- reject placeholder/raw-secret policies.

Not allowed:

- device commands or device mutations;
- raw SSID, BSSID, password, passphrase, PSK, or target config key in tracked
  files/evidence;
- server exposure or external packet probes;
- explicit scan/connect without a private allowlist.

## Policy Contract

Tracked files may contain only:

- target id;
- `ssid_source=env:A90_WIFI_SSID`;
- `ssid_sha256`;
- `security=open|owe|wpa2|wpa3`;
- `credential_source=env:A90_WIFI_PSK` only for `wpa2`/`wpa3`;
- cleanup and command policy flags.

Tracked files must not contain:

- raw SSID;
- raw BSSID/MAC;
- raw password/passphrase/PSK;
- Android `targetConfigKey`.

## Implementation

- Validator: `scripts/revalidation/wifi_android_target_policy_v442.py`
  - consumes latest or explicit V441 manifest;
  - validates optional policy JSON;
  - emits a secret-free template into private evidence;
  - rejects placeholder target hashes and raw-secret fields.
- Example template: `docs/operations/WIFI_TARGET_ALLOWLIST_V442.example.json`
  - intentionally uses a placeholder hash;
  - must be copied to a private untracked path and filled with real hashes/env
    references before V443.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_android_target_policy_v442.py

python3 scripts/revalidation/wifi_android_target_policy_v442.py \
  --out-dir tmp/wifi/v442-android-wifi-target-policy-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_android_target_policy_v442.py \
  --out-dir tmp/wifi/v442-android-wifi-target-policy-hostrun-<ts> \
  run

python3 scripts/revalidation/wifi_android_target_policy_v442.py \
  --out-dir tmp/wifi/v442-android-wifi-target-policy-example-reject-<ts> \
  --policy docs/operations/WIFI_TARGET_ALLOWLIST_V442.example.json \
  run

git diff --check
```

The example-policy validation is expected to fail because the placeholder hash
is not live-ready.

## Expected Decisions

- `v442-wifi-target-policy-plan-ready`
- `v442-wifi-target-policy-template-pass`
- `v442-wifi-target-policy-allowlist-ready`
- `v442-wifi-target-policy-review-required`
- `v442-wifi-target-policy-missing-v441`
- `v442-wifi-target-policy-v441-not-ready`

## Next Gate Rule

V443 may be explicit scan/connect preflight only after a private untracked V442
policy validates as `v442-wifi-target-policy-allowlist-ready`.

V443 must still keep server exposure blocked and must never write raw
credentials or raw network identifiers to evidence.
