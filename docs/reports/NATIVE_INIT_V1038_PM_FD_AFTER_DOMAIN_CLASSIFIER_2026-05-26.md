# V1038 PM fd Gap After Domain Proof

- date: `2026-05-26`
- scope: host-only classifier
- decision: `v1038-pm-fd-gap-after-domain-proof-classified`
- pass: `True`
- evidence: `tmp/wifi/v1038-pm-fd-after-domain-classifier/manifest.json`

## Summary

V1038 classifies the state after V1037:

1. V1036/V1037 removed the earlier PM runtime-domain blocker.
2. The PM fd contract still fails: `pm_proxy_helper` and `pm-service` do not
   hold `/dev/subsys_modem`.
3. A concrete Android/native parity bug remains in helper source:
   `pm-proxy` is still mapped to `u:r:vendor_per_mgr:s0`, while Android runs it
   as `u:r:vendor_per_proxy:s0`.

## Checks

| Check | Result |
| --- | --- |
| Android V1024 positive PM fd contract | pass |
| V1028/V1029 previous hypothesis present | pass |
| V1036 PM domains static-proven | pass |
| V1037 runtime-domain gap removed | pass |
| V1037 PM fd gap reproduced | pass |
| V1037 lower guardrails clean | pass |
| `pm-proxy` service-default context mismatch | pass |

## Android PM Contract

| Actor | Android domain | FD evidence |
| --- | --- | --- |
| `pm_proxy_helper` | `u:r:per_proxy_helper:s0` | `/dev/subsys_modem` |
| `pm-service` | `u:r:vendor_per_mgr:s0` | `/dev/subsys_modem` |
| `pm-proxy` | `u:r:vendor_per_proxy:s0` | process/domain present |
| `mdm_helper` | `u:r:vendor_mdm_helper:s0` | `/dev/esoc-0` |

## V1037 Native Delta

| Item | Value |
| --- | --- |
| runtime guard blocked | `False` |
| runtime guard matched count | `4` |
| `pm-proxy` expected context | `u:r:vendor_per_mgr:s0` |
| `pm-proxy` observed context | `u:r:vendor_per_mgr:s0` |
| `pm_proxy_helper` `/dev/subsys_modem` fd count | `0` |
| `pm-service` `/dev/subsys_modem` fd count | `0` |
| `mdm_helper` `/dev/esoc-0` fd count | `1` |
| PM full contract seen | `False` |
| service-manager started | `False` |
| `/dev/subsys_esoc0` open attempted | `False` |
| cleanup reboot | `True` |

## Interpretation

The V1029 domain-gap hypothesis is no longer sufficient. V1037 proves PM actor
runtime domains can match, but also proves the fd contract still does not form.

The shortest safe correction is source/build-only:

1. map `/vendor/bin/pm-proxy` to `u:r:vendor_per_proxy:s0`;
2. keep `/vendor/bin/pm-service` mapped to `u:r:vendor_per_mgr:s0`;
3. add focused PM fd/wchan capture around `pm_proxy_helper` and `pm-service`
   before another live retry;
4. keep service-manager/CNSS, subsystem open, Wi-Fi HAL, scan/connect, DHCP,
   credentials, and external ping gated.

## Guardrails

- no device command
- no device mutation
- no actor start
- no daemon start
- no Wi-Fi HAL start
- no scan/connect/link-up
- no credentials
- no DHCP, route, or external ping
- no eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write
- no boot image write or partition write

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_fd_after_domain_classifier_v1038.py
python3 scripts/revalidation/native_wifi_pm_fd_after_domain_classifier_v1038.py plan
python3 scripts/revalidation/native_wifi_pm_fd_after_domain_classifier_v1038.py run
```

Result:

```text
decision: v1038-pm-fd-gap-after-domain-proof-classified
pass: True
next: V1039 should source/build helper v177 with pm-proxy mapped to u:r:vendor_per_proxy:s0 and add focused PM fd/wchan capture before another bounded live retry
```

## Next

V1039 should be source/build-only helper `v177` support for PM proxy context
parity and focused PM fd/wchan capture. Do not run a new live PM actor retry
until that build artifact is validated.
