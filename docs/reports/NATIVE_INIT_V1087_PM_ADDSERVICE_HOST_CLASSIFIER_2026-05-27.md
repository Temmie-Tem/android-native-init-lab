# Native Init V1087 PM addService Host Classifier Report

## Summary

V1087 passed as a host-only classifier. It reconciles the V1071 exit-255
direction with the newer V1086 evidence and marks the V1071 BPF/syscall plan as
obsolete for the current branch.

Decision:

```text
v1087-addservice-readiness-policy-delta-classified
```

V1086 already used the uprobe route and proved the current blocker:
`pm-service` reaches `addService("vendor.qcom.PeripheralManager", ...)`, logs
the addService failure, and returns `0` before QMI thread creation.

## Evidence

| item | path |
| --- | --- |
| classifier | `scripts/revalidation/native_wifi_pm_addservice_host_classifier_v1087.py` |
| manifest | `tmp/wifi/v1087-pm-addservice-host-classifier/manifest.json` |
| summary | `tmp/wifi/v1087-pm-addservice-host-classifier/summary.md` |
| V1086 input | `tmp/wifi/v1086-pm-service-success-path-trace-live/manifest.json` |
| V694 positive control | `tmp/wifi/v694-peripheral-vndservice-query-orchestrated-live-rerun/manifest.json` |

## Result

```json
{
  "bpf_uprobe_route_already_used": true,
  "decision": "v1087-addservice-readiness-policy-delta-classified",
  "exit255_direction_obsolete": true,
  "policy_delta": true,
  "readiness_delta": true,
  "v1086_addservice_failure": true,
  "v694_provider_positive": true
}
```

## Findings

- V1086 `per_mgr` exits `0`, not `255`.
- V1086 reaches `pm_add_service_call=1` and `pm_add_service_fail_log=1`.
- V1086 does not reach QMI startup: `pm_pthread_create_call=0`.
- V694 proves `vendor.qcom.PeripheralManager` registration through
  `/vendor/bin/vndservice list`.
- V694 positive path included `vndservicemanager_ready=1`.
- V694 positive path included the V490 SELinux policy-load proof.
- V1072 reference evidence shows service context files are visible, but
  setexec can still be accepted while runtime context stays `kernel`.

## Interpretation

The immediate next step is not another broad BPF syscall search for exit `255`.
That branch has already been superseded by the V1086 trace.

The next live gate should reproduce the V694 provider-positive preconditions in
the current PM observer path:

1. require or refresh the V490 SELinux policy-load precondition;
2. start `vndservicemanager`;
3. wait for an explicit `vndservicemanager` readiness/query signal;
4. then start `pm-service`;
5. immediately query `/vendor/bin/vndservice list` for
   `vendor.qcom.PeripheralManager`.

## Guardrails

- Host-only only.
- No device command.
- No tracefs write.
- No BPF attach.
- No PM actor start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credentials, DHCP, route change, or external ping.
- No partition write, flash, or reboot.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_addservice_host_classifier_v1087.py
python3 scripts/revalidation/native_wifi_pm_addservice_host_classifier_v1087.py
```

Result:

```text
decision: v1087-addservice-readiness-policy-delta-classified
pass: True
```

## Next

V1088 should be source/build or bounded live, depending on whether the current
helper already exposes a suitable readiness query. The minimal repair is to add
a PM-observer `vndservicemanager` readiness/query gate before `per_mgr`, and to
make the V490 policy-load precondition explicit before retrying addService.
