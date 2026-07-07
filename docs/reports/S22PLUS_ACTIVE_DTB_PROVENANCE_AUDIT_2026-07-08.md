# S22+ — Active DTB Provenance Audit (2026-07-08)

## Summary

Codex added and ran a read-only active-DTB provenance audit after the direct
`vendor_boot` ramoops patch booted but left live `ramoops_region/status`
disabled.

Result: pass. The direct `vendor_boot` patch was not the right standalone live
unit because the stock DTBO overlay applies `status = "disabled"` to the
`ramoops_region` after the base vendor DTB is selected.

## Scope

Host/read-only only:

- no flash
- no reboot
- no partition write
- no sysfs write
- no module insertion
- no file staged on the device

Added helper:

`workspace/public/src/scripts/revalidation/s22plus_active_dtb_provenance_audit.py`

Private JSON output from the final run:

`workspace/private/runs/s22plus_active_dtb_provenance_20260707T185707Z/active_dtb_provenance.json`

## Baseline Checks

The audit re-verified the current Android baseline:

- Android boot completed.
- `boot_recovery=0`.
- Magisk/root is available.
- Current `boot` matches the pinned Magisk boot baseline.
- Current `vendor_boot` matches stock FYG8.
- Current `dtbo` matches stock FYG8.

No write or reboot was used to collect this evidence.

## Evidence

Live `/proc/device-tree/reserved-memory/ramoops_region` currently has:

```text
compatible = "ramoops"
size       = 0000000000200000
pmsg-size  = 00200000
mem-type   = 00000002
phandle    = 00000274
status     = "disabled"
```

The stock `vendor_boot` DTB evidence:

- 4 concatenated FDT blobs.
- Every blob has `__symbols__/ramoops_mem = /reserved-memory/ramoops_region`.
- Every blob has the same non-status ramoops base properties seen in the live
  node.
- The stock vendor_boot DTB has no `status` property on that node.
- The direct patched vendor_boot DTB adds `status = "okay"` to all 4 blobs.

The stock `dtbo.img` evidence:

- 11 FDT blobs total.
- Blobs 9 and 10 contain the `ramoops_mem` fixup to
  `/fragment@116:target:0`.
- Those same blobs apply
  `/fragment@116/__overlay__/status = "disabled"`.

The existing patched-DTBO output evidence:

- It changes only those two target overlay status values from `"disabled"` to
  `"okay"`.
- The final audit saw patched DTBO blobs 9 and 10 as:

```text
blob 9  /fragment@116/__overlay__/status = "okay"
blob 10 /fragment@116/__overlay__/status = "okay"
```

## Corrected Interpretation

The previous direct `vendor_boot` live result was real but the interpretation
needed correction.

The stronger model is:

1. Base vendor DTB supplies `/reserved-memory/ramoops_region`.
2. Stock DTBO overlay targets that node through `ramoops_mem`.
3. Stock DTBO then applies `status = "disabled"`.
4. Therefore a vendor_boot-only patch that adds `status = "okay"` can boot yet
   still result in live `status = "disabled"` after overlay application.

So the direct `vendor_boot` patch did not prove that vendor_boot is inactive. It
proved that patching vendor_boot alone is insufficient while stock DTBO remains
in place.

## Next Gate

Do not flash M13 or M15 yet.

The next useful live unit is a DTBO-status gate:

1. Flash only the SHA-pinned patched DTBO candidate.
2. Require Android/root to return.
3. Verify live `/proc/device-tree/reserved-memory/ramoops_region/status =
   "okay"`.
4. Restore stock DTBO.
5. Only after this gate passes, design the M13 positive-control capture with a
   proven enabled ramoops node.

This retires the direct vendor_boot-only ramoops path.

## Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_active_dtb_provenance_audit.py

PYTHONPATH=workspace/public/src/scripts/revalidation \
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_active_dtb_provenance_audit.py \
  --serial <redacted> \
  --out workspace/private/runs/s22plus_active_dtb_provenance_20260707T185707Z/active_dtb_provenance.json
```

Observed final result:

```text
result=pass
conclusion=stock-dtbo-overlay-overrides-ramoops-status
live_status=["disabled"]
stock_dtbo_target_statuses=[(9, "disabled"), (10, "disabled")]
patched_dtbo_target_statuses=[(9, "okay"), (10, "okay")]
```
