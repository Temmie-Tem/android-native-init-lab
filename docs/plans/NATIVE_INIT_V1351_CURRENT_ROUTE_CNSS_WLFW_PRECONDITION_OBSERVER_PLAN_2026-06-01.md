# Native Init V1351 — Current-route CNSS/WLFW Precondition Observer Plan

- Date: 2026-06-01
- Cycle: `V1351` (project axis; source/build-only first)
- Native build: `A90 Linux init 0.9.68 (v724)` (unchanged)
- Type: helper observer design plan
- Status: SOURCE/BUILD IMPLEMENTED

## Goal

V1350 superseded the old PM register blocker. The current route already reaches
`mdm_subsys_powerup`, but still sees no GPIO142, PCIe, MHI, WLFW, BDF, FW-ready,
or `wlan0`. Android V1347 reaches:

```text
cnss-daemon wlfw_start -> ICNSS QMI -> BDF -> FW-ready -> wlan0
```

V1351 should define a compact observer for the current provider-ready private
`SDX50M` route that answers the next narrow question:

> Does native `cnss-daemon` reach the same pre-`wlfw_start` runtime state as
> Android, and if not, which state is the last clean native checkpoint?

## Inputs

| Evidence | Role |
| --- | --- |
| `docs/reports/NATIVE_INIT_V1345_CURRENT_ROUTE_MDM2AP_TIMING_SAMPLER_LIVE_2026-06-01.md` | current route reaches `mdm_subsys_powerup` and records no lower response |
| `docs/reports/NATIVE_INIT_V1347_ANDROID_EARLIEST_RESPONSE_RECAPTURE_LIVE_2026-06-01.md` | Android positive WLFW/QMI/BDF/FW-ready/`wlan0` anchors |
| `docs/reports/NATIVE_INIT_V1350_PM_REGISTER_SUPERSESSION_CLASSIFIER_2026-06-01.md` | PM register blocker is superseded; current branch is CNSS/WLFW precondition |
| `stage3/linux_init/helpers/a90_android_execns_probe.c` | existing helper already has `cnss_before_esoc` and `cnss_userspace_readiness` primitives |

## Implementation Direction

V1351 should be source/build-only first. Extend
`stage3/linux_init/helpers/a90_android_execns_probe.c` minimally rather than
starting a new live gate immediately.

Add one compact observer mode or flag combination for the existing
`wifi-companion-pm-service-trigger-observer` route:

```text
current provider-ready private SDX50M route
  -> start PM/provider/CNSS actors as V1345 does
  -> keep current private cnss-daemon.sdx50m bind
  -> capture compact CNSS/WLFW precondition summary before/during mdm_subsys_powerup
  -> keep existing MDM2AP timing sampler
```

## Required New Output Keys

The output must be low-volume and parseable:

| key | meaning |
| --- | --- |
| `cnss_wlfw_pre.begin=1` / `end=1` | bounded section markers |
| `cnss_wlfw_pre.cnss_daemon_started=0|1` | `cnss-daemon` was spawned and observable |
| `cnss_wlfw_pre.cnss_diag_started=0|1` | `cnss_diag` was spawned and observable |
| `cnss_wlfw_pre.cld80211_seen=0|1` | native reached the generic netlink family surface |
| `cnss_wlfw_pre.pm_register_ret=...` | CNSS PM register return values, if observed |
| `cnss_wlfw_pre.pm_connect_ret=...` | CNSS PM connect return values, if observed |
| `cnss_wlfw_pre.wlfw_start_seen=0|1` | Android anchor `wlfw_start` appeared |
| `cnss_wlfw_pre.wlfw_service_request_seen=0|1` | WLFW service request thread marker appeared |
| `cnss_wlfw_pre.icnss_qmi_seen=0|1` | ICNSS QMI connected marker appeared |
| `cnss_wlfw_pre.bdf_seen=0|1` | BDF download marker appeared |
| `cnss_wlfw_pre.fw_ready_seen=0|1` | WLAN FW ready marker appeared |
| `cnss_wlfw_pre.wlan0_seen=0|1` | `wlan0` appeared |
| `cnss_wlfw_pre.last_checkpoint=...` | one of the decision checkpoints below |
| `cnss_wlfw_pre.safety_*` | Wi-Fi HAL, scan/connect, credential, DHCP/route, external ping all zero |

## Checkpoints

| Checkpoint | Meaning | Next |
| --- | --- | --- |
| `cnss-not-started` | helper route failed before CNSS userspace | repair actor order |
| `cnss-netlink-only` | native reaches `cld80211` but no PM connect or WLFW marker | inspect CNSS runtime/env/property delta |
| `pm-connect-ok-no-wlfw` | PM path succeeds but no `wlfw_start` | inspect `cnss-daemon` internal WLFW start branch |
| `wlfw-start-no-qmi` | `wlfw_start` appears but QMI does not connect | inspect WLFW/QMI service route |
| `qmi-no-bdf` | QMI connects but BDF is absent | inspect BDF/tftp/rfs path |
| `bdf-no-fw-ready` | BDF starts but FW-ready is absent | inspect firmware response path |
| `fw-ready-no-wlan0` | firmware-ready occurs but no netdev | inspect driver/netdev path |
| `wlan0-present` | lower Wi-Fi stack is ready for a separate scan/connect gate | plan credential-bearing Wi-Fi gate separately |

## Guardrails

Blocked in V1351 source/build and any later live observer:

- Wi-Fi scan/connect/link-up;
- credential use;
- DHCP/routes;
- external ping;
- Wi-Fi HAL start unless explicitly promoted in a separate later gate;
- PMIC/GPIO/GDSC writes;
- direct eSoC ioctl/notify/BOOT_DONE spoof;
- boot image or partition writes.

Allowed in later bounded live validation only after source/build review:

- existing current-route PM/provider/CNSS actor sequence;
- existing private `cnss-daemon.sdx50m` bind;
- existing read-only MDM2AP timing sampler;
- compact read-only dmesg/proc/fd/status summaries.

## Validation For Source/build-only Unit

When implementing V1351:

```bash
gcc/clang static helper build command used by the existing helper workflow
file stage3/linux_init/helpers/a90_android_execns_probe_vNNN
readelf -d stage3/linux_init/helpers/a90_android_execns_probe_vNNN | grep INTERP || true
strings stage3/linux_init/helpers/a90_android_execns_probe_vNNN | grep 'a90_android_execns_probe v'
python3 -m py_compile scripts/revalidation/native_wifi_current_route_cnss_wlfw_precondition_observer_live_v1351.py
python3 scripts/revalidation/native_wifi_current_route_cnss_wlfw_precondition_observer_live_v1351.py plan
git diff --check
```

No live execution should be bundled into the source/build commit.

## Source/build Result

Implemented as helper `a90_android_execns_probe v280` plus the host wrapper
`scripts/revalidation/native_wifi_current_route_cnss_wlfw_precondition_observer_live_v1351.py`.
The source/build result is documented in:

- `docs/reports/NATIVE_INIT_V1351_CURRENT_ROUTE_CNSS_WLFW_PRECONDITION_OBSERVER_SOURCE_BUILD_2026-06-01.md`
