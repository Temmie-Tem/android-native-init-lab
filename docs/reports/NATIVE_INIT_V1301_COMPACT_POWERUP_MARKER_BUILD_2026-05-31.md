# Native Init V1301 Compact Powerup Marker Build

## Summary

- Cycle: `V1301`
- Type: source/build-only
- Decision: `v1301-compact-powerup-marker-build-pass`
- Result: PASS
- Helper marker: `a90_android_execns_probe v273`
- Built helper: `stage3/linux_init/helpers/a90_android_execns_probe_v273`
- SHA256: `dd1d15a5ef01189526720814c50b007f6dc9a0f25e9239caf0e9da34c65b6b46`
- Size: `1319408`
- Evidence:
  - `tmp/wifi/v1301-execns-helper-v273-build/manifest.json`
  - `tmp/wifi/v1301-execns-helper-v273-build/summary.md`

V1301 updates the compact dense response sampler so each compact sample emits a small `powerup_marker` block. This preserves the V1299 full-window behavior while adding a direct reachability signal for `pm-service` threads blocked in `mdm_subsys_powerup`.

## Added Helper Surface

- `EXECNS_VERSION` bumped to `a90_android_execns_probe v273`.
- `append_pm_service_trigger_observer_powerup_marker_compact()` scans `/proc` for `pm-service`.
- Per sample, the compact output now records:
  - `per_mgr_process_count`
  - `per_mgr_thread_count`
  - `powerup_thread_count`
  - `subsys_esoc0_open_inferred`
  - first `mdm_subsys_powerup` thread pid, tid, state, comm, wchan, syscall name, and path argument index
  - best-effort first syscall path via `process_vm_readv`, without ptrace

## Validation

| check | result |
| --- | --- |
| V1300 input decision | `v1300-v1299-esoc0-reached-manifest-false-negative` |
| source strings | PASS |
| static aarch64 build | PASS |
| readelf `INTERP` absent | PASS |
| readelf dynamic section absent | PASS |
| binary strings | PASS |

The build used `scripts/revalidation/build_android_execns_probe_helper.sh stage3/linux_init/helpers/a90_android_execns_probe_v273`.

## Safety

- Source/build-only; no deploy or device command was executed.
- No PM/CNSS actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, PMIC write, GPIO request/hold, direct eSoC ioctl, flash, boot image write, or partition write occurred.

## Next

V1302 should deploy helper `v273` only. V1303 should rerun the bounded compact dense response sampler and require the new `powerup_marker` keys before using the result to classify the remaining SDX50M no-response gate.
