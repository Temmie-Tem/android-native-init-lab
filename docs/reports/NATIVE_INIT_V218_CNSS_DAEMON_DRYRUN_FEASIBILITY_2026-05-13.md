# v218 CNSS Daemon Dry-Run Feasibility

## Summary

v218 adds a manifest-first CNSS daemon dry-run feasibility modeler. It does not
execute `cnss-daemon`, `cnss_diag`, or any Wi-Fi service.

Result: PASS.

Final decision: `daemon-dryrun-partial`.

Reason: service and binary visibility are mapped, but host ELF/library
inspection is incomplete.

## Changes

- Added `scripts/revalidation/wifi_cnss_daemon_dryrun.py`.
- Added v218 plan:
  `docs/plans/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_PLAN_2026-05-13.md`.

## Scope

The modeler consumes v210/v216/v217 manifests and writes:

- `tmp/wifi/v218-cnss-daemon-dryrun/manifest.json`
- `tmp/wifi/v218-cnss-daemon-dryrun/daemon-dependencies.json`
- `tmp/wifi/v218-cnss-daemon-dryrun/summary.md`

Native read-only validation writes the same files under:

- `tmp/wifi/v218-cnss-daemon-dryrun-native`

## Static Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_cnss_daemon_dryrun.py
```

Result: PASS.

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_cnss_daemon_dryrun
wifi_cnss_daemon_dryrun.validate_no_active_commands()
print('v218 command guard PASS')
PY
```

Result:

```text
v218 command guard PASS
```

## Manifest-Only Run

Command:

```bash
python3 scripts/revalidation/wifi_cnss_daemon_dryrun.py \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v216-manifest tmp/wifi/v216-service-replay-model/manifest.json \
  --v217-manifest tmp/wifi/v217-icnss-debug-recovery-inventory/manifest.json \
  --v217-native-manifest tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json \
  --out-dir tmp/wifi/v218-cnss-daemon-dryrun
```

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v218-cnss-daemon-dryrun decision=daemon-dryrun-partial reason=service and binary visibility are mapped, but host ELF/library inspection is incomplete
```

## Native Read-Only Run

Command:

```bash
python3 scripts/revalidation/wifi_cnss_daemon_dryrun.py \
  --native-bridge \
  --out-dir tmp/wifi/v218-cnss-daemon-dryrun-native
```

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v218-cnss-daemon-dryrun-native decision=daemon-dryrun-partial reason=service and binary visibility are mapped, but host ELF/library inspection is incomplete
```

Native captures:

```text
captures=11
ok=5
```

The failed native captures are expected in the current default native state
because `/vendor` and `/system/vendor` are not mounted as Android runtime paths.
v210 already proved the vendor binaries are visible through the temporary
read-only vendor asset model.

## Daemon Model

| daemon | executable | native visible | ELF state | blockers |
| --- | --- | --- | --- | --- |
| `cnss-daemon` | `/system/vendor/bin/cnss-daemon` | yes via v210 | `no-host-vendor-root` | `requires-icnss-cnss-recovery-model-before-execution`, `reboot-only-icnss-recovery-known`, `elf-inspection-no-host-vendor-root` |
| `cnss_diag` | `/system/vendor/bin/cnss_diag` | yes via v210 | `no-host-vendor-root` | `requires-icnss-cnss-recovery-model-before-execution`, `reboot-only-icnss-recovery-known`, `elf-inspection-no-host-vendor-root` |

## Guardrails

- No daemon execution.
- No service start.
- No ICNSS sysfs/debugfs writes.
- No firmware path mutation.
- No vendor/system mount mutation in default mode.
- No Wi-Fi enablement.
- No rfkill write.
- No link-up.
- No scan/connect.

## Hashes

```text
41023966ff9febefcba4632af122619743bdeb9e7879effb7ffc76f61aad0f65  scripts/revalidation/wifi_cnss_daemon_dryrun.py
a7e475cf5a1338328b155a1bf01728c5f147f540cbc84e57fdac60696e8631ad  docs/plans/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_PLAN_2026-05-13.md
137dc3cf3fa37d92a2693c17c353c669eb95c92e173d8ec8ea3a47c719b07e57  tmp/wifi/v218-cnss-daemon-dryrun/manifest.json
cebadd33b00789189920fd3705bb0960f7b1e7b33bfc9d7b4dfd3b07f399ff53  tmp/wifi/v218-cnss-daemon-dryrun/daemon-dependencies.json
9f853564a7fa7a597522f39a85750106ab390b2064ee2dfd0ea6f2f2ff68bb07  tmp/wifi/v218-cnss-daemon-dryrun/summary.md
c07513f3cc7365a74c3f518cd0ff9c6e24f52d633ced1a08ff5cb5160b426bc0  tmp/wifi/v218-cnss-daemon-dryrun-native/manifest.json
cebadd33b00789189920fd3705bb0960f7b1e7b33bfc9d7b4dfd3b07f399ff53  tmp/wifi/v218-cnss-daemon-dryrun-native/daemon-dependencies.json
33d877cc067c020c8766e5193cf2fcd39a7a76ce14fb73ad21d93fb827f85b13  tmp/wifi/v218-cnss-daemon-dryrun-native/summary.md
```

## Decision

v218 is enough to proceed to v219 planning, but not enough to execute daemons.
The next step should design a minimal native Android-env shim and decide how to
obtain or mount a host-visible vendor root for `readelf`/library inspection
without turning that into daemon execution.

## Next

Plan v219 as native Android-env shim planning. It should define temporary mount
visibility, path aliases, property/socket policy, user/group/capability policy,
log policy, and rollback/evidence requirements before any service experiment.
