# V1044 PM/PIL Android GPIO/eSoC Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v1044-pm-pil-android-gpio-esoc-classifier/manifest.json` | `v1044-pm-pil-blocker-android-gpio-esoc-classified` |

V1044 confirms that V1043 is no longer blocked by PM actor SELinux context
parity. The remaining failure is lower: native `pm_proxy_helper` reaches
`pil_boot/subsys_powerup` and blocks before forming the `/dev/subsys_modem` fd
contract that Android shows.

## Evidence

- Classifier:
  `scripts/revalidation/native_wifi_pm_pil_android_gpio_esoc_classifier_v1044.py`
- Summary:
  `tmp/wifi/v1044-pm-pil-android-gpio-esoc-classifier/summary.md`
- Latest pointer:
  `tmp/wifi/latest-v1044-pm-pil-android-gpio-esoc-classifier.txt`

## Findings

- Native V1043:
  - PM runtime-domain guard did not block.
  - PM domain match count was `4`.
  - `pm_proxy_helper`, `pm-service`, `pm-proxy`, and `mdm_helper` were started.
  - `pm_proxy_helper` and `pm-service` kept `/dev/subsys_modem` fd count at `0`.
  - `mdm_helper` still held `/dev/esoc-0`, so the actor surface was present.
  - `pm_proxy_helper` was captured in D-state with `flush_work`, `pil_boot`, and
    `subsys_powerup` stack markers.
- Android positive controls:
  - V1024 proves `pm_proxy_helper -> /dev/subsys_modem`,
    `pm-service -> /dev/subsys_modem`, and `mdm_helper -> /dev/esoc-0`.
  - V968 proves Android dmesg ordering through GPIO135/142 request,
    `vendor.mdm_helper`, `cnss-daemon`, `/dev/subsys_esoc0` get, WLAN-PD,
    ICNSS QMI, BDF, FW-ready, and `wlan0`.
  - V852 adds direct PCIe RC1 link initialization evidence and a positive
    `mdm status` IRQ count in Android-good state.

## Interpretation

The Android dmesg path is sufficient to prove ordering and positive-path
correlation. It is not sufficient to prove exact GPIO135 HIGH or PMIC GPIO9
deassert transition timing; that remains a separate sampler problem.

For the current blocker, exact GPIO timing is not the next required action. The
more useful next gate is to classify what Android has before or during
`pm_proxy_helper` PIL/subsystem powerup that the native path still lacks.

## Guardrails

No device contact, Android boot, ADB command, Magisk module, eSoC ioctl,
`/dev/subsys_esoc0` open, actor start, daemon start, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, boot image write, partition write,
firmware mutation, GPIO write, sysfs write, or debugfs write occurred in V1044.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_pil_android_gpio_esoc_classifier_v1044.py
python3 scripts/revalidation/native_wifi_pm_pil_android_gpio_esoc_classifier_v1044.py
```

Result:

```text
decision: v1044-pm-pil-blocker-android-gpio-esoc-classified
pass: True
```

## Next

V1045 should be a host-only PM/PIL prerequisite delta classifier. It should not
repeat V1043 unchanged. If V1045 proves exact GPIO transition timing is the
remaining uncertainty, then use a bounded Android adb/Magisk sampler; otherwise
continue with the smaller source/evidence delta.
