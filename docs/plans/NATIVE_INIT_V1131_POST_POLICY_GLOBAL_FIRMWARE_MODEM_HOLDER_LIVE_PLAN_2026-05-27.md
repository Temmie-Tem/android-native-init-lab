# Native Init V1131 Post-policy Global Firmware Modem-holder Live Plan

Date: `2026-05-27`

## Objective

Run one bounded live gate that combines the current post-policy provider-positive
PM observer path with global firmware mounts and the helper `v213` scoped
`/dev/subsys_modem` pre-holder.

The question is narrow:

```text
V490 policy load
  -> global firmware mounts visible
  -> vendor.qcom.PeripheralManager provider visible
  -> cnss-daemon PM register/connect returns 0
  -> modem pre-holder confirms /dev/subsys_modem first-opener state
  -> mss/mdm3/WLFW/service69/wlan0 either advances or remains blocked
```

## Preconditions

- Helper `v213` is deployed:
  `docs/reports/NATIVE_INIT_V1131_EXECNS_HELPER_V213_DEPLOY_2026-05-27.md`
- Helper sha256:
  `d1c354b2b089ede50cc53d452666d119e9151b1e97b7bb1344dbd0431bd69356`
- Current boot has V401 selinuxfs and V490 policy-load preconditions refreshed.
- Native version remains `A90 Linux init 0.9.68 (v724)`.
- Native selftest has `fail=0`.

## Implementation

Runner:

```text
scripts/revalidation/native_wifi_post_policy_global_firmware_modem_holder_live_v1131.py
```

The runner reuses V1121 global firmware mount-only orchestration and overrides
the helper child command with:

```text
--pm-observer-start-cnss-before-per-proxy
--allow-pm-observer-modem-pre-holder
--pm-observer-modem-pre-holder
```

The V1130 helper implementation opens only:

```text
/dev/subsys_modem
```

with:

```text
O_RDONLY | O_NONBLOCK | O_CLOEXEC
```

Plain retry is disabled.

## Command

After V401/V490 are current on this boot, run:

```bash
python3 scripts/revalidation/native_wifi_post_policy_global_firmware_modem_holder_live_v1131.py \
  --allow-tracefs-mount \
  --allow-tracefs-write \
  --allow-vendor-mount \
  --allow-selinuxfs-mount \
  --allow-pm-service-trigger-observer \
  --allow-cnss-daemon-start \
  --assume-yes \
  run
```

## Success Criteria

- Firmware mount-only setup executes and both firmware targets are visible.
- Helper sha/marker is `v213`.
- Helper usage exposes both modem pre-holder flags.
- `pm_service_trigger_observer.modem_pre_holder_requested=1`.
- `pm_service_trigger_observer.modem_pre_holder_allowed=1`.
- `pm_service_trigger_observer.modem_pre_holder_start_attempted=1`.
- The result classifies whether the holder confirms and whether
  `mss`/`mdm3`/WLFW/service `69`/`wlan0` advance.
- Cleanup reboot restores native health if any PM actor or holder remains active.

## Guardrails

Do not execute:

```text
/dev/subsys_esoc0 open
eSoC ioctl/control
Wi-Fi HAL start
scan/connect/link-up
SSID/password use
DHCP/route changes
external ping
partition writes
boot image writes
flash
```

## Expected Branches

- `v1131-modem-holder-advances-wlfw-surface`:
  stop and capture BDF/fw-ready/interface state before any scan/connect.
- `v1131-modem-holder-confirmed-lower-state-still-blocked`:
  confirmed first-opener is not sufficient; next classify eSoC/mdm3 transition.
- `v1131-modem-holder-not-confirmed`:
  classify why `O_NONBLOCK` `/dev/subsys_modem` holder did not confirm.
- `v1131-forbidden-action-observed`:
  stop and audit helper output before any retry.
