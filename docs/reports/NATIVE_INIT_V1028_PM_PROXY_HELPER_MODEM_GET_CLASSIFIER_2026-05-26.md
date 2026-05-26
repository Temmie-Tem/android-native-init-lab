# V1028 PM Proxy Helper Modem-Get Classifier

- date: `2026-05-26`
- scope: host-only classifier
- decision: `v1028-pm-proxy-helper-modem-get-blocker-classified`
- pass: `True`
- evidence: `tmp/wifi/v1028-pm-proxy-helper-modem-get-classifier/manifest.json`

## Summary

V1028 compares the Android-positive V1024 PM/eSoC fd contract with the native
V1027 PM full-contract live result. It classifies the remaining blocker as a
native `pm_proxy_helper` modem subsystem-get issue, not a missing process order
or a reason to retry the same live sequence.

## Findings

Android V1024 proves:

| Signal | Value |
| --- | --- |
| `pm_proxy_helper -> /dev/subsys_modem` | `True` |
| `pm-service -> /dev/subsys_modem` | `True` |
| `mdm_helper -> /dev/esoc-0` | `True` |
| WLFW/FW-ready/`wlan0` chain | `True` |

Native V1027 proves:

| Signal | Value |
| --- | --- |
| `pm_proxy_helper_start_executed` | `True` |
| `per_mgr_start_executed` | `True` |
| `pm_proxy_start_executed` | `True` |
| `mdm_helper_start_executed` | `True` |
| `pm_proxy_helper_subsys_modem_fd_count` | `0` |
| `per_mgr_subsys_modem_fd_count` | `0` |
| `mdm_helper_esoc0_fd_count` | `1` |
| `pm_full_contract_poll_count` | `54` |
| `pm_proxy_helper.postflight_safe` | `False` |
| `contract_result` | `reboot-required` |
| cleanup reboot | `True` |

The decisive native dmesg lines are:

```text
[ 2379.619475]  [3:pm_proxy_helper:  613] subsys-restart: __subsystem_get(): __subsystem_get: modem count:0
[ 2379.619489]  [3:pm_proxy_helper:  613] subsys-restart: __subsystem_get(): Changing subsys fw_name to modem
[ 2379.621691]  [0:pm_proxy_helper:  613] subsys-pil-tz 4080000.qcom,mss: modem: loading from 0x000000008d800000 to 0x0000000097800000
```

`post-ps` also shows:

```text
613 Ds    pm_proxy_helper             pm_proxy_helper
```

## Interpretation

The native sequence is no longer missing `pm_proxy_helper`, `pm-service`,
`pm-proxy`, or `mdm_helper`. V1027 starts those actors and observes
`mdm_helper` holding `/dev/esoc-0`.

The remaining blocker is earlier: `pm_proxy_helper` enters the modem
subsystem-get/PIL-loading path and becomes unsafe to stop before an observable
`/dev/subsys_modem` fd appears. Therefore the next unit should compare
Android/native `pm_proxy_helper` runtime inputs and service context rather than
retrying V1027 unchanged.

## Guardrails

- Host-only classifier.
- No device command, actor start, daemon start, Wi-Fi HAL, `wificond`,
  scan/connect, credential use, DHCP/route, external ping, eSoC ioctl,
  `/dev/subsys_esoc0` open, GPIO/sysfs/debugfs write, boot image write, or
  partition write occurred in V1028.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_proxy_helper_modem_get_classifier_v1028.py
python3 scripts/revalidation/native_wifi_pm_proxy_helper_modem_get_classifier_v1028.py run
```

Result:

```text
decision: v1028-pm-proxy-helper-modem-get-blocker-classified
pass: True
```

## Next

V1029 should be a host-only Android/native `pm_proxy_helper` runtime-input
delta. Inputs to compare include init service definition, user/group,
capabilities, SELinux domain, property/service state, firmware path visibility,
and any modem subsystem precondition visible before the Android fd contract
appears.
