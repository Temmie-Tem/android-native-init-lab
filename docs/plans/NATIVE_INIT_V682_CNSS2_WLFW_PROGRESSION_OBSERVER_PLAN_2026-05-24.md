# Native Init V682 cnss2/WLFW Progression Observer Plan

## Objective

Run one bounded current-boot observer that tests the V681 routing decision:
service-notifier `180/74` and CNSS retry are not sufficient unless cnss2/WLFW
progression moves toward WLFW service `69`, BDF download, firmware-ready, and
`wlan0`.

V682 reuses helper v112 and the V679 live arm instead of adding a new helper.
The difference is classification: the result is judged as cnss2/WLFW progression
or a confirmed pre-WLFW gap, not as a Binder debugfs result.

## Inputs

- helper: `/cache/bin/a90_android_execns_probe`
- expected helper marker: `a90_android_execns_probe v112`
- expected helper SHA256:
  `a2c72c4157f6ddf089a40b2a5310288f3f0390ceced1f423519dcb8c1a8cc643`
- runner: `scripts/revalidation/native_wifi_cnss2_wlfw_progression_observer_v682.py`
- reused live arm: `scripts/revalidation/native_wifi_v535_binder_registry_snapshot_v679.py`

## Allowed Live Actions

- V641 one-shot clean-DSP reboot.
- V401 SELinuxfs mount surface.
- V490 Android SELinux policy-load proof.
- Bounded helper v112 Android userspace-order start-only proof.
- Read-only cnss2/icnss/QCA6390 focused captures.
- WLFW QRTR nameservice readback without QMI payload.
- Runner-owned reboot cleanup.

## Forbidden Actions

- No supplicant or hostapd start.
- No Wi-Fi scan/connect/link-up.
- No credential use.
- No DHCP, route change, or external ping.
- No sysfs subsystem state write.
- No `esoc0` open or hold.
- No boot image or partition write.

## Success Criteria

V682 passes if one of these is true:

| decision | meaning |
| --- | --- |
| `v682-cnss2-wlfw-progressed` | WLFW/BDF/firmware-ready/`wlan0` marker moved; next gate can classify `wlan0` readiness |
| `v682-cnss2-wlfw-gap-confirmed` | service `74`, CNSS retry, and focused sysfs were observed, but WLFW/BDF/`wlan0` stayed absent; next gate isolates the missing cnss2/QMI trigger |

V682 fails if current-boot prerequisites, service `74`, CNSS retry, or focused
cnss2 sysfs capture are missing.

## Commands

```sh
python3 -m py_compile \
  scripts/revalidation/native_wifi_cnss2_wlfw_progression_observer_v682.py

python3 scripts/revalidation/native_wifi_cnss2_wlfw_progression_observer_v682.py \
  --out-dir tmp/wifi/v682-cnss2-wlfw-progression-observer-plan \
  plan

python3 scripts/revalidation/native_wifi_cnss2_wlfw_progression_observer_v682.py \
  --out-dir tmp/wifi/v682-cnss2-wlfw-progression-observer-live \
  --apply \
  --assume-yes \
  run
```

## Expected Routing

If V682 confirms the gap again, V683 should stop treating Binder debugfs as the
main path and instead isolate the missing cnss2/QMI trigger: QCA6390 power-on,
WLFW service publication, BDF transfer trigger, or the Android-only runtime edge
that causes those markers to appear.
