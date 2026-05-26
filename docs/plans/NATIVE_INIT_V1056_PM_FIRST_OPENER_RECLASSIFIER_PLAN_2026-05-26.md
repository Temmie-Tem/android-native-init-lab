# V1056 PM First-Opener Reclassifier Plan

## Goal

Reclassify the post-V1055 blocker without another live retry.

V1055 proved that a private-root modem pre-holder reaches the correct
`/dev/subsys_modem` node, but the nonblocking open returns `errno=14` and the
plain open does not return before the bounded window ends. The next question is
whether the V1045/V1047 model was too narrow: Android may not rely on a
pre-existing PM holder before `pm_proxy_helper`; it may successfully perform the
first modem open from a runtime state native does not yet reproduce.

## Inputs

- V1043 native PM full-contract blocker:
  `tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live/manifest.json`
- V1045 PM/PIL prerequisite classifier:
  `docs/reports/NATIVE_INIT_V1045_PM_PIL_PREREQUISITE_DELTA_2026-05-26.md`
- V1052 private-root repair live result:
  `tmp/wifi/v1052-pm-full-contract-with-modem-holder-live/manifest.json`
- V1055 helper `v180` plain fallback live result:
  `tmp/wifi/v1055-pm-full-contract-with-modem-holder-live/manifest.json`
- V1024 Android timing and fd positive control:
  `tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/v1022-late-android-pm-esoc-timing/manifest.json`
  and early `sample-loop.txt`
- Helper source:
  `stage3/linux_init/helpers/a90_android_execns_probe.c`
- Native v724 init source:
  `stage3/linux_init/v724/90_main.inc.c`

## Method

1. Parse V1055 for corrected node visibility, nonblocking `errno=14`, plain
   retry, missing holder confirmation, and missing PM fd contract.
2. Parse V1043 for the earlier native `pm_proxy_helper` first-opener block in
   `pil_boot/subsys_powerup/flush_work`.
3. Parse Android V1024 timing for:
   - `vendor.per_proxy_helper` start time;
   - `__subsystem_get(): modem count:0`;
   - later `__subsystem_get(): modem count:1`;
   - `vendor.per_mgr` start time.
4. Compare Android order with helper `v180` order. In Android,
   `vendor.per_proxy_helper` starts before `vendor.per_mgr`; therefore a
   synthetic pre-holder before `pm_proxy_helper` is not Android-faithful.
5. Produce a host-only manifest and summary with the next safest route.

## Success Criteria

- The classifier records that Android `pm_proxy_helper` starts while modem count
  is `0` and later reaches count `1`.
- The classifier records that native V1043/V1055 first-opener attempts remain
  blocked and do not form the PM fd contract.
- The decision explicitly rejects another same-order pre-holder retry.
- The next route is narrowed to first-opener runtime prerequisite analysis,
  especially firmware path/global mount and Android early-init state parity.

## Hard Gates

- Host-only. No device command, bridge command, Android boot, ADB command, or
  live actor start.
- No `/dev/subsys_modem`, `/dev/subsys_esoc0`, or `/dev/esoc-0` open.
- No eSoC ioctl, GPIO/sysfs/debugfs write, module load, boot image write,
  partition write, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_first_opener_reclassifier_v1056.py
python3 scripts/revalidation/native_wifi_pm_first_opener_reclassifier_v1056.py run
```

## Next

If V1056 classifies the blocker as Android count-zero first-open parity rather
than a missing holder, V1057 should be a read-only native/host classifier for
the lower first-open prerequisites:

1. `firmware_class.path`;
2. global and private firmware mounts;
3. `modem.b00`/`modem.mdt` visibility from the path used by PIL;
4. whether native has already perturbed the modem before the PM first-open
   window.

Do not rerun the same modem pre-holder live gate.
