# Native Init V1330 Android Timing Recapture Plan

## Summary

- Cycle: `V1330`
- Type: plan-only, no live execution
- Decision: `v1330-focused-android-readonly-timing-recapture-plan-ready`
- Result: PASS
- Inputs:
  - `tmp/wifi/v1329-android-only-sdx50m-prereq-classifier/manifest.json`
  - `tmp/wifi/v1328-mdm2ap-timing-sampler-live/manifest.json`
  - `tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json`
  - `tmp/wifi/v896-android-mdm-helper-image-contract-validate/manifest.json`
  - `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/manifest.json`
- Reuse candidates:
  - `scripts/revalidation/android_mdm_helper_timing_handoff_v622.py`
  - `scripts/revalidation/native_wifi_android_mdm_helper_timing_recapture_v622.py`

V1329 closes the host-only reconciliation step: native can reproduce the late
`per_proxy`/`mdm_helper`/`pm-service` path and hold `mdm_subsys_powerup`, but the
full V1328 timing window still has no GPIO142/MDM2AP response, no MDM errfatal
IRQ, no PCIe RC1, no MHI/ks, no WLFW/BDF, and no `wlan0`. Android-positive
evidence has that downstream chain, and existing evidence appears to place PCIe
L0 before the captured `pm-service` eSoC timestamp.

The next useful step is a focused Android read-only recapture with one coherent
timeline. Do not start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes,
ping externally, write PMIC/GPIO/GDSC/eSoC state, or mutate native boot images
inside this plan.

## Objective

Build a V1331 Android read-only collector/handoff that answers one question:

> In Android, what is the earliest observable event that precedes SDX50M
> response: `per_mgr`/`per_proxy`, `mdm_helper`, `__subsystem_get(esoc0)`,
> GPIO142, PCIe RC1, MHI pipe, or `ks`?

The collector must avoid the previous ambiguity where a post-boot fd snapshot
timestamp was compared against kernel dmesg timestamps. V1331 should put all
kernel events on dmesg monotonic timestamps and keep init property boottimes as
a separately labelled clock source unless the script verifies they are directly
comparable.

## Data Contract

V1331 should collect, from Android only:

1. `getprop` snapshot
   - `sys.boot_completed`
   - `init.svc.vendor.per_mgr`
   - `init.svc.vendor.per_proxy`
   - `init.svc.vendor.per_proxy_helper`
   - `init.svc.vendor.mdm_launcher`
   - `init.svc.vendor.mdm_helper`
   - `init.svc.cnss-daemon`
   - `ro.boottime.*` for the same service set when present
2. dmesg markers with original timestamps
   - `subsys-restart`, `__subsystem_get`, `subsys_esoc0`, `subsys_modem`
   - `mdm_subsys_powerup`, `esoc0`, `SDX50M`
   - `ap2mdm`, `mdm2ap`, `errfatal`, GPIO135, GPIO142
   - `msm_pcie`, `PCIe RC1`, `LTSSM`, `L0`
   - `mhi`, `mhi_0305_01.01.00_pipe_10`, `ks`
   - `icnss`, `wlfw`, `BDF`, `FW ready`, `wlan0`
3. read-only process/fd snapshots after boot completion
   - `pm-service`, `per_proxy`, `per_proxy_helper`
   - `mdm_helper`, `ks`
   - fds pointing at `/dev/subsys_esoc0`, `/dev/esoc-0`, and
     `/dev/mhi_0305_01.01.00_pipe_10`
4. read-only interrupt snapshot
   - `/proc/interrupts` lines matching MDM status, MDM errfatal, GPIO142, or
     related eSoC status lines

## Success Criteria

V1331 should pass if it captures:

- Android `sys.boot_completed=1`
- at least one Android-positive response marker: GPIO142, PCIe RC1/L0, MHI,
  WLFW/BDF, or `wlan0`
- the first dmesg timestamp for `__subsystem_get(esoc0)` if available
- the first dmesg timestamp for PCIe RC1/L0 if available
- `ks`/MHI pipe presence or absence after boot completion
- an explicit decision that classifies the ordering as one of:
  - `android-pcie-after-subsys-esoc0`
  - `android-pcie-before-captured-subsys-esoc0`
  - `android-esoc0-marker-missing-but-response-present`
  - `android-response-chain-missing`
  - `android-clock-source-incomparable`

`android-pcie-before-captured-subsys-esoc0` is not by itself a failure. It means
the previous captured `pm-service` eSoC timestamp was not the earliest trigger
and V1332 should classify earlier Android init/provider actions.

## Guardrails

- Android boot handoff is allowed only for the recapture runner that explicitly
  restores the native boot image afterward and verifies rollback.
- The collector itself is read-only.
- No Wi-Fi HAL start, scan/connect/link-up, credentials, DHCP/routes, or
  external ping.
- No native PMIC/GPIO/GDSC/eSoC write, direct eSoC ioctl/notify, blind
  `BOOT_DONE`, flash outside the approved Android-handoff/rollback wrapper, or
  partition write.
- No broad repo or binary scans that are unrelated to the V1331 evidence keys.

## Next

V1331 should implement the Android read-only collector/handoff by extending the
V622 pattern, but with the V1330 marker list and clock-source classification.
Only after V1331 produces a coherent Android ordering should native lower-level
experiments resume.
