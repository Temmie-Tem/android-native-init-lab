# Native Init V2187 Screenapp UI Validation Live

## Summary

- Candidate tag: `v2187-screenapp-ui-validation`.
- Parent/promoted rollback baseline: `v2186-wifi-ui-polish`.
- Type: rollbackable live test-boot UI validation.
- Decision: `v2187-screenapp-ui-validation-pass`.
- Result: PASS.
- Reason: V2187 rendered WIFI STATUS and WIFI PING RESULTS through screenapp, then rolled back to V2186 with selftest fail=0.
- Evidence directory: `tmp/wifi/runs/v2187-screenapp-ui-validation-p1-screenapp-clean-20260610-103339`.
- Test boot image: `workspace/private/inputs/boot_images/boot_linux_v2187_screenapp_ui_validation.img`.
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2186_wifi_ui_polish.img`.

## Screen Evidence

- `screenapp wifi-status`: pass `True`, title `WIFI STATUS`, presented `1`.
- `screenapp wifi-ping`: pass `True`, title `WIFI PING RESULTS`, presented `1`.
- Both commands use the same native draw functions as the `NETWORK` menu apps.
- This is command-level framebuffer presentation evidence; physical button navigation/OCR remains optional follow-up evidence.
- `autohud` is not restored inside the test boot because rollback to V2186 immediately reboots and restores the baseline HUD service.

## Rollback

- Rollback attempt: `from-recovery`.
- Rollback command ok: `True`.
- Post-rollback status ok: `True`.
- Post-rollback selftest ok: `True`.

## Safety Scope

- `screenapp wifi-status` is read-only.
- `screenapp wifi-ping` is explicit and bounded, using the existing `NETWORK > PING TEST` collector.
- No credentials, raw SSID, BSSID, private IP, gateway, or peer MAC details are included in this public report.
- No PMIC/GPIO/GDSC/regulator writes, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or `/dev/subsys_esoc0` path was used.
