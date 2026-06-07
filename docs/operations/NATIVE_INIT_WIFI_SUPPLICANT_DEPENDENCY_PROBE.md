# Native Init Wi-Fi Supplicant Dependency Probe

Date: `2026-06-08`

## Purpose

This probe decides whether native Wi-Fi connect must carry the staged
standalone `wpa_supplicant` bundle, or whether an existing vendor supplicant can
run in the minimal direct `nl80211` route.

It is a dependency discriminator, not the final Wi-Fi lifecycle command.

## Scope

Default mode is credential-free:

- starts each candidate with an empty no-connect config;
- uses direct `-i wlan0 -D nl80211 -c <config> -O <native socket dir> -t`;
- waits for `/cache/a90-wifi/.../sockets/wlan0`;
- sends `PING` through a tiny staged `a90_wpa_ctrl_request` helper;
- terminates the candidate and removes probe scratch data.

Optional `connect` mode uses an already prepared remote
`/cache/a90-wifi/wpa_supplicant.conf` and checks carrier only. It does not run
DHCP, install routes, or ping.

## Candidate Matrix

Each candidate is tested twice:

| Base | Path | Context |
| --- | --- | --- |
| `standalone` | `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` | native direct |
| `standalone` | `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` | `u:r:hal_wifi_supplicant_default:s0` |
| `vendor_hw` | `/vendor/bin/hw/wpa_supplicant` | native direct |
| `vendor_hw` | `/vendor/bin/hw/wpa_supplicant` | `u:r:hal_wifi_supplicant_default:s0` |
| `vendor` | `/vendor/bin/wpa_supplicant` | native direct |
| `vendor` | `/vendor/bin/wpa_supplicant` | `u:r:hal_wifi_supplicant_default:s0` |

This separates binary availability, dynamic/runtime dependency, `nl80211`
initialization, control socket readiness, and SELinux exec-context dependency.

## Commands

Credential-free dependency probe:

```bash
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_wifi_supplicant_dependency_probe.py \
  --label no-connect
```

Optional carrier-only connect probe after preparing a config on-device:

```bash
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_wifi_supplicant_dependency_probe.py \
  --label connect-default \
  --mode connect \
  --prepare-profile default
```

## Decisions

- `supplicant-dependency-precondition-wlan0-missing`: rerun on a Wi-Fi-ready
  boot/helper route; this is not a supplicant dependency result.
- `supplicant-dependency-vendor-direct-ctrl-ready`: a vendor candidate can be
  used for the baseline direct `nl80211` route without the standalone bundle for
  at least no-connect control readiness.
- `supplicant-dependency-standalone-only-ctrl-ready`: keep the standalone bundle
  as the baseline dependency unless a later connect-mode vendor test passes.
- `supplicant-dependency-no-ctrl-ready-candidate`: dependency wall remains before
  native `wifi connect`; inspect per-candidate log counters.
- `supplicant-dependency-vendor-hw-connects` or
  `supplicant-dependency-vendor-connects`: vendor supplicant can replace the
  standalone bundle for carrier-level connect.
- `supplicant-dependency-standalone-connects`: standalone remains the practical
  connect dependency.

## Safety

- No Wi-Fi HAL/HIDL/global socket path is used.
- No DHCP, route, DNS, credential upload, or external ping occurs.
- No raw SSID/PSK is logged by the probe.
- Probe artifacts are written under structured private `tmp/wifi/runs/`.
- Probe scratch under `/cache/a90-wifi/supplicant-dependency-probe/` is removed
  unless `--keep-remote` is explicitly set.

## V2171 Result

V2171 ran the probe on a `v726-wifi-lifecycle` Wi-Fi-ready route and rolled back
to `v2169-transport-contract`.

- Decision: `supplicant-dependency-standalone-only-ctrl-ready`
- Evidence: `tmp/wifi/runs/native-wifi-supplicant-dependency-probe-no-connect-v726-wlan0-final-20260608-064510/manifest.json`
- Consequence: native `wifi connect` should keep the staged standalone
  `wpa_supplicant` bundle; vendor supplicant paths were absent in the native
  namespace.
