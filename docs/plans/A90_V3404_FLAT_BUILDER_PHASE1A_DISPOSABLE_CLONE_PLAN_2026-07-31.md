# A90 V3404 Flat Builder Phase 1A Disposable Clone Plan

- Date: `2026-07-31`
- Tier: `H0`
- Schema name: `flat-builder-v1`
- Device authority: none

## Objective

Materialize the final effective V3404 build state and reproduce the Phase 0
boot, ramdisk, init, helper, and engine golden hashes without executing legacy
code in the canonical repository namespace.

## Isolation contract

1. Export tracked `HEAD` into a fresh mode-0700 directory below
   `workspace/private/outputs/`.
2. Copy only the exact V3403/V3404 boot inputs, V3403 Doom source, and recovered
   V535 property-runtime directory into the clone.
3. Enter a new bubblewrap user/mount/PID/network namespace.
4. Expose the disposable clone only as `/work`; do not bind the canonical
   repository or its private tree.
5. Bind host toolchain/runtime directories read-only and use private `/tmp` and
   `HOME`.
6. Fault-test that the canonical absolute path is absent and a clone-private
   sentinel is writable before any legacy import.
7. Reject any tracked source containing the canonical absolute repository path.

## Migration order

1. Capture legacy effective data and generated source only inside `/work`.
2. Materialize one fully flattened `v3404-effective` manifest and source tree.
3. Build it twice through the only writing entrypoint.
4. Require exact Phase 0 equality for boot, ramdisk, init, helper, and engine.
5. Only after parity, move identity injection to existing `-DINIT_VERSION` and
   `-DINIT_BUILD` paths and record any intentional new profile separately.
6. Future versions use shallow data-only `extends`; never mutate a parent
   module.

## Permanent new-pipeline rules

- Manifest loading is data-only and performs no writes.
- `buildlib` functions do not mutate module globals or write files.
- `build.py` is the only writer.
- One source file has one canonical module name.
- No `a90test_<stem>` alias is used for production builder modules.
- Adapter/generated C is a real versioned source file, not an inherited Python
  string.
- Legacy builders remain frozen until five-artifact parity passes.

## Stop conditions

- The canonical repository becomes visible inside the sandbox.
- A required input is not exact or is taken from an undeclared fallback.
- Any legacy operation targets a path outside `/work`.
- Native-init or helper C changes.
- A flat artifact differs without a complete byte-level attribution.
- Any device, staging, reboot, flash, or network-to-device action is requested.
