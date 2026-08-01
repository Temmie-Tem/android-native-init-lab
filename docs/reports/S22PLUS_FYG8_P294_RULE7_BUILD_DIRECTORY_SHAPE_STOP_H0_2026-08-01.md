# S22+ FYG8 P2.94 Rule-7 build-directory shape stop H0

Date: 2026-08-01 KST

Scope: the second exact P2.94 host-only formal re-entry attempt, immediate
fail-closed stop, and a new non-formal input-shape guard. No candidate package,
static closure, promotion, manifest, connected read, device action, Odin,
Download transition, partition transfer, reboot, D0, D1, or F1 occurred.

## Result

The exact v2 approval binding passed `103/103` Tier-1 source receipts and the
`66/3` Tier-2/Tier-3 execution closure. The production formal command consumed
the producer-owned FYG8 source default correctly, then failed before linked
audit because its selected A/B directories had the wrong inventory:

```text
build artifact directory inventory mismatch:
['.config', 'Image', 'Image.lz4', 'System.map', 'abi.xml',
 'modules.builtin', 'modules.builtin.modinfo', 'vmlinux', 'vmlinux.symvers']
```

The private failure receipt is
`workspace/private/outputs/s22plus_fyg8_p294/build-repro-result.rule7-reentry-v2.json`,
size `271`, SHA256
`85aa600eca295c87f97379605a37fd990d1f4d9ddb4d8f01df5c1360ea473a2e`.
The command ran exactly once. The stop-on-new-failure condition ended the
approval; no downstream command ran.

## Attribution

`artifacts-a` and `artifacts-b` are the nine-artifact preserved comparison
directories. The formal verifier's production `verify_bundle()` instead
requires exactly the seven members declared by `ARTIFACT_LIMITS`, including
`build-result.json` and excluding `Image.lz4` plus module inventory files. The
correct preserved formal inputs are:

```text
workspace/private/outputs/s22plus_fyg8_p294/full-lto-dd20b502-v1/repro-a
workspace/private/outputs/s22plus_fyg8_p294/full-lto-dd20b502-v1/repro-b
```

Both have exactly `.config`, `Image`, `System.map`, `abi.xml`,
`build-result.json`, `vmlinux`, and `vmlinux.symvers`. Their embedded production
output receipts match those files. The failure was a second approval-command
input-shape error, not a candidate-byte or linked-audit failure.

## Recurrence guard

Two actual approval-window input-shape failures now justify a mechanical H0
guard. `s22plus_fyg8_p294_formal_input_preflight.py` invokes the real production
argument parser without calling `formal.check()`, requires the producer source
default, exact A/B directory inventories and embedded receipts, direct
executable GNU tools, direct intent/patch inputs, distinct A/B paths, and an
absent new result path. It reports `formal_invoked=false`.

Four focused tests cover the passing shape, the source-contract-file mistake,
the preserved nine-artifact-directory mistake, and an occupied result path.
The actual P2.94 invocation shape passes over `repro-a/repro-b`:

```text
verdict = PASS_P294_FORMAL_INPUT_SHAPE_HOST_ONLY
formal_invoked = false
```

The private guard receipt is
`workspace/private/outputs/s22plus_fyg8_p294/formal-input-preflight-v2.json`,
size `3989`, SHA256
`e1829bb29521136bfef0ab8d5150794f14a1c71e04562b9ab5dc54fe408a2a3d`.
The guard is outside all 103 payload SOURCE_KEYS and cannot change the existing
intent or Full-LTO A/B pair. Any new formal attempt still requires a fresh exact
Rule-7 approval and a new result path.

Verdict: `NO_PROOF_P294_RULE7_BUILD_DIRECTORY_SHAPE_STOPPED_H0`.
