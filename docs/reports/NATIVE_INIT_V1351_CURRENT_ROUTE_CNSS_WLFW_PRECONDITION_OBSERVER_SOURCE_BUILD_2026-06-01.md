# Native Init V1351 — Current-route CNSS/WLFW Precondition Observer Source/build

- Date: 2026-06-01
- Cycle: `V1351`
- Native build: `A90 Linux init 0.9.68 (v724)` (unchanged)
- Type: source/build-only helper observer
- Result: PASS

## Summary

V1351 adds a compact `cnss_wlfw_pre.*` summary to the existing current-route
MDM2AP timing sampler. The new observer is gated by an explicit helper flag and
does not add a new live action path.

## Artifacts

| Artifact | Value |
| --- | --- |
| Helper source | `stage3/linux_init/helpers/a90_android_execns_probe.c` |
| Helper binary | `stage3/linux_init/helpers/a90_android_execns_probe_v280` |
| Helper marker | `a90_android_execns_probe v280` |
| Helper SHA256 | `509f7bb1eb599883d337afb167b29e271c3fe238e1bb1205fb9a93229263c278` |
| Host wrapper | `scripts/revalidation/native_wifi_current_route_cnss_wlfw_precondition_observer_live_v1351.py` |
| Plan manifest | `tmp/wifi/v1351-current-route-cnss-wlfw-precondition-observer-plan/manifest.json` |

## Helper Changes

- Added `--pm-observer-current-route-cnss-wlfw-precondition-summary`.
- The new flag requires the existing
  `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler` path.
- The helper emits `cnss_wlfw_pre.*` after the existing `mdm2ap_timing.*`
  summary, using the same bounded observation window.
- PM register/connect return values are emitted as `not-observed` until a later
  gate adds a safe direct return-value trace. This keeps V1351 non-invasive.

## Output Keys

The helper now emits:

```text
cnss_wlfw_pre.begin=1
cnss_wlfw_pre.mode=current-route-cnss-wlfw-precondition
cnss_wlfw_pre.sample_interval_ms=...
cnss_wlfw_pre.sample_count=...
cnss_wlfw_pre.cnss_daemon_started=0|1
cnss_wlfw_pre.cnss_diag_started=0|1
cnss_wlfw_pre.cld80211_seen=0|1
cnss_wlfw_pre.pm_register_ret=not-observed
cnss_wlfw_pre.pm_connect_ret=not-observed
cnss_wlfw_pre.wlfw_start_seen=0|1
cnss_wlfw_pre.wlfw_service_request_seen=0|1
cnss_wlfw_pre.icnss_qmi_seen=0|1
cnss_wlfw_pre.bdf_seen=0|1
cnss_wlfw_pre.fw_ready_seen=0|1
cnss_wlfw_pre.wlan0_seen=0|1
cnss_wlfw_pre.last_checkpoint=...
cnss_wlfw_pre.safety_*=0
cnss_wlfw_pre.end=1
```

## Guardrails

V1351 source/build and the later bounded live observer keep these blocked:

- Wi-Fi HAL start;
- scan/connect/link-up;
- credential handling;
- DHCP/routes;
- external ping;
- PMIC/GPIO/GDSC writes;
- direct eSoC ioctl/notify/BOOT_DONE spoof;
- boot image or partition writes.

## Validation

Executed:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh stage3/linux_init/helpers/a90_android_execns_probe_v280
python3 -m py_compile scripts/revalidation/native_wifi_current_route_cnss_wlfw_precondition_observer_live_v1351.py
python3 scripts/revalidation/native_wifi_current_route_cnss_wlfw_precondition_observer_live_v1351.py plan
git diff --check
secret scan over changed docs/scripts/helper source
```

Observed:

```text
stage3/linux_init/helpers/a90_android_execns_probe_v280: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
sha256: 509f7bb1eb599883d337afb167b29e271c3fe238e1bb1205fb9a93229263c278
dynamic section: none
v1351_decision: v1351-current-route-cnss-wlfw-precondition-plan-ready
v1351_pass: True
git diff --check: PASS
secret-scan: PASS
```

## Decision

`V1351` is ready for the next deploy/live gate. The next step is to deploy helper
`v280` and run the bounded live observer, still without Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, lower writes, or boot image writes.
