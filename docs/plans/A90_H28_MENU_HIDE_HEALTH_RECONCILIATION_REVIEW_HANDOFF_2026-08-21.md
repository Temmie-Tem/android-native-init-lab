# A90 H28 menu-hide health reconciliation — independent review handoff

This is an H0 review handoff for
`A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_V1`. It is not an approval and does
not authorize a connected session.

## Review target

Review the complete execution-critical closure, including every exact path
listed by `a90_h28_physical_system_return_reconcile_v1.py`'s
`EXECUTION_SOURCE_RELS`, of
`workspace/public/src/scripts/server-distro/a90_h28_menu_hide_health_reconcile_v1.py`
and its interactions with the A90 target contract, the fixed boot-only owner,
the managed Native bridge, and the two prior H28 observer incidents.

The reviewer must independently verify that:

- the old slow-health capability, token, sidecar, and log directory are not
  reused;
- the fixed H28 manifest, nine-record journal, terminal, active guard, and
  consumed candidate guard are bound exactly;
- the physical-return intent SHA is
  `19377bc18714c7b2b698665a8c9ff96573d3c1fdfb028efba5b86f6b2def9f66`;
- the first Native observation intent SHA is
  `8f401590bca71575258a2e3d45e1bee6c55fd4e8eeff4c22012fc25f559d05be`;
- the consumed slow-health intent SHA is
  `63c26238f332a7bc1bad37a3950d5dc05f383c50a4a09ecfe57e2a119a390ac4`;
- the twelve prior slow-health receipt names, sizes, and SHA-256 values are
  declared in source and are not silently widened at runtime;
- the new `O_EXCL` intent is durable before USB, bridge, socket, or Native
  contact;
- the raw bridge `hide` line is exactly one send with a captured receipt that
  explicitly contains `hide requested` (prompt-only or `[done]`-only output
  is rejected), and no retry;
- the fixed 3.0-second asynchronous-menu settle from
  `native_init_flash.py` is awaited before any boot-ID request; interruption
  or failure parks after the intent and no read is sent;
- the subsequent command/log order is `boot-id`, `version`, `selftest`,
  `status`, `boot-id-final`, with exactly two boot-ID reads and one hide send;
- the final boot-ID receipt is present, valid, and exactly equal to the first;
  changed, missing, invalid, or failed final reads park without a recovery
  record or active-guard removal;
- exact V2321, `fail=0`, `pstore entries=0`, first boot ID, and unchanged
  A90/foreign USB inventory are required for success;
- every failed, busy, drifted, malformed, or uncertain path retains both
  guards and cannot create a second observer; and
- only exact recovery-record readback releases the active guard.

## Required hostile corpus

The review should reject at least: missing or malformed prior receipt files;
prior receipt size/hash drift; token substitution; review or closure drift;
intent publication after the hide call; a second hide or retry; hide output
that is prompt-only, `[done]`-only, busy/error, or empty; settle interruption;
boot-ID not first; wrong resident/build; selftest
failure; pstore entries; boot-ID drift; changed A90 or foreign endpoint
inventory; missing/changed guards; a pre-existing new sidecar; a recovery
record with the active guard retained; and any caller-selected path, command,
endpoint, or unsafe action.

## Reviewer output

The independent result must be a separate canonical JSON review with the
capability, exact H28 bindings, execution-closure digest, `PASS_GO` or a
no-go verdict, empty/typed findings, and explicit zero-contact fields. Leave
the verdict and findings to the reviewer; this handoff is not a self-signing
result.
