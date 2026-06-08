# Native Init V2183 / V2182 HUD Menu Cleanup Baseline Promotion

## Summary

- Promotion run: `V2183`
- Promoted baseline tag: `v2182-hud-menu-cleanup`
- Device-visible build: `A90 Linux init 0.9.255 (v2182-hud-menu-cleanup)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2182_hud_menu_cleanup.img`
- Boot SHA256: `8e3e16f68d019ef5f56d2246ddcc7dbf14aa5ae08b40a0b983688812d792f839`
- Source builder: `workspace/public/src/scripts/revalidation/build_native_init_boot_v2182_hud_menu_cleanup.py`
- Source/build report: `docs/reports/NATIVE_INIT_V2182_HUD_MENU_CLEANUP_SOURCE_BUILD_2026-06-09.md`
- Immediate rollback image: `workspace/private/inputs/boot_images/boot_linux_v2178_wifi_profile_autoconnect.img`
- Rollback SHA256: `8ea6f468f997446e9fa3e80606db107ca27d067f3ee023ff45c2ecf159341047`
- Decision: `v2183-v2182-hud-menu-cleanup-baseline-promoted`
- Result: PASS

## Scope Promoted

V2182 keeps the V2178 Wi-Fi profile/autoconnect baseline and promotes the UI/HUD cleanup as the current rollback/test baseline:

- HUD storage line now shows backend, free bytes, free percent, and read/write rate snapshots.
- HUD Wi-Fi line surfaces profile/autoconnect decisions and runtime Wi-Fi status without exposing secrets.
- HUD status geometry is centralized as a six-row layout so menu/log/preview screens do not overlap the HUD.
- Main menu removes duplicate `STATUS` / `LIVE STATUS` entries and clarifies `USB NET STATUS` versus Wi-Fi HUD status.
- Display test preview text now describes the current HUD summary plus log-tail structure.

## Live Evidence

Evidence directory:

- `workspace/private/runs/ui/v2182-hud-menu-cleanup-live-20260609-083432`

Observed checks:

| Check | Result |
| --- | --- |
| V2182 flash local marker | PASS: local image contained `A90 Linux init 0.9.255 (v2182-hud-menu-cleanup)` |
| V2182 flash SHA | PASS: local, remote, and boot readback SHA matched `8e3e16f68d019ef5f56d2246ddcc7dbf14aa5ae08b40a0b983688812d792f839` |
| V2182 boot verify | PASS: `cmdv1 version` and `cmdv1 status` rc=0/status=ok |
| `statushud` | PASS: framebuffer presented at `1080x2400` on CRTC `133` |
| `screenmenu` | PASS: background HUD menu show request accepted |
| `watchhud 1 2` | PASS: framebuffer presented twice |
| V2182 selftest | PASS: `selftest fail=0` in V2182 status/selftest evidence |
| V2178 rollback | PASS: boot readback SHA matched `8ea6f468f997446e9fa3e80606db107ca27d067f3ee023ff45c2ecf159341047` |
| V2178 rollback boot verify | PASS: `A90 Linux init 0.9.253 (v2178-wifi-profile-autoconnect)` rc=0/status=ok |
| Final baseline flash | PASS: V2182 reflashed as the current baseline; boot readback SHA matched and `status` reported `selftest fail=0` |

## Notes

- The live UI validation did not perform OCR or screenshot analysis. It verified the KMS presentation path and command success for the HUD/menu surfaces.
- One post-rollback raw `a90ctl selftest verbose` attempt hit serial `AT` noise and missed the A90P1 END marker; the recovered transport path returned rc=0, and `status` independently reported `selftest fail=0`.
- V2178 remains the immediate rollback image for this promotion because it is the previous verified Wi-Fi profile/autoconnect baseline.

## Safety Scope

- No credentials, Wi-Fi scan/connect/DHCP/external ping, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or firmware/partition content writes were part of this UI promotion.
- Boot flashing was limited to rollbackable native-init boot image swaps through TWRP and boot partition readback verification.
- Private artifacts remain under `workspace/private/` and are not tracked.
