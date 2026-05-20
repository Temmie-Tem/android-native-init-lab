# Native Init v416 Current Gate Packet Plan

## Scope

V416 aggregates V411 through V415 evidence into one current Wi-Fi gate decision.

V416 is host-only.  It reads existing evidence and must not execute bridge or
device commands, deploy helpers, start service-manager, start Wi-Fi HALs,
scan/connect/link-up, or perform Wi-Fi bring-up.

## Inputs

- V411 helper v27 deploy preflight.
- V411 binderized query preflight/live manifest.
- V412 result router.
- V413 VINTF Wi-Fi declaration collector.
- V414 static/runtime target classifier.
- V415 runtime/static comparator.

## Decisions

```text
v416-current-gate-waiting-for-v411-deploy
```

All host-side follow-up tools are ready and the next live gate is helper v27
deploy only.

```text
v416-current-gate-waiting-for-v411-live-query
```

Helper v27 is deployed and V411 live binderized query is the next gate.

```text
v416-current-gate-primary-runtime-match-ready
```

V415 has proven runtime/static primary match and the next plan should be a
no-scan/no-link HIDL client proof.

```text
v416-current-gate-micro-query-needed
```

V411 runtime query failed or timed out; use V414 primary patterns to design a
smaller micro `hwservicemanager` query.

## Current Expected Result

Current evidence should route to:

```text
v416-current-gate-waiting-for-v411-deploy
```

Required next approval phrase:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

## Success Criteria

- Executes no device command.
- Evidence output is private.
- Aggregates V411-V415 decisions without changing their meaning.
- Preserves the no-Wi-Fi-bring-up boundary.
- Names the exact next live gate and required approval phrase.
