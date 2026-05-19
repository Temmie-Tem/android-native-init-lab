# v342 Plan: V317 Approved Preflight Mode

- date: `2026-05-19`
- scope: host-side V317 approved preflight / handoff consistency
- boot image change: none planned
- device mutation: none planned
- status: implemented / validated

## Summary

v342 adds a no-device-command `preflight` mode to the V317 runner. The mode uses
the same approval and blocker checks as `run`, but returns
`private-property-namespace-proof-preflight-ready` without calling `device_cmd()`.

v342 also tightens the final handoff packet so it blocks on a dirty current tree
and prints a preflight command before the live command.

## Implementation

- Add `preflight` subcommand to `wifi_private_property_namespace_proof.py`.
- Return `private-property-namespace-proof-preflight-ready` only after blockers
  and approval checks pass.
- Never execute `live_run()` or `cleanup_sequence()` for `preflight`.
- Add `preflight_command` to `wifi_v317_handoff_packet.py` by converting the live
  command's final subcommand to `preflight`.
- Add `current-tree-clean` handoff check so the handoff and runner agree on
  dirty-tree blocking.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_private_property_namespace_proof.py \
  scripts/revalidation/wifi_v317_handoff_packet.py
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v342-v317-noapproval-preflight \
  preflight || true
python3 scripts/revalidation/wifi_v317_handoff_packet.py \
  --out-dir tmp/wifi/v342-handoff-dirty-tree-check \
  packet || true
git diff --check
```

Expected pre-commit result:

```text
no approval preflight: private-property-namespace-proof-approval-required
handoff dirty tree: v317-handoff-blocked, blocker=current-tree-clean
```

Post-commit regeneration must refresh V336/V331/V340, then run approved
preflight on clean HEAD and expect:

```text
private-property-namespace-proof-preflight-ready
commands=[]
device_commands_executed=false
device_mutations=false
```

## Acceptance

- `preflight` with no approval remains blocked.
- dirty-tree handoff is blocked before any live proof request.
- clean-head approved preflight passes without device commands.
- exact live `run` remains unexecuted until the operator explicitly chooses it.
