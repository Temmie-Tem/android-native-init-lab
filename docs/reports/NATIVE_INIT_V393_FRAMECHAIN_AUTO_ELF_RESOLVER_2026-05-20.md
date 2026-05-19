# Native Init v393 Framechain Auto ELF Resolver

## Summary

V393 improves the V392 post-live analysis path. The frame-chain analyzer now automatically reuses existing host-side Android ELF evidence, including the V391 read-only bionic `libc.so` pull, so the first approved V392 backchain capture can symbolize known return-address paths without an extra manual `--elf-root`.

This update is host-only. It does not deploy helper v21, does not start service-manager daemons, and does not attempt Wi-Fi bring-up.

## Changed Tooling

- tool: `scripts/revalidation/wifi_service_manager_framechain_analyze.py`
- plan: `docs/plans/NATIVE_INIT_V393_FRAMECHAIN_AUTO_ELF_RESOLVER_PLAN_2026-05-20.md`

New behavior:

- keeps explicit `--elf-root` support
- adds automatic ELF cache discovery by default
- adds `--no-auto-elf-cache` to disable automatic discovery
- records `elf_roots`, `elf_aliases`, and `auto_elf_cache` in the analyzer manifest
- resolves helper namespace paths under `/tmp/.../root/apex/...`
- reuses V391 `libc.so` for bionic libc frame return-address symbolization

## Reused Evidence

- V391 libc pull: `tmp/wifi/v391-libc-symbolize-20260520-065233/files/libc.so`
- V391 manifest: `tmp/wifi/v391-libc-symbolize-20260520-065233/manifest.json`
- V221 root manifest: `tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json`
- system root cache: `tmp/wifi/v227-android-core-system-library-evidence/system-root`
- vendor root cache: `tmp/wifi/v222-vendor-root-evidence-export/vendor-root`

## Validation

Static validation:

```text
python3 -m py_compile scripts/revalidation/wifi_service_manager_framechain_analyze.py
```

Result: PASS.

Synthetic auto-ELF smoke:

- evidence: `tmp/wifi/v393-framechain-auto-elf-smoke/`
- final evidence: `tmp/wifi/v393-framechain-auto-elf-smoke-final/analyze/`
- synthetic map row: `/tmp/a90-v231-1910/root/apex/com.android.runtime/lib64/bionic/libc.so + 0x8be90`
- decision: `service-manager-framechain-symbolization-pass`
- symbol: `abort`
- source: `??:?`
- `device_commands_executed`: `False`
- `device_mutations`: `False`
- `daemon_start_executed`: `False`
- `wifi_bringup_executed`: `False`

No-auto regression:

- evidence: `tmp/wifi/v393-framechain-auto-elf-smoke-final/no-auto/`
- decision: `service-manager-framechain-maprow-ready`
- symbols present: `False`
- purpose: proves `--no-auto-elf-cache` disables implicit V391 libc reuse

V390 negative regression:

- evidence: `tmp/wifi/v393-framechain-negative-v390/`
- final evidence: `tmp/wifi/v393-framechain-negative-v390-final/`
- decision: `service-manager-framechain-needs-v392-live`
- pass: `True`
- `device_commands_executed`: `False`
- `device_mutations`: `False`
- `daemon_start_executed`: `False`
- `wifi_bringup_executed`: `False`

V392 no-approval executor regression:

- evidence: `tmp/wifi/v393-v392-noapproval-full/`
- decision: `v392-deploy-live-executor-approval-required`
- pass: `True`
- `device_commands_executed`: `False`
- `device_mutations`: `False`
- `daemon_start_executed`: `False`
- `wifi_bringup_executed`: `False`

Read-only device health:

- evidence: `tmp/wifi/v393-readonly-20260520-071428/`
- `version`: PASS
- `status`: PASS
- `selftest`: PASS

## Impact On Next Live Run

V392 remains the next live execution target. V393 does not remove the exact approval requirement.

Required V392 approval phrases remain:

```text
approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up
```

```text
approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

If approved V392 frame-chain evidence points into the already cached bionic libc path, the V392 executor can now route directly to `service-manager-framechain-symbolization-pass`.
