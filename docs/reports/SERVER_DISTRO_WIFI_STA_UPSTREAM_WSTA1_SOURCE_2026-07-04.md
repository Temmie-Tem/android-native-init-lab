# Server-Distro Wi-Fi STA Upstream WSTA1 Source Gate

- Date: 2026-07-04 KST
- Unit: WSTA1 Debian STA client rootfs/firstboot support.
- Scope: source/static validation only.
- Device action: none. No flash, no reboot, no Wi-Fi association, no DHCP, no public tunnel start.

## Verdict

WSTA1 is implemented source-side.

The Debian appliance now has a source path for STA-only upstream that preserves the Stage0 hardware
contract: native init materializes `wlan0`, while Debian owns the long-lived station supplicant, DHCP,
route policy, and public tunnel after handoff.

The default D-public boot remains non-Wi-Fi and non-public by default. STA starts only when the operator
stages the explicit enable file and private supplicant config under `/etc/a90-dpublic/`.

## Change

`workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py` now includes the Debian STA
client tools in the rootfs package set:

- `wpasupplicant`
- `isc-dhcp-client`

The builder also stages the new helper:

- source: `workspace/public/src/scripts/server-distro/a90_dpublic_wifi_sta.sh`
- target: `/usr/local/bin/a90-dpublic-wifi-sta`
- mode: `0755`

`workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh` now runs the helper only when
`/etc/a90-dpublic/wifi-sta-enable` exists. If the enable file is absent, firstboot records
`wifi_sta_requested=0`, `wifi_sta_started=0`, `wifi_sta_decision=wifi-sta-manual`, and
`wifi_sta_secret_values_logged=0`.

The helper requires:

- `/etc/a90-dpublic/wifi-sta-enable`
- `/etc/a90-dpublic/wpa_supplicant-wlan0.conf`
- Debian `wpa_supplicant`, `dhclient`, and `ip`

It appends redacted marker fields only. It does not parse, print, or commit SSID/PSK values.

## Validation

Static/source validation:

```text
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_wifi_sta.sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py \
  tests/test_dpublic_smoke_helpers.py \
  tests/test_server_distro_debian_rootfs_builder.py \
  tests/test_server_distro_wifi_sta_upstream_plan.py
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_dpublic_smoke_helpers \
  tests.test_server_distro_debian_rootfs_builder \
  tests.test_server_distro_wifi_sta_upstream_plan
git diff --check
```

## Safety Boundary

- No boot image was built or flashed.
- No live device command was executed.
- No Wi-Fi scan/connect/DHCP/ping was run.
- No public tunnel was started or stopped.
- No credentials, public URLs, tokens, BSSID/MAC, DHCP leases, or concrete private-network addresses are
  committed.
- Native init still does not own the public tunnel; this is Debian firstboot/rootfs support only.

## Next Gate

WSTA2 should validate the native side below association:

- flash only through the checked helper if a new boot artifact is needed;
- run `server-distro hardware-contract`;
- prove `wlan0_present=1` through `wifi status` or a bounded no-start probe;
- keep native STA/DHCP/tunnel workers stopped;
- keep `selftest fail=0`.

WSTA3, with private credentials staged by the operator, should then boot Debian and validate that
`a90-dpublic-wifi-sta` can associate, run DHCP, preserve USB NCM recovery, and make the outbound default
route `wlan0` without logging secrets.
