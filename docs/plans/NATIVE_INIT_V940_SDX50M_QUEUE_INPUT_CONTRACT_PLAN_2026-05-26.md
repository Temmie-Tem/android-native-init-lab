# V940 SDX50M Queue Input Contract Plan

## Goal

Classify why native `mdm_helper` reaches `/dev/esoc-0` but still reports
`unable to queue event for SDX50M`, while Android reaches WLAN-PD, WLFW, BDF,
and `wlan0`.

This is a host-only planning/classification gate. It does not start new actors
or retry eSoC triggers.

## Current Basis

- V938 proves the repaired runtime namespace has:
  - private property root;
  - `property_service` socket;
  - visible `/sys/bus/esoc` and `/sys/bus/msm_subsys`;
  - private `/dev/esoc-0` char node;
  - `mdm_helper` final `/dev/esoc-0` fd.
- V938 also proves native still has:
  - no `ks`;
  - no MHI pipe;
  - no WLFW/BDF/`wlan0`;
  - repeated `unable to queue event for SDX50M`.
- V939 closes exact `mdm_helper` property-context materialization as the first
  response. The exact keys are absent, but generic prefixes and runtime
  property surfaces are present, and Android's sampled lower post-boot shape
  is not sufficient to require current `ks`/MHI as success criteria.
- Earlier PM work shows `pm-service` / `pm-proxy` property denials were removed
  by V860, but Android-equivalent fd lifetime remained unproven.

## Questions

1. Is the SDX50M queue failure caused by missing PeripheralManager voter or
   provider registration state rather than property contexts?
2. Does `mdm_helper` expect `vendor.per_mgr` / `vendor.per_proxy` to be
   init-managed and alive at the moment it queues the SDX50M event?
3. Is the queue failure emitted before or after `/dev/esoc-0` fd acquisition?
4. Does V938 capture enough process/fd/timing evidence to answer the ordering,
   or does helper `v156` need narrower queue-timing instrumentation?
5. Does Android reference evidence already show a positive queue transition,
   or is a fresh V913 Android read-only recapture needed only for timing
   refresh?

## Inputs

- `tmp/wifi/v938-mdm-helper-lower-contract-capture-live/manifest.json`
- `tmp/wifi/v939-v938-lower-contract-classifier/manifest.json`
- `tmp/wifi/v914-v913-android-timeline-reclassifier/manifest.json`
- `docs/reports/NATIVE_INIT_V857_PM_SERVICE_PROPERTY_CONTRACT_2026-05-25.md`
- `docs/reports/NATIVE_INIT_V860_PM_SERVICE_PROPERTY_SUPERSET_2026-05-25.md`
- `docs/reports/NATIVE_INIT_V861_PM_SERVICE_DOMAIN_PARITY_2026-05-25.md`
- `docs/reports/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_2026-05-25.md`
- `docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md`
- `docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md`

## Method

1. Parse V938 actor surface:
   - `mdm_helper` pid;
   - fd acquisition phase;
   - queue-failure dmesg lines;
   - postflight actor cleanup;
   - `pm-service` / `per_mgr_light` lifetime markers.
2. Parse V857/V860/V861/V867 PM reports for already-closed blockers:
   - property-set permission;
   - property-context read gaps;
   - direct exec vs init service contract;
   - ioprio/lifecycle support;
   - known D-state risks.
3. Compare Android V914 positive path:
   - upper Wi-Fi markers remain the primary success target;
   - current `ks`/MHI/GPIO142 post-boot markers are diagnostics only.
4. Produce a host-only decision:
   - `pm-provider-lifetime-gap`;
   - `queue-timing-instrumentation-needed`;
   - `android-recapture-needed`;
   - or `safe-live-retry-preconditions-met`.

## Hard Gates

- No device command.
- No `pm-service`, `pm-proxy`, `mdm_helper`, `ks`, service-manager, CNSS, Wi-Fi
  HAL, wificond, supplicant, or hostapd start.
- No `/dev/subsys_esoc0` open.
- No eSoC ioctl.
- No GPIO/sysfs/debugfs write.
- No module load/unload.
- No scan/connect/link-up.
- No credential use.
- No DHCP/route mutation.
- No external ping.
- No boot image or partition write.

## Success Criteria

- Host-only classifier produces private evidence.
- The next live gate is selected from evidence rather than from property-context
  speculation.
- Property-context override, Magisk module, Android recapture, and eSoC trigger
  retry are each explicitly accepted or rejected for the next step.
- If new helper work is needed, its scope is source/build-only and narrower
  than another full runtime-contract replay.

## Expected Next

If V940 classifies a PM/provider lifetime gap, V941 should be source/build-only
helper support that captures `mdm_helper` queue timing against `pm-service`
provider/lifetime markers without starting Wi-Fi HAL or opening
`/dev/subsys_esoc0`.

If V940 proves the evidence is stale or insufficient, rerun the existing V913
Android read-only collector with a fresh output directory before modifying the
native helper.
