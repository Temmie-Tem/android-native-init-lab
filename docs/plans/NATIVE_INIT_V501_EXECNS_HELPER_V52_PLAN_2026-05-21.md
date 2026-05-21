# Native Init V501 Execns Helper v52 Plan

Date: 2026-05-21

## Goal

V501 adds the helper-side contract for the eventual native-init
connect/DHCP/external-ping path.

It is intentionally not the final live Wi-Fi connection implementation. The new
mode exposes the approval surface, private config path validation, tool
readiness checks, and redacted evidence keys that V500/V53 will build on.

## Helper v52

Artifact:

```text
tmp/wifi/v501-a90_android_execns_probe-v52/a90_android_execns_probe
```

SHA256:

```text
2a3b83f852e17f93cf82a9617f396457718024f28ac510fb915848e3e3547a7d
```

New helper mode:

```text
--mode wifi-active-session-connect-ping
```

New required live arguments:

```text
--allow-connect-dhcp-ping
--connect-config /cache/a90-wifi/<private-file>
--connect-iface auto|wlan0
--ping-target <IPv4 literal>
```

## Current Behavior

The v52 mode is a scaffold:

- validates that `--connect-config` is under `/cache/a90-wifi`;
- refuses symlink/non-regular config files;
- checks that the private config mode is not group/other-readable;
- reports supplicant, DHCP client, `ip`, and `ping` tool readiness;
- emits `wifi_connect_ping.executor_implemented=0`;
- does not start `wpa_supplicant`;
- does not run DHCP;
- does not send external packets.

This keeps V500 fail-closed while making the helper contract concrete.

## Deploy Wrapper

New wrapper:

```text
scripts/revalidation/wifi_execns_helper_v52_deploy_preflight.py
```

Exact deploy approval phrase:

```text
approve v501 deploy execns helper v52 only; no live connect and no Wi-Fi bring-up
```

Deploying v52 only replaces `/cache/bin/a90_android_execns_probe`. It must not
run the new connect mode.

## Next Version

V502/V53 should implement the live executor body:

1. materialize a private supplicant config inside the helper namespace;
2. start bounded `wpa_supplicant`;
3. wait for association on the selected WLAN interface;
4. run the selected DHCP client;
5. run interface-bound external ping;
6. cleanup supplicant, DHCP state, temporary secrets, addresses/routes, and
   helper-owned children.

## Validation

```text
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v501-a90_android_execns_probe-v52/a90_android_execns_probe

python3 -m py_compile \
  scripts/revalidation/native_wifi_connect_ping_v499.py \
  scripts/revalidation/native_wifi_connect_ping_v500.py \
  scripts/revalidation/wifi_execns_helper_v52_deploy_preflight.py

python3 scripts/revalidation/wifi_execns_helper_v52_deploy_preflight.py \
  --out-dir tmp/wifi/v501-execns-helper-v52-plan-<ts> \
  plan

python3 scripts/revalidation/native_wifi_connect_ping_v500.py \
  --out-dir tmp/wifi/v500-native-connect-ping-preflight-<ts> \
  preflight

python3 scripts/revalidation/wifi_private_secret_guard_v446.py --include-untracked run
git diff --check
```
