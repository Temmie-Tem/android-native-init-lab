# Native Init V2190 V2189 Security P0 Stage Fix Baseline Promotion

## Summary

- Promoted baseline: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`.
- Promotion run: `V2190`.
- Promoted artifact tag: `v2189-security-p0-stage-fix`.
- Decision: `v2190-v2189-security-p0-stage-fix-baseline-promotion-pass`.
- Result: PASS.
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img`.
- Boot SHA256:
  `a7332612199cfd275f2dfc6fdb25843af401a1ecef2fa54ac0f52afe705f1ffe`.
- Previous baseline:
  `A90 Linux init 0.9.259 (v2187-screenapp-ui-validation)`.
- Emergency fallback:
  `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`.

## Evidence

- Source/build report:
  `docs/reports/NATIVE_INIT_V2189_SECURITY_P0_STAGE_FIX_SOURCE_BUILD_2026-06-10.md`.
- Live validation:
  `docs/reports/NATIVE_INIT_V2189_SECURITY_P0_STAGE_FIX_LIVE_VALIDATION_2026-06-10.md`.
- Promotion precheck:
  `docs/reports/NATIVE_INIT_V2189_PROMOTION_PRECHECK_2026-06-10.md`.
- Fresh local security scan:
  `docs/security/scans/SECURITY_FRESH_SCAN_V2189_2026-06-10.md`.

Live validation proved:

- caller-pinned flash SHA matched the local image;
- remote `/tmp/native_init_boot.img` SHA matched the pinned SHA;
- boot partition readback prefix SHA matched the pinned SHA;
- rebooted native init reported
  `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`;
- native selftest reported `fail=0` before and after the bounded Wi-Fi smoke;
- `/cache/a90-wifi` and staged standalone supplicant artifacts were root-owned
  with non-writable group/other bits;
- `wifi status` reported `supplicant.root_exec_ok=1`;
- bounded `wifi connect <profile>` reached carrier and `wpa_state=COMPLETED`;
- `wifi cleanup` completed.

Fresh security precheck proved:

- PASS `10`, WARN `1`, FAIL `0`;
- new implementation blocker from local scan: `0`;
- remaining warning is the intentional trusted-lab boundary for USB ACM,
  localhost bridge, and USB-local NCM tcpctl.

## Promotion Scope

V2190 promotes the already-built and live-validated V2189 artifact. It does not
change PID1 source, helper source, boot packaging, Wi-Fi behavior, or runtime
command semantics.

The promoted baseline includes:

- V2187 screenapp/UI validation behavior;
- V2188 flash artifact identity hardening;
- V2189 staged Wi-Fi executable ownership fix;
- V2189 explicit root-exec reporting for standalone supplicant paths;
- existing USB ACM bridge, USB NCM, tcpctl, Wi-Fi lifecycle, HUD/menu, and
  screenapp command contracts.

## Rollback And Fallback

- Current baseline/normal rollback target:
  `workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img`.
- Previous conservative rollback:
  `workspace/private/inputs/boot_images/boot_linux_v2187_screenapp_ui_validation.img`.
- Emergency transport fallback:
  `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`.
- Known-good early fallback:
  `workspace/private/inputs/boot_images/boot_linux_v48.img`.

## Accepted Risk

The accepted trusted-lab root-control boundary remains unchanged:

- USB ACM root shell is intentional for local rescue/control.
- Host serial bridge must remain localhost-bound unless an explicit new auth and
  threat model is designed.
- USB-local NCM/tcpctl must not be exposed on LAN or Wi-Fi.
- Wi-Fi credentials and raw captures remain under ignored private roots.

## Deferred Cleanup

Architecture cleanup is intentionally deferred after promotion:

- `A90_WIFI_TEST_BOOT` research scaffolding in `v724/90_main.inc.c`;
- active no-op modem/QRTR/SSCTL boot-call audit;
- builder monkeypatch/import tower refactor;
- stale `a90_config.h` default version comments;
- dead `v319/90_main.inc.c` cleanup.

These are maintainability debts, not V2190 promotion blockers.

## Decision

`v2189-security-p0-stage-fix` is promoted as the current native-init baseline by
V2190. Future normal rollback/test cycles should start from V2189 unless a test
explicitly validates an older image.
