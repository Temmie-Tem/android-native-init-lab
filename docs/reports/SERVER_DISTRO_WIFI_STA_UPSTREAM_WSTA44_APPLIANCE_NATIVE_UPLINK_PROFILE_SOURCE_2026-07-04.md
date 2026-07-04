# WSTA44 Appliance Native-Uplink Profile Source

- Date: 2026-07-04
- Scope: host-only source/productization update
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta44-appliance-native-uplink-profile-source-pass`

## What Changed

WSTA43 proved the full WSTA28 -> WSTA42 live path.  WSTA44 moves that proof into
the appliance workflow contract without making public exposure a boot default.

Added a Debian-side appliance policy helper:

- `/usr/local/bin/a90-dpublic-native-uplink-profile`
- default `profile`/`preflight` mode records readiness only;
- `autoconnect-confirmed` remains operator-gated through
  `/etc/a90-dpublic/native-uplink-enable`,
  `A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED=1`, and the native uplink confirm token;
- public/quick tunnel operations are not started by this helper and report that the
  WSTA43 host-orchestrated public sequence is required.

Updated both rootfs staging paths:

- `build_debian_aarch64_rootfs.py` stages the new helper and records the stage
  marker contract.
- `prepare_wsta3_sta_rootfs.py` stages the same helper when refreshing an existing
  WSTA rootfs and canonicalizes the native-uplink/public-default marker lines in
  `/etc/a90-server-distro-stage`.

Updated firstboot:

- records whether the native-uplink profile helper is present;
- records `native_uplink_decision=operator-profile-manual`;
- records `native_uplink_public_default=off`;
- does not auto-run native uplink or public tunnel from this new profile.

## Safety

- No boot image was built or flashed.
- No device command was run.
- No Wi-Fi association, DHCP, ping, cloudflared process, public URL, SSID, PSK, or
  raw network identifier is recorded in this report.
- Existing WSTA43 remains the bounded public-live path.  Persistent always-on public
  exposure remains a separate gate.

## Validation

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_dpublic_smoke_helpers \
  tests.test_server_distro_debian_rootfs_builder \
  tests.test_prepare_wsta3_sta_rootfs
```

Result: `Ran 37 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py \
  workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py
```

Result: pass

```text
sh -n \
  workspace/public/src/scripts/server-distro/a90_dpublic_native_uplink_profile.sh \
  workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh
```

Result: pass

```text
git diff --check
```

Result: pass

## Next

WSTA45 can turn this profile into an operator-facing wrapper or appliance menu
entry that runs the already-proven WSTA43 sequence with the same explicit native
reboot, credentialed-Wi-Fi, and public-exposure gates.  That should remain
default-off and fail-closed.
