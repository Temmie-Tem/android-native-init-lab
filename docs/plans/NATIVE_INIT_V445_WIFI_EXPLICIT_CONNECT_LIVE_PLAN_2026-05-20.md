# Native Init V445 Wi-Fi Explicit Connect Live Plan

Date: 2026-05-20

## Goal

V445 is the bounded live runner for explicit Android Wi-Fi scan/connect.  It is
allowed to run only after V444 preflight proves that a private target policy and
matching env values are ready.

The runner is intentionally fail-closed:

```text
V444 preflight must pass before Android boot/flash starts.
```

## Scope

Allowed after V444-ready:

- boot Android through the existing handoff path;
- enable Android Wi-Fi;
- start scan;
- capture scan results only in redacted/count form;
- connect with `cmd wifi connect-network` using env-derived values;
- observe Wi-Fi status, route, DNS, connectivity, and listener surfaces;
- cleanup by forgetting the resolved network and disabling Wi-Fi;
- restore native v319.

Not allowed:

- raw SSID/BSSID/password/passphrase/PSK in evidence;
- server exposure;
- external packet probes;
- live execution without V444-ready preflight;
- leaving Android Wi-Fi enabled after the test.

## Implementation

- Runner: `scripts/revalidation/wifi_android_explicit_connect_live_v445.py`
  - `plan`: records the full handoff plan without mutation;
  - `dry-run`: executes nested dry-runs without device mutation;
  - `run`: executes V444 preflight first and refuses to boot Android if it fails;
  - `collect`: internal Android-booted collector for the live scan/connect phase.

The collector:

- loads the private V442/V443 policy;
- validates env values through V444/V442 logic;
- writes command displays using env placeholders;
- redacts scan results and saved network lists;
- uses resolved network id only for cleanup;
- verifies cleanup containment.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_android_explicit_connect_live_v445.py

python3 scripts/revalidation/wifi_android_explicit_connect_live_v445.py \
  --out-dir tmp/wifi/v445-explicit-connect-live-plan-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  --allow-read-wifi-env --i-understand-wifi-secret-env \
  --allow-explicit-scan-connect --i-understand-explicit-wifi-connect \
  plan

python3 scripts/revalidation/wifi_android_explicit_connect_live_v445.py \
  --out-dir tmp/wifi/v445-explicit-connect-live-dryrun-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  --allow-read-wifi-env --i-understand-wifi-secret-env \
  --allow-explicit-scan-connect --i-understand-explicit-wifi-connect \
  dry-run

python3 scripts/revalidation/wifi_android_explicit_connect_live_v445.py \
  --out-dir tmp/wifi/v445-explicit-connect-live-missing-policy-fixed-<ts> \
  --allow-android-boot-flash --assume-yes --i-understand-native-rollback \
  --allow-read-wifi-env --i-understand-wifi-secret-env \
  --allow-explicit-scan-connect --i-understand-explicit-wifi-connect \
  run

git diff --check
```

Without real private policy/env values, `run` must fail as
`v445-handoff-preflight-blocked` with no device commands and no device
mutations.

## Expected Decisions

- `v445-handoff-plan-ready`
- `v445-handoff-dryrun-ready`
- `v445-handoff-preflight-blocked`
- `v445-explicit-connect-cleanup-pass`
- `v445-explicit-connect-no-connection`
- `v445-explicit-connect-cleanup-forget-failed`
- `v445-explicit-connect-cleanup-not-contained`

## Pass Criteria For Live

A live PASS must prove:

- V444 preflight passed before Android boot/flash;
- Android boot-complete passed;
- explicit scan/connect produced connected/IP/validated evidence;
- scan results and saved network lists were redacted;
- resolved network cleanup forget passed;
- cleanup disable removed active Wi-Fi exposure;
- native v319 rollback completed.

## Next Gate Rule

V445 live execution remains blocked until:

```text
V443 materialized private policy PASS
V444 explicit connect preflight READY
```

After V445 live PASS, the next branch should be V446 explicit connect stability
or server binding policy.  Server exposure remains blocked until binding, ACL,
authentication, and listener policy are explicit.
