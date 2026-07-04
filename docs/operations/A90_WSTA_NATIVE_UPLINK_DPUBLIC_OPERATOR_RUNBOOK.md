# A90 WSTA Native-Uplink D-Public Operator Runbook

This runbook is the operator path for the proven WSTA45 profile publish flow:

```text
WSTA45 operator wrapper
  -> WSTA43 orchestrator
  -> WSTA28 native warm reboot + scan-green precondition
  -> WSTA42 native-owned STA uplink + Debian D-public quick Tunnel
  -> WSTA48 redacted result aggregate
```

It is not a flash procedure.  It does not make public exposure persistent.  Public
exposure remains bounded to the explicit WSTA45/WSTA43/WSTA42 live gate and must be
cleaned up by the runner before the run is considered complete.

## Preconditions

Run from the repository root:

```text
cd /home/temmie/dev/A90_5G_rooting
```

Check the bridge and current resident before any live publish:

```text
python3 workspace/public/src/scripts/revalidation/a90_bridge.py status --json
python3 workspace/public/src/scripts/revalidation/a90ctl.py version
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest
```

Stop before publish if the bridge is unhealthy, the device is not on the expected
native Wi-Fi uplink-capable resident, or `selftest` reports a new failure.

## Host-Only Preflight

Validate the operator/profile surface without touching the device:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py \
  --run-dir workspace/private/runs/server-distro/wsta45-operator-preflight \
  --print-full-json
```

Expected result:

```text
decision=wsta45-appliance-operator-preflight-pass
native_reboot=false
wifi_connect=false
public_tunnel=false
profile_contract_ok=true
```

## Print The Publish Template

Print the redacted command skeleton:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py \
  --print-publish-template
```

The output must contain `<native-confirm-token>` and `<public-confirm-token>` placeholders,
not token values.  Fill those placeholders only at execution time from an
operator-approved private source.  Do not commit the filled command or paste token values
into reports.

## Live Publish

Choose a private run directory:

```text
RUN_DIR="workspace/private/runs/server-distro/wsta45-profile-publish-<utc-run-id>"
```

Run the WSTA45 publish gate with every live/public acknowledgement explicit:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py \
  --mode publish \
  --run-dir "${RUN_DIR}" \
  --use-native-uplink-profile \
  --allow-operator-live \
  --allow-native-reboot \
  --allow-public-live \
  --ack-credentialed-wifi \
  --ack-public-exposure \
  --native-confirm-token "<native-confirm-token>" \
  --public-confirm-token "<public-confirm-token>"
```

Optional WSTA43 tuning arguments may follow a literal `--`, but WSTA45 blocks gate flags
from passthrough.  Supply all live/public gate flags at the WSTA45 layer.

## Redacted Result Aggregate

After the live runner exits, summarize the private run without exposing URL or credential
material:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta48_redacted_result_aggregate.py \
  --input "${RUN_DIR}" \
  --output "${RUN_DIR}/wsta48_result.json" \
  > "${RUN_DIR}/wsta48_summary.json"
```

Expected aggregate conditions:

```text
redaction_guard.ok=true
all_pass=true
decisions include wsta45-appliance-operator-wsta43-profile-pass
decisions include wsta43-orchestrated-native-uplink-dpublic-pass
decisions include wsta42-native-uplink-dpublic-tunnel-pass
```

The aggregate output belongs under `workspace/private/runs/` unless a report copies only
redacted counts/decisions.

## Post-Run Health

Run independent post-checks:

```text
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest
python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status
```

Expected post-run state:

```text
selftest fail=0
wifi status reports no active public tunnel process
wifi status reports autoconnect disabled unless a later operator step explicitly re-enables it
```

## Stop Conditions

Stop and do not retry-loop if any of these happen:

- WSTA45 does not return `wsta45-appliance-operator-wsta43-profile-pass`.
- WSTA43 or WSTA42 returns a blocked decision.
- WSTA42 cleanup does not report D-public cleanup, profile cleanup, helper cleanup, and
  chroot cleanup as clean.
- WSTA48 `redaction_guard.ok` is false.
- Independent post-run `selftest` regresses.
- The bridge becomes unreachable after the native warm reboot.

Do not commit private run JSON, raw tunnel URLs, credential material, token values, raw
SSID/BSSID/IP/DNS/gateway values, or private aggregate files.

## Non-Goals

- No `native_init_flash.py` invocation belongs in this WSTA45 publish path.
- No raw partition write belongs here.
- No always-on public exposure is authorized by this runbook.
- No Wi-Fi credential value should appear in shell history, committed files, reports, or
  copied aggregate output.
