# Native Init v393 Framechain Auto ELF Resolver Plan

## Goal

Make V392 post-live frame-chain analysis immediately useful by reusing existing host-side Android ELF evidence without requiring a manual `--elf-root` on the first approved V392 run.

This is a host-only improvement. It must not deploy helpers, start Android daemons, start Wi-Fi HAL, scan, connect, collect credentials, or mutate the device.

## Context

V390 captured PC/LR map rows for `servicemanager` SIGABRT and V391 pulled the matching bionic `libc.so` read-only from:

```text
/mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so
```

V392 helper v21 is ready to capture frame-chain return-address map rows. Without an automatic ELF resolver, the first V392 live result would likely stop at `service-manager-framechain-maprow-ready` even when matching ELF evidence is already present locally.

## Implementation

- Extend `scripts/revalidation/wifi_service_manager_framechain_analyze.py`.
- Preserve explicit `--elf-root` behavior.
- Add automatic host ELF cache discovery by default.
- Add `--no-auto-elf-cache` for reproducible/manual-only runs.
- Discover reusable roots:
  - `tmp/wifi/v227-android-core-system-library-evidence/system-root`
  - `tmp/wifi/v222-vendor-root-evidence-export/vendor-root`
  - roots listed in `tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json`
- Discover bionic libc alias from latest V391 `manifest.json`.
- Resolve namespace paths such as:
  - `/tmp/a90-v231-1910/root/apex/com.android.runtime/lib64/bionic/libc.so`
  - `/apex/com.android.runtime/lib64/bionic/libc.so`
  - `/system/apex/com.android.runtime/lib64/bionic/libc.so`

## Validation

- `python3 -m py_compile scripts/revalidation/wifi_service_manager_framechain_analyze.py`
- Synthetic frame-chain log maps `frame0_ra` into bionic `libc.so` and must return `service-manager-framechain-symbolization-pass`.
- V390 negative log without frame-chain evidence must still return `service-manager-framechain-needs-v392-live`.
- V392 no-approval executor must still execute no device command, no mutation, no daemon start, and no Wi-Fi bring-up.
- Read-only device health check must still pass.

## Expected Outcome

After the approved V392 live run, if frame-chain return addresses map into a locally available Android ELF, the executor/analyzer should route directly to symbolized caller inspection instead of asking for manual ELF roots.
