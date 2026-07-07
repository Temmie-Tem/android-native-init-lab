# S22+ Bootloop / Manual Download Recheck - Clean Baseline - 2026-07-08

## Scope

Operator reported a bootloop observation followed by manual Download-mode entry.
Codex rechecked the connected S22+ state before attempting any recovery flash.

No flash, reboot, sysfs write, partition write, or rollback action was performed
by this recheck.

## Result

The device had already returned to rooted Android by the time it was inspected.
The correct response was to avoid an unnecessary rollback flash and verify the
current baseline instead.

## Evidence

USB/ADB:

- USB enumerated as Samsung MTP (`04e8:6860`), not Odin/Download, during the
  recheck.
- ADB showed one `SM-S906N` / `g0q` device.
- `sys.boot_completed=1`.
- Magisk root was available: `uid=0(root) ... context=u:r:magisk:s0`.
- Verified boot state remained `orange`.
- `persist.sys.safemode` was empty.

Partition state:

- `boot` SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- `dtbo` SHA256:
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`
- `vendor_boot` SHA256 from the reset-reason probe:
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`
- Live `ramoops_region/status=disabled`.

Read-only evidence probes:

- `s22plus_reset_reason_readonly_probe.py` result: `pass`.
- Probe run directory:
  `workspace/private/runs/s22plus_reset_reason_readonly_20260707T235107Z`
- Reported boot reason: `reboot,download`.
- `pstore` entry estimate: `0`.
- `s22plus_retained_evidence_probe.py` run found no marker hits for:
  `S22_NATIVE_INIT`, `S22_NATIVE_INIT_M23`, or
  `S22_NATIVE_INIT_USB_ACM_M23_DTS_QMP`.
- Retained-evidence run directory:
  `workspace/private/runs/s22plus_retained_evidence_probe_20260707T235109Z`

## Interpretation

This is not a cleanup failure and not a reason to flash rollback again. Current
boot, dtbo, and vendor_boot match the known clean rooted S22+ baseline. The
manual Download-mode observation should be treated as an operator-side recovery
event that had already resolved before the host recheck.

No new native-init marker was retained, so this event does not improve the
silent-hang observability frontier. Continue with the host-only DTS-exact
QMP-PHY dependency closure work; do not rerun the consumed M22 path.
