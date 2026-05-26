# Native Init V1078 PM Service Uprobe Active Live Plan

## Goal

Run the first bounded active PM-service uprobe proof on native v724: mount the
minimal read-only vendor surface, register selected dynamic uprobes for
`pm-service`, attach the V1076 BPF counter helper, run the existing PM trigger
observer child, then clean up tracefs/vendor/SELinuxfs state.

## Background

V1075 classified `pm-service` as a stripped AArch64 PIE and selected aligned
entry/main/PLT offsets. V1076 built `a90_pm_service_uprobe_counter v1076`.
V1077 deployed that helper and proved safe check-only/default behavior. V1078 is
the first live attach attempt around the PM actor observer.

## Gate

- Verify V1077 manifest is PASS.
- Verify `/cache/bin/a90_android_execns_probe` and
  `/cache/bin/a90_pm_service_uprobe_counter` sha256 values.
- Mount `sda29` read-only with `noload` through a synthetic block node when
  `/dev/block/sda29` is absent.
- Mount tracefs only for the bounded observation window.
- Register the compact uprobe set:
  - `elf_entry:0x6000`
  - `libc_init_main_candidate:0x7650`
  - `android_log:0x9e60`
  - `binder_driver:0xa0a0`
  - `mdmdetect_system_info:0x9f40`
  - `qmi_csi_register:0x9fb0`
  - `property_set:0x9ec0`
- Run the PM trigger observer through an uploaded child script to avoid
  `a90_tcpctl run` argument-count truncation.
- Always remove uprobe events and unmount temporary filesystems after the run.

## Forbidden

- No service-manager expansion beyond the existing observer contract.
- No CNSS daemon start, Wi-Fi HAL start, scan/connect/link-up, credentials,
  DHCP, route changes, or external ping.
- No `/dev/esoc*` open, `wlan.ko` load, boot image write, partition write, flash,
  or reboot.

## Success Criteria

- `pm-service` binary is visible at the read-only vendor mount.
- Dynamic uprobe events register and clean up without residue.
- BPF counters attach and collect at least one entry/main or PLT hit from the PM
  observer child.
- Postflight surface remains clean: no forbidden actor, no Wi-Fi link, no
  persistent tracefs/vendor mount, and native selftest `fail=0`.

## Failure Classification

If dynamic uprobe event registration succeeds but BPF attach fails, V1078 should
not retry longer. It should classify the attach boundary and route the next
cycle either to a finer BPF/perf attach stage classifier or to a tracefs-only
dynamic uprobe collector.
