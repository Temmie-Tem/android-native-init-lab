# A90 WSTA Native-Uplink D-Public Operator Runbook

> **종료된 에픽의 운영 문서 · 권한 없음**
>
> 이 문서는 A90 server-distro / WSTA 에픽에 속합니다. 해당 에픽은
> **2026-07-05에 종료 선언**됐고, `GOAL_A90.md`는 WSTA를 "retired experiment"로,
> `A90_TARGET_CONTRACT.md`는 남은 WSTA 스냅샷을 정리 대상 obsolete 파일로
> 다룹니다.
>
> 본문은 현행 계약 계층(`AGENTS.md`, target contract,
> `DEVICE_ACTION_RISK_TIERS.md`, `DEVICE_ACTION_PROCESS_V2.md`)을 참조하지
> **않으며**, 여기 적힌 절차는 D0/D1/F1 위험 등급 판정을 대신하지 않습니다.
> 기기 작업 권한은 `AGENTS.md`와 선택된 binding target contract에서만
> 나옵니다.
>
> 과거 실행 기록으로 보존하며 본문은 수정하지 않습니다.


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

## Persistent Workflow Status

For the lease-bound WSTA88 workflow, generate a default-off preflight and compact server
status bundle before any attended live run:

```text
WSTA88_RUN="workspace/private/runs/server-distro/wsta88-persistent-operator-<utc-run-id>"
WSTA108_RUN="workspace/private/runs/server-distro/wsta108-server-status-<utc-run-id>"

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta88_persistent_operator_workflow.py \
  --run-dir "${WSTA88_RUN}" \
  --prepare-to-execute \
  --ttl-sec 300 \
  --ack-credentialed-wifi \
  --ack-public-exposure \
  --native-confirm-token-source private \
  --public-confirm-token-source private

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py \
  --run-dir "${WSTA108_RUN}" \
  --emit-server-status \
  --wsta88-operator-workflow-json "${WSTA88_RUN}/wsta88_operator_workflow.json"
```

Expected status:

```text
server_status.state=SERVER_PROFILE_READY_DEFAULT_OFF
public_state=PUBLIC_OFF
live_execution_requested=false
wifi_owner=native-init
debian_role=service-surface-consumer
handoff_required_for_wsta88=false
packet_filter.ready=true
```

If a WSTA90 service hardening manifest exists, pass it with
`--wsta90-service-hardening-manifest-json` so WSTA108 also shows service-count,
no-new-privs, capability-drop, and seccomp readiness.  This is still host-only status
generation; it does not run WSTA58, connect Wi-Fi, open a public tunnel, mutate packet
filters, reboot, switch-root, or flash.

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
