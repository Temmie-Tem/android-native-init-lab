# Native Init V446 Wi-Fi Private Secret Guard Plan

Date: 2026-05-20

## Goal

V446 adds a repository-side safety gate before the private Wi-Fi credential
flow.  V443/V444/V445 already avoid writing raw network identifiers and
credentials to evidence, but the remaining operational risk is accidental
tracking of local policy, env, or copied Android status output.

## Scope

Allowed:

- add ignore rules for local Wi-Fi policy/env material;
- scan tracked files and optionally untracked repository-visible files;
- report only file, line, rule, and sanitized detail;
- run before V443 materialization, V444 preflight, and V445 live execution.

Not allowed:

- read ignored `tmp/` evidence or shell history;
- print raw SSID, BSSID, passphrase, PSK, or target config values;
- execute device commands;
- enable Wi-Fi, scan, connect, or expose a server.

## Implementation

- `.gitignore`
  - ignores local env files and private/local Wi-Fi target policies;
  - keeps example env files trackable.
- `scripts/revalidation/wifi_private_secret_guard_v446.py`
  - verifies required ignore patterns;
  - scans `git ls-files`;
  - optionally scans `git ls-files --others --exclude-standard`;
  - detects repository-visible private policy/env paths;
  - detects non-placeholder Wi-Fi env assignments, raw connect commands, raw
    connected-SSID status lines, Wi-Fi-adjacent MAC values, and forbidden
    raw JSON policy fields;
  - writes private evidence and never emits secret values in findings.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_private_secret_guard_v446.py

python3 scripts/revalidation/wifi_private_secret_guard_v446.py \
  --out-dir tmp/wifi/v446-wifi-private-secret-guard-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_private_secret_guard_v446.py \
  --out-dir tmp/wifi/v446-wifi-private-secret-guard-run-<ts> \
  --include-untracked \
  run

git diff --check
```

Negative validation should create a temporary untracked probe with synthetic
non-placeholder Wi-Fi values, confirm `v446-wifi-private-secret-guard-findings`,
then remove the probe and rerun the clean scan.

## Expected Decisions

- `v446-wifi-private-secret-guard-plan-ready`
- `v446-wifi-private-secret-guard-pass`
- `v446-wifi-private-secret-guard-findings`
- `v446-wifi-private-secret-guard-scan-error`

## Pass Criteria

V446 passes only when:

- required ignore patterns are present;
- no repository-visible private policy/env files are detected;
- no raw Wi-Fi credential or target identifiers are detected in tracked or
  included-untracked files;
- findings do not print secret values;
- no device command or Wi-Fi bring-up occurs.

## Next Gate

After V446 passes, the operator can set private local env values, run V443 to
materialize an ignored private policy, run V444 preflight, then run V445 live.

Server exposure remains blocked.
