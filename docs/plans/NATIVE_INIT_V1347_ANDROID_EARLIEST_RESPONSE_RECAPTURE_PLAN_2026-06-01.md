# Native Init V1347 — Android Earliest Response Recapture Plan

- Date: 2026-06-01
- Cycle: `V1347` (project axis; boot image handoff only for observation)
- Native rollback image: `stage3/boot_linux_v724.img`
- Android boot candidate: discovered from `backups/baseline_*/boot.img`
- Type: bounded Android handoff + read-only lower-response recapture
- Status: PLAN

## Goal

V1346 selected an Android read-only recapture because V1345 proves the current
native provider-ready private `SDX50M` route reaches `mdm_subsys_powerup` with
no lower transition, while the Android-positive reference still lacks enough
PCIe/MHI ordering detail on the same monotonic timeline.

V1347 should temporarily boot Android, collect the earliest SDX50M response
markers, then restore native v724 and verify health.

## Required Markers

Collect these read-only surfaces on one Android boot:

| Surface | Evidence |
| --- | --- |
| PM/provider/CNSS order | `getprop init.svc.*` and `ro.boottime.*` for `per_mgr`, `per_proxy`, `pm_proxy_helper`, `mdm_helper`, `cnss_diag`, `cnss-daemon`, QRTR/RFS/pd-mapper |
| eSoC trigger | dmesg markers for `__subsystem_get(esoc0)`, `/dev/subsys_esoc0`, and `mdm_subsys_powerup` |
| MDM2AP response | dmesg/interrupt markers for GPIO142, MDM status, errfatal/status IRQ |
| PCIe response | dmesg markers for RC1 reset, LTSSM, L0, current speed/lanes, and read-only `/sys/bus/pci/devices` surface |
| MHI/ks | dmesg `MHI`, process/fd scan for `ks`, `/dev/mhi_0305_01.01.00_pipe_10`, and read-only `/sys/bus/mhi/devices` surface |
| Wi-Fi lower publication | dmesg `wlfw`, BDF files, FW-ready, and `wlan0` netdev creation |

## Implementation

Add:

- `scripts/revalidation/native_wifi_android_earliest_response_recapture_v1347.py`
- `scripts/revalidation/android_earliest_response_handoff_v1347.py`

The collector is based on V1331 but extends capture to avoid the previous
tail-window blind spot:

- filtered dmesg without `tail`;
- early boot filtered dmesg from the first 2400 lines;
- existing unfiltered dmesg tail for context;
- process/fd scan for PM, `mdm_helper`, `ks`, CNSS;
- interrupt scan for GPIO/status/errfatal/PCIe/MHI;
- read-only PCIe/MHI/netdev sysfs surface.

## Decision Labels

| Decision | Meaning | Next |
| --- | --- | --- |
| `v1347-android-earliest-response-order-captured` | PCIe/MHI or MHI pipe evidence and WLFW/BDF/`wlan0` evidence are on the same record | classify exact Android-only prerequisite ordering against V1345 |
| `v1347-android-wlfw-before-subsys-esoc0` | Android still shows WLFW before captured eSoC marker, but PCIe/MHI ordering remains incomplete | host-only classify whether the captured eSoC marker is late/secondary |
| `v1347-android-response-chain-missing` | Android boot did not expose the expected lower response chain | recapture earlier or inspect Android boot state |
| `v1347-handoff-*-rollback-complete` | Android handoff failed but native rollback completed | inspect failure evidence before retry |

## Safety Contract

Allowed:

- temporary Android boot flash;
- Android read-only `adb shell su -c` commands;
- rollback flash to `stage3/boot_linux_v724.img`;
- native post-rollback `version`/health checks from the inherited handoff stack.

Blocked:

- Wi-Fi HAL start initiated by our tools;
- `wificond` start initiated by our tools;
- scan/connect/link-up;
- credential use;
- DHCP/routes;
- external ping;
- sysfs/debugfs writes;
- eSoC ioctl/notify/BOOT_DONE spoof;
- PMIC/GPIO/GDSC writes;
- boot image mutation outside the bounded Android handoff/rollback sequence.

The saved Wi-Fi SSID/password must not be used in V1347.

## Validation

Before live:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_android_earliest_response_recapture_v1347.py \
  scripts/revalidation/android_earliest_response_handoff_v1347.py
python3 scripts/revalidation/native_wifi_android_earliest_response_recapture_v1347.py plan
python3 scripts/revalidation/android_earliest_response_handoff_v1347.py plan
git diff --check
```

Live command:

```bash
python3 scripts/revalidation/android_earliest_response_handoff_v1347.py \
  --allow-android-boot-flash \
  --i-understand-native-rollback \
  --assume-yes \
  run
```
