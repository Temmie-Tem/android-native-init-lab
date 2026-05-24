# Native Init V756 Non-ftrace HDD/PLD Observability Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_nonftrace_hdd_pld_observability_v756.py`
- scope: read-only non-ftrace observability classifier; no Wi-Fi trigger

## Goal

V755 proved that tracefs can be mounted and cleaned up, but function-filter
surfaces and HDD/PLD target functions are not available. V756 classifies the
remaining low-risk observability routes before another Wi-Fi trigger: dynamic
debug, kprobe events, printk/loglevel state, existing dmesg markers, and WLAN
sysfs state.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V753_HDD_PLD_PREREQ_CLASSIFIER_2026-05-24.md`
- `docs/reports/NATIVE_INIT_V755_TRACEFS_MOUNT_FILTER_PROOF_2026-05-24.md`
- `tmp/wifi/v753-hdd-pld-prereq-classifier/manifest.json`
- `tmp/wifi/v755-tracefs-mount-filter-proof-retry/manifest.json`

## Work Items

1. Validate V753 and V755 as input evidence.
2. Confirm current native health with `version`, `status`, `selftest`, and
   `tracefs full`.
3. Capture `/proc/cmdline`, `/proc/sys/kernel/printk`, and readable printk
   module parameters.
4. Capture dynamic-debug catalog availability and bounded HDD/PLD-related
   catalog hits without writing control files.
5. Capture kprobe-event/debugfs/tracefs read surfaces without mounting or
   writing events.
6. Capture relevant config options from `/proc/config.gz`.
7. Capture focused dmesg and current WLAN/sysfs state.
8. Route V757 to dynamic-debug, kprobe, or boot-image/log instrumentation based
   on the current surfaces.

## Forbidden

- no tracefs/debugfs mount
- no ftrace, dynamic-debug, or kprobe control writes
- no `boot_wlan`, `qcwlanstate`, bind/unbind, module, or subsystem writes
- no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping
- no boot image or partition writes

## Success Criteria

- Produce `manifest.json` and `summary.md`.
- Prove whether dynamic-debug target catalog entries are available.
- Prove whether kprobe-event surfaces are usable without a new mount.
- Prove whether current printk/dmesg/sysfs state gives enough HDD/PLD
  resolution.
- Prove no device mutation, Wi-Fi trigger, connect attempt, credential use, or
  external ping occurred.
- Select the least invasive V757 route.

## Source References

- Linux dynamic debug documentation:
  <https://docs.kernel.org/admin-guide/dynamic-debug-howto.html>
- Linux kprobe event tracing documentation:
  <https://docs.kernel.org/trace/kprobetrace.html>
- Linux printk documentation:
  <https://docs.kernel.org/core-api/printk-basics.html>
