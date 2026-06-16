# NATIVE_INIT V2626 — ACDB AFE topology probe build

Date: 2026-06-16

## Scope

Host-only build-only unit. It builds a future Android-good own-process
helper/preload pair that calls only the AFE topology ID/table GET path.
No device handoff, flash, native replay `SET`, speaker write, or ACDB command execution occurred.

## Decision

- decision: `v2626-acdb-afe-topology-probe-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2626-acdb-afe-topology-probe-build-only`
- helper: `workspace/private/builds/audio/v2626-acdb-afe-topology-probe-build-only/bin/a90_acdb_afe_topology_probe_exec_linked_v2626`
- helper_sha256: `0809e0d81fc4681d59efee23af46dd5841a75ecd4cc5c0a6b07bb76202506865`
- preload: `workspace/private/builds/audio/v2626-acdb-afe-topology-probe-build-only/bin/liba90_acdb_afe_topology_probe_combined_preload_v2626.so`
- preload_sha256: `08082387b8a922424ea226b1aad382b857d75d16ae12c2d1c6fd5bba0f24e194`

## Why This Unit Exists

Gate-2 verification superseded the old post-init topology-capture handover:
topology cal_type 39 is already captured, while the native replay manifest
still lacks AFE topology cal_type 8/9. V2547 showed command `0x13262`
during the successful topology path, but the old tap only preserved the direct
4-byte out buffer. V2626 adds a command-specific indirect capture for that path.

## Probe Contract

- direct_commands: `['0x130d8', '0x13262']`
- capacity_sweep: `[4, 256, 4096]`
- tap_indirect_layout: `{'cmd': '0x13262', 'kind': 'ind-afe-topology', 'ptr_word': 1, 'cap_word': 0}`
- helper omits `0x12eeb`, VOL sweep, `send_audio_cal_v5`, `/dev/msm_audio_cal`, and native SET.
- raw captures remain private-only and require future live Gate-2 operator verification before replay.

## Static Gates

- required_ok: `True`
- prohibited_ok: `True`
- vendor_libs_ok: `True`
- build_ok: `True`

## Next

Run a bounded Android-good own-process live handoff with these artifacts, pull the
complete tap directory privately, and classify any `ind-afe-topology` records as
payload candidates only after `ret==0` and non-zero-buffer checks. Native replay remains blocked.
