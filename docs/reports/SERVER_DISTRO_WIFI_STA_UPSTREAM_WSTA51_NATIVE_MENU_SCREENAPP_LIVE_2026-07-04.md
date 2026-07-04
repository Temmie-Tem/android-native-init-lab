# WSTA51 Native Menu Screenapp Live

- Date: 2026-07-04
- Scope: rollback-gated live validation of the WSTA native screenapp surface
- Candidate: `A90 Linux init 0.11.151 (v3395-wsta-screenapp-live)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3395_wsta_screenapp_live.img`
- Boot SHA256: `4d3eb72f20d8a2cf6186b81b7cdcf86c01b68bbc34d9007cc573d0bb19fb0605`
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Decision: `wsta51-native-menu-screenapp-live-pass`

## Summary

WSTA51 validates the WSTA50 native menu/screenapp surface in a real boot artifact.
V3395 was built from the V3394 resident baseline and adds no Wi-Fi association,
DHCP, public tunnel, native reboot, userdata handoff, or flash behavior to the
WSTA screen.  The screen remains a read-only operator display surface.

The live `screenapp wsta` and `screenapp dpublic` aliases both presented the
same `WSTA D-PUBLIC` screen successfully:

```text
screenapp.safety=display-only-explicit
screenapp.title=WSTA D-PUBLIC
screenapp.valid=1
screenapp.rc=0
screenapp.presented=1
```

## Build Evidence

New source builder:

- `workspace/public/src/scripts/revalidation/build_native_init_boot_v3395_wsta_screenapp_live.py`

The builder inherits the V3394 redacted WPA failure-detail image and changes only
the V3395 identity plus WSTA screenapp live-validation metadata.  Its boot-image
required-string audit includes:

```text
screenapp.title=WSTA D-PUBLIC
WSTA D-PUBLIC
WSTA PUBLISH
FLOW WSTA45 -> WSTA43 -> WSTA42
PUBLISH: HOST RUNBOOK ONLY
NATIVE MENU: DISPLAY-ONLY NO CONNECT
AGGREGATE: WSTA48 REDACTED RESULT
```

Generated source-build report:

- `docs/reports/NATIVE_INIT_V3395_WSTA_SCREENAPP_SOURCE_BUILD_2026-07-04.md`

## Flash And Health

Pre-flash gates:

- Current resident health was clean: `status` and `selftest` reported `fail=0`.
- Rollback images were present and matched the required SHA256 values for v2321 and
  v2237; the v48 fallback image was present.
- TWRP recovery image was present and matched the documented recovery image SHA256.
- The checked helper verified local Android boot magic, expected version marker,
  local image SHA256, remote pushed image SHA256, and boot-prefix readback SHA256.

Flash result:

```text
phase.native_init_flash.total.elapsed_sec=61.834 ok=1
version: 0.11.151 build=v3395-wsta-screenapp-live
status=ok
```

Post-boot health:

```text
selftest: pass=12 warn=1 fail=0
status: selftest fail=0
```

Post-screenapp status remained clean.  `wifi status` was queried only as a read-only
post-check; it reported no active supplicant process, no active interface, autoconnect
disabled, and `secret_values_logged=0`.

## Screenapp Live Result

The first direct `screenapp` attempt returned `busy` because the auto menu was active.
After an explicit `hide` and settle delay, both aliases passed:

```text
cmdv1 screenapp wsta
screenapp.app=wsta
screenapp.safety=display-only-explicit
screenapp.title=WSTA D-PUBLIC
screeninfo: presented framebuffer 1080x2400 on crtc=133
screenapp.valid=1
screenapp.rc=0
screenapp.presented=1
status=ok
```

```text
cmdv1 screenapp dpublic
screenapp.app=dpublic
screenapp.safety=display-only-explicit
screenapp.title=WSTA D-PUBLIC
screeninfo: presented framebuffer 1080x2400 on crtc=133
screenapp.valid=1
screenapp.rc=0
screenapp.presented=1
status=ok
```

## Safety

- Only the boot partition was flashed, and only through `native_init_flash.py`.
- No forbidden partition was touched.
- No credentialed Wi-Fi association, DHCP, public tunnel, public smoke request,
  userdata format/populate, switch-root, or persistent public exposure ran.
- No raw public URL, confirm token, SSID, PSK, BSSID, MAC, IP, gateway, DNS value,
  or device serial is committed in this report.
- The initial `busy` response did not change device state; it confirmed the existing
  menu policy boundary.  The successful run used the documented `hide` pre-step.

## Validation

Host/source validation:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_build_native_init_boot_v3395_wsta_screenapp_live \
  tests.test_native_wsta_operator_screenapp_source
```

Result: `Ran 6 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_native_init_boot_v3395_wsta_screenapp_live.py
```

Result: pass

Live validation:

- V3395 checked-helper flash: pass.
- `version`, `status`, `selftest`: pass with `fail=0`.
- `screenapp wsta`: pass, `presented=1`.
- `screenapp dpublic`: pass, `presented=1`.
- post-screenapp `status`/`selftest`: pass with `fail=0`.

## Next

WSTA now has a real native visual operator surface for the bounded publish path.
The next meaningful WSTA step is no longer another display/productization pass; it
should be a gated persistent exposure design or a live run of the WSTA45 operator
publish path using the committed WSTA49 runbook.
