# Native Init Wi-Fi Lifecycle Commands

Date: `2026-06-09`

This is the operator-facing command contract for native-init Wi-Fi lifecycle
work. It keeps diagnostic/status commands separate from scan/connect/autoconnect
mutations.

## Current Command Surface

```text
wifi
wifi status
wifi scan [delay_ms]
wifi connect [profile]
wifi dhcp [profile]
wifi cleanup
wifi profile list
wifi profile status [profile]
wifi autoconnect status
wifi autoconnect enable [profile]
wifi autoconnect disable
wifi autoconnect once [profile]
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
  `/cache/native-init-wifi-runtime.summary`, including `runtime.decision`;
- machine-readable autoconnect result fields from
  `/cache/a90-wifi/autoconnect.result`:
  `autoconnect.profile`, `autoconnect.decision`, `autoconnect.final_rc`,
  `autoconnect.carrier_up`, and `autoconnect.nameserver_count`;
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

## `wifi profile ...`

`wifi profile list` and `wifi profile status [profile]` expose only redacted
profile inventory:

- profile name, enabled state, band, priority, key management;
- config/secret presence and mode booleans;
- no raw SSID, PSK, BSSID, MAC, DHCP lease, or generated supplicant config.

Profile files are staged by the host-side helper
`workspace/public/src/scripts/revalidation/a90_wifi_profile_stage.py`. Native
commands intentionally do not accept raw PSK argv.

## `wifi autoconnect ...`

`wifi autoconnect status|enable|disable|once` controls explicit profile-backed
autoconnect:

- `status` is read-only.
- `enable [profile]` validates the profile and writes `autoconnect=1`.
- `disable` writes `autoconnect=0` and does not tear down an active link.
- `once [profile]` runs the same bounded connect/DHCP sequence on demand.

Boot autoconnect is disabled by default and is started in the background only
when staged config says `autoconnect=1`. Boot autoconnect never runs external
ping. A valid run writes `wifi-autoconnect-running` immediately, then replaces
it with a terminal result such as `wifi-autoconnect-pass`,
`wifi-autoconnect-connect-failed`, or `wifi-autoconnect-wlan0-timeout`.
Disabled/no-config boot paths write authoritative inactive result files so
older success state is not reused by status/UI polling.

## `wifi connect [profile]`

`wifi connect [profile]` is the bounded association/carrier primitive. It is not
a full network bring-up command.

It:

- waits for `wlan0` with a bounded timeout;
- brings `wlan0` administratively up;
- calls the same config generator as `wifi config prepare [profile]`;
- requires the staged standalone `wpa_supplicant` bundle from V2171;
- starts or reuses standalone `wpa_supplicant` with:

```text
wpa_supplicant -i wlan0 -D nl80211 -c /cache/a90-wifi/wpa_supplicant.conf -O /cache/a90-wifi/sockets -t
```

- waits for `/cache/a90-wifi/sockets/wlan0` to answer `PING`;
- sends redacted ctrl commands:
  - `DRIVER COUNTRY KR`;
  - `SCAN`;
  - `ENABLE_NETWORK 0`;
  - `SELECT_NETWORK 0`;
  - `REASSOCIATE`;
- waits for `/sys/class/net/wlan0/carrier` to become `1`;
- leaves the supplicant running only if carrier comes up.

It does not:

- run DHCP;
- install routes;
- set DNS;
- ping external hosts;
- enable boot autoconnect;
- print raw SSID, PSK, BSSID, MAC, IP, or raw ctrl replies.

Expected decision labels:

| Label | Meaning |
| --- | --- |
| `wifi-connect-carrier-up` | Association/carrier succeeded. |
| `wifi-connect-no-carrier` | Supplicant control path ran, but carrier did not come up before timeout. |
| `wifi-connect-wlan0-timeout` | `wlan0` did not appear before the bounded precondition timeout. |
| `wifi-connect-config-prepare-failed` | Profile/secret-backed supplicant config generation failed. |
| `wifi-connect-supplicant-missing` | Standalone `wpa_supplicant` wrapper is absent or not executable. |
| `wifi-connect-supplicant-start-failed` | PID1 failed to spawn the standalone supplicant. |
| `wifi-connect-ctrl-timeout` | Supplicant started but private control socket did not become ready. |
| `wifi-connect-supplicant-busy-no-ctrl` | A supplicant-like process exists but no usable private ctrl socket is available. |

`wifi connect` remains blocked while the native-init menu/power-busy gate is
active. Hide the menu first when deliberately running association.

Live validation entrypoint:

```text
python3 workspace/public/src/scripts/revalidation/native_wifi_connect_carrier_handoff_v2174.py
```

The runner flashes the V2174 test boot, runs only the carrier-level connect
window, and verifies rollback `selftest fail=0`. After the V2183 promotion, this
runner remains carrier-level evidence only; new Wi-Fi lifecycle work should
treat `v2182-hud-menu-cleanup` as the current baseline and use older images only
for explicit rollback/regression testing.

## `wifi dhcp [profile]`

`wifi dhcp [profile]` is the bounded DHCP/temporary-route primitive after
carrier-level association. It is not an association command and it is not a
general connectivity soak.

It:

- requires `wlan0` to exist;
- requires `/sys/class/net/wlan0/carrier` to be `1`;
- writes a generated DHCP script under `/cache/a90-wifi/`;
- runs bounded BusyBox `udhcpc` against `wlan0`;
- installs temporary wlan0 route/DNS from DHCP;
- updates `/cache/native-init-wifi-runtime.summary` for the HUD/status surface;
- prints only high-level DHCP state.

It does not:

- start Wi-Fi association if carrier is absent;
- run external ping;
- persist credentials;
- create boot autoconnect state;
- print raw SSID, PSK, BSSID, DHCP lease transcript, gateway, DNS server, or
  ping transcript in public reports.

Expected decision labels:

| Label | Meaning |
| --- | --- |
| `wifi-dhcp-pass` | DHCP succeeded and IPv4/default route are present. |
| `wifi-dhcp-wlan0-missing` | `wlan0` was absent. |
| `wifi-dhcp-no-carrier` | Carrier was absent; run `wifi connect` first. |
| `wifi-dhcp-busybox-missing` | BusyBox was not executable. |
| `wifi-dhcp-script-prepare-failed` | Runtime directory/script setup failed. |
| `wifi-dhcp-failed` | DHCP ran but did not produce the required state. |

## `wifi cleanup`

`wifi cleanup` removes Wi-Fi connectivity residue for repeated tests:

- sends `TERMINATE` to the private supplicant control socket when present;
- stops stale `udhcpc` by pidfile;
- removes temporary wlan0 default route/address and generated resolver files;
- refreshes the runtime summary.

It is intentionally separate from `wifi dhcp` so stability runs can choose
whether to keep the link up for hold/idle validation.

## Connectivity Runner

The first DHCP/route/ping-scoped runner is:

```text
python3 workspace/public/src/scripts/revalidation/native_wifi_dhcp_ping_handoff_v2176.py
```

Minimum contract:

- require `wifi connect`/carrier as precondition;
- run DHCP with bounded timeout;
- install only temporary scoped routes/DNS;
- keep external ping as an explicit test-only scope.

## Immediate Connect Entry Gates

These risks must be blocked before implementing or live-running
`wifi connect [profile]`:

1. `wlan0` readiness gate:
   - wait for `wifi status` to report `decision=wifi-status-wlan0-present`;
   - use a bounded timeout and emit a precondition label if `wlan0` is absent;
   - do not start supplicant against a missing interface.
2. Wi-Fi bring-up property root:
   - keep Wi-Fi test boots on the verified V726-derived property snapshot used
     by the promoted V2174 baseline unless a new snapshot is explicitly
     provisioned;
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
