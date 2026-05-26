# V1000 Android eSoC/GPIO Recapture Handoff Live Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| V913 handoff live under V1000 output path | `tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/manifest.json` | `v913-handoff-collector-failed-rollback-complete` |
| V913 Android collector | `tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/v913-android-esoc-gpio-timeline-run/manifest.json` | `v913-android-esoc-gpio-timeline-incomplete` |

The live handoff executed and restored native v724. The collector failed its
older "complete positive timeline" criteria because BDF, `wlan0`, `ks`, MHI,
and GPIO142 IRQ-positive markers were not present. The run still produced useful
Android-positive lower timing evidence.

## Handoff Health

- Android boot-complete: PASS.
- Android read-only collector executed.
- Native rollback: PASS.
- Post-rollback native health:
  - `boot: BOOT OK shell 4.2s`
  - `selftest: pass=11 warn=1 fail=0`
  - exposure guard OK, NCM absent, TCP services stopped.
- Wi-Fi bring-up, credential use, DHCP/routing, and external ping were not
  executed.

## Captured Android Timeline

| Marker | Time | Evidence |
| --- | ---: | --- |
| MDM3 GPIO request block | `0.865s` | GPIO135, GPIO141, GPIO142, GPIO53 requested |
| AP2MDM config marker | `0.865262s` | `mdm_configure_ipc set AP2MDM_ERRFATAL2` |
| Wi-Fi HAL legacy start | `6.854689s` | `vendor.wifi_hal_legacy` |
| Wi-Fi HAL ext start | `6.965385s` | `vendor.wifi_hal_ext` |
| `wificond` start | `8.147853s` | `init: starting service 'wificond'` |
| `vendor.mdm_helper` start | `8.256167s` | `init: starting service 'vendor.mdm_helper'` |
| `cnss-daemon` start | `8.263292s` | `init: starting service 'cnss-daemon'` |
| `/dev/subsys_esoc0` get | `8.426630s` | `__subsystem_get: esoc0 count:0` |
| `cnss-daemon wlfw_start` | `8.434392s` | `cnss-daemon wlfw_start: Starting` |
| WLAN-PD indication | `9.448181s` | `msm/modem/wlan_pd` |
| ICNSS QMI connected | `9.450701s` | `icnss_qmi: QMI Server Connected` |

This current Android boot differs from the earlier V966 interpretation: in this
capture, `/dev/subsys_esoc0` get appears about `7.762ms` before
`cnss-daemon wlfw_start`, not after it.

## GPIO / eSoC Surface

- `/sys/kernel/debug/gpio` was readable.
- GPIO135/AP-side line snapshot: `gpio135 : out 0 16mA no pull`.
- GPIO142/MDM status snapshot: `gpio142 : in 0 8mA no pull`.
- PMIC GPIO9 appeared in the PMIC pinctrl snapshot.
- `/proc/interrupts` exposed `msmgpio-dc 142 Edge mdm status`, count `0`.
- `subsys9/state` was `OFFLINING`.
- `esoc0` sysfs exposed `DRIVER=mdm-4x` and
  `OF_COMPATIBLE_0=qcom,ext-sdx50m`.

## Process / FD Surface

- `mdm_helper` ran as `u:r:vendor_mdm_helper:s0`.
- `mdm_helper` held `/dev/esoc-0`.
- `cnss-daemon` ran as `u:r:vendor_wcnss_service:s0`.
- `wificond` ran as `u:r:wificond:s0`.
- Wi-Fi HAL legacy/ext services ran as `u:r:hal_wifi_default:s0`.
- No `/vendor/bin/ks` or MHI pipe was observed during this bounded capture.

## Interpretation

V1000 is not a full Android Wi-Fi-positive boot proof. It is a lower timing
recapture. The important new fact is that the current Android boot can reach
`wlfw_start`, WLAN-PD, and ICNSS QMI while:

- `subsys9/state` is still sampled as `OFFLINING`;
- GPIO142 interrupt count remains `0`;
- `ks` and MHI pipe are not observed;
- BDF and `wlan0` are not present in this short no-scan/no-connect window.

Therefore the next native route should not require post-boot `mdm3=ONLINE`,
GPIO142 IRQ-positive, `ks`, MHI, BDF, or `wlan0` as preconditions for trying to
reproduce the Android lower service window. The next step should first compare
V1000 against V998/V918/V923/V964 to decide whether the native fail-closed gate
was too strict around `/dev/subsys_esoc0` ordering.

## Guardrails

- Android userspace actions were read-only.
- No Wi-Fi scan/connect/link-up.
- No credential use.
- No DHCP, route mutation, or external ping.
- No GPIO/sysfs/debugfs write.
- No native eSoC ioctl.
- No native `/dev/subsys_esoc0` trigger.
- Boot partition was temporarily written for Android handoff and then restored
  to native v724 by the wrapper.

## Validation

Executed:

```bash
python3 scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py \
  --out-dir tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
python3 scripts/revalidation/a90ctl.py bootstatus
python3 scripts/revalidation/a90ctl.py exposure
```

Result:

```text
decision: v913-handoff-collector-failed-rollback-complete
pass: False
reason: V913 Android timeline collector failed, and native rollback steps completed
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

## Next

Plan V1001 as a host-only comparator over:

- V1000 Android current timing;
- V998 post-SELinux service-window no-WLFW;
- V918/V964 `sdx50m_toggle_soft_reset` stalls;
- V923 fail-closed CNSS-before-eSoC gate;
- V966/V968 older Android timing assumptions.

The decision should explicitly answer whether the next live native gate should
allow `/dev/subsys_esoc0` only inside the fully repaired service-window actor
set, or whether a different missing precondition must be proven first.
