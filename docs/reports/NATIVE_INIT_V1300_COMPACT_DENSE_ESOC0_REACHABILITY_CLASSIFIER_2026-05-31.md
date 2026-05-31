# Native Init V1300 Compact Dense eSoC Reachability Classifier

## Summary

- Cycle: `V1300`
- Type: host-only classifier
- Decision: `v1300-v1299-esoc0-reached-manifest-false-negative`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1300-compact-dense-esoc0-reachability-classifier/manifest.json`
  - `tmp/wifi/v1300-compact-dense-esoc0-reachability-classifier/summary.md`

V1300 compares the V1295 verbose dense sampler and the V1299 compact dense sampler. It corrects the V1299 manifest interpretation: V1299 did reach `/dev/subsys_esoc0` / `mdm_subsys_powerup`, but the manifest classified it as no trigger because the compact loop omitted repeated syscall/kmsg probes and a blocked `openat("/dev/subsys_esoc0")` does not create a visible fd.

## Comparison

| run | decision | samples | ended | truncated | stdout_bytes | manifest_esoc0 | path_esoc0 | wchan_powerup | kmsg_esoc0 | fd_esoc0_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V1295 | `v1295-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required` | 14 | false | true | 1048576 | true | 58 | 69 | 56 | 0 |
| V1299 | `v1299-compact-dense-full-window-response-sampled-no-esoc0-trigger` | 42 | true | false | 778235 | false | 2 | 13 | 0 | 0 |

## Interpretation

- V1299 solved the stdout-cap problem: full compact dense window completed with 42 phases and no truncation.
- V1299 did not prove `pm-service` skipped `/dev/subsys_esoc0`; it proved the compact manifest used the wrong reachability signal.
- The fd-only signal is insufficient because a blocked open has no stable completed fd to count.
- The actual blocker remains after `mdm_subsys_powerup`: GPIO142 IRQ, PCIe/MHI, MHI pipe, `ks`, WLFW, and `wlan0` remain absent.

## Safety

- Host-only classifier; no bridge or device command was executed.
- No PM/CNSS actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, PMIC write, GPIO request/hold, direct eSoC ioctl, flash, boot image write, or partition write occurred.

## Next

V1301 should be source/build-only. Add a compact per-sample powerup marker to the live sampler so the next bounded run can record `/dev/subsys_esoc0` / `mdm_subsys_powerup` reachability without restoring the verbose syscall/kmsg blocks that hit the helper stdout cap.
