# Native Init V762 Source Target Verification Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_source_staging_v760.py`
- scope: host-only rerun after operator staged Samsung OSRC source

## Goal

After the operator staged and unpacked the official OSRC package, rerun the V760
verifier with stricter target matching. V762 records whether the exact source
archive exposes all HDD/QCACLD and CNSS2 files required for kernel log
instrumentation planning.

## Work Items

1. Confirm `kernel_build/` source staging remains ignored by git.
2. Auto-detect nested `Kernel.tar.gz` inside the staged OSRC directory.
3. Verify all target source groups:
   - `qcacld_hdd_main`
   - `qcacld_hdd_driver_ops`
   - `cnss2_main`
   - `cnss2_qmi`
4. Keep patching/building/flashing blocked.
5. Select V763 kernel log instrumentation planning only if all target groups are
   present.

## Forbidden

- no source patch
- no source extraction by the verifier
- no kernel build
- no boot image or partition write
- no device command
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping

## Success Criteria

- V760 rerun reports `v760-source-targets-verified`.
- `target_groups_missing` is empty.
- `kernel_build/SM-A908N_KOR_12_Opensource/` remains ignored.
- Next gate is kernel log instrumentation planning, not live patch/flash.
