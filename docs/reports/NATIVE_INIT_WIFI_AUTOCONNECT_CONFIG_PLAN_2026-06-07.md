# Native Init Wi-Fi Autoconnect Config Plan

## Summary

- Type: design plan.
- Target baseline: `v726-wifi-lifecycle`.
- Status: planned; no autoconnect implementation is enabled by this document.
- Goal: persist known Wi-Fi profiles and optionally connect at boot without exposing credentials in logs, HUD, or uploaded artifacts.

## Current Baseline

- Native Wi-Fi bring-up is persistent enough for `wlan0` to appear at boot.
- Bounded connect evidence already proved association, DHCP, gateway ping, and external ping.
- The HUD consumes `/cache/native-init-wifi-runtime.summary` for non-secret runtime state.
- Boot does not currently scan, connect, run DHCP, or ping unless a test/helper explicitly does so.

## Config Layout

- Primary config root: `/mnt/sdext/a90/config/wifi/`
- Primary secret root: `/mnt/sdext/a90/secrets/wifi/`
- Cache fallback root: `/cache/a90-wifi/config/`
- Runtime root: `/cache/a90-wifi/`
- Config file mode: `0600`
- Secret file mode: `0600`
- Directory mode: `0700`

Recommended files:

- `/mnt/sdext/a90/config/wifi/autoconnect.conf`
- `/mnt/sdext/a90/config/wifi/profiles/<profile>.conf`
- `/mnt/sdext/a90/secrets/wifi/<profile>.psk`
- `/cache/a90-wifi/wpa_supplicant.conf`
- `/cache/native-init-wifi-runtime-input.summary`

## Global Options

Example `autoconnect.conf`:

```ini
version=1
autoconnect=0
default_profile=home5g
connect_timeout_sec=35
dhcp=1
external_ping=0
scan_before_connect=1
retry_count=1
```

Rules:

- `autoconnect=0` is the default until the user explicitly enables it.
- `external_ping=0` is the default for boot; external reachability tests remain explicit.
- DHCP may be enabled for autoconnect, but route/DNS changes must be recorded in runtime state.

## Profile Options

Example `profiles/home5g.conf`:

```ini
version=1
enabled=1
ssid_file=/mnt/sdext/a90/secrets/wifi/home5g.ssid
psk_file=/mnt/sdext/a90/secrets/wifi/home5g.psk
band=5g
priority=100
key_mgmt=WPA-PSK
```

Rules:

- Store SSID and PSK in separate `0600` files so config status can report only `ssid_present=1` and `psk_present=1`.
- Do not write raw SSID, PSK, BSSID, full MAC, assigned IP, DNS, or DHCP lease into regular logs.
- Generated `wpa_supplicant.conf` must live under `/cache/a90-wifi/` and be deleted or overwritten on each connect attempt.

## Commands

Planned user-facing commands:

- `wifi config status`: validate config roots, file modes, and profile presence without printing secrets.
- `wifi profile add <name>`: create profile metadata and prompt/write secret files through a controlled path.
- `wifi profile list`: show profile names, enabled state, band, priority, and secret presence only.
- `wifi scan`: bring `wlan0` up and run a bounded scan without association.
- `wifi connect <profile>`: run one bounded connect, DHCP if enabled, and update runtime summary.
- `wifi disconnect`: stop supplicant/client state and return `wlan0` to a clean idle state.
- `wifi autoconnect enable|disable`: toggle boot autoconnect explicitly.

## Boot Autoconnect Flow

1. Wait for V726 baseline readiness: `wlan0_present=1` and `baseline_ready=1`.
2. Read `autoconnect.conf`; exit if absent or `autoconnect=0`.
3. Validate default/enabled profile and secret file modes.
4. Generate `/cache/a90-wifi/wpa_supplicant.conf` from profile secrets.
5. Start `wpa_supplicant` with `-D nl80211 -i wlan0` and a native-writable control directory.
6. Wait for `COMPLETED` up to `connect_timeout_sec`.
7. Run DHCP only if `dhcp=1`.
8. Update `/cache/native-init-wifi-runtime-input.summary` with safe display labels.
9. Leave external ping disabled unless an explicit test command requested it.

## HUD Surface

The HUD should stay compact:

- Disconnected baseline: `WIFI READY wlan0 down xx:7f:3a`
- Connected: `WIFI UP <ssid_label> -56dBm 866M 192.168.0.x`
- Active traffic: append `D<rx>/U<tx>M` only when RX/TX deltas are non-zero.

Label rules:

- `ssid_label` may be full for local HUD, but artifacts must redact it.
- `ip4_label` remains masked as `a.b.c.x`.
- MAC stays tail-only.

## Artifact Hygiene

- Do not upload config roots or secret roots by default.
- Archive allowlist must exclude:
  - `/mnt/sdext/a90/config/wifi/`
  - `/mnt/sdext/a90/secrets/wifi/`
  - `/cache/a90-wifi/wpa_supplicant.conf`
  - `/cache/a90-wifi/*.psk`
- Secret scan must check raw SSID/PSK values and hex encodings before accepting any archive.
- Reports should contain presence booleans and redacted labels only.

## Implementation Progress

- 2026-06-07: Step 1 source scaffold added.
  - Added `wifi config status` as a read-only native-init command.
  - Validates config roots, autoconnect config, default profile metadata, secret-file presence, and owner-only modes.
  - Does not read, print, archive, or log SSID/PSK values; status prints `secret_values_logged=0`.
  - Boot autoconnect, scan, connect, DHCP, routes, and ping remain disabled until later steps.

## Implementation Order

1. Add config parser and `wifi config status`.
2. Add profile validation and generated supplicant config writer.
3. Add explicit `wifi scan` and `wifi connect <profile>` commands.
4. Add runtime summary bridge for SSID/RSSI/link speed after connection.
5. Add boot autoconnect gated by `autoconnect=1`.
6. Add hold/reconnect policy only after one-shot autoconnect is stable.

## Acceptance Gates

- Config status passes with `secret_values_logged=0`.
- One explicit connect updates HUD/runtime state and preserves artifact redaction.
- Boot with `autoconnect=0` remains identical to current V726 baseline.
- Boot with `autoconnect=1` connects to the selected profile and records carrier/DHCP state.
- Rollback to the current V726 image remains valid.

## Open Decisions

- Whether the first implementation supports multiple profiles or only one `default_profile`.
- Whether SSID should be shown in full on the local HUD or shortened by default.
- Whether DHCP autoconnect should install default route/DNS at boot or require an explicit `network=full` option.
