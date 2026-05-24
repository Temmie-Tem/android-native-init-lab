# Native Init V768 MDM3/ESOC Gap Classifier Plan

- date: `2026-05-25 KST`
- scope: host-only evidence classifier
- runner: `scripts/revalidation/native_wifi_mdm3_esoc_gap_classifier_v768.py`

## Goal

Reconcile the runtime `mdm_helper`/esoc/mdm3 evidence with the V767
instrumentation-build result, then choose the next Wi-Fi blocker gate without
repeating blind live starts.

## Inputs

- V620: `sysmon_esoc0` absence is a later state delta, not a proven first
  notifier prerequisite.
- V622: Android same-boot timing shows `mdm_helper` starts after service
  notifier `180`.
- V740: `mdm_helper` is only a bounded post-notifier candidate.
- V764: service180-gated `mdm_helper` starts but mdm3/WLFW/BDF/`wlan0` do not
  advance; `/dev/subsys_esoc0` is absent.
- V767: ICNSS/QCACLD instrumented objects compile with all 19 markers, but final
  `Image` is blocked by RKP_CFP Python2 host compatibility.

## Contract

- load existing manifest/report evidence only;
- classify repeat `mdm_helper`, raw esoc0, subsystem writes, boot_wlan retry,
  and instrumentation packaging candidates;
- preserve all Wi-Fi scan/connect/credential/DHCP/external-ping gates;
- write private evidence under `tmp/wifi/v768-mdm3-esoc-gap-classifier/`.

## Forbidden

- no device command;
- no service-manager, Wi-Fi HAL, companion, or `mdm_helper` start;
- no esoc0 open/hold;
- no subsystem state write, bind/unbind, or module load/unload;
- no boot image write, partition write, flash, or reboot;
- no Wi-Fi scan/connect, credential use, DHCP/routes, or external ping.

## Success Criteria

- V620/V622/V740/V764/V767 prerequisite decisions are current and passing.
- V764 proves `mdm_helper` started with no lower progress.
- V764 proves direct esoc0 char-device path is unavailable.
- V767 proves instrumentation object compile coverage.
- Next gate is selected from current evidence instead of operator preference.
