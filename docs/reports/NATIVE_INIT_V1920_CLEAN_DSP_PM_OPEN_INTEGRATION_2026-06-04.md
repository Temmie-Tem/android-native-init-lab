# Native Init V1920 Clean-DSP PM-Open Integration

## Summary

- Cycle: `V1920`
- Decision: `v1920-service74-pm-open-post74-stall`
- Label: `service74-pm-open-post74-stall`
- Pass: `True`
- Reason: service74 and PM `/dev/subsys_modem` open coexisted, but WLAN-PD/WLFW69/wlanmdsp/wlan0 stayed absent
- Evidence: `tmp/wifi/v1920-clean-dsp-pm-open-integration`
- Inner handoff: `tmp/wifi/v1920-clean-dsp-pm-open-integration/v1847-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | service74-pm-open-post74-stall | service74 and PM `/dev/subsys_modem` open coexisted, but WLAN-PD/WLFW69/wlanmdsp/wlan0 stayed absent |
| hook/prearm/handoff | True / True / True | rollback=True |
| clean_dsp_seen | True | A90v641/sibling fwssctl text in handoff evidence |
| service180/service74 | True / True | 1,1,1 / 1,1,1 |
| pm_open | True | /dev/subsys_modem fd=0x8 |
| wlanpd/wlfw69/wlanmdsp/wlan0 | False / False / False / False | wlan_pd_counts=0,0,0 |

## Steps

- `pre-version` rc `0` ok `True` evidence `host/pre-version.txt`
- `pre-selftest` rc `0` ok `True` evidence `host/pre-selftest.txt`
- `pre-flags` rc `0` ok `True` evidence `host/pre-flags.txt`
- `arm-clean-dsp-flag` rc `0` ok `True` evidence `host/arm-clean-dsp-flag.txt`
- `cleanup-leftover-clean-dsp-flag` rc `1` ok `False` evidence `host/cleanup-leftover-clean-dsp-flag.txt`
- `post-mounts` rc `1` ok `False` evidence `host/post-mounts.txt`
- `post-selftest` rc `0` ok `True` evidence `host/post-selftest.txt`
- `post-status` rc `0` ok `True` evidence `host/post-status.txt`
- `manual-cleanup-flag` rc `0` ok `True` evidence `host/manual-cleanup-flag.txt`
- `manual-post-mounts` rc `0` ok `True` evidence `host/manual-post-mounts.txt`
- `manual-post-selftest` rc `0` ok `True` evidence `host/manual-post-selftest.txt`
- `manual-post-status` rc `0` ok `True` evidence `host/manual-post-status.txt`

## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V1847 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
