# V384 Preapproval Audit

## Summary

- Added and ran `scripts/revalidation/wifi_v384_preapproval_audit.py` as a host-only approval freshness gate.
- Clean HEAD audit passed.
- No bridge command, device mutation, daemon start, or Wi-Fi bring-up was executed by this audit.

## Evidence

- Clean audit evidence: `tmp/wifi/v384-preapproval-audit-clean/manifest.json`
- Initial self-block evidence while the audit script was untracked: `tmp/wifi/v384-preapproval-audit-current/manifest.json`

## Clean Audit Result

```text
decision: v384-preapproval-audit-pass
pass: True
reason: all host-only preapproval checks passed
next: run exact V384 approval-gated executor
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Checks Covered

- `git-clean`: clean HEAD before approval execution.
- `required-files`: V384 helper, wrappers, executor, classifier, handoff, and reports are present.
- `helper-v15-artifact`: local helper artifact exists and matches SHA `dfd543c02ccefbbbcf2fe0eb7ee168b40d40363927a63104c7aef0b9aed0bb16`.
- `helper-v15-marker`: helper strings include `a90_android_execns_probe v15` and service-manager ptrace-lite capture markers.
- `approval-phrases`: exact V384 deploy/live approval phrases are synchronized across wrappers/docs.
- `py-compile`: V384 Python wrappers and classifier compile.
- `executor-plan`: plan mode stays no-device-action and passes.
- `executor-noapproval`: no-approval `full` mode remains fail-closed with both exact approval blockers.

## Required Approval Phrases

Deploy helper v15:

```text
approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up
```

Live ptrace-lite crash capture:

```text
approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Command

```bash
python3 scripts/revalidation/wifi_v384_deploy_live_executor.py \
  --out-dir tmp/wifi/v384-executor-full-$(date +%Y%m%d-%H%M%S) \
  --deploy-approval-phrase "approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up" \
  --live-approval-phrase "approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  full
```
