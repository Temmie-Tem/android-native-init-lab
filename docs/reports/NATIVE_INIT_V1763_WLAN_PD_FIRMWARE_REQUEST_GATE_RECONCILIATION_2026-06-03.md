# Native Init V1763 WLAN-PD Firmware-request Gate Reconciliation

## Summary

- Cycle: `V1763`
- Type: host-only reconciliation of the active WLAN-PD firmware-request directive
- Decision: `v1763-v1739-equivalent-firmware-request-gate-closed-host-pass`
- Label: `firmware-not-requested`
- Result: PASS
- Reason: V1753 already ran the V1739-equivalent Android-good/native firmware-request gate; the fixed label is firmware-not-requested
- Evidence: `tmp/wifi/v1763-wlan-pd-firmware-request-gate-reconciliation`

## Gate Status

- The current directive asks for the Android-good firmware-request capture and the native V1736 SM-route comparison.
- That exact discriminator is already present as V1753 and must not be rerun without a new reason, because the contract says one run sets one label.
- Fixed label: `firmware-not-requested`.

## Android-good Evidence

- Manifest: `tmp/wifi/v1753-android-good-wlan-pd-firmware-request/manifest.json`
- Decision/pass: `v1753-android-good-firmware-request-observed-rollback-pass` / `True`
- requested `wlanmdsp`: `1`
- requested PD image: `1`
- trace lines: `{"cnss_daemon": 18, "rmt_storage": 126, "tftp_server": 890}`
- served/request paths: `["/vendor/firmware_mnt/image/wlanmdsp.mbn", "/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn", "/vendor/firmware/wlanmdsp.mbn", "/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn"]`

## Native V1736 SM-route Evidence

- Manifest: `tmp/wifi/v1736-wlan-pd-timestamped-observer-handoff/manifest.json`
- Decision/pass: `v1736-wlfw-start-reached-downstream-block-rollback-pass` / `True`
- service-manager / tftp running: `1` / `1`
- WLFW start/request/worker hits: `1` / `1` / `1`
- WLFW service 69 / requested `wlanmdsp`: `0` / `0`
- old firmware-serve label: `firmware-not-requested`

## Existing Diff

- Manifest: `tmp/wifi/v1753-wlan-pd-firmware-request-diff/manifest.json`
- Decision/pass: `v1753-firmware-not-requested-android-good-diff-pass` / `True`
- Label: `firmware-not-requested`
- Reason: Android-good tftp_server requests wlanmdsp.mbn, while the native V1736 service-manager route reaches the WLFW worker but never requests wlanmdsp
- Fresh native attempt: `{"decision": "v1736-test-boot-flash-or-verify-failed", "live_error": "tcpctl did not become ready: timed out", "manifest": "tmp/wifi/v1753-native-wlan-pd-firmware-request-sm-route/manifest.json", "pass": false, "present": true, "reason": "test boot flash/verify failed; live_error=tcpctl did not become ready: timed out", "rollback": {"attempt": "from-native", "ok": true}}`

## Superseded Follow-up Drift

- V1761: `{"present": true, "path": "tmp/wifi/v1761-wlan-pd-autoload-trigger-contract-classifier/manifest.json", "decision": "v1761-cnss-pm-service-object-gap-before-wlanmdsp-host-pass", "pass": true, "label": "pm-service-object-gap-before-wlanmdsp-request", "reason": "Android-good reaches PM register/vote before wlanmdsp request; native reaches WLFW request but stops at the PeripheralManager null-service-object path and never requests wlanmdsp"}`
- V1762: `{"present": true, "path": "tmp/wifi/v1762-wlan-pd-helper-contract-gap-classifier/manifest.json", "decision": "v1762-helper-needs-new-narrow-service-object-mode-source-pass", "pass": true, "label": "new-narrow-service-object-mode-needed", "reason": "current helper has V1736 SM-route and peripheral uprobes, but its PM route is a broad pm-trio path already falsified by V1686; no narrow service-object-visible mode exists"}`
- Treat the V1761/V1762 PM/service-object follow-up as superseded for now by the user's latest stop directive.
- Do not implement the V1762 narrow PM service-object helper mode in this unit.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, partition write, tracefs write, or new actor start.

## Next

- Stop after the `firmware-not-requested` label.
- The next legitimate work is a separately scoped modem-side WLAN-PD autoload/request-trigger analysis, but only after explicitly reconciling it with this latest stop directive.
- Do not return to route minimization, tracefs plumbing, PM actor expansion, QCACLD, eSoC/RC1, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping from this unit.
