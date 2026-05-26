# V1044 PM/PIL Android GPIO/eSoC Classifier Plan

## Goal

Classify the current V1043 PM full-contract blocker against existing Android
GPIO/eSoC timing evidence without touching the device.

V1043 already proved current-boot SELinux domain parity for all PM actors, but
`pm_proxy_helper` still blocked before the `/dev/subsys_modem` fd predicate. The
open question is whether this is still a domain/ordering problem, or a lower
PIL/eSoC prerequisite that Android satisfies before the native path.

## Inputs

- V1043 native PM proof:
  `tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live/manifest.json`
- V1043 focused transcript:
  `tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live/native/mdm-helper-cnss-before-esoc.txt`
- V968 Android dmesg GPIO/eSoC timing classifier:
  `tmp/wifi/v968-android-dmesg-esoc-gpio-timing/manifest.json`
- V1024 Android PM/eSoC fd contract classifier:
  `tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json`
- V852 Android provider surface dmesg/interrupt/GPIO captures:
  `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/android/commands/`
- Classifier:
  `scripts/revalidation/native_wifi_pm_pil_android_gpio_esoc_classifier_v1044.py`

## Method

1. Confirm V1043 ran after V1042 policy refresh and matched the four PM actor
   SELinux domains.
2. Confirm V1043 started the PM actor order but never observed the
   `/dev/subsys_modem` fd contract.
3. Confirm V1043 captured `pm_proxy_helper` in D-state with
   `flush_work -> pil_boot -> subsys_powerup` stack evidence.
4. Confirm Android evidence shows the positive PM fd contract, GPIO135/142
   identity, PCIe RC1 link, WLAN-PD, ICNSS QMI, BDF, FW-ready, and `wlan0`.
5. Preserve the known limitation: existing Android dmesg/sysfs proves ordering,
   but not exact GPIO135 assert or PMIC GPIO9 deassert transition timing.

## Hard Gates

- Host-only classifier; no live device contact.
- No Android boot, ADB command, Magisk module, eSoC ioctl, `/dev/subsys_esoc0`
  open, actor start, daemon start, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, boot image write, partition write, firmware
  mutation, GPIO write, sysfs write, or debugfs write.

## Success Criteria

- The classifier writes private evidence under
  `tmp/wifi/v1044-pm-pil-android-gpio-esoc-classifier/`.
- The result proves V1043 fixed PM runtime-domain parity but failed below that
  at `pil_boot/subsys_powerup`.
- The result proves Android-good evidence has the positive PM/eSoC/Wi-Fi chain.
- The result routes the next step to a lower prerequisite delta, not a blind
  PM full-contract retry.

## Next

If classified, V1045 should identify the Android-only prerequisite that lets
`pm_proxy_helper` complete PIL/subsystem powerup. A bounded Android dmesg or
Magisk sampler is only justified if exact GPIO level transition timing becomes
necessary for that delta.
