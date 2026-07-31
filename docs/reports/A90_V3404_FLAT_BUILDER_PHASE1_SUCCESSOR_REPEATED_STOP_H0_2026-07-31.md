# A90 V3404 Flat Builder Phase 1 Successor Repeated H0 Stop

- Date: `2026-07-31`
- Decision: `STOP_REPEATED_HOST_ACCEPTED_PATH_REWRITE_HASH_UNCHANGED`
- Scope: host-only closure-capture successor
- Device, staging, reboot, flash, or network-to-device action: none

## Successor design

The successor installed a Python audit-hook write guard for the canonical
accepted V3404 path, replaced every loaded common-builder `main()` instance
with a sentinel, and required exact SHA, size, and mtime preservation.

The fault injection proved direct write-open rejection. The real legacy
closure, however, invoked the sentinel once and then continued through upper
post-processing. That path still rebuilt/replaced the canonical output. The
audit hook did not provide complete rename/replace containment.

The same material capture failure occurred twice. Neither attempt produced an
accepted closure snapshot.

## Preserved identities

The accepted content remains byte-identical:

```text
0a8827aeb46e2fb2cdf1e7cf7320626b4b3a43fcdbbff2024d92dcbc088e83d3
```

No tracked source or report was rewritten by the legacy builder. The accepted
file mtime changed again, so the no-overwrite contract failed despite content
identity.

## Disposition

Stop the Phase 1 line under the repeated material host-failure rule. The
failed capture scripts are not adopted. The inherited builder remains
authoritative and no flat builder exists.

Do not attempt another in-process monkey-patch or Python audit-hook variant.
Any future restart requires a stronger containment primitive selected in a new
H0 unit, such as a fully disposable repository clone with no path to the
canonical private tree. This report grants no device authority.
