# Native Init v242 CNSS Runtime Requirement Inventory Plan

- target: host-side Wi-Fi/CNSS runtime requirement inventory
- baseline: `A90 Linux init 0.9.59 (v159)` on device, v241 helper/linker evidence available
- implementation: no boot image change, no daemon start
- output: `tmp/wifi/v242-cnss-runtime-inventory/`

## Goal

v241 proved that a private Android execution namespace can resolve
`/vendor/bin/cnss-daemon` linker dependencies when `/dev/null`, real
linkerconfig, and a private `com.android.vndk.v30 -> com.android.vndk.current`
APEX alias are present.

v242 does not start `cnss-daemon`. It inventories the remaining Android runtime
contract needed before a controlled start-only runner can be considered.

## Scope

- Parse existing evidence:
  - v216 Android service replay model
  - v218 CNSS daemon dry-run
  - v241 VNDK APEX alias linker-list PASS result
- Collect live read-only native state:
  - version/status/selftest
  - `/mnt/system` visibility
  - linkerconfig and helper presence
  - `cnss-daemon` and `cnss_diag` path aliases
  - Android property/socket paths
  - ICNSS/sysfs, rfkill, network, device-node candidates
- Produce a start-only blocker list:
  - launcher identity contract: user, groups, capabilities
  - Android property/socket availability
  - SELinux label mismatch
  - kernel/device-node availability
  - service ordering constraints

## Guardrails

- No `cnss-daemon` or `cnss_diag` execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill write.
- No ICNSS bind/unbind or sysfs writes.
- No persistent Android partition write.
- No global bind mount or daemon lifecycle mutation.

`mountsystem ro` is allowed as a bounded read-only visibility step because the
inventory needs Android system/vendor paths; it must not remount read-write.

## AOSP Runtime References

- Android init service syntax has explicit `service`, `user`, `group`,
  `capabilities`, `socket`, `file`, and `seclabel` semantics. v242 treats these
  as a runtime contract to emulate or document before native start-only.
- Android linker namespace configuration controls `search.paths`,
  `permitted.paths`, and vendor/VNDK namespace links. v241 closed the linker
  dependency blocker only inside a private namespace, so v242 keeps runtime
  inventory separate from linker-list success.

## Implementation

- Add `scripts/revalidation/wifi_cnss_runtime_inventory.py`.
- Default output directory: `tmp/wifi/v242-cnss-runtime-inventory`.
- Use private/no-follow `EvidenceStore` output helpers.
- Record every command transcript under `captures/`.
- Write:
  - `manifest.json`
  - `summary.md`
  - `runtime-requirements.json`
  - `live-captures.json`

## Decision Labels

- `cnss-runtime-inventory-ready-for-launcher-contract-plan`
  - v241 linker prerequisite PASS and live inventory completed enough to plan
    a native launcher contract, but daemon start remains blocked.
- `cnss-runtime-inventory-prereq-gap`
  - required v216/v218/v241 evidence is missing or not PASS.
- `cnss-runtime-inventory-live-gap`
  - live read-only collection failed for required paths.
- `cnss-runtime-inventory-manual-review`
  - evidence is internally inconsistent.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_cnss_runtime_inventory.py
git diff --check
python3 scripts/revalidation/wifi_cnss_runtime_inventory.py collect
```

Expected result:

- no daemon start
- output directory created with private permissions
- decision is not a Wi-Fi bring-up approval
- next item is a launcher-contract plan, not active Wi-Fi

