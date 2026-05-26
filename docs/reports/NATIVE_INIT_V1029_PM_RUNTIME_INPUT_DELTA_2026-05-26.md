# V1029 PM Runtime Input Delta

- date: `2026-05-26`
- scope: host-only classifier
- decision: `v1029-pm-actor-selinux-runtime-domain-gap-classified`
- pass: `True`
- evidence: `tmp/wifi/v1029-pm-runtime-input-delta/manifest.json`

## Summary

V1029 classifies the V1028 `pm_proxy_helper` modem-get blocker as a PM actor
runtime-domain gap. Android runs the PM actors in vendor SELinux domains while
holding the required fd contract. Native V1027 requests the matching target
contexts, but captured `attr/current` remains `kernel`.

## Findings

Android V1024 evidence:

| Actor | Android domain | FD |
| --- | --- | --- |
| `pm_proxy_helper` | `u:r:per_proxy_helper:s0` | `/dev/subsys_modem` |
| `pm-service` | `u:r:vendor_per_mgr:s0` | `/dev/subsys_modem` |
| `pm-proxy` | `u:r:vendor_per_proxy:s0` | n/a |
| `mdm_helper` | `u:r:vendor_mdm_helper:s0` | `/dev/esoc-0` |

Native V1027 evidence:

| Actor | Requested target | `setexeccon` | Runtime capture |
| --- | --- | --- | --- |
| `pm_proxy_helper` | `u:r:per_proxy_helper:s0` | `ok` | `kernel` |
| `pm-service` | `u:r:vendor_per_mgr:s0` | `ok` | `kernel` |
| `pm-proxy` | `u:r:vendor_per_mgr:s0` | `ok` | `kernel` |
| `mdm_helper` | `u:r:vendor_mdm_helper:s0` | `ok` | `kernel` |

The native fd delta remains:

| Signal | Value |
| --- | --- |
| `pm_proxy_helper_subsys_modem_fd_count` | `0` |
| `per_mgr_subsys_modem_fd_count` | `0` |
| `mdm_helper_esoc0_fd_count` | `1` |

V1027 dmesg still shows `pm_proxy_helper` entering modem subsystem-get and PIL
loading before the fd predicate appears:

```text
[ 2379.619475]  [3:pm_proxy_helper:  613] subsys-restart: __subsystem_get(): __subsystem_get: modem count:0
[ 2379.619489]  [3:pm_proxy_helper:  613] subsys-restart: __subsystem_get(): Changing subsys fw_name to modem
[ 2379.621691]  [0:pm_proxy_helper:  613] subsys-pil-tz 4080000.qcom,mss: modem: loading from 0x000000008d800000 to 0x0000000097800000
```

## Interpretation

The remaining gap is not the basic PM init-contract model. V863 captured the
`vendor.per_proxy_helper` rc contract, and the current helper already includes
the `pm_proxy_helper` child, `per_mgr` `ioprio rt 4`, and lifecycle marker
support.

The actionable blocker is that native PM actors are not proven to run in the
same runtime SELinux domains as Android. Repeating V1027 unchanged risks the
same `pm_proxy_helper` D-state/reboot-cleanup path without improving the fd
predicate.

## Guardrails

- Host-only classifier.
- No device command, actor start, daemon start, Wi-Fi HAL, `wificond`,
  scan/connect, credential use, DHCP/route, external ping, eSoC ioctl,
  `/dev/subsys_esoc0` open, GPIO/sysfs/debugfs write, boot image write, or
  partition write occurred in V1029.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_runtime_input_delta_v1029.py
python3 scripts/revalidation/native_wifi_pm_runtime_input_delta_v1029.py run
```

Result:

```text
decision: v1029-pm-actor-selinux-runtime-domain-gap-classified
pass: True
```

## Next

V1030 should be source/build-only support for a fail-closed PM actor
runtime-domain proof. The helper should verify that PM actors actually leave
`kernel` context before any PM full-contract fd gate, post-provider retry,
CNSS/Wi-Fi surface, scan/connect, or external ping attempt.
