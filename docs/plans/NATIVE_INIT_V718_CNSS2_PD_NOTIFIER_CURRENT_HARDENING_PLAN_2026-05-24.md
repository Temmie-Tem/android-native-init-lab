# Native Init V718 CNSS2 PD-Notifier Current-Boot Hardening Plan

- date: `2026-05-24 KST`
- scope: read-only current-boot CNSS2/WLAN-PD classifier hardening
- runner: `scripts/revalidation/native_wifi_cnss2_pd_notifier_readonly_v706.py`
- approval phrase accepted by runner: `approve v666 cnss2 pd-notifier firing check and modem subsys state read; no Wi-Fi HAL start, no scan/connect, no DHCP, no external ping`

## Reason

The next Wi-Fi blocker is the gap between userspace-visible service-notifier
`180/74` and actual CNSS2/ICNSS progression into QCA6390 WLFW service `69`.
The useful causal chain is:

```text
modem ONLINE
  -> service-locator can resolve WLAN-PD
    -> service-notifier 180/74 appears
      -> kernel ICNSS/CNSS2 notifier should fire
        -> QCA6390 power/MHI/WLFW progresses
          -> service 69 / BDF / fw_ready / wlan0
```

V717 proved the helper window is not simply too short: service `180/74`,
provider registration, and CNSS retry were present for `30s`, but WLFW/BDF
and `wlan0` stayed absent.

## Problem Found

The first V718 rerun of the V706 read-only classifier was itself unsafe for
interpretation:

- the native menu was active;
- every read-only capture returned `[busy]`;
- the script still classified the run as `v706-service180-absent-current-boot`.

That is a harness bug. Busy captures must be treated as a blocked evidence
collection, not as negative CNSS2 evidence.

## Changes

Patch the V706 runner before using it as the V718 gate:

1. issue a bounded `hide` command before read-only collection;
2. record `busy_steps` and `failed_steps` in the manifest surface;
3. block interpretation when essential captures are busy/incomplete;
4. keep optional missing sysfs paths as evidence, not hard failures;
5. narrow QCA power/MHI dmesg patterns so PMIC power-on and generic PCIe logs
   are not counted as QCA6390 progress.

## Allowed

- `status`, `selftest`
- read-only `cat`, `ls`, `/proc/net/*`, and `dmesg`
- bounded `hide` to clear the on-device menu before read-only collection

## Forbidden

- Wi-Fi HAL, `wificond`, supplicant, or hostapd start
- scan/connect/link-up
- credential use
- DHCP, route change, external ping
- sysfs writes, subsystem state writes, `esoc0` open/hold
- boot image or partition write

## Success Criteria

- `python3 -m py_compile` passes for the patched runner.
- Plan/preflight still work without live mutation.
- Live read-only run has no `busy_steps` or essential `failed_steps`.
- The manifest accurately reports current service `180/74`, pd-notifier,
  QCA power/MHI, WLFW/BDF, `wlan0`, and modem subsystem state.

## Expected Next Decision

- If service `180/74` is absent in the current boot, do not retry CNSS/HAL;
  restore lower modem/WLAN-PD readiness first.
- If service `180/74` is present but no kernel pd-notifier/power markers
  follow, target ICNSS/CNSS2 notifier registration.
- If QCA/WLFW progresses, move to a separate wlan0-readiness gate before any
  scan/connect.
