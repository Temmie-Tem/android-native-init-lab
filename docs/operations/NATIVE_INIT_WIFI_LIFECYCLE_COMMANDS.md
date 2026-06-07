# Native Init Wi-Fi Lifecycle Commands

Date: `2026-06-08`

This is the operator-facing command contract for native-init Wi-Fi lifecycle
work. It keeps diagnostic/status commands separate from scan/connect/autoconnect
mutations.

## Current Command Surface

```text
wifi
wifi status
wifi scan [delay_ms]
wifi config status
wifi config prepare [profile]
```

## `wifi status`

`wifi status` is read-only and safe while the on-device menu is visible.

It reports:

- `wlan0_present`;
- `mac`, `operstate`, `carrier`, `flags`;
- `rx_bytes`, `tx_bytes`;
- current IPv4 address if one exists;
- redacted runtime summary fields from
  `/cache/native-init-wifi-runtime.summary`;
- standalone supplicant path, executable bit, process count, and control socket
  presence;
- `secret_values_logged=0`.

Missing `wlan0` is reported as `decision=wifi-status-wlan0-missing` but does not
make the status command fail. This keeps status usable as a pollable UI and
automation primitive.

## `wifi scan [delay_ms]`

`wifi scan` is a bounded, credential-free nl80211 scan primitive.

It:

- brings `wlan0` administratively up;
- resolves the `nl80211` generic-netlink family;
- sends `NL80211_CMD_TRIGGER_SCAN` with a wildcard SSID;
- waits `delay_ms` milliseconds, default `5000`, max `30000`;
- dumps BSS count via `NL80211_CMD_GET_SCAN`;
- redacts raw SSID/BSSID content.

The nl80211 socket has a receive timeout so the PID 1 command path does not
block indefinitely. If scan trigger returns `EBUSY`, the command records
`trigger_busy_continue=1` and still performs the bounded scan dump.

It does not:

- launch Wi-Fi HAL/HIDL;
- start or use `wpa_supplicant`;
- associate or authenticate;
- read or write Wi-Fi credentials;
- run DHCP;
- install routes;
- ping external hosts.

Expected decision labels:

| Label | Meaning |
| --- | --- |
| `wifi-scan-pass` | At least one BSS entry was returned. |
| `wifi-scan-zero-bss` | Scan completed but no BSS entry was returned. |
| `wifi-scan-iface-missing` | `wlan0` is absent. |
| `wifi-scan-iface-up-failed` | `SIOCSIFFLAGS` failed. |
| `wifi-scan-nl80211-open-failed` | Generic netlink socket/family setup failed. |
| `wifi-scan-trigger-failed` | `NL80211_CMD_TRIGGER_SCAN` failed. |
| `wifi-scan-dump-failed` | `NL80211_CMD_GET_SCAN` failed. |

`wifi scan` remains blocked while the native-init menu/power-busy gate is
active. Hide the menu first when deliberately running scan.

## `wifi config ...`

`wifi config status` and `wifi config prepare [profile]` remain delegated to the
existing Wi-Fi config module.

- `status` is read-only and menu-safe.
- `prepare` is explicit and writes only runtime config under `/cache/a90-wifi/`.
- Public git must never contain raw PSK, generated supplicant config, DHCP
  leases, or connect artifacts.

## Next Command

The next native-init command should be:

```text
wifi connect [profile]
```

Minimum contract before implementation:

- use the staged standalone `wpa_supplicant` bundle established by V2171;
- use the prepared config path from `wifi config prepare`;
- wait for the private control socket under `/cache/a90-wifi/sockets/`;
- issue bounded `SCAN`/`SELECT_NETWORK` or equivalent control actions;
- capture redacted supplicant status and kernel state;
- avoid DHCP/routes/ping unless the command is explicitly scoped beyond link
  association.

## Immediate Connect Entry Gates

These risks must be blocked before implementing or live-running
`wifi connect [profile]`:

1. `wlan0` readiness gate:
   - wait for `wifi status` to report `decision=wifi-status-wlan0-present`;
   - use a bounded timeout and emit a precondition label if `wlan0` is absent;
   - do not start supplicant against a missing interface.
2. Wi-Fi bring-up property root:
   - keep V2172-style Wi-Fi test boots on the verified V726 property snapshot
     unless a new snapshot is explicitly provisioned;
   - do not point helpers at non-existent per-run roots such as
     `/mnt/sdext/a90/private-property-v317/v2172/dev/__properties__`.
3. Secret hygiene:
   - load SSID/PSK only from `workspace/private/secrets/` or existing private
     runtime env files;
   - write generated supplicant config only under `/cache/a90-wifi/`;
   - never use `wpa_supplicant -K`;
   - redact SSID/PSK/BSSID/MAC/IP in public artifacts and keep
     `secret_values_logged=0`.

Everything else, including helper supervisor timeout cleanup, repeated-run
stability, hold/idle, reconnect, autoconnect, and UI polish, belongs to the
post-connect stabilization pass unless it blocks the first bounded connect.
