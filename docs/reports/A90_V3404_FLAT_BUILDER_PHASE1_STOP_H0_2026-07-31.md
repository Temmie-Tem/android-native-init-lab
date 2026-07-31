# A90 V3404 Flat Builder Phase 1 H0 Stop

- Date: `2026-07-31`
- Decision: `STOP_HOST_ACCEPTED_PATH_REWRITE_HASH_UNCHANGED`
- Scope: host-only effective-closure audit
- Device, staging, reboot, flash, or network-to-device action: none

## Intended audit

Phase 1 attempted to replace the 171-module native boot wrapper chain with a
flat effective snapshot. V726 also enters a separate Wi-Fi builder lineage, so
the audit tried to intercept the final common builder immediately before its
`main()` and inspect the effective argument/function state.

## Stop event

The legacy tree loaded the same common source under different module names.
The interception patched one module instance while the V3404 chain invoked
another. The audit therefore ran the normal host builder and rewrote the
canonical accepted V3404 output path.

No source or device action occurred. The rewritten bytes are identical to the
accepted identity:

```text
accepted boot before  0a8827aeb46e2fb2cdf1e7cf7320626b4b3a43fcdbbff2024d92dcbc088e83d3
accepted boot after   0a8827aeb46e2fb2cdf1e7cf7320626b4b3a43fcdbbff2024d92dcbc088e83d3
```

The tracked V3404 report is unchanged. Native-init and helper source hashes
also remain:

```text
init_v724.c                    88363bfaea42b93cf652b0e5bb5bf2beff88d7ce11595c019e2d4d59529378ba
a90_android_execns_probe.c     d71446bb9073362fa75a263ce7bf20b4eea0279f12f3f494610b4a08346ab635
```

The accepted file timestamp changed. Phase 1 therefore fails its stronger
no-overwrite contract even though content identity is preserved.

## Disposition

Stop this Phase 1 unit without retry. The inherited builder remains
authoritative and no flat builder is accepted.

A successor must perform closure extraction in a disposable copied module
tree or in a subprocess whose common builder entrypoint is replaced before
any legacy import. It must first prove, with a fault test, that reaching an
unexpected `main()` cannot open the canonical output path. This report grants
no device authority.
