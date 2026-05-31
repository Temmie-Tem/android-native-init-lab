# Native Init V1345 — Current Route MDM2AP Timing Sampler Plan

- Date: 2026-06-01
- Cycle: `V1345` (project axis; no boot image or partition write implied)
- Native build: `A90 Linux init 0.9.68 (v724)` (unchanged)
- Type: bounded live lower-response sampler plan
- Status: PLAN

## Goal

V1344 reconciled the current V1343 route with the prior lower-response record:

```text
private cnss-daemon.sdx50m
  -> CNSS registers SDX50M
  -> PM/eSoC path is reached
  -> no GPIO142 / PCIe / MHI / WLFW / wlan0 response
```

V1345 should run one current live sampler that combines:

1. the V1328 compact `mdm2ap_timing.*` sampler; and
2. the V1343/V1221 private `cnss-daemon.sdx50m` route.

The point is not to connect Wi-Fi yet. The point is to prove, with the current
helper/artifact route, exactly whether the lower SDX50M response window still
has no MDM2AP/GPIO142, PCIe RC1/LTSSM, MHI/`ks`, WLFW/BDF, or `wlan0`
transition.

## Current Facts

| Fact | Evidence |
| --- | --- |
| Current route reaches `SDX50M` + eSoC but not WLFW/`wlan0` | `docs/reports/NATIVE_INIT_V1343_PROVIDER_READY_SDX50M_ROUTE_LIVE_2026-06-01.md` |
| Current route matches post-AP2MDM response gap | `docs/reports/NATIVE_INIT_V1344_CURRENT_ROUTE_LOWER_RESPONSE_RECONCILIATION_2026-06-01.md` |
| Prior timing sampler already captures GPIO142/errfatal/PCIe/MHI/ks/WLFW/`wlan0` aggregate fields | `docs/reports/NATIVE_INIT_V1328_MDM2AP_TIMING_SAMPLER_LIVE_2026-05-31.md` |
| helper v279 contains both private SDX50M route and timing sampler support | `stage3/linux_init/helpers/a90_android_execns_probe.c` |

## Proposed Gate

Add `scripts/revalidation/native_wifi_current_route_mdm2ap_timing_sampler_live_v1345.py`.

Implementation should reuse the V1328/V1242 live sampler stack, but adjust the
child helper command to require the current private SDX50M route:

```text
--pm-observer-late-per-proxy-response-sampler
--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler
--pm-observer-private-cnss-daemon-sdx50m
--private-cnss-daemon-path /cache/bin/cnss-daemon.sdx50m
```

Required helper/artifact identity:

| Artifact | Expected |
| --- | --- |
| helper marker | `a90_android_execns_probe v279` |
| helper SHA256 | `2ec7c9584e0adb09755e1066ee01a986e3b7fd719c11b8a96aaf5c500d9dd15a` |
| private CNSS path | `/cache/bin/cnss-daemon.sdx50m` |
| private CNSS SHA256 | `784fd7bd9b602d8e1f94c9ceef977845909f452611025c40fda589d0e57de5fd` |

## Success Labels

| Decision | Meaning | Next |
| --- | --- | --- |
| `v1345-current-route-mdm2ap-progress` | GPIO142, errfatal IRQ, PCIe, MHI/`ks`, WLFW, or `wlan0` progressed | classify first progressed surface before Wi-Fi HAL/scan/connect |
| `v1345-current-route-mdm2ap-full-window-no-transition` | current route reaches `mdm_subsys_powerup`, but full timing window has no downstream response | classify Android-only SDX50M response prerequisite; no Wi-Fi HAL yet |
| `v1345-current-route-timing-missing` | timing block is incomplete | inspect helper output and avoid retrying blindly |
| `v1345-current-route-private-cnss-missing` | private `cnss-daemon.sdx50m` was not used | repair current route precondition |
| `v1345-current-route-safety-violation` | helper reports forbidden Wi-Fi/network/lower mutation action | stop and audit evidence |

## Safety Contract

V1345 may start bounded PM/CNSS/mdm_helper/per_proxy actors inside the existing
observer stack and may mount debugfs for read-only sampling if the reused V1242
sampler requires it.

Blocked:

- Wi-Fi HAL start.
- `wificond`.
- scan/connect/link-up.
- credential use.
- DHCP/routes.
- external ping.
- manual `/dev/subsys_esoc0` open outside the PM-service path.
- eSoC ioctl/notify/BOOT_DONE spoof.
- PMIC/GPIO/GDSC writes.
- boot image write, flash, or partition write.

Required cleanup:

- If the PM/eSoC path cannot prove process cleanup, reboot cleanup is acceptable
  and must be followed by `version`/`selftest` health evidence.

## Validation

Before live:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_current_route_mdm2ap_timing_sampler_live_v1345.py
python3 scripts/revalidation/native_wifi_current_route_mdm2ap_timing_sampler_live_v1345.py plan
git diff --check
run focused secret scan on new V1345 files
```

Live command:

```bash
python3 scripts/revalidation/native_wifi_current_route_mdm2ap_timing_sampler_live_v1345.py run
```

V1345 still must not use the stored Wi-Fi SSID/password or attempt external
connectivity. Those are only valid after lower readiness (`wlan0`/WLFW/BDF) is
proven by a separate gate.
