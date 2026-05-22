# Native Init V644 Clean-DSP CNSS/WLFW Readback Plan

- date: `2026-05-23 KST`
- cycle: `v644`
- scope: bounded native live proof
- target: verify whether the V598/V625/V627 CNSS-including service `180` path
  still works under V641's clean-DSP state, and whether it moves service `74`,
  WLAN-PD, WLFW/QMI, BDF, or `wlan0`

## Background

V642 proved that clean-DSP + no-CNSS Android-order companion reaches QRTR
TX/`sysmon-qmi`, but not service-notifier. V643 then classified the safe
partial-positive gap:

- V642/V619 no-CNSS path: QRTR TX + `sysmon-qmi`, service-notifier absent;
- V598/V625/V627 CNSS-including path: service `180` appears, but service `74`,
  WLAN-PD, WLFW/QMI, BDF, and `wlan0` remain absent.

V644 therefore replays the CNSS-including V598-class path on top of V641's
clean-DSP state. This targets the next blocker while still staying below HAL,
scan/connect, credentials, DHCP, routes, and external ping.

## Guardrails

V644 must not:

- write ADSP/CDSP/SLPI boot nodes;
- open `esoc0`;
- write `boot_wlan`, `qcwlanstate`, or other WLAN driver-state sysfs nodes;
- start service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- change the boot image or write boot partitions.

## Implementation

Add `scripts/revalidation/native_wifi_clean_dsp_cnss_wlfw_readback_v644.py`.

The runner:

1. verifies native is `A90 Linux init 0.9.67 (v641)`;
2. verifies V641 clean-DSP proof log/timeline and current rpmsg state;
3. requires current-boot V490 policy-load proof;
4. requires helper v104;
5. reuses the V596/V598 firmware mount + `subsys_modem` holder path;
6. starts only the V598-class lower companion window:
   `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon`;
7. performs WLFW QRTR nameservice readback for service `69` instances `0/1`;
8. captures service `180`, service `74`, WLAN-PD, WLFW/QMI, BDF, `wlan0`, and
   kernel-warning markers;
9. uses reboot cleanup.

## Success Criteria

V644 passes diagnostically if it returns one of:

- `v644-post-180-advanced`: service `74`, WLAN-PD, WLFW/QMI, BDF, or `wlan0`
  moves forward;
- `v644-service180-only-clean-dsp`: service `180` is reproduced cleanly but
  service `74`/WLAN-PD/WLFW remains absent;
- `v644-cnss-no-service180-regression`: clean-DSP + helper v104 no longer
  reproduces service `180`, requiring helper/timing comparison.

V644 fails on kernel warnings, helper contract mismatch, QMI payload attempts,
cleanup failure, stale V490, missing clean-DSP state, or any forbidden Wi-Fi
bring-up action.

## Required Live Sequence

Because V642 reboot cleanup returns to an unarmed v641 boot, the live sequence
must be:

1. arm `/cache/native-init-sibling-fwssctl-v641`;
2. reboot into v641 clean-DSP state;
3. run `mountsystem ro`;
4. mount SELinuxfs through V401;
5. run current-boot V490 into `tmp/wifi/v644-v490-current-run/`;
6. run V644 preflight;
7. run V644 live proof.

## Next Gate

- If service `74`/WLAN-PD/WLFW advances, plan the smallest CNSS/HAL readiness
  gate with scan/connect still blocked.
- If service `180` only is reproduced, keep HAL/qcwlanstate blocked and
  classify the service `74`/WLAN-PD publisher gap under clean-DSP evidence.
- If service `180` regresses, compare helper v104 vs v100 and companion order
  before retrying live.
