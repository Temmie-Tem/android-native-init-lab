# Native Init V844 mdm3/ext-sdx50m Boot Interface Classifier Plan

## Goal

Correct the Wi-Fi bring-up architecture model using Samsung OSRC DTS and ICNSS
source evidence, then select the next safe gate for the missing WLFW service 69
publication.

## Scope

V844 is host-only. It reads existing V819/V823/V840/V843 evidence and local
Samsung OSRC source. It does not contact the device, send QRTR/QMI payloads,
open `esoc0`, write GPIO/sysfs/debugfs, start service-manager, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP, change routes, ping externally, write
boot images, write partitions, or flash a custom kernel.

## Inputs

- V843 current-window CNSS stall classifier:
  `tmp/wifi/v843-current-window-cnss-stall-classifier/manifest.json`
- V819 mdm3/eSoC registration catalogue:
  `tmp/wifi/v819-mdm3-esoc-registration-catalogue/manifest.json`
- V823 SSCTL nameservice matrix:
  `tmp/wifi/v823-ssctl-nameservice-matrix/manifest.json`
- V840 provider-first prearmed listener:
  `tmp/wifi/v840-provider-first-prearmed-listener-live/manifest.json`
- Samsung OSRC DTS:
  `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r02.dts`
- Samsung OSRC ICNSS source:
  `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c`
  and `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss_qmi.c`

## Classification Rules

V844 passes if:

1. V843 confirms the current native `cnss-daemon` retry is alive but still
   pre-WLFW.
2. V819/V823/V840 still show `mss` can reach `ONLINE`, while `mdm3` remains
   `OFFLINING` and WLFW/BDF/FW-ready/`wlan0` remain absent.
3. The r3q DTS identifies `qcom,mdm3` as `qcom,ext-sdx50m` with AP/MDM GPIO
   handshake, `qcom,ssctl-instance-id=<0x10>`, and `qcom,sysmon-id=<0x14>`.
4. ICNSS source shows service-notifier UP is not the initial boot trigger, while
   WLFW depends on QRTR service 69 arrival through `wlfw_new_server()`.
5. The selected next step is read-only classification of the mdm3/ext-sdx50m
   eSoC boot interface, not another listener/CNSS/HAL retry.

## Expected Decision

Expected result: `v844-mdm3-ext-sdx50m-boot-interface-selected`.

This means the immediate blocker is no longer modeled as an MPSS WLAN-PD timing
problem. The missing prerequisite is that the external mdm3/ext-sdx50m side does
not advance far enough to publish WLFW service 69.

## Next Gate

V845 should perform a read-only live snapshot of mdm3/ext-sdx50m eSoC GPIO and
sysfs surfaces. It must not open raw `esoc0`, write GPIO/sysfs, start Wi-Fi HAL,
scan/connect, run DHCP, change routes, ping externally, or write boot images.
